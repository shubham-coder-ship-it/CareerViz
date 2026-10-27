"""Original fictional examples, evaluated by the production content rubric."""
from functools import lru_cache
from io import BytesIO
from xml.sax.saxutils import escape

from scoring import evaluate_resume, SCORING_VERSION

PROFILES = [
    ('Software developer','Technology','Python, JavaScript, SQL, Git, Docker, Linux, testing, REST APIs', 'web applications and backend services'),
    ('Mechanical engineer','Engineering','AutoCAD, SolidWorks, thermodynamics, fabrication, HVAC, machining', 'mechanical design and equipment testing'),
    ('Financial analyst','Finance','financial analysis, budgeting, financial reporting, Excel, investment analysis, portfolio management', 'budget forecasts and financial reporting'),
]


def example_text(role, skills, focus, tier, level):
    if tier >= 3:
        work = ''
        if level == 'Intermediate':
            work = f'Experience\n{role} Intern | Fictional Studio | Jan 2024 - Jun 2024\nSupported team delivery, analyzed requirements and tested 20 cases. Documented decisions and resolved issues during weekly reviews.\n'
        elif level == 'Experienced':
            work = f'Experience\n{role} | Fictional Studio | Jan 2020 - Dec 2025\nLed delivery of {focus}. Improved turnaround by 25 percent and supported 40 users. Managed reviews, coordinated stakeholders and documented quality checks.\n'
        return (f'Alex Morgan\n{role} | Example City\nalex.morgan@example.com | +1 202 555 0147\nhttps://example.com/portfolio | https://example.com/profile\n'
                f'Profile\n{role} focused on {focus}. Brings structured problem solving, careful documentation and practical project experience. Works with stakeholders to clarify requirements, deliver dependable results and explain technical decisions clearly. Seeks a role aligned with these skills and demonstrated contributions.\n'
                f'Skills\n{skills}\nCollaboration, written communication, requirements analysis, problem solving and quality checks.\n'
                f'Education\nBachelor degree | Example University | 2020 - 2024\nRelevant coursework: foundations and applied methods for {focus}.\n'
                +work+
                f'Projects\nApplied {role} project | Jan 2024 - Apr 2024 | https://example.com/project\nBuilt and developed a practical solution for {focus}. Designed the workflow, implemented quality checks and automated 20 tests. Reduced completion time by 25 percent in the fictional evaluation.\n'
                'Process improvement project | Aug 2023 - Dec 2023\nAnalyzed 500 records, created a documented review process and delivered clear results for 40 users. Tested assumptions, resolved reported issues and optimized the final workflow.\n'
                f'Certifications\nExample applied {role.lower()} course | Fictional Learning Center | 2024\nAdd a real issuer, completion date and verification link for your own certificates.\n'
                'Achievements\nOrganized a 5-person project team and completed the planned demonstration. Recognized for clear documentation in a fictional university showcase.\n'
                'Illustrative fictional resume. All names, organizations, dates and results are invented. Original CareerViz content, free to adapt. Replace every claim with your own verified information. No scoring outcome is guaranteed.\n')
    head = 'Alex Morgan\n'
    if tier > 0:
        head += 'alex.morgan@example.com | +1 202 555 0147\n'
    if tier >= 2:
        head += f'Profile\n{role} focused on {focus}. Committed to clear communication, dependable delivery, collaboration and continuous improvement.\n'
    head += 'Skills\n' + (skills if tier > 0 else ', '.join(skills.split(',')[:2]) + ', basic team communication') + '\n'
    if tier >= 2:
        head += 'Collaboration, problem solving, written communication and structured technical documentation for cross functional teams.\n'
    head += 'Education\n' + ('Bachelor degree, Example University, 2024\n' if tier > 0 else 'Studied at Example learning center\n')
    if tier >= 1:
        section = 'Experience' if level != 'Fresher' else 'Projects'
        head += f'{section}\n'
        if level == 'Intermediate':
            head += 'Internship at Fictional Studio, 2024\n'
        elif level == 'Experienced':
            head += f'{role}, Fictional Studio, 2020–2025\n'
        head += f'Built a project for {focus}. Developed documentation and tested the final output with a team.\n'
        if tier >= 2:
            head += f'Implemented a repeatable workflow for {focus}. Analyzed requirements, designed practical solutions and delivered clear documentation. Supported team reviews and resolved reported issues using structured investigation.\n'
        if tier >= 3:
            head += 'Automated 20 tests and reduced turnaround by 25 percent. Improved workflows for 40 users and processed 500 records. Managed reviews, deployed changes and optimized quality checks.\nCertifications\nCompleted an example professional development course with a practical assessment.\n'
    return head + '\nIllustrative fictional resume. Original CareerViz content, free to adapt. No scoring outcome is guaranteed.\n'


@lru_cache(maxsize=1)
def catalog():
    examples = []
    for role, industry, skills, focus in PROFILES:
        for level in ['Fresher','Intermediate','Experienced']:
            for tier in [0, .5, 1, 2, 3]:
                text = example_text(role, skills, focus, tier, level)
                quality = evaluate_resume(text)
                for format_name in ['Single-column PDF', 'Compact PDF']:
                    examples.append(dict(id=f'{len(examples):03}', role=role, industry=industry, level=level,
                                         format=format_name, text=text, **quality))
    return examples


