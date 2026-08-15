#!/usr/bin/env python3
# Last updated: 2026-08-15 · Fullstack Engineer · features.json became a REGISTRY (schema v2:
#   kind/added/status/where/destination/url per entry, alongside the unchanged dev+prod booleans).
#   save_flags() now preserves non-`flags` top-level keys (e.g. `_schema`) instead of clobbering them.
#   NEW POST /api/flags/upsert (same RELEASE_CENTER=1 + loopback local-admin gate as /api/flags/set,
#   404 anywhere else) creates or updates a whole registry entry — validated key/kind/status, string
#   fields whitelisted, where={screen,spot,file}, dev/prod coerced to bool, sane defaults so a new
#   entry is never half-formed. GET /api/flags/all already returned the FULL entry objects, so the
#   Dev Area hub can render dates + locations; GET /api/flags still returns only per-env booleans and
#   the ff-<key> body-class mechanism is untouched.
# Prev 2026-08-15 · Fullstack Engineer · GET /api/release/history is now visible on the hosted
#   DEV site too (gate: _local_admin_ok() OR APP_ENV=="dev"; production keeps the 404). Powers the new
#   read-only app/dev/versions.html screen. Hardened _release_history for hosts without a usable git
#   checkout (Render): fetch stays best-effort, for-each-ref failure → {"versions":[],"note":"history
#   unavailable on this host"} instead of a 500, current commit falls back origin/main → HEAD. The
#   rollback POST is untouched and stays strictly local-admin (hosted boxes have no git push creds).
# Prev 2026-08-15 · Algorithm Expert · consensus + claims layer on the Oracle stream.
#   (1) NEW additive SSE `event: consensus` on POST /api/ask — after the answer finishes streaming, ONE
#       small Haiku call classifies each retrieved source's main_claim as agree/oppose/neutral toward the
#       answer's central claim; payload {"agree":n,"oppose":n,"neutral":n,"per_source":[{id,stance}]},
#       emitted BEFORE `event: done`. Fully guarded: any failure (model, JSON, DB) skips the event and the
#       stream still ends with `done` — clients that ignore unknown events are untouched.
#   (2) NEW auth-gated GET /api/consensus-demo?q=... — retrieval + the same classification WITHOUT
#       streaming an answer (the classifier infers the majority position from the sources): test surface.
#   (3) Claims layer wired into retrieval: sources retrieved by /api/ask (and consensus-demo) now carry an
#       additive "claims" key ([{id,claim_text,stance,confidence}] from claims via claim_sources) in the
#       existing `sources` SSE payload when rows exist. _RETRIEVAL_SQL additionally selects main_claim.
#   Eval harness lives in analysis/rag_eval/ (closed-corpus answer + verifier scoring; keeps its own copy
#   of the retrieval SQL + grounding prompt — update it if those change here).
# Prev 2026-07-23 · Advisory · Feature flags + Release Center. GET /api/flags (per-env booleans
#   from features.json) & /api/flags/all (full dev+prod matrix). Local-only admin: POST /api/flags/set +
#   /api/release/{deploy-dev,promote}, gated by RELEASE_CENTER=1 AND loopback (404 anywhere else); the
#   admin page app/release-center.html is served only under the same gate. APP_ENV picks each flag's column.
# Prev 2026-07-22 13:55 UTC · Full-Stack Engineer · added GET /api/molecules/{id} — single-molecule
#   detail endpoint powering the new molecule detail PAGE. Returns the molecule row (id/name/category/taste/
#   use_notes) + mentions_count (COUNT from source_molecules, same signal as /api/molecules) + up to 10 linked
#   `papers` (source_molecules → sources, ORDER BY priority_score DESC NULLS LAST, year DESC NULLS LAST),
#   all parameterized via pg_rows. SELECT-only; 404 {"error":"not found"} for a missing id. Regex branch sits
#   next to the list handler and requires a numeric id, so the bare /api/molecules list is NOT shadowed.
# Prev 2026-07-22 12:06 UTC · Full-Stack Engineer · added GET /api/molecule-suggestions —
#   context-aware molecule chips for the Oracle answer panel. Bare JSON array, SELECT-only. Ranks
#   molecules NAMED in the passed question+answer text (m.name substring of q), then whose chemical
#   FAMILY is named (m.category substring of q), then fills by mentions_count DESC; supports ?q, ?limit
#   (default 6, cap 12), ?exclude=id,id (non-ints ignored); deduped by id, exclude always applied.
# Prev 2026-07-20 14:52 UTC · Coordinator (for Data Engineer) · GET /api/molecules is now paginated:
#   `limit` (≤200, default 50) + `offset`, and `meta=1` returns {items,total,limit,offset} so the Molecules
#   pager can show "X of N". Bare (no-meta) calls unchanged. Verified live vs Neon (50/page, total 799, Fats=10).
# Prev 2026-07-20 13:40 UTC · Coordinator · Oracle no longer narrates its own retrieval: the
#   grounding prompt was rewritten so answers never mention the corpus/database/search, never open with a
#   coverage caveat, and never refuse — uncovered parts are answered from general knowledge, UNCITED and
#   unflagged. Guardrail kept: citations are never invented or attached to unsupporting sources.
# Prev 2026-07-20 13:21 UTC · Coordinator · added OPEN `GET /api/version` (live deploy identity:
#   commit/branch/started_at/feature flags — answers "is my push actually live?" without signing in) and
#   `Cache-Control: no-cache, must-revalidate` on HTML so a fresh deploy is never hidden by browser cache.
# Prev 2026-07-20 12:49 UTC · Coordinator (for Data Engineer) · /api/ask now emits an ADDITIVE
#   `event: status` ("retrieving" before the DB query, "answering" before the model streams) so the UI can
#   honestly show "Digging the MeatCODE database…"; SSE headers moved ahead of retrieval to allow it.
#   User-facing error text is now vendor-neutral ("The MeatCODE Oracle is unavailable right now…") with the
#   real diagnostic kept in the server log. Also (2026-07-20 earlier): shared-password Basic Auth gate.
# Previously: 2026-07-08 10:20 UTC · Algorithm Expert · POST /api/ask is now grounded RAG: retrieves
#   the top-6 sources via ts_rank_cd(search_vec, websearch_to_tsquery(...)) filtered to citable +
#   on-topic (relevance_llm >= 60), streams those REAL rows in the existing `sources` SSE event (was
#   hardcoded to []), and grounds Claude's system prompt to answer ONLY from those numbered sources
#   with inline [id] citations (id = the real sources.id, so citation chips still resolve via the
#   existing GET /api/papers/{id}). Falls back to the prior ungrounded behaviour if DATABASE_URL is
#   unset or retrieval fails — never crashes the request. See docs/ORACLE_GROUNDED_RETRIEVAL.md and
#   analysis/oracle_eval/ (retrieval-only sanity check against live Neon).
"""
MeatCODE — single-file Claude API server.

What it does
------------
- Serves every file in the SAME folder as this script (so it serves
  MeatCODE_Mockup_GFI_v7.html / v6.html, the SVGs, the assets, etc.)
- Handles POST /api/ask  →  grounded RAG over the MeatCODE literature corpus:
  retrieves the top-6 sources ranked by Postgres full-text relevance
  (sources.search_vec), grounds Claude's answer in ONLY those sources, and
  streams it back to the Oracle in the exact SSE format the mockup expects:
      event: sources   (REAL retrieved rows; [] if DATABASE_URL is unset or
                         retrieval fails — mockup shows "No matches…")
      event: chunk     (one event per text fragment)
      event: done

Endpoints
---------
  POST /api/ask                 Oracle answer — grounded RAG over Neon `sources`, streamed as SSE
                                 (events: status → sources [each with additive "claims"] → status →
                                  chunk* → consensus [additive, best-effort] → done)
  GET  /api/consensus-demo?q=   auth-gated test surface: runs the same retrieval + agree/oppose/neutral
                                 classification WITHOUT streaming an answer (classifier infers the
                                 majority position from the sources' main claims)
  GET  /api/health              {ok, db_ok, has_anthropic_key, model}
  GET  /api/experts[?q=&country=&sort=&min_relevance=&limit=]  Neon-backed expert list (map, filterable)
  GET  /api/expert-facets       country counts for curated experts (UI filter buttons)
  GET  /api/experts/{id}        single expert (detail panel)
  GET  /api/molecules[?q=&category=&sort=name|popularity&limit=]  Database tab: molecules
                                 (mentions_count = COUNT from source_molecules)
  GET  /api/molecules/{id}      single molecule (detail page): fields + mentions_count + linked papers
  GET  /api/molecule-suggestions[?q=&limit=&exclude=id,id,...]  context-aware molecule chips for the
                                 Oracle answer panel: bare array ranked by molecules named in `q`, then
                                 whose chemical family (category) appears in `q`, then top by mentions_count
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

import os, sys, json, re, threading, base64, hmac, datetime, subprocess, glob
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ─── Config ──────────────────────────────────────────────────────────
PORT       = int(os.environ.get("PORT", "8000"))  # cloud hosts (Render, etc.) inject $PORT; 8000 locally
MODEL      = "claude-sonnet-4-6"           # if you get a model-access error, try "claude-opus-4-8" or "claude-haiku-4-5-20251001"
MAX_TOKENS = 1600
# Consensus classification (the "N support · M oppose" signal) is a single SMALL call per question —
# haiku-class on purpose: it reads the finished answer + ≤6 main_claim snippets and emits ~100 tokens
# of JSON. Sonnet here would multiply cost for zero product benefit.
CONSENSUS_MODEL      = "claude-haiku-4-5-20251001"
CONSENSUS_MAX_TOKENS = 600
ORACLE_TOP_K          = 6    # sources retrieved + handed to Claude per question
ORACLE_MIN_RELEVANCE  = 60   # relevance_llm gate; sources scored below this are off-topic (PROJECT_STATE.md)
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
def load_dotenv(path, skip_empty=False):
    if not path or not os.path.exists(path): return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        # A blank value in an OVERLAY file (e.g. an empty ANTHROPIC_API_KEY= in
        # .env.dev) must never wipe a real value already loaded from .env.
        if skip_empty and v == "": continue
        # .env is authoritative: overwrite any stale shell export (e.g. an old
        # ANTHROPIC_API_KEY left over from `export`), which setdefault would keep.
        os.environ[k] = v

# .env at repo root first (the convention), then next to this script as fallback
load_dotenv(os.path.join(REPO_ROOT, ".env"))
load_dotenv(os.path.join(HERE, ".env"))
# Two-environment support. APP_ENV is set to "dev" by run-local.command and by the
# meatcode-dev Render service; anything else (incl. unset) means production. When dev,
# load .env.dev LAST so local dev runs use the DEV database + DEV key, never production.
# On Render, .env.dev isn't in the repo (gitignored) — the service's own dashboard env
# vars are used instead, so this line is a harmless no-op there.
APP_ENV = os.environ.get("APP_ENV", "prod").strip().lower()
if APP_ENV == "dev":
    load_dotenv(os.path.join(REPO_ROOT, ".env.dev"), skip_empty=True)

# ─── Feature flags (Release Center) ──────────────────────────────────
# features.json is committed (it is config, not a secret): each flag holds a dev + a prod
# boolean, so ONE file drives both environments and each server reads only its own column.
# Reorg-proof file finding: look at the repo root first, else ANYWHERE under it — so
# moving features.json / the .command scripts into a folder like "Release Center" never
# breaks anything. Cached; only re-globs if the remembered path disappears.
_resolve_cache = {}
def _resolve_repo_file(name):
    hit = _resolve_cache.get(name)
    if hit and os.path.exists(hit):
        return hit
    direct = os.path.join(REPO_ROOT, name)
    if os.path.exists(direct):
        _resolve_cache[name] = direct; return direct
    found = glob.glob(os.path.join(REPO_ROOT, "**", name), recursive=True)
    hit = found[0] if found else direct
    _resolve_cache[name] = hit
    return hit

def load_flags():
    """The registry: {key: {label, description, kind, added, status, where, dev, prod, ...}}.
    Only `dev`/`prod` are behavioural (they drive /api/flags → ff-<key> body classes);
    every other key is descriptive metadata rendered by the Dev Area hub."""
    try:
        with open(_resolve_repo_file("features.json"), encoding="utf-8") as _f:
            data = json.load(_f)
        return data.get("flags", {}) if isinstance(data, dict) else {}
    except Exception:
        return {}

def save_flags(flags):
    """Write the registry back, PRESERVING any other top-level keys (e.g. `_schema`)."""
    path = _resolve_repo_file("features.json")
    doc = {}
    try:
        with open(path, encoding="utf-8") as _f:
            existing = json.load(_f)
        if isinstance(existing, dict):
            doc = existing
    except Exception:
        doc = {}
    doc["flags"] = flags
    with open(path, "w", encoding="utf-8") as _f:
        json.dump(doc, _f, indent=2, ensure_ascii=False)
        _f.write("\n")

# Registry fields an /api/flags/upsert call is allowed to write. `dev`/`prod` are coerced
# to booleans; `where` is a {screen, spot, file} object; everything else is a plain string.
FLAG_TEXT_FIELDS = ("label", "description", "kind", "added", "updated", "status",
                    "destination", "url", "note")
FLAG_WHERE_FIELDS = ("screen", "spot", "file")
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


# ─── Oracle retrieval (grounded RAG) ──────────────────────────────────
# RETRIEVE step of docs/DECISION_Oracle_Answer_Engine.docx's phased plan — the
# keyword/full-text phase (semantic/embedding search + reranking are explicitly
# "later" in that doc). Ranks the citable + on-topic corpus by Postgres full-text
# relevance to the question; the GROUND step below hands ONLY those rows to Claude
# so /api/ask can never silently answer from training data when the DB is up.
# Full design notes + empirical before/after numbers: docs/ORACLE_GROUNDED_RETRIEVAL.md.
#
# The query is exactly the spec'd filter: citable (search_vec IS NOT NULL) +
# on-topic (relevance_llm IS NULL OR >= ORACLE_MIN_RELEVANCE), ranked by
# ts_rank_cd. Two deliberate additions on top of that spec, both discovered via
# live testing while building this feature (see analysis/oracle_eval/results.md):
#   1. Outer `WHERE rank > 0` — websearch_to_tsquery ANDs bare words, so ts_rank_cd
#      is provably 0 for any source missing even one query term. Without this
#      filter, LIMIT pads out with zero-relevance rows in arbitrary order whenever
#      fewer than ORACLE_TOP_K truly match — handing Claude (and citing to the
#      user) irrelevant papers instead of honestly returning fewer/zero sources.
#      A SELECT-list alias can't be referenced in the same query's WHERE, hence
#      the subquery.
#   2. An OR-query fallback in _retrieve_sources() below — that same AND-only
#      behaviour meant a natural multi-word question matched 0 rows 10/14 times
#      in the eval set even when the corpus clearly had relevant papers (e.g.
#      "key Maillard reaction products in grilled beef" against a corpus that
#      contains a Maillard-mechanism review). Retrying with the same words OR'd
#      together dropped that to 0/14. Still plain FTS keyword search (this
#      month's phase per the decision doc), not semantic search, and it's PROJECT_
#      STATE.md's own already-flagged next step ("switch to keyword extraction or
#      OR/`|` query semantics to lift recall") — not new scope.
# NOTE: keep in sync with analysis/oracle_eval/run_eval.py, which duplicates this
# SQL + the fallback (deliberately standalone so the eval never imports/requires
# the Anthropic client — see that file's header).
_RETRIEVAL_SQL = """
    SELECT * FROM (
        SELECT id, name AS title, year, COALESCE(journal, venue) AS journal, venue,
               doi, url, abstract, main_claim,
               ts_rank_cd(search_vec, websearch_to_tsquery('english', %s)) AS rank
        FROM sources
        WHERE search_vec IS NOT NULL
          AND (relevance_llm IS NULL OR relevance_llm >= %s)
    ) ranked
    WHERE rank > 0
    ORDER BY rank DESC
    LIMIT %s
