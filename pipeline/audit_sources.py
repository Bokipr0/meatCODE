#!/usr/bin/env python3
# Last updated: 2026-07-07 10:32 UTC · Data Engineer (audit loop) · new orchestrator
"""Recurring data-authentication loop — SELECTION + ORCHESTRATION layer.

Every run (intended cadence: every 2 days) this script:
  1. Pulls a CANDIDATE POOL from Neon, biased toward never-audited / least-recently
     audited sources and higher priority_score (so nothing is starved and the most
     important rows come first). SELECT-only on existing tables.
  2. For each candidate it assembles the full "what do we know about this source"
     view: its stored metadata, the taxonomy TOPICS it is tagged to (source_topics
     -> topics), and the taxonomy QUERIES/KEYWORDS that connect to it (matched to
     those topics via the bible db/taxonomy/keywords_topics.json). This is the heart
     of the deliverable — surfacing info + tagging + connected queries per source.
  3. Ranks the pool by dynamic audit priority and judges the top N for
     tag-correctness / relevance / quality, producing a keep|review|quarantine
     verdict per source.
  4. Writes the verdicts to the `source_audits` table (migration 0003) AND to a
     human-readable markdown report under docs/audits/<YYYY-MM-DD>.md.

The scoring/judging brains live in a sibling module `audit_judge.py` (owned by the
Algorithm Expert). We import it; if it is absent or --mock-judge is passed we fall
back to a self-contained heuristic so this script always runs standalone.

Contract expected from audit_judge (see EXPECTED INPUT SCHEMA below for the dicts
we hand it):
    rank_for_audit(candidates: list[dict], weights: dict | None = None) -> list[dict]
        # returns candidates sorted by DESC audit priority, each gaining 'audit_priority': float
    judge_source(source: dict) -> dict
        # -> {tag_score:int(0-100), tag_issues:list[str], relevance_score:int(0-100),
        #     quality_score:int(0-100), verdict:'keep'|'review'|'quarantine', notes:str}
    DEFAULT_WEIGHTS: dict
    update_weights(prev_weights: dict, audit_results: list[dict]) -> dict

EXPECTED INPUT SCHEMA — each candidate dict this module builds and passes in:
    id, name(title), year, journal, venue, doi, authors,
    abstract(truncated), abstract_len, citation_count, priority_score,
    relevance_llm, is_review, top_keywords, ingest_query,
    tags:      list[{slug, name, branch, priority, level}]   # taxonomy topics it carries
    branches:  list[str]                                     # distinct branches of those tags
    queries:   list[{keyword, branch, priority, slug}]       # taxonomy queries that connect to it
    query_keywords: list[str]
    last_audited: datetime|None, audit_count: int

Usage:
    python3 pipeline/audit_sources.py [--n 20] [--dry-run] [--mock-judge]
                                      [--pool 150] [--weights weights.json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# Shared Neon accessor — prefer the repo's db.connect; fall back to a direct
# psycopg2 connection from .env so this script stays self-sufficient even when
# db/connect.py isn't present locally (some syncs leave only its .pyc).
try:
    from db.connect import get_conn       # shared accessor — do NOT reinvent
except Exception:
    def _load_env_once():
        envp = REPO_ROOT / ".env"
        if not envp.exists():
            return
        for _line in envp.read_text(encoding="utf-8").splitlines():
            _line = _line.strip()
            if not _line or _line.startswith("#") or "=" not in _line:
                continue
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

    def get_conn():
        """Direct Neon connection from DATABASE_URL (fallback)."""
        _load_env_once()
        url = os.environ.get("DATABASE_URL")
        if not url:
            raise RuntimeError("DATABASE_URL not set (checked environment and .env)")
        import psycopg2
        return psycopg2.connect(url)

from db import taxonomy                   # the governing bible loader

POOL_DEFAULT = 150
N_DEFAULT = 20

# ---------------------------------------------------------------------------
# Candidate dict fields pulled straight from `sources`.
SOURCE_COLS = ("id", "name", "year", "journal", "venue", "doi", "authors",
               "abstract", "citation_count", "priority_score", "relevance_llm",
               "is_review", "top_keywords", "search_query")
ABSTRACT_TRUNC = 800


# ===========================================================================
# MOCK judge (fallback so this script runs standalone before audit_judge exists)
# ===========================================================================
MOCK_WEIGHTS = {"staleness": 1.0, "priority": 1.0, "relevance_gap": 0.8,
                "tag_gap": 0.6, "citation": 0.4}

CUR_YEAR = 2026
CORE_JOURNALS = (
    "food chemistry", "journal of agricultural and food chemistry", "meat science",
    "food research international", "comprehensive reviews in food science",
    "flavour and fragrance", "journal of the science of food and agriculture",
    "trends in food science", "npj science of food", "lwt", "molecules", "foods",
)
TOPIC_RX = re.compile(
    r"(meat|beef|pork|chicken|poultry|flavou?r|aroma|volatile|umami|maillard|"
    r"strecker|lipid oxidation|sensory|odou?r|hydrolysate|yeast extract|"
    r"process flavou?r|precursor|thiamine|furan|sulf)", re.I)


def mock_rank_for_audit(candidates: list[dict], weights: dict | None = None) -> list[dict]:
    """Heuristic dynamic-priority ranking. Prefers stale / high-priority /
    low-relevance / untagged sources — i.e. the ones most worth re-checking."""
    w = weights or MOCK_WEIGHTS
    now = datetime.now(timezone.utc)
    for c in candidates:
        la = c.get("last_audited")
        if la is None:
            stale = 1.0
        elif isinstance(la, datetime):
            days = (now - la).days
            stale = min(1.0, max(0.0, days) / 14.0)   # ~2 audit cycles -> fully stale
        else:
            stale = 0.5
        prio = (c.get("priority_score") or 0) / 100.0
        rel = c.get("relevance_llm")
        rel_gap = (1.0 - rel / 100.0) if rel is not None else 0.4   # low rel = worth a look
        tag_gap = 1.0 if not c.get("tags") else 0.0
        impact = min(1.0, (c.get("citation_count") or 0) / 200.0)
        c["audit_priority"] = round(float(
            w.get("staleness", 1.0) * stale
            + w.get("priority", 1.0) * prio
            + w.get("relevance_gap", 0.8) * rel_gap
            + w.get("tag_gap", 0.6) * tag_gap
            + w.get("citation", 0.4) * impact), 4)
    return sorted(candidates, key=lambda c: c.get("audit_priority", 0.0), reverse=True)


def mock_judge_source(s: dict) -> dict:
    """Self-contained tag / relevance / quality heuristic -> verdict."""
    text = f"{s.get('name', '')} {s.get('abstract', '')}".lower()
    tags = s.get("tags") or []

    # --- tag correctness -----------------------------------------------------
    if not tags:
        tag_score = 20
        tag_issues = ["no taxonomy topics tagged (source_topics empty)"]
    else:
        tag_issues, supported = [], 0
        for t in tags:
            toks = [w for w in re.split(r"[^a-z0-9]+", (t.get("name") or "").lower()) if len(w) > 3]
            if toks and any(w in text for w in toks):
                supported += 1
            else:
                tag_issues.append(f"tag '{t.get('name')}' not evident in title/abstract")
        tag_score = int(round(40 + 60 * (supported / len(tags))))
        if len(tags) > 6:
            tag_issues.append("many tags (>6) — possible over-tagging")

    # --- relevance -----------------------------------------------------------
    rel_llm = s.get("relevance_llm")
    if rel_llm is not None:
        relevance_score = int(rel_llm)
    else:
        relevance_score = 70 if TOPIC_RX.search(text) else 30

    # --- quality -------------------------------------------------------------
    q = 0.0
    journal = (s.get("journal") or s.get("venue") or "").lower()
    if journal:
        q += 30 if any(k in journal for k in CORE_JOURNALS) else 12
    if s.get("doi"):
        q += 12
    if s.get("abstract"):
        q += 12
    if s.get("is_review"):
        q += 12
    cites, year = s.get("citation_count"), s.get("year")
    if cites and year:
        q += min(22.0, (cites / max(1, CUR_YEAR - year)) * 3)
    if year and year >= 2018:
        q += 10
    quality_score = int(round(min(100.0, q)))

    # --- verdict -------------------------------------------------------------
    if relevance_score < 40:
        verdict = "quarantine"
    elif relevance_score >= 60 and tag_score >= 50 and quality_score >= 40:
        verdict = "keep"
    else:
        verdict = "review"

    notes = (f"mock heuristic — relevance {relevance_score}, "
             f"{len(tags)} tag(s) score {tag_score}, quality {quality_score}"
             + (f"; {len(tag_issues)} tag issue(s)" if tag_issues else ""))
    return {"tag_score": tag_score, "tag_issues": tag_issues,
            "relevance_score": relevance_score, "quality_score": quality_score,
            "verdict": verdict, "notes": notes}


def mock_update_weights(prev_weights: dict, audit_results: list[dict]) -> dict:
    """Gentle nudge: if a run surfaces many quarantines, lean harder on the
    relevance gap next time (find more suspect rows). Placeholder — the real
    weight-evolution logic is the Algorithm Expert's in audit_judge.update_weights."""
    nxt = dict(prev_weights)
    if audit_results:
        q_frac = sum(1 for r in audit_results if r.get("verdict") == "quarantine") / len(audit_results)
        nxt["relevance_gap"] = round(min(2.0, nxt.get("relevance_gap", 0.8) * (1 + 0.2 * q_frac)), 3)
    return nxt


