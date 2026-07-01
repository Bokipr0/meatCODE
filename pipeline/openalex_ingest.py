#!/usr/bin/env python3
"""
Literature -> Neon source ingester (keyless). Topic-driven by the taxonomy bible.

Sources (--source):
  europepmc  (DEFAULT) — Europe PMC; keyless, has abstracts, strong food/flavor coverage.
  openalex             — OpenAlex; use when its full-text search is healthy.

For each taxonomy keyword query: pull top works, keep those WITH an abstract
(so they're citable), dedupe against existing rows (by DOI, then provider id),
insert into `sources`, and tag each to its canonical topic via `source_topics`.
`search_vec` auto-populates via the DB trigger. Reads DATABASE_URL from meatCODE/.env.

Usage:
    python3 pipeline/openalex_ingest.py --priority HIGH --per-topic 7
    python3 pipeline/openalex_ingest.py --source openalex --topics "maillard meat flavor" --dry-run
"""
from __future__ import annotations
import argparse
import json
import ssl
import sys
import time
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

MAILTO = "liorteper1@mail.tau.ac.il"
OPENALEX = "https://api.openalex.org/works"
OA_SELECT = ("id,doi,title,publication_year,authorships,primary_location,"
             "cited_by_count,abstract_inverted_index,concepts,type")
EUROPEPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

try:
    import certifi
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CTX = ssl.create_default_context()


def _get(url: str, retries: int = 3) -> dict:
    last = None
    for a in range(retries):
        try:
            req = Request(url, headers={"User-Agent": f"MeatCODE ingester ({MAILTO})"})
            with urlopen(req, timeout=25, context=SSL_CTX) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # transient 503/429 are common; fail fast
            last = e
            time.sleep(a + 1)
    raise last


def norm_doi(doi):
    if not doi:
        return None
    return doi.replace("https://doi.org/", "").replace("http://doi.org/", "").strip().lower() or None


# ---------------- OpenAlex ----------------
def _reconstruct_abstract(inv):
    if not inv:
        return None
    pos = [(i, w) for w, idxs in inv.items() for i in idxs]
    pos.sort()
    return " ".join(w for _, w in pos).strip() or None


def fetch_openalex(query, per_topic, min_year):
    filt = f"has_abstract:true,type:article,from_publication_date:{min_year}-01-01"
    url = (f"{OPENALEX}?search={quote(query)}&filter={quote(filt)}"
           f"&per-page={min(per_topic, 200)}&select={OA_SELECT}&mailto={MAILTO}")
    return _get(url).get("results", [])


def row_openalex(w, query):
    abstract = _reconstruct_abstract(w.get("abstract_inverted_index"))
    if not abstract:
        return None
    doi = norm_doi(w.get("doi"))
    oa = (w.get("id") or "").rsplit("/", 1)[-1]
    loc = w.get("primary_location") or {}
    src = loc.get("source") or {}
    authors = "; ".join((a.get("author") or {}).get("display_name", "")
                        for a in (w.get("authorships") or [])).strip("; ")
    concepts = ", ".join(c.get("display_name", "") for c in (w.get("concepts") or [])[:6])
    return {"name": w.get("title") or "(untitled)",
            "url": f"https://doi.org/{doi}" if doi else w.get("id"),
            "year": w.get("publication_year"), "venue": src.get("display_name"),
            "journal": src.get("display_name"), "authors": authors or None, "doi": doi,
            "abstract": abstract, "citation_count": w.get("cited_by_count"),
            "top_keywords": concepts or None, "search_query": query,
            "external_id": f"openalex:{oa}" if oa else None}


# ---------------- Europe PMC ----------------
def fetch_europepmc(query, per_topic, min_year):
    q = f"{query} AND (PUB_YEAR:[{min_year} TO 3000]) AND HAS_ABSTRACT:Y"
    url = (f"{EUROPEPMC}?query={quote(q)}&format=json"
           f"&pageSize={min(per_topic, 100)}&resultType=core")
    return (_get(url).get("resultList") or {}).get("result", [])