@lru_cache(maxsize=64)
def example_pdf(identifier):
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    example = next(e for e in catalog() if e['id'] == identifier)
    output = BytesIO()
    styles = getSampleStyleSheet()
    if example['format'] == 'Compact PDF':
        styles['BodyText'].fontSize = 9
        styles['BodyText'].leading = 11
    from reportlab.lib import colors
    styles['Heading2'].fontSize = 11
    styles['Heading2'].leading = 13
    styles['Heading2'].textColor = colors.HexColor('#213547')
    styles['BodyText'].fontSize = 9 if example['format']=='Compact PDF' else 10
    styles['BodyText'].leading = 12
    headings = {'Profile','Skills','Education','Experience','Projects','Certifications','Achievements'}
    story = []
    for index,line in enumerate(example['text'].splitlines()):
        style = 'Title' if index == 0 else 'Heading2' if line in headings else 'BodyText'
        story.extend([Paragraph(escape(line), styles[style]), Spacer(1, 4 if line in headings else 3)])
    SimpleDocTemplate(output, title='CareerViz fictional resume example').build(story)
    return output.getvalue()


def render_examples():
    import streamlit as st
    st.title('Resume format examples')
    st.write('Explore fictional resumes evaluated with the same review-v3 evidence-weighted rubric as your own upload.')
    st.caption('Original CareerViz examples, free to reuse. Names, organizations and contacts are fictional. Scores illustrate this rubric and do not guarantee ATS or hiring outcomes.')
    bands = {'0–40':(0,40), '41–60':(41,60), '61–80':(61,80), '81–100':(81,100)}
    band = st.selectbox('Target score range', list(bands), index=2)
    st.write('Start with a complete format below. Lower-score filters show drafts with missing information for comparison.')
    template = """YOUR FULL NAME
Target job title | City, Country
Email | Phone | Portfolio / LinkedIn / GitHub (relevant links only)

PROFILE
Two to four lines describing your relevant experience, strengths and target role.

SKILLS
Relevant technical skills and tools. Add only skills you can demonstrate.

EDUCATION
Degree / qualification | Institution | Start - completion date
Relevant coursework or academic results, if useful.

EXPERIENCE / INTERNSHIPS
Job title | Organization | Start - end date
- What you did, how you did it, and the genuine result.
- Add measured impact when available; never invent numbers.
For a fresher without employment, emphasize projects instead.

PROJECTS
Project title | Dates | Link if available
- Problem, your contribution, tools used and demonstrated outcome.

CERTIFICATIONS
Certificate title | Issuer | Date | Verification link
Include only real, relevant certifications. Omit this section if not applicable.

ACHIEVEMENTS
Relevant awards or verifiable accomplishments, if applicable.

CHECK BEFORE SENDING
Use a clear single-column layout and readable font. Keep dates consistent.
Proofread, check links, export selectable-text PDF and tailor skills to the job.
Do not add sensitive identity numbers, unnecessary personal details or false claims.
"""
    with st.expander('Complete resume structure and writing checklist', expanded=True):
        st.text(template)
        st.download_button('Download editable blank format', template, file_name='CareerViz_resume_format.txt', mime='text/plain')
    examples = catalog()
    with st.container(horizontal=True):
        role = st.selectbox('Job role', ['All']+sorted({e['role'] for e in examples}))
        level = st.selectbox('Experience level', ['All','Fresher','Intermediate','Experienced'])
        industry = st.selectbox('Industry', ['All']+sorted({e['industry'] for e in examples}))
        format_name = st.selectbox('Resume format', ['All','Single-column PDF','Compact PDF'])
    lo, hi = bands[band]
    matches = [e for e in examples if lo <= e['score'] <= hi and (role=='All' or e['role']==role)
               and (level=='All' or e['level']==level) and (industry=='All' or e['industry']==industry)
               and (format_name=='All' or e['format']==format_name)]
    st.write(f'{len(matches)} matching examples')
    if not matches:
        st.info('No examples match these filters. Broaden the role, experience, industry or score range.')
    for e in matches:
        with st.expander(f"{e['role']} · {e['level']} · {e['score']}/100 · {e['industry']}"):
            st.text(e['text'])
            if st.checkbox('Preview PDF', key='preview_example_'+e['id']):
                import base64
                st.iframe('data:application/pdf;base64,'+base64.b64encode(example_pdf(e['id'])).decode(),height=500)
            st.dataframe(e['score_breakdown'], hide_index=True)
            st.write('Performs well:', ', '.join(e['strengths']) or 'Limited evidence in this draft.')
            for suggestion in e['improvements']:
                st.write('• '+suggestion)
            st.caption('Keywords are assessed as resume evidence. Compare your actual target job description for role-specific missing skills. Never copy fictional achievements as your own.')
            st.download_button('Download sample PDF', example_pdf(e['id']), file_name=f"CareerViz_example_{e['id']}.pdf", mime='application/pdf', key='example_'+e['id'])
