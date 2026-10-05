# Last updated: 2026-10-05 · Full-Stack · NEW — logic for the dev "Papers browser" API
#   (flag `papers_browser`). Pure stdlib + SQL handed in by the caller: every function takes a
#   `run(sql, params) -> list[dict]` callable (the server passes its `pg_rows`), so this module
#   opens no connections itself and is trivially testable. SELECT-only, fully parameterized;
#   ORDER BY comes from a fixed whitelist map, user input is NEVER interpolated into SQL.
#
# Public entry points (each returns plain Python; the server does the HTTP glue):
#   list_papers(qs, run)            -> dict   GET  /api/papers-browser
#   facets(run)                     -> dict   GET  /api/papers-browser/facets
#   rows_by_ids(body, run)          -> dict   POST /api/papers-browser/rows
#   export_csv_filtered(qs, run)    -> (bytes, filename)   GET  .../export.csv
#   export_csv_ids(body, run)       -> (bytes, filename)   POST .../export.csv
#   resolve_pdf(qs, run, email)     -> (status_code, dict) GET  .../pdf?id=N
#
# Search decision (q): the query is split on whitespace; EVERY token must match (AND) at least one
# of name / authors / journal / venue / doi / abstract via case-insensitive ILIKE '%token%' (so
# partial words match; %, _ and \ in the input are escaped). We deliberately do NOT use
# tsquery for filtering (it would drop partial-word matches); search_vec is not used at all.
import csv
import io
import json
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import datetime
import decimal

MAX_PAGE_SIZE = 50
DEFAULT_PAGE_SIZE = 50
MAX_IDS = 2000

# Columns never exposed (tsvector index + opaque jsonb blob).
_EXCLUDED_COLS = {"search_vec", "metadata"}

# Fallback (current public.sources shape) if information_schema discovery fails.
_FALLBACK_COLS = [
    "id", "name", "year", "authors", "affiliation", "venue", "url", "abstract", "notes",
    "created_at", "updated_at", "source_type", "doi", "external_id", "search_query",
    "citation_count", "top_keywords", "external_key", "trust_tier", "composite_score",
    "review_status", "dimensions_id", "journal", "dimensions_topics", "priority_score",
    "is_review", "relevance_llm", "pathway", "method", "sensory_descriptor", "matrix",
    "compound_class", "study_type", "main_claim", "tailored_abstract",
]

# Light columns for the list view (contract order).
_LIST_COLS = [
    "id", "name", "authors", "year", "journal", "venue", "doi", "url", "citation_count",
    "relevance_llm", "priority_score", "review_status", "trust_tier", "study_type",
    "is_review", "source_type", "created_at",
]

# Enum / non-JSON-friendly columns are cast to text in SQL.
_CAST_TEXT = {"source_type"}

_SORT_MAP = {
    "year": "s.year",
    "citations": "s.citation_count",
    "relevance": "s.relevance_llm",
    "priority": "s.priority_score",
    "title": "lower(s.name)",
    "authors": "lower(s.authors)",
    "journal": "lower(COALESCE(NULLIF(s.journal, ''), s.venue))",
    "created": "s.created_at",
}

_cols_cache = {"cols": None}


# ─── helpers ───────────────────────────────────────────────────────────
def _first(qs, key, default=""):
    v = qs.get(key)
    if not v:
        return default
    return (v[0] if isinstance(v, (list, tuple)) else v) or default


def _int(s):
    try:
        return int(str(s).strip())
    except (TypeError, ValueError):
        return None


def _csv_list(s):
    return [x.strip() for x in str(s or "").split(",") if x.strip()]


def _jsonable(v):
    if isinstance(v, decimal.Decimal):
        return float(v)
    if isinstance(v, (datetime.datetime, datetime.date)):
        return v.isoformat()
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    return v


def _norm_row(r):
    return {k: _jsonable(v) for k, v in r.items()}


def doi_url_for(doi):
    d = (doi or "").strip()
    if not d:
        return None
    if d.lower().startswith("http"):
        return d
    return "https://doi.org/" + d


def _full_cols(run):
    """All columns of public.sources except search_vec/metadata, in table order (cached)."""
    if _cols_cache["cols"]:
        return _cols_cache["cols"]
    cols = []
    try:
        rows = run(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = current_schema() AND table_name = 'sources' "
            "ORDER BY ordinal_position", ())
        cols = [r["column_name"] for r in rows if r["column_name"] not in _EXCLUDED_COLS]
    except Exception:
        cols = []
    if not cols or "id" not in cols:
        cols = list(_FALLBACK_COLS)
    _cols_cache["cols"] = cols
    return cols


def _select_list(cols):
    parts = []
    for c in cols:
        if c in _CAST_TEXT:
            parts.append('s."%s"::text AS "%s"' % (c, c))
        else:
            parts.append('s."%s"' % c)
    return ", ".join(parts)


