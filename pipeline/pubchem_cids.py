#!/usr/bin/env python3
# Last updated: 2026-08-15 · Data Engineer agent · initial version (20-molecule pilot)
"""
Fill molecules.pubchem_cid from PubChem PUG-REST by EXACT name lookup.

Zero-fabrication policy:
  - Only writes a CID when PubChem returns exactly ONE CID for the exact
    molecule name (no partial/fuzzy matching, no guessing).
  - Only fills rows where pubchem_cid IS NULL; never overwrites.
  - Skips rows flagged is_junk.

Prioritizes molecules that already have a CAS number (i.e. the MVL-matched,
confirmed-real compounds), then the rest by id.

Usage (from repo root):
    python3 pipeline/pubchem_cids.py --limit 20 [--dry-run]

Respects PubChem's rate guidance (<=5 req/s) via a 0.3 s sleep per request.
"""
import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

PUG = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{}/cids/JSON"


def load_env():
    env = REPO_ROOT / ".env"
    if env.is_file():
        for raw in env.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.lower().startswith("export "):
                line = line[7:].lstrip()
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v


def lookup_cid(name: str, timeout: float = 10.0):
    """Return the single CID for an exact name, or None (ambiguous/absent/error)."""
    url = PUG.format(urllib.parse.quote(name, safe=""))
    req = urllib.request.Request(url, headers={"User-Agent": "MeatCODE-pipeline/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None
    cids = (data.get("IdentifierList") or {}).get("CID") or []
    if len(cids) == 1 and isinstance(cids[0], int):
        return cids[0]
    return None  # ambiguous (>1) or empty — never guess


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    load_env()
    import psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()

    cur.execute("SELECT count(*) FROM molecules WHERE pubchem_cid IS NOT NULL")
    before = cur.fetchone()[0]

    cur.execute(
        """SELECT id, name FROM molecules
            WHERE pubchem_cid IS NULL AND NOT is_junk
            ORDER BY (cas_number IS NOT NULL) DESC, id
            LIMIT %s""",
        (args.limit,),
    )
    rows = cur.fetchall()
    print(f"pubchem_cid non-null before: {before}; attempting {len(rows)} lookups")

    filled = ambiguous_or_missing = 0
    for mid, name in rows:
        cid = lookup_cid(name)
        time.sleep(0.3)
        if cid is None:
            ambiguous_or_missing += 1
            print(f"  - {name!r}: no unambiguous CID (skipped)")
            continue
        filled += 1
        print(f"  + {name!r}: CID {cid}")
        if not args.dry_run:
            cur.execute(
                "UPDATE molecules SET pubchem_cid = %s WHERE id = %s AND pubchem_cid IS NULL",
                (str(cid), mid),
            )
    if not args.dry_run:
        conn.commit()

    cur.execute("SELECT count(*) FROM molecules WHERE pubchem_cid IS NOT NULL")
    after = cur.fetchone()[0]
    print(f"done: filled={filled} skipped={ambiguous_or_missing} | pubchem_cid non-null: {before} -> {after}")
    conn.close()


if __name__ == "__main__":
    main()
