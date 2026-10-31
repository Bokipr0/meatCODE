# Updated 2026-10-31 · Denver notes: validation, ownership, missing context and retries.
from pathlib import Path
import sys, unittest, uuid, json
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
import user_research as research
class Cursor:
 def __init__(self,rows):self.rows=iter(rows);self.calls=[]
 def execute(self,sql,args):self.calls.append((sql,args))
 def fetchone(self):return next(self.rows)
def uid():return str(uuid.uuid4())
def payload():return dict(session_id=uid(),event_id=uid(),consent=True,consent_version=research.DEMO_VERSION,comment='My note',tester_label='Alex',turn_id=uid(),conversation_id=uid(),anchor_event_id=uid(),elapsed_ms=5500,opened_elapsed_ms=1500)
class NoteTests(unittest.TestCase):
 def write(self,p,rows):
  sid,note,identity=research.validate_note(p);cur=Cursor(rows)
  with patch.object(research,'_session'):
   result=research._write_note(cur,'prod',sid,note,identity,p['consent_version'])
  return result,cur
 def test_owned_anchors_are_saved_without_inventing_a_rating(self):
  p=payload();r,c=self.write(p,[('Alex',),None,(p['session_id'],p['conversation_id'],2),(p['session_id'],'oracle.completed')])
  self.assertTrue(r['ok']);sql,args=c.calls[-1];self.assertIn("NULL,'other'",sql)
  context=json.loads(args[-1]);self.assertEqual(context['turn_id'],p['turn_id']);self.assertEqual(context['anchor_event_id'],p['anchor_event_id']);self.assertEqual(context['opened_elapsed_ms'],1500)
 def test_missing_context_saves_note_but_never_claims_a_link(self):
  p=payload();r,c=self.write(p,[('Alex',),None,None,None]);context=json.loads(c.calls[-1][1][-1]);self.assertEqual(context['turn_status'],'unavailable');self.assertNotIn('turn_id',context);self.assertEqual(context['event_status'],'unavailable')
 def test_cross_session_turn_and_event_are_rejected(self):
  p=payload()
  for rows in [[('Alex',),None,(uid(),p['conversation_id'],1)],[('Alex',),None,(p['session_id'],p['conversation_id'],1),(uid(),'scene.viewed')]]:
   with self.assertRaises(research.InputError):self.write(p,rows)
 def test_retry_is_idempotent_and_cannot_replace_text(self):
  p=payload();r,c=self.write(p,[('Alex',),(p['session_id'],'My note','denver')]);self.assertTrue(r['duplicate']);self.assertFalse(any('INSERT' in q for q,a in c.calls))
  with self.assertRaises(research.InputError):self.write(p,[('Alex',),(p['session_id'],'different','denver')])
 def test_name_and_bounded_text_are_required(self):
  with self.assertRaises(research.InputError):self.write(payload(),[(None,)])
  for text in ['', ' ', 'x'*2001, 'bad\x00text', 4]:
   p=payload();p['comment']=text
   with self.assertRaises(research.InputError):research.validate_note(p)
  p=payload();p['rating']='helpful'
  with self.assertRaises(research.InputError):research.validate_note(p)
if __name__=='__main__':unittest.main()
