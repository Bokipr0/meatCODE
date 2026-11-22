#!/usr/bin/env python3
# Last updated: 2026-11-22 05:45 UTC · Claude (Fable 5.2) · status lists received files as 'waiting' before their first ledger row · 05:05 · licence/permission note made optional (field removed from the page) · 04:10 · people sign in with a username + password (HTTP Basic, same pair as the MeatCODE site); the key is an optional machine credential; status lists recent papers · prev 2026-11-21 Opus 5.5 · keyed upload page + rights gate + supervised worker
"""MeatCODE cloud KG intake (Render).

PDF upload (username + password sign-in, open-access / rights-cleared declaration) -> disk inbox -> the existing
guarded worker (pipeline/grobid/batch_worker.py: GROBID parse, DOI/hash/overlap checks, ledger,
claim extraction, one paper at a time) -> hosted LightRAG. Nothing here writes to Neon or
promotes canonical knowledge. Never logs or returns secrets.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.parse
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DATA = Path(os.environ.get("INTAKE_DATA", "/data"))
INBOX, BATCH, PROV = DATA / "inbox", DATA / "batch", DATA / "provenance"
AUDIT = DATA / "audit.jsonl"
MAX_BYTES = int(os.environ.get("INTAKE_MAX_MB", "50")) * 1024 * 1024
RIGHTS = {"open_access", "rights_cleared"}
RATE = int(os.environ.get("INTAKE_MAX_UPLOADS_PER_HOUR", "60"))
_recent: deque[float] = deque()
_lock = threading.Lock()
HERE = Path(__file__).resolve().parent
PAGE = (HERE / "upload.html").read_bytes() if (HERE / "upload.html").exists() else b"<h1>MeatCODE KG intake</h1>"


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def audit(**event) -> None:
    event["at"] = now()
    with _lock, AUDIT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def key_ok(given: str | None) -> bool:
    """Optional machine credential (scripts). People use the username + password below."""
    expected = os.environ.get("INTAKE_API_KEY", "")
    return len(expected) >= 32 and bool(given) and hmac.compare_digest(given.encode(), expected.encode())


_fails: dict[str, deque] = {}
LOCK_AFTER, LOCK_WINDOW = 10, 900          # 10 wrong passwords per address -> refused for 15 minutes


def client_ip(handler) -> str:
    return (handler.headers.get("X-Forwarded-For") or handler.client_address[0]).split(",")[0].strip()[:64]


def locked(ip: str) -> bool:
    t = time.time()
    with _lock:
        q = _fails.get(ip)
        while q and t - q[0] > LOCK_WINDOW:
            q.popleft()
        return bool(q) and len(q) >= LOCK_AFTER


def signed_in(handler) -> str | None:
    """Name of the authenticated caller, or None. Never logs credentials."""
    if key_ok(handler.headers.get("X-Intake-Key")):
        return "machine"
    user, password = os.environ.get("INTAKE_USER", ""), os.environ.get("INTAKE_PASSWORD", "")
    header = handler.headers.get("Authorization") or ""
    if not user or len(password) < 6 or not header.startswith("Basic "):
        return None
    ip = client_ip(handler)
    if locked(ip):
        return None
    try:
        given_user, _, given_password = base64.b64decode(header[6:], validate=True).decode("utf-8").partition(":")
    except (ValueError, UnicodeDecodeError):
        return None
    ok = hmac.compare_digest(given_user.encode(), user.encode()) & hmac.compare_digest(given_password.encode(), password.encode())
    if not ok:
        with _lock:
            _fails.setdefault(ip, deque()).append(time.time())
        audit(action="refused", reason="bad_password")
        return None
    return given_user


def safe_name(name: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(name or "paper.pdf").name)[:80].strip("._") or "paper"
    return stem if stem.lower().endswith(".pdf") else stem + ".pdf"


def rate_ok() -> bool:
    t = time.time()
    with _lock:
        while _recent and t - _recent[0] > 3600:
            _recent.popleft()
        if len(_recent) >= RATE:
            return False
        _recent.append(t)
        return True


def ledger_status() -> dict:
    path = BATCH / "papers.sqlite"
    counts, attention, recent, ledger_files = {}, [], [], set()
    if path.exists():
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            counts = dict(con.execute("SELECT status, count(*) FROM papers GROUP BY status"))
            attention = [{"file": Path(p).name, "status": s, "reason": r} for p, s, r in con.execute(
                "SELECT pdf_path,status,reason FROM papers WHERE status IN "
                "('review_required','submission_unknown','retry_wait','failed') ORDER BY updated_at DESC LIMIT 50")]
            ledger_files = {Path(r[0]).name for r in con.execute("SELECT pdf_path FROM papers")}
            recent = [{"file": Path(p).name, "status": st, "doi": d, "note": r, "updated": u} for p, st, d, r, u in con.execute(
                "SELECT pdf_path,status,paper_doi,reason,updated_at FROM papers ORDER BY updated_at DESC LIMIT 40")]
        finally:
            con.close()
    queued = sorted(p.name for p in INBOX.glob("*.pdf")) if INBOX.exists() else []
    # Files received but not yet in the ledger (GROBID + claim extraction take minutes before the first ledger row).
    seen = {r["file"] for r in recent}
    waiting = [{"file": n, "status": "waiting", "doi": None, "note": "received; parsing starts in turn", "updated": ""}
               for n in queued if n not in seen and n not in ledger_files]
    recent = waiting[:40] + recent
    return {"ledger": counts, "attention": attention, "recent": recent, "inbox_files": len(queued),
            "graph_url": os.environ.get("LIGHTRAG_URL", "").rstrip("/") + "/webui/",
            "worker": WORKER_STATE.copy(), "paused": (BATCH / "pause.json").exists()}


class Handler(BaseHTTPRequestHandler):
    server_version = "meatcode-kg-intake"

    def _json(self, code: int, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):  # path only; never headers
        sys.stderr.write("%s %s\n" % (self.command, self.path.split("?")[0]))

    def _challenge(self):
        if locked(client_ip(self)):
            return self._json(429, {"error": "Too many wrong passwords. Try again in 15 minutes."})
        data = b'{"error": "Sign in required"}'
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="MeatCODE knowledge-graph intake", charset="UTF-8"')
        self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(data)))
        self.end_headers(); self.wfile.write(data)

    def do_GET(self):
        if self.path == "/health":
            return self._json(200, {"status": "ok"})
        if not signed_in(self):
            return self._challenge()
        if self.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'")
            self.send_header("Content-Length", str(len(PAGE)))
            self.end_headers()
            self.wfile.write(PAGE)
        elif self.path == "/api/status":
            self._json(200, ledger_status())
        else:
            self._json(404, {"error": "Not found"})

    def do_PUT(self):
        if self.path != "/api/upload":
            return self._json(404, {"error": "Not found"})
        who = signed_in(self)
        if not who:
            return self._challenge()
        rights = (self.headers.get("X-Rights") or "").strip()
        evidence = (self.headers.get("X-Rights-Evidence") or "").strip()
        uploader = ((self.headers.get("X-Uploader") or "").strip()[:80] or who)
        name = safe_name(urllib.parse.unquote(self.headers.get("X-Filename") or ""))
        if rights not in RIGHTS or len(evidence) > 500:      # the licence/permission note is optional (2026-11-22, Lior)
            audit(action="refused", reason="rights", rights=rights[:40], file=name, uploader=uploader)
            return self._json(400, {"error": "Only open-access or rights-cleared papers are accepted. Choose which applies."})
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = -1
        if not 5 <= length <= MAX_BYTES:
            return self._json(413 if length > MAX_BYTES else 400, {"error": f"PDF must be 1 byte to {MAX_BYTES // 1048576} MB"})
        if not rate_ok():
            return self._json(429, {"error": "Too many uploads this hour; retry later"})
        body = self.rfile.read(length)
        if len(body) != length or not body.startswith(b"%PDF-"):
            audit(action="refused", reason="not_pdf", file=name, uploader=uploader)
            return self._json(400, {"error": "Not a PDF file"})
        digest = hashlib.sha256(body).hexdigest()
        INBOX.mkdir(parents=True, exist_ok=True); PROV.mkdir(parents=True, exist_ok=True)
        target = INBOX / f"{digest[:12]}-{name}"
        prov = PROV / f"{digest}.json"
        if prov.exists():
            audit(action="duplicate_upload", sha256=digest, file=name, uploader=uploader)
            return self._json(200, {"status": "already_received", "sha256": digest})
        tmp = target.with_suffix(".part")
        tmp.write_bytes(body)
        prov.write_text(json.dumps({"sha256": digest, "file": target.name, "rights": rights,
                                    "rights_evidence": evidence, "uploader": uploader, "received_at": now()}))
        os.replace(tmp, target)  # the worker only sees complete files (.pdf suffix)
        audit(action="accepted", sha256=digest, file=target.name, rights=rights, rights_evidence=evidence, uploader=uploader)
        return self._json(202, {"status": "queued", "sha256": digest,
                                "note": "The worker parses, checks DOI/duplicates/overlap, then submits one paper at a time."})


WORKER_STATE = {"running": False, "restarts": 0, "last_exit": None}


def supervise_worker() -> None:
    lightrag = os.environ.get("LIGHTRAG_URL", "https://meatcode-lightrag.onrender.com")
    cmd = [sys.executable, str(Path(os.environ.get("PIPELINE_DIR", "/app/pipeline/grobid")) / "batch_worker.py"),
           "--watch", "--inbox", str(INBOX), "--output", str(BATCH),
           "--graph", str(DATA / "graph/kv_store_full_docs.json"), "--lightrag-url", lightrag,
           "--interval", os.environ.get("INTAKE_WORKER_INTERVAL", "60")]
    while True:
        WORKER_STATE["running"] = True
        code = subprocess.call(cmd)
        WORKER_STATE.update(running=False, last_exit=code, restarts=WORKER_STATE["restarts"] + 1)
        time.sleep(min(300, 15 * WORKER_STATE["restarts"]))


def main() -> None:
    for p in (INBOX, BATCH, PROV):
        p.mkdir(parents=True, exist_ok=True)
    if os.environ.get("INTAKE_WORKER", "1") == "1":
        threading.Thread(target=supervise_worker, name="grobid-worker", daemon=True).start()
    port = int(os.environ.get("PORT", "10000"))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
