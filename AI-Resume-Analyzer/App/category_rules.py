"""Explicit category evidence, independent of resume score and page count."""
import re
RULES = {
 'INFORMATION-TECHNOLOGY':['devops','cloud','aws','kubernetes','terraform','docker','python','javascript','typescript','postgresql','linux','ci/cd','site reliability','distributed systems','software development','network administration'],
 'ENGINEERING':['mechanical engineering','electrical engineering','fabrication','autocad','solidworks','thermodynamics','finite element','hvac','machining','mechatronics'],
 'HEALTHCARE':['patient care','nursing','clinical care','healthcare','medical records','physician','pharmacology'],
 'FINANCE':['financial analysis','financial reporting','financial planning','investment analysis','portfolio management','budgeting'],
 'ACCOUNTANT':['accounting','auditing','general ledger','accounts payable','accounts receivable','tax preparation'],
 'HR':['human resources','recruitment','employee relations','payroll','talent acquisition','onboarding'],
 'SALES':['sales target','sales pipeline','lead generation','account management','salesforce','sales representative'],
 'CONSTRUCTION':['construction management','civil engineering','site supervision','quantity surveying','structural design'],
 'CHEF':['chef','culinary','food preparation','menu planning','kitchen management','food safety'],
 'ADVOCATE':['litigation','legal research','court proceedings','legal counsel','advocate','contract law'],
 'BANKING':['retail banking','loan processing','credit analysis','bank teller','mortgage','banking operations'],
 'BUSINESS-DEVELOPMENT':['business development','market expansion','strategic partnerships','client acquisition','go to market'],
 'CONSULTANT':['management consulting','business consulting','business transformation','stakeholder analysis','consultant'],
 'DESIGNER':['graphic design','ui/ux','user experience','figma','typography','visual design','adobe illustrator'],
 'DIGITAL-MEDIA':['digital marketing','search engine optimization','google analytics','content marketing','social media marketing','video production'],
 'PUBLIC-RELATIONS':['public relations','media relations','press releases','crisis communication','publicist'],
 'AGRICULTURE':['agronomy','crop management','soil science','irrigation','horticulture','agriculture'],
 'APPAREL':['fashion design','textile design','garment','apparel','pattern making'],
 'ARTS':['fine arts','painting','sculpture','art exhibition','performing arts'],
 'AUTOMOBILE':['automotive','vehicle diagnostics','automobile','engine repair','vehicle maintenance'],
 'AVIATION':['aviation','aircraft','air traffic','flight operations','aeronautical','pilot license'],
 'BPO':['business process outsourcing','call center','bpo','customer support','inbound calls','outbound calls'],
 'FITNESS':['personal trainer','fitness training','exercise physiology','strength training','fitness instructor'],
 'TEACHER':['lesson planning','classroom management','teaching','curriculum development','student assessment'],
}
SPECIALIZATIONS = {
 'Cloud & DevOps':['devops','terraform','kubernetes','ci/cd','site reliability','cloudwatch','infrastructure automation'],
 'Data Science':['machine learning','data science','tensorflow','pytorch','statistical modeling','predictive modeling'],
 'Web Development':['react','django','javascript','typescript','frontend','full stack','web development'],
 'Android Development':['android','kotlin','android studio'],
 'IOS Development':['ios development','swift','xcode'],
}
ALIASES = {'data science':'INFORMATION-TECHNOLOGY','web development':'INFORMATION-TECHNOLOGY','android development':'INFORMATION-TECHNOLOGY','ios development':'INFORMATION-TECHNOLOGY','ui-ux development':'DESIGNER','finance':'FINANCE','hr':'HR','hospitality':'CHEF','legal':'ADVOCATE'}


def contains(text, term):
    return re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', text, re.I) is not None


def canonical_category(label):
    raw = str(label or '').strip()
    return ALIASES.get(raw.casefold(), re.sub(r'[ _]+','-',raw.upper()))


def category_evidence(text):
    header = '\n'.join(text.splitlines()[:12])
    results=[]
    for category,terms in RULES.items():
        hits=[term for term in terms if contains(text,term)]
        if len(hits)<2: continue
        # Header specialization is useful evidence, never a degree's broad "engineering" label.
        points=len(hits)+sum(2 for term in hits if contains(header,term))
        results.append({'category':category,'terms':hits,'points':points,'recommendations':[t for t in terms if t not in hits]})
    return sorted(results,key=lambda r:(-r['points'],r['category']))


def infer_category(text):
    results=category_evidence(text)
    if not results or (len(results)>1 and results[0]['points']==results[1]['points']):return None
    best=dict(results[0])
    if best['category']=='INFORMATION-TECHNOLOGY':
        head='\n'.join(text.splitlines()[:12])
        specs=[]
        for label,terms in SPECIALIZATIONS.items():
            hits=[t for t in terms if contains(text,t)]
            if len(hits)>=2:specs.append((sum(3 if contains(head,t) else 1 for t in hits),label))
        specs.sort(reverse=True)
        best['specialization']=specs[0][1] if specs and (len(specs)==1 or specs[0][0]>specs[1][0]) else None
    return best
