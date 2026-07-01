#!/usr/bin/env python3
"""Sync the taxonomy bible (db/taxonomy/keywords_topics.json) into the Postgres
`topics` table so the DB mirrors it. Upsert by slug; NEVER deletes (safe/idempotent).

Ensures each branch exists as a root topic, then upserts every keyword's topic as
a child. Run after editing the bible:  python3 pipeline/sync_taxonomy.py
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db.connect import get_conn
from db.taxonomy import load, branches


def main(dry_run: bool = False) -> None:
    conn = get_conn()
    cur = conn.cursor()

    # 1) ensure each branch exists as a root topic (level 0, no parent)
    branch_ids: dict[str, int] = {}
    for b in branches():
        cur.execute("select id from topics where slug = %s", (b,))
        row = cur.fetchone()
        if row:
            branch_ids[b] = row[0]
        else:
            cur.execute(
                "insert into topics(slug,name,parent_id,root_branch,level) "
                "values(%s,%s,null,%s,0) returning id",
                (b, b.replace("_", " ").title(), b),
            )
            branch_ids[b] = cur.fetchone()[0]

    # 2) upsert each taxonomy topic by slug
    ins = upd = 0
    for r in load():
        slug, name, branch = r["topic_slug"], r["topic_name"], r["branch"]
        level = r.get("topic_level")
        cur.execute("select id from topics where slug = %s", (slug,))
        row = cur.fetchone()
        if row:
            cur.execute(
                "update topics set name=%s, root_branch=%s, level=%s, "
                "parent_id=coalesce(parent_id,%s) where slug=%s",
                (name, branch, level, branch_ids[branch], slug),
            )
            upd += 1
        else:
            cur.execute(
                "insert into topics(slug,name,parent_id,root_branch,level) "
                "values(%s,%s,%s,%s,%s)",
                (slug, name, branch_ids[branch], branch, level),
            )
            ins += 1

    if dry_run:
        conn.rollback()
        print(f"[dry-run] would insert {ins}, update {upd} topics (rolled back).")
    else:
        conn.commit()
        cur.execute("select count(*) from topics")
        print(f"taxonomy synced: {ins} inserted, {upd} updated. topics table now {cur.fetchone()[0]} rows.")
    conn.close()


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
