"""CareerViz localhost JSON API. Run: python api.py --port 8502.

Data and training mutations require HTTP Basic admin authentication. The web app
and API share service functions and the same SQLite database. No mock responses.
"""
import argparse
import base64
import hashlib
import hmac
import json
import os
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs

from database import initialize, get_connection
from services import verify_password, persist_analysis, load_analysis
from resume_pipeline import analyze_resume
from certificate_verification import verify_certificate




class Handler(BaseHTTPRequestHandler):
    server_version = 'CareerViz'

    def log_message(self, *_):
        pass  # Request paths can contain private certificate/analysis identifiers.

    def respond(self, status, data, mime='application/json'):
        payload = json.dumps(data, allow_nan=False).encode() if mime == 'application/json' else data
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length',str(len(payload)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers()
        self.wfile.write(payload)

    def admin(self):
        try:
            scheme, encoded = self.headers.get('Authorization','').split(' ',1)
            username, password = base64.b64decode(encoded,validate=True).decode().split(':',1)
            if scheme != 'Basic' or not hmac.compare_digest(username,os.getenv('ADMIN_USER','admin')) or not verify_password(password):
                raise ValueError()
        except Exception:
            raise PermissionError('Admin HTTP Basic authentication is required.')

    def owner(self):
        token = self.headers.get('Authorization','')
        if not token.startswith('Bearer ') or len(token[7:]) < 32:
            raise PermissionError('Use the private owner token returned by POST /api/analyze.')
        return token[7:]

    def handle_request(self):
        parsed = urlsplit(self.path)
        path = parsed.path.rstrip('/')
        query = parse_qs(parsed.query)
        body = {}
        if self.command == 'POST':
            length = int(self.headers.get('Content-Length','0'))
            if length <= 0 or length > 29*1024*1024:
                raise ValueError('JSON request must be between 1 byte and 29 MB.')
            body = json.loads(self.rfile.read(length))
            if not isinstance(body,dict):
                raise ValueError('JSON body must be an object.')
        with get_connection() as conn:
            if self.command == 'GET':
                if path == '/api/health':
                    return self.respond(200,{'application':'CareerViz','database':conn.execute('PRAGMA quick_check').fetchone()[0]})
                if path == '/api/examples':
                    from resume_examples import catalog
                    lo, hi = int(query.get('min_score',['0'])[0]), int(query.get('max_score',['100'])[0])
                    examples = [e for e in catalog() if lo <= e['score'] <= hi and all(e[key]==query[key][0] for key in ['role','industry','level','format'] if key in query)]
                    return self.respond(200,examples)
                if path.startswith('/api/example/'):
                    from resume_examples import example_pdf
                    return self.respond(200,example_pdf(path.split('/')[-1]),'application/pdf')
                if path.startswith('/api/verify/'):
                    result = verify_certificate(conn,path.split('/')[-1])
                    return self.respond(200 if result else 404,result or {'error':'Certificate not found.'})
                if path.startswith('/api/analysis/'):
                    return self.respond(200,load_analysis(conn,self.owner(),path.split('/')[-1]))
                if path in ['/api/models'] or path.startswith('/api/job/'):
                    return self.respond(410,{'error':'Model training has been removed. CareerViz uses the supplied reference dataset.'})
            else:
                if path == '/api/analyze':
                    filename = str(body.get('filename',''))
                    if not filename.lower().endswith(('.pdf','.docx','.png','.jpg','.jpeg')):
                        raise ValueError('Upload a PDF, DOCX, PNG or JPG resume.')
                    content = base64.b64decode(body.get('content_base64',''),validate=True)
                    result = analyze_resume(conn,content,filename,body.get('personal_details',{}),body.get('job_description',''))
                    owner = secrets.token_urlsafe(32)
                    saved = persist_analysis(conn,owner,hashlib.sha256(content).hexdigest(),filename,result,body.get('personal_details',{}))
                    return self.respond(201,{'owner_token':owner,'analysis':saved})
                if path in ['/api/datasets','/api/processing-preview','/api/train','/api/activate']:
                    return self.respond(410,{'error':'Model training has been removed. No upload or activation is required.'})
        self.respond(404,{'error':'Endpoint not found.'})

    def dispatch(self):
        try:
            self.handle_request()
        except PermissionError as exc:
            self.respond(403,{'error':str(exc)})
        except (ValueError,KeyError,TypeError) as exc:
            self.respond(400,{'error':str(exc)})
        except Exception as exc:
            __import__('logging').exception('CareerViz API failure: %s',type(exc).__name__)
            self.respond(500,{'error':'Backend operation failed. Check the server log.'})

    do_GET = dispatch
    do_POST = dispatch


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8502)
    options = parser.parse_args()
    initialize()
    print(f'CareerViz API http://127.0.0.1:{options.port}/api/health',flush=True)
    ThreadingHTTPServer(('127.0.0.1',options.port),Handler).serve_forever()
