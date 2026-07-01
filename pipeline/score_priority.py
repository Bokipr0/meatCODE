#!/usr/bin/env python3
"""Deterministic priority_score (0-100) for all sources + light QA dedupe.

Signals (tunable weights below):
  relevance proxy (on-topic terms) · venue tier · review-type · citations/year
  (age-normalized) · recency · taxonomy-tagged. When relevance_llm is present it
  dominates (blended 60/40). Also removes exact title-duplicates (keeps richest row).

Run:  python3 pipeline/score_priority.py
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db.connect import get_conn
from psycopg2.extras import execute_values

CUR_YEAR = 2026
CORE_JOURNALS = (  # lowercased substrings of high-signal food/flavor venues
    "food chemistry", "journal of agricultural and food chemistry", "meat science",
    "food research international", "comprehensive reviews in food science",
    "flavour and fragrance", "journal of the science of food and agriculture",
    "trends in food science", "npj science of food", "lwt", "molecules", "foods",
)
REVIEW_RX = re.compile(r"\b(review|meta-analysis|systematic|state[- ]of[- ]the[- ]art|overview|advances in)\b", re.I)
TOPIC_RX = re.compile(r"(meat|beef|pork|chicken|poultry|flavou?r|aroma|volatile|umami|maillard|"
                      r"strecker|lipid oxidation|sensory|odou?r|hydrolysate|yeast extract)", re.I)

# Weights (max contribution of each signal). Edit freely; they cap at 100.
W_RELEVANCE, W_VENUE_CORE, W_VENUE_OTHER, W_REVIEW, W_IMPACT, W_RECENT, W_TAGGED = 25, 20, 8, 15, 20, 10, 10


def venue_points(journal: str | None) -> int:
    j = (journal or "").lower()
    if not j:
        return 0
    return W_VENUE_CORE if any(k in j for k in CORE_JOURNALS) else W_VENUE_OTHER


def deterministic(row) -> tuple[float, bool]:
    name, abstract, journal, year, cites, tagged = row
    text = f"{name or ''} {abstract or ''}"
    s = 0.0
    s += W_RELEVANCE if TOPIC_RX.search(text) else 0
    s += venue_points(journal)
    is_rev = bool(REVIEW_RX.search(name or ""))
    s += W_REVIEW if is_rev else 0
    if cites and year:
        s += min(W_IMPACT, (cites / max(1, CUR_YEAR - year)) * 3)
    if year and year >= 2021:
        s += W_RECENT
    elif year and year >= 2015:
        s += W_RECENT / 2
    s += W_TAGGED if tagged else 0
    return round(min(100.0, s), 1), is_rev


def dedupe(cur, conn) -> int:
    cur.execute("select lower(name), array_agg(id) from sources "
                "group by 1 having count(*) > 1")
    groups = cur.fetchall()
    dropped = 0
    for _, ids in groups:
        cur.execute("select id, coalesce(citation_count,0), (doi is not null)::int, "
                    "(abstract is not null)::int from sources where id = any(%s)", (ids,))
        rows = sorted(cur.fetchall(), key=lambda r: (-r[1], -r[2], -r[3], r[0]))
        drop = [r[0] for r in rows[1:]]
        try:
            cur.execute("delete from source_topics where source_id = any(%s)", (drop,))
            cur.execute("delete from sources where id = any(%s)", (drop,))
            conn.commit(); dropped += len(drop)
        except Exception as e:
            conn.rollback()
            print(f"  ! could not delete dupes {drop} (linked elsewhere): {str(e)[:60]}")
    return dropped


def main():
    conn = get_conn(); cur = conn.cursor()

    print("== dedupe ==")
    print("  removed", dedupe(cur, conn), "duplicate rows")

    cur.execute("""
        select s.id, s.name, s.abstract, s.journal, s.year, s.citation_count,
               exists(select 1 from source_topics st where st.source_id = s.id) tagged,
               s.relevance_llm
        from sources s
    """)
    updates = []
    for _id, name, abstract, journal, year, cites, tagged, rel_llm in cur.fetchall():
        base, is_rev = deterministic((name, abstract, journal, year, cites, tagged))
        score = round(0.6 * rel_llm + 0.4 * base, 1) if rel_llm is not None else base
        updates.append((_id, score, is_rev))

    execute_values(cur,
        "UPDATE sources s SET priority_score = v.ps::numeric, is_review = v.rev::boolean "
        "FROM (VALUES %s) AS v(id, ps, rev) WHERE s.id = v.id::bigint",
        updates, template="(%s,%s,%s)")
    conn.commit()
    print(f"scored {len(updates)} sources.")

    print("\n== priority distribution ==")
    for lo, hi in [(80, 101), (60, 80), (40, 60), (0, 40)]:
        cur.execute("select count(*) from sources where priority_score >= %s and priority_score < %s", (lo, hi))
        print(f"  {lo:3d}-{hi-1:<3d}: {cur.fetchone()[0]}")
    cur.execute("select count(*) from sources where is_review")
    print("  reviews:", cur.fetchone()[0])

    print("\n== top 10 by priority_score ==")
    cur.execute("select round(priority_score,1), year, left(name,64) from sources "
                "order by priority_score desc nulls last limit 10")
    for ps, y, t in cur.fetchall():
        print(f"  {ps:5}  [{y}]  {t}")
    conn.close()


if __name__ == "__main__":
    main()
