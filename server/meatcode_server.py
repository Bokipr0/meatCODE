#!/usr/bin/env python3
# Last updated: 2026-07-07 10:34 UTC · Data Engineer (parallel team run: database-category API) ·
#   added read-only GET /api/molecules, /api/sources, /api/companies, /api/db-facets for the new
#   "Database" section (Molecules/Experts/Companies/Sources). SELECT-only, no writes.
#   NOTE: organizations table is EMPTY (0 rows) and experts.org_type is NULL for all 3,129 experts
#   (verified live) — /api/companies auto-detects this per request and falls back to a derived
#   (org_type-based) query that currently returns [] until org_type gets backfilled; see
#   PROJECT_STATE.md / this session's AGENT_UPDATE_LOG.md entry for details.
#   (Previous stamp referenced GET /api/experts/{id}/papers, /api/experts/{id}/similar,
#   /api/experts/export.csv, /api/experts/stats and a shared _expert_filter_sql() helper — none of
#   that is actually present in this file; looks like an earlier session's plan that never landed.
#   Left the /api/experts code as-is per this round's scope; flagging for whoever picks it up next.)
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

Endpoints
---------
  POST /api/ask                 Oracle answer, streamed as SSE
  GET  /api/health              {ok, db_ok, has_anthropic_key, model}
  GET  /api/experts[?q=&country=&sort=&min_relevance=&limit=]  Neon-backed expert list (map, filterable)
  GET  /api/expert-facets       country counts for curated experts (UI filter buttons)
  GET  /api/experts/{id}        single expert (detail panel)
  GET  /api/molecules[?q=&category=&sort=name|popularity&limit=]  Database tab: molecules
                                 (mentions_count = COUNT from source_molecules)
  GET  /api/sources[?q=&topic=&sort=relevance|citations|year&min_relevance=&limit=]  Database tab:
                                 literature sources
  GET  /api/companies[?q=&country=&sort=name|country&limit=]  Database tab: companies — reads the
                                 `organizations` table if populated, else derives from
                                 experts.org_type (currently [] — see NOTE at top of file)
  GET  /api/db-facets?entity=molecules|experts|companies|sources  filter-dropdown options
                                 (countries / categories / topics / year range) per entity
  GET  /api/papers/{id}         single paper (citation modal)
  GET  /api/papers/recent[?limit=]  recent papers (dashboard rows)
  GET  /api/templates           lists deployed Claude Design templates in app/templates/
  GET  /templates/ ...          serves app/templates/ (the template gallery + exports)

Claude Design templates: drop an exported .html into app/templates/ and include
<script src="meatcode-api.js"></script> — the connector wires its elements to the
endpoints above (same live Claude+Neon backend as the mockup). Gallery at
http://localhost:8000/templates/ .

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
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ─── Config ──────────────────────────────────────────────────────────
PORT       = int(os.environ.get("PORT", "8000"))  # cloud hosts (Render, etc.) inject $PORT; 8000 locally
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
TEMPLATES_DIR = os.path.join(REPO_ROOT, "app", "templates")  # Claude Design template exports


