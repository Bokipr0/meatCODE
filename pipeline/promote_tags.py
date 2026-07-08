#!/usr/bin/env python3
"""Promote the flat per-source tag arrays (migration 0005) into the relational
tag system (migration 0006): `tags` (category vocabulary) + `source_tags` (junction).

Re-runnable / idempotent — run it again whenever more sources get tagged
(`pipeline/tag_sources.py`) and it will pick up the new tags. Set-based SQL.

    python3 pipeline/promote_tags.py
"""
from __future__ import annotations
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for line in (ROOT / ".env").read_text().splitlines():
    if line.startswith("DATABASE_URL"):
        os.environ.setdefault("DATABASE_URL", line.split("=", 1)[1].strip())

import psycopg2

CATEGORIES = ["pathway", "method", "sensory_descriptor", "matrix", "compound_class"]
SLUG = "btrim(lower(regexp_replace(btrim(v), '[^a-zA-Z0-9]+', '-', 'g')), '-')"

# one UNION arm per category — normalized (name = trimmed value, slug = kebab)
def arms():
    return "\nUNION ALL\n".join(
        f"SELECT id, '{c}'::text AS category, btrim(v) AS name, {SLUG} AS slug "
        f"FROM sources, unnest({c}) v WHERE btrim(v) <> ''"
        for c in CATEGORIES
    )


def main():
    conn = psycopg2.connect(os.environ["DATABASE_URL"]); conn.autocommit = True
    cur = conn.cursor()
    src = f"WITH exploded AS (\n{arms()}\n)"

    # 1) upsert the vocabulary
    cur.execute(f"""
        {src}
        INSERT INTO tags (category, name, slug)
        SELECT DISTINCT category, name, slug FROM exploded
        ON CONFLICT (category, slug) DO NOTHING;
    """)
    # 2) populate the junction
    cur.execute(f"""
        {src}
        INSERT INTO source_tags (source_id, tag_id)
        SELECT DISTINCT e.id, t.id
        FROM exploded e
        JOIN tags t ON t.category = e.category AND t.slug = e.slug
        ON CONFLICT DO NOTHING;
    """)

    cur.execute("SELECT category, count(*) FROM tags GROUP BY 1 ORDER BY 2 DESC")
    print("tags by category:", dict(cur.fetchall()))
    cur.execute("SELECT count(*) FROM tags"); print("tags total:", cur.fetchone()[0])
    cur.execute("SELECT count(*) FROM source_tags"); print("source_tags links:", cur.fetchone()[0])
    cur.execute("SELECT count(DISTINCT source_id) FROM source_tags"); print("sources linked:", cur.fetchone()[0])
    conn.close()


if __name__ == "__main__":
    main()
