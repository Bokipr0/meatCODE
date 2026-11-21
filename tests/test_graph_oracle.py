# Last updated: 2026-11-17 · Codex · graph identity, feedback and isolation regressions.
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
spec=importlib.util.spec_from_file_location('graph_oracle',Path(__file__).parents[1]/'server/graph_oracle.py')
# Also runnable from the staging directory.
if not spec.origin or not Path(spec.origin).exists():
 spec=importlib.util.spec_from_file_location('graph_oracle','/Users/lior/Documents/Claude/Projects/Claude Database/meatCODE/server/graph_oracle.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
FIXTURE='''<graphml xmlns="http://graphml.graphdrawing.org/xmlns"><key id="d" attr.name="description"/><key id="s" attr.name="source_id"/><graph edgedefault="undirected"><node id="ingredient"><data key="d">Ingredient precursor in a fixture process</data><data key="s">chunk-1</data></node><node id="reaction"><data key="d">Fixture ingredient reaction</data><data key="s">chunk-1</data></node><edge id="edge-1" source="ingredient" target="reaction"><data key="d">Fixture connection</data><data key="s">chunk-1</data></edge></graph></graphml>'''
class GraphTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'graph.graphml';self.path.write_text(FIXTURE)
  self.env=patch.dict(os.environ,{'KG_ORACLE_GRAPH_PATH':str(self.path),'KG_ORACLE_STATE_DIR':str(Path(self.tmp.name)/'state')});self.env.start();g.CACHE.clear()
  self.session='tester-session-capability-0123456789';self.owner=g.token(self.session)
 def tearDown(self):self.env.stop();self.tmp.cleanup()
 def model(self,prompt):
  self.prompt=prompt
  return json.dumps({'answer':'Fixture answer [ingredient]','ingredient_question':True,'focus':'Precursors','title':'Fixture process','same_process':True,'stages':{'Precursors':['ingredient','invented'],'Reactions':['reaction']},'relation_ids':['edge-1','fake-edge']})
 def ask(self):return g.dispatch('ask',{'question':'ingredient'},self.session,self.model)['map']
 def test_real_ids_only_and_undirected_semantics(self):
  m=self.ask();self.assertEqual(m['stages']['Precursors'],['ingredient']);self.assertEqual([e['id'] for e in m['edges']],['edge-1']);self.assertFalse(m['edges'][0]['directed'])
 def test_company_question_has_no_map(self):
  result=g.dispatch('ask',{'question':'ingredient companies'},self.session,lambda _:json.dumps({'answer':'No company evidence','ingredient_question':False}))
  self.assertIsNone(result['map'])
 def test_feedback_is_durable_idempotent_and_iterates(self):
  m=self.ask();body={'map_id':m['id'],'comment':'Focus on the precursor','request_id':'feedback-request-0123456789'}
  first=g.dispatch('feedback',body,self.session,self.model)['map'];second=g.dispatch('feedback',body,self.session,self.model)['map']
  state=g.state_read();self.assertEqual(state['revision'],1);self.assertEqual(len(state['feedback']),1);self.assertEqual(len(state['graph_updates']['nodes']),1);self.assertEqual(len(state['graph_updates']['edges']),2);self.assertEqual(first['parent_id'],m['id']);self.assertEqual(first['family_id'],m['family_id']);self.assertEqual(first['feedback_revision'],second['feedback_revision']);self.assertEqual(self.path.read_text(),FIXTURE)
 def test_feedback_survives_model_failure(self):
  m=self.ask()
  def failed(_):raise RuntimeError('model offline')
  with self.assertRaises(RuntimeError):g.dispatch('feedback',{'map_id':m['id'],'comment':'Correction','request_id':'feedback-request-0123456789'},self.session,failed)
  self.assertEqual(g.state_read()['revision'],1)
 def test_map_session_ownership(self):
  m=self.ask()
  with self.assertRaises(ValueError):g.dispatch('ask',{'question':'ingredient','map_id':m['id']},'different-session-capability-0123456789',self.model)
 def test_feedback_cannot_reference_unknown_entity(self):
  m=self.ask()
  with self.assertRaises(ValueError):g.dispatch('feedback',{'map_id':m['id'],'comment':'Correction','entity_ids':['forged'],'request_id':'feedback-request-0123456789'},self.session,self.model)
 def test_no_match_does_not_call_model(self):
  r=g.dispatch('ask',{'question':'zzzzzzz'},self.session,lambda _:self.fail('model should not run'))
  self.assertIsNone(r['map'])
 def test_fork_retains_map_lineage(self):
  m=self.ask();next_map=g.dispatch('ask',{'question':'reaction','map_id':m['id']},self.session,self.model)['map'];self.assertEqual(next_map['parent_id'],m['id'])
if __name__=='__main__':unittest.main()