"""

def _retrieve_sources(question, limit=ORACLE_TOP_K):
    """Rank the corpus by full-text relevance to `question`. Tries a strict
    AND-match first (precise); if that returns nothing, retries once with the
    same words OR'd together (recall fallback — see the comment block above).
    Returns (rows, used_fallback). `rows` may legitimately be [] — that IS the
    "corpus doesn't cover this" signal, not an error. Raises on DB/connection
    failure; the caller (do_POST) treats a raised exception as "retrieval
    unavailable" and degrades to the pre-RAG ungrounded behaviour, distinct from
    a clean empty result."""
    rows = pg_rows(_RETRIEVAL_SQL, (question, ORACLE_MIN_RELEVANCE, limit))
    if rows:
        return rows, False
    or_query = " OR ".join(question.split())
    if not or_query:
        return [], False
    return pg_rows(_RETRIEVAL_SQL, (or_query, ORACLE_MIN_RELEVANCE, limit)), True


def _public_source_fields(rows):
    """Trim retrieval rows to what the mockup's `sources` SSE handler reads (s.id /
    s.title / s.year / s.journal — see askOracle()'s streamSSE in
    app/meatcode_mockup.html) plus doi/url for future use. `id` here is the REAL
    sources.id: the mockup uses it both as the citation-chip label ("[id]") and as
    the GET /api/papers/{id} lookup key when a chip is clicked, so Claude must cite
    using these same ids (see _grounding_system_prompt below)."""
    return [{
        "id": r["id"],
        "title": r.get("title"),
        "year": r.get("year"),
        "journal": r.get("journal"),
        "doi": r.get("doi"),
        "url": r.get("url"),
    } for r in rows]


# ─── Claims layer (paper claim records attached to retrieval) ─────────
def _claims_for_sources(source_ids):
    """The `claims` table (45 rows, curated stance-tagged claims linked to papers via
    `claim_sources`) existed but nothing read it. This surfaces it: returns
    {source_id: [{id, claim_text, stance, confidence}, ...]} for whichever of the
    retrieved ids have claim rows (most don't yet — 69 links across 818 sources).
    Callers attach it as an ADDITIVE "claims" key on the `sources` SSE payload, so
    clients that don't know the key are untouched. Growth plan for this record:
    analysis/rag_eval/CLAIM_LAYER_NOTES.md."""
    if not source_ids:
        return {}
    rows = pg_rows(
        "SELECT cs.source_id, c.id, c.claim_text, c.stance::text AS stance, "
        "c.confidence::float AS confidence "
        "FROM claim_sources cs JOIN claims c ON c.id = cs.claim_id "
        "WHERE cs.source_id = ANY(%s) "
        "ORDER BY c.confidence DESC NULLS LAST, c.id ASC",
        (list(source_ids),))
    out = {}
    for r in rows:
        out.setdefault(r["source_id"], []).append({
            "id": r["id"], "claim_text": r["claim_text"],
            "stance": r["stance"], "confidence": r["confidence"],
        })
    return out


def _attach_claims(public_rows):
    """Best-effort: decorate _public_source_fields() output with each source's claim
    records. Never raises — a claims-lookup failure must not break the sources event."""
    try:
        cmap = _claims_for_sources([p["id"] for p in public_rows])
        for p in public_rows:
            if p["id"] in cmap:
                p["claims"] = cmap[p["id"]]
    except Exception as e:
        sys.stderr.write("[oracle] claims lookup skipped: %s\n" % str(e)[:200])
    return public_rows


# ─── Consensus classification (agree / oppose / neutral) ─────────────
def _consensus_classify(rows, answer_text=None):
    """ONE small model call that classifies each retrieved source as agree / oppose /
    neutral toward the answer's central claim — the honest "N papers support · M oppose"
    signal. Inputs are only what we actually have: the finished answer (when called from
    /api/ask) and each source's main_claim (falling back to a short abstract snippet).
    When answer_text is None (the /api/consensus-demo path) the classifier first infers
    the majority position from the sources and classifies against that, returning it as
    "central_claim" so the caller can show what was voted on.

    Returns {"agree": n, "oppose": n, "neutral": n, "per_source": [{"id","stance"}]}.
    Raises on any failure — callers guard and simply skip the event (never break the
    stream). Every retrieved source gets a stance; ids the model drops default neutral."""
    def _s(x):
        if x is None:
            return ""
        if isinstance(x, (list, tuple)):
            return " ".join(str(v) for v in x if v)
        return str(x)

    src_lines = []
    for r in rows:
        claim = _s(r.get("main_claim")).strip() or _s(r.get("abstract")).strip()[:300]
        src_lines.append("[%s] %s\nCLAIM: %s" % (
            r["id"], _s(r.get("title"))[:140] or "(untitled)",
            claim[:400] or "(no claim or abstract on file)"))
    if answer_text:
        task = (
            "Below is an ANSWER produced from these sources, then the sources' own main claims.\n"
            "1. Identify the answer's single central claim.\n"
            "2. Classify each source: does its claim support that central claim (agree), "
            "contradict it (oppose), or neither / off-point / insufficient (neutral)?\n\n"
            "ANSWER:\n" + answer_text[:4000]
        )
    else:
        task = (
            "Below are sources' main claims retrieved for the question. No answer exists yet.\n"
            "1. Infer the majority position these sources take on the question — one sentence, "
            "returned as \"central_claim\".\n"
            "2. Classify each source: agree / oppose / neutral toward that position."
        )
    prompt = (
        task + "\n\nSOURCES:\n" + "\n\n".join(src_lines) +
        "\n\nRespond with ONLY a JSON object, no prose, exactly this shape:\n"
        '{"central_claim": "...", "per_source": [{"id": <source id number>, "stance": "agree|oppose|neutral"}]}\n'
        "Include every source id listed above exactly once. Be conservative: when a claim is "
        "tangential or you are unsure, use neutral — never force agreement."
    )
    resp = client.messages.create(
        model=CONSENSUS_MODEL, max_tokens=CONSENSUS_MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("consensus: no JSON in model output")
    data = json.loads(m.group(0))

    stance_of = {}
    for item in data.get("per_source", []):
        try:
            sid = int(item.get("id"))
        except (TypeError, ValueError):
            continue
        stance = str(item.get("stance", "")).strip().lower()
        stance_of[sid] = stance if stance in ("agree", "oppose", "neutral") else "neutral"
    per_source = [{"id": r["id"], "stance": stance_of.get(r["id"], "neutral")} for r in rows]
    out = {
        "agree":   sum(1 for p in per_source if p["stance"] == "agree"),
        "oppose":  sum(1 for p in per_source if p["stance"] == "oppose"),
        "neutral": sum(1 for p in per_source if p["stance"] == "neutral"),
        "per_source": per_source,
    }
    if answer_text is None and data.get("central_claim"):
        out["central_claim"] = str(data["central_claim"])[:400]
    return out


def _format_sources_block(rows):
    """Render retrieved rows as the numbered reference list injected into Claude's
    system prompt. Bracket numbers are the real sources.id (not a 1..N position)
    so an inline [id] citation Claude writes resolves to the correct paper when
    the mockup's citation chip fetches /api/papers/{id}."""
    if not rows:
        return ("SOURCES: (none listed for this question — answer from your own knowledge, "
                "uncited, and say nothing about sources or coverage)")
    parts = []
    for r in rows:
        meta = " · ".join(filter(None, [str(r["year"]) if r.get("year") else None, r.get("journal")]))
        snippet = (r.get("abstract") or "").strip()
        if len(snippet) > 500:
            snippet = snippet[:500].rsplit(" ", 1)[0] + "…"
        parts.append("[%s] %s%s\n%s" % (
            r["id"],
            r.get("title") or "(untitled)",
            (" (" + meta + ")") if meta else "",
            snippet or "(no abstract on file)",
        ))
    return "SOURCES:\n\n" + "\n\n".join(parts)


def _grounding_system_prompt(rows, used_fallback=False):
    """GROUND step: the existing persona/style (SYSTEM_PROMPT, unchanged) plus the
    numbered source list and citation rules.

    Product decision (2026-07-20, Lior): the Oracle must NEVER narrate its own
    retrieval — no "the MeatCODE corpus doesn't cover this", no "the sources
    retrieved are about X", no refusing to answer. Users get a direct answer with
    citations attached where a listed source genuinely supports the point.

    The one guardrail deliberately kept: citations must never be invented or
    attached to claims the source doesn't support. Hiding *provenance commentary*
    is a presentation choice; fabricating attribution would be a credibility
    (and scientific) failure. Uncited sentences are how unsupported material is
    handled — silently, without a disclaimer.

    `used_fallback=True` means rows came from the looser OR-query recall fallback
    (see _retrieve_sources), so the model is told to read abstracts critically —
    silently, without surfacing that to the user."""
    fallback_note = (
        "\nSome listed sources were matched loosely, so term overlap does not "
        "guarantee relevance — read each abstract and only cite ones that actually "
        "address the question. Never mention this matching detail to the user.\n"
        if used_fallback else ""
    )
    return SYSTEM_PROMPT + (
        "\n\nANSWERING RULES (read carefully):\n"
        "Answer the question directly and usefully, in your normal voice.\n"
        "Numbered sources may be listed below. Where one genuinely supports a point "
        "you make, cite it inline using the exact bracket number shown immediately "
        "before that source (for example, if a source is labeled [123], write [123] "
        "in your answer — not [1]).\n"
        "NEVER invent a citation number, and NEVER attach a citation to a claim that "
        "the cited source does not actually support.\n"
        "Where the listed sources do not cover part of the question, simply answer "
        "that part from your own knowledge of flavour and aroma chemistry, leaving it "
        "uncited. Do not flag it, hedge it, or apologise for it.\n"
        "NEVER describe your own information sources or how you obtained anything. Do "
        "not mention the corpus, the database, retrieval, searching, what was or was "
        "not found, or whether something came from the listed sources versus your own "
        "knowledge. Never open with a caveat about coverage, and never say you cannot "
        "answer. Just give the answer." + fallback_note + "\n"
        + _format_sources_block(rows)
    )


# ─── HTTP handler ────────────────────────────────────────────────────
# ─── Optional shared-password gate (HTTP Basic Auth) ─────────────────
# Set SITE_PASSWORD (and optionally SITE_USER, default "meatcode") in the
# environment / Render dashboard to require a username + password for EVERY
# request — static files, the Oracle, and the API. Leave SITE_PASSWORD unset
# (e.g. local dev) and the gate is OFF. Credentials live in env vars, never in
# the repo. The browser prompts once, then reuses them for all fetches too.
SITE_USER = os.environ.get("SITE_USER", "meatcode")
SITE_PASSWORD = os.environ.get("SITE_PASSWORD")   # None/"" → gate disabled

# ─── Build / deploy identity (powers the open /api/version endpoint) ──
# Render injects RENDER_GIT_* automatically on every deploy; empty when running locally.
# This is what makes "is my latest push actually live?" answerable at a glance.
BUILD_COMMIT  = os.environ.get("RENDER_GIT_COMMIT", "")
BUILD_BRANCH  = os.environ.get("RENDER_GIT_BRANCH", "")
BUILD_SERVICE = os.environ.get("RENDER_SERVICE_NAME", "local")
STARTED_AT    = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


class Handler(SimpleHTTPRequestHandler):
    # Serve static files from the folder this script lives in
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=SERVE_DIR, **kw)

    # ─── shared-password gate ───
    def _authorized(self):
        """True if the gate is off, or the request carries valid Basic creds."""
        if not SITE_PASSWORD:
            return True                       # no password set → gate disabled
        hdr = self.headers.get("Authorization", "")
        if hdr.startswith("Basic "):
            try:
                user, _, pw = base64.b64decode(hdr[6:]).decode("utf-8").partition(":")
            except Exception:
                return False
            # constant-time compares avoid leaking length/timing info
            return hmac.compare_digest(user, SITE_USER) and hmac.compare_digest(pw, SITE_PASSWORD)
        return False

    def _deny(self):
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="MeatCODE"')
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        try:
            self.wfile.write(b"Authentication required.")
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))

    # CORS for any browser request (works for file:// origin too)
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        # Force HTML to revalidate on every load. Without this the browser happily
        # serves its cached copy after a deploy — the classic "I pushed but the site
        # still looks the same". Assets keep their normal caching.
        try:
            _p = urlparse(self.path).path
            if _p.endswith(".html") or _p.endswith("/"):
                self.send_header("Cache-Control", "no-cache, must-revalidate")
        except Exception:
            pass
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

    # ─── Release Center: local-only admin capability check ───
    def _local_admin_ok(self):
        # These powers exist ONLY on your local cockpit: RELEASE_CENTER=1 is set solely by
        # release-center.command / run-local on your Mac (never on Render), AND the caller
        # must be loopback. Either check failing → the route behaves as if it doesn't exist.
        host = self.client_address[0] if self.client_address else ""
        return os.environ.get("RELEASE_CENTER") == "1" and host in ("127.0.0.1", "::1", "localhost")

    # Disable directory listings entirely on the public server.
    def list_directory(self, path):
        self.send_error(404, "Not found")
        return None

    # ─── GET: /api/* handled here; everything else = static files ───
    def do_GET(self):
        path = urlparse(self.path).path
        if path not in ("/api/health", "/api/version") and not self._authorized():
            return self._deny()                # health + version stay open (uptime / deploy checks)
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
        # The Release Center page: full controls on the local cockpit; a READ-ONLY
        # view on the hosted dev site (so the in-app H overlay can show it); hidden
        # entirely on production. Write/deploy endpoints stay local-only regardless.
        if low.endswith("release-center.html") and not (self._local_admin_ok() or APP_ENV == "dev"):
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
        # Pretty URL for the internal Agent Command Center dashboard (served over https so
        # its microphone dictation works — browsers block the mic on file:// / sandboxed panels).
        if path in ("/command-center", "/command-center/"):
            self.path = "/app/agent_command_center.html"
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
        if path == "/api/flags":
            # What the mockup reads to switch features on/off for THIS environment.
            flags = load_flags()
            return self._send_json({k: bool(v.get(APP_ENV, False)) for k, v in flags.items()})
        if path == "/api/flags/all":
            # Full dev+prod matrix — powers the Release Center dashboard.
            return self._send_json({"env": APP_ENV, "admin": self._local_admin_ok(), "flags": load_flags()})
        if path == "/api/release/history":
            # Promoted snapshots + which is live. READ-ONLY, so it's also visible on the
            # hosted DEV site (powers app/dev/versions.html); production keeps the 404.
            # The rollback POST stays strictly local-admin — a hosted box has no push creds.
            if not (self._local_admin_ok() or APP_ENV == "dev"):
                return self._send_json({"error": "not found"}, 404)
            return self._release_history()
        if path == "/api/version":
            # OPEN (like /api/health) so deploy status is checkable without signing in.
            # `commit` tells you exactly which push is live; `features` confirms the NEW
            # code is running, not just that *something* is running.
            return self._send_json({
                "service": BUILD_SERVICE,
                "env": APP_ENV,                  # "dev" (staging/local) or "prod" (public site)
                "commit": (BUILD_COMMIT[:12] or "local"),
                "commit_full": BUILD_COMMIT,
                "branch": (BUILD_BRANCH or "local"),
                "server_started_utc": STARTED_AT,
                "model": MODEL,
                "password_gate": bool(SITE_PASSWORD),
                "features": {
                    "sse_status_event": True,        # "Digging the MeatCODE database" phase
                    "vendor_neutral_errors": True,   # no model name in user-facing errors
                    "html_no_cache": True,           # fresh deploys show immediately
                },
            })
        if path == "/api/templates":
            # No DB needed — lists whatever Claude Design exports live in app/templates/.
            return self._send_json(self._list_templates())

        if not DATABASE_URL:
            return self._send_json({"error": "DATABASE_URL not configured"}, 503)
        try:
            if path == "/api/consensus-demo":
                # Test surface for the consensus signal: same retrieval as POST /api/ask,
                # same classifier, but NO streamed answer (and no Sonnet call) — the
                # classifier infers the majority position from the sources' main claims
                # and votes against that. Auth-gated like every other API GET (only
                # /api/health + /api/version are open). Classification failure is
                # reported in-band, not as a 5xx — retrieval results are still useful.
                q = (qs.get("q") or [""])[0].strip()
                if not q:
                    return self._send_json({"error": "missing ?q="}, 400)
                rows, used_fallback = _retrieve_sources(q)
                out = {
                    "question": q,
                    "used_fallback": used_fallback,
                    "sources": _attach_claims(_public_source_fields(rows)),
                }
                if rows:
                    try:
                        out["consensus"] = _consensus_classify(rows)
                    except Exception as e:
                        sys.stderr.write("[oracle] consensus-demo classify failed: %s\n" % str(e)[:300])
                        out["consensus_error"] = "classification unavailable"
                else:
                    out["consensus"] = {"agree": 0, "oppose": 0, "neutral": 0, "per_source": []}
                return self._send_json(out)

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
                # Pagination: `limit` (page size, ≤200) + `offset`. `meta=1` returns
                # {"items":[...], "total":N, "limit":L, "offset":O} for pagers that need
                # the grand total; without meta it returns the bare list (back-compat).
                limit = max(1, min(200, int((qs.get("limit") or ["50"])[0])))
                offset = max(0, int((qs.get("offset") or ["0"])[0]))
                want_meta = (qs.get("meta") or ["0"])[0].strip() in ("1", "true", "yes")
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
                    " ORDER BY " + order_by + ", m.id ASC LIMIT %s OFFSET %s"
                )
                rows = pg_rows(sql, tuple(params + [limit, offset]))
                if not want_meta:
                    return self._send_json(rows)
                # total for the SAME filters (no limit/offset) so the pager can show "X of N"
                total_rows = pg_rows("SELECT COUNT(*) AS total FROM molecules m" + where_sql, tuple(params))
                total = int(total_rows[0]["total"]) if total_rows else 0
                return self._send_json({"items": rows, "total": total, "limit": limit, "offset": offset})

            m = re.match(r"^/api/molecules/(\d+)$", path)
            if m:
                # Single-molecule detail page. Sits AFTER the exact `path == "/api/molecules"`
                # list branch above and matches only a numeric id segment, so the bare
                # /api/molecules list endpoint is never shadowed. Two SELECT-only queries.
                mid = int(m.group(1))
                # (1) the molecule row + mentions_count — same COUNT-from-source_molecules
                #     LEFT JOIN pattern as /api/molecules, narrowed to this id.
                rows = pg_rows(
                    "SELECT m.id, m.name, m.category, m.taste, m.use_notes, "
                    "COALESCE(sm.mentions_count, 0)::int AS mentions_count "
                    "FROM molecules m "
                    "LEFT JOIN (SELECT molecule_id, COUNT(*) AS mentions_count "
                    "FROM source_molecules GROUP BY molecule_id) sm ON sm.molecule_id = m.id "
                    "WHERE m.id = %s",
                    (mid,))
                if not rows:
                    return self._send_json({"error": "not found"}, 404)
                molecule = rows[0]
                # (2) the sources LINKED to this molecule via the source_molecules junction
                #     (join source_molecules → sources on source_id), most-relevant/most-
                #     recent first, capped at 10 for the detail panel.
                molecule["papers"] = pg_rows(
                    "SELECT s.id, s.name, s.year, s.journal, s.doi, s.url "
                    "FROM source_molecules sm JOIN sources s ON s.id = sm.source_id "
                    "WHERE sm.molecule_id = %s "
                    "ORDER BY s.priority_score DESC NULLS LAST, s.year DESC NULLS LAST, s.id DESC "
                    "LIMIT 10",
                    (mid,))
                return self._send_json(molecule)

            if path == "/api/molecule-suggestions":
                # Context-aware molecule chips for the Oracle answer panel: given the
                # question + answer prose (`q`), surface the molecules most relevant to it.
                # Ranking (all case-insensitive, matched AGAINST `q` so long free text works):
                #   (1) molecules NAMED in the text  — m.name is a substring of q;
                #   (2) molecules whose chemical FAMILY is named — m.category is a substring of q
                #       ("pyrazines", "aldehydes", "sulfur", …);
                #   (3) fill remaining slots with the most-referenced molecules (mentions_count DESC).
                # `exclude` (CSV of ids; non-integers ignored) drops chips already on screen; rows are
                # inherently deduped by id (one row per molecule via the aggregated join) and capped to
                # `limit`. Blank q → every match_rank is 0, so it degrades to pure top-by-mentions.
                # SELECT-only; `q` and the id list are bound params (never interpolated). Same LEFT JOIN
                # for mentions_count as /api/molecules; returns the bare array the frontend consumes.
                limit = max(1, min(12, int((qs.get("limit") or ["6"])[0])))
                q = (qs.get("q") or [""])[0].strip()

                exclude_ids = []
                for tok in (qs.get("exclude") or [""])[0].split(","):
                    tok = tok.strip()
                    if not tok:
                        continue
                    try:
                        exclude_ids.append(int(tok))
                    except ValueError:
                        pass  # parse defensively — silently ignore non-integer ids

                where = []
                params = []
                if exclude_ids:
                    # <> ALL(array) instead of NOT IN (…) so an id list of any length is one bound
                    # param; only added when non-empty (avoids an untyped empty-array cast issue).
                    where.append("m.id <> ALL(%s)")
                    params.append(exclude_ids)
                where_sql = (" WHERE " + " AND ".join(where)) if where else ""

                # Score in SQL: name-in-q (2) outranks category-in-q (1) outranks everything else
                # (0); mentions_count breaks ties within every tier, so tier 3 naturally becomes
                # "top by mentions". The <> '' guards stop a blank name/category matching all of q
                # via '%%'. '%%' is the psycopg2-escaped literal '%' → the pattern '%<name>%'.
                sql = (
                    "SELECT m.id, m.name, m.category, m.taste, "
                    "COALESCE(sm.mentions_count, 0)::int AS mentions_count "
                    "FROM molecules m "
                    "LEFT JOIN (SELECT molecule_id, COUNT(*) AS mentions_count "
                    "FROM source_molecules GROUP BY molecule_id) sm ON sm.molecule_id = m.id" +
                    where_sql +
                    " ORDER BY (CASE "
                    "WHEN m.name IS NOT NULL AND m.name <> '' AND %s ILIKE '%%' || m.name || '%%' THEN 2 "
                    "WHEN m.category IS NOT NULL AND m.category <> '' AND %s ILIKE '%%' || m.category || '%%' THEN 1 "
                    "ELSE 0 END) DESC, mentions_count DESC NULLS LAST, m.id ASC "
                    "LIMIT %s"
                )
                params.extend([q, q, limit])
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

    def _release_history(self):
        """List promoted snapshots (prod-* tags) newest-first + which one is live.

        Degrades gracefully on hosts without a usable git checkout (e.g. the Render
        container may lack git, the .git dir, or an `origin` remote): the fetch is
        best-effort, we fall back to listing LOCAL tags, and if even that fails we
        return {"versions": [], "note": "history unavailable on this host"} — never a 500.
        """
        try:
            try:
                # Best-effort refresh of tags — fine to fail (no network / no origin).
                subprocess.run(["git", "-C", REPO_ROOT, "fetch", "origin", "--tags", "--quiet"],
                               capture_output=True, text=True, timeout=25)
            except Exception:
                pass
            fmt = "%(refname:short)\t%(creatordate:format:%Y-%m-%d %H:%M)\t%(objectname:short)\t%(subject)"
            r = subprocess.run(["git", "-C", REPO_ROOT, "for-each-ref", "--sort=-creatordate",
                                "--format", fmt, "refs/tags/prod-*"],
                               capture_output=True, text=True, timeout=15)
            if r.returncode != 0:
                # Not a git checkout at all → honest empty answer, not an error.
                return self._send_json({"current": None, "current_commit": "",
                                        "versions": [], "note": "history unavailable on this host"})
            versions = []
            for line in r.stdout.splitlines():
                p = line.split("\t")
                if len(p) >= 3:
                    versions.append({"tag": p[0], "date": p[1], "commit": p[2],
                                     "subject": (p[3] if len(p) > 3 else "")})
            cur = ""
            try:
                cur = subprocess.run(["git", "-C", REPO_ROOT, "rev-parse", "--short", "origin/main"],
                                     capture_output=True, text=True, timeout=15).stdout.strip()
                if not cur or " " in cur:   # "origin/main" missing → rev-parse error text
                    cur = ""
            except Exception:
                cur = ""
            if not cur:
                try:
                    # No origin/main ref — use HEAD (what this host is actually running).
                    cur = subprocess.run(["git", "-C", REPO_ROOT, "rev-parse", "--short", "HEAD"],
                                         capture_output=True, text=True, timeout=15).stdout.strip()
                except Exception:
                    cur = ""
            current_tag = next((v["tag"] for v in versions if v["commit"] == cur), None)
            return self._send_json({"current": current_tag, "current_commit": cur,
                                    "versions": versions})
        except Exception:
            # Missing git binary (FileNotFoundError) or anything else unexpected.
            return self._send_json({"current": None, "current_commit": "",
                                    "versions": [], "note": "history unavailable on this host"})

    def _handle_admin_post(self, path):
        """Release Center actions — reachable only after _local_admin_ok() passes."""
        if path == "/api/flags/set":
            body = self._read_json_body() or {}
            key = str(body.get("key", "")).strip()
            env = str(body.get("env", "")).strip().lower()
            val = bool(body.get("value"))
            flags = load_flags()
            if key not in flags or env not in ("dev", "prod"):
                return self._send_json({"error": "unknown flag or env"}, 400)
            flags[key][env] = val
            save_flags(flags)
            return self._send_json({"ok": True, "flags": flags})
        if path == "/api/flags/upsert":
            # Create OR update a whole registry entry, so a new feature/screen can be
            # registered from the Dev Area hub instead of hand-editing features.json.
            body = self._read_json_body() or {}
            key = str(body.get("key", "")).strip()
            if not re.match(r"^[a-z0-9][a-z0-9_]{1,48}$", key):
                return self._send_json({"error": "key must be lowercase a-z0-9_ (2-49 chars)"}, 400)
            flags = load_flags()
            entry = dict(flags.get(key) or {})
            is_new = key not in flags
            for f in FLAG_TEXT_FIELDS:
                if f in body and body[f] is not None:
                    entry[f] = str(body[f]).strip()
            if "where" in body and isinstance(body["where"], dict):
                where = dict(entry.get("where") or {})
                for f in FLAG_WHERE_FIELDS:
                    if f in body["where"] and body["where"][f] is not None:
                        where[f] = str(body["where"][f]).strip()
                entry["where"] = where
            for env in ("dev", "prod"):
                if env in body:
                    entry[env] = bool(body[env])
            # Sensible defaults so a new entry is never half-formed.
            entry.setdefault("label", key)
            entry.setdefault("kind", "feature")
            entry.setdefault("status", "placeholder")
            entry.setdefault("added", datetime.date.today().isoformat())
            entry.setdefault("dev", True)
            entry.setdefault("prod", False)
            if entry.get("kind") not in ("feature", "screen"):
                return self._send_json({"error": "kind must be 'feature' or 'screen'"}, 400)
            if entry.get("status") not in ("live", "preview", "placeholder"):
                return self._send_json({"error": "status must be live|preview|placeholder"}, 400)
            flags[key] = entry
            save_flags(flags)
            return self._send_json({"ok": True, "created": is_new, "key": key,
                                    "entry": entry, "flags": flags})
        if path in ("/api/release/deploy-dev", "/api/release/promote"):
            script = "deploy-dev.command" if path.endswith("deploy-dev") else "promote-to-prod.command"
            target = _resolve_repo_file(script)
            if not os.path.exists(target):
                return self._send_json({"error": script + " not found"}, 404)
            try:
                # Open it in Terminal so YOUR "type yes" confirm still gates the deploy.
                subprocess.Popen(["open", target])
            except Exception as e:
                return self._send_json({"error": str(e)}, 500)
            return self._send_json({"ok": True, "launched": script})
        if path == "/api/release/rollback":
            body = self._read_json_body() or {}
            tag = str(body.get("tag", "")).strip()
            # Only real prod-* snapshots — never an arbitrary ref.
            if not re.match(r"^prod-[0-9-]+$", tag):
                return self._send_json({"error": "bad snapshot name"}, 400)
            chk = subprocess.run(["git", "-C", REPO_ROOT, "rev-parse", "--verify", "--quiet", tag + "^{commit}"],
                                 capture_output=True, text=True)
            if chk.returncode != 0:
                return self._send_json({"error": "unknown snapshot"}, 404)
            push = subprocess.run(["git", "-C", REPO_ROOT, "push", "origin", tag + "^{commit}:main",
                                   "--force-with-lease"], capture_output=True, text=True)
            if push.returncode != 0:
                return self._send_json({"error": (push.stderr or push.stdout or "rollback failed").strip()}, 500)
            return self._send_json({"ok": True, "rolled_back_to": tag})
        return self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        # ── Local Release Center admin — exists ONLY on the local cockpit (RELEASE_CENTER=1
        #    + loopback); returns 404 anywhere else, so a hosted server can never be driven. ──
        if path in ("/api/flags/set", "/api/flags/upsert", "/api/release/deploy-dev",
                    "/api/release/promote", "/api/release/rollback"):
            if not self._local_admin_ok():
                self.send_error(404, "Not found"); return
            return self._handle_admin_post(path)
        if not self._authorized():
            return self._deny()
        if path != "/api/ask":
            self.send_error(404, "POST not supported for " + path); return

        # Read JSON body
        body = self._read_json_body()
        if body is None:
            self.send_error(400, "Bad JSON"); return
        question = (body.get("question") or "").strip()
        if not question:
            self.send_error(400, "Missing 'question'"); return

        # ─── RETRIEVE — before opening the SSE stream, so the very first event can
        # carry the real citation set (matches docs/DECISION_Oracle_Answer_Engine.docx:
        # understand → find → pick top few → write). DATABASE_URL missing → identical
        # to the pre-RAG behaviour (empty sources, ungrounded answer). Any retrieval
        # exception (bad connection, Neon asleep/unreachable, psycopg2 missing, etc.)
        # degrades the same way instead of crashing the request — that is NOT treated
        # as "corpus doesn't cover this" (misleading if the DB is just unreachable);
        # only a clean zero-row result earns that message (see _grounding_system_prompt).
        sources_rows = []
        used_fallback = False
        retrieval_ok = True

        # SSE response — headers go out BEFORE retrieval runs, so we can emit an
        # honest "retrieving" phase while the DB query is actually in flight (the UI
        # shows "Digging the MeatCODE database…" during it). Everything from here on
        # is a committed 200; retrieval failures degrade gracefully rather than 500.
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

        # 0) status: retrieving — ADDITIVE and backward-compatible. Clients that
        #    ignore `status` behave exactly as before (sources → chunk → done).
        send_event("status", "retrieving")

        if DATABASE_URL:
            try:
                sources_rows, used_fallback = _retrieve_sources(question)
            except Exception as e:
                retrieval_ok = False
                sys.stderr.write("[oracle] retrieval error: %s\n" % str(e)[:300])
        grounded = bool(DATABASE_URL) and retrieval_ok

        # 1) sources event — the REAL rows retrieved above (grounded RAG; this used
        #    to be hardcoded "[]"). The Oracle UI still handles an empty array
        #    gracefully for the DB-missing / retrieval-failed / genuinely-nothing-
        #    matched cases. Each source additionally carries a "claims" key (its rows
        #    from the curated `claims` table, when any exist) — ADDITIVE, best-effort.
        send_event("sources", json.dumps(_attach_claims(_public_source_fields(sources_rows)), default=str))

        # 2) GROUND + stream — the answer as chunk events, grounded in those sources
        #    when retrieval worked; the untouched original SYSTEM_PROMPT otherwise
        #    (graceful fallback). Model/config/messages shape unchanged.
        system_prompt = _grounding_system_prompt(sources_rows, used_fallback) if grounded else SYSTEM_PROMPT
        send_event("status", "answering")
        try:
            answer_parts = []
            with client.messages.stream(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=system_prompt,
                messages=[{"role": "user", "content": question}],
            ) as stream:
                for text in stream.text_stream:
                    if text:
                        answer_parts.append(text)
                        send_event("chunk", text)

            # 3) consensus event — ADDITIVE, emitted BEFORE `done`, and fully guarded:
            #    one small Haiku call classifies each retrieved source's main_claim as
            #    agree/oppose/neutral toward the finished answer's central claim, so the
            #    UI can honestly show "N papers support · M oppose". ANY failure here
            #    (model, JSON parse, timeout) skips the event entirely — the stream
            #    still ends with `done`, and clients that ignore unknown SSE events
            #    (the current mockup) behave exactly as before.
            if grounded and sources_rows:
                try:
                    consensus = _consensus_classify(sources_rows, "".join(answer_parts))
                    send_event("consensus", json.dumps(consensus, default=str))
                except Exception as e:
                    sys.stderr.write("[oracle] consensus skipped: %s\n" % str(e)[:300])
            send_event("done", "")
        except Exception as e:
            # Keep the real diagnostic in the server log (Render → Logs), but show the
            # user vendor-neutral product language — never name the model provider.
            sys.stderr.write("[oracle] answer error: %s\n" % str(e)[:300])
            send_event("error", "The MeatCODE Oracle is unavailable right now. Please try again in a moment.")


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
