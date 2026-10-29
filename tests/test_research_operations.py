# Last updated: 2026-10-29 · Backend · scoped monitoring commands and private journey safety.
from contextlib import contextmanager
from email.message import Message
from pathlib import Path
import datetime,io,json,sys,unittest,uuid
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
import research_operations as operations
import research_dashboard as dashboard
import user_research as research


class Handler:
    def __init__(self,payload=None,token='t'*48,origin='https://example.test'):
        body=json.dumps(payload or {'command':'status','environment':'prod','minutes':60}).encode()
        self.headers=Message();self.path='/api/research/operations';self.rfile=io.BytesIO(body);self.wfile=io.BytesIO();self.close_connection=False;self.status=None;self.response_headers={}
        for key,value in {'Host':'example.test','Origin':origin,'Content-Type':'application/json','Content-Length':str(len(body)),'X-MeatCODE-Research':'1','X-MeatCODE-Research-Admin':token}.items():
            if value is not None:self.headers[key]=value
    def send_response(self,status):self.status=status
    def send_header(self,key,value):self.response_headers[key]=value
    def end_headers(self):pass
    def result(self):return json.loads(self.wfile.getvalue())


class OperationsTests(unittest.TestCase):
    def test_only_monitoring_vocabulary_is_accepted(self):
        for payload in ({'command':'ls'},{'command':'status; curl evil'},{'command':'SELECT * FROM sessions'},{'command':'status','sql':'DROP TABLE'},{'command':'status','url':'https://evil.test'},{'command':'status','environment':'all'},{'command':'status','environment':[]},{'command':'status','minutes':True},{'command':'status','minutes':12}):
            with self.assertRaises(research.InputError):operations.parameters(payload,'prod')
        self.assertEqual(operations.parameters({'command':'errors'},'dev'),('errors','dev',60))

    def test_admin_and_same_origin_remain_mandatory(self):
        for token,origin in ((None,'https://example.test'),('wrong','https://example.test'),('t'*48,'https://other.test')):
            h=Handler(token=token,origin=origin)
            with patch.object(operations,'status') as status:
                operations.handle(h,'fake-db','dev',{'RENDER':'true','RESEARCH_ADMIN_TOKEN':'t'*48,'RESEARCH_PRODUCTION_DATABASE_URL':'readonly-db'})
            self.assertEqual(h.status,403);status.assert_not_called();self.assertEqual(h.rfile.tell(),0)
        h=Handler();del h.headers['X-MeatCODE-Research']
        with patch.object(operations,'status') as status:operations.handle(h,'fake-db','prod',{'RESEARCH_ADMIN_TOKEN':'t'*48})
        self.assertEqual(h.status,403);status.assert_not_called()

    def test_production_access_from_dev_needs_explicit_read_connection(self):
        for allowed in (False,True):
            h=Handler();env={'RENDER':'true','RESEARCH_ADMIN_TOKEN':'t'*48}
            if allowed:env['RESEARCH_PRODUCTION_DATABASE_URL']='private-readonly-db'
            with patch.object(operations,'status',return_value={'mode':'read_only'}) as status:
                operations.handle(h,'dev-db','dev',env)
            self.assertEqual(h.status,200 if allowed else 400)
            self.assertNotIn('private-readonly-db',h.wfile.getvalue().decode())
            self.assertEqual(status.called,allowed)

    def test_status_exposes_only_public_allowlisted_configuration(self):
        version={'env':'prod','commit_full':'a'*40,'server_started_utc':'2026-10-29T17:00:00+00:00','model':'claude-sonnet-4-6','token':'private-credential','connection_string':'postgresql://private'}
        with patch.object(operations,'_public_json',side_effect=[version,{'db_ok':True,'has_anthropic_key':True,'api_key':'private-secret'}]):result=operations.status('prod')
        self.assertEqual(result['checks']['scope'],'configuration_only');self.assertEqual(result['mode'],'read_only')
        self.assertNotIn('private',json.dumps(result));self.assertEqual(result['revision'],'a'*40)
        with self.assertRaises(research.InputError):operations._public_json('prod','https://evil.test')

    def test_error_feed_is_metadata_only_bounded_and_parameterized(self):
        sid=uuid.uuid4();created=datetime.datetime.now(datetime.timezone.utc)
        class Cursor:
            def execute(self,query,args):self.query,self.args=query,args
            def fetchall(self):return [(uuid.uuid4(),'oracle.failed','oracle',created,300,'model_unavailable',0,sid,1000)]
        cur=Cursor();result=operations.activity(cur,'prod',60,True)
        self.assertIn("name='oracle.failed'",cur.query);self.assertIn('LIMIT 50',cur.query);self.assertNotIn('prod',cur.query);self.assertEqual(cur.args[0],'prod')
        self.assertNotIn(str(sid),json.dumps(result));self.assertNotIn('question',cur.query);self.assertNotIn('answer',cur.query)

    def test_errors_never_return_connection_or_exception_details(self):
        h=Handler({'command':'activity','environment':'prod'})
        with patch.object(dashboard,'readonly',side_effect=RuntimeError('postgresql://private-token')):
            operations.handle(h,'fake-db','prod',{'RESEARCH_ADMIN_TOKEN':'t'*48})
        self.assertEqual(h.status,503);self.assertNotIn('postgresql',h.wfile.getvalue().decode())


