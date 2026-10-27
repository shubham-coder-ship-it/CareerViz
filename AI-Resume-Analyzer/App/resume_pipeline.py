"""One analysis flow for PDF/DOCX, UI, reports and dataset imports."""
import re
from functools import lru_cache
from pathlib import Path
from scoring import evaluate_resume, validate_resume_text
from services import extract_document, normalize_candidate
from category_rules import RULES, SPECIALIZATIONS, contains, infer_category


@lru_cache(maxsize=1)
def skill_vocabulary():
    import csv
    path=Path(__file__).resolve().parent/'pyresparser'/'skills.csv'
    with path.open(encoding='utf-8-sig') as source:
        words=next(csv.reader(source))
    generic={'ms','system','process','technical','technical skills','engineering','design','reports','documentation','training','supervisor','policies','logging','legal','construction','english','compliance','inventory','assembly','repairs','gmail','certification','certifications','interactive','health','reporting','watchdog','workflows','finance','keyboard','international','visual','controls','engagement','regulatory','analysis','analytical','interactive','green','requests','updates','responses'}
    all_terms=set(t.casefold().strip() for t in words if t.strip())
    all_terms.update(t for values in RULES.values() for t in values)
    all_terms.update(t for values in SPECIALIZATIONS.values() for t in values)
    all_terms.update(['fastapi','flask','git','github actions','bash','docker compose','rabbitmq','supabase','sqlite','rag','pgvector','rest apis','s3','ec2','iam','vpc','cloudwatch','visual studio code'])
    return tuple(sorted(all_terms-generic))


def extract_skills(text):
    # Contact addresses and profile URLs are not skill evidence.
    content=re.sub(r'[^\s@]+@[^\s@]+\.[^\s@]+|(?:https?://|www\.)\S+', ' ', text)
    return [term for term in skill_vocabulary() if contains(content,term)]


def extract_degrees(text):
    from scoring import extract_sections
    body=extract_sections(text)['Education']
    patterns=[r'\bB\.?\s?Tech\b',r'\bM\.?\s?Tech\b',r'\bB\.?\s?Sc\b',r'\bM\.?\s?Sc\b',r'\bMBA\b',r'\bBCA\b',r'\bMCA\b',r'\bPh\.?D\b',r'\b(?:Bachelor|Master)(?: of [A-Za-z ]{3,45})?',r'\bDiploma(?: in [A-Za-z ]{3,45})?']
    return sorted({m.group(0).strip() for pattern in patterns for m in re.finditer(pattern,body,re.I)})


def experience_level(section_text):
    work=section_text.get('Experience','')+'\n'+section_text.get('Internships','')
    if re.search(r'\b(internship|intern|virtual training|practical training|apprentice)\b',work,re.I):return 'Intermediate'
    if len(work.split())>=20 and re.search(r'\b(?:19|20)\d{2}\b',work):return 'Experienced'
    return 'Fresher'


def parse_resume(content, filename, form=None):
    form=form or {}
    text=extract_document(content,filename)
    validate_resume_text(text)
    skills=extract_skills(text)
    quality=evaluate_resume(text,skills)
    from scoring import EMAIL, PHONE
    contact_head='\n'.join(text.splitlines()[:15])
    email=EMAIL.search(contact_head)
    phones=[m.group(0).strip() for m in PHONE.finditer(contact_head) if 10<=len(re.sub(r'\D','',m.group(0)))<=15]
    data=normalize_candidate({'name':None,'email':email.group(0) if email else None,'mobile_number':phones[0] if phones else None,'degree':extract_degrees(text),'skills':skills,'no_of_pages':1},form.get('name',''),form.get('email',''),form.get('mobile',''),resume_text=text)
    if filename.lower().endswith('.pdf'):
        import io
        from pdfminer.pdfpage import PDFPage
        data['no_of_pages']=sum(1 for _ in PDFPage.get_pages(io.BytesIO(content)))
    elif filename.lower().endswith('.docx'):
        data['page_count_note']='DOCX page count is unavailable without a layout engine; one is used as the legacy model default.'
    else:
        data['page_count_note']='Single resume image; text was read using local OCR.'
    return text, data, quality


def analyze_resume(conn, content, filename, form=None, job_description=''):
    text,data,quality=parse_resume(content,filename,form)
    skills=data['skills']
    level=experience_level(quality['section_text'])
    from reference_data import match_career
    dataset_match=match_career(skills)
    prediction={'used_model':False,'field':None,'confidence':None,'model_version':None}
    evidence=infer_category(text)
    if dataset_match and evidence and dataset_match['field']!=evidence['category'] and len(evidence['terms'])>=3:
        dataset_match=None
        prediction['reason']='Reference skill overlap conflicts with stronger explicit career evidence; resume-term rules were used.'
    field=dataset_match['field'] if dataset_match else evidence['category'] if evidence else 'Job field could not be determined'
    specialization=(evidence or {}).get('specialization')
    suggestions=(evidence or {}).get('recommendations',[])
    if specialization:
        targets=SPECIALIZATIONS.get(specialization,[])
        suggestions=[t for t in targets if not contains(text,t)]
    elif dataset_match:
        suggestions=dataset_match['suggested_skills']
    job_match=None
    if job_description.strip():
        required=extract_skills(job_description)
        matched=[s for s in required if contains(text,s)]
        missing=[s for s in required if s not in matched]
        job_match={'recognized_skills':required,'matched':matched,'missing':missing,'coverage_percent':round(100*len(matched)/len(required)) if required else None,'note':'Coverage of recognized skill keywords in the supplied job description, not an employer ATS rating.'}
        suggestions=missing
    return dict(quality,candidate=data,experience_level=level,predicted_field=field,specialization=specialization,skills=skills,recommended_skills=suggestions,model=prediction,dataset_match=dataset_match,category_evidence=evidence,job_match=job_match,resume_text=text,analysis_version='3.0-reference')
