# Last updated: 2026-10-29 · Codex · authenticated dev-login dashboard access and production boundary tests.
from contextlib import contextmanager
import base64
import datetime
from email.message import Message
import io
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch,MagicMock
import uuid

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
import research_dashboard as dashboard
import user_research as research


class Handler:
    def __init__(self,path='/api/research/dashboard',token=None):
        self.path=path;self.headers=Message();self.wfile=io.BytesIO()
        self.close_connection=False;self.response_headers={};self.status=None
        if token is not None:self.headers['X-MeatCODE-Research-Admin']=token

    def send_response(self,status):self.status=status
    def send_header(self,key,value):self.response_headers[key]=value
    def end_headers(self):pass
    def result(self):return json.loads(self.wfile.getvalue())


class Cursor:
    def __init__(self,empty=False):
        self.calls=[];self.stage=0;self.empty=empty;self.sid=uuid.uuid4()

    def execute(self,query,args=None):
        self.calls.append((query,args));self.stage+=1

    def fetchone(self):
        return (0,0,0,0,0,None,0) if self.empty else (1,2,1,1,1,1200,2)

    def fetchall(self):
        if self.empty:return []
        if self.stage==2:return [('oracle',4)]
        created=datetime.datetime(2026,10,29,tzinfo=datetime.timezone.utc)
        if self.stage>=5:return []
        if self.stage==3:return [(uuid.uuid4(),'oracle.completed','oracle',created,1200,None,3,self.sid,4500,'Alex')]
        return [(created,'helpful','answer','session '+str(self.sid),self.sid,'Alex')]