def _like_escape(tok):
    return tok.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


# ─── filters / sort ────────────────────────────────────────────────────
def _parse_sort(qs):
    sort = _first(qs, "sort", "year").strip().lower()
    if sort not in _SORT_MAP:
        sort = "year"
    d = _first(qs, "dir", "desc").strip().lower()
    if d not in ("asc", "desc"):
        d = "desc"
    return sort, d


def _order_by(sort, d):
    col = _SORT_MAP[sort]                       # whitelisted
    direction = "ASC" if d == "asc" else "DESC"  # whitelisted
    return "%s %s NULLS LAST, s.id %s" % (col, direction, direction)


def _build_where(qs):
    where, params = [], []

    q = _first(qs, "q").strip()
    if q:
        for tok in q.split()[:8]:
            like = "%" + _like_escape(tok) + "%"
            where.append(
                "(s.name ILIKE %s OR s.authors ILIKE %s OR s.journal ILIKE %s OR s.venue ILIKE %s "
                "OR s.doi ILIKE %s OR s.abstract ILIKE %s)")
            params.extend([like] * 6)

    n = _int(_first(qs, "year_min"))
    if n is not None:
        where.append("s.year >= %s"); params.append(n)
    n = _int(_first(qs, "year_max"))
    if n is not None:
        where.append("s.year <= %s"); params.append(n)
    n = _int(_first(qs, "min_relevance"))
    if n is not None:
        where.append("s.relevance_llm >= %s"); params.append(n)
    n = _int(_first(qs, "max_relevance"))
    if n is not None:
        where.append("s.relevance_llm <= %s"); params.append(n)
    n = _int(_first(qs, "min_citations"))
    if n is not None:
        where.append("s.citation_count >= %s"); params.append(n)

    for key, col in (("review_status", "s.review_status"), ("study_type", "s.study_type"),
                     ("trust_tier", "s.trust_tier")):
        vals = _csv_list(_first(qs, key))
        if vals:
            where.append("%s = ANY(%%s)" % col)
            params.append(vals)

    topics = _csv_list(_first(qs, "topic"))
    if topics:
        where.append(
            "EXISTS (SELECT 1 FROM source_topics st JOIN topics t ON t.id = st.topic_id "
            "WHERE st.source_id = s.id AND t.slug = ANY(%s))")
        params.append(topics)
    tags = _csv_list(_first(qs, "tag"))
    if tags:
        where.append(
            "EXISTS (SELECT 1 FROM source_tags sg JOIN tags g ON g.id = sg.tag_id "
            "WHERE sg.source_id = s.id AND g.slug = ANY(%s))")
        params.append(tags)

    # Tri-state presence filters: 1 = has it, 0 = missing it, absent = no filter. The 0 variants
    # are the audit lenses ("no DOI", "no abstract", "untagged", "no main claim").
    def _tri(key):
        v = _first(qs, key).strip().lower()
        if v in ("1", "true", "yes"):
            return True
        if v in ("0", "false", "no"):
            return False
        return None
    for key, present in (
            ("has_doi", "(s.doi IS NOT NULL AND btrim(s.doi) <> '')"),
            ("has_url", "(s.url IS NOT NULL AND btrim(s.url) <> '')"),
            ("has_abstract", "(s.abstract IS NOT NULL AND btrim(s.abstract) <> '')"),
            ("has_main_claim", "(s.main_claim IS NOT NULL AND btrim(s.main_claim) <> '')"),
            ("has_tags", "EXISTS (SELECT 1 FROM source_tags x WHERE x.source_id = s.id)"),
            # Same predicate the Oracle retrieval uses: citable (search_vec) AND relevance_llm >= 60.
            ("in_oracle", "(s.search_vec IS NOT NULL AND s.relevance_llm >= 60)")):
        t = _tri(key)
        if t is True:
            where.append(present)
        elif t is False:
            where.append("NOT COALESCE(" + present + ", FALSE)")
    ir = _first(qs, "is_review").strip().lower()
    if ir in ("1", "true", "yes"):
        where.append("s.is_review IS TRUE")
    elif ir in ("0", "false", "no"):
        where.append("s.is_review IS NOT TRUE")

    return ((" WHERE " + " AND ".join(where)) if where else ""), params


