"""
fetch_dimensions.py
══════════════════════════════════════════════════════════════════════
Sixth fetcher for pipeline.py — Dimensions.ai via the DSL API.

Drop next to pipeline.py and register:

    from fetch_dimensions import fetch_dimensions
    FETCHERS["dimensions"] = fetch_dimensions

Returns the same paper-dict shape as the other fetchers, plus a
`dimensions_meta` sidecar with grants / altmetric / concepts — fields
the other sources don't expose.

Auth modes (controlled by DIMENSIONS_AUTH_TYPE env var):
  • "api_key" (default) — for the Scientometric Research Program. Set
    DIMENSIONS_API_KEY.
  • "login" — for institutional access. Set DIMENSIONS_USERNAME and
    DIMENSIONS_PASSWORD.

The token is cached in module-global state and refreshed when it
expires (~1 hour). Thread-safe via a lock.
"""

from __future__ import annotations
import logging
import os
import threading
import time
from typing import Any

import requests

log = logging.getLogger("dimensions")

DSL_BASE = "https://app.dimensions.ai/api"
AUTH_TYPE = os.environ.get("DIMENSIONS_AUTH_TYPE", "api_key").strip().lower()

_token_lock = threading.Lock()
_token: str | None = None
_token_expires_at: float = 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Auth — cached bearer token
# ─────────────────────────────────────────────────────────────────────────────

def _get_token() -> str | None:
    """Return a fresh bearer token. Cached for ~50 minutes."""
    global _token, _token_expires_at

    with _token_lock:
        if _token and time.time() < _token_expires_at:
            return _token

        try:
            if AUTH_TYPE == "login":
                username = os.environ.get("DIMENSIONS_USERNAME", "").strip()
                password = os.environ.get("DIMENSIONS_PASSWORD", "").strip()
                if not username or not password:
                    log.error("DIMENSIONS_AUTH_TYPE=login but USERNAME/PASSWORD not set")
                    return None
                r = requests.post(
                    f"{DSL_BASE}/auth.json",
                    json={"username": username, "password": password},
                    timeout=20,
                )
            else:  # api_key
                key = os.environ.get("DIMENSIONS_API_KEY", "").strip()
                if not key:
                    log.error("DIMENSIONS_API_KEY not set")
                    return None
                r = requests.post(
                    f"{DSL_BASE}/auth.json",
                    json={"key": key},
                    timeout=20,
                )

            if not r.ok:
                log.error("Dimensions auth failed: HTTP %s — %s",
                          r.status_code, r.text[:200])
                return None
            _token = r.json().get("token")
            _token_expires_at = time.time() + 50 * 60   # 50min safety margin
            log.info("Dimensions auth OK")
            return _token
        except Exception as e:
            log.error("Dimensions auth exception: %s", e)
            return None


# ─────────────────────────────────────────────────────────────────────────────
# DSL query
# ─────────────────────────────────────────────────────────────────────────────

DSL_TEMPLATE = """
search publications
  in title_abstract_only
  for "{keyword}"
where year >= 2010
return publications [
    id + doi + title + year + journal + authors + abstract +
    times_cited + altmetric + concepts + category_for + funders
]
limit {limit}
skip {skip}
""".strip()


def _run_dsl(query: str, token: str) -> dict[str, Any] | None:
    """Execute a DSL query. Returns the parsed JSON response, or None on failure."""
    try:
        r = requests.post(
            f"{DSL_BASE}/dsl.json",
            headers={"Authorization": f"JWT {token}"},
            data=query.encode("utf-8"),
            timeout=60,
        )
        if r.status_code == 401:
            # Token expired — caller will retry with a fresh token
            log.warning("Dimensions token expired mid-flight")
            return None
        if r.status_code == 429:
            # Rate-limit hit
            retry_after = int(r.headers.get("Retry-After", 30))
            log.warning("Dimensions rate-limited, sleeping %ds", retry_after)
            time.sleep(retry_after)
            return None
        if not r.ok:
            log.warning("Dimensions DSL HTTP %s — %s",
                        r.status_code, r.text[:200])
            return None
        return r.json()
    except Exception as e:
        log.warning("Dimensions DSL exception: %s", e)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Record shape conversion
# ─────────────────────────────────────────────────────────────────────────────

