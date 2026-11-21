#!/usr/bin/env python3
# Last updated: 2026-11-21 23:55 UTC · Claude (Opus 5.5) · cloud KG intake: keyed upload page + rights gate + supervised GROBID batch worker
"""MeatCODE cloud KG intake (Render).

PDF upload (intake key + open-access / rights-cleared declaration) -> disk inbox -> the existing
guarded worker (pipeline/grobid/batch_worker.py: GROBID parse, DOI/hash/overlap checks, ledger,
claim extraction, one paper at a time) -> hosted LightRAG. Nothing here writes to Neon or
promotes canonical knowledge. Never logs or returns secrets.
"""
from __future__ import annotations

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
    expected = os.environ.get("INTAKE_API_KEY", "")
    return len(expected) >= 32 and bool(given) and hmac.compare_digest(given.encode(), expected.encode())


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
    counts, attention = {}, []
    if path.exists():
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            counts = dict(con.execute("SELECT status, count(*) FROM papers GROUP BY status"))
            attention = [{"file": Path(p).name, "status": s, "reason": r} for p, s, r in con.execute(
                "SELECT pdf_path,status,reason FROM papers WHERE status IN "
                "('review_required','submission_unknown','retry_wait','failed') ORDER BY updated_at DESC LIMIT 50")]
        finally:
            con.close()
    queued = sorted(p.name for p in INBOX.glob("*.pdf")) if INBOX.exists() else []
    return {"ledger": counts, "attention": attention, "inbox_files": len(queued),
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

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'")
            self.send_header("Content-Length", str(len(PAGE)))
            self.end_headers()
            self.wfile.write(PAGE)
        elif self.path == "/health":
            self._json(200, {"status": "ok"})
        elif self.path == "/api/status":
            if not key_ok(self.headers.get("X-Intake-Key")):
                return self._json(403, {"error": "Intake key required"})
            self._json(200, ledger_status())
        else:
            self._json(404, {"error": "Not found"})

    def do_PUT(self):
        if self.path != "/api/upload":
            return self._json(404, {"error": "Not found"})
        if not key_ok(self.headers.get("X-Intake-Key")):
            audit(action="refused", reason="bad_key")
            return self._json(403, {"error": "Intake key required"})
        rights = (self.headers.get("X-Rights") or "").strip()
        evidence = (self.headers.get("X-Rights-Evidence") or "").strip()
        uploader = (self.headers.get("X-Uploader") or "").strip()[:80]
        name = safe_name(self.headers.get("X-Filename") or "")
        if rights not in RIGHTS or not 5 <= len(evidence) <= 500:
            audit(action="refused", reason="rights", rights=rights[:40], file=name, uploader=uploader)
            return self._json(400, {"error": "Only open-access or rights-cleared papers are accepted. "
                                             "Declare which, with the licence or permission source."})
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
