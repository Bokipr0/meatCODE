# Last updated: 2026-10-29 · Production-only intake, internal/browser exclusions and automation guards.
from email.message import Message
import io,json,subprocess,unittest
from pathlib import Path
from server import research_http as http


class Research:
 class InputError(ValueError):pass
 class WithdrawnError(Exception):pass
 def __init__(self):self.writes=[];self.config_calls=0
 def config(self,env,app_env):
  self.config_calls+=1
  return {'enabled':True,'environment':app_env,'demo_mode':True,'consent_version':'2026-10-29-demo-v1','retention_days':90,'clarity_project_id':'public-project','posthog':{'enabled':True,'project_token':'phc_public_fixture','api_host':'https://eu.i.posthog.com'}}
 def write_events(self,*args):self.writes.append(('events',args));return {'ok':True}
 def write_chat(self,*args):self.writes.append(('chat',args));return {'ok':True}
 def write_feedback(self,*args):self.writes.append(('feedback',args));return {'ok':True}
 def withdraw(self,*args):self.writes.append(('withdraw',args));return {'ok':True}


class ReadSpy(io.BytesIO):
 def __init__(self,value):super().__init__(value);self.reads=0
 def read(self,*args):self.reads+=1;return super().read(*args)


class Handler:
 def __init__(self,path,extra=None):
  self.path=path;self.headers=Message();self.wfile=io.BytesIO();self.rfile=ReadSpy(b'{}');self.close_connection=False;self.status=None
  for name,value in {'Host':'example.test','Origin':'https://example.test','Sec-Fetch-Site':'same-origin','Content-Type':'application/json','Content-Length':'2','X-MeatCODE-Research':'1',**(extra or {})}.items():self.headers[name]=value
 def send_response(self,status):self.status=status
 def send_header(self,*args):pass
 def end_headers(self):pass
 def result(self):return json.loads(self.wfile.getvalue())


class ProductionIntakeTests(unittest.TestCase):
 def setUp(self):
  self.module=Research()
  with http._capture_lock:http._captures.clear()
 def call(self,environment='prod',route='events',extra=None,config=False):
  h=Handler('/api/research/'+('config' if config else route),extra)
  http.handle(h,'GET' if config else 'POST',h.path,self.module,'misconfigured-private-storage',environment,{'USER_RESEARCH_ENABLED':'true','USER_RESEARCH_DEMO_MODE':'true'},True)
  return h
 def test_nonproduction_never_writes_even_when_all_settings_enable_it(self):
  for env in ('dev','local','staging'):
   for route in ('events','chat','feedback','withdraw'):
    with self.subTest(environment=env,route=route):
     h=self.call(env,route);self.assertEqual(h.status,404);self.assertEqual(h.rfile.reads,0)
  self.assertEqual(self.module.writes,[]);self.assertEqual(self.module.config_calls,0)
 def test_development_public_config_disables_providers_and_demo(self):
  h=self.call('dev',config=True);d=h.result();self.assertEqual(h.status,200);self.assertFalse(d['enabled']);self.assertFalse(d['demo_mode']);self.assertEqual(d['capture_excluded'],'nonproduction');self.assertFalse(d['posthog']['enabled']);self.assertEqual(d['posthog']['project_token'],'');self.assertEqual(d['clarity_project_id'],'');self.assertEqual(self.module.writes,[])
 def test_ordinary_production_browser_can_capture(self):
  h=self.call(extra={'User-Agent':'Mozilla/5.0 (Macintosh) AppleWebKit/605.1.15 Version/18.0 Safari/605.1.15'})
  self.assertEqual(h.status,200);self.assertEqual(self.module.writes[0][0],'events')
  d=self.call(config=True).result();self.assertTrue(d['enabled']);self.assertEqual(d['capture_excluded'],'')
 def test_internal_cookie_and_header_block_before_parsing_or_storage(self):
  for extra in ({'Cookie':'ordinary=value; __Host-mc_research_internal=1'},{'X-MeatCODE-Internal':'1'}):
   for route in ('events','chat','feedback'):
    h=self.call(route=route,extra=extra);self.assertEqual(h.status,404);self.assertEqual(h.rfile.reads,0)
   d=self.call(extra=extra,config=True).result();self.assertFalse(d['enabled']);self.assertEqual(d['capture_excluded'],'internal');self.assertFalse(d['demo_mode'])
  self.assertEqual(self.module.writes,[])
 def test_internal_setting_is_not_an_authentication_or_other_cookie_match(self):
  for cookie in ('mc_research_internal=1','__Host-mc_research_internal=0','other=__Host-mc_research_internal%3D1'):
   self.assertTrue(self.call(extra={'Cookie':cookie},config=True).result()['enabled'])
 def test_recognized_automation_is_disabled_without_retaining_user_agent(self):
  for agent in ('Googlebot/2.1','Mozilla/5.0 compatible Bingbot/2.0','Mozilla/5.0 HeadlessChrome/131.0','Playwright','python-requests/2.31','Python-urllib/3.11','curl/8.0','Wget/1.21'):
   with self.subTest(agent=agent):
    h=self.call(extra={'User-Agent':agent});self.assertEqual(h.status,404);self.assertEqual(h.rfile.reads,0)
    d=self.call(extra={'User-Agent':agent},config=True).result();self.assertFalse(d['enabled']);self.assertEqual(d['capture_excluded'],'automation');self.assertNotIn(agent,json.dumps(d))
  self.assertEqual(self.module.writes,[])
 def test_production_deletion_stays_available_for_excluded_browsers(self):
  h=self.call(route='withdraw',extra={'Cookie':'__Host-mc_research_internal=1','User-Agent':'HeadlessChrome/131.0'})
  self.assertEqual(h.status,200);self.assertEqual(self.module.writes[0][0],'withdraw')
 def test_webdriver_runtime_never_initializes_capture_or_providers(self):
  source=Path(__file__).resolve().parents[1]/'app/assets/user-research.js'
  script="const vm=require('node:vm'),fs=require('node:fs');const forbidden=new Proxy({}, {get(){throw Error('automation accessed browser collection')}});let context={window:{},navigator:{webdriver:true},document:forbidden,fetch(){throw Error('automation performed network')}};vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),context);if(context.window.MCResearch)throw Error('automation initialized capture');"
  result=subprocess.run(['node','-e',script,str(source)],capture_output=True,text=True,timeout=10)
  self.assertEqual(result.returncode,0,result.stderr)

if __name__=='__main__':unittest.main()
