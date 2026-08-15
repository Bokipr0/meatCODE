#!/usr/bin/env python3
# Last updated: 2026-08-15 · Data Engineer agent · initial version
"""
Backfill source_topics for sources that have ZERO topic rows, using ONLY
exact name-matches between data already on the row and EXISTING topics.
No new topics are created; nothing is guessed.

Match rule (deterministic): a candidate string matches a topic when their
normalized forms are identical. Normalization = lowercase + collapse all
non-alphanumeric runs to a single space (so 'meat-aroma' == 'Meat aroma'
== slug 'meat_aroma'). No stemming, no fuzzy matching, no synonyms.

Candidate strings per source:
  - each element of sources.dimensions_topics (ingest search-query buckets)
  - each comma-separated token of sources.top_keywords

Inserts are ON CONFLICT DO NOTHING against the (source_id, topic_id) PK.

Usage (from repo root):
    python3 pipeline/backfill_source_topics.py [--dry-run]
"""
import argparse
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


def load_env():
    env = REPO_ROOT / ".env"
    if env.is_file():
        for raw in env.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.lower().startswith("export "):
                line = line[7:].lstrip()
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    load_env()
    import psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()

    # topic lookup: normalized name AND normalized slug -> topic_id
    cur.execute("SELECT id, slug, name FROM topics")
    tmap = {}
    for tid, slug, name in cur.fetchall():
        tmap.setdefault(norm(name), tid)
        tmap.setdefault(norm(slug), tid)
    # strip the '_topic' suffix convention on slugs too (fermentation_topic -> Fermentation)
    # NOTE: only via the topic NAME, which already covers it; no extra aliasing added.

    cur.execute("SELECT count(*) FROM sources s WHERE NOT EXISTS (SELECT 1 FROM source_topics st WHERE st.source_id = s.id)")
    untagged_before = cur.fetchone()[0]

    cur.execute(
        """SELECT s.id, s.dimensions_topics, s.top_keywords
             FROM sources s
            WHERE NOT EXISTS (SELECT 1 FROM source_topics st WHERE st.source_id = s.id)
              AND (COALESCE(array_length(s.dimensions_topics, 1), 0) > 0
                   OR COALESCE(s.top_keywords, '') <> '')"""
    )
    rows = cur.fetchall()
    print(f"untagged sources before: {untagged_before}; with matchable raw data: {len(rows)}")

    pairs = set()
    unmatched_values = {}
    for sid, dims, kw in rows:
        candidates = list(dims or [])
        if kw:
            candidates += [t for t in kw.split(",")]
        for c in candidates:
            c = c.strip()
            if not c:
                continue
            tid = tmap.get(norm(c))
            if tid:
                pairs.add((sid, tid))
            else:
                unmatched_values[c] = unmatched_values.get(c, 0) + 1

    print(f"insertable (source_id, topic_id) pairs: {len(pairs)} across {len({s for s, _ in pairs})} sources")
    top_unmatched = sorted(unmatched_values.items(), key=lambda x: -x[1])[:12]
    print("top unmatched values (no existing topic of that name — left alone):")
    for v, n in top_unmatched:
        print(f"   {v!r} x{n}")

    if not args.dry_run and pairs:
        cur.executemany(
            "INSERT INTO source_topics (source_id, topic_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            sorted(pairs),
        )
        conn.commit()

    cur.execute("SELECT count(*) FROM sources s WHERE NOT EXISTS (SELECT 1 FROM source_topics st WHERE st.source_id = s.id)")
    untagged_after = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM source_topics")
    total_rows = cur.fetchone()[0]
    print(f"untagged sources: {untagged_before} -> {untagged_after} | source_topics rows total: {total_rows}")
    conn.close()


if __name__ == "__main__":
    main()