class JourneyTests(unittest.TestCase):
    def test_journey_exposes_requested_fields_without_capability(self):
        now=datetime.datetime(2026,10,29,12,0,tzinfo=datetime.timezone.utc);sid=uuid.uuid4();user=uuid.uuid4();clarity=uuid.uuid4()
        class Cursor:
            def execute(self,query,args):self.query,self.args=query,args
            def fetchall(self):return [('turn','oracle.input',now,user,'Tester A','submitted question',12345,clarity,'conversation','complete',sid),('old','feedback.input',now,None,None,'helpful',None,None,None,'submitted',sid)]
        cur=Cursor();result=dashboard.journey(cur,'prod',60,2,now)
        row=result['rows'][0];self.assertEqual((row['date'],row['user_ref'],row['input'],row['elapsed_ms']),('2026-10-29',str(user),'submitted question',12345))
        self.assertEqual(row['clarity_ref'],str(clarity));self.assertNotIn(str(sid),json.dumps(result));self.assertIsNone(result['rows'][1]['elapsed_ms']);self.assertTrue(result['rows'][1]['user_ref'].startswith('s_'))
        self.assertEqual(cur.args[-1],2);self.assertEqual(cur.args[0],'prod');self.assertEqual(cur.args[3],'prod');self.assertNotIn('prod',cur.query)

    def test_dedicated_storage_never_falls_back_when_required(self):
        with self.assertRaises(research.StorageError):dashboard._database_settings('prod','prod',{'RENDER':'true','RESEARCH_DATABASE_REQUIRED':'true'},'scientific-db',False)
        chosen,_=dashboard._database_settings('prod','prod',{'RENDER':'true','RESEARCH_DATABASE_URL':'research-db'},'scientific-db',False);self.assertEqual(chosen,'research-db')
        with self.assertRaises(research.InputError):dashboard._database_settings('dev','prod',{'RENDER':'true','RESEARCH_PRODUCTION_DATABASE_URL':'wrong-direction'},'production-db',False)
        with patch.object(dashboard,'_local_settings',side_effect=[{'RESEARCH_DATABASE_URL':'dev-research','RESEARCH_DATABASE_REQUIRED':'true'},{'RESEARCH_DATABASE_REQUIRED':'true'}]):
            self.assertEqual(dashboard._database_settings('dev','dev',{},None,True)[0],'dev-research')
        self.assertTrue(dashboard.can_select_environment('dev',{'RENDER':'true','RESEARCH_PRODUCTION_DATABASE_URL':'read-only'}));self.assertFalse(dashboard.can_select_environment('prod',{'RENDER':'true'}))

if __name__=='__main__':unittest.main()
