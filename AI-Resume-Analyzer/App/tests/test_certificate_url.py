import io
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from certificate_verification import verification_url


class CertificateURLTests(unittest.TestCase):
    def test_live_default_and_blank_setting(self):
        code='RA-2026-'+'A'*32
        for value in ['', '   ']:
            with patch.dict(os.environ,{'PUBLIC_APP_URL':value}):
                self.assertEqual(verification_url(code),'https://careerviz7217.streamlit.app/?verify='+code)
    def test_explicit_override_and_validation(self):
        with patch.dict(os.environ,{'PUBLIC_APP_URL':'https://another.example/app/'}):
            self.assertEqual(verification_url('test'),'https://another.example/app/?verify=test')
        with patch.dict(os.environ,{'PUBLIC_APP_URL':'javascript:alert(1)'}):
            with self.assertRaises(ValueError):verification_url()
    def test_certificate_pdf_contains_live_verification_link(self):
        from reports import build_pdf
        from pdfminer.high_level import extract_text
        result={'candidate':{'name':'Fictional Candidate'},'analysis_id':'sample','analyzed_at':'2026-10-27',
                'score':50,'scoring_version':'review-v3','experience_level':'Fresher','predicted_field':'ENGINEERING'}
        cert={'code':'RA-2026-'+'A'*32,'issued_at':'2026-10-27'}
        with patch.dict(os.environ,{'PUBLIC_APP_URL':''}):
            pdf=build_pdf(result,cert)
        self.assertIn('https://careerviz7217.streamlit.app/',extract_text(io.BytesIO(pdf)))
        self.assertIn(b'https://careerviz7217.streamlit.app/',pdf)


if __name__=='__main__':unittest.main()
