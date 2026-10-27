"""Public, code-based verification without exposing private resume records."""
import json
import os
import re
from urllib.parse import urlencode, urlsplit

DEFAULT_PUBLIC_APP_URL = 'https://careerviz7217.streamlit.app'


def verification_url(code=''):
    base = (os.getenv('PUBLIC_APP_URL', '').strip() or DEFAULT_PUBLIC_APP_URL).rstrip('/')
    parts = urlsplit(base)
    if parts.scheme not in {'http','https'} or not parts.netloc or parts.username or parts.password or parts.query or parts.fragment:
        raise ValueError('PUBLIC_APP_URL must be an HTTP(S) application URL without credentials, query or fragment.')
    return base + '/?' + urlencode({'verify': code})


def verify_certificate(conn, code):
    code = str(code or '').strip().upper()
    if not re.fullmatch(r'RA-\d{4}-[0-9A-F]{32}', code):
        return None
    row = conn.execute('SELECT c.code,c.candidate,c.issued_at,c.status,a.result FROM certificates c JOIN analyses a ON a.id=c.analysis_id WHERE c.code=?', (code,)).fetchone()
    if not row:
        return None
    result = json.loads(row[4])
    from scoring import is_generated_assessment
    status='invalid-document' if is_generated_assessment(result.get('resume_text','')) else row[3]
    return {'code': row[0], 'candidate': row[1], 'issued_at': row[2], 'status': status, 'score': result['score'], 'experience_level': result['experience_level'], 'predicted_field': result['predicted_field']}


def render_verification_page(conn):
    import streamlit as st
    st.title('Certificate verification')
    st.caption('CareerViz · Check a certificate against the issuing database')
    initial = st.query_params.get('verify', '')
    with st.form('public_certificate_verification'):
        code = st.text_input('Certificate code', value=initial, max_chars=80)
        submitted = st.form_submit_button('Verify certificate')
    if submitted:
        code = code.strip().upper()
        st.query_params['verify'] = code
    elif not initial:
        st.info('Enter the code printed on the certificate.')
        return
    else:
        code = initial
    certificate = verify_certificate(conn, code)
    if certificate is None:
        st.error('Certificate not found. Check the code and the issuing website address.')
    elif certificate['status'] != 'issued':
        st.error('This certificate is not valid. Status: ' + certificate['status'])
    else:
        st.success('Verified: this certificate was issued by CareerViz.')
        with st.container(border=True):
            st.subheader(certificate['candidate'])
            st.write('Certificate code:', certificate['code'])
            st.write('Issued:', certificate['issued_at'])
            st.write('Resume score:', str(certificate['score']) + ' / 100')
            st.write('Experience level:', certificate['experience_level'])
            st.write('Job field:', certificate['predicted_field'])
        st.caption('Compare these details with the certificate. Verification confirms an automated resume assessment; it does not confer accreditation or guarantee employment.')
    st.link_button('Back to resume analyzer', verification_url().split('?')[0])
