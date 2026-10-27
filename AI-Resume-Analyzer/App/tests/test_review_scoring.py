import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scoring import evaluate_resume, SCORING_VERSION
from resume_pipeline import extract_skills

WEAK='''Alex Morgan
alex@example.com | +1 202 555 0147
Profile
Highly motivated hardworking student seeking a challenging role in software development with a dynamic team.
Skills
Python, SQL, JavaScript, Git, Docker, Linux, keyboard, international, visual, controls, engagement, regulatory
Education
Bachelor degree expected 2027
Projects
Created a calculator application with keyboard controls. Built a tutorial project using Python.
Certifications
Completed an online course about software development.
'''


class ReviewScoringTests(unittest.TestCase):
    def test_exact_weights_and_reproducibility(self):
        result=evaluate_resume(WEAK)
        self.assertEqual([r['maximum'] for r in result['score_breakdown']],[25,20,15,10,10,10,5,5])
        self.assertEqual(result['score'],sum(r['earned'] for r in result['score_breakdown']))
        self.assertEqual(result,evaluate_resume(WEAK))
        self.assertEqual(result['scoring_version'],'review-v3')
        self.assertEqual(sum(v['maximum'] for v in result['subscores'].values()),100)
    def test_sections_and_keyword_noise_do_not_make_strong_resume(self):
        self.assertLess(evaluate_resume(WEAK)['score'],60)
        self.assertFalse(set(['keyboard','international','visual','controls','engagement','regulatory']) & set(extract_skills(WEAK)))
        padded=WEAK.replace('Linux,','Linux, international, visual, keyboard, engagement,')
        self.assertEqual(evaluate_resume(WEAK)['score'],evaluate_resume(padded)['score'])
    def test_demonstrated_skills_and_project_evidence_improve_score(self):
        strong=WEAK.replace('Created a calculator application with keyboard controls. Built a tutorial project using Python.',
            'Inventory service | Jan 2025 - Jun 2025 | https://github.com/alex-morgan/inventory\nDesigned and implemented a Python and SQL API with Docker and Linux. Reduced latency by 25 percent, tested 40 cases and supported 100 users.')
        a,b=evaluate_resume(WEAK),evaluate_resume(strong)
        self.assertGreater(b['score'],a['score'])
        self.assertGreater(b['score_breakdown'][0]['earned'],a['score_breakdown'][0]['earned'])
        self.assertGreater(b['score_breakdown'][2]['earned'],a['score_breakdown'][2]['earned'])
    def test_dates_and_phone_are_not_achievement_metrics(self):
        base=evaluate_resume(WEAK)
        dated=evaluate_resume(WEAK.replace('Created a calculator','2024 - 2025\nCreated a calculator'))
        self.assertEqual(base['score_breakdown'][0]['earned'],dated['score_breakdown'][0]['earned'])
    def test_no_experience_credit_for_courses_and_placeholder_links(self):
        result=evaluate_resume(WEAK)
        self.assertEqual(result['score_breakdown'][1]['earned'],0)
        placeholder=evaluate_resume(WEAK.replace('Created a calculator','https://example.com/project\nCreated a calculator'))
        self.assertEqual(result['score_breakdown'][0]['earned'],placeholder['score_breakdown'][0]['earned'])

    def test_guided_training_not_full_work_credit(self):
        text=WEAK+'\nExperience\nVirtual Intern | Example Studio | 2024 - 2025\nCompleted guided milestones and hands-on lab exercises. Developed and implemented automation in structured assignments.\n'
        result=evaluate_resume(text)
        self.assertLessEqual(result['score_breakdown'][1]['earned'],8)
        self.assertIn('Guided-training language: True',result['score_breakdown'][1]['evidence'])


if __name__=='__main__':unittest.main()
