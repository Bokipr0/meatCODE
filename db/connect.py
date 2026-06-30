#!/usr/bin/env python3
"""Shared Neon accessor for all MeatCODE agents and scripts.

Usage:
    from db.connect import get_conn      # in any script/agent
    python3 db/connect.py                # prints a live health + citable-corpus snapshot

Reads DATABASE_URL from meatCODE/.env (git-ignored). Never hard-code credentials.
The mockup must NOT use this — it goes through server/reaktzia-mvp instead.
"""
from __future__ import annotations
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]   # meatCODE/


def _load_env() -> None:
    envf = REPO_ROOT / ".env"
    if envf.is_file():
        for line in envf.read_text().splitlines():
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                k, v = s.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def get_conn():
    """Return a psycopg2 connection to Neon using DATABASE_URL from .env."""
    _load_env()
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL not set — add it to meatCODE/.env (see .env.example)."
        )
    import psycopg2
    return psycopg2.connect(url)


def _snapshot() -> None:
    conn = get_conn()
    cur = conn.cursor()

    def one(sql: str):
        try:
            cur.execute(sql)
            return cur.fetchone()[0]
        except Exception as e:
            conn.rollback()
            return f"(err: {str(e)[:60]})"

    print("== MeatCODE / Neon snapshot ==")
    print("sources total :", one("select count(*) from sources"))
    print("  w/ abstract :", one("select count(*) from sources where abstract is not null and abstract <> ''"))
    print("  w/ search_vec:", one("select count(*) from sources where search_vec is not null"))
    print("molecules     :", one("select count(*) from molecules"))
    print("experts       :", one("select count(*) from experts"))
    print("claims        :", one("select count(*) from claims"))
    print("\nThe 'w/ search_vec' number is the citable corpus the Oracle can actually retrieve.")
    conn.close()


if __name__ == "__main__":
    _snapshot()
