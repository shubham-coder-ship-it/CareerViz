"""Reports generated exclusively from an authorized saved analysis."""
import io
from html import escape
from services import load_analysis, issue_certificate


def build_pdf(result, certificate=None):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
    stream = io.BytesIO()
    styles = getSampleStyleSheet()
    styles['Title'].textColor = colors.HexColor('#213547')
    styles['BodyText'].leading = 15
    story = []
    def text(value, style='BodyText'):
        story.append(Paragraph(escape(str(value)), styles[style]))
        story.append(Spacer(1, 9))
    def section(title, values):
        text(title, 'Heading2')
        if isinstance(values, (list, tuple)):
            if title in {'Current skills','Recommended skills'}:
                text(', '.join(str(v) for v in values) or 'No additional information available.')
            else:
                for value in values:
                    text('• ' + str(value))
        else:
            text(values or 'Unavailable')
    text('CareerViz', 'Title')
    text('Resume Analysis Certificate' if certificate else 'Resume Analysis Report', 'Heading1')
    story.append(HRFlowable(width='100%', color=colors.HexColor('#e57836')))
    story.append(Spacer(1, 20))
    candidate = result['candidate']
    text(candidate['name'], 'Heading1')
    text('Analysis ID: ' + result['analysis_id'])
    text('Analysis date: ' + result['analyzed_at'])
    if certificate:
        text('Certificate code: ' + certificate['code'])
        text('Issued: ' + certificate['issued_at'])
    else:
        text('Email: ' + candidate.get('email', 'Unavailable'))
        text('Mobile: ' + candidate.get('mobile_number', 'Unavailable'))
        text('Source: ' + result['filename'])
    text('Resume content score: ' + str(result['score']) + ' / 100', 'Heading2')
    text('Scoring rubric: ' + result.get('scoring_version','legacy section-completeness rubric'))
    text('Experience level: ' + result['experience_level'])
    text('Predicted job field: ' + result['predicted_field'])
    if certificate:
        from certificate_verification import verification_url
        link = verification_url(certificate['code'])
        story.append(Spacer(1, 30))
        text('Verify this certificate', 'Heading2')
        story.append(Paragraph('<link href="' + escape(link, quote=True) + '" color="#245b91"><u>Open the certificate verification page</u></link>', styles['BodyText']))
        story.append(Spacer(1, 12))
        text(link)
        text('Scan the QR code or open the link to compare this certificate with its stored record.')
        from reportlab.graphics.barcode.qr import QrCodeWidget
        from reportlab.graphics.shapes import Drawing
        qr = QrCodeWidget(link)
        bounds = qr.getBounds()
        drawing = Drawing(100, 100, transform=[100/(bounds[2]-bounds[0]), 0, 0, 100/(bounds[3]-bounds[1]), 0, 0])
        drawing.add(qr)
        story.append(drawing)
    else:
        section('Score interpretation', result.get('score_explanation', 'Legacy section-completeness score. Reanalyze the original resume using the current evidence rubric.'))
        if result.get('score_breakdown'):
            section('Scoring rubric: ' + result.get('scoring_version','legacy'), [f"{r['criterion']}: {r['earned']} / {r['maximum']} — {r['evidence']}" for r in result['score_breakdown']])
        section('Education and qualifications', candidate.get('degree'))
        section('Current skills', result['skills'])
        section('Recommended skills', result['recommended_skills'])
        section('Strengths / detected sections', result['strengths'])
        section('Weaknesses and actionable improvements', result['improvements'])
        section('Section breakdown', [key + ': ' + ('Detected' if value else 'Missing') for key, value in result['sections'].items()])
        if result.get('section_text'):
            for heading,key in [('Education details','Education'),('Experience details','Experience'),('Internship details','Internships'),('Project details','Projects')]:
                if result['section_text'].get(key):section(heading,result['section_text'][key])
        else:
            section('Extracted resume content (education, experience and projects)', result.get('resume_text', 'Unavailable').splitlines())
        if result.get('job_match'):
            section('Job-description keyword comparison',str(result['job_match']))
        section('Prediction provenance', str(result.get('model', {})))
    if not certificate:
        text('This automated assessment does not guarantee employment. Review all results and recommendations before use.')
    def footer(canvas, doc):
        canvas.saveState()
        if certificate:
            canvas.setStrokeColor(colors.HexColor('#213547'))
            canvas.setLineWidth(1)
            canvas.rect(25, 45, A4[0]-50, A4[1]-70)
        canvas.setStrokeColor(colors.HexColor('#d7dde2'))
        canvas.line(40, 38, A4[0]-40, 38)
        canvas.setFont('Helvetica', 8)
        canvas.drawString(40, 25, 'CareerViz | Certificate verification' if certificate else 'CareerViz | Automated assessment')
        canvas.drawRightString(A4[0]-40, 25, 'Page ' + str(doc.page))
        canvas.restoreState()
    SimpleDocTemplate(stream, pagesize=A4, rightMargin=45, leftMargin=45, topMargin=40, bottomMargin=52).build(story, onFirstPage=footer, onLaterPages=footer)
    return stream.getvalue()


