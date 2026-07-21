"""Persistent HTTP response cache (SQLite-backed).

Caches by request URL so re-runs and repeated names never re-hit the network.
Negative results (e.g. HTTP 404 'name not found') are cached too, so unknown
names are not retried every run. Thread-safe for the pipeline's use.
"""
from __future__ import annotations

import os
import sqlite3
import threading
import time
from typing import Optional


class HttpCache:
    def __init__(self, path: str, ttl: Optional[float] = None):
        self.path = path
        self.ttl = ttl
        self._lock = threading.Lock()
        parent = os.path.dirname(os.path.abspath(path))
        os.makedirs(parent, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS http_cache "
            "(key TEXT PRIMARY KEY, status INTEGER, body TEXT, ts REAL)"
        )
        self._conn.commit()

    def get(self, key: str) -> Optional[dict]:
        """Return {'status': int, 'body': str} or None on miss/expiry."""
        with self._lock:
            row = self._conn.execute(
                "SELECT status, body, ts FROM http_cache WHERE key = ?", (key,)
            ).fetchone()
        if not row:
            return None
        status, body, ts = row
        if self.ttl is not None and (time.time() - ts) > self.ttl:
            return None
        return {"status": status, "body": body}

    def set(self, key: str, status: int, body: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO http_cache (key, status, body, ts) VALUES (?, ?, ?, ?)",
                (key, status, body, time.time()),
            )
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()
