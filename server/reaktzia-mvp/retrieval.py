"""Postgres full-text retrieval for the Reaktzia Oracle.

Connects to Neon via DATABASE_URL, runs a ranked tsvector query against
the `sources` table, returns the top-k chunks for an LLM prompt.
"""

from __future__ import annotations

import os
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor


# A short, structured shape for an Oracle context chunk.
def _chunk(row: dict[str, Any]) -> dict[str, Any]:
    abstract = (row.get("abstract") or "").strip()
    if len(abstract) > 1200:
        abstract = abstract[:1200].rsplit(" ", 1)[0] + " …"
    return {
        "id":       row["id"],
        "title":    row.get("name")    or "(untitled)",
        "year":     row.get("year"),
        "authors":  row.get("authors") or "",
        "journal":  row.get("journal") or row.get("venue") or "",
        "doi":      row.get("doi"),
        "abstract": abstract,
        "score":    float(row.get("rank") or 0.0),
        "topics":   row.get("dimensions_topics") or [],
    }


def retrieve(question: str, k: int = 5) -> list[dict[str, Any]]:
    """Return the top-k sources ranked by Postgres full-text search.

    Empty or whitespace-only questions return [] (the API layer treats
    this as the 'empty' state). Connection failures bubble up — the API
    layer maps them to a 503 with a helpful message.
    """
    q = (question or "").strip()
    if not q:
        return []

    url = os.environ["DATABASE_URL"]

    sql = """
        SELECT
            id, name, year, authors, journal, venue, doi, abstract,
            dimensions_topics,
            ts_rank_cd(search_vec, query) AS rank
        FROM sources,
             websearch_to_tsquery('english', %s) query
        WHERE search_vec @@ query
        ORDER BY rank DESC
        LIMIT %s;
    """

    with psycopg2.connect(url) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (q, k))
            rows = cur.fetchall()

    # If the FTS query finds nothing (rare but possible with very narrow
    # questions), fall back to ILIKE so the demo never returns empty.
    if not rows:
        fallback_sql = """
            SELECT
                id, name, year, authors, journal, venue, doi, abstract,
                dimensions_topics,
                0.001 AS rank
            FROM sources
            WHERE coalesce(name, '') ILIKE %s
               OR coalesce(abstract, '') ILIKE %s
            ORDER BY year DESC NULLS LAST
            LIMIT %s;
        """
        like = f"%{q}%"
        with psycopg2.connect(url) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(fallback_sql, (like, like, k))
                rows = cur.fetchall()

    return [_chunk(r) for r in rows]


def fetch_paper(paper_id: int) -> dict[str, Any] | None:
    """Return a single paper by id, for the paper-detail modal."""
    url = os.environ["DATABASE_URL"]
    sql = """
        SELECT id, name, year, authors, journal, venue, doi, abstract,
               url, citation_count, dimensions_topics
        FROM sources
        WHERE id = %s;
    """
    with psycopg2.connect(url) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (paper_id,))
            row = cur.fetchone()
    return dict(row) if row else None


def recent_papers(limit: int = 6) -> list[dict[str, Any]]:
    """Return a handful of recent papers for the dashboard 'For you' row."""
    url = os.environ["DATABASE_URL"]
    sql = """
        SELECT id, name, year, authors, journal, venue, dimensions_topics
        FROM sources
        WHERE year IS NOT NULL
        ORDER BY year DESC NULLS LAST, id DESC
        LIMIT %s;
    """
    with psycopg2.connect(url) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (limit,))
            return [dict(r) for r in cur.fetchall()]


def db_health() -> dict[str, Any]:
    """Tiny sanity check used by /api/health."""
    url = os.environ["DATABASE_URL"]
    with psycopg2.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM sources;")
            (sources_count,) = cur.fetchone()
            cur.execute("SELECT count(*) FROM sources WHERE search_vec IS NOT NULL;")
            (indexed_count,) = cur.fetchone()
    return {
        "sources_total":   sources_count,
        "sources_indexed": indexed_count,
    }
