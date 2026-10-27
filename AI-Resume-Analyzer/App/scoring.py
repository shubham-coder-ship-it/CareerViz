"""Versioned, evidence-based resume rubric. This is not a universal ATS score."""
import re
import unicodedata
from candidate_identity import extract_candidate_name
SCORING_VERSION = 'review-v3'
SECTION_PATTERNS = {
    'Profile': r'(?:professional |career )?(?:profile|summary|objective)|about me',
    'Skills': r'(?:(?:technical|core|professional|key) )?(?:skills|competencies|qualifications)(?: (?:and|&) (?:tools|competencies))?|skill highlights|highlights',
    'Education': r'(?:education(?: (?:and|&) (?:training|qualifications))?|academic (?:background|qualifications)|qualifications)',
    'Experience': r'(?:(?:professional|work|employment|relevant) )?(?:experience|employment|history)(?: (?:and|&) (?:practical )?training)?',
    'Internships': r'(?:internships?|practical training|training)',
    'Projects': r'(?:(?:personal|academic|selected|technical|relevant) )?projects?(?: (?:and|&) (?:research|achievements))?',
    'Certifications': r'certifications?(?: (?:and|&) badges)?|certificates|licenses',
    'Achievements': r'achievements|awards|accomplishments',
    'Interests': r'interests?|interested|hobbies',
    'Other': r'others?|extra curricular activities|extracurricular activities',
}
ACTION = re.compile(r'\b(built|developed|implemented|engineered|designed|led|managed|created|improved|reduced|increased|delivered|optimized|automated|analyzed|processed|tested|deployed|completed|organized|supported|trained|resolved|achieved)\b', re.I)
EMAIL = re.compile(r'[^\s@]+@[^\s@]+\.[^\s@]+')
PHONE = re.compile(r'(?<!\d)(?:\+?\d[\d ()-]{7,18}\d)(?!\d)')


def extract_sections(text):
    sections = {key: [] for key in SECTION_PATTERNS}
    current = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        # Normalize decorative numbering and punctuation in headings only.
        heading = re.sub(r'^\s*(?:\d+[.)]\s*|[•#*]+\s*)', '', line).strip(' :–—-').casefold()
        matched = next((key for key, pattern in SECTION_PATTERNS.items() if re.fullmatch(pattern, heading)), None)
        if matched:
            current = matched
            continue
        inline = re.match(r'^([^:]{2,45}):\s*(.+)$', line)
        inline_key=next((key for key,pattern in SECTION_PATTERNS.items() if inline and re.fullmatch(pattern,inline[1].casefold())),None)
        if inline_key:
            current=inline_key
            sections[current].append(inline[2])
        elif current:
            sections[current].append(line)
    return {key: '\n'.join(lines) for key, lines in sections.items()}


def is_generated_assessment(text):
    head = '\n'.join(text.splitlines()[:25]).casefold()
    document_title = any(re.search(r'^\s*' + title + r'\s*$', head, re.M) for title in ['resume analysis report','resume analysis certificate'])
    report_markers = sum(marker in text.casefold() for marker in ['analysis id:', 'certificate code:', 'score interpretation', 'prediction provenance', 'section breakdown', 'verify this certificate'])
    return document_title and report_markers >= 1


def validate_resume_text(text):
    if is_generated_assessment(text):
        raise ValueError('This is an analysis report or certificate, not a resume. Upload the original candidate resume; generated reports cannot be scored or used for training.')
    sections = extract_sections(text)
    evidence = sum(len(re.findall(r'\b\w+\b', sections[key])) >= 4 for key in ['Skills','Education','Experience','Projects'])
    if evidence < 2:
        raise ValueError('Insufficient resume evidence: include readable Skills and Education, Experience, or Projects sections with actual content, not just headings.')
    return sections


