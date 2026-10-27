"""Prepare the user's local reference ZIP without extracting or publishing resumes."""
import collections
import concurrent.futures
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def initialize_worker(archive, terms):
    global SOURCE, MATCHER
    SOURCE = zipfile.ZipFile(archive)
    MATCHER = re.compile(r'(?<!\w)(?:'+ '|'.join(re.escape(t) for t in sorted(terms,key=len,reverse=True))+r')(?!\w)', re.I)


def inspect_member(name):
    from pdfminer.high_level import extract_text
    category = PurePosixPath(name).parent.name.upper()
    try:
        content=SOURCE.read(name)
        if not content.startswith(b'%PDF-'):
            raise ValueError('Invalid PDF signature')
        text=extract_text(io.BytesIO(content),maxpages=15)
        if len(text.strip())<40:
            raise ValueError('No readable text; OCR may be required')
        text=re.sub(r'[^\s@]+@[^\s@]+\.[^\s@]+|(?:https?://|www\.)\S+',' ',text)
        skills=sorted({m.group(0).casefold() for m in MATCHER.finditer(text)})
        return {'file':PurePosixPath(name).name,'category':category,'skills':skills,'status':'ready','content_hash':hashlib.sha256(content).hexdigest()}
    except Exception as exc:
        return {'file':PurePosixPath(name).name,'category':category,'skills':[],'status':'unreadable','error':str(exc)[:160]}


def main(archive):
    from resume_pipeline import skill_vocabulary
    with zipfile.ZipFile(archive) as source:
        members=[i for i in source.infolist() if not i.is_dir() and i.filename.lower().endswith('.pdf')]
        if len(members)>10000 or sum(i.file_size for i in members)>500*1024*1024:
            raise ValueError('Reference dataset exceeds safety limits.')
        for member in members:
            path=PurePosixPath(member.filename.replace('\\','/'))
            if path.is_absolute() or '..' in path.parts or member.file_size>10*1024*1024:
                raise ValueError('Unsafe reference archive member.')
    records=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=4,initializer=initialize_worker,initargs=(archive,skill_vocabulary())) as pool:
        for record in pool.map(inspect_member,[i.filename for i in members],chunksize=8):
            records.append(record)
            if len(records)%100==0:print(f'Prepared {len(records)}/{len(members)} PDFs',flush=True)
    profiles={}
    seen=set()
    for record in records:
        if record['status']!='ready':continue
        key=(record['category'],record['content_hash'])
        if key in seen:
            record['status']='duplicate';continue
        seen.add(key)
        profile=profiles.setdefault(record['category'],{'documents':0,'skills':collections.Counter()})
        profile['documents']+=1;profile['skills'].update(record['skills'])
    summary={'source':'data.zip','files':len(records),'usable':sum(r['status']=='ready' for r in records),
             'unreadable':sum(r['status']=='unreadable' for r in records),'duplicates':sum(r['status']=='duplicate' for r in records),
             'categories':len(profiles),'method':'Fixed dataset skill matching; no model training. Up to 15 pages per reference PDF.'}
    folder=Path(__file__).resolve().parents[1]/'reference_data';folder.mkdir(exist_ok=True)
    temporary=folder/'index.tmp'
    temporary.write_text(json.dumps({'summary':summary,'profiles':profiles,'records':records}),encoding='utf-8')
    os.replace(temporary,folder/'index.json')
    print(json.dumps(summary),flush=True)


if __name__=='__main__':main(sys.argv[1])
