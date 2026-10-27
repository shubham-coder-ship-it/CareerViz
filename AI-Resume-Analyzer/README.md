# CareerViz

A simple resume analyzer using the supplied data.zip as a fixed local reference dataset. **No model training, Excel training upload, scaling, activation or model-management workflow remains in the app or API.** Original navigation, layout and CSS are retained.

## Start

From the outer workspace run `./Start-CareerViz.ps1`, or:

```powershell
cd .\AI-Resume-Analyzer\App
..\venv\Scripts\python.exe -m streamlit run App.py
```

Open http://127.0.0.1:8501. The optional local JSON API runs from App with `..\venv\Scripts\python.exe api.py --port 8502`.

## User

Upload an original PDF, DOCX, PNG or JPG resume, fill any missing contact details, and click Analyze Resume. The app extracts readable text, contacts, education and skills, uses a consistent review-v3 evidence-weighted score, compares skills against the reference categories, and explains improvements. A target job description adds a separate skill-coverage comparison. Reports and verifiable certificates use saved results. Generated reports cannot be re-uploaded as resumes.

## Admin

Sign in using your configured credentials. Admin shows reference records and category/status charts, saved user analyses and score filters, Pin and moderate feedback, and Verify certificate. There are no training controls. Existing database records, certificates and saved artifacts have not been deleted.

## Reference dataset

The supplied archive contains 2,484 PDFs in 24 category folders: 2,483 are readable and one is unreadable. The local index records only filenames, category, extracted skills, processing status and content hashes. It does not store names, contact details or full resume text. Duplicate hashes within a category are excluded from profiles. Processing reads at most 15 pages per PDF; parsing errors are counted and shown.

Career matching uses explicit skill-frequency similarity across categories. It does not fit or load a machine-learning classifier. Category folder labels are accepted as supplied and may contain errors. Weak or tied matches abstain; existing explicit domain rules provide a labeled fallback. Similarity is not a probability, ATS approval or employment guarantee.

The index is stored privately in `App/reference_data/index.json`. To rebuild after changing the archive (developer maintenance only):

```powershell
..\venv\Scripts\python.exe scripts/build_reference.py C:\path\to\data.zip
```

This prepares reference data, not a trainable model. Original PDFs remain in the supplied archive and are not published.

## Resume format examples

The public library uses original fictional information, not reference PDFs or user resumes. It includes a complete editable blank text format, writing checklist, professionally structured PDF examples, score filters, role/industry/experience filters, previews and downloads. Complete formats include contact links, summary, skills, education, experience or projects, certifications and achievements. Omit irrelevant sections in your actual resume. The same rubric calculates every displayed score; the default filter shows complete high-score examples, while lower ranges illustrate weak drafts. Never copy fictional accomplishments as your own.

## API

Health, resume analysis, private owner-token analysis retrieval, fictional example downloads and public certificate verification remain. Former training/dataset/model endpoints return HTTP 410 and cannot start jobs or activate models. New analyses ignore all previously saved model artifacts.

## Verification

```powershell
..\venv\Scripts\python.exe -m unittest discover -s tests -p test_reference_app.py -v
```

Tests cover complete reference-file accounting, dataset privacy, category matching and abstention, all generated PDF score parity, complete resume sections, saved analysis/certificates, and the actual User/About/Admin interfaces. Retired training code and obsolete training tests are excluded from this source distribution.

The content score is not a universal ATS rating. Configure PUBLIC_APP_URL for certificate links usable on other devices. Scanned PDFs use local Windows OCR automatically; PNG/JPG resumes are also supported. Local OCR needs Windows OCR language support. Scanned PDFs need Poppler (set PDFTOPPM_PATH if it is not discoverable); on this computer the bundled Poppler is detected automatically. Up to eight scanned pages are supported. Check extracted text and use manual contact fallback when a crop or OCR error removes information. Keep `.env`, private datasets, database files and backups private.

## Current scoring: review-v3

The supplied score-comparison PDF provides the eight category weights: projects 25, experience 20, skills 15, education 10, summary/targeting 10, formatting 10, certifications 5 and supporting evidence 5. Deterministic text signals reward implementation detail, contextual skill use, genuine quantitative signals and non-placeholder links. Generic keyword noise is excluded. Guided training without measured outcomes is capped separately from work evidence. Named education, dates and optional grade information affect education credit. Links and statements are detected, not independently verified; visual layout and applicant competitiveness cannot be fully assessed from extracted text.

A subjective review score of 57 cannot be reproduced exactly from the PDF alone. Scores are not hard-coded or forced to mean 55/standard deviation 15 because no human-labeled outcome dataset was supplied. Existing saved analyses and certificates retain their original scores and versions; reanalyze the original resume for review-v3. New reports, certificates and examples share the same scoring function.

## Appearance and admin analytics

The reference-video inspired presentation uses pearl, lavender, sage and plum; the resume processing, review-v3 rubric, OCR, reference matching and database schema are unchanged. Admin now has authenticated, read-only analytics with 7/30/90-day, all-time and custom date ranges in Asia/Kolkata, career/score/rubric filters, daily activity, career distribution, score distribution, experience mix, feedback summaries and filtered CSV exports. CSV output omits session tokens and escapes spreadsheet formula prefixes. Feedback summaries use the date range; certificate totals are date-filtered and linked to the selected analyses. Mixed scoring versions are labeled; filter by one rubric before comparing scores.

Analysis sessions count distinct saved submission-session tokens. They are not unique people, active online visitors, page views, bounce rates or browsing duration; the existing database does not collect those events. No new tracking or backend schema changes were introduced. Reference data, moderation and certificate verification remain available below the analytics dashboard.
