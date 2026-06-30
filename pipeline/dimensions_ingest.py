#!/usr/bin/env python3
"""
Dimensions.ai → Neon Postgres ingester.

Pulls top researchers and recent publications for each topic in the
flavor-science taxonomy and upserts them into the existing `experts` and
`sources` tables. Deduplicates against ORCID, DOI, and dimensions_id.

Required env vars:
    DIMENSIONS_API_KEY   — your Dimensions Analytics API key
    DATABASE_URL         — Neon Postgres connection string

Usage:
    # Run schema additions once, then:
    export DIMENSIONS_API_KEY="..."
    export DATABASE_URL="postgresql://neondb_owner:...@...neon.tech/neondb?sslmode=require"
    python3 dimensions_ingest.py
    # OR limit to specific topics:
    python3 dimensions_ingest.py --topics maillard,meat-aroma
    # OR validate connectivity without writing:
    python3 dimensions_ingest.py --dry-run --topics maillard
"""
import argparse
import json
import os
import ssl
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    import certifi
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CTX = ssl.create_default_context()

try:
    import psycopg2
except ImportError:
    sys.exit("Missing dependency: pip install psycopg2-binary")

def _load_dotenv():
    """
    Minimal .env loader — looks for a .env file next to this script and in
    the current working dir, then sets os.environ keys that aren't already set.
    No external dependency required.
    """
    candidates = [
        Path(__file__).resolve().parent / ".env",
        Path.cwd() / ".env",
    ]
    for path in candidates:
        if not path.is_file():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.lower().startswith("export "):
                line = line[7:].lstrip()
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val
        return path
    return None

_loaded_from = _load_dotenv()

# ─── CONFIG ───────────────────────────────────────────────────────────────────
DIMENSIONS_API           = "https://app.dimensions.ai/api"
YEAR_FROM                = 2018          # only ingest papers this recent or newer
RESEARCHERS_PER_TOPIC    = 25
PAPERS_PER_TOPIC         = 80
SLEEP_BETWEEN_TOPICS_SEC = 2

# Topic slug → Dimensions DSL `for` clause body.
# The for clause accepts a single quoted phrase. Single phrase per topic
# keeps the DSL valid; we pick the most discriminating phrase for each one.
# Slugs match the chip filters in the Reaktzia mockup.
TOPIC_QUERIES = {
    "maillard":      "Maillard reaction",
    "meat-aroma":    "meat aroma volatiles",
    "off-note":      "off-flavor masking",
    "plant-protein": "pea protein flavor",
    "sensory":       "odor threshold",
    "fermentation":  "fermentation aroma",
}

# ─── HTTP helpers ─────────────────────────────────────────────────────────────
def _post(url, body, headers, timeout=60):
    req = Request(url, data=body, headers=headers, method="POST")
    return urlopen(req, context=SSL_CTX, timeout=timeout)

def get_token(api_key):
    """Authenticate with Dimensions and return a JWT bearer token."""
    body = json.dumps({"key": api_key}).encode("utf-8")
    with _post(f"{DIMENSIONS_API}/auth",
               body, {"Content-Type": "application/json"},
               timeout=30) as r:
        data = json.loads(r.read())
    if "token" not in data:
        raise RuntimeError(f"Auth response missing token: {data}")
    return data["token"]

def dsl(token, query, retries=3):
    """Run a DSL query; returns parsed JSON. Handles 429 with backoff."""
    body = query.encode("utf-8")
    headers = {
        "Authorization": f"JWT {token}",
        "Content-Type":  "text/plain",
    }
    last_err = None
    for attempt in range(retries):
        try:
            with _post(f"{DIMENSIONS_API}/dsl", body, headers, timeout=120) as r:
                return json.loads(r.read())
        except HTTPError as e:
            if e.code == 429:
                wait = 30 * (attempt + 1)
                print(f"    rate-limited — sleeping {wait}s")
                time.sleep(wait)
                last_err = e
                continue
            if e.code == 401:
                raise RuntimeError("Auth failed — re-fetch the token") from e
            msg = e.read().decode("utf-8", "ignore")[:300]
            print(f"    HTTP {e.code}: {msg}")
            last_err = e
            time.sleep(5)
        except URLError as e:
            print(f"    URL error: {e}")
            last_err = e
            time.sleep(5)
    raise RuntimeError(f"DSL query failed after {retries} attempts: {last_err}")

