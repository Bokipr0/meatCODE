# Last updated: 2026-11-21 22:45 UTC · Claude (Opus 5.5) · hosted LightRAG source: auth header, mapping, truncation flag, URL/key guards, no write-back
import importlib.util, json, os, sys, tempfile, threading, unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'server'))
spec = importlib.util.spec_from_file_location('graph_oracle_remote_t', Path(__file__).parents[1] / 'server/graph_oracle.py')
g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)
KEY = 'k' * 48
PAYLOAD = {'nodes': [
    {'id': 'Ingredient', 'labels': ['Ingredient'], 'properties': {'entity_id': 'Ingredient', 'entity_type': 'chemical', 'description': 'Ingredient precursor', 'source_id': 'chunk-1<SEP>chunk-2', 'file_path': '/x/paperA.pdf'}},
    {'id': 'Reaction', 'labels': ['Reaction'], 'properties': {'entity_id': 'Reaction', 'entity_type': 'process', 'description': 'Ingredient reaction', 'source_id': 'chunk-1'}},
    {'id': 'note', 'labels': ['note'], 'properties': {'entity_type': 'MEATCODE_FEEDBACK'}}],
  'edges': [{'id': 'Ingredient-Reaction', 'type': 'DIRECTED', 'source': 'Ingredient', 'target': 'Reaction', 'properties': {'description': 'links', 'keywords': 'k', 'source_id': 'chunk-1'}},
            {'id': 'note-Ingredient', 'type': 'DIRECTED', 'source': 'note', 'target': 'Ingredient', 'properties': {}}],
  'is_truncated': True}
SEEN = []
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        SEEN.append((self.path, self.headers.get('X-API-Key')))
        if self.headers.get('X-API-Key') != KEY:
            self.send_response(403); self.end_headers(); return
        body = json.dumps(PAYLOAD).encode(); self.send_response(200)
        self.send_header('Content-Type', 'application/json'); self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass
class RemoteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(('127.0.0.1', 0), H); threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.url = 'http://127.0.0.1:%d' % cls.srv.server_port
    @classmethod
    def tearDownClass(cls): cls.srv.shutdown()
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); g.CACHE.clear(); SEEN.clear()
        self.env = patch.dict(os.environ, {'KG_ORACLE_REMOTE_URL': self.url, 'KG_ORACLE_REMOTE_API_KEY': KEY, 'KG_ORACLE_STATE_DIR': self.tmp.name}, clear=False)
        self.env.start(); os.environ.pop('KG_ORACLE_GRAPH_PATH', None); os.environ.pop('KG_ORACLE_LIGHTRAG_URL', None)
    def tearDown(self): self.env.stop(); self.tmp.cleanup()
    def test_status_maps_graph_and_flags_truncation(self):
        s = g.dispatch('status', {}, '', None)
        self.assertTrue(s['ready']); self.assertEqual((s['nodes'], s['connections']), (2, 1))
        self.assertEqual(s['source'], 'hosted_lightrag_graph'); self.assertTrue(s['graph_truncated'])
        self.assertEqual(s['feedback_annotations'], 1); self.assertEqual(s['feedback_target'], 'provenance_overlay_only')
        self.assertIn('label=%2A', SEEN[0][0]); self.assertIn('max_nodes=20000', SEEN[0][0])
    def test_edges_are_undirected_and_cached(self):
        d = g.graph(); g.graph()
        self.assertFalse(d['edges']['Ingredient-Reaction']['directed']); self.assertEqual(d['nodes']['Ingredient']['papers'], ['paperA.pdf'])
        self.assertEqual(len(SEEN), 1)
    def test_ask_uses_hosted_records_only(self):
        session = 'tester-session-capability-0123456789'
        model = lambda p: json.dumps({'answer': 'ok [Ingredient]', 'ingredient_question': True, 'focus': 'Precursors', 'title': 't',
                                      'stages': {'Precursors': ['Ingredient', 'Invented'], 'Reactions': ['Reaction']}, 'relation_ids': ['Ingredient-Reaction']})
        m = g.dispatch('ask', {'question': 'ingredient'}, session, model)['map']
        self.assertEqual(m['stages']['Precursors'], ['Ingredient']); self.assertEqual(m['source'], 'hosted_lightrag_graph')
    def test_wrong_key_is_a_clear_error(self):
        with patch.dict(os.environ, {'KG_ORACLE_REMOTE_API_KEY': 'x' * 40}):
            s = g.dispatch('status', {}, '', None)
        self.assertFalse(s['ready']); self.assertIn('HTTP 403', s['message'])
    def test_refuses_plain_http_remote_short_key_and_embedded_creds(self):
        for url, key in (('http://kg.example.com', KEY), ('https://kg.example.com', 'short'), ('https://u:p@kg.example.com', KEY)):
            with patch.dict(os.environ, {'KG_ORACLE_REMOTE_URL': url, 'KG_ORACLE_REMOTE_API_KEY': key}):
                self.assertFalse(g.dispatch('status', {}, '', None)['ready'])
        self.assertEqual(SEEN, [])
if __name__ == '__main__': unittest.main()
