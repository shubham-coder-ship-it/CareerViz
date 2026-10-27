import io
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from services import extract_document
from candidate_identity import extract_candidate_name
from scoring import extract_sections


class OCRTests(unittest.TestCase):
    def test_about_me_and_missing_name(self):
        self.assertIsNone(extract_candidate_name('STUDENT\n+91 9876543210\npaya n\nABOUT ME\nSome student profile'))
        self.assertEqual(extract_sections('ABOUT ME\nA student working on data science projects\nEDUCATION\nBachelor degree at Example University')['Profile'],'A student working on data science projects')
    def test_image_dispatch(self):
        with patch('ocr_reader.image_text',return_value='Readable resume text with education and skills in a clear document.') as read:
            self.assertIn('Readable',extract_document(b'png input','resume.png'))
            read.assert_called_once()
    def test_native_pdf_does_not_require_ocr(self):
        from reportlab.pdfgen import canvas
        data=io.BytesIO();c=canvas.Canvas(data);c.drawString(40,700,'Readable resume with clear education and several demonstrated programming skills.');c.save()
        with patch('ocr_reader.recognize_image',side_effect=AssertionError('Unnecessary OCR')):
            self.assertIn('Readable',extract_document(data.getvalue(),'resume.pdf'))
    @unittest.skipUnless(os.name=='nt','Windows local OCR')
    def test_attached_real_files(self):
        from resume_pipeline import parse_resume
        pdf=Path(os.getenv('CAREERVIZ_OCR_PDF_FIXTURE',''))
        image=Path(os.getenv('CAREERVIZ_OCR_IMAGE_FIXTURE',''))
        if not pdf.is_file() or not image.is_file():self.skipTest('Optional private OCR fixtures are not configured')
        expected=os.getenv('CAREERVIZ_OCR_EXPECTED_NAME','Test Candidate')
        for source,manual in [(pdf,{'name':expected}),(image,{})]:
            text,candidate,result=parse_resume(source.read_bytes(),source.name,manual)
            self.assertEqual(candidate['name'].casefold(),expected.casefold())
            self.assertNotEqual(candidate['email'],'Unavailable')
            self.assertNotEqual(candidate['mobile_number'],'Unavailable')
            self.assertTrue(result['sections']['Education'])
            self.assertTrue(result['sections']['Skills'])


if __name__=='__main__':unittest.main()
