import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import database
from reference_data import match_career, reference_index
from resume_examples import catalog, example_pdf
from resume_pipeline import analyze_resume
from services import extract_document, persist_analysis, load_analysis, issue_certificate
from scoring import evaluate_resume


class ReferenceAppTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.patch=patch.object(database,'DB_PATH',str(Path(self.temp.name)/'test.db'));self.patch.start()
        database.initialize();self.conn=database.get_connection()
    def tearDown(self):
        self.conn.close();self.patch.stop();self.temp.cleanup()
    def test_reference_archive_complete_and_private(self):
        data=reference_index()
        if not data['records']:self.skipTest('Optional private reference index is not configured')
        self.assertEqual(data['summary']['files'],2484)
        self.assertGreaterEqual(data['summary']['categories'],20)
        self.assertEqual(len(data['records']),2484)
        self.assertFalse(any('resume_text' in r or 'name' in r or 'email' in r for r in data['records']))
        self.assertEqual(sum(data['summary'][k] for k in ['usable','unreadable','duplicates']),2484)
    def test_matching_and_abstention(self):
        if not reference_index()['profiles']:self.skipTest('Optional private reference index is not configured')
        self.assertIsNone(match_career(['zzzzzz']))
        for skills,category in [(['autocad','solidworks','thermodynamics','fabrication'],'ENGINEERING'),(['accounting','auditing','general ledger','accounts payable'],'ACCOUNTANT')]:
            match=match_career(skills)
            self.assertIsNotNone(match)
            self.assertEqual(match['field'],category)
    def test_examples_scores_and_complete_structure(self):
        for example in catalog():
            self.assertEqual(evaluate_resume(extract_document(example_pdf(example['id']),'sample.pdf'))['score'],example['score'],example['id'])
        for example in [e for e in catalog() if 'All names, organizations' in e['text']]:
            for heading in ['Profile','Skills','Education','Projects','Certifications','Achievements']:
                self.assertIn(heading,example['text'])
    def test_analysis_save_report_and_certificate(self):
        result=analyze_resume(self.conn,example_pdf('008'),'resume.pdf')
        self.assertFalse(result['model']['used_model'])
        saved=persist_analysis(self.conn,'owner','hash','resume.pdf',result)
        self.assertEqual(load_analysis(self.conn,'owner',saved['analysis_id'])['score'],result['score'])
        from reports import build_pdf
        with self.assertRaisesRegex(ValueError,'report or certificate'):
            analyze_resume(self.conn,build_pdf(saved),'report.pdf')
        from certificate_verification import verify_certificate
        cert=issue_certificate(self.conn,'owner',saved['analysis_id'])
        self.assertEqual(verify_certificate(self.conn,cert['code'])['status'],'issued')
    def test_admin_has_only_requested_tools(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(Path(database.__file__).with_name('App.py')),default_timeout=40)
        app.session_state['_ara_nav']='Admin';app.session_state['_ara_admin_ok']=True;app.session_state['_ara_admin_until']=time.time()+300
        app.run();self.assertFalse(app.exception,str(app.exception))
        self.assertTrue(any(e.label=='Pin and moderate feedback' for e in app.expander))
        self.assertTrue(any(e.label=='Verify certificate' for e in app.expander))
        self.assertFalse(any('train' in b.label.casefold() or 'activate' in b.label.casefold() for b in app.button))
        self.assertFalse(any('Model Management' in str(c.value) for c in app.segmented_control))
    def test_user_and_about_pages(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(Path(database.__file__).with_name('App.py')),default_timeout=40).run()
        self.assertFalse(app.exception,str(app.exception))
        app.button(key='nav_About').click().run()
        self.assertFalse(app.exception,str(app.exception))
        self.assertTrue(any('no model training' in m.value.casefold() for m in app.markdown))

    def test_training_api_removed(self):
        import threading
        from urllib.request import Request,urlopen
        from urllib.error import HTTPError
        from api import Handler,ThreadingHTTPServer
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            for endpoint in ['train','activate','datasets','processing-preview']:
                req=Request('http://127.0.0.1:'+str(server.server_port)+'/api/'+endpoint,data=b'{}',headers={'Content-Type':'application/json'})
                with self.assertRaises(HTTPError) as error:urlopen(req,timeout=5)
                self.assertEqual(error.exception.code,410)
                error.exception.close()
        finally:server.shutdown();server.server_close();thread.join()


if __name__=='__main__':unittest.main()