# ─── tiny .env loader (no python-dotenv needed) ──────────────────────
def load_dotenv(path):
    if not path or not os.path.exists(path): return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        # .env is authoritative: overwrite any stale shell export (e.g. an old
        # ANTHROPIC_API_KEY left over from `export`), which setdefault would keep.
        os.environ[k] = v

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
    # NB: psycopg2's `with connect() as conn` commits the transaction but does NOT
    # close the connection — so a bare `with` leaks one connection per request until
    # Neon's ceiling is hit. Close explicitly in finally.
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


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

    # Disable directory listings entirely on the public server.
    def list_directory(self, path):
        self.send_error(404, "Not found")
        return None

    # ─── GET: /api/* handled here; everything else = static files ───
    def do_GET(self):
        path = urlparse(self.path).path
        if path.startswith("/api/"):
            return self._handle_api_get(path)
        # Bare URL → the product mockup, so visitors land on MeatCODE (not a file list).
        if path in ("/", ""):
            self.send_response(302)
            self.send_header("Location", "/app/meatcode_mockup.html")
            self.end_headers()
            return
        # Public-server hygiene: never serve repo internals / secrets / scripts.
        low = path.lower()
        if low.startswith("/.") or "/." in low or low.endswith(".command") or low.endswith(".env"):
            self.send_error(404, "Not found")
            return
        # Pretty URL for the template gallery: /templates/... → app/templates/...
        # (bare /templates or /templates/ serves the gallery index). Keeps exported
        # templates portable — their relative meatcode-api.js and root-absolute
        # /api/* calls both resolve regardless of where the file physically lives.
        if path == "/templates" or path == "/templates/":
            self.path = "/app/templates/index.html"
        elif path.startswith("/templates/"):
            self.path = "/app/templates/" + path[len("/templates/"):]
        return super().do_GET()

    def _handle_api_get(self, path):
        qs = parse_qs(urlparse(self.path).query)
        if path == "/api/health":
            # Superset shape: `db`/`ok` kept for back-compat; `db_ok`/`has_anthropic_key`
            # are what app/templates/meatcode-api.js reads for its status chip.
            return self._send_json({
                "ok": True,
                "db": bool(DATABASE_URL),
                "db_ok": bool(DATABASE_URL),
                "has_anthropic_key": bool(API_KEY),
                "model": MODEL,
            })
        if path == "/api/templates":
            # No DB needed — lists whatever Claude Design exports live in app/templates/.
            return self._send_json(self._list_templates())

        if not DATABASE_URL:
            return self._send_json({"error": "DATABASE_URL not configured"}, 503)
        try:
            if path == "/api/experts":
                limit = max(1, min(500, int((qs.get("limit") or ["200"])[0])))
                q = (qs.get("q") or [""])[0].strip()
                country = (qs.get("country") or [""])[0].strip()
                sort = (qs.get("sort") or ["relevance"])[0].strip().lower()
                min_relevance_raw = (qs.get("min_relevance") or [""])[0].strip()

                sort_map = {
                    "relevance": "relevance_score DESC NULLS LAST, h_index DESC NULLS LAST",
                    "h_index": "h_index DESC NULLS LAST",
                    "papers": "total_papers DESC NULLS LAST",
                }
                order_by = sort_map.get(sort, sort_map["relevance"])

                where = ["relevance_score IS NOT NULL"]
                params = []
                if q:
                    where.append("(name ILIKE %s OR affiliation ILIKE %s)")
                    like = "%" + q + "%"
                    params.extend([like, like])
                if country:
                    where.append("country ILIKE %s")
                    params.append(country)
                if min_relevance_raw:
                    try:
                        min_relevance = float(min_relevance_raw)
                        where.append("relevance_score >= %s")
                        params.append(min_relevance)
                    except ValueError:
                        pass

                sql = (
                    "SELECT id, name, affiliation, country, org_type::text AS org_type, "
                    "relevance_score::float AS relevance_score, h_index, total_papers, "
                    "keywords, orcid, linkedin_url, current_org FROM experts "
                    "WHERE " + " AND ".join(where) + " "
                    "ORDER BY " + order_by + " LIMIT %s"
                )
                params.append(limit)
                return self._send_json(pg_rows(sql, tuple(params)))
            if path == "/api/expert-facets":
                countries = pg_rows(
                    "SELECT country, COUNT(*) AS count FROM experts "
                    "WHERE relevance_score IS NOT NULL AND country IS NOT NULL "
                    "GROUP BY country ORDER BY count DESC"
                )
                total_rows = pg_rows(
                    "SELECT COUNT(*) AS total FROM experts WHERE relevance_score IS NOT NULL"
                )
                total = total_rows[0]["total"] if total_rows else 0
                for row in countries:
                    row["count"] = int(row["count"])
                return self._send_json({"countries": countries, "total": int(total)})
            m = re.match(r"^/api/experts/(\d+)$", path)
            if m:
                rows = pg_rows(
                    "SELECT id, name, affiliation, country, org_type::text AS org_type, "
                    "research_field::text AS research_field, relevance_score::float AS relevance_score, "
                    "h_index, total_papers, keywords, key_research, knowledge_gaps, orcid, "
                    "linkedin_url, email, current_org, dimensions_topics FROM experts WHERE id=%s",
                    (int(m.group(1)),))
                return self._send_json(rows[0] if rows else {"error": "not found"}, 200 if rows else 404)
            if path == "/api/papers/recent":
                limit = max(1, min(20, int((qs.get("limit") or ["6"])[0])))
                return self._send_json(pg_rows(
                    "SELECT id, name, year, authors, journal, venue "
                    "FROM sources WHERE year IS NOT NULL "
                    "ORDER BY year DESC NULLS LAST, id DESC LIMIT %s",
                    (limit,)))
            m = re.match(r"^/api/papers/(\d+)$", path)
            if m:
                rows = pg_rows(
                    "SELECT id, name, year, authors, journal, venue, doi, abstract, url, "
                    "citation_count, priority_score::float AS priority_score, relevance_llm "
                    "FROM sources WHERE id=%s", (int(m.group(1)),))
                return self._send_json(rows[0] if rows else {"error": "not found"}, 200 if rows else 404)

            # ─── Database section: Molecules / Sources / Companies (+ shared facets) ───
            if path == "/api/molecules":
                limit = max(1, min(1000, int((qs.get("limit") or ["200"])[0])))
                q = (qs.get("q") or [""])[0].strip()
                category = (qs.get("category") or [""])[0].strip()
                sort = (qs.get("sort") or ["name"])[0].strip().lower()

                sort_map = {
                    "name": "m.name ASC",
                    "popularity": "mentions_count DESC NULLS LAST, m.name ASC",
                }
                order_by = sort_map.get(sort, sort_map["name"])

                where = []
                params = []
                if q:
                    where.append("m.name ILIKE %s")
                    params.append("%" + q + "%")
                if category:
                    where.append("m.category ILIKE %s")
                    params.append(category)
                where_sql = (" WHERE " + " AND ".join(where)) if where else ""

                sql = (
                    "SELECT m.id, m.name, m.category, m.taste, m.use_notes, "
                    "COALESCE(sm.mentions_count, 0)::int AS mentions_count "
                    "FROM molecules m "
                    "LEFT JOIN (SELECT molecule_id, COUNT(*) AS mentions_count "
                    "FROM source_molecules GROUP BY molecule_id) sm ON sm.molecule_id = m.id" +
                    where_sql +
                    " ORDER BY " + order_by + ", m.id ASC LIMIT %s"
                )
                params.append(limit)
                return self._send_json(pg_rows(sql, tuple(params)))

            if path == "/api/sources":
                limit = max(1, min(1000, int((qs.get("limit") or ["200"])[0])))
                q = (qs.get("q") or [""])[0].strip()
                topic = (qs.get("topic") or [""])[0].strip()
                sort = (qs.get("sort") or ["relevance"])[0].strip().lower()
                min_relevance_raw = (qs.get("min_relevance") or [""])[0].strip()

                sort_map = {
                    "relevance": "s.priority_score DESC NULLS LAST",
                    "citations": "s.citation_count DESC NULLS LAST",
                    "year": "s.year DESC NULLS LAST",
                }
                order_by = sort_map.get(sort, sort_map["relevance"])

                where = []
                params = []
                if q:
                    where.append("(s.name ILIKE %s OR s.abstract ILIKE %s)")
                    like = "%" + q + "%"
                    params.extend([like, like])
                if min_relevance_raw:
                    try:
                        min_relevance = float(min_relevance_raw)
                        where.append("s.relevance_llm >= %s")
                        params.append(min_relevance)
                    except ValueError:
                        pass
                if topic:
                    where.append(
                        "EXISTS (SELECT 1 FROM source_topics st JOIN topics t "
                        "ON t.id = st.topic_id WHERE st.source_id = s.id AND t.slug = %s)"
                    )
                    params.append(topic)
                where_sql = (" WHERE " + " AND ".join(where)) if where else ""

                sql = (
                    "SELECT s.id, s.name, s.year, s.journal, s.doi, s.citation_count, "
                    "s.priority_score::float AS priority_score, s.relevance_llm "
                    "FROM sources s" + where_sql +
                    " ORDER BY " + order_by + ", s.id DESC LIMIT %s"
                )
                params.append(limit)
                return self._send_json(pg_rows(sql, tuple(params)))

            if path == "/api/companies":
                limit = max(1, min(1000, int((qs.get("limit") or ["200"])[0])))
                q = (qs.get("q") or [""])[0].strip()
                country = (qs.get("country") or [""])[0].strip()
                sort = (qs.get("sort") or ["name"])[0].strip().lower()
                order_by = "country ASC NULLS LAST, name ASC" if sort == "country" else "name ASC"

                # `organizations` is the real table for this entity. It is EMPTY today
                # (verified live against Neon), but check on every request — rather than
                # hardcoding that fact — so this endpoint switches itself over automatically
                # the day the table gets populated, with no server code change needed.
                org_count = pg_rows("SELECT COUNT(*) AS n FROM organizations")[0]["n"]
                if org_count > 0:
                    where = []
                    params = []
                    if q:
                        where.append("name ILIKE %s")
                        params.append("%" + q + "%")
                    if country:
                        where.append("country ILIKE %s")
                        params.append(country)
                    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
                    sql = (
                        "SELECT id, name, country, org_type::text AS type, website, description "
                        "FROM organizations" + where_sql +
                        " ORDER BY " + order_by + ", id ASC LIMIT %s"
                    )
                    params.append(limit)
                    return self._send_json(pg_rows(sql, tuple(params)))

                # Fallback: organizations table empty → derive companies from experts whose
                # org_type marks them non-academic (company / ngo_gov / culinary), grouped by
                # employer name (current_org, falling back to affiliation). NOTE (verified
                # live): experts.org_type is NULL for ALL 3,129 experts today, so this branch
                # currently returns [] — it is real, forward-compatible SQL, not a stub; it
                # will start returning rows the moment org_type gets backfilled. Not fabricated.
                where = [
                    "e.org_type IS NOT NULL",
                    "e.org_type != 'academy'",
                    "COALESCE(e.current_org, e.affiliation) IS NOT NULL",
                ]
                params = []
                if q:
                    where.append("COALESCE(e.current_org, e.affiliation) ILIKE %s")
                    params.append("%" + q + "%")
                if country:
                    where.append("e.country ILIKE %s")
                    params.append(country)
                sql = (
                    "SELECT MIN(e.id) AS id, COALESCE(e.current_org, e.affiliation) AS name, "
                    "MODE() WITHIN GROUP (ORDER BY e.country) AS country, "
                    "MODE() WITHIN GROUP (ORDER BY e.org_type::text) AS type, "
                    "COUNT(*) AS expert_count "
                    "FROM experts e WHERE " + " AND ".join(where) + " "
                    "GROUP BY COALESCE(e.current_org, e.affiliation) "
                    "ORDER BY " + order_by + " LIMIT %s"
                )
                params.append(limit)
                return self._send_json(pg_rows(sql, tuple(params)))

            if path == "/api/db-facets":
                entity = (qs.get("entity") or [""])[0].strip().lower()
                if entity == "molecules":
                    rows = pg_rows(
                        "SELECT DISTINCT category FROM molecules "
                        "WHERE category IS NOT NULL ORDER BY category"
                    )
                    return self._send_json({"categories": [r["category"] for r in rows]})
                if entity == "experts":
                    rows = pg_rows(
                        "SELECT DISTINCT country FROM experts "
                        "WHERE country IS NOT NULL ORDER BY country"
                    )
                    return self._send_json({"countries": [r["country"] for r in rows]})
                if entity == "companies":
                    org_count = pg_rows("SELECT COUNT(*) AS n FROM organizations")[0]["n"]
                    if org_count > 0:
                        rows = pg_rows(
                            "SELECT DISTINCT country FROM organizations "
                            "WHERE country IS NOT NULL ORDER BY country"
                        )
                    else:
                        rows = pg_rows(
                            "SELECT DISTINCT country FROM experts "
                            "WHERE country IS NOT NULL AND org_type IS NOT NULL "
                            "AND org_type != 'academy' ORDER BY country"
                        )
                    return self._send_json({"countries": [r["country"] for r in rows]})
                if entity == "sources":
                    topic_rows = pg_rows(
                        "SELECT DISTINCT t.slug, t.name FROM topics t "
                        "JOIN source_topics st ON st.topic_id = t.id "
                        "ORDER BY t.name"
                    )
                    year_rows = pg_rows(
                        "SELECT MIN(year) AS year_min, MAX(year) AS year_max "
                        "FROM sources WHERE year IS NOT NULL"
                    )
                    yr = year_rows[0] if year_rows else {"year_min": None, "year_max": None}
                    return self._send_json({
                        "topics": [{"slug": r["slug"], "name": r["name"]} for r in topic_rows],
                        "year_min": yr["year_min"],
                        "year_max": yr["year_max"],
                    })
                return self._send_json({"error": "unknown entity " + entity}, 400)

            return self._send_json({"error": "unknown endpoint " + path}, 404)
        except Exception as e:
            return self._send_json({"error": "database error: " + str(e)[:200]}, 503)

    # ─── template gallery listing (no DB) ───
    def _list_templates(self):
        """List app/templates/*.html (except the gallery index) for /api/templates."""
        out = []
        try:
            for fname in sorted(os.listdir(TEMPLATES_DIR)):
                if not fname.endswith(".html") or fname == "index.html":
                    continue
                stem = os.path.splitext(fname)[0]
                out.append({
                    "file": fname,
                    "url": "/templates/" + fname,
                    "name": stem.replace("-", " ").replace("_", " ").title(),
                })
        except FileNotFoundError:
            pass
        return out

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            return json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except Exception:
            return None

    def do_POST(self):
        path = urlparse(self.path).path
        if path != "/api/ask":
            self.send_error(404, "POST not supported for " + path); return

        # Read JSON body
        body = self._read_json_body()
        if body is None:
            self.send_error(400, "Bad JSON"); return
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
    # ThreadingHTTPServer so a long Oracle SSE stream doesn't block other requests
    # (paper lookups, expert-map fetches, static assets) served concurrently.
    httpd = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    candidates = ["app/meatcode_mockup.html", "meatcode_mockup.html",
                  "app/MeatCODE_Mockup_GFI_v7.html"]
    mock = next((c for c in candidates if os.path.exists(os.path.join(SERVE_DIR, c))), candidates[0])
    print(f"\n  MeatCODE server running on http://localhost:{PORT}")
    print(f"  Mockup:    http://localhost:{PORT}/{mock}")
    print(f"  Templates: http://localhost:{PORT}/templates/   (Claude Design gallery)")
    print(f"  Model:     {MODEL}")
    print(f"  Database:  {'connected via DATABASE_URL' if DATABASE_URL else 'NOT set — /api/experts & /api/papers 503; mockup uses demo data'}")
    print(f"  Press Ctrl+C to stop.\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped.")

if __name__ == "__main__":
    main()