# ===========================================================================
# DB read helpers (SELECT-only on existing tables)
# ===========================================================================
def table_exists(cur, name: str) -> bool:
    cur.execute("select to_regclass(%s)", (f"public.{name}",))
    return cur.fetchone()[0] is not None


def fetch_pool(cur, pool_size: int, have_audits: bool) -> list[dict]:
    """Candidate pool biased to never-audited / least-recently-audited + high priority."""
    cols = ", ".join(f"s.{c}" for c in SOURCE_COLS)
    if have_audits:
        sql = f"""
            SELECT {cols}, la.last_audited, la.audit_count
            FROM sources s
            LEFT JOIN (
                SELECT source_id, max(audited_at) AS last_audited, count(*) AS audit_count
                FROM source_audits GROUP BY source_id
            ) la ON la.source_id = s.id
            ORDER BY (la.last_audited IS NOT NULL) ASC,   -- never-audited first
                     la.last_audited ASC NULLS FIRST,     -- then least-recently audited
                     s.priority_score DESC NULLS LAST     -- then most important
            LIMIT %s
        """
    else:
        sql = f"""
            SELECT {cols}, NULL::timestamptz AS last_audited, 0 AS audit_count
            FROM sources s
            ORDER BY s.priority_score DESC NULLS LAST
            LIMIT %s
        """
    cur.execute(sql, (pool_size,))
    rows = cur.fetchall()
    out = []
    for r in rows:
        d = dict(zip(SOURCE_COLS, r[:len(SOURCE_COLS)]))
        d["last_audited"] = r[len(SOURCE_COLS)]
        d["audit_count"] = r[len(SOURCE_COLS) + 1] or 0
        # normalise / enrich
        d["priority_score"] = float(d["priority_score"]) if d["priority_score"] is not None else None
        d["ingest_query"] = d.pop("search_query", None)
        abs = d.get("abstract") or ""
        d["abstract_len"] = len(abs)
        d["abstract"] = (abs[:ABSTRACT_TRUNC] + " …") if len(abs) > ABSTRACT_TRUNC else abs
        out.append(d)
    return out


