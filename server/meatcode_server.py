#!/usr/bin/env python3
"""
MeatCODE — single-file Claude API server.

What it does
------------
- Serves every file in the SAME folder as this script (so it serves
  MeatCODE_Mockup_GFI_v7.html / v6.html, the SVGs, the assets, etc.)
- Handles POST /api/ask  →  streams Claude's answer back to the Oracle
  in the exact SSE format the mockup expects:
      event: sources   (with empty [] array)
      event: chunk     (one event per text fragment)
      event: done

Run it
------
    1.  pip install anthropic              # one-time
    2.  export ANTHROPIC_API_KEY=sk-ant-...
    3.  python3 meatcode_server.py

Then open  http://localhost:8000/MeatCODE_Mockup_GFI_v7.html  in your browser,
click Oracle, type a question, hit Ask. That's it.

To stop: Ctrl+C in the terminal.

If you'd rather keep the key in a file: drop a `.env` next to this script with
ANTHROPIC_API_KEY=sk-ant-...  on its own line. The script reads it automatically.
"""

import os, sys, json, re, threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ─── Config ──────────────────────────────────────────────────────────
PORT       = 8000
MODEL      = "claude-sonnet-4-6"           # if you get a model-access error, try "claude-opus-4-8" or "claude-haiku-4-5-20251001"
MAX_TOKENS = 1600
SYSTEM_PROMPT = (
    "You are MeatCODE Oracle — a flavor & aroma research assistant for "
    "GFI Israel. Answer concisely (3–5 short paragraphs max). Focus on "
    "meat-flavor chemistry: Maillard, sulfur volatiles, lipid oxidation, "
    "off-note masking, plant-protein flavor systems, cultivated meat, "
    "and the analytical techniques behind them (GC-MS, GC-O, SPME, etc.). "
    "Use plain prose paragraphs separated by blank lines. Cite compounds "
    "by name. After the main answer, add a final line starting with "
    "'Follow-ups:' followed by 2–3 short follow-up questions separated "
    "by ' · ' (a space, middle dot, space). Do not use markdown headers, "
    "bullets, or code blocks."
)

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)          # meatCODE/ repo root (server/ is one level down)
SERVE_DIR = REPO_ROOT                      # serve the whole repo so /app/meatcode_mockup.html resolves


# ─── tiny .env loader (no python-dotenv needed) ──────────────────────
def load_dotenv(path):
    if not path or not os.path.exists(path): return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)

# .env at repo root first (the convention), then next to this script as fallback
load_dotenv(os.path.join(REPO_ROOT, ".env"))
load_dotenv(os.path.join(HERE, ".env"))
API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not API_KEY:
    sys.stderr.write(
        "\nERROR: ANTHROPIC_API_KEY is not set.\n"
        "  Either:  export ANTHROPIC_API_KEY=sk-ant-...\n"
        "  Or:      put ANTHROPIC_API_KEY=sk-ant-... in a .env file next to this script.\n\n"
    )
    sys.exit(1)

try:
    import anthropic
except ImportError:
    sys.stderr.write("\nERROR: anthropic package not installed.\n"
                     "  Run:  pip install anthropic\n\n")
    sys.exit(1)

client = anthropic.Anthropic(api_key=API_KEY)

# ─── optional Postgres (for /api/experts and /api/papers) ────────────
# Oracle + static serving work without a DB; these endpoints need DATABASE_URL
# (read from the same .env). If psycopg2 or the URL is missing, they 503 and the
# mockup falls back to its demo data.
DATABASE_URL = os.environ.get("DATABASE_URL")

def pg_rows(sql, params=()):
    import psycopg2
    from psycopg2.extras import RealDictCursor
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]