# ─── 1) list ───────────────────────────────────────────────────────────
def list_papers(qs, run):
    sort, d = _parse_sort(qs)
    where_sql, params = _build_where(qs)

    ps = _int(_first(qs, "page_size", str(DEFAULT_PAGE_SIZE)))
    if ps is None or ps < 1:
        ps = DEFAULT_PAGE_SIZE
    ps = min(ps, MAX_PAGE_SIZE)
    page = _int(_first(qs, "page", "1"))
    if page is None or page < 1:
        page = 1

    total = int(run("SELECT COUNT(*) AS n FROM sources s" + where_sql, tuple(params))[0]["n"])
    pages = max(1, (total + ps - 1) // ps)
    if page > pages:
        page = pages
    offset = (page - 1) * ps

    sql = ("SELECT " + _select_list(_LIST_COLS) +
           ", (s.search_vec IS NOT NULL AND s.relevance_llm >= 60) AS in_oracle"
           " FROM sources s" + where_sql +
           " ORDER BY " + _order_by(sort, d) + " LIMIT %s OFFSET %s")
    rows = run(sql, tuple(params + [ps, offset]))
    items = []
    for r in rows:
        r = _norm_row(r)
        r["title"] = r.pop("name", None)
        r["doi_url"] = doi_url_for(r.get("doi"))
        items.append(r)
    return {"items": items, "total": total, "page": page, "page_size": ps,
            "pages": pages, "sort": sort, "dir": d}


# ─── 2) facets ─────────────────────────────────────────────────────────
def facets(run):
    out = {}
    t = run(
        "SELECT MIN(year) AS ymin, MAX(year) AS ymax, COUNT(*) AS papers, "
        "COUNT(*) FILTER (WHERE doi IS NOT NULL AND btrim(doi) <> '') AS with_doi, "
        "COUNT(*) FILTER (WHERE url IS NOT NULL AND btrim(url) <> '') AS with_url, "
        "COUNT(*) FILTER (WHERE is_review IS TRUE) AS reviews FROM sources", ())[0]
    out["year_min"] = t["ymin"]
    out["year_max"] = t["ymax"]
    for key in ("review_status", "study_type", "trust_tier"):
        # key is a fixed literal from the tuple above, never user input
        rows = run('SELECT "%s" AS value, COUNT(*) AS count FROM sources '
                   'WHERE "%s" IS NOT NULL AND btrim("%s") <> \'\' '
                   'GROUP BY 1 ORDER BY 2 DESC, 1 ASC' % (key, key, key), ())
        out[key] = [{"value": r["value"], "count": int(r["count"])} for r in rows]
    rows = run(
        "SELECT t.slug, t.name, COUNT(DISTINCT st.source_id) AS count FROM topics t "
        "JOIN source_topics st ON st.topic_id = t.id GROUP BY t.slug, t.name "
        "HAVING COUNT(DISTINCT st.source_id) > 0 ORDER BY 3 DESC, t.name ASC", ())
    out["topics"] = [{"slug": r["slug"], "name": r["name"], "count": int(r["count"])} for r in rows]
    rows = run(
        "SELECT g.category, g.slug, g.name, COUNT(DISTINCT sg.source_id) AS count FROM tags g "
        "JOIN source_tags sg ON sg.tag_id = g.id GROUP BY g.category, g.slug, g.name "
        "HAVING COUNT(DISTINCT sg.source_id) > 0 ORDER BY 4 DESC, g.name ASC LIMIT 200", ())
    out["tags"] = [{"category": r["category"], "slug": r["slug"], "name": r["name"],
                    "count": int(r["count"])} for r in rows]
    out["totals"] = {"papers": int(t["papers"]), "with_doi": int(t["with_doi"]),
                     "with_url": int(t["with_url"]), "reviews": int(t["reviews"])}
    return out


# ─── 3) rows by ids ────────────────────────────────────────────────────
def _clean_ids(body):
    ids = body.get("ids") if isinstance(body, dict) else None
    out, seen = [], set()
    if isinstance(ids, list):
        for x in ids:
            if isinstance(x, bool) or not isinstance(x, int):
                continue
            if x in seen or x < 0 or x > 9223372036854775807:
                continue
            seen.add(x); out.append(x)
            if len(out) >= MAX_IDS:
                break
    return out


def _fetch_full_by_ids(ids, run):
    cols = _full_cols(run)
    if not ids:
        return [], []
    rows = run("SELECT " + _select_list(cols) + " FROM sources s WHERE s.id = ANY(%s)", (ids,))
    by_id = {int(r["id"]): _norm_row(r) for r in rows}
    ordered = [by_id[i] for i in ids if i in by_id]
    for r in ordered:
        r["doi_url"] = doi_url_for(r.get("doi"))
    missing = [i for i in ids if i not in by_id]
    return ordered, missing


def rows_by_ids(body, run):
    ids = _clean_ids(body)
    items, missing = _fetch_full_by_ids(ids, run)
    return {"items": items, "missing": missing}


# ─── 4/5) CSV ──────────────────────────────────────────────────────────
def _cell(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (list, tuple)):
        return "; ".join("" if x is None else str(x) for x in v)
    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False)
    return v


