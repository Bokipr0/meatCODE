# Last updated: 2026-11-17 · Codex · Local HTTP UI fixture; no real model, DB or analytics.
"""Serve the real Oracle UI against deterministic local streams on 127.0.0.1:18791."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import sys
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'server'))
from oracle_presentation import AnswerSections, DETAIL_MARKER

BRIEF = ('Start with a small, controlled precursor trial: fix your protein base and heating process, then vary '
         'one factor at a time [101]. Record the aroma change before scaling up.\n\n'
         'The best conditions depend on your matrix, so use the first trial as a comparison, not a validated recipe.')
DETAIL = ('Working from: the protein base and heating process you described. Open: exact pH and precursor levels.\n\n'
          'Compare each trial with the same unmodified base. Keep the analytical method consistent so a change in '
          'sampling does not look like a change in aroma. This is supporting detail in a local UI fixture [102].\n\n'
          'Next step: write down the one factor you will vary, how you will measure it, and the comparison you will use.')
STATE = {'asks': 0, 'research_writes': 0}


class Fixture(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, *args):
        pass

    def send_json(self, data):
        body = json.dumps(data).encode()
        self.send_response(200); self.send_header('Content-Type', 'application/json'); self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/api/version': return self.send_json({'env': 'dev', 'commit': 'LOCAL-FIXTURE'})
        if path == '/api/flags': return self.send_json({'oracle_redesign': True, 'meatcode_avatar': True})
        if path == '/api/research/config': return self.send_json({'enabled': False, 'environment': 'dev', 'posthog': {'enabled': False}, 'clarity_project_id': ''})
        if path == '/api/test-status': return self.send_json(STATE)
        if path == '/api/molecule-suggestions': return self.send_json([])
        if path.startswith('/api/papers/'):
            return self.send_json({'id': int(path.rsplit('/', 1)[1]), 'title': 'Local evidence fixture', 'name': 'Local evidence fixture', 'year': 2026, 'abstract': 'Local test record. No scientific data queried.', 'url': 'https://example.org/evidence'})
        if path.startswith('/api/'): return self.send_json({'ok': True, 'rows': [], 'totals': {}})
        if path == '/':
            data = (ROOT / 'app/meatcode_mockup.html').read_text()
            data = data.replace('<body', '<body', 1).replace('</body>', '<div style="position:fixed;top:3px;left:45%;z-index:99999;font:11px sans-serif;color:#007b78;pointer-events:none">Local test · sample answer</div></body>')
            body = data.encode(); self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.end_headers(); self.wfile.write(body); return
        return super().do_GET()

    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers.get('Content-Length', '0'))) or b'{}')
        path = urlsplit(self.path).path
        if path != '/api/ask':
            if path.startswith('/api/research/'): STATE['research_writes'] += 1
            return self.send_json({'ok': True})
        STATE['asks'] += 1
        question = payload.get('question', '')
        self.send_response(200); self.send_header('Content-Type', 'text/event-stream'); self.send_header('Cache-Control', 'no-store'); self.end_headers()
        def event(name, data):
            text = 'event: '+name+'\n'+'\n'.join('data: '+line for line in str(data).split('\n'))+'\n\n'
            self.wfile.write(text.encode()); self.wfile.flush()
        if 'Clarify' in question:
            event('ask', json.dumps({'question': 'Which protein base?', 'options': ['Pea', 'Soy'], 'asked': 1, 'max': 3})); event('done', ''); return
        sources = [{'id': i, 'title': 'Local evidence fixture '+str(i), 'year': 2026, 'journal': 'UI fixture'} for i in (101, 102)]
        event('sources', json.dumps(sources))
        if 'Quick' in question: raw = 'Change one variable at a time and compare it with your unchanged base [101].'
        elif 'Legacy' in question: raw = 'A short legacy lead [101].\n\nSupporting explanation from an older response [102].'
        elif 'Long' in question: raw = BRIEF+'\n\n'+DETAIL_MARKER+'\n\n'+('Supporting legacy paragraph [102]. '+('additional evidence '*35)+'\n\n')*7
        else: raw = BRIEF+'\n\n'+DETAIL_MARKER+'\n\n'+DETAIL
        raw += '\n\nFollow-ups: How should I compare trials? · Which measurement fits?'
        presentation = AnswerSections()
        try:
            for i in range(0, len(raw), 23):
                for name, data in presentation.feed(raw[i:i+23]): event(name, data)
                time.sleep(.035 if 'Streaming' in question else .001)
            for name, data in presentation.finish(): event(name, data)
            event('done', '')
        except (BrokenPipeError, ConnectionResetError): pass


if __name__ == '__main__':
    print('Local fixture ready on http://127.0.0.1:18791', flush=True)
    ThreadingHTTPServer(('127.0.0.1', 18791), Fixture).serve_forever()