# ─── HTTP handler ────────────────────────────────────────────────────
class Handler(SimpleHTTPRequestHandler):
    # Serve static files from the folder this script lives in
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=SERVE_DIR, **kw)

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))

    # CORS for any browser request (works for file:// origin too)
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204); self.end_headers()

    # ─── JSON helper ───
    def _send_json(self, obj, code=200):
        body = json.dumps(obj, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    # ─── GET: /api/* handled here; everything else = static files ───
    def do_GET(self):
        path = urlparse(self.path).path
        if path.startswith("/api/"):
            return self._handle_api_get(path)
        return super().do_GET()

    def _handle_api_get(self, path):
        qs = parse_qs(urlparse(self.path).query)
        if path == "/api/health":
            return self._send_json({"ok": True, "db": bool(DATABASE_URL), "model": MODEL})
        if not DATABASE_URL:
            return self._send_json({"error": "DATABASE_URL not configured"}, 503)
        try:
            if path == "/api/experts":
                limit = max(1, min(500, int((qs.get("limit") or ["200"])[0])))
                return self._send_json(pg_rows(
                    "SELECT id, name, affiliation, country, org_type::text AS org_type, "
                    "relevance_score::float AS relevance_score, h_index, total_papers, "
                    "keywords, orcid, linkedin_url, current_org FROM experts "
                    "WHERE relevance_score IS NOT NULL "
                    "ORDER BY relevance_score DESC NULLS LAST, h_index DESC NULLS LAST LIMIT %s",
                    (limit,)))
            m = re.match(r"^/api/experts/(\d+)$", path)
            if m:
                rows = pg_rows(
                    "SELECT id, name, affiliation, country, org_type::text AS org_type, "
                    "research_field::text AS research_field, relevance_score::float AS relevance_score, "
                    "h_index, total_papers, keywords, key_research, knowledge_gaps, orcid, "
                    "linkedin_url, email, current_org, dimensions_topics FROM experts WHERE id=%s",
                    (int(m.group(1)),))
                return self._send_json(rows[0] if rows else {"error": "not found"}, 200 if rows else 404)
            m = re.match(r"^/api/papers/(\d+)$", path)
            if m:
                rows = pg_rows(
                    "SELECT id, name, year, authors, journal, venue, doi, abstract, url, "
                    "citation_count, priority_score::float AS priority_score, relevance_llm "
                    "FROM sources WHERE id=%s", (int(m.group(1)),))
                return self._send_json(rows[0] if rows else {"error": "not found"}, 200 if rows else 404)
            return self._send_json({"error": "unknown endpoint " + path}, 404)
        except Exception as e:
            return self._send_json({"error": "database error: " + str(e)[:200]}, 503)

    def do_POST(self):
        path = urlparse(self.path).path
        if path != "/api/ask":
            self.send_error(404, "POST not supported for " + path); return

        # Read JSON body
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except Exception as e:
            self.send_error(400, "Bad JSON: " + str(e)); return
        question = (body.get("question") or "").strip()
        if not question:
            self.send_error(400, "Missing 'question'"); return

        # SSE response — start streaming
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        def send_event(event, data):
            # Multi-line data → multiple data: lines (per SSE spec)
            lines = str(data).split("\n")
            payload = "event: %s\n%s\n\n" % (
                event, "\n".join("data: " + l for l in lines)
            )
            try:
                self.wfile.write(payload.encode("utf-8")); self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass

        # 1) sources event — empty array (no RAG in this minimal server).
        #    The Oracle UI handles empty gracefully and shows
        #    "No matches in the database — Claude is responding based on the question alone."
        send_event("sources", "[]")

        # 2) stream Claude's answer as chunk events
        try:
            with client.messages.stream(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": question}],
            ) as stream:
                for text in stream.text_stream:
                    if text: send_event("chunk", text)
            send_event("done", "")
        except Exception as e:
            send_event("error", "Claude API error: " + str(e))


# ─── Run it ──────────────────────────────────────────────────────────
def main():
    httpd = HTTPServer(("0.0.0.0", PORT), Handler)
    candidates = ["app/meatcode_mockup.html", "meatcode_mockup.html",
                  "app/MeatCODE_Mockup_GFI_v7.html"]
    mock = next((c for c in candidates if os.path.exists(os.path.join(SERVE_DIR, c))), candidates[0])
    print(f"\n  MeatCODE server running on http://localhost:{PORT}")
    print(f"  Open:  http://localhost:{PORT}/{mock}")
    print(f"  Model: {MODEL}")
    print(f"  Database: {'connected via DATABASE_URL' if DATABASE_URL else 'NOT set — /api/experts will 503, mockup uses demo data'}")
    print(f"  Press Ctrl+C to stop.\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped.")

if __name__ == "__main__":
    main()