class DashboardTests(unittest.TestCase):
    def test_dev_site_login_reused_but_never_for_production_or_cross_origin(self):
        env={'SITE_PASSWORD':'fixture-dev-password','RENDER':'true'}
        h=Handler();h.headers['Authorization']='Basic '+base64.b64encode(b'meatcode:fixture-dev-password').decode()
        self.assertTrue(dashboard._dev_login_ok(h.headers,env,'dev'))
        self.assertFalse(dashboard._dev_login_ok(h.headers,env,'prod'))
        self.assertFalse(dashboard._dev_login_ok(h.headers,{},'dev'))
        self.assertFalse(dashboard._dev_login_ok(h.headers,dict(env,RESEARCH_DEV_LOGIN_ACCESS='false'),'dev'))
        with patch.object(dashboard,'_database_settings',side_effect=research.StorageError()):
            dashboard.handle(h,'fake-db','dev',env)
        self.assertEqual(h.status,503) # Passed authorization; storage intentionally unavailable.
        h.headers['Sec-Fetch-Site']='cross-site'
        dashboard.handle(h,'fake-db','dev',env)
        self.assertEqual(h.status,403)
        h=Handler();h.headers['Authorization']='Basic '+base64.b64encode(b'meatcode:wrong').decode()
        self.assertFalse(dashboard._dev_login_ok(h.headers,env,'dev'))

    def test_dev_site_login_reads_only_production_through_viewer_connection(self):
        env={'SITE_PASSWORD':'fixture-dev-password','RENDER':'true',
             'RESEARCH_PRODUCTION_DATABASE_URL':'production-readonly-research'}
        @contextmanager
        def readonly(target):
            self.assertEqual(target,'production-readonly-research');yield Cursor(empty=True)
        for path in ('/api/research/dashboard','/api/research/journey'):
            h=Handler(path);h.headers['Authorization']='Basic '+base64.b64encode(b'meatcode:fixture-dev-password').decode()
            with patch.object(dashboard,'readonly',readonly):dashboard.handle(h,'development-scientific-db','dev',env)
            self.assertEqual(h.status,200);self.assertEqual(h.result()['environment'],'prod')
            self.assertEqual(h.result()['access_mode'],'dev_site_login');self.assertFalse(h.result()['can_select_environment'])
            self.assertNotIn('production-readonly-research',h.wfile.getvalue().decode())

    def test_shared_password_alone_and_missing_or_short_admin_tokens_are_denied(self):
        for env in ({},{'SITE_PASSWORD':'s'*48},{'RESEARCH_ADMIN_TOKEN':'short'},
                    {'RESEARCH_ADMIN_TOKEN':'s'*48,'SITE_PASSWORD':'s'*48}):
            h=Handler(token=env.get('RESEARCH_ADMIN_TOKEN'))
            dashboard.handle(h,'fake-db','prod',dict(env,RENDER='true'),local_admin=False)
            self.assertEqual(h.status,403)
            self.assertEqual(h.response_headers['Cache-Control'],'no-store')
        h=Handler();dashboard.handle(h,'fake-db','prod',{'RENDER':'true'},local_admin=True)
        self.assertEqual(h.status,403)

    def test_duplicate_admin_headers_and_wrong_tokens_are_rejected(self):
        for provided in ('x'*48,None):
            h=Handler(token=provided)
            dashboard.handle(h,'fake-db','prod',{'RESEARCH_ADMIN_TOKEN':'t'*48})
            self.assertEqual(h.status,403)
        h=Handler(token='t'*48);h.headers['X-MeatCODE-Research-Admin']='t'*48
        dashboard.handle(h,'fake-db','prod',{'RESEARCH_ADMIN_TOKEN':'t'*48})
        self.assertEqual(h.status,403)

    def test_cross_origin_browser_cannot_read_local_admin_dashboard(self):
        for headers in ({'Origin':'https://unrelated.test','Host':'localhost:8000'},
                        {'Sec-Fetch-Site':'cross-site'}, {'Origin':'null','Host':'localhost:8000'}):
            h=Handler()
            for key,value in headers.items():h.headers[key]=value
            dashboard.handle(h,'fake-db','dev',{},local_admin=True)
            self.assertEqual(h.status,403)

    def test_supported_parameters_are_bounded_and_unknown_fields_rejected(self):
        for query in ('?minutes=1','?limit=51','?limit=0','?environment=all','?environment=dev&environment=prod',
                      '?minutes=15;DROP%20TABLE','?token=secret','?minutes=','?limit=１','?limit='+'9'*5000):
            with self.assertRaises(research.InputError):dashboard.parameters('/api/research/dashboard'+query,'prod')
        self.assertEqual(dashboard.parameters('/api/research/dashboard?minutes=1440&limit=1','dev'),('prod',1440,1))
        with self.assertRaises(research.InputError):dashboard.parameters('/api/research/dashboard?environment=dev','dev')

    def test_hosted_token_cannot_cross_environments(self):
        h=Handler('/api/research/dashboard?environment=dev',token='t'*48)
        dashboard.handle(h,'fake-db','prod',{'RENDER':'true','RESEARCH_ADMIN_TOKEN':'t'*48})
        self.assertEqual(h.status,400)

    def test_snapshot_is_bounded_parameterized_and_has_no_session_capabilities(self):
        cur=Cursor();result=dashboard.snapshot(cur,'prod',60,7)
        self.assertEqual(result['source'],'neon_first_party')
        self.assertEqual(result['totals']['median_response_ms'],1200)
        self.assertEqual(result['totals']['module_clicks'],2)
        self.assertEqual(result['limits']['activity_limit'],7)
        self.assertEqual(cur.calls[2][1][-1],7)
        self.assertNotIn(str(cur.sid),json.dumps(result))
        self.assertTrue(result['activity'][0]['session_label'].startswith('s_'))
        self.assertIn('LIMIT 20',cur.calls[3][0])
        for query,args in cur.calls:
            self.assertTrue(query.lstrip().startswith(('WITH','SELECT')))
            self.assertNotIn('prod',query)
            self.assertIsInstance(args,tuple)

    def test_empty_snapshot_is_zero_and_null(self):
        result=dashboard.snapshot(Cursor(empty=True),'prod')
        self.assertEqual(result['totals']['sessions'],0)
        self.assertIsNone(result['totals']['median_response_ms'])
        self.assertEqual(result['activity'],[]);self.assertEqual(result['feedback'],[])

    def test_successful_local_admin_and_hosted_token_paths(self):
        @contextmanager
        def readonly(target):
            self.assertEqual(target,'fake-db');yield Cursor()
        for local,environ,token in ((True,{},None),(False,{'RENDER':'true','RESEARCH_ADMIN_TOKEN':'t'*48},'t'*48)):
            h=Handler(token=token)
            with patch.object(dashboard,'readonly',readonly),patch.object(dashboard,'_database_settings',return_value=('fake-db',environ)):
                dashboard.handle(h,'fake-db','prod',environ,local)
            self.assertEqual(h.status,200);self.assertEqual(h.response_headers['Cache-Control'],'no-store')
            self.assertEqual(h.result()['providers']['posthog']['delivery'],'unverified')
            self.assertEqual(h.result()['environment'],'prod')
            self.assertFalse(h.result()['can_select_environment'])

    def test_errors_do_not_disclose_database_or_token_details(self):
        h=Handler()
        with patch.object(dashboard,'_database_settings',side_effect=RuntimeError('private-db-token')):
            dashboard.handle(h,'fake-db','prod',{},True)
        self.assertEqual(h.status,503);self.assertNotIn('private-db-token',h.wfile.getvalue().decode())

    def test_official_provider_links_only_and_config_is_not_delivery_proof(self):
        env={'POSTHOG_PROJECT_TOKEN':'phc_'+'publicfixture'*3,'POSTHOG_API_HOST':'https://eu.i.posthog.com',
             'POSTHOG_PROJECT_URL':'https://eu.posthog.com/project/123',
             'POSTHOG_DASHBOARD_URL':'https://eu.posthog.com/project/123/dashboard/456'}
        providers=dashboard.providers(env,'prod')
        self.assertTrue(providers['posthog']['configured']);self.assertEqual(providers['posthog']['delivery'],'unverified')
        for url in ('https://eu.posthog.com.evil.test/project/123','https://u:p@eu.posthog.com/project/123',
                    'https://eu.posthog.com:443/project/123','https://eu.posthog.com/project/123?token=private'):
            self.assertEqual(dashboard._provider_url(url),'')
        self.assertNotIn('phc_',json.dumps(providers))

    def test_readonly_connection_cannot_commit(self):
        import psycopg2
        connection=MagicMock();connection.cursor.return_value.__enter__.return_value=MagicMock()
        with patch.object(psycopg2,'connect',return_value=connection):
            with dashboard.readonly('fake-db'):pass
        connection.set_session.assert_called_once_with(readonly=True,isolation_level='REPEATABLE READ')
        connection.commit.assert_not_called();connection.rollback.assert_called();connection.close.assert_called_once()


