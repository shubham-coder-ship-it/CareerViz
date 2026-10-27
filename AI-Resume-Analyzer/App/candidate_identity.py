"""Conservative resume-header identity extraction, independent of NLP downloads."""
import re
import unicodedata

LOCATIONS = {
    'andhra pradesh','arunachal pradesh','assam','bihar','chhattisgarh','goa','gujarat',
    'haryana','himachal pradesh','jharkhand','karnataka','kerala','madhya pradesh',
    'maharashtra','manipur','meghalaya','mizoram','nagaland','odisha','orissa','punjab',
    'rajasthan','sikkim','tamil nadu','telangana','tripura','uttar pradesh','uttarakhand',
    'west bengal','delhi','new delhi','chandigarh','puducherry','jammu and kashmir',
    'ladakh','andaman and nicobar islands','lakshadweep','dadra and nagar haveli',
    'tamilnadu','uttarpradesh','madhyapradesh','westbengal','india','mumbai','chennai','hyderabad','bengaluru','bangalore','kolkata','pune',
    'new york','california','texas','london','united states','united kingdom',
}
NON_NAMES = {
    'about','me','interested','interests','others','activities','curricular',
    'cv','name','resume','curriculum','vitae','profile','summary','objective','career','education',
    'experience','employment','internship','projects','skills','certifications','contact',
    'address','location','state','city','country','district','email','phone','mobile',
    'engineer','engineering','developer','technician','manager','facilities','software',
    'analyst','consultant','designer','student','graduate','fresher','university','college',
    'school','bachelor','master','degree','personal','details','professional','portfolio',
    'linkedin','github','http','https','www','pvt','ltd','limited','inc','street','road',
    'nagar','postal','pin','pincode','qualification','qualifications','data','science',
}
SECTIONS = re.compile(r'^(about me|summary|objective|career objective|education|work experience|experience|employment|skills|projects|certifications|qualifications|interests|interested|others)\b', re.I)


def is_person_name(value):
    value = ' '.join(str(value or '').strip().split())
    folded = value.casefold().strip(' .,')
    if not 2 <= len(value) <= 100 or folded in LOCATIONS:
        return False
    if any(re.search(r'(?<!\w)' + re.escape(place) + r'(?!\w)', folded) for place in LOCATIONS):
        return False
    words = value.split()
    if not 1 <= len(words) <= 6:
        return False
    if any(word.casefold().strip('.,') in NON_NAMES for word in words):
        return False
    return any(c.isalpha() for c in value) and all(c.isalpha() or c.isspace() or c in ".'-’" or unicodedata.category(c).startswith('M') for c in value)


def extract_candidate_name(text):
    """Only trust an explicit name label or a plausible standalone header line.

    Never promote arbitrary proper nouns from the address or resume body.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()][:15]
    for line in lines:
        match = re.match(r'^(?:candidate(?:\s+name)?|full\s+name|name)\s*[:：-]\s*(.+)$', line, re.I)
        if match and is_person_name(match[1]):
            return ' '.join(match[1].split())
    for line in lines:
        if SECTIONS.match(line):
            break
        # Columns/contact separators do not form part of a candidate's name.
        candidate = re.split(r'\s*[|•]\s*', line)[0].strip()
        if 2 <= len(candidate.split()) <= 5 and is_person_name(candidate):
            return candidate
        if '@' in line or len(re.sub(r'\D','',line))>=7:
            # A missing/cropped name must use the manual fallback; addresses and
            # OCR fragments appearing after contact details are not candidates.
            break
    return None