def attach_tags_and_queries(cur, pool: list[dict]) -> None:
    """Populate tags / branches / queries (taxonomy) on each candidate in place."""
    ids = [c["id"] for c in pool]
    if not ids:
        return
    cur.execute("""
        SELECT st.source_id, t.slug, t.name, t.root_branch, t.level
        FROM source_topics st
        JOIN topics t ON t.id = st.topic_id
        WHERE st.source_id = ANY(%s)
    """, (ids,))
    by_src: dict[int, list[dict]] = {}
    for sid, slug, name, branch, level in cur.fetchall():
        by_src.setdefault(sid, []).append(
            {"slug": slug, "name": name, "branch": branch, "level": level})

    # slug -> taxonomy record (the bible) gives the connected keyword/query + priority
    tax_by_slug = {r["topic_slug"]: r for r in taxonomy.load()}

    for c in pool:
        tags = by_src.get(c["id"], [])
        queries, seen_q = [], set()
        for t in tags:
            rec = tax_by_slug.get(t["slug"])
            if rec:
                t.setdefault("priority", rec.get("priority"))
                if not t.get("branch"):
                    t["branch"] = rec.get("branch")
                kw = rec.get("keyword")
                if kw and kw not in seen_q:
                    seen_q.add(kw)
                    queries.append({"keyword": kw, "branch": rec.get("branch"),
                                    "priority": rec.get("priority"), "slug": t["slug"]})
        # canonical ordering of tags (branch order -> priority -> name)
        tags.sort(key=lambda t: (
            taxonomy.BRANCH_ORDER.index(t["branch"]) if t.get("branch") in taxonomy.BRANCH_ORDER else 99,
            taxonomy.PRIORITY_ORDER.get(t.get("priority", "MED"), 9),
            (t.get("name") or "").lower()))
        c["tags"] = tags
        c["branches"] = sorted({t["branch"] for t in tags if t.get("branch")})
        c["queries"] = queries
        c["query_keywords"] = [q["keyword"] for q in queries]