def _safe(v):
    """Excel/Sheets formula-injection guard: a text cell starting with = + - @ (or tab/CR) would be
    EXECUTED as a formula when the CSV is opened — prefix a single quote. Numbers pass untouched."""
    if isinstance(v, str) and v and v[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + v
    return v


def _csv_bytes(rows, cols):
    header = list(cols) + ["doi_url"]
    buf = io.StringIO()
    w = csv.writer(buf, quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
    w.writerow(header)
    for r in rows:
        w.writerow([_safe(_cell(r.get(c))) for c in cols] + [_safe(_cell(r.get("doi_url")))])
    return ("﻿" + buf.getvalue()).encode("utf-8")


def _csv_filename():
    return "meatcode_papers_%s.csv" % datetime.datetime.now(
        datetime.timezone.utc).strftime("%Y%m%d_%H%M")


def export_csv_filtered(qs, run):
    sort, d = _parse_sort(qs)
    where_sql, params = _build_where(qs)
    cols = _full_cols(run)
    rows = run("SELECT " + _select_list(cols) + " FROM sources s" + where_sql +
               " ORDER BY " + _order_by(sort, d), tuple(params))
    rows = [_norm_row(r) for r in rows]
    for r in rows:
        r["doi_url"] = doi_url_for(r.get("doi"))
    return _csv_bytes(rows, cols), _csv_filename()


def export_csv_ids(body, run):
    ids = _clean_ids(body)
    items, _missing = _fetch_full_by_ids(ids, run)
    return _csv_bytes(items, _full_cols(run)), _csv_filename()


# ─── 6) open-access PDF resolver (Unpaywall) ───────────────────────────
_PDF_TTL = 24 * 3600
_PDF_CACHE_MAX = 5000
_pdf_cache = {}          # doi(lower) -> (expires_ts, pdf_url|None)
_pdf_lock = threading.Lock()


def _norm_doi(doi):
    d = (doi or "").strip()
    d = re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", d, flags=re.I)
    d = re.sub(r"^doi:\s*", "", d, flags=re.I)
    return d.strip()


def _unpaywall_lookup(doi, email):
    """Returns (ok, pdf_url|None). ok False = network/upstream failure (not cached)."""
    url = "https://api.unpaywall.org/v2/%s?email=%s" % (
        urllib.parse.quote(doi, safe="/"), urllib.parse.quote(email, safe="@"))
    req = urllib.request.Request(url, headers={"User-Agent": "MeatCODE-papers-browser/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read(2_000_000).decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return True, None              # DOI unknown to Unpaywall = no OA copy known
        return False, None
    except Exception:
        return False, None
    pdf = None
    best = data.get("best_oa_location") or {}
    if isinstance(best, dict):
        pdf = best.get("url_for_pdf")
    if not pdf:
        for loc in data.get("oa_locations") or []:
            if isinstance(loc, dict) and loc.get("url_for_pdf"):
                pdf = loc["url_for_pdf"]
                break
    if pdf and not re.match(r"^https?://", str(pdf), re.I):
        pdf = None
    return True, pdf


def resolve_pdf(qs, run, email):
    pid = _int(_first(qs, "id"))
    if pid is None:
        return 400, {"ok": False, "error": "missing or invalid ?id="}
    rows = run("SELECT id, doi, url FROM sources WHERE id = %s", (pid,))
    if not rows:
        return 404, {"ok": False, "error": "paper not found", "id": pid}
    doi = _norm_doi(rows[0].get("doi")) or None
    landing = doi_url_for(doi) or ((rows[0].get("url") or "").strip() or None)
    base = {"ok": True, "id": pid, "doi": doi, "landing_url": landing,
            "pdf_url": None, "source": "none", "cached": False}
    if not doi:
        return 200, base
    email = (email or "").strip()
    if not email:
        base["source"] = "unavailable"
        return 200, base
    key = doi.lower()
    now = time.time()
    with _pdf_lock:
        hit = _pdf_cache.get(key)
    if hit and hit[0] > now:
        base["pdf_url"] = hit[1]
        base["source"] = "unpaywall" if hit[1] else "none"
        base["cached"] = True
        return 200, base
    ok, pdf = _unpaywall_lookup(doi, email)
    if not ok:
        base["source"] = "unavailable"
        return 200, base
    with _pdf_lock:
        if len(_pdf_cache) >= _PDF_CACHE_MAX:
            for k in [k for k, v in _pdf_cache.items() if v[0] <= now][:1000] or list(_pdf_cache)[:500]:
                _pdf_cache.pop(k, None)
        _pdf_cache[key] = (now + _PDF_TTL, pdf)
    base["pdf_url"] = pdf
    base["source"] = "unpaywall" if pdf else "none"
    return 200, base
