"""Validation, private saved analyses, and additive database migrations."""
import datetime as dt
import hashlib
import io
import json
import os
import re
import secrets
import uuid
import zipfile
from pathlib import PurePosixPath
from xml.etree import ElementTree as ET


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def normalize_candidate(data, name='', email='', mobile='', resume_text=None):
    data = dict(data)
    def clean(value):
        value = str(value or '').strip()
        return '' if value.lower() in {'none', 'null', 'nan', 'n/a'} else value
    from candidate_identity import is_person_name, extract_candidate_name
    valid_name = is_person_name
    if resume_text is not None:
        data['name'] = extract_candidate_name(resume_text)
    def valid_email(value):
        return bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value))
    def valid_phone(value):
        return 7 <= len(re.sub(r'\D', '', value)) <= 15
    for key, fallback, validator in [('name', name, valid_name), ('email', email, valid_email), ('mobile_number', mobile, valid_phone)]:
        value, fallback = clean(data.get(key)), clean(fallback)
        data[key] = value if validator(value) else fallback if validator(fallback) else 'Unavailable'
    data['degree'] = data.get('degree') or 'Unavailable'
    data['skills'] = sorted(set(str(s).strip() for s in data.get('skills') or [] if str(s).strip()))
    data['no_of_pages'] = data.get('no_of_pages') or 1
    return data


def extract_document(content, filename):
    if not content or len(content) > int(os.getenv('MAX_RESUME_MB', '10')) * 1024 * 1024:
        raise ValueError('Resume is empty or exceeds the configured size limit.')
    suffix = os.path.splitext(filename)[1].lower()
    try:
        if suffix == '.pdf' and content.startswith(b'%PDF-'):
            from ocr_reader import pdf_text
            text = pdf_text(content)
        elif suffix in {'.png','.jpg','.jpeg'}:
            from ocr_reader import image_text
            text = image_text(content)
        elif suffix == '.docx' and zipfile.is_zipfile(io.BytesIO(content)):
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                if sum(z.file_size for z in archive.infolist()) > 30 * 1024 * 1024:
                    raise ValueError('DOCX expanded size exceeds the limit.')
                root = ET.fromstring(archive.read('word/document.xml'))
                ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                text = '\n'.join(' '.join(t.text or '' for t in para.findall('.//w:t', ns)) for para in root.findall('.//w:p', ns))
        else:
            raise ValueError('Upload a genuine PDF, DOCX, PNG or JPG document.')
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError('Document is corrupted, encrypted, or unreadable. Upload an unlocked PDF or DOCX.') from exc
    text = '\n'.join(line.strip() for line in text.splitlines() if line.strip())
    if len(text) < 40:
        raise ValueError('Not enough text could be read, even after local OCR. Upload a clearer scan, PNG/JPG, or selectable-text PDF.')
    return text


