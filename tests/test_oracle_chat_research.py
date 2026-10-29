# Last updated: 2026-10-29 · Codex · explicit chat consent, immutable turns, ordering and erasure.
from pathlib import Path
import sys,os,uuid,unittest
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'server')]
import user_research as research
import research_dashboard as dashboard


def payload():
 return {'session_id':str(uuid.uuid4()),'consent':True,'consent_version':research.CONSENT_VERSION,'full_chat_consent':True,'turn_id':str(uuid.uuid4()),'conversation_id':str(uuid.uuid4()),'turn_index':1,'question':'<private question>','answer':'','status':'submitted','revision':0,'source_ids':[],'truncated':False}


class ValidationTests(unittest.TestCase):
 def test_new_explicit_chat_consent_is_mandatory(self):
  for change in ({'full_chat_consent':False},{'full_chat_consent':1},{'consent_version':'2026-10-29'},{'consent':False}):
   p=payload();p.update(change)
   with self.assertRaises(research.InputError):research.validate_chat(p)
 def test_text_identity_and_citations_are_bounded(self):
  for change in ({'question':''},{'question':'x'*12001},{'answer':'x'*64001},{'revision':True},{'source_ids':[True]},{'source_ids':list(range(1,102))},{'question':'bad\x00text'},{'prompt':'extra'},{'truncated':1}):
   p=payload();p.update(change)
   with self.assertRaises(research.InputError):research.validate_chat(p)
  p=payload();p['answer']='a'*64000;research.validate_chat(p)
 def test_transcript_query_is_private_and_bounded(self):
  self.assertEqual(dashboard.parameters('/api/research/dashboard?minutes=129600','prod'),('prod',129600,50))
  cid=str(uuid.uuid4());self.assertEqual(dashboard.transcript_parameters('/api/research/transcript?conversation='+cid,'prod'),('prod',cid,0,20))
  for suffix in ('&limit=21','&after=-1','&after=1&after=2','&session_id=private'):
   with self.assertRaises(research.InputError):dashboard.transcript_parameters('/api/research/transcript?conversation='+cid+suffix,'prod')


@unittest.skipUnless(os.environ.get('USER_RESEARCH_TEST_DB_URL'),'Rollback-only database checks are opt-in.')
class DatabaseTests(unittest.TestCase):
 def setUp(self):
  import psycopg2
  self.conn=psycopg2.connect(os.environ['USER_RESEARCH_TEST_DB_URL'],connect_timeout=5);self.cur=self.conn.cursor();self.cur.execute("SET LOCAL statement_timeout='5s'; SET LOCAL lock_timeout='3s'")
  self.p=payload();self.sid,self.turn=research.validate_chat(self.p)
 def tearDown(self):self.conn.rollback();self.conn.close()
 def test_terminal_response_cannot_be_overwritten_by_delayed_checkpoints(self):
  research._write_chat(self.cur,'dev',self.sid,self.turn)
  final=dict(self.turn,status='complete',revision=2,answer='actual answer',source_ids=[1,2]);research._write_chat(self.cur,'dev',self.sid,final)
  research._write_chat(self.cur,'dev',self.sid,dict(self.turn,revision=1,answer='partial'))
  self.cur.execute('SELECT status,answer,revision FROM user_research.oracle_turns WHERE turn_id=%s AND environment=%s',(self.turn['turn_id'],'dev'))
  self.assertEqual(self.cur.fetchone(),('complete','actual answer',2))
 def test_conversation_ownership_identity_and_withdrawal(self):
  research._write_chat(self.cur,'dev',self.sid,self.turn)
  with self.assertRaises(research.InputError):research._write_chat(self.cur,'dev',self.sid,dict(self.turn,question='different'))
  with self.assertRaises(research.InputError):research._write_chat(self.cur,'dev',str(uuid.uuid4()),dict(self.turn,turn_id=str(uuid.uuid4()),turn_index=2))
  research._withdraw(self.cur,'dev',self.sid)
  self.cur.execute('SELECT count(*) FROM user_research.oracle_turns WHERE session_id=%s AND environment=%s',(self.sid,'dev'));self.assertEqual(self.cur.fetchone()[0],0)
  with self.assertRaises(research.WithdrawnError):research._write_chat(self.cur,'dev',self.sid,self.turn)
 def test_whole_conversation_pages_preserve_turn_order_and_environment(self):
  research._write_chat(self.cur,'dev',self.sid,self.turn)
  research._write_chat(self.cur,'dev',self.sid,dict(self.turn,turn_id=str(uuid.uuid4()),turn_index=2,status='clarification',answer='Which temperature?'))
  first=dashboard.transcript(self.cur,'dev',self.turn['conversation_id'],0,1);self.assertTrue(first['has_more']);self.assertEqual(first['next_after'],1)
  second=dashboard.transcript(self.cur,'dev',self.turn['conversation_id'],first['next_after'],1);self.assertEqual(second['turns'][0]['index'],2);self.assertFalse(second['has_more'])
  self.assertNotIn(self.sid,str(first));self.assertEqual(dashboard.transcript(self.cur,'prod',self.turn['conversation_id'])['turns'],[])

if __name__=='__main__':unittest.main()
