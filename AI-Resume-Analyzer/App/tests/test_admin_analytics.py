import datetime as dt
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
import database
from admin_analytics import local_dates,load_activity,filter_activity,csv_download


class AdminAnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.patch=patch.object(database,'DB_PATH',str(Path(self.temp.name)/'test.db'));self.patch.start()
        database.initialize();self.conn=database.get_connection()
        for i,stamp in enumerate(['2026-10-26T18:29:00+00:00','2026-10-26T18:31:00+00:00','2026-10-27T09:00:00+00:00']):
            payload={'candidate':{'name':'Fictional Person'},'score':50+i*10,'predicted_field':'ENGINEERING' if i==0 else 'INFORMATION-TECHNOLOGY','experience_level':'Fresher','scoring_version':'review-v3' if i else 'evidence-v2'}
            self.conn.execute('INSERT INTO analyses VALUES (?,?,?,?,?,?)',(str(i),'same-session' if i<2 else 'other-session',str(i),'fictional.pdf',stamp,json.dumps(payload)))
        self.conn.commit()
    def tearDown(self):
        self.conn.close();self.patch.stop();self.temp.cleanup()
    def test_local_dates_boundary_and_legacy_feedback(self):
        dates=local_dates(pd.Series(['2026-10-26T18:31:00+00:00','2026-10-27_00:01:00','bad']))
        self.assertEqual(dates.iloc[0].date(),dt.date(2026,10,27));self.assertEqual(dates.iloc[1].hour,0);self.assertTrue(pd.isna(dates.iloc[2]))
    def test_inclusive_filters_and_distinct_submission_sessions(self):
        frame,_,_=load_activity(self.conn)
        filtered=filter_activity(frame,dt.date(2026,10,27),dt.date(2026,10,27))
        self.assertEqual(len(filtered),2);self.assertEqual(filtered.Session.nunique(),2)
        chosen=filter_activity(frame,dt.date(2026,10,26),dt.date(2026,10,27),['ENGINEERING'],'evidence-v2',(50,50))
        self.assertEqual(len(chosen),1)
        with self.assertRaises(ValueError):filter_activity(frame,dt.date(2026,10,28),dt.date(2026,10,27))
    def test_export_does_not_reveal_session_tokens_or_excel_formulas(self):
        data=pd.DataFrame({'Session':['secret-token'],'Name':['=SAMPLE()'],'Score':[55]})
        export=csv_download(data).decode('utf-8-sig')
        self.assertNotIn('secret-token',export);self.assertIn("'=SAMPLE()",export)
    def test_admin_dashboard_filters_and_charts(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(Path(database.__file__).with_name('App.py')),default_timeout=40)
        app.session_state['_ara_nav']='Admin';app.session_state['_ara_admin_ok']=True;app.session_state['_ara_admin_until']=time.time()+300
        app.run();self.assertFalse(app.exception,str(app.exception))
        self.assertTrue(any(m.label=='Analysis sessions' for m in app.metric))
        app.segmented_control(key='analytics_period').set_value('Custom').run()
        app.date_input(key='analytics_start').set_value(dt.date(2026,10,27)).run()
        app.date_input(key='analytics_end').set_value(dt.date(2026,10,27)).run()
        self.assertFalse(app.exception,str(app.exception))
        self.assertEqual(next(m.value for m in app.metric if m.label=='Resume analyses'),'2')
        app.date_input(key='analytics_start').set_value(dt.date(2026,10,28)).run()
        self.assertTrue(any('on or after' in e.value for e in app.error))
    def test_signed_out_admin_cannot_see_analytics(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(Path(database.__file__).with_name('App.py')),default_timeout=40)
        app.session_state['_ara_nav']='Admin';app.run()
        self.assertFalse(app.exception,str(app.exception));self.assertFalse(app.metric)


if __name__=='__main__':unittest.main()