def _to_record(p: dict, keyword: str, branch: str) -> dict:
    """Map a Dimensions publication dict into the pipeline's standard record shape."""
    doi = (p.get("doi") or "").strip()
    uid = doi if doi else (p.get("id") or "")

    # Authors come as [{"first_name": ..., "last_name": ..., "full_name": ...}]
    authors = []
    for a in (p.get("authors") or []):
        full = a.get("full_name") or (
            f"{a.get('first_name','')} {a.get('last_name','')}".strip()
        )
        if full:
            authors.append(full)

    # Concepts is a list of {"concept": "name", "relevance": 0.93}
    concept_names = []
    for c in (p.get("concepts") or []):
        if isinstance(c, dict) and c.get("concept"):
            concept_names.append(c["concept"])
        elif isinstance(c, str):
            concept_names.append(c)

    # Sidecar — preserved on the record but not flattened
    dimensions_meta = {
        "altmetric":   p.get("altmetric") or 0,
        "concepts":    p.get("concepts") or [],
        "category_for": [
            (cf.get("name") if isinstance(cf, dict) else cf)
            for cf in (p.get("category_for") or [])
        ],
        "funders":     [
            (f.get("name") if isinstance(f, dict) else f)
            for f in (p.get("funders") or [])
        ],
    }

    return {
        "id":         uid,
        "title":      p.get("title", "") or "",
        "year":       p.get("year"),
        "venue":      ((p.get("journal") or {}).get("title")
                       if isinstance(p.get("journal"), dict)
                       else (p.get("journal") or "")) or "",
        "authors":    authors,
        "url":        f"https://doi.org/{doi}" if doi else (
                       f"https://app.dimensions.ai/details/publication/{p.get('id','')}"
                       if p.get("id") else ""),
        "abstract":   p.get("abstract", "") or "",
        "citations":  int(p.get("times_cited") or 0),
        "concepts":   concept_names[:5],
        "branch":     branch,
        "keyword":    keyword,
        "db":         "dimensions",
        "dimensions_meta": dimensions_meta,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Public fetcher
# ─────────────────────────────────────────────────────────────────────────────

def fetch_dimensions(keyword: str, state: dict, branch: str = "") -> list[dict]:
    """
    Fetch papers from Dimensions.ai matching `keyword`.

    Same signature + return type as the other pipeline fetchers
    (openalex, s2, pubmed, crossref, serpapi). Honors the shared
    `state["cursors"]` / `state["seen_dois"]` contract for resumable
    cursor-based pagination.

    Tuned defaults:
      • DSL "skip" offset persisted across runs in state["cursors"]
      • Page size 50 (DSL allows up to 1000 but smaller is friendlier)
      • Up to MAX_PAGES pages per call (defaults to pipeline.py's MAX_PAGES)
    """
    db = "dimensions"
    cursor_key = f"{keyword}::{db}"

    # Read pagination settings from the pipeline's env vars so a single
    # pipeline.py change to PER_PAGE/MAX_PAGES affects this fetcher too.
    per_page  = int(os.environ.get("PER_PAGE",  "25"))
    max_pages = int(os.environ.get("MAX_PAGES", "8"))

    skip = state["cursors"].get(cursor_key, 0)

    token = _get_token()
    if not token:
        log.warning("Dimensions: no token available, skipping")
        return []

    papers: list[dict] = []
    pages = 0

    while pages < max_pages:
        query = DSL_TEMPLATE.format(keyword=keyword.replace('"', '\\"'),
                                    limit=per_page, skip=skip)
        data = _run_dsl(query, token)

        # Token expired? Force-refresh and retry the same page once.
        if data is None:
            global _token, _token_expires_at
            with _token_lock:
                _token = None
                _token_expires_at = 0
            token = _get_token()
            if not token:
                break
            data = _run_dsl(query, token)
            if data is None:
                break

        results = data.get("publications", [])
        if not results:
            state["cursors"].pop(cursor_key, None)
            break

        for p in results:
            doi = (p.get("doi") or "").strip()
            uid = doi if doi else (p.get("id") or "")
            if not uid:
                continue
            if uid in state.get("seen_dois", set()):
                continue
            papers.append(_to_record(p, keyword, branch))

        skip += len(results)
        state["cursors"][cursor_key] = skip
        pages += 1

        # Polite delay — Dimensions standard tier is ~30 req/min
        time.sleep(2.0)

    log.info("Dimensions [%s]: +%d papers", keyword[:40], len(papers))
    return papers
