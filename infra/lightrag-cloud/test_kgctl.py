# Last updated: 2026-11-21 21:34 UTC · Claude (Sonnet 5.5) · kgctl unit tests
import json, threading, unittest, tempfile, os, io, contextlib
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import kgctl

SEEN = []

class H(BaseHTTPRequestHandler):
    def _do(self):
        n = int(self.headers.get("Content-Length") or 0)
        SEEN.append((self.command, self.path, self.headers.get("X-API-Key"), self.rfile.read(n)))
        b = json.dumps({"status": "ok"}).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    do_GET = do_POST = do_DELETE = _do
    def log_message(self, *a): pass

class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), H); threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.kg = kgctl.KG(f"http://127.0.0.1:{cls.srv.server_port}", "k" * 40)
    @classmethod
    def tearDownClass(cls): cls.srv.shutdown()
    def setUp(self):
        SEEN.clear(); self.d = tempfile.mkdtemp(); kgctl.AUDIT = Path(self.d) / "a.jsonl"
    def go(self, *argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf): kgctl.run(kgctl.build_parser().parse_args(argv), self.kg)
    def test_destructive_needs_yes(self):
        for argv in (["entity-delete", "X"], ["entity-merge", "A", "--into", "B"], ["relation-delete", "A", "B"], ["delete-doc", "d1"]):
            with self.assertRaises(SystemExit): self.go(*argv)
        self.assertEqual(SEEN, [])
    def test_api_key_header_and_merge_body(self):
        self.go("entity-merge", "Msk", "Mxk", "--into", "Musk", "--yes")
        m, p, k, b = SEEN[0]
        self.assertEqual((m, p, k), ("POST", "/graph/entities/merge", "k" * 40))
        self.assertEqual(json.loads(b), {"entities_to_change": ["Msk", "Mxk"], "entity_to_change_into": "Musk"})
    def test_rename_sets_flag(self):
        self.go("entity-edit", "Old", "--rename", "New")
        body = json.loads(SEEN[0][3]); self.assertTrue(body["allow_rename"]); self.assertEqual(body["updated_data"], {"entity_name": "New"})
    def test_audit_has_no_secret(self):
        self.go("entity-delete", "X", "--yes")
        line = kgctl.AUDIT.read_text(); self.assertIn("entity-delete", line); self.assertNotIn("k" * 40, line)
    def test_upload_multipart(self):
        f = Path(self.d) / "p.pdf"; f.write_bytes(b"%PDF-1.4 x")
        self.go("upload", str(f))
        self.assertIn(b'filename="p.pdf"', SEEN[0][3]); self.assertEqual(SEEN[0][1], "/documents/upload")
    def test_bad_set(self):
        with self.assertRaises(SystemExit): self.go("relation-edit", "A", "B", "--set", "nokv")

if __name__ == "__main__": unittest.main()