def cached_pdf(result, certificate=None):
    """Session-scoped generated bytes; slider/navigation reruns do not rebuild PDFs."""
    import streamlit as st
    import hashlib, json
    from certificate_verification import verification_url
    key=hashlib.sha256((json.dumps(result,sort_keys=True)+json.dumps(certificate,sort_keys=True)+verification_url()).encode()).hexdigest()
    cache=st.session_state.setdefault('_analysis_pdf_cache',{})
    if key not in cache:
        if len(cache)>=4:cache.pop(next(iter(cache)))
        cache[key]=build_pdf(result,certificate)
    return cache[key]


def render_saved_analysis(conn, owner, analysis_id):
    import streamlit as st
    result = load_analysis(conn, owner, analysis_id)
    if result.get('resume_text'):
        try:
            from scoring import validate_resume_text
            validate_resume_text(result['resume_text'])
        except ValueError:
            st.error('This saved record does not contain a valid original resume. Upload the original resume and analyze it again; a generated report cannot be scored.')
            return
    from scoring import SCORING_VERSION
    if result.get('scoring_version') != SCORING_VERSION:
        st.warning('This saved result uses an earlier scoring version. Reanalyze the original resume for the current evidence-weighted review. Older saved scores have not been changed.')
    with st.container(horizontal=True):
        st.header('Resume analysis')
        st.download_button('Download Analysis PDF', cached_pdf(result), file_name='resume_analysis_' + analysis_id + '.pdf', mime='application/pdf', key='report_' + analysis_id)
    st.caption('Analysis ' + analysis_id + ' · ' + result['analyzed_at'])
    candidate = result['candidate']
    st.subheader(candidate['name'])
    st.write('Email:', candidate['email'], ' · Mobile:', candidate['mobile_number'])
    with st.container(horizontal=True):
        st.metric('Resume content score', str(result['score']) + ' / 100')
        st.metric('Experience', result['experience_level'])
        st.metric('Job field', result['predicted_field'])
    st.progress(result['score'] / 100)
    degrees=candidate.get('degree') or []
    st.write('Education:', ', '.join(degrees) if isinstance(degrees,list) else degrees or 'Unavailable')
    if result.get('specialization'):st.write('Role focus:',result['specialization'])
    st.caption(result.get('score_explanation','Legacy section-completeness estimate.'))
    if result.get('score_breakdown'):
        with st.expander('How this score was calculated',expanded=True):
            st.dataframe(result['score_breakdown'],hide_index=True)
    if result.get('subscores'):
        st.write('Score components:', {key: str(value['earned'])+' / '+str(value['maximum']) for key,value in result['subscores'].items()})
    model=result.get('model',{})
    if model.get('recommendations'):
        st.subheader('Model career recommendations')
        st.dataframe(model['recommendations'], hide_index=True)
        st.caption('Probabilities compare the categories present in the training dataset. They are not employment probabilities.')
    if model.get('used_model'):
        st.caption(f"Category source: trained model {model.get('model_version')} · model probability {model.get('confidence',0):.0%}. This is not a resume-quality score.")
    elif result.get('dataset_match'):
        st.caption('Career source: your supplied reference dataset. '+result['dataset_match']['note'])
        st.dataframe(result['dataset_match']['matches'],hide_index=True)
    elif result.get('category_evidence'):
        st.caption('Category source: explicit resume-term rules · ' + ', '.join(result['category_evidence']['terms']))
    if model.get('reason'):st.caption(model['reason'])
    if result.get('job_match'):
        match=result['job_match']
        with st.container(border=True):
            st.subheader('Job-description skill coverage')
            if match['coverage_percent'] is not None:st.metric('Recognized keyword coverage',str(match['coverage_percent'])+'%')
            else:st.info('No recognized skill keywords found in the job description.')
            st.caption(match['note'])
            st.write('Matched:', ', '.join(match['matched']) or 'None detected')
            st.write('Not detected:', ', '.join(match['missing']) or 'None')
    for title, values in [('Current skills', result['skills']), ('Recommended skills', result['recommended_skills']), ('Strengths', result['strengths']), ('Improvement areas', result['improvements'])]:
        with st.container(border=True):
            st.subheader(title)
            st.write(', '.join(values) if values else 'No additional information available.')
    from theme import chart_section_completeness, chart_gauge, chart_bar_counts
    import pandas as pd
    st.plotly_chart(chart_gauge(result['score'], 'Resume Score'), key='saved_gauge_' + analysis_id)
    if result['skills']:
        import re
        counts = pd.Series({skill: len(re.findall(r'(?<!\w)'+re.escape(skill)+r'(?!\w)', result.get('resume_text',''), re.I)) for skill in result['skills']})
        st.plotly_chart(chart_bar_counts(counts, 'Current skills (mentions)', orientation='h', x_title='Mentions', top_n=15), key='saved_skills_' + analysis_id)
    st.plotly_chart(chart_section_completeness(result['sections']), key='saved_sections_' + analysis_id)
    with st.expander('Extracted education, experience and project details'):
        st.text(result.get('resume_text', 'Unavailable'))
    from Courses import ds_course, web_course, android_course, ios_course, uiux_course, resume_videos, interview_videos
    catalogs = {'Data Science': ds_course, 'Web Development': web_course, 'Android Development': android_course, 'IOS Development': ios_course, 'UI-UX Development': uiux_course}
    catalog = catalogs.get(result.get('specialization') or result['predicted_field'], [])
    if catalog:
        with st.expander('Recommended courses'):
            count = st.slider('Number of courses', 1, min(10, len(catalog)), min(5, len(catalog)))
            for title, link in catalog[:count]:
                st.link_button(title, link)
    with st.expander('Resume writing and interview tips'):
        st.video(resume_videos[0])
        st.video(interview_videos[0])
    if result.get('resume_path', '').lower().endswith('.pdf'):
        from pathlib import Path
        path = Path(result['resume_path']).resolve()
        root = Path(__file__).resolve().parent / 'Uploaded_Resumes'
        if path.is_relative_to(root) and path.is_file() and st.checkbox('Show original PDF preview',key='preview_'+analysis_id):
            with st.expander('Original PDF preview'):
                import base64
                st.iframe('data:application/pdf;base64,' + base64.b64encode(path.read_bytes()).decode(), height=550)
    if candidate['name'] == 'Unavailable':
        st.info('Enter a valid candidate name and reanalyze to issue a named certificate.')
        return
    cert = issue_certificate(conn, owner, analysis_id)
    st.download_button('Download Analysis Certificate', cached_pdf(result, cert), file_name='certificate_' + cert['code'] + '.pdf', mime='application/pdf', key='certificate_' + analysis_id)
    from certificate_verification import verification_url
    st.link_button('Verify this certificate',verification_url(cert['code']))
    st.caption('Certificate '+cert['code']+' · Share this verification link only with intended recipients.')
    from urllib.parse import urlsplit
    if urlsplit(verification_url()).hostname in {'localhost','127.0.0.1','::1'}:
        st.info('Certificate verification currently uses localhost. Configure PUBLIC_APP_URL before sharing it outside this computer.')
