# Last updated: 2026-11-22 04:20 UTC · Claude (Fable 5.2) · intake: username/password sign-in, lockout, optional key, rights gate, PDF check, dedupe, audit, status
import base64, http.client, json, os, sqlite3, sys, tempfile, threading, unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
TMP = tempfile.mkdtemp()
os.environ.update(INTAKE_DATA=TMP, INTAKE_API_KEY="k" * 40, INTAKE_USER="team", INTAKE_PASSWORD="correct-horse", INTAKE_MAX_MB="1", INTAKE_MAX_UPLOADS_PER_HOUR="100")
sys.path.insert(0, str(Path(__file__).parent))
import intake_server as s
PDF = b"%PDF-1.7\n fixture \n%%EOF"
def basic(u="team", p="correct-horse"): return "Basic " + base64.b64encode(f"{u}:{p}".encode()).decode()
class IntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for p in (s.INBOX, s.BATCH, s.PROV): p.mkdir(parents=True, exist_ok=True)
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), s.Handler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
    @classmethod
    def tearDownClass(cls): cls.srv.shutdown()
    def setUp(self): s._fails.clear()
    def req(self, method, path, body=b"", **headers):
        c = http.client.HTTPConnection("127.0.0.1", self.srv.server_port); c.request(method, path, body=body, headers=headers)
        r = c.getresponse(); raw = r.read()
        return r.status, (json.loads(raw or b"{}") if (r.getheader("Content-Type") or "").startswith("application/json") else {}), r
    def up(self, body=PDF, auth=None, rights="open_access", ev="CC-BY 4.0 https://doi.org/x", name="a.pdf", **extra):
        h = {"Authorization": auth or basic(), "X-Rights": rights, "X-Rights-Evidence": ev, "X-Filename": name, "Content-Length": str(len(body))}; h.update(extra)
        return self.req("PUT", "/api/upload", body, **h)[:2]
    def audit(self): return [json.loads(l) for l in s.AUDIT.read_text().splitlines()] if s.AUDIT.exists() else []
    def test_health_public_everything_else_needs_sign_in(self):
        self.assertEqual(self.req("GET", "/health")[0], 200)
        for path in ("/", "/api/status"):
            code, _, r = self.req("GET", path); self.assertEqual(code, 401); self.assertIn("Basic", r.getheader("WWW-Authenticate"))
            self.assertEqual(self.req("GET", path, Authorization=basic())[0], 200)
        self.assertEqual(self.req("PUT", "/api/upload", PDF)[0], 401)
    def test_wrong_password_refused_logged_and_locked_out(self):
        for _ in range(s.LOCK_AFTER): self.assertIn(self.req("GET", "/api/status", Authorization=basic(p="nope"))[0], (401, 429))
        self.assertEqual(self.audit()[-1]["reason"], "bad_password")
        self.assertEqual(self.req("GET", "/api/status", Authorization=basic())[0], 429)   # even the right password, while locked
        self.assertNotIn("nope", s.AUDIT.read_text()); self.assertNotIn("correct-horse", s.AUDIT.read_text())
    def test_wrong_user_and_malformed_header(self):
        self.assertEqual(self.req("GET", "/api/status", Authorization=basic(u="other"))[0], 401)
        self.assertEqual(self.req("GET", "/api/status", Authorization="Basic !!!")[0], 401)
    def test_machine_key_still_works(self):
        self.assertEqual(self.req("GET", "/api/status", **{"X-Intake-Key": "k" * 40})[0], 200)
        self.assertEqual(self.req("GET", "/api/status", **{"X-Intake-Key": "x" * 40})[0], 401)
    def test_rights_gate(self):
        before = len(list(s.INBOX.glob("*.pdf")))
        for r, ev in (("publisher", "x" * 10), ("", "x" * 10), ("open_access", "x" * 501)):
            self.assertEqual(self.up(rights=r, ev=ev)[0], 400)
        self.assertEqual(self.audit()[-1]["reason"], "rights"); self.assertEqual(len(list(s.INBOX.glob("*.pdf"))), before)
    def test_licence_note_is_optional(self):
        self.assertEqual(self.up(body=PDF + b"no-note", ev="")[0], 202)
    def test_not_pdf_and_too_big(self):
        self.assertEqual(self.up(body=b"hello world")[0], 400)
        self.assertEqual(self.up(body=b"%PDF-" + b"0" * (1024 * 1024 + 10))[0], 413)
    def test_accept_then_dedupe_with_provenance_and_uploader(self):
        before = set(s.INBOX.glob("*.pdf"))
        code, j = self.up(body=PDF + b"1", name="..%2F..%2Fevil%20name.pdf"); self.assertEqual(code, 202)
        files = list(set(s.INBOX.glob("*.pdf")) - before); self.assertEqual(len(files), 1); self.assertNotIn("..", files[0].name); self.assertIn("evil_name", files[0].name)
        prov = json.loads((s.PROV / f"{j['sha256']}.json").read_text()); self.assertEqual(prov["rights"], "open_access"); self.assertEqual(prov["uploader"], "team")
        self.assertEqual(self.up(body=PDF + b"1")[1]["status"], "already_received"); self.assertEqual(len(set(s.INBOX.glob("*.pdf")) - before), 1)
    def test_status_lists_recent_papers(self):
        con = sqlite3.connect(s.BATCH / "papers.sqlite"); con.execute("CREATE TABLE IF NOT EXISTS papers (pdf_sha256 TEXT, pdf_path TEXT, paper_doi TEXT, status TEXT, reason TEXT, updated_at TEXT)")
        con.execute("INSERT INTO papers VALUES ('h','/data/inbox/x.pdf','10.1/x','review_required','No DOI','t')"); con.commit(); con.close()
        _, j, _ = self.req("GET", "/api/status", Authorization=basic())
        self.assertEqual(j["ledger"]["review_required"], 1); self.assertEqual(j["attention"][0]["file"], "x.pdf"); self.assertEqual(j["recent"][0]["doi"], "10.1/x")
if __name__ == "__main__": unittest.main()
