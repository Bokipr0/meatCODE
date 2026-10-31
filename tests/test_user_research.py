# Last updated: 2026-10-29 10:49 UTC · Data/Backend · public provider config, consent renewal and rollback-only storage regression checks.
import datetime
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'server'))
sys.path.insert(0,str(ROOT/'pipeline/user_research'))
import user_research as research
from clarity_import import sanitize_aggregates, _reserve
from settings import settings


def event_payload():
    return {'session_id':str(uuid.uuid4()),'consent':True,'consent_version':research.CONSENT_VERSION,
            'events':[{'event_id':str(uuid.uuid4()),'name':'oracle.completed','scene':'oracle',
                       'properties':{'duration_ms':1200,'source_count':3}}]}


class ValidationTests(unittest.TestCase):
    def test_runtime_settings_and_render_dotenv_isolation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'.env').write_text('DATABASE_URL=file-production-placeholder\nCLARITY_EXPORT_TOKEN=file-token-placeholder\n')
            (root/'.env.dev').write_text('DATABASE_URL=file-development-placeholder\nCLARITY_EXPORT_TOKEN=\n')
            process={'RENDER':'true','DATABASE_URL':'runtime-db-placeholder','CLARITY_EXPORT_TOKEN':'runtime-token-placeholder'}
            self.assertEqual(settings('prod',process,root)['DATABASE_URL'],'runtime-db-placeholder')
            self.assertEqual(settings('dev',process,root)['CLARITY_EXPORT_TOKEN'],'runtime-token-placeholder')
            self.assertEqual(settings('dev',{},root)['DATABASE_URL'],'file-development-placeholder')
            self.assertEqual(settings('dev',{},root)['CLARITY_EXPORT_TOKEN'],'file-token-placeholder')
            self.assertEqual(settings('prod',process,root/'absent')['CLARITY_EXPORT_TOKEN'],'runtime-token-placeholder')

    def test_demo_policy_is_versioned_and_optional_mode_can_be_restored(self):
        demo=research.config({'USER_RESEARCH_ENABLED':'1'},'dev')
        self.assertTrue(demo['demo_mode'])
        self.assertEqual(demo['consent_version'],research.DEMO_VERSION)
        optional=research.config({'USER_RESEARCH_ENABLED':'1','RESEARCH_DEMO_MODE':'false'},'prod')
        self.assertFalse(optional['demo_mode'])
        self.assertEqual(optional['consent_version'],research.CONSENT_VERSION)
        payload=event_payload();payload['consent_version']=research.DEMO_VERSION
        payload['user_ref']=str(uuid.uuid4());payload['events'][0]['elapsed_ms']=0
        research.validate_events(payload)

    def test_opt_in_defaults(self):
        self.assertFalse(research.config({},'dev')['enabled'])
        self.assertTrue(research.config({'USER_RESEARCH_ENABLED':'true'},'prod')['enabled'])
        self.assertEqual(research.config({},'prod')['retention_days'],90)

    def test_posthog_requires_public_project_key_official_host_and_research_enablement(self):
        token='phc_'+'publicfixture'*3
        valid={'USER_RESEARCH_ENABLED':'1','POSTHOG_PROJECT_TOKEN':token,'POSTHOG_API_HOST':'https://eu.i.posthog.com'}
        self.assertTrue(research.config(valid,'prod')['posthog']['enabled'])
        for changes in ({'USER_RESEARCH_ENABLED':'0'},{'POSTHOG_PROJECT_TOKEN':'phx_privatefixture'},
                        {'POSTHOG_API_HOST':'https://eu.i.posthog.com.evil.test'},
                        {'POSTHOG_API_HOST':'https://eu.i.posthog.com/private'}, {'POSTHOG_PROJECT_TOKEN':''}):
            env=dict(valid);env.update(changes)
            self.assertFalse(research.config(env,'prod')['posthog']['enabled'])
        self.assertFalse(research.config({},'prod')['posthog']['enabled'])

    def test_old_consent_requires_explicit_renewal(self):
        payload=event_payload();payload['consent_version']='2026-10-28'
        with self.assertRaises(research.InputError):research.validate_events(payload)

    def test_reject_raw_prompts_and_unconsented_input_before_db(self):
        for changes in ({'consent':False},{'consent':1},{'consent_version':'old'},{'prompt':'secret'}):
            payload=event_payload();payload.update(changes)
            with self.assertRaises(research.InputError):research.write_events(None,'dev',payload)
        payload=event_payload();payload['events'][0]['properties']['prompt']='never store'
        with self.assertRaises(research.InputError):research.validate_events(payload)

    def test_limits_and_explicit_types(self):
        for value in (True,-1,3600001,'1200'):
            payload=event_payload();payload['events'][0]['properties']['duration_ms']=value
            with self.assertRaises(research.InputError):research.validate_events(payload)
        payload=event_payload();payload['events']*=21
        with self.assertRaises(research.InputError):research.validate_events(payload)
        payload=event_payload();payload['session_id']=str(uuid.uuid1())
        with self.assertRaises(research.InputError):research.validate_events(payload)

    def test_feedback_boundary(self):
        payload=event_payload();payload.pop('events');payload.update(event_id=str(uuid.uuid4()),rating='helpful',category='answer',comment='explicit feedback')
        self.assertEqual(research.validate_feedback(payload)[1]['comment'],'explicit feedback')
        for text in ('x'*2001,'bad\x00input'):
            payload['comment']=text
            with self.assertRaises(research.InputError):research.validate_feedback(payload)

    def test_aggregate_privacy(self):
        result=sanitize_aggregates([
            {'metricName':'Traffic','information':[{'totalSessionCount':'7','OS':'Mac OS X','URL':'https://private.test/?prompt=secret',
                                                   'prompt':'secret','Referrer URL':'secret','count':float('nan')}]},
            {'metricName':'Popular Pages','information':[{'URL':'secret','totalSessionCount':'9'}]},
            {'metricName':'Page Title','information':[{'title':'secret'}]}])
        self.assertEqual(result,[{'metricName':'Traffic','information':[{'totalSessionCount':7,'OS':'Mac OS X'}]}])
        self.assertNotIn('secret',json.dumps(result))


