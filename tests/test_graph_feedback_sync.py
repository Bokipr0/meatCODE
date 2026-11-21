# Last updated: 2026-11-18 · Codex · native graph feedback outbox regressions.
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
import graph_oracle as g
import graph_feedback_sync as sync

GRAPH='''<graphml xmlns="http://graphml.graphdrawing.org/xmlns"><graph edgedefault="undirected"><node id="ingredient"/><node id="reaction"/></graph></graphml>'''
class Writer:
    def __init__(self):self.nodes={};self.edges={};self.fail=False
    def ready(self):
        if self.fail:raise sync.PendingSync('Service busy')
    def upsert_node(self,name,values):self.nodes[name]=values
    def upsert_edge(self,source,target,values):self.edges[(source,target)]=values
    def verify(self,name,targets):
        assert name in self.nodes
        assert all((name,t) in self.edges for t in targets)

class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.path=self.root/'graph.graphml';self.path.write_text(GRAPH)
        self.env=patch.dict(os.environ,{'KG_ORACLE_GRAPH_PATH':str(self.path),'KG_ORACLE_STATE_DIR':str(self.root/'state'),'KG_ORACLE_LIGHTRAG_URL':'http://127.0.0.1:9621'})
        self.env.start();g.CACHE.clear()
        self.feedback=dict(id='feedback-test-123',request_id='retry-id',owner='private-owner',comment='Keep the precursor context visible.',entity_ids=['ingredient','reaction'],map_id='map-1',source_graph_version='version-1',revision=1,provenance='user_feedback',evidence_state='unverified')
        g.state_write({'maps':{},'feedback':[self.feedback],'revision':1})
    def tearDown(self):self.env.stop();self.temp.cleanup()
    def test_native_node_edges_wiki_and_completed_outbox(self):
        writer=Writer();self.assertTrue(sync.sync_pending_once(g,writer))
        self.assertEqual(len(writer.nodes),1);self.assertEqual(len(writer.edges),2)
        node=next(iter(writer.nodes.values()))
        self.assertEqual(node['entity_type'],'MEATCODE_FEEDBACK');self.assertEqual(node['source_id'],'')
        page=Path(node['file_path']).read_text();self.assertIn('unverified user feedback',page);self.assertIn('version-1',page);self.assertNotIn('private-owner',page)
        self.assertEqual(g.state_read()['feedback'][0]['native_sync']['status'],'synced')
        self.assertFalse(sync.sync_pending_once(g,writer))
        self.assertEqual(self.path.read_text(),GRAPH)
    def test_busy_is_retryable_without_losing_contribution(self):
        writer=Writer();writer.fail=True;sync.sync_pending_once(g,writer)
        state=g.state_read();self.assertEqual(len(state['feedback']),1);self.assertEqual(state['feedback'][0]['native_sync']['status'],'pending')
        self.assertEqual(writer.nodes,{})
        state['feedback'][0]['native_sync']['retry_at']=0;g.state_write(state)
        writer.fail=False;self.assertTrue(sync.sync_pending_once(g,writer));self.assertEqual(sync.status(g.state_read()['feedback'])['pending'],0)
    def test_partial_write_retries_with_same_annotation_id(self):
        writer=Writer();real=writer.upsert_edge
        def fail(*args):raise sync.PendingSync('temporary embedding failure')
        writer.upsert_edge=fail;sync.sync_pending_once(g,writer)
        state=g.state_read();state['feedback'][0]['native_sync']['retry_at']=0;g.state_write(state)
        writer.upsert_edge=real;sync.sync_pending_once(g,writer)
        self.assertEqual(len(writer.nodes),1);self.assertEqual(len(writer.edges),2)
    def test_private_sync_metadata_excluded_from_reasoner(self):
        sync.sync_pending_once(g,Writer());result=g.select('ingredient',g.graph(),g.state_read()['feedback'])
        self.assertNotIn('native_sync',result['feedback'][0]);self.assertNotIn('owner',result['feedback'][0])
    def test_native_feedback_nodes_excluded_from_scientific_stages(self):
        self.path.write_text('''<graphml xmlns="http://graphml.graphdrawing.org/xmlns"><key id="t" attr.name="entity_type"/><graph edgedefault="undirected"><node id="ingredient"/><node id="annotation"><data key="t">MEATCODE_FEEDBACK</data></node><edge source="annotation" target="ingredient"/></graph></graphml>''')
        graph=g.graph();self.assertEqual(graph['annotation_count'],1);self.assertNotIn('annotation',graph['nodes']);self.assertFalse(graph['edges'])
    def test_remote_destination_rejected(self):
        with self.assertRaises(sync.PendingSync):sync.LightRAGWriter('https://example.com',self.root)
    def test_wrong_graph_directory_blocks_writes(self):
        writer=sync.LightRAGWriter('http://127.0.0.1:9621',self.root)
        writer.request=lambda *_:{'status':'healthy','working_directory':'/different/store'}
        with self.assertRaises(sync.PendingSync):writer.ready()
    def test_pipeline_busy_blocks_writes(self):
        writer=sync.LightRAGWriter('http://127.0.0.1:9621',self.root)
        def request(path,*_):
            return {'status':'healthy','working_directory':str(self.root),'configuration':{}} if path=='/health' else {'busy':True}
        writer.request=request
        with self.assertRaises(sync.PendingSync):writer.ready()
if __name__=='__main__':unittest.main()
