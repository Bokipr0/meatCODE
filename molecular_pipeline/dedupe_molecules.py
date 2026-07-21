#!/usr/bin/env python3
"""
dedupe_molecules.py — ONE-FILE molecular name deduplication pipeline.

Resolves many names of the same molecule into one canonical record, keyed by the
**Standard InChIKey**, via PubChem PUG REST. Zero external dependencies — pure
Python standard library (sqlite3 + urllib). Just run it:

    python3 dedupe_molecules.py molecules.csv        # batch-import a CSV of names
    python3 dedupe_molecules.py resolve "vanillin"   # resolve one name, show record
    python3 dedupe_molecules.py review               # names needing manual review
    python3 dedupe_molecules.py stats                # counts

Options:  --db PATH (default moldedup.db)  --column NAME  --source LABEL  --limit N  --no-header

Tables (normalized): molecules (1 per InChIKey) · synonyms (many→one) ·
external_identifiers (CAS/CID/ChEBI/HMDB/KEGG) · sources (provenance).
Ambiguous names (>1 PubChem match) are flagged for review, never guessed.
Responses are cached, so re-running the same list is instant and skips the API.
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import re
import sqlite3
import sys
import time
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

# ── settings ───────────────────────────────────────────────────────────
PUG = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
TIMEOUT = 20.0
MIN_INTERVAL = 0.25          # ≤5 req/s (PubChem's ceiling)
MAX_RETRIES = 4
BACKOFF = 0.5
USER_AGENT = "moldedup-solo/1.0"
RETRY_STATUS = {429, 500, 502, 503, 504}

_CAS = re.compile(r"^\d{2,7}-\d{2}-\d$")
_CHEBI = re.compile(r"^CHEBI:\d+$", re.I)
_HMDB = re.compile(r"^HMDB\d+$", re.I)
_KEGG = re.compile(r"^C\d{5}$")
_WS = re.compile(r"\s+")

log = logging.getLogger("moldedup")
_last_call = [0.0]           # module-level rate-limit clock


# ── text normalization ─────────────────────────────────────────────────
def normalize(name):
    if not name:
        return ""
    s = unicodedata.normalize("NFKC", str(name)).strip()
    s = s.strip("\"'`“”‘’«»").strip()
    return _WS.sub(" ", s).casefold()


def clean(name):
    if not name:
        return ""
    s = unicodedata.normalize("NFKC", str(name)).strip().strip("\"'`“”‘’«»").strip()
    return _WS.sub(" ", s)


# ── database schema + helpers ──────────────────────────────────────────
SCHEMA = """
CREATE TABLE IF NOT EXISTS molecules (
  id INTEGER PRIMARY KEY, inchikey TEXT UNIQUE NOT NULL, inchi TEXT, cid INTEGER,
  canonical_smiles TEXT, isomeric_smiles TEXT, formula TEXT, molecular_weight REAL,
  iupac_name TEXT, preferred_name TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS sources (
  id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, kind TEXT, detail TEXT);
CREATE TABLE IF NOT EXISTS synonyms (
  id INTEGER PRIMARY KEY, molecule_id INTEGER REFERENCES molecules(id),
  name TEXT NOT NULL, normalized_name TEXT UNIQUE NOT NULL,
  status TEXT DEFAULT 'resolved', review_reason TEXT,
  source_id INTEGER REFERENCES sources(id), created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS external_identifiers (
  id INTEGER PRIMARY KEY, molecule_id INTEGER REFERENCES molecules(id),
  scheme TEXT NOT NULL, value TEXT NOT NULL, source_id INTEGER,
  UNIQUE(molecule_id, scheme, value));
CREATE TABLE IF NOT EXISTS _http_cache (url TEXT PRIMARY KEY, status INTEGER, body TEXT);
CREATE INDEX IF NOT EXISTS ix_syn_status ON synonyms(status);
CREATE INDEX IF NOT EXISTS ix_mol_inchikey ON molecules(inchikey);
"""


def connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def get_or_create_source(conn, name, kind="import", detail=""):
    row = conn.execute("SELECT id FROM sources WHERE name=?", (name,)).fetchone()
    if row:
        return row["id"]
    cur = conn.execute("INSERT INTO sources(name, kind, detail) VALUES (?,?,?)", (name, kind, detail))
    return cur.lastrowid


# ── PubChem client (cache + retry + rate-limit + timeout) ──────────────
def pug_get(conn, url):
    """Return (status, parsed_json_or_None), cached in the DB (negatives too)."""
    row = conn.execute("SELECT status, body FROM _http_cache WHERE url=?", (url,)).fetchone()
    if row:
        return row["status"], (json.loads(row["body"]) if row["body"] else None)
    last_err = None
    for attempt in range(MAX_RETRIES + 1):
        wait = MIN_INTERVAL - (time.monotonic() - _last_call[0])
        if wait > 0:
            time.sleep(wait)
        _last_call[0] = time.monotonic()
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=TIMEOUT) as resp:
                status, text = resp.status, resp.read().decode("utf-8", "replace")
        except HTTPError as e:
            status = e.code
            text = ""
            if status not in RETRY_STATUS:  # e.g. 404 = genuine "not found"
                conn.execute("INSERT OR REPLACE INTO _http_cache VALUES (?,?,?)", (url, status, ""))
                conn.commit()
                return status, None
            last_err = e
            time.sleep(BACKOFF * (2 ** attempt))
            continue
        except (URLError, TimeoutError) as e:
            last_err = e
            time.sleep(BACKOFF * (2 ** attempt))
            continue
        if "PUGREST.ServerBusy" in text and attempt < MAX_RETRIES:
            time.sleep(BACKOFF * (2 ** attempt))
            continue
        parsed = json.loads(text) if text.strip() else None
        conn.execute("INSERT OR REPLACE INTO _http_cache VALUES (?,?,?)", (url, status, text))
        conn.commit()
        return status, parsed
    raise RuntimeError(f"PubChem failed after retries: {url} ({last_err})")


def resolve(conn, name):
    """Resolve a name → dict with identity/properties/synonyms, or an unresolved/ambiguous marker."""
    status, data = pug_get(conn, f"{PUG}/compound/name/{quote(name, safe='')}/cids/JSON")
    cids = (data or {}).get("IdentifierList", {}).get("CID", []) if status == 200 else []
    if not cids:
        return {"resolved": False, "reason": "no PubChem match for name"}
    if len(cids) > 1:
        return {"resolved": False, "ambiguous": True,
                "reason": f"name maps to {len(cids)} PubChem CIDs: {cids[:8]}"}
    cid = int(cids[0])
    props = _properties(conn, cid)
    inchikey = (props.get("InChIKey") or "").strip()
    if not inchikey:
        return {"resolved": False, "reason": f"CID {cid} returned no InChIKey"}
    syns = _synonyms(conn, cid)
    ext = {"CID": [str(cid)]}
    cas = None
    for s in syns:
        s = s.strip()
        if _CAS.match(s):
            cas = cas or s
            ext.setdefault("CAS", []).append(s)
        elif _CHEBI.match(s):
            ext.setdefault("ChEBI", []).append(s.upper())
        elif _HMDB.match(s):
            ext.setdefault("HMDB", []).append(s.upper())
        elif _KEGG.match(s):
            ext.setdefault("KEGG", []).append(s)
    return {
        "resolved": True, "inchikey": inchikey, "cid": cid,
        "inchi": props.get("InChI"),
        "canonical_smiles": props.get("CanonicalSMILES"),
        "isomeric_smiles": props.get("IsomericSMILES"),
        "formula": props.get("MolecularFormula"),
        "molecular_weight": _to_float(props.get("MolecularWeight")),
        "iupac_name": props.get("IUPACName"),
        "cas": cas, "synonyms": syns, "external": ext,
    }


def _properties(conn, cid):
    classic = "InChIKey,InChI,CanonicalSMILES,IsomericSMILES,MolecularFormula,MolecularWeight,IUPACName"
    status, data = pug_get(conn, f"{PUG}/compound/cid/{cid}/property/{classic}/JSON")
    props = _first(data)
    if status == 200 and props:
        return props
    # PubChem renamed SMILES fields in 2024 → minimal set + modern SMILES names
    _, dmin = pug_get(conn, f"{PUG}/compound/cid/{cid}/property/InChIKey,InChI,MolecularFormula,MolecularWeight,IUPACName/JSON")
    props = _first(dmin) or {}
    _, dsm = pug_get(conn, f"{PUG}/compound/cid/{cid}/property/ConnectivitySMILES,SMILES/JSON")
    sm = _first(dsm) or {}
    props.setdefault("IsomericSMILES", sm.get("SMILES"))
    props.setdefault("CanonicalSMILES", sm.get("ConnectivitySMILES"))
    return props


def _synonyms(conn, cid):
    _, data = pug_get(conn, f"{PUG}/compound/cid/{cid}/synonyms/JSON")
    info = (data or {}).get("InformationList", {}).get("Information", [])
    return list(info[0].get("Synonym", []) or []) if info else []


def _first(data):
    rows = (data or {}).get("PropertyTable", {}).get("Properties", [])
    return rows[0] if rows else None


def _to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ── ingestion (the 8-step dedup) ───────────────────────────────────────
def ingest_name(conn, name, source_id):
    norm, disp = normalize(name), clean(name)
    if not norm:
        return "error"
    syn = conn.execute("SELECT molecule_id, status FROM synonyms WHERE normalized_name=?", (norm,)).fetchone()
    if syn and syn["status"] == "resolved" and syn["molecule_id"]:
        return "exists"

    r = resolve(conn, name)
    if r.get("ambiguous"):
        _review_syn(conn, norm, disp, source_id, "ambiguous", r["reason"])
        return "ambiguous"
    if not r.get("resolved") or not r.get("inchikey"):
        _review_syn(conn, norm, disp, source_id, "unresolved", r.get("reason", "no match"))
        return "unresolved"

    mol = conn.execute("SELECT id FROM molecules WHERE inchikey=?", (r["inchikey"],)).fetchone()
    if mol:
        mol_id, created = mol["id"], False
    else:
        cur = conn.execute(
            "INSERT INTO molecules(inchikey,inchi,cid,canonical_smiles,isomeric_smiles,"
            "formula,molecular_weight,iupac_name,preferred_name) VALUES (?,?,?,?,?,?,?,?,?)",
            (r["inchikey"], r.get("inchi"), r.get("cid"), r.get("canonical_smiles"),
             r.get("isomeric_smiles"), r.get("formula"), r.get("molecular_weight"),
             r.get("iupac_name"), r.get("iupac_name") or disp))
        mol_id, created = cur.lastrowid, True

    _attach_syn(conn, mol_id, norm, disp, source_id, "resolved")
    resolver_src = get_or_create_source(conn, "pubchem", kind="resolver")
    for s in r.get("synonyms", []):
        sn = normalize(s)
        if sn and sn != norm:
            _attach_syn(conn, mol_id, sn, clean(s), resolver_src, "resolved", skip_if_other=True)
    _store_ext(conn, mol_id, r, resolver_src)
    conn.commit()
    return "created" if created else "attached"


def _attach_syn(conn, mol_id, norm, disp, source_id, status, skip_if_other=False):
    row = conn.execute("SELECT id, molecule_id FROM synonyms WHERE normalized_name=?", (norm,)).fetchone()
    if row is None:
        conn.execute("INSERT INTO synonyms(molecule_id,name,normalized_name,status,source_id) VALUES (?,?,?,?,?)",
                     (mol_id, disp, norm, status, source_id))
    elif row["molecule_id"] is None:
        conn.execute("UPDATE synonyms SET molecule_id=?, status=?, review_reason=NULL WHERE id=?",
                     (mol_id, status, row["id"]))
    elif row["molecule_id"] != mol_id:
        log.warning("synonym %r already maps to molecule %s (not reassigning)", norm, row["molecule_id"])


def _review_syn(conn, norm, disp, source_id, status, reason):
    row = conn.execute("SELECT id, molecule_id FROM synonyms WHERE normalized_name=?", (norm,)).fetchone()
    if row is None:
        conn.execute("INSERT INTO synonyms(molecule_id,name,normalized_name,status,review_reason,source_id) "
                     "VALUES (NULL,?,?,?,?,?)", (disp, norm, status, reason, source_id))
    elif row["molecule_id"] is None:
        conn.execute("UPDATE synonyms SET status=?, review_reason=? WHERE id=?", (status, reason, row["id"]))
    conn.commit()


def _store_ext(conn, mol_id, r, source_id):
    pairs = set()
    if r.get("cid"):
        pairs.add(("CID", str(r["cid"])))
    for scheme, vals in r.get("external", {}).items():
        for v in vals:
            if v:
                pairs.add((scheme, str(v)))
    for scheme, value in pairs:
        conn.execute("INSERT OR IGNORE INTO external_identifiers(molecule_id,scheme,value,source_id) "
                     "VALUES (?,?,?,?)", (mol_id, scheme, value, source_id))


# ── commands ───────────────────────────────────────────────────────────
def read_names(path, column, has_header):
    names = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        if has_header:
            reader = csv.DictReader(fh)
            fields = reader.fieldnames or []
            col = column or ("name" if "name" in fields else (fields[0] if fields else None))
            if not col or col not in fields:
                raise SystemExit(f"column {col!r} not found; columns = {fields}")
            names = [(row.get(col) or "").strip() for row in reader]
        else:
            names = [row[0].strip() for row in csv.reader(fh) if row]
    return [n for n in names if n]


def cmd_ingest(args):
    conn = connect(args.db)
    names = read_names(args.csv, args.column, not args.no_header)
    if args.limit:
        names = names[: args.limit]
    src = get_or_create_source(conn, args.source or f"import:{args.csv}", "import", args.csv)
    conn.commit()
    counts = {}
    for i, name in enumerate(names, 1):
        try:
            status = ingest_name(conn, name, src)
        except Exception as e:  # noqa: BLE001 — one bad name never kills the batch
            conn.rollback()
            log.warning("error on %r: %s", name, str(e)[:120])
            status = "error"
        counts[status] = counts.get(status, 0) + 1
        if i % 25 == 0:
            log.info("...%d/%d", i, len(names))
    print(f"\nIngested {len(names)} names from {args.csv}:")
    for k in ("created", "attached", "exists", "ambiguous", "unresolved", "error"):
        if counts.get(k):
            print(f"  {k:11s}: {counts[k]}")
    flagged = counts.get("ambiguous", 0) + counts.get("unresolved", 0)
    if flagged:
        print(f"\n{flagged} name(s) need review — run:  python3 {os.path.basename(sys.argv[0])} review --db {args.db}")


def cmd_resolve(args):
    conn = connect(args.db)
    src = get_or_create_source(conn, "cli:resolve", "manual")
    conn.commit()
    status = ingest_name(conn, args.name, src)
    print(f"[{status}] {args.name}")
    row = conn.execute("SELECT * FROM molecules WHERE inchikey=(SELECT m.inchikey FROM molecules m "
                       "JOIN synonyms s ON s.molecule_id=m.id WHERE s.normalized_name=?)",
                       (normalize(args.name),)).fetchone()
    if row:
        print(f"  InChIKey : {row['inchikey']}\n  CID      : {row['cid']}\n"
              f"  Formula  : {row['formula']}   MW: {row['molecular_weight']}\n"
              f"  IUPAC    : {row['iupac_name']}")


def cmd_review(args):
    conn = connect(args.db)
    q = "SELECT name, status, review_reason FROM synonyms WHERE status IN ('ambiguous','unresolved') ORDER BY status, name"
    rows = conn.execute(q + (f" LIMIT {int(args.limit)}" if args.limit else "")).fetchall()
    if not rows:
        print("Nothing to review. 🎉")
        return
    print(f"{len(rows)} name(s) need manual review:\n")
    for r in rows:
        print(f"  [{r['status']:10s}] {r['name']}\n       ↳ {r['review_reason']}")


def cmd_stats(args):
    conn = connect(args.db)

    def g(sql):
        return conn.execute(sql).fetchone()[0]

    mols = g("SELECT count(*) FROM molecules")
    syn_total = g("SELECT count(*) FROM synonyms")
    resolved = g("SELECT count(*) FROM synonyms WHERE status = 'resolved'")
    to_review = g("SELECT count(*) FROM synonyms WHERE status != 'resolved'")
    ext = g("SELECT count(*) FROM external_identifiers")
    srcs = g("SELECT count(*) FROM sources")
    print("=== moldedup stats ===")
    print(f"  molecules            : {mols}")
    print(f"  synonyms (total)     : {syn_total}")
    print(f"  synonyms (resolved)  : {resolved}")
    print(f"  synonyms (to review) : {to_review}")
    print(f"  external identifiers : {ext}")
    print(f"  sources              : {srcs}")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    # allow the bare form:  dedupe_molecules.py molecules.csv
    if argv and argv[0] not in ("ingest", "resolve", "review", "stats") and argv[0].lower().endswith(".csv"):
        argv = ["ingest"] + argv

    # shared options usable before OR after the subcommand
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--db", default="moldedup.db", help="SQLite file (default moldedup.db)")
    common.add_argument("--log-level", default="INFO")

    p = argparse.ArgumentParser(parents=[common],
                                description="One-file molecular name deduplication (PubChem → InChIKey).")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("ingest", parents=[common]); sp.add_argument("csv")
    sp.add_argument("--column"); sp.add_argument("--source"); sp.add_argument("--limit", type=int)
    sp.add_argument("--no-header", action="store_true"); sp.set_defaults(func=cmd_ingest)
    sp = sub.add_parser("resolve", parents=[common]); sp.add_argument("name"); sp.set_defaults(func=cmd_resolve)
    sp = sub.add_parser("review", parents=[common]); sp.add_argument("--limit", type=int); sp.set_defaults(func=cmd_review)
    sp = sub.add_parser("stats", parents=[common]); sp.set_defaults(func=cmd_stats)

    args = p.parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO),
                        format="%(asctime)s %(levelname)s: %(message)s")
    args.func(args)


if __name__ == "__main__":
    main()
