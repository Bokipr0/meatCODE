# Last updated: 2026-11-21 23:59 UTC · Claude (Opus 5.5) · intake: key, rights gate, PDF check, dedupe, audit, status
import http.client, json, os, sqlite3, sys, tempfile, threading, unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
TMP = tempfile.mkdtemp()
os.environ.update(INTAKE_DATA=TMP, INTAKE_API_KEY="k" * 40, INTAKE_MAX_MB="1", INTAKE_MAX_UPLOADS_PER_HOUR="100")
sys.path.insert(0, str(Path(__file__).parent))
import intake_server as s
PDF = b"%PDF-1.7\n fixture \n%%EOF"
class IntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for p in (s.INBOX, s.BATCH, s.PROV): p.mkdir(parents=True, exist_ok=True)
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), s.Handler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
    @classmethod
    def tearDownClass(cls): cls.srv.shutdown()
    def req(self, method, path, body=b"", **headers):
        c = http.client.HTTPConnection("127.0.0.1", self.srv.server_port); c.request(method, path, body=body, headers=headers)
        r = c.getresponse(); return r.status, json.loads(r.read() or b"{}") if r.getheader("Content-Type","").startswith("application/json") else {}
    def up(self, body=PDF, key="k" * 40, rights="open_access", ev="CC-BY 4.0 https://doi.org/x", name="a.pdf"):
        return self.req("PUT", "/api/upload", body, **{"X-Intake-Key": key, "X-Rights": rights, "X-Rights-Evidence": ev, "X-Filename": name, "Content-Length": str(len(body))})
    def audit(self): return [json.loads(l) for l in s.AUDIT.read_text().splitlines()] if s.AUDIT.exists() else []
    def test_page_and_health_are_public_status_is_not(self):
        self.assertEqual(self.req("GET", "/")[0], 200); self.assertEqual(self.req("GET", "/health")[0], 200)
        self.assertEqual(self.req("GET", "/api/status")[0], 403)
        self.assertEqual(self.req("GET", "/api/status", **{"X-Intake-Key": "k" * 40})[0], 200)
    def test_wrong_key_refused_and_logged(self):
        self.assertEqual(self.up(key="x" * 40)[0], 403); self.assertEqual(self.audit()[-1]["reason"], "bad_key")
    def test_rights_gate(self):
        before = len(list(s.INBOX.glob("*.pdf")))
        for r, ev in (("publisher", "x" * 10), ("", "x" * 10), ("open_access", "")):
            self.assertEqual(self.up(rights=r, ev=ev)[0], 400)
        self.assertEqual(self.audit()[-1]["reason"], "rights"); self.assertEqual(len(list(s.INBOX.glob("*.pdf"))), before)
    def test_not_pdf_and_too_big(self):
        self.assertEqual(self.up(body=b"hello world")[0], 400)
        self.assertEqual(self.up(body=b"%PDF-" + b"0" * (1024 * 1024 + 10))[0], 413)
    def test_accept_then_dedupe_with_provenance(self):
        before = set(s.INBOX.glob("*.pdf"))
        code, j = self.up(body=PDF + b"1", name="../../evil name.pdf"); self.assertEqual(code, 202)
        files = list(set(s.INBOX.glob("*.pdf")) - before); self.assertEqual(len(files), 1); self.assertNotIn("..", files[0].name)
        prov = json.loads((s.PROV / f"{j['sha256']}.json").read_text()); self.assertEqual(prov["rights"], "open_access")
        self.assertEqual(self.up(body=PDF + b"1")[1]["status"], "already_received"); self.assertEqual(len(set(s.INBOX.glob("*.pdf")) - before), 1)
    def test_status_reads_ledger(self):
        con = sqlite3.connect(s.BATCH / "papers.sqlite"); con.execute("CREATE TABLE IF NOT EXISTS papers (pdf_sha256 TEXT, pdf_path TEXT, status TEXT, reason TEXT, updated_at TEXT)")
        con.execute("INSERT INTO papers VALUES ('h','/data/inbox/x.pdf','review_required','No DOI','t')"); con.commit(); con.close()
        code, j = self.req("GET", "/api/status", **{"X-Intake-Key": "k" * 40})
        self.assertEqual(j["ledger"]["review_required"], 1); self.assertEqual(j["attention"][0]["file"], "x.pdf")
    def test_no_secret_in_audit(self):
        self.up(); self.assertNotIn("k" * 40, s.AUDIT.read_text())
if __name__ == "__main__": unittest.main()