# ===========================================================================
# Reporting
# ===========================================================================
def _cell(x) -> str:
    """Make a value safe for a markdown table cell."""
    s = "" if x is None else str(x)
    return s.replace("|", "/").replace("\n", " ").strip()


def _short(x, n: int) -> str:
    s = _cell(x)
    return (s[: n - 1] + "…") if len(s) > n else s


def write_report(path: Path, run_id: str, judged: list[tuple[dict, dict]],
                 weights: dict, pool_size: int, judge_mode: str,
                 next_weights: dict, wrote_db: bool, db_rows: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    verdicts = {"keep": 0, "review": 0, "quarantine": 0}
    for _c, r in judged:
        verdicts[r["verdict"]] = verdicts.get(r["verdict"], 0) + 1

    L = []
    L.append(f"# Source audit — {now:%Y-%m-%d}")
    L.append("")
    L.append(f"_Run `{run_id}` · {now:%Y-%m-%d %H:%M UTC} · judge: **{judge_mode}** · "
             f"pool {pool_size} → audited {len(judged)}_")
    L.append("")
    L.append("## Summary")
    L.append("")
    L.append(f"- **Audited:** {len(judged)} sources")
    L.append(f"- **Verdicts:** {verdicts['keep']} keep · {verdicts['review']} review · "
             f"{verdicts['quarantine']} quarantine")
    L.append(f"- **Written to `source_audits`:** {'yes — ' + str(db_rows) + ' rows' if wrote_db else 'no (dry-run / table missing)'}")
    L.append(f"- **Audit-priority weights:** `{json.dumps(weights)}`")
    L.append(f"- **Recommended next weights:** `{json.dumps(next_weights)}`")
    L.append("")

    # Flagged lists
    quarantine = [(c, r) for c, r in judged if r["verdict"] == "quarantine"]
    review = [(c, r) for c, r in judged if r["verdict"] == "review"]
    if quarantine:
        L.append("### ⚠️ Flagged for quarantine")
        L.append("")
        for c, r in quarantine:
            L.append(f"- **#{c['id']}** {_short(c.get('name'), 90)} — {_cell(r['notes'])}")
        L.append("")
    if review:
        L.append("### 🟡 Flagged for review")
        L.append("")
        for c, r in review:
            L.append(f"- **#{c['id']}** {_short(c.get('name'), 90)}")
        L.append("")

    # Main table
    L.append("## Audited sources")
    L.append("")
    L.append("| # | id | Source | Yr | Branches | Tags | Connected queries | tag | rel | qual | Verdict |")
    L.append("|--:|--:|--------|--:|----------|------|-------------------|--:|--:|--:|---------|")
    for i, (c, r) in enumerate(judged, 1):
        tags = ", ".join(_short(t["name"], 26) for t in c.get("tags", [])) or "—"
        qs = ", ".join(_short(q["keyword"], 26) for q in c.get("queries", [])) or "—"
        branches = ", ".join(c.get("branches", [])) or "—"
        L.append("| {i} | {id} | {name} | {yr} | {br} | {tags} | {qs} | {tg} | {rl} | {ql} | {vd} |".format(
            i=i, id=c["id"], name=_short(c.get("name"), 54),
            yr=_cell(c.get("year") or ""), br=_short(branches, 40),
            tags=_short(tags, 60), qs=_short(qs, 60),
            tg=r["tag_score"], rl=r["relevance_score"], ql=r["quality_score"],
            vd=r["verdict"]))
    L.append("")

    # Per-source detail (tag issues + connected-query provenance)
    L.append("## Detail — info · tagging · connected queries")
    L.append("")
    for c, r in judged:
        L.append(f"### #{c['id']} · {_short(c.get('name'), 110)}")
        meta = " · ".join(x for x in [
            _cell(c.get("journal") or c.get("venue")),
            str(c.get("year")) if c.get("year") else "",
            f"{c.get('citation_count')} cites" if c.get("citation_count") is not None else "",
            f"DOI {c.get('doi')}" if c.get("doi") else "",
            "review" if c.get("is_review") else "",
        ] if x)
        L.append(f"- {meta}")
        L.append(f"- priority_score `{c.get('priority_score')}` · relevance_llm `{c.get('relevance_llm')}` "
                 f"· audit_priority `{c.get('audit_priority')}` · prior audits `{c.get('audit_count', 0)}`")
        L.append(f"- **Tags:** " + (", ".join(f"{t['name']} ({t.get('branch','?')}/{t.get('priority','?')})"
                                               for t in c.get("tags", [])) or "_none_"))
        L.append(f"- **Connected taxonomy queries:** " + (", ".join(f"`{q['keyword']}`"
                 for q in c.get("queries", [])) or "_none_"))
        if c.get("ingest_query"):
            L.append(f"- **Ingest query:** `{_cell(c['ingest_query'])}`")
        if r.get("tag_issues"):
            L.append(f"- **Tag issues:** " + "; ".join(_cell(x) for x in r["tag_issues"]))
        L.append(f"- **Scores:** tag {r['tag_score']} · relevance {r['relevance_score']} · "
                 f"quality {r['quality_score']} → **{r['verdict']}**")
        L.append(f"- **Notes:** {_cell(r['notes'])}")
        L.append("")

    path.write_text("\n".join(L), encoding="utf-8")


# ===========================================================================
# Orchestration
# ===========================================================================
def resolve_judge(force_mock: bool):
    """Return (rank_fn, judge_fn, update_fn, default_weights, mode_label)."""
    if not force_mock:
        mod = None
        try:
            import audit_judge as mod            # same dir when run as a script
        except Exception:
            try:
                from pipeline import audit_judge as mod
            except Exception:
                mod = None
        if mod is not None and all(hasattr(mod, a) for a in
                                   ("rank_for_audit", "judge_source", "DEFAULT_WEIGHTS", "update_weights")):
            return (mod.rank_for_audit, mod.judge_source, mod.update_weights,
                    dict(mod.DEFAULT_WEIGHTS), "audit_judge")
    return (mock_rank_for_audit, mock_judge_source, mock_update_weights,
            dict(MOCK_WEIGHTS), "mock")


def main() -> int:
    ap = argparse.ArgumentParser(description="Recurring source-audit selection + orchestration.")
    ap.add_argument("--n", type=int, default=N_DEFAULT, help="how many sources to audit (default 20)")
    ap.add_argument("--pool", type=int, default=POOL_DEFAULT, help="candidate pool size (default 150)")
    ap.add_argument("--dry-run", action="store_true", help="do everything but write to the DB")
    ap.add_argument("--mock-judge", action="store_true", help="force the built-in heuristic judge")
    ap.add_argument("--weights", help="path to a JSON file of audit-priority weights (override)")
    args = ap.parse_args()

    rank_fn, judge_fn, update_fn, weights, judge_mode = resolve_judge(args.mock_judge)
    if args.weights:
        weights.update(json.loads(Path(args.weights).read_text()))

    run_id = uuid.uuid4().hex
    print(f"== source audit == run {run_id}")
    print(f"   judge: {judge_mode} | pool target: {args.pool} | audit N: {args.n} | "
          f"dry-run: {args.dry_run}")

    # --- read candidate pool (SELECT-only) ---------------------------------
    try:
        conn = get_conn()
    except Exception as e:
        print(f"!! could not connect to Neon: {e}")
        print("   (build target reached; run is read-dependent so nothing to audit.)")
        return 2
    cur = conn.cursor()

    have_audits = table_exists(cur, "source_audits")
    if not have_audits:
        print("   note: source_audits table not found — treating all sources as never-audited. "
              "Apply db/migrations/0003_source_audits.sql to enable DB writes + recency bias.")

    pool = fetch_pool(cur, args.pool, have_audits)
    attach_tags_and_queries(cur, pool)
    print(f"   pool: {len(pool)} candidates "
          f"({sum(1 for c in pool if not c['tags'])} untagged, "
          f"{sum(1 for c in pool if c.get('audit_count'))} previously audited)")

    # --- rank + judge -------------------------------------------------------
    ranked = rank_fn(pool, weights)
    top = ranked[: args.n]
    judged: list[tuple[dict, dict]] = []
    for c in top:
        res = judge_fn(c)
        # coerce verdict into the allowed set so DB CHECK never fails
        if res.get("verdict") not in ("keep", "review", "quarantine"):
            res["verdict"] = "review"
        judged.append((c, res))

    verdicts = {"keep": 0, "review": 0, "quarantine": 0}
    for _c, r in judged:
        verdicts[r["verdict"]] = verdicts.get(r["verdict"], 0) + 1

    # --- write to source_audits (unless dry-run / table missing) -----------
    wrote_db, db_rows = False, 0
    if not args.dry_run and have_audits:
        from psycopg2.extras import execute_values
        rows = [(c["id"], run_id, r["tag_score"], r["relevance_score"], r["quality_score"],
                 r["verdict"], json.dumps(r.get("tag_issues") or []), r.get("notes", ""),
                 json.dumps(weights), c.get("audit_priority"))
                for c, r in judged]
        execute_values(cur,
            "INSERT INTO source_audits (source_id, run_id, tag_score, relevance_score, "
            "quality_score, verdict, tag_issues, notes, weights_snapshot, audit_priority) VALUES %s",
            rows, template="(%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s::jsonb,%s)")
        conn.commit()
        wrote_db, db_rows = True, len(rows)
    elif not args.dry_run and not have_audits:
        print("   !! skipping DB write — source_audits table does not exist yet.")

    # --- recommended next weights (evolution hook) -------------------------
    try:
        next_weights = update_fn(weights, [r for _c, r in judged])
    except Exception as e:
        print(f"   (update_weights failed, keeping current: {e})")
        next_weights = weights

    # --- markdown report ----------------------------------------------------
    now = datetime.now(timezone.utc)
    report_path = REPO_ROOT / "docs" / "audits" / f"{now:%Y-%m-%d}.md"
    if report_path.exists():
        report_path = report_path.with_name(f"{now:%Y-%m-%d}_{now:%H%M%S}.md")
    write_report(report_path, run_id, judged, weights, len(pool), judge_mode,
                 next_weights, wrote_db, db_rows)

    conn.close()

    # --- stdout summary -----------------------------------------------------
    print(f"   verdicts: {verdicts['keep']} keep · {verdicts['review']} review · "
          f"{verdicts['quarantine']} quarantine")
    quarantined = [c["id"] for c, r in judged if r["verdict"] == "quarantine"]
    if quarantined:
        print(f"   quarantine flagged: {quarantined}")
    print(f"   DB: {'wrote ' + str(db_rows) + ' rows to source_audits' if wrote_db else 'no write'}")
    print(f"   report: {report_path}")
    print(f"   next weights: {json.dumps(next_weights)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
