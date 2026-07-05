#!/usr/bin/env python3
# Last updated: 2026-07-05 16:06 UTC · Data Engineer (parallel white-space run) · initial version, verified live against Neon
"""White-space analysis: empirical corpus coverage vs. the MeatCODE taxonomy.

Quantifies where the literature corpus (sources / source_topics) does and
doesn't cover the taxonomy bible (db/taxonomy/keywords_topics.json), so the
gaps can be read as *empirical white spaces* — topics the taxonomy says
matter (HIGH/MED priority) but the corpus barely touches.

SELECT-only. Does not modify any data or schema.

Usage:
    python3 analysis/white_space_analysis.py            # prints + writes white_space_data.md
    python3 analysis/white_space_analysis.py --no-write  # print only

Reads DATABASE_URL from meatCODE/.env via db.connect.get_conn().
Reads the taxonomy bible via db.taxonomy (db/taxonomy/keywords_topics.json).

CRITICAL CAVEAT (measured below, not assumed): only the ~332 newly-ingested
sources were tagged into source_topics when they were added via
openalex_ingest.py. The original ~496 sources predate that tagging pass and
were never back-tagged. So every topic/branch coverage number in this report
reflects ONLY the tagged subset of the corpus, not the whole corpus. The
tagged-vs-untagged split is measured and reported explicitly (section 4)
precisely so this limitation isn't silently baked into the white-space read.
"""
from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime, timezone

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from db.connect import get_conn          # noqa: E402
from db import taxonomy as tax           # noqa: E402


def fetch_all(cur, sql, params=None):
    cur.execute(sql, params or ())
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def fetch_one(cur, sql, params=None):
    cur.execute(sql, params or ())
    row = cur.fetchone()
    return row[0] if row else None


def run() -> dict:
    conn = get_conn()
    cur = conn.cursor()
    out: dict = {}

    # ------------------------------------------------------------------
    # 0. Corpus totals
    # ------------------------------------------------------------------
    out["sources_total"] = fetch_one(cur, "SELECT count(*) FROM sources")
    out["sources_with_relevance"] = fetch_one(
        cur, "SELECT count(*) FROM sources WHERE relevance_llm IS NOT NULL"
    )
    out["sources_high_relevance"] = fetch_one(
        cur, "SELECT count(*) FROM sources WHERE relevance_llm >= 60"
    )
    out["sources_very_high_relevance"] = fetch_one(
        cur, "SELECT count(*) FROM sources WHERE relevance_llm >= 80"
    )

    # ------------------------------------------------------------------
    # 1. Tagged vs untagged sources (the critical caveat)
    # ------------------------------------------------------------------
    out["sources_tagged"] = fetch_one(
        cur, "SELECT count(DISTINCT source_id) FROM source_topics"
    )
    out["sources_untagged"] = out["sources_total"] - out["sources_tagged"]
    out["source_topics_rows"] = fetch_one(cur, "SELECT count(*) FROM source_topics")

    # ------------------------------------------------------------------
    # 2. Per-topic coverage (join topics <-> source_topics <-> sources)
    #    topics.slug matches taxonomy topic_slug; topics.name / root_branch
    #    give branch. We bring in priority from the taxonomy bible in Python
    #    since priority isn't stored in Postgres (source of truth is the JSON).
    # ------------------------------------------------------------------
    topic_rows = fetch_all(
        cur,
        """
        SELECT
            t.id                                            AS topic_id,
            t.slug                                           AS topic_slug,
            t.name                                            AS topic_name,
            t.root_branch                                     AS branch,
            count(DISTINCT st.source_id)                      AS n_sources,
            count(DISTINCT st.source_id) FILTER (
                WHERE s.relevance_llm >= 60
            )                                                  AS n_high_relevance
        FROM topics t
        LEFT JOIN source_topics st ON st.topic_id = t.id
        LEFT JOIN sources s        ON s.id = st.source_id
        GROUP BY t.id, t.slug, t.name, t.root_branch
        ORDER BY branch, n_sources ASC
        """,
    )

    # Attach taxonomy priority (by topic_slug) so we can flag HIGH-priority gaps.
    bible_by_slug = {r["topic_slug"]: r for r in tax.load()}
    for row in topic_rows:
        rec = bible_by_slug.get(row["topic_slug"])
        row["priority"] = rec["priority"] if rec else None
        row["in_bible"] = rec is not None
    out["topic_rows"] = topic_rows

    # ------------------------------------------------------------------
    # 3. Per-branch rollup
    # ------------------------------------------------------------------
    branch_rows = fetch_all(
        cur,
        """
        SELECT
            t.root_branch                                     AS branch,
            count(DISTINCT st.source_id)                      AS n_sources,
            count(DISTINCT st.source_id) FILTER (
                WHERE s.relevance_llm >= 60
            )                                                  AS n_high_relevance
        FROM topics t
        LEFT JOIN source_topics st ON st.topic_id = t.id
        LEFT JOIN sources s        ON s.id = st.source_id
        GROUP BY t.root_branch
        ORDER BY n_sources DESC
        """,
    )
    for row in branch_rows:
        row["high_share_pct"] = (
            round(100.0 * row["n_high_relevance"] / row["n_sources"], 1)
            if row["n_sources"] else 0.0
        )
        row["n_topics_in_bible"] = len(tax.records(branch=row["branch"]))
    out["branch_rows"] = branch_rows

    # Topics with zero corpus rows never surface via the LEFT JOIN grouped by
    # topic id above if the topic itself has no source_topics rows at all —
    # actually they DO surface (LEFT JOIN keeps the topic row with n_sources=0).
    # But topics that exist in the bible and were never synced into `topics`
    # at all would be invisible. Check for that gap explicitly:
    synced_slugs = {r["topic_slug"] for r in topic_rows}
    bible_slugs = {r["topic_slug"] for r in tax.load()}
    out["bible_topics_missing_from_db"] = sorted(bible_slugs - synced_slugs)

    # ------------------------------------------------------------------
    # 4. Thin evidence layers
    # ------------------------------------------------------------------
    out["claims_count"] = fetch_one(cur, "SELECT count(*) FROM claims")
    out["molecules_total"] = fetch_one(cur, "SELECT count(*) FROM molecules")
    out["molecule_categories"] = fetch_all(
        cur,
        """
        SELECT coalesce(category, '(uncategorized)') AS category, count(*) AS n
        FROM molecules
        GROUP BY category
        ORDER BY n DESC
        """,
    )
    out["claims_with_sources"] = fetch_one(
        cur, "SELECT count(DISTINCT claim_id) FROM claim_sources"
    )
    out["claims_with_molecules"] = fetch_one(
        cur, "SELECT count(DISTINCT claim_id) FROM claim_molecules"
    )

    conn.close()
    return out


