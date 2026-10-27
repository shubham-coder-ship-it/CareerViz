"""Dataset-based skill matching. No trainable model, scaler or activation workflow."""
import json
import math
from functools import lru_cache
from pathlib import Path

INDEX = Path(__file__).with_name('reference_data') / 'index.json'


@lru_cache(maxsize=2)
def _read_index(path, modified):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def reference_index():
    if not INDEX.is_file():
        return {'records':[], 'profiles':{}, 'summary':{'status':'Reference data has not been prepared.'}}
    return _read_index(str(INDEX), INDEX.stat().st_mtime_ns)


def match_career(skills):
    from resume_pipeline import skill_vocabulary
    allowed=set(skill_vocabulary())
    profiles = reference_index()['profiles']
    observed = {s.casefold() for s in skills}
    if not observed or not profiles:
        return None
    categories = len(profiles)
    rankings = []
    for category, profile in profiles.items():
        counts = profile['skills']
        matched = observed & set(counts)
        # Terms found across most categories convey little information about a job.
        score = sum(math.log((categories+1)/(1+sum(t in p['skills'] for p in profiles.values()))) *
                    (counts[t]/max(profile['documents'],1)) for t in matched)
        if len(matched) >= 2 and score > 0:
            rankings.append({'field':category, 'similarity_points':round(score,3), 'matched_skills':sorted(matched)})
    rankings.sort(key=lambda r:(-r['similarity_points'],r['field']))
    if not rankings or (len(rankings)>1 and rankings[0]['similarity_points'] <= rankings[1]['similarity_points']*1.05):
        return None
    best = rankings[0]
    def relevance(item):
        term,count=item
        rarity=math.log((categories+1)/(1+sum(term in p['skills'] for p in profiles.values())))
        return count/max(profiles[best['field']]['documents'],1)*rarity
    missing = [term for term,count in sorted(profiles[best['field']]['skills'].items(),key=lambda item:(-relevance(item),item[0])) if term in allowed and term not in observed and relevance((term,count))>0][:8]
    return {'field':best['field'],'matches':rankings[:3], 'suggested_skills':missing,
            'note':'Skill similarity to the supplied reference dataset; not a trained model probability or a hiring guarantee.'}