def migrate(conn):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS analyses (id TEXT PRIMARY KEY, owner TEXT NOT NULL, file_hash TEXT NOT NULL, filename TEXT NOT NULL, created_at TEXT NOT NULL, result TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS analyses_owner ON analyses(owner);
    CREATE TABLE IF NOT EXISTS certificates (code TEXT PRIMARY KEY, analysis_id TEXT UNIQUE NOT NULL, candidate TEXT NOT NULL, issued_at TEXT NOT NULL, status TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS dataset_imports (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, archive_hash TEXT NOT NULL, summary TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS dataset_files (hash TEXT PRIMARY KEY, import_id TEXT NOT NULL, category TEXT NOT NULL, path TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS dataset_jobs (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, status TEXT NOT NULL, completed INTEGER NOT NULL DEFAULT 0, total INTEGER NOT NULL DEFAULT 0, error TEXT, archive_path TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS admin_audit (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, action TEXT NOT NULL, details TEXT NOT NULL);
    """)
    columns = {r[1] for r in conn.execute('PRAGMA table_info(user_feedback)')}
    for name, sql in [('pinned', 'INTEGER NOT NULL DEFAULT 0'), ('published', 'INTEGER NOT NULL DEFAULT 0'), ('analysis_id', 'TEXT')]:
        if name not in columns:
            conn.execute(f'ALTER TABLE user_feedback ADD COLUMN {name} {sql}')
    user_columns = {r[1] for r in conn.execute('PRAGMA table_info(user_data)')}
    for name, kind in [('analysis_id','TEXT'),('content_hash','TEXT'),('label_source',"TEXT DEFAULT 'legacy'"),('scoring_version','TEXT')]:
        if name not in user_columns:
            conn.execute(f'ALTER TABLE user_data ADD COLUMN {name} {kind}')
    conn.commit()


def save_analysis(conn, owner, file_hash, filename, result, commit=True):
    analysis_id = str(uuid.uuid4())
    result = dict(result, analysis_id=analysis_id, analyzed_at=now(), filename=filename, file_type=os.path.splitext(filename)[1])
    conn.execute('INSERT INTO analyses VALUES (?,?,?,?,?,?)', (analysis_id, owner, file_hash, filename, result['analyzed_at'], json.dumps(result)))
    if commit:
        conn.commit()
    return result


def load_analysis(conn, owner, analysis_id):
    row = conn.execute('SELECT result FROM analyses WHERE id=? AND owner=?', (analysis_id, owner)).fetchone()
    if not row:
        raise PermissionError('Analysis unavailable for this session.')
    return json.loads(row[0])


def issue_certificate(conn, owner, analysis_id):
    result = load_analysis(conn, owner, analysis_id)
    for attempt in range(4):
        code = 'RA-' + dt.datetime.now(dt.timezone.utc).strftime('%Y') + '-' + secrets.token_hex(16).upper()
        conn.execute('INSERT OR IGNORE INTO certificates VALUES (?,?,?,?,?)', (code, analysis_id, result['candidate']['name'], now(), 'issued'))
        conn.commit()
        row = conn.execute('SELECT * FROM certificates WHERE analysis_id=?', (analysis_id,)).fetchone()
        if row:
            return dict(zip(['code', 'analysis_id', 'candidate', 'issued_at', 'status'], row))
    raise ValueError('Certificate allocation failed; retry the download.')



def verify_password(password):
    import hmac
    encoded = os.getenv('ADMIN_PASSWORD_HASH', '')
    try:
        scheme, iterations, salt, digest = encoded.split('$')
        if scheme != 'pbkdf2_sha256' or int(iterations) < 100000:
            return False
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), int(iterations)).hex()
        return hmac.compare_digest(actual, digest)
    except (ValueError, TypeError):
        return False


def require_admin():
    import streamlit as st
    if not st.session_state.get('_ara_admin_ok') or st.session_state.get('_ara_admin_until', 0) < __import__('time').time():
        raise PermissionError('An authenticated, unexpired admin session is required.')


def audit(conn, action, details):
    conn.execute('INSERT INTO admin_audit(created_at,action,details) VALUES (?,?,?)', (now(), action, json.dumps(details)))
    conn.commit()


def model_operation(function):
    """Serialize model lifecycle operations across Streamlit sessions/processes."""
    from functools import wraps
    @wraps(function)
    def wrapped(conn, *args, **kwargs):
        token = uuid.uuid4().hex
        conn.execute('CREATE TABLE IF NOT EXISTS model_operation_lock (scope TEXT PRIMARY KEY, token TEXT NOT NULL)')
        conn.commit()
        try:
            conn.execute('INSERT INTO model_operation_lock VALUES (?,?)', ('models', token))
            conn.commit()
        except __import__('sqlite3').IntegrityError as exc:
            conn.rollback()
            raise ValueError('A model operation is already running. Retry after it completes. If a server crashed, an administrator must inspect and clear its stale lock.') from exc
        try:
            return function(conn, *args, **kwargs)
        except BaseException:
            # Never commit partially written model metadata while releasing a lock.
            conn.rollback()
            raise
        finally:
            conn.execute('DELETE FROM model_operation_lock WHERE token=?', (token,))
            conn.commit()
    return wrapped


def persist_analysis(conn, owner, file_hash, filename, result, form=None):
    """Commit the saved payload and training-history row together, or neither."""
    form=form or {}
    conn.execute('SAVEPOINT save_complete_analysis')
    try:
        saved=save_analysis(conn,owner,file_hash,filename,result,commit=False)
        candidate=saved['candidate']
        values={
            'sec_token':owner,'act_name':form.get('name',''),'act_mail':form.get('email',''),'act_mob':form.get('mobile',''),
            'Name':candidate['name'],'Email_ID':candidate['email'],'resume_score':str(saved['score']),
            'Timestamp':saved['analyzed_at'],'Page_no':str(candidate['no_of_pages']),
            'Predicted_Field':saved['predicted_field'] if saved['predicted_field']!='Job field could not be determined' else '',
            'User_level':saved['experience_level'],'Actual_skills':json.dumps(saved['skills']),
            'Recommended_skills':json.dumps(saved['recommended_skills']),'Recommended_courses':json.dumps(saved.get('courses',[])),
            'pdf_name':filename,'training_status':'NEW','analysis_id':saved['analysis_id'],'content_hash':file_hash,
            'label_source':'prediction','scoring_version':saved['scoring_version'],
        }
        conn.execute('INSERT INTO user_data ('+','.join(values)+') VALUES ('+','.join('?' for _ in values)+')',list(values.values()))
        conn.execute('RELEASE save_complete_analysis')
        conn.commit()
        return saved
    except Exception:
        conn.execute('ROLLBACK TO save_complete_analysis')
        conn.execute('RELEASE save_complete_analysis')
        raise