def render_markdown(data: dict) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = []
    a = lines.append

    a("# White-Space Data — Empirical Corpus Coverage vs. Taxonomy")
    a("")
    a(f"# Last updated: {ts} · Data Engineer (parallel white-space run) · "
      f"live query against Neon via analysis/white_space_analysis.py")
    a("")
    a("Factual data only — no strategic interpretation. Companion to the Advisory "
      "agent's strategic white-space narrative (docs/). Re-run the script anytime "
      "for fresh numbers: `python3 analysis/white_space_analysis.py`.")
    a("")

    # ---- 0. Headline totals ----
    a("## 0. Corpus totals")
    a("")
    a(f"- Sources total: **{data['sources_total']}**")
    a(f"- Sources with `relevance_llm` scored: **{data['sources_with_relevance']}**")
    a(f"- Sources with `relevance_llm >= 60` (high-relevance, Oracle-eligible): "
      f"**{data['sources_high_relevance']}**")
    a(f"- Sources with `relevance_llm >= 80` (very-high): "
      f"**{data['sources_very_high_relevance']}**")
    a(f"- `claims` rows: **{data['claims_count']}**")
    a(f"- `molecules` rows: **{data['molecules_total']}**")
    a("")

    # ---- 1. Tagged vs untagged caveat ----
    a("## 1. CRITICAL CAVEAT — tagged vs. untagged sources")
    a("")
    pct_tagged = round(100.0 * data["sources_tagged"] / data["sources_total"], 1) if data["sources_total"] else 0
    a(f"- Sources with **at least one** `source_topics` tag: **{data['sources_tagged']}** "
      f"({pct_tagged}% of {data['sources_total']} total)")
    a(f"- Sources with **zero** taxonomy tags (untagged): **{data['sources_untagged']}**")
    a(f"- Total `source_topics` rows (sources can carry >1 topic): **{data['source_topics_rows']}**")
    a("")
    a("**Read this before trusting any topic/branch coverage number below.** Per "
      "PROJECT_STATE.md, only the ~332 sources ingested via `openalex_ingest.py` "
      "(the post-taxonomy-sync ingest pass) were tagged into `source_topics`. The "
      "original ~496 legacy sources were never back-tagged. The measured tagged "
      f"count above ({data['sources_tagged']}) confirms this: it is far below the "
      f"{data['sources_total']}-source total. Every coverage/white-space number in "
      "this report describes **the tagged subset only** — a topic showing '0 "
      "sources' may still have relevant papers sitting untagged in the other "
      f"{data['sources_untagged']} sources. Back-tagging the legacy 496 is a "
      "prerequisite for a fully trustworthy gap read.")
    a("")
    if data["bible_topics_missing_from_db"]:
        a(f"- Additionally, **{len(data['bible_topics_missing_from_db'])} taxonomy "
          "topics have no row at all in the `topics` table** (never synced): "
          f"{', '.join(data['bible_topics_missing_from_db'][:20])}"
          f"{' …' if len(data['bible_topics_missing_from_db']) > 20 else ''}")
        a("")

    # ---- 2. Branch coverage table ----
    a("## 2. Branch coverage (tagged subset)")
    a("")
    a("| Branch | Tagged sources | High-relevance (≥60) | High-relevance share | Topics in taxonomy bible |")
    a("|---|---:|---:|---:|---:|")
    for r in data["branch_rows"]:
        a(f"| {r['branch']} | {r['n_sources']} | {r['n_high_relevance']} | "
          f"{r['high_share_pct']}% | {r['n_topics_in_bible']} |")
    a("")
    total_tagged_rollup = sum(r["n_sources"] for r in data["branch_rows"])
    a(f"(Branch totals sum to {total_tagged_rollup} source-topic pairs, not "
      f"{data['sources_tagged']} distinct sources, because a source can be tagged "
      "to topics in more than one branch.)")
    a("")

    # ---- 3. Top under-covered HIGH-priority topics ----
    a("## 3. Top ~15 empirical white-space topics (HIGH priority, low/zero coverage)")
    a("")
    high_topics = [r for r in data["topic_rows"] if r["priority"] == "HIGH"]
    high_topics_sorted = sorted(high_topics, key=lambda r: (r["n_sources"], r["n_high_relevance"]))
    top_gaps = high_topics_sorted[:15]
    a("| Topic | Branch | Priority | Tagged sources | High-relevance (≥60) |")
    a("|---|---|---|---:|---:|")
    for r in top_gaps:
        a(f"| {r['topic_name']} | {r['branch']} | {r['priority']} | "
          f"{r['n_sources']} | {r['n_high_relevance']} |")
    a("")
    zero_high = [r for r in high_topics if r["n_sources"] == 0]
    a(f"- **{len(zero_high)} of {len(high_topics)} HIGH-priority topics have ZERO tagged sources.**")
    a("")

    # Full topic table (all priorities) for completeness / re-use by other agents.
    a("## 4. Full topic coverage table (all branches, all priorities)")
    a("")
    a("| Topic | Branch | Priority | Tagged sources | High-relevance (≥60) |")
    a("|---|---|---|---:|---:|")
    for r in sorted(data["topic_rows"], key=lambda r: (r["branch"], r["n_sources"])):
        a(f"| {r['topic_name']} | {r['branch']} | {r['priority'] or '(not in bible)'} | "
          f"{r['n_sources']} | {r['n_high_relevance']} |")
    a("")

    # ---- 5. Thin evidence layers ----
    a("## 5. Thin evidence layers")
    a("")
    a(f"- `claims` total: **{data['claims_count']}** "
      f"(claims linked to ≥1 source: {data['claims_with_sources']}; "
      f"claims linked to ≥1 molecule: {data['claims_with_molecules']})")
    a(f"- `molecules` total: **{data['molecules_total']}**, by category:")
    a("")
    a("| Category | Molecules |")
    a("|---|---:|")
    for r in data["molecule_categories"]:
        a(f"| {r['category']} | {r['n']} |")
    a("")
    a("These are the thinnest layers in the schema — 45 claims and the molecule "
      "table's category spread are far below what a credible molecular/claims "
      "surface needs; treat both as structurally thin regardless of the "
      "topic-coverage read above.")
    a("")

    return "\n".join(lines)


def main():
    no_write = "--no-write" in sys.argv
    data = run()
    md = render_markdown(data)

    print(md)

    if not no_write:
        out_path = REPO_ROOT / "analysis" / "white_space_data.md"
        out_path.write_text(md)
        print(f"\n[written] {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