@unittest.skipUnless(os.environ.get('USER_RESEARCH_TEST_DB_URL'),'Live rollback-only dashboard query test is opt-in.')
class DashboardDatabaseTests(unittest.TestCase):
    def test_real_aggregates_and_environment_filter_rollback(self):
        import psycopg2
        connection=psycopg2.connect(os.environ['USER_RESEARCH_TEST_DB_URL'],connect_timeout=5)
        sid=str(uuid.uuid4());event_id=str(uuid.uuid4())
        try:
            with connection.cursor() as cur:
                cur.execute("SET LOCAL statement_timeout='5s'")
                before=dashboard.snapshot(cur,'prod',15,50)
                research._write_events(cur,'prod',sid,[{'event_id':event_id,'name':'oracle.completed','scene':'oracle',
                                                     'duration_ms':1200,'source_count':3}])
                research._write_feedback(cur,'prod',sid,{'event_id':str(uuid.uuid4()),'rating':'helpful','category':'answer','comment':'rollback fixture'})
                after=dashboard.snapshot(cur,'prod',15,50)
                self.assertEqual(after['totals']['oracle_completed'],before['totals']['oracle_completed']+1)
                self.assertEqual(after['totals']['feedback'],before['totals']['feedback']+1)
                self.assertNotIn(sid,json.dumps(after))
                with self.assertRaises(research.InputError):dashboard.snapshot(cur,'dev',15,50)
        finally:
            connection.rollback();connection.close()


if __name__=='__main__':unittest.main()
