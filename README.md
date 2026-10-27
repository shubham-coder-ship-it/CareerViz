# CareerViz

A Streamlit resume analyzer with evidence-based scoring, career matching, local OCR, fictional resume examples, verifiable analysis certificates, and an authenticated admin analytics dashboard.

## Features

- PDF and DOCX parsing; Windows local OCR for scanned PDFs and PNG/JPG resumes.
- A versioned, transparent scoring rubric with strengths and improvement suggestions.
- Career matching against an optional local reference dataset, with explicit term-rule fallback.
- Fictional resume examples, score filters, editable blank format and PDF downloads.
- Saved reports and certificate verification.
- Admin-only date, career, score and rubric filters; activity charts, feedback moderation and CSV exports.

No model training or activation is required. Resume scores are document-evidence assessments, not ATS approval, verified qualifications or employment guarantees. Usage charts count saved analyses and submission sessions, not page views or unique people.

## Quick start

Python 3.11 or newer is recommended. The existing development environment uses Python 3.14 and Streamlit 1.65.

```powershell
git clone https://github.com/shubham-coder-ship-it/CareerViz.git
cd CareerViz
python -m venv AI-Resume-Analyzer/venv
.\AI-Resume-Analyzer\venv\Scripts\python.exe -m pip install -r AI-Resume-Analyzer/App/requirements.txt
Copy-Item AI-Resume-Analyzer/App/.env.example AI-Resume-Analyzer/App/.env
```

To configure admin access, run the password-hash helper and paste its printed `ADMIN_PASSWORD_HASH` line into `AI-Resume-Analyzer/App/.env`. Choose your own password; no admin password is shipped in this repository.

```powershell
.\AI-Resume-Analyzer\venv\Scripts\python.exe AI-Resume-Analyzer/App/scripts/hash_admin_password.py
.\Start-CareerViz.ps1
```

Open [CareerViz locally](http://127.0.0.1:8501/). The SQLite database is created automatically.

On Linux/macOS, create a virtual environment, install the same requirements, change into `AI-Resume-Analyzer/App`, then run `python -m streamlit run App.py`. Selectable-text PDF/DOCX parsing works there; the bundled local OCR helper currently requires Windows and an installed OCR language. Scanned PDFs also require Poppler (`PDFTOPPM_PATH` can specify its executable).

## Reference dataset

Personal resumes and the reference ZIP/index are intentionally excluded from GitHub. You can use text-based analysis and term-rule career fallback without them. To enable reference matching, provide a local ZIP of PDFs organized into career-category folders and run, from `AI-Resume-Analyzer/App`:

```powershell
..\venv\Scripts\python.exe scripts/build_reference.py C:\path\to\data.zip
```

Use data you are authorized to process. The generated private index remains ignored by Git. Do not commit real users' resumes, databases, password hashes or generated reports.

## Checks

From `AI-Resume-Analyzer/App`, with the environment activated:

```text
python -m unittest discover -s tests -p "test_*.py" -v
```

Reference-dataset integration tests skip when the optional local index is absent. Real OCR fixture tests are optional: set `CAREERVIZ_OCR_PDF_FIXTURE`, `CAREERVIZ_OCR_IMAGE_FIXTURE`, and `CAREERVIZ_OCR_EXPECTED_NAME` to private files and their expected name on a Windows development machine. No personal test fixtures are published.

[Detailed implementation and API guide](AI-Resume-Analyzer/README.md). Historical project context and third-party parser references are retained in [README history](AI-Resume-Analyzer/README_HISTORY.md). Third-party dependencies retain their respective licenses.
