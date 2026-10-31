# Last updated: 2026-10-31 · Names belong to immutable sessions, not browser profiles.
from contextlib import contextmanager
from pathlib import Path
import datetime, sys, unittest, uuid
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'server'))
import user_research as research
import research_dashboard as dashboard

class SessionCursor:
    def __init__(self): self.rows={}; self.key=None; self.result=None
    def execute(self, query, args):
        if 'SELECT 1 FROM' in query: self.result=None
        elif 'INSERT INTO user_research.sessions' in query:
            self.key=args[:2]; self.rows.setdefault(self.key,(None,None,None))
        elif 'SELECT user_ref,clarity_ref,tester_label' in query: self.result=self.rows[args]
        elif 'UPDATE user_research.sessions SET user_ref=' in query:
            key=args[-2:];self.rows[key]=tuple(old if old is not None else new for old,new in zip(self.rows[key],args[:3]))
    def fetchone(self): return self.result

class NameTests(unittest.TestCase):
    def test_acknowledged_name_is_bound_to_session_and_cannot_be_replaced(self):
        cur=SessionCursor()
        @contextmanager
        def transaction(_): yield cur
        def payload(sid,name):return dict(session_id=sid,consent=True,consent_version=research.DEMO_VERSION,tester_label=name,user_ref=browser)
        first,second,browser=[str(uuid.uuid4()) for _ in range(3)]
        with patch.object(research,'transaction',transaction):
            self.assertEqual(research.name_session('fake','prod',payload(first,' Alex ')),{'ok':True})
            research.name_session('fake','prod',payload(first,'Alex')) # response-lost retry is idempotent
            research.name_session('fake','prod',payload(second,'Alex')) # identical names and browser, independent sessions
            self.assertEqual(len(cur.rows),2)
            self.assertEqual(cur.rows[(first,'prod')][2],'Alex')
            with self.assertRaises(research.InputError):research.name_session('fake','prod',payload(first,'Sam'))
            self.assertEqual(cur.rows[(first,'prod')][2],'Alex')
            for name in ('', '  ', 'bad\nname', 'x'*81, False):
                with self.assertRaises(research.InputError):research.name_session('fake','prod',payload(first,name))
    def test_dashboard_same_names_have_distinct_session_references(self):
        first,second,browser=[str(uuid.uuid4()) for _ in range(3)]
        now=datetime.datetime.now(datetime.timezone.utc)
        class Cursor:
            def execute(self,*args):pass
            def fetchall(self):
                return [(str(uuid.uuid4()),kind,now,browser,'Alex','Input',1200,None,None,'submitted',sid,{})
                        for sid in (first,second) for kind in ('oracle.input','feedback.input')]
        rows=dashboard.journey(Cursor(),'prod')['rows']
        self.assertEqual(rows[0]['session_label'],rows[1]['session_label'])
        self.assertNotEqual(rows[0]['session_label'],rows[2]['session_label'])
        self.assertEqual(rows[0]['session_label'],dashboard._session_label(first,'prod'))
        self.assertNotIn(first,str(rows)) # deletion capability remains private

if __name__=='__main__':unittest.main()

