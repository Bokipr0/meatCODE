# Last updated: 2026-10-29 · Journey capture · consent, separation, time bounds and rollback-only identity tests.
from pathlib import Path
import os,sys,uuid,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
import user_research as research

def refs():return {'user_ref':str(uuid.uuid4()),'clarity_ref':str(uuid.uuid4()),'tester_label':'Tester seven'}
def event_payload():return {'session_id':str(uuid.uuid4()),'consent':True,'consent_version':research.CONSENT_VERSION,'events':[{'event_id':str(uuid.uuid4()),'name':'module.clicked','scene':'inventory','elapsed_ms':4321,'properties':{}}],**refs()}
def chat_payload():
 p=event_payload();p.pop('events');p.update(full_chat_consent=True,turn_id=str(uuid.uuid4()),conversation_id=str(uuid.uuid4()),turn_index=1,question='Synthetic private input',answer='',status='submitted',revision=0,source_ids=[],truncated=False,elapsed_ms=4321);return p

class JourneyValidationTests(unittest.TestCase):
 def test_clicks_have_allowlisted_target_and_bounded_elapsed_time(self):
  p=event_payload();sid,events=research.validate_events(p);self.assertEqual(events[0]['scene'],'inventory');self.assertEqual(events[0]['elapsed_ms'],4321)
  for value in (-1,86400001,True,'7',1.5):
   p=event_payload();p['events'][0]['elapsed_ms']=value
   with self.assertRaises(research.InputError):research.validate_events(p)
  for name,scene in (('any.click','inventory'),('module.clicked','sensitive raw text')):
   p=event_payload();p['events'][0].update(name=name,scene=scene)
   with self.assertRaises(research.InputError):research.validate_events(p)
 def test_references_are_not_deletion_capability_and_are_distinct(self):
  for change in ('user_ref','clarity_ref','same'):
   p=event_payload()
   if change=='same':p['clarity_ref']=p['user_ref']
   else:p[change]=p['session_id']
   with self.assertRaises(research.InputError):research.validate_events(p)
 def test_optional_label_is_explicit_and_bounded(self):
  p=event_payload();p['tester_label']=''
  self.assertIsNone(research._journey(p,p['session_id'])['tester_label'])
  for value in ('x'*81,'bad\nlabel',{},True):
   p=event_payload();p['tester_label']=value
   with self.assertRaises(research.InputError):research.validate_events(p)
 def test_legacy_chat_is_accepted_without_relabelling_or_fabricated_time(self):
  p=chat_payload();p['consent_version']='2026-10-29-chat-v1'
  for field in ('user_ref','clarity_ref','tester_label','elapsed_ms'):p.pop(field)
  sid,turn=research.validate_chat(p);self.assertEqual(turn['consent_version'],'2026-10-29-chat-v1');self.assertIsNone(turn['elapsed_ms']);self.assertNotIn('user_ref',turn)
  p['user_ref']=str(uuid.uuid4())
  with self.assertRaises(research.InputError):research.validate_chat(p)
 def test_feedback_gets_elapsed_and_joins_existing_session_references(self):
  p=event_payload();p.pop('events');p.update(event_id=str(uuid.uuid4()),rating='helpful',category='usability',comment='Synthetic feedback',elapsed_ms=9876)
  sid,data=research.validate_feedback(p);self.assertEqual(data['elapsed_ms'],9876)
  self.assertNotIn('user_ref',data) # identities live only once, on the session

@unittest.skipUnless(os.environ.get('USER_RESEARCH_TEST_DB_URL'),'Rollback-only journey database checks are opt-in.')
class JourneyDatabaseTests(unittest.TestCase):
 def setUp(self):
  import psycopg2
  self.conn=psycopg2.connect(os.environ['USER_RESEARCH_TEST_DB_URL'],connect_timeout=5);self.cur=self.conn.cursor();self.cur.execute("SET LOCAL statement_timeout='5s'; SET LOCAL lock_timeout='3s'")
 def tearDown(self):self.conn.rollback();self.conn.close()
 def test_reference_immutability_join_and_erase(self):
  p=chat_payload();sid,turn=research.validate_chat(p);research._write_chat(self.cur,'prod',sid,turn)
  self.cur.execute('SELECT s.user_ref,s.clarity_ref,s.tester_label,t.elapsed_ms,t.consent_version FROM user_research.oracle_turns t JOIN user_research.sessions s USING(session_id,environment) WHERE t.turn_id=%s AND t.environment=%s',(p['turn_id'],'prod'))
  row=self.cur.fetchone();self.assertEqual(tuple(map(str,row[:2])),(p['user_ref'],p['clarity_ref']));self.assertEqual(row[2:],('Tester seven',4321,research.CONSENT_VERSION))
  with self.assertRaises(research.InputError):research._session(self.cur,'prod',sid,{'user_ref':str(uuid.uuid4())})
  research._withdraw(self.cur,'prod',sid);self.cur.execute('SELECT count(*) FROM user_research.oracle_turns WHERE session_id=%s AND environment=%s',(sid,'prod'));self.assertEqual(self.cur.fetchone()[0],0)
 def test_old_chat_consent_is_stored_as_old_and_time_unknown(self):
  p=chat_payload();p['consent_version']='2026-10-29-chat-v1'
  for field in ('user_ref','clarity_ref','tester_label','elapsed_ms'):p.pop(field)
  sid,turn=research.validate_chat(p);research._write_chat(self.cur,'prod',sid,turn)
  self.cur.execute('SELECT t.consent_version,s.consent_version,t.elapsed_ms,s.user_ref FROM user_research.oracle_turns t JOIN user_research.sessions s USING(session_id,environment) WHERE t.turn_id=%s AND t.environment=%s',(p['turn_id'],'prod'))
  self.assertEqual(self.cur.fetchone(),('2026-10-29-chat-v1','2026-10-29-chat-v1',None,None))

if __name__=='__main__':unittest.main()
