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
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get('Content-Length', '0')))
        SEEN.append((self.path, self.headers.get('X-API-Key'), json.loads(body)))
        if QUERY['data'] is None or self.headers.get('X-API-Key') != KEY:
            self.send_response(500); self.end_headers(); return
        out = json.dumps({'status': 'success', 'data': QUERY['data']}).encode(); self.send_response(200)
        self.send_header('Content-Type', 'application/json'); self.end_headers(); self.wfile.write(out)
    def log_message(self, *a): pass
QUERY = {'data': None}
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
    def test_ask_retrieves_through_lightrag_and_keeps_passages_server_side(self):
        QUERY['data'] = {'entities': [{'entity_name': 'Reaction'}, {'entity_name': 'Not in graph'}],
                         'relationships': [{'src_id': 'Reaction', 'tgt_id': 'Ingredient'}],
                         'chunks': [{'content': 'PASSAGE-TEXT about browning', 'file_path': '/x/paperA.pdf'}]}
        prompts = []
        def model(p):
            prompts.append(p)
            return json.dumps({'answer': 'ok [Reaction]', 'ingredient_question': True, 'focus': 'Reactions', 'title': 't',
                               'stages': {'Precursors': ['Ingredient'], 'Reactions': ['Reaction']}, 'relation_ids': ['Ingredient-Reaction']})
        try:
            out = g.dispatch('ask', {'question': 'zzzz qqqq'}, 'tester-session-capability-0123456789', model)   # no keyword match
        finally:
            QUERY['data'] = None
        self.assertEqual(out['retrieval'], 'lightrag_query'); self.assertEqual(len(out['map']['edges']), 1)
        self.assertEqual(sorted(n['id'] for n in out['evidence']), ['Ingredient', 'Reaction'])
        self.assertIn('PASSAGE-TEXT', prompts[-1]); self.assertNotIn('PASSAGE-TEXT', json.dumps(out))
        post = [s for s in SEEN if s[0] == '/query/data'][0]
        self.assertEqual(post[1], KEY); self.assertEqual(post[2]['query'], 'zzzz qqqq'); self.assertFalse(post[2]['enable_rerank'])
    def test_retrieval_fault_falls_back_to_keywords(self):
        model = lambda p: json.dumps({'answer': 'ok', 'ingredient_question': False, 'stages': {}})
        out = g.dispatch('ask', {'question': 'ingredient'}, 'tester-session-capability-0123456789', model)   # POST answers 500
        self.assertEqual(out['retrieval'], 'keyword'); self.assertEqual(g.dispatch('status', {}, '', None)['retrieval'], 'lightrag_query')
        with patch.dict(os.environ, {'KG_ORACLE_REMOTE_QUERY': '0'}):
            self.assertEqual(g.dispatch('status', {}, '', None)['retrieval'], 'keyword')
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


class ExplorerUrlTests(unittest.TestCase):
    """The address behind the page's "Open the full knowledge graph" button (2026-11-22)."""

    def url(self, **env):
        import graph_oracle as module
        clean = {k: v for k, v in os.environ.items() if not k.startswith('KG_ORACLE_')}
        with patch.dict(os.environ, {**clean, **env}, clear=True):
            return module.explorer_url()

    def test_hosted_graph_points_at_its_own_viewer_without_any_secret(self):
        out = self.url(KG_ORACLE_REMOTE_URL='https://graph.example.org/', KG_ORACLE_REMOTE_API_KEY='k' * 40)
        self.assertEqual(out, 'https://graph.example.org/webui/')
        self.assertNotIn('k' * 40, out)

    def test_explicit_address_wins(self):
        self.assertEqual(self.url(KG_ORACLE_REMOTE_URL='https://graph.example.org', KG_ORACLE_EXPLORER_URL='https://kg.example.org/view'),
                         'https://kg.example.org/view')

    def test_nothing_unsafe_or_local_is_ever_offered(self):
        self.assertIsNone(self.url())                                                     # local graph file: no button
        for bad in ('http://graph.example.org', 'https://user:pw@graph.example.org', 'https://graph.example.org/?key=1',
                    'javascript:alert(1)', 'http://127.0.0.1:9621'):
            self.assertIsNone(self.url(KG_ORACLE_EXPLORER_URL=bad), bad)
        self.assertIsNone(self.url(KG_ORACLE_REMOTE_URL='http://127.0.0.1:9621'))         # loopback sandbox: nothing public to open
