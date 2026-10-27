# AI Resume Analyzer

AI Resume Analyzer is a Python and Streamlit application that parses PDF resumes with natural language processing, analyzes their content, predicts a likely career field, and returns skill, course, and resume-writing recommendations through an interactive web interface. It also includes a feedback form and an admin dashboard with analytics over all analyzed resumes.

## Features

### User

- Upload a resume in PDF format and preview it in-browser
- Automatic extraction of name, email, contact number, degree, and skills
- Candidate experience-level detection (Fresher / Intermediate / Experienced)
- Predicted career field based on detected skills (Data Science, Web, Android, iOS, or UI/UX Development)
- Skill recommendations tailored to the predicted field
- Course and certification recommendations
- Resume score with section-by-section writing tips (objective, education, experience, skills, projects, etc.)
- Bonus resume-writing and interview-preparation video recommendations

### Feedback

- Feedback form with a 1-5 rating and comments
- Past ratings shown as a pie chart, with full comment history

### Admin

- Login-protected dashboard (see [Configuration](#configuration))
- Table view of all analyzed resumes and applicant data
- CSV export of applicant data
- Table view of all feedback submissions
- Pie-chart analytics: ratings, predicted field, experience level, resume score, and usage by IP, city, state, and country

## Technology Stack

**Application**
- [Python](https://www.python.org/)
- [Streamlit](https://streamlit.io/)

**Resume Processing**
- [spaCy](https://spacy.io/)
- [pyresparser](https://github.com/OmkarPathak/pyresparser) (with a customized parser file, see [pyresparser notes](#pyresparser-notes))
- [pdfminer3](https://pypi.org/project/pdfminer3/) / [pdfminer.six](https://github.com/pdfminer/pdfminer.six) for PDF text extraction

**Data & Analytics**
- [pandas](https://pandas.pydata.org/)
- [Plotly](https://plotly.com/)

**Database**
- [MySQL](https://www.mysql.com/)
- [PyMySQL](https://pypi.org/project/PyMySQL/)

**Utilities**
- [geocoder](https://pypi.org/project/geocoder/) and [geopy](https://pypi.org/project/geopy/) for IP-based location lookup
- [Pillow](https://pypi.org/project/Pillow/)
- [streamlit-tags](https://pypi.org/project/streamlit-tags/)
- [NLTK](https://www.nltk.org/)
- [python-dotenv](https://pypi.org/project/python-dotenv/) for loading configuration from `.env`

## Project Structure

```text
AI-Resume-Analyzer/
├── App/
│   ├── App.py              # Streamlit application entry point
│   ├── Courses.py          # Static course/video recommendation data
│   ├── requirements.txt    # Python dependencies
│   ├── Logo/                # App logo/icon assets
│   └── Uploaded_Resumes/    # Resumes uploaded at runtime are saved here
├── pyresparser/
│   └── resume_parser.py    # Customized resume parser (see notes below)
├── screenshots/             # Screenshots used in this README
├── .env.example              # Template for local environment configuration
├── .gitignore
└── README.md
```

## Requirements

- Python 3.9 (the pinned dependencies, in particular spaCy 2.3.5, target this version)
- MySQL Server, running and reachable
- pip

## How to Start

### 1. Clone the repository

```bash
git clone
cd AI-Resume-Analyzer
```

### 2. Create and activate a virtual environment

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

macOS/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

`requirements.txt` lives inside `App/`:

```bash
cd App
pip install -r requirements.txt
```

### 4. Install the spaCy language model

```bash
python -m spacy download en_core_web_sm
```

### 5. Apply the custom resume parser

The application relies on the `pyresparser` package installed from PyPI, but this repository ships a customized `pyresparser/resume_parser.py` (at the repository root) that should replace the one installed in your virtual environment:

```text
venv/Lib/site-packages/pyresparser/resume_parser.py   (Windows)
venv/lib/python3.9/site-packages/pyresparser/resume_parser.py   (macOS/Linux)
```

Copy the repository's `pyresparser/resume_parser.py` over that installed file. See [pyresparser notes](#pyresparser-notes) for why this manual step exists.

### 6. Configure MySQL and environment variables

Make sure MySQL is installed and running, then copy the environment template:

```bash
cp ../.env.example ../.env
```

Edit `.env` and set your MySQL host, user, and password. The database itself (`cv`, or whatever you name it) and its tables (`user_data`, `user_feedback`) are created automatically by the application on first run if they don't already exist — you do not need to create them manually.

### 7. Run the application

From the `App/` directory:

```bash
streamlit run App.py
```

Streamlit will print a local URL (typically `http://localhost:8501`) to open in your browser.

## Database Setup

The application automatically creates the following on startup, using the connection details from your `.env` file:

```text
cv (database)
├── user_data       # applicant info, parsed resume data, scores, recommendations
└── user_feedback    # feedback form submissions
```

## Usage

```text
Start application
      ↓
Enter your name, email, and mobile number
      ↓
Upload a PDF resume
      ↓
Resume parsing (name, email, contact, degree, skills)
      ↓
Experience-level detection and resume analysis
      ↓
Predicted field, skill and course recommendations
      ↓
Resume score and section-by-section writing tips
```

Use the sidebar to switch between the **User**, **Feedback**, **About**, and **Admin** views.

## Screenshots

**User — Main Screen**

![Main screen](screenshots/user/1-main-screen.png)

**Resume Analysis**

![Resume analysis](screenshots/user/2-analysis.jpg)

**Skill & Course Recommendations**

![Recommendations](screenshots/user/3-recom.png)

**Feedback Form**

![Feedback form](screenshots/feedback/1-form.png)

**Admin Dashboard**

![Admin dashboard](screenshots/admin/2-user-data.png)

More screenshots are available in the [`screenshots/`](screenshots) directory.

## Troubleshooting

**MySQL connection error**
Confirm MySQL is running, and that `MYSQL_HOST`, `MYSQL_USER`, and `MYSQL_PASSWORD` in `.env` are correct for your local setup.

**spaCy model not found**
Run `python -m spacy download en_core_web_sm` inside your activated virtual environment.

**`streamlit: command not found`**
Make sure your virtual environment is activated and dependencies from `App/requirements.txt` are installed.

**`GeocoderUnavailable` error**
The location lookup requires internet access; check your connection.

**Resume parsing returns no data**
Only PDF resumes are supported. Make sure you've completed the [custom parser step](#5-apply-the-custom-resume-parser) above, since the unmodified `pyresparser` package may not extract fields correctly.

## Configuration

All configuration is read from environment variables, loaded from `.env` (see `.env.example`):

| Variable          | Description                                  | Default                  |
|-------------------|-----------------------------------------------|---------------------------|
| `MYSQL_HOST`       | MySQL server host                             | `localhost`                |
| `MYSQL_USER`       | MySQL user                                    | `root`                      |
| `MYSQL_PASSWORD`   | MySQL password                                | *(empty)*                   |
| `MYSQL_DATABASE`   | Database name                                 | `cv`                         |
| `ADMIN_USER`       | Username for the Admin dashboard              | `admin`                       |
| `ADMIN_PASSWORD`   | Password for the Admin dashboard              | `YOUR_CONFIGURED_PASSWORD`        |

## Development Commands

```bash
streamlit run App.py
```

This project has no automated test suite, linter, or build step.

## Privacy / Data Handling

For every resume analyzed, the application stores the following in MySQL: the applicant's submitted name, email, and mobile number; parsed resume data (name, email, skills, degree, page count); the predicted field, experience level, and resume score; recommended skills and courses; the uploaded PDF's filename; and, for the admin analytics view, the user's IP address, approximate location (city/state/country from IP-based geolocation), and basic server/host info of the machine running the app.

This data is used only to power the admin analytics dashboard. There is no third-party tracking or analytics service in the app.

Uploaded resumes are saved locally to `App/Uploaded_Resumes/` and are excluded from version control via `.gitignore`. Avoid committing real resumes or personal data to Git, and avoid deploying this app publicly without reviewing whether this level of data collection is appropriate for your use case.

## pyresparser Notes

This repository includes a customized `pyresparser/resume_parser.py`. It is not imported directly as a Python package from this location — instead, it's designed to replace the `resume_parser.py` file inside the `pyresparser` package installed via pip (see [step 5](#5-apply-the-custom-resume-parser)). The installed `pyresparser` package supplies the rest of the package (`utils.py`, `__init__.py`, and the bundled entity-extraction model) that this file depends on.

## License

This repository does not currently include a license file. Contact the repository owner if you need clarification on usage terms.

## Version 2.0 update: setup and operation

Run these commands from the `AI-Resume-Analyzer` directory in PowerShell:

```powershell
.\venv\Scripts\python.exe -m pip install -r App\requirements.txt
.\venv\Scripts\python.exe App\scripts\hash_admin_password.py
```

Create or update `App/.env` with `ADMIN_USER` and the printed
`ADMIN_PASSWORD_HASH` value. Keep the entire hash in single quotes, including
all dollar signs. There is no default admin password. Existing `ADMIN_PASSWORD`
plaintext configuration is no longer accepted. The password generator prompts
locally and does not write the password. Restart the server after configuration.

```powershell
Set-Location App
..\venv\Scripts\python.exe -m streamlit run App.py --server.port 8501
```

The current local environment has Streamlit 1.65.0; the existing requirements
pin is retained. ReportLab >=4 is the added runtime dependency.
Resume names are extracted conservatively from header lines without NLTK corpora.
Optional resources for legacy NLP helpers can be installed once:

```powershell
..\venv\Scripts\python.exe -m nltk.downloader -d nltk_data punkt punkt_tab averaged_perceptron_tagger averaged_perceptron_tagger_eng maxent_ne_chunker maxent_ne_chunker_tab words stopwords wordnet
```

Without corpora, the existing parser falls back to text matching for skills and
the candidate form for unclear names. Downloads never occur during analysis.
`MAX_RESUME_MB` defaults to 10. `RESUME_DB_PATH` optionally overrides the SQLite
path. Location lookup is disabled unless `ENABLE_GEOLOCATION=true`; enabled
lookups have a two-second timeout. Keep personal documents and the database
outside public web roots and back them up before operational migrations.

### Storage and migration

Startup runs additive, repeatable migrations. Existing candidate rows and model
artifacts are retained. New tables: `analyses`, `certificates`, `dataset_imports`,
`dataset_files`, `admin_audit`, and `model_operation_lock`. Feedback gains
`pinned`, `published`, and `analysis_id`. Existing feedback is private by default.
No manual migration command is needed. Analysis records hold normalized profile,
text, content hash, file type, score, sections, recommendations, model provenance,
and timestamps. Certificates have a unique code and one certificate per analysis.

Private results are scoped to the current Streamlit session's random owner
identifier. Navigation preserves that session and its last saved analysis.
A new browser session has no identity recovery/login flow and cannot reopen
private historical analyses from a previous session; admins can inspect records.
Do not distribute session secrets. The public certificate page is `/?verify=<certificate-code>` and requires no login.
Certificates include its clickable link and QR code. Public verification exposes only
the certificate name, code, issue date, status, score, experience level and field,
not contact information or resume text. Possession of the unguessable code grants
access to these certificate details. Admin verification remains available.

### Analyze, download and certificate

Enter contact details, choose a readable PDF or DOCX, and click Analyze Resume.
Extracted valid contact details take precedence; validated form details fill gaps.
A changed file clears the displayed cached result. Explicit reanalysis creates a
new analysis; navigation and downloads do not rerun inference or insert another
candidate. Download Analysis PDF and Download Analysis Certificate appear with
the saved result. Certificate downloads retain the issued code. These are
non-accredited automated assessments. Scanned documents require external OCR.
DOCX pagination cannot be established from XML; the model's page-count feature
uses its existing default of one for DOCX.

### Import a ZIP dataset

1. Sign in to Admin and open Data Management → Import resume dataset ZIP.
2. Choose a ZIP. Review categories, supported files, duplicates and failures.
3. Click Confirm dataset import. Files are copied into `App/datasets/<import-id>`
   with a source archive and persisted import metadata. No model is trained.

Supported folder names are listed in `App/admin_extensions.py:CATEGORIES`.
They include the original 24 resume dataset categories. Nested wrappers such as
`data/data/ENGINEERING` are supported. Unknown categories are previewed and
skipped; rename them to an appropriate documented category before importing.
Archives are limited to 100 MB compressed, 250 MB expanded, 2000 entries, 10 MB
per document, and a maximum compression ratio of 200. Absolute paths, traversal,
symlinks, encrypted archives and unsupported document types are rejected/skipped.
SHA-256 detects duplicates within and across imports. Imported rows are identified
as dataset records rather than fabricated candidate profiles.

### Train, inspect, activate and delete models

Use Model Management to choose Random Forest, Logistic Regression, SVM or Gradient
Boosting, test fraction, seed, estimator count and regularization where relevant.
Filter candidates by an inclusive score range, experience, category and status;
select records and verify their category labels before Train Model. A minimum
of 70 excludes scores below 70. Scores are features/filter criteria, not labels.
Imported category folders supply actual supervised labels; review automatically
predicted candidate labels before including them in training.

The skill vocabulary, scaler and categorical encoder learn only from training
records. Splits are stratified and reproducible; insufficient class coverage
raises an error. Metrics include held-out accuracy, weighted precision/recall/F1,
macro-F1, balanced accuracy, confusion matrix and per-class performance.
Cross-validation is explicitly reported as not run. Tree importance and linear
coefficients use transformed feature names; kernel SVM shows an unsupported
explanation message. Importance is descriptive, not causal.

Training saves an inactive bundle and evaluation metadata. Review it and click
Activate selected model to switch inference explicitly. Existing production
models are never activated/replaced automatically by training. Algorithm metadata,
record IDs and a selected-ID dataset fingerprint are saved with each run; this
fingerprint identifies selected records, not a full content snapshot.

Deletion requires the selected scope, confirmation and admin-password verification.
The active model is protected. Inactive artifacts are moved into
`App/models/_deleted` for recovery, then unregistered; datasets are untouched.
Audit outcomes are retained. File failures are reported and require inspection;
this is not a permanent purge. Model operations are serialized across sessions
using a SQLite lock. A server crash can leave a lock: stop the server, verify that
no training/inference process is running, back up the DB, and have an operator
clear the stale `model_operation_lock` row before restarting.

Feedback pinning is private. Public feedback requires a separate explicit
moderation action. Review/redact personal information before publishing; the
public list uses Anonymous rather than the submitter's name.

### Tests and current limitations

```powershell
.\venv\Scripts\python.exe -m unittest discover -s App\tests -v
.\venv\Scripts\python.exe -m compileall -q App
```

Tests use temporary databases and model directories. PDF layout fixtures in
`App/tests/output` are synthetic test documents, never production records.
Backend tests cover extraction/validation, contact precedence, private ownership,
certificate stability, ZIP traversal/duplicate detection/import, score filtering,
four real algorithms, active-model protection, password verification, navigation,
saved-result rendering and authenticated admin rendering. Browser checks at widths 390, 768 and 1440 found no horizontal page overflow;
the compact navigation was visually inspected. Full real-device and all-admin-panel
visual regression coverage remains outstanding. SVM probability emits an upstream deprecation warning
in the installed scikit-learn version; it remains functional.

Validation run: 15 integration tests passed. Compile checks passed. PDF report and
certificate were rendered with Poppler and inspected. NLTK corpus download was
stopped after a stalled transfer; use the setup command above when network access
is reliable. Contact fallback and skill extraction remain available without corpora.


### ZIP upload responsiveness fix

Dataset selection now performs a lightweight archive/signature preview once per
uploaded content hash. It does not extract resume text while rendering the page.
Confirm dataset import launches a separate local Python worker. A small Streamlit
fragment polls persisted progress without rerunning the whole admin dashboard.
You can navigate during import, return to its status, or cancel the worker.
Completed records are retained when cancellation occurs. Parsing errors are
reported in the final per-file summary. Imports do not hold SQLite write locks
while parsing documents. The additive `dataset_jobs` table tracks job status;
queued archives are retained in `App/datasets/_jobs` for auditing.


### Name extraction and public certificate verification

Names must be supported by an explicit Name field or a plausible standalone
resume header. Address lines, known state/location names, section headings and
job titles are rejected; unclear extraction uses the submitted name. Reanalyze
previously processed resumes to correct old saved results and issue a new
certificate. Existing certificate IDs are preserved when downloaded again.

The certificate system-signature block has been replaced with a verification
link and QR code. The public verification page compares the code to its stored
record and reports missing/revoked certificates. It does not expose private
reports, emails, phone numbers or uploaded files.

Configure `PUBLIC_APP_URL` in `App/.env` to the actual deployed application URL
before sharing certificates with other people. For example, use your own HTTPS
application origin (and path prefix if deployed under one). Do not include query
parameters or a fragment. Without this setting the link uses local address
`http://127.0.0.1:8501` and works only on this computer. Hosting or a reachable
network endpoint is required for verification from other devices. Restart after
changing the setting and redownload certificates so the PDF contains that URL.
The verification page explains that issuance records an automated assessment.
