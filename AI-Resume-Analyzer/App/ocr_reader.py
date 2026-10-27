"""Private local OCR fallback; ordinary selectable PDFs retain their original text."""
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def poppler_binary():
    configured=os.getenv('PDFTOPPM_PATH')
    candidates=[configured,shutil.which('pdftoppm')]
    if os.name=='nt':
        candidates.append(str(Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'))
    for candidate in candidates:
        if candidate and Path(candidate).is_file():return str(candidate)
    raise ValueError('Scanned PDF reading needs Poppler. Set PDFTOPPM_PATH to pdftoppm, or upload the resume as PNG/JPG.')


def _recognize_image(path):
    if os.name!='nt':
        raise ValueError('Local OCR currently uses Windows text recognition. Upload a selectable-text PDF or DOCX on this server.')
    executable=shutil.which('powershell.exe')
    if not executable:raise ValueError('Windows PowerShell is unavailable for local text recognition.')
    try:
        result=subprocess.run([executable,'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',
                               str(Path(__file__).with_name('scripts')/'windows_ocr.ps1'),'-ImagePath',str(Path(path).resolve())],
                              capture_output=True,timeout=40,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if result.returncode:
            raise ValueError('Local OCR could not read this image. Check that an English Windows OCR language is installed, or upload a selectable-text PDF.')
        return json.loads(result.stdout.decode('utf-8-sig'))['text']
    except subprocess.TimeoutExpired as exc:
        raise ValueError('Local text recognition timed out. Upload a clearer or smaller image.') from exc


def recognize_image(path):
    return _recognize_image(path)


def image_text(content):
    from PIL import Image,ImageOps
    with tempfile.TemporaryDirectory(prefix='careerviz_ocr_') as directory:
        try:
            with Image.open(io.BytesIO(content)) as source:
                if source.format not in {'PNG','JPEG'} or source.width*source.height>25_000_000:
                    raise ValueError('Use a PNG or JPG image up to 25 megapixels.')
                image=ImageOps.exif_transpose(source).convert('RGB')
                image.thumbnail((2200,2200))
                path=Path(directory)/'resume.png';image.save(path)
        except (OSError,Image.DecompressionBombError) as exc:
            raise ValueError('Resume image is damaged or too large. Upload a clear PNG or JPG.') from exc
        return recognize_image(path)


def pdf_text(content):
    from pdfminer.high_level import extract_text
    native=extract_text(io.BytesIO(content))
    pages=native.split('\f')
    if pages and not pages[-1].strip():pages.pop()
    missing=[i for i,text in enumerate(pages) if len(text.strip())<40]
    if not missing:return native
    if len(pages)>8:
        raise ValueError('Scanned resumes support up to 8 pages. Upload a shorter resume or a selectable-text PDF.')
    binary=poppler_binary()
    with tempfile.TemporaryDirectory(prefix='careerviz_ocr_') as directory:
        source=Path(directory)/'resume.pdf';source.write_bytes(content)
        for index in missing:
            prefix=Path(directory)/('page_'+str(index))
            try:
                rendered=subprocess.run([binary,'-f',str(index+1),'-l',str(index+1),'-singlefile','-scale-to','2200','-png',str(source),str(prefix)],capture_output=True,timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            except subprocess.TimeoutExpired as exc:
                raise ValueError('Scanned PDF rendering timed out. Try a smaller or clearer PDF.') from exc
            if rendered.returncode or not prefix.with_suffix('.png').exists():
                raise ValueError('This scanned PDF could not be rendered. Upload its PNG/JPG image instead.')
            pages[index]=recognize_image(prefix.with_suffix('.png'))
    return '\n'.join(pages)
