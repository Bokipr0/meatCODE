"""Canonical MeatCODE taxonomy — the single source of truth ("the bible").

Bible file: db/taxonomy/keywords_topics.json  (edit THERE; everything reads it.)

RULE FOR ALL AGENTS/SCRIPTS: never hardcode topic/keyword lists. Any ingest,
filter, sort, or tagging operation goes through this module so the whole
database stays governed by one taxonomy. The Postgres `topics` table is synced
from here via pipeline/sync_taxonomy.py.

Each record: keyword, branch, priority (HIGH/MED), topic_slug, topic_name, topic_level.
"""
from __future__ import annotations
import json
from functools import lru_cache
from pathlib import Path

TAXONOMY_PATH = Path(__file__).resolve().parent / "taxonomy" / "keywords_topics.json"

# Canonical ordering used everywhere (Atlas 5 families, then priority, then depth).
BRANCH_ORDER = ["analytics", "flavor_chemistry", "flavor_ingredients", "meat_analogs", "meat_science"]
PRIORITY_ORDER = {"HIGH": 0, "MED": 1, "LOW": 2}


def _rank(r: dict):
    return (
        BRANCH_ORDER.index(r["branch"]) if r.get("branch") in BRANCH_ORDER else 99,
        PRIORITY_ORDER.get(r.get("priority", "MED"), 9),
        r.get("topic_level", 9),
        (r.get("topic_name") or "").lower(),
    )


@lru_cache(maxsize=1)
def load() -> list[dict]:
    """All taxonomy records, in canonical order."""
    recs = json.loads(TAXONOMY_PATH.read_text())
    recs.sort(key=_rank)
    return recs


def branches() -> list[str]:
    present = {r["branch"] for r in load()}
    return [b for b in BRANCH_ORDER if b in present]


def records(branch: str | None = None, priority: str | None = None) -> list[dict]:
    out = load()
    if branch:
        out = [r for r in out if r["branch"] == branch]
    if priority:
        out = [r for r in out if r.get("priority") == priority]
    return out


def search_queries(branch: str | None = None, priority: str | None = None) -> list[str]:
    """Ordered keyword search strings for literature ingest (openalex_ingest, etc.)."""
    return [r["keyword"] for r in records(branch=branch, priority=priority)]


def query_meta(keyword: str) -> dict | None:
    """Return the taxonomy record whose keyword == this search string (provenance)."""
    for r in load():
        if r["keyword"] == keyword:
            return r
    return None


def classify(text: str, top_k: int = 3) -> list[dict]:
    """Best canonical topics for arbitrary text (e.g. a paper title+abstract),
    by topic_name occurrence, returned in canonical order. Cheap first pass."""
    t = (text or "").lower()
    seen, out = set(), []
    for r in load():
        name = (r.get("topic_name") or "").lower()
        if len(name) >= 4 and name in t and r["topic_slug"] not in seen:
            seen.add(r["topic_slug"])
            out.append(r)
    return out[:top_k]


def sort_key(rec: dict):
    """Canonical sort key for any object carrying branch/priority/topic_level."""
    return _rank(rec)


if __name__ == "__main__":
    recs = load()
    print(f"Taxonomy bible: {TAXONOMY_PATH}")
    print(f"{len(recs)} keywords across {len(branches())} branches: {branches()}")
    for b in branches():
        rs = records(branch=b)
        print(f"  {b:20s} {len(rs):3d} topics  ({sum(1 for r in rs if r['priority']=='HIGH')} HIGH)")