def row_europepmc(w, query):
    abstract = (w.get("abstractText") or "").strip()
    if not abstract:
        return None
    doi = norm_doi(w.get("doi"))
    ji = w.get("journalInfo") or {}
    jn = (ji.get("journal") or {}).get("title")
    kws = w.get("keywordList") or {}
    keywords = ", ".join((kws.get("keyword") or [])[:6]) if isinstance(kws, dict) else None
    pid = f"{w.get('source', '')}:{w.get('id', '')}"
    return {"name": w.get("title") or "(untitled)",
            "url": (f"https://doi.org/{doi}" if doi
                    else f"https://europepmc.org/abstract/{w.get('source','')}/{w.get('id','')}"),
            "year": int(w["pubYear"]) if w.get("pubYear") else None,
            "venue": jn, "journal": jn, "authors": w.get("authorString"), "doi": doi,
            "abstract": abstract, "citation_count": w.get("citedByCount"),
            "top_keywords": keywords, "search_query": query,
            "external_id": f"europepmc:{pid}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["europepmc", "openalex"], default="europepmc",
                    help="metadata source (default europepmc; OpenAlex search may be degraded)")
    ap.add_argument("--topics", help="semicolon-separated queries (override taxonomy)")
    ap.add_argument("--topics-file", help="one query per line (override taxonomy)")
    ap.add_argument("--branch", help="limit taxonomy queries to one branch")
    ap.add_argument("--priority", help="limit taxonomy queries to a priority, e.g. HIGH")
    ap.add_argument("--per-topic", type=int, default=40)
    ap.add_argument("--min-year", type=int, default=2000)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    queries = []
    if args.topics_file:
        queries += [l.strip() for l in Path(args.topics_file).read_text().splitlines()
                    if l.strip() and not l.strip().startswith("#")]
    if args.topics:
        queries += [q.strip() for q in args.topics.split(";") if q.strip()]
    if not queries:
        from db.taxonomy import search_queries
        queries = search_queries(branch=args.branch, priority=args.priority)
        print(f"No --topics given -> {len(queries)} queries from the taxonomy bible "
              f"(db/taxonomy/keywords_topics.json).")
    if not queries:
        sys.exit("No topics resolved.")

    fetch = fetch_europepmc if args.source == "europepmc" else fetch_openalex
    mkrow = row_europepmc if args.source == "europepmc" else row_openalex
    print(f"Source: {args.source} | {len(queries)} queries | per-topic {args.per_topic}")

    existing_doi = existing_ext = set()
    slug2id = {}
    if not args.dry_run:
        from db.connect import get_conn
        conn = get_conn(); cur = conn.cursor()
        cur.execute("select lower(doi) from sources where doi is not null")
        existing_doi = {r[0] for r in cur.fetchall()}
        cur.execute("select external_id from sources where external_id is not null")
        existing_ext = {r[0] for r in cur.fetchall()}
        cur.execute("select slug, id from topics")
        slug2id = {s: i for s, i in cur.fetchall()}

    from psycopg2.extras import execute_values
    from db.taxonomy import query_meta
    cols = ["name", "url", "year", "venue", "journal", "authors", "doi",
            "abstract", "citation_count", "top_keywords", "search_query", "external_id"]

    seen_doi, seen_ext = set(), set()
    total_new = total_tagged = 0
    for q in queries:
        try:
            works = fetch(q, args.per_topic, args.min_year)
        except Exception as e:
            print(f"  ! fetch failed for '{q}': {e}")
            continue
        batch = []
        for w in works:
            row = mkrow(w, q)
            if not row:
                continue
            d, ext = row["doi"], row["external_id"]
            if d and (d in existing_doi or d in seen_doi):
                continue
            if ext and (ext in existing_ext or ext in seen_ext):
                continue
            if d: seen_doi.add(d)
            if ext: seen_ext.add(ext)
            batch.append(row)
        if args.dry_run:
            print(f"  '{q}': fetched {len(works)}, new {len(batch)}")
            continue
        if batch:
            vals = [[r[c] for c in cols] for r in batch]
            ids = [x[0] for x in execute_values(
                cur, f"INSERT INTO sources ({', '.join(cols)}) VALUES %s RETURNING id",
                vals, fetch=True)]
            pairs = []
            for r, sid in zip(batch, ids):
                meta = query_meta(r["search_query"])
                tid = slug2id.get(meta["topic_slug"]) if meta else None
                if tid:
                    pairs.append((sid, tid))
            if pairs:
                execute_values(cur, "INSERT INTO source_topics(source_id, topic_id) VALUES %s "
                                    "ON CONFLICT DO NOTHING", pairs)
            conn.commit()   # commit per topic so a timeout never loses prior work
            total_new += len(ids); total_tagged += len(pairs)
        print(f"  '{q}': fetched {len(works)}, inserted {len(batch)}")
        time.sleep(0.1)

    if args.dry_run:
        print("\n(dry run — nothing written)")
        return
    print(f"\nInserted {total_new} new sources ({total_tagged} tagged to canonical topics). "
          f"search_vec auto-populated by trigger.")
    conn.close()


if __name__ == "__main__":
    main()