def evaluate_resume(text, skills=None):
    """Evidence proxies using the review PDF's eight weights; no forced calibration."""
    sections=validate_resume_text(text)
    if skills is None:
        from resume_pipeline import extract_skills
        skills=extract_skills(text)
    detected={key:len(re.findall(r'\b\w+\b',body))>=4 for key,body in sections.items()}
    if detected['Experience'] and re.search(r'\b(intern|internship|apprentice)\b',sections['Experience'],re.I):detected['Internships']=True
    def terms(body):
        return {s.casefold() for s in skills if re.search(r'(?<!\w)'+re.escape(s)+r'(?!\w)',body,re.I)}
    def actions(body):return len({v.casefold() for v in ACTION.findall(body)})
    def metrics(body):
        return len(set(re.findall(r'\b\d+(?:\.\d+)?\s*(?:%|percent\b|ms\b|seconds?\b|users?\b|orders?\b|tests?\b|clients?\b|hours?\b|records?\b|employees?\b)',body,re.I)))
    def links(body):
        urls=re.findall(r'(?:https?://|www\.)[^\s<>]+',body,re.I)
        return [u for u in urls if not re.search(r'(?:example\.(?:com|org|net)|localhost|127\.0\.0\.1|your[-_]?name|placeholder)',u,re.I)]
    def date(body):return bool(re.search(r'\b(?:19|20)\d{2}\b',body))
    projects=sections['Projects']
    work='\n'.join(sections[k] for k in ['Experience','Internships'])
    detail=bool(re.search(r'\b(?:api|application|app|dashboard|prototype|system|service|analysis|design|model|campaign|report|budget|study|workflow|device|process|portfolio)\b',projects,re.I))
    implementation=len(terms(projects))>=2 and actions(projects)>=2
    project_score=(3 if detected['Projects'] else 0)+min(4,actions(projects))+(4 if detail else 0)+(4 if implementation else 0)+min(6,metrics(projects)*2)+(4 if links(projects) else 0)
    if re.search(r'\b(?:followed a tutorial|copied from|tutorial project)\b',projects,re.I) and not metrics(projects):project_score=min(project_score,10)
    organization=bool(re.search(r'\|[^|\n]{3,70}\||\b(?:at|with|for) [A-Z][A-Za-z&.-]+(?: [A-Z][A-Za-z&.-]+){0,4}|\b(?:Ltd|Inc|LLC|Company|Corporation|University|Hospital|Studio)\b',work))
    experience_score=(2 if detected['Experience'] or detected['Internships'] else 0)+(4 if organization else 0)+(2 if date(work) else 0)+min(4,actions(work))+min(6,metrics(work)*2)+(2 if links(work) else 0)
    guided_training=bool(re.search(r'\b(?:job simulation|virtual cohort|hands.on labs?|lab exercises|structured assignments|guided milestones)\b',work,re.I))
    if guided_training and not metrics(work):experience_score=min(experience_score,8)
    declared=terms(sections['Skills'])
    contribution_lines=[line for line in re.split(r'\n+|(?<=[.!?])\s+',projects+'\n'+work) if actions(line)]
    demonstrated=declared & terms('\n'.join(contribution_lines))
    skill_score=(4 if detected['Skills'] and declared else 0)+min(3,len(declared)*.5)+min(8,len(demonstrated)*2)
    skill_score=int(skill_score)
    education=sections['Education']
    degree=bool(re.search(r'\b(?:b\.?\s?tech|m\.?\s?tech|bachelor|master|ph\.?d|diploma|bsc|msc|mba|bca|mca|degree)\b',education,re.I))
    institution=bool(re.search(r'\b[A-Za-z][A-Za-z &.-]{2,70}(?:University|College|Institute|Academy)\b|\b(?:IIT|NIT|IIIT)\s+[A-Za-z]+',education,re.I))
    grade=bool(re.search(r'\b(?:CGPA|GPA)\s*[:=-]?\s*\d(?:\.\d+)?|\b\d{2}(?:\.\d+)?\s*%',education,re.I))
    education_score=(3 if degree else 0)+(3 if institution else 0)+(2 if date(education) else 0)+(2 if grade else 0)
    profile=sections['Profile'];profile_words=len(profile.split())
    targeted=bool(re.search(r'\b(?:developer|engineer|analyst|designer|accountant|nurse|teacher|chef|manager|specialist|consultant|marketing|finance|sales|cloud|devops|student|graduate)\b',profile,re.I))
    generic=bool(re.search(r'\b(?:hard.?working|dynamic individual|seeking a challenging|highly motivated|results.?driven)\b',profile,re.I))
    summary_score=(2 if 20<=profile_words<=90 else 0)+(2 if targeted else 0)+(2 if terms(profile) else 0)+(2 if actions(profile) or metrics(profile) else 0)+(2 if profile_words>=15 and not generic else 0)
    words=re.findall(r'\b\w+\b',text)
    damaged=text.count('\ufffd')+text.count('(cid:')+sum(unicodedata.category(c) in {'Cc','Cf'} and c not in '\n\t\r' for c in text)
    lines=[v.strip().casefold() for v in text.splitlines() if len(v.split())>5]
    repetitive=len(lines)>3 and len(set(lines))/len(lines)<.8
    contacts=int(bool(extract_candidate_name(text)))+int(bool(EMAIL.search(text)))+int(bool(PHONE.search('\n'.join(text.splitlines()[:15]))))
    format_score=(3 if damaged==0 and not repetitive else 1 if damaged<=2 and not repetitive else 0)+(2 if 150<=len(words)<=1000 else 1 if 80<=len(words)<=1500 else 0)+min(2,sum(detected[k] for k in ['Skills','Education','Experience','Projects'])//2)+contacts
    cert=sections['Certifications']
    cert_title=len(cert.split())>=5
    issuer=bool(re.search(r'\b(?:issued by|issuer|coursera|udemy|google|microsoft|aws|cisco|oracle|university|institute|academy|center|centre)\b|\|',cert,re.I))
    certification_score=(2 if cert_title else 0)+(1 if issuer else 0)+(1 if date(cert) else 0)+(1 if links(cert) else 0)
    evidence_body=projects+'\n'+work
    evidence_score=(2 if links(evidence_body) else 0)+min(2,metrics(evidence_body))+(1 if (organization and date(work)) or (detail and implementation and date(projects)) else 0)
    breakdown=[
        {'criterion':'Project quality','earned':project_score,'maximum':25,'evidence':f'{actions(projects)} distinct actions, {len(terms(projects))} relevant tools/skills, {metrics(projects)} quantitative signals, {len(links(projects))} non-placeholder links. Deliverable and implementation detail are assessed.'},
        {'criterion':'Experience quality','earned':experience_score,'maximum':20,'evidence':f'Organization signal: {organization}; dates: {date(work)}; {actions(work)} actions; {metrics(work)} outcomes; {len(links(work))} supporting links. Guided-training language: {guided_training}; training-only evidence without measured outcomes is capped at 8.'},
        {'criterion':'Demonstrated skills','earned':skill_score,'maximum':15,'evidence':f'{len(declared)} recognized skills declared; {len(demonstrated)} also demonstrated in projects or experience. Listing more keywords alone cannot earn full credit.'},
        {'criterion':'Education','earned':education_score,'maximum':10,'evidence':f'Qualification: {degree}; named institution: {institution}; dates: {date(education)}; GPA/percentage: {grade}.'},
        {'criterion':'Summary and targeting','earned':summary_score,'maximum':10,'evidence':f'{profile_words} summary words; target role: {targeted}; relevant skill and contribution signals; generic wording is not rewarded.'},
        {'criterion':'Formatting and readability','earned':format_score,'maximum':10,'evidence':f'{len(words)} extracted words, {damaged} damaged characters, repeated padding: {repetitive}; {contacts}/3 header contact signals. Visual layout is not inferred from text alone.'},
        {'criterion':'Certifications','earned':certification_score,'maximum':5,'evidence':f'Title content: {cert_title}; issuer: {issuer}; date: {date(cert)}; non-placeholder link: {bool(links(cert))}.'},
        {'criterion':'Supporting evidence','earned':evidence_score,'maximum':5,'evidence':'Project/work links, quantified contributions, and traceable dates/context. Links and claims are detected, not independently verified.'},
    ]
    guidance=[
        'Describe a named project, your implementation decisions and genuine results; include a repository, demo or portfolio link where available.',
        'Describe actual work, internships or volunteering with the organization, dates, your contribution and genuine outcomes. A certification alone is not work experience.',
        'Connect listed skills to specific work or project contributions. Remove skills you cannot demonstrate and unsupported claims of expertise.',
        'Include your qualification, named institution and dates; add GPA or percentage if available and relevant to the application.',
        'Write a concise summary targeted to the role, with relevant tools and a concrete contribution rather than generic adjectives.',
        'Check contact details, PDF extraction, repeated padding and document length. Review the visual layout yourself.',
        'List relevant certifications with title, issuer, date and a real verification link. Do not invent credentials.',
        'Add genuine metrics and working project or work-sample links. Never invent numbers or confidential employer information.',
    ]
    return {'score':sum(r['earned'] for r in breakdown),'scoring_version':SCORING_VERSION,'score_breakdown':breakdown,
            'subscores':{'Content quality':{'earned':sum(r['earned'] for r in breakdown[:5])+certification_score,'maximum':85},'Format':{'earned':format_score,'maximum':10},'Supporting evidence':{'earned':evidence_score,'maximum':5}},
            'sections':detected,'section_text':sections,'strengths':[r['criterion'] for r in breakdown if r['earned']>=r['maximum']*.8],
            'improvements':[guidance[i] for i,r in enumerate(breakdown) if r['earned']<r['maximum']],
            'score_explanation':'Evidence-weighted review rubric using the supplied comparison document weights. Measures documented project/work quality, demonstrated skills and supporting evidence; not just section presence. Deterministic text signals cannot verify claims, rank applicants, or reproduce a subjective reviewer exactly. Scores are not calibrated to a target average or hiring outcomes.'}


def compute_resume_score(resume_text):
    return evaluate_resume(resume_text)['score']