# ─── Postgres upsert helpers ──────────────────────────────────────────────────
def _norm_orcid(raw):
    """Dimensions returns orcid_id as a list of strings — take the first."""
    if not raw:
        return None
    if isinstance(raw, list):
        return raw[0] if raw else None
    return raw

def _full_name(first, last):
    name = " ".join(p for p in (first, last) if p).strip()
    return name or None

def upsert_expert(cur, r, topic_slug):
    """Returns (id_or_None, status) — status in {'inserted','updated','skipped'}.

    Accepts both top-level researcher dicts and author dicts from publication results.
    """
    name = _full_name(r.get("first_name"), r.get("last_name"))
    if not name:
        return None, "skipped"

    dim_id      = r.get("id") or r.get("researcher_id")
    orcid       = _norm_orcid(r.get("orcid_id"))
    h_index     = r.get("h_index")
    total_pubs  = r.get("total_publications")

    # current_research_org can be a dict (researcher search) OR
    # affiliations[0] (publication author).
    current_org_obj = r.get("current_research_org") or {}
    if not current_org_obj and r.get("affiliations"):
        aff = r["affiliations"]
        if isinstance(aff, list) and aff:
            current_org_obj = aff[0] if isinstance(aff[0], dict) else {}
    current_org = current_org_obj.get("name") if isinstance(current_org_obj, dict) else None
    country     = current_org_obj.get("country_name") if isinstance(current_org_obj, dict) else None

    # Find existing (by ORCID or dimensions_id)
    cur.execute("""
        SELECT id, dimensions_topics FROM experts
        WHERE (orcid = %(orcid)s AND %(orcid)s IS NOT NULL)
           OR (dimensions_id = %(dim_id)s AND %(dim_id)s IS NOT NULL)
        LIMIT 1
    """, {"orcid": orcid, "dim_id": dim_id})
    row = cur.fetchone()

    if row:
        existing_id, existing_topics = row
        merged_topics = sorted(set((existing_topics or []) + [topic_slug]))
        cur.execute("""
            UPDATE experts SET
                h_index            = COALESCE(%s, h_index),
                total_papers       = COALESCE(%s, total_papers),
                orcid              = COALESCE(orcid, %s),
                dimensions_id      = COALESCE(dimensions_id, %s),
                current_org        = COALESCE(%s, current_org),
                affiliation        = COALESCE(affiliation, %s),
                country            = COALESCE(country, %s),
                dimensions_topics  = %s
            WHERE id = %s
        """, (h_index, total_pubs, orcid, dim_id,
              current_org, current_org, country, merged_topics, existing_id))
        return existing_id, "updated"

    cur.execute("""
        INSERT INTO experts (
            name, affiliation, country, h_index, total_papers,
            orcid, dimensions_id, current_org, dimensions_topics
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (name, current_org, country, h_index, total_pubs,
          orcid, dim_id, current_org, [topic_slug]))
    return cur.fetchone()[0], "inserted"

def upsert_source(cur, p, topic_slug):
    title = p.get("title")
    if not title:
        return None, "skipped"

    dim_id  = p.get("id")
    doi     = p.get("doi")
    year    = p.get("year")
    cite    = p.get("times_cited") or 0
    abstr   = p.get("abstract")
    journal_obj = p.get("journal")
    journal = None
    if isinstance(journal_obj, dict):
        journal = journal_obj.get("title")
    elif isinstance(journal_obj, str):
        journal = journal_obj

    # author list (cap 30 to keep TEXT field manageable)
    authors_raw = p.get("authors") or []
    authors_list = []
    for a in authors_raw[:30]:
        if isinstance(a, dict):
            n = _full_name(a.get("first_name"), a.get("last_name"))
            if n:
                authors_list.append(n)
    authors_str = "; ".join(authors_list) if authors_list else None

    url = f"https://doi.org/{doi}" if doi else f"https://app.dimensions.ai/details/publication/{dim_id}"

    # Find existing
    cur.execute("""
        SELECT id, dimensions_topics FROM sources
        WHERE (doi = %(doi)s AND %(doi)s IS NOT NULL)
           OR (dimensions_id = %(dim_id)s AND %(dim_id)s IS NOT NULL)
        LIMIT 1
    """, {"doi": doi, "dim_id": dim_id})
    row = cur.fetchone()

    if row:
        existing_id, existing_topics = row
        merged_topics = sorted(set((existing_topics or []) + [topic_slug]))
        cur.execute("""
            UPDATE sources SET
                citation_count    = GREATEST(COALESCE(citation_count, 0), %s),
                year              = COALESCE(year, %s),
                authors           = COALESCE(authors, %s),
                abstract          = COALESCE(abstract, %s),
                journal           = COALESCE(journal, %s),
                doi               = COALESCE(doi, %s),
                dimensions_id     = COALESCE(dimensions_id, %s),
                url               = COALESCE(url, %s),
                dimensions_topics = %s
            WHERE id = %s
        """, (cite, year, authors_str, abstr, journal,
              doi, dim_id, url, merged_topics, existing_id))
        return existing_id, "updated"

    cur.execute("""
        INSERT INTO sources (
            name, url, year, venue, authors, citation_count,
            doi, dimensions_id, abstract, journal,
            search_query, dimensions_topics
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (title, url, year, journal, authors_str, cite,
          doi, dim_id, abstr, journal, topic_slug, [topic_slug]))
    return cur.fetchone()[0], "inserted"

# ─── Main flow ────────────────────────────────────────────────────────────────
def fetch_researchers(token, dsl_query, limit):
    # Field list constrained to what's available on the free Dimensions tier.
    q = (
        f'search researchers '
        f'for "{dsl_query}" '
        f'return researchers'
        f'[id+first_name+last_name+orcid_id+current_research_org'
        f'+first_publication_year+last_publication_year+dimensions_url] '
        f'limit {limit}'
    )
    return dsl(token, q).get("researchers", [])

def fetch_publications(token, dsl_query, year_from, limit):
    # Minimal safe field set for the free Dimensions tier.
    q = (
        f'search publications '
        f'for "{dsl_query}" '
        f'where year >= {year_from} '
        f'return publications'
        f'[id+doi+title+abstract+authors+year+times_cited+journal] '
        f'limit {limit}'
    )
    return dsl(token, q).get("publications", [])

def main():
    parser = argparse.ArgumentParser(description="Dimensions → Neon ingester")
    parser.add_argument("--topics", default=None,
                        help=f"Comma-separated topic slugs. Default: all of {','.join(TOPIC_QUERIES)}")
    parser.add_argument("--dry-run", action="store_true",
                        help="Fetch from Dimensions but do not write to Postgres.")
    parser.add_argument("--researchers", type=int, default=RESEARCHERS_PER_TOPIC,
                        help=f"Researchers per topic (default {RESEARCHERS_PER_TOPIC})")
    parser.add_argument("--papers", type=int, default=PAPERS_PER_TOPIC,
                        help=f"Papers per topic (default {PAPERS_PER_TOPIC})")
    parser.add_argument("--year-from", type=int, default=YEAR_FROM,
                        help=f"Earliest publication year (default {YEAR_FROM})")
    args = parser.parse_args()

    api_key = os.environ.get("DIMENSIONS_API_KEY")
    db_url  = os.environ.get("DATABASE_URL")
    if _loaded_from:
        print(f"Loaded env from {_loaded_from}")
    if not api_key: sys.exit("Set DIMENSIONS_API_KEY env var first")
    if not args.dry_run and not db_url:
        sys.exit("Set DATABASE_URL env var (or pass --dry-run)")

    # Resolve topics
    topics = dict(TOPIC_QUERIES)
    if args.topics:
        wanted = {t.strip() for t in args.topics.split(",") if t.strip()}
        topics = {k: v for k, v in TOPIC_QUERIES.items() if k in wanted}
        if not topics:
            sys.exit(f"No topics match: {args.topics}\nAvailable: {','.join(TOPIC_QUERIES)}")
    print(f"Topics to ingest: {', '.join(topics)}")

    print("\nAuthenticating with Dimensions…")
    token = get_token(api_key)
    print(f"  ✓ token acquired ({len(token)} chars)")

    conn = cur = None
    if not args.dry_run:
        print("\nConnecting to Postgres…")
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        print("  ✓ connected")

    grand = {"r_ins": 0, "r_upd": 0, "p_ins": 0, "p_upd": 0}

    for slug, query in topics.items():
        print(f"\n=== Topic: {slug}")
        print(f"    DSL: {query}")
        stats = {"r_ins": 0, "r_upd": 0, "p_ins": 0, "p_upd": 0}

        # 1. researchers
        try:
            researchers = fetch_researchers(token, query, args.researchers)
            print(f"    {len(researchers)} researcher(s) returned")
        except Exception as e:
            print(f"    ! researcher fetch failed: {e}")
            researchers = []

        for r in researchers:
            if args.dry_run:
                stats["r_ins"] += 1
                continue
            try:
                _, status = upsert_expert(cur, r, slug)
                if status == "inserted": stats["r_ins"] += 1
                elif status == "updated":  stats["r_upd"] += 1
            except Exception as e:
                print(f"      ! expert upsert error: {e}")
                conn.rollback()
                cur = conn.cursor()
        if not args.dry_run:
            conn.commit()

        # 2. publications
        try:
            pubs = fetch_publications(token, query, args.year_from, args.papers)
            print(f"    {len(pubs)} publication(s) returned")
        except Exception as e:
            print(f"    ! publication fetch failed: {e}")
            pubs = []

        for p in pubs:
            if args.dry_run:
                stats["p_ins"] += 1
                continue
            try:
                _, status = upsert_source(cur, p, slug)
                if status == "inserted": stats["p_ins"] += 1
                elif status == "updated":  stats["p_upd"] += 1
                # Also extract this paper's authors as expert rows
                for a in (p.get("authors") or [])[:30]:
                    if not isinstance(a, dict): continue
                    try:
                        _, a_status = upsert_expert(cur, a, slug)
                        if a_status == "inserted": stats["r_ins"] += 1
                        elif a_status == "updated":  stats["r_upd"] += 1
                    except Exception as ae:
                        print(f"        ! author upsert error: {ae}")
                        conn.rollback()
                        cur = conn.cursor()
            except Exception as e:
                print(f"      ! source upsert error: {e}")
                conn.rollback()
                cur = conn.cursor()
        if not args.dry_run:
            conn.commit()
            cur.execute("""
                INSERT INTO ingest_log
                    (source, topic_slug,
                     inserted_experts, updated_experts,
                     inserted_sources, updated_sources)
                VALUES ('dimensions', %s, %s, %s, %s, %s)
            """, (slug, stats["r_ins"], stats["r_upd"],
                  stats["p_ins"], stats["p_upd"]))
            conn.commit()

        print(f"    researchers +{stats['r_ins']} / ~{stats['r_upd']} updated")
        print(f"    papers      +{stats['p_ins']} / ~{stats['p_upd']} updated")
        for k in grand: grand[k] += stats[k]
        time.sleep(SLEEP_BETWEEN_TOPICS_SEC)

    print("\n══════════════════════════════════════════")
    print(f"  TOTAL  researchers +{grand['r_ins']}  ~{grand['r_upd']} updated")
    print(f"         papers      +{grand['p_ins']}  ~{grand['p_upd']} updated")
    print("══════════════════════════════════════════")

    if not args.dry_run:
        cur.close(); conn.close()

if __name__ == "__main__":
    main()