@unittest.skipUnless(os.environ.get('USER_RESEARCH_TEST_DB_URL'),'Live DB rollback test is opt-in.')
class RollbackDatabaseTests(unittest.TestCase):
    def setUp(self):
        import psycopg2
        self.psycopg2=psycopg2
        self.conn=psycopg2.connect(os.environ['USER_RESEARCH_TEST_DB_URL'],connect_timeout=5)
        self.cur=self.conn.cursor()
        self.cur.execute("SET LOCAL statement_timeout='6s'; SET LOCAL lock_timeout='3s'")
        self.payload=event_payload();self.sid,self.events=research.validate_events(self.payload)

    def tearDown(self):
        self.conn.rollback();self.cur.close();self.conn.close()

    def test_idempotency_environment_and_withdrawal(self):
        self.assertEqual(research._write_events(self.cur,'prod',self.sid,self.events)['accepted'],1)
        self.assertEqual(research._write_events(self.cur,'prod',self.sid,self.events)['duplicate'],1)
        feedback={'event_id':str(uuid.uuid4()),'rating':'helpful','category':'bug','comment':"fixture '; DROP TABLE scientific; --"}
        self.assertEqual(research._write_feedback(self.cur,'prod',self.sid,feedback)['accepted'],1)
        self.assertEqual(research._write_feedback(self.cur,'prod',self.sid,feedback)['duplicate'],1)
        research._withdraw(self.cur,'prod',self.sid)
        for table in ('events','feedback','oracle_turns'):
            self.cur.execute('SELECT count(*) FROM user_research.'+table+' WHERE session_id=%s AND environment=%s',(self.sid,'prod'))
            self.assertEqual(self.cur.fetchone()[0],0)
        with self.assertRaises(research.WithdrawnError):research._write_events(self.cur,'prod',self.sid,self.events)
        research._withdraw(self.cur,'prod',self.sid)
        self.cur.execute('SELECT withdrawn_at IS NOT NULL, tester_label,user_ref,clarity_ref,consent_at,consent_version FROM user_research.sessions WHERE session_id=%s AND environment=%s',(self.sid,'prod'))
        self.assertEqual(self.cur.fetchone(),(True,None,None,None,None,None))

    def test_denver_note_keeps_name_and_event_until_withdrawn(self):
        sid=self.sid
        version=research.DEMO_VERSION
        research._write_events(self.cur,'prod',sid,self.events,{'tester_label':'QA'},version)
        payload=dict(session_id=sid,consent=True,consent_version=version,tester_label='QA',
                     event_id=str(uuid.uuid4()),comment='fixture note',anchor_event_id=self.events[0]['event_id'])
        _,note,identity=research.validate_note(payload)
        def submit():return research._write_note(self.cur,'prod',sid,note,identity,version)
        self.assertFalse(submit()['duplicate']);self.assertTrue(submit()['duplicate'])
        self.cur.execute("SELECT tester_label,context->>'anchor_event_id',f.created_at IS NOT NULL FROM user_research.feedback f JOIN user_research.sessions USING(session_id,environment) WHERE f.event_id=%s",(note['event_id'],))
        self.assertEqual(self.cur.fetchone(),('QA',self.events[0]['event_id'],True))
        research._withdraw(self.cur,'prod',sid)
        with self.assertRaises(research.WithdrawnError):submit()
        self.cur.execute('SELECT count(*) FROM user_research.feedback WHERE session_id=%s',(sid,))
        self.assertEqual(self.cur.fetchone()[0],0)

    def test_renewed_consent_is_explicit_and_other_legacy_rows_are_unchanged(self):
        untouched=str(uuid.uuid4())
        for session in (self.sid,untouched):
            self.cur.execute('INSERT INTO user_research.sessions(session_id,environment,consent_version) VALUES(%s,%s,%s)',
                             (session,'prod','2026-10-28'))
        research._write_events(self.cur,'prod',self.sid,self.events)
        self.cur.execute('SELECT consent_version FROM user_research.sessions WHERE session_id=%s AND environment=%s',(self.sid,'prod'))
        self.assertEqual(self.cur.fetchone()[0],research.CONSENT_VERSION)
        self.cur.execute('SELECT consent_version FROM user_research.sessions WHERE session_id=%s AND environment=%s',(untouched,'prod'))
        self.assertEqual(self.cur.fetchone()[0],'2026-10-28')

    def test_withdrawal_serializes_concurrent_writers(self):
        research._withdraw(self.cur,'prod',self.sid)
        other=self.psycopg2.connect(os.environ['USER_RESEARCH_TEST_DB_URL'],connect_timeout=5)
        try:
            with other.cursor() as cur:
                cur.execute("SET LOCAL lock_timeout='200ms'; SET LOCAL statement_timeout='2s'")
                with self.assertRaises(self.psycopg2.errors.LockNotAvailable):
                    research._write_events(cur,'prod',self.sid,self.events)
        finally:
            other.rollback();other.close()

    def test_export_daily_dedup_and_quota(self):
        project='test'+uuid.uuid4().hex[:12];today=datetime.date.today()
        first,state=_reserve(self.cur,'prod',project,today,1)
        if state=='archive_not_configured':return self.assertIsNone(first)
        self.assertEqual(state,'reserved')
        self.assertEqual(_reserve(self.cur,'prod',project,today,1),(None,'pending'))
        self.cur.execute("UPDATE user_research.clarity_exports SET status='failed',attempts=10 WHERE export_id=%s",(first,))
        self.assertEqual(_reserve(self.cur,'prod',project,today,2),(None,'daily_limit'))


if __name__=='__main__':unittest.main()
