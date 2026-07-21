"""Command-line interface.

    python ingest.py init                         # create tables
    python ingest.py ingest molecules.csv         # batch import (CSV)
    python ingest.py ingest molecules.csv --column compound --source "flavor list"
    python ingest.py resolve "vanillin"           # one name
    python ingest.py review                        # names needing manual review
    python ingest.py stats                         # counts

DB target: --db-url or $DATABASE_URL (default sqlite:///moldedup.db).
"""
from __future__ import annotations

import argparse
import csv
import logging
import sys
from collections import Counter
from typing import List, Optional

from .config import Config
from .db import build_engine, build_session_factory, init_db
from .models import ExternalIdentifier, Molecule, Source, Synonym, STATUS_RESOLVED
from .pipeline import IngestionPipeline


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def _read_names(path: str, column: Optional[str], has_header: bool) -> List[str]:
    """Read molecule names from a CSV. With a header, use `column` (default 'name',
    falling back to the first column). Without a header, use the first column."""
    names: List[str] = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        if has_header:
            reader = csv.DictReader(fh)
            fields = reader.fieldnames or []
            col = column or ("name" if "name" in fields else (fields[0] if fields else None))
            if col is None:
                raise SystemExit("CSV appears empty / has no columns")
            if col not in fields:
                raise SystemExit(f"column {col!r} not found; available: {fields}")
            for row in reader:
                v = (row.get(col) or "").strip()
                if v:
                    names.append(v)
        else:
            for row in csv.reader(fh):
                if row and row[0].strip():
                    names.append(row[0].strip())
    return names


def _make_pipeline(cfg: Config):
    engine = build_engine(cfg.db_url)
    session_factory = build_session_factory(engine)
    # Import the resolver lazily so `init`/`stats`/`review` don't require `requests`.
    from .resolvers.pubchem import PubChemResolver
    resolver = PubChemResolver(cfg)
    return engine, session_factory, IngestionPipeline(session_factory, resolver)


def _config_from_args(args) -> Config:
    overrides = {}
    if args.db_url:
        overrides["db_url"] = args.db_url
    if args.cache:
        overrides["cache_path"] = args.cache
    if args.min_interval is not None:
        overrides["min_request_interval"] = args.min_interval
    overrides["log_level"] = args.log_level
    return Config.from_env(**overrides)


# ---- commands -----------------------------------------------------------
def cmd_init(args) -> int:
    cfg = _config_from_args(args)
    engine = build_engine(cfg.db_url)
    init_db(engine)
    print(f"Initialized database at {cfg.db_url}")
    return 0


def cmd_ingest(args) -> int:
    cfg = _config_from_args(args)
    engine, _, pipeline = _make_pipeline(cfg)
    init_db(engine)  # ensure tables
    names = _read_names(args.csv, args.column, has_header=not args.no_header)
    if args.limit:
        names = names[: args.limit]
    if not names:
        print("No names found in CSV.")
        return 1
    source = args.source or f"import:{args.csv}"
    print(f"Ingesting {len(names)} names from {args.csv} (source={source!r}) …")
    outcomes = pipeline.ingest_batch(names, source_name=source, source_detail=args.csv)
    counts = Counter(o.status for o in outcomes)
    print("\n=== summary ===")
    for status in ("created", "attached", "exists", "ambiguous", "unresolved", "error"):
        if counts.get(status):
            print(f"  {status:11s}: {counts[status]}")
    print(f"  total      : {len(outcomes)}")
    flagged = [o for o in outcomes if o.status in ("ambiguous", "unresolved")]
    if flagged:
        print(f"\n{len(flagged)} name(s) need manual review — run `review`.")
    return 0


def cmd_resolve(args) -> int:
    cfg = _config_from_args(args)
    engine, session_factory, pipeline = _make_pipeline(cfg)
    init_db(engine)
    session = session_factory()
    try:
        source = pipeline.get_or_create_source(session, args.source or "cli:resolve", kind="manual")
        session.commit()
        outcome = pipeline.ingest_name(session, args.name, source)
        session.commit()
        print(f"[{outcome.status}] {args.name}  {outcome.message}")
        if outcome.inchikey:
            mol = session.query(Molecule).filter_by(inchikey=outcome.inchikey).one()
            print(f"  InChIKey : {mol.inchikey}")
            print(f"  CID      : {mol.cid}")
            print(f"  Formula  : {mol.formula}   MW: {mol.molecular_weight}")
            print(f"  IUPAC    : {mol.iupac_name}")
            print(f"  Synonyms : {len(mol.synonyms)}   ExternalIDs: {len(mol.external_ids)}")
    finally:
        session.close()
    return 0


def cmd_review(args) -> int:
    cfg = _config_from_args(args)
    engine = build_engine(cfg.db_url)
    init_db(engine)
    session = build_session_factory(engine)()
    try:
        q = (session.query(Synonym)
             .filter(Synonym.status.in_(("ambiguous", "unresolved")))
             .order_by(Synonym.status, Synonym.name))
        rows = q.limit(args.limit).all() if args.limit else q.all()
        if not rows:
            print("Nothing to review. 🎉")
            return 0
        print(f"{len(rows)} name(s) need manual review:\n")
        for s in rows:
            print(f"  [{s.status:10s}] {s.name}\n       ↳ {s.review_reason}")
    finally:
        session.close()
    return 0


def cmd_stats(args) -> int:
    cfg = _config_from_args(args)
    engine = build_engine(cfg.db_url)
    init_db(engine)
    session = build_session_factory(engine)()
    try:
        mols = session.query(Molecule).count()
        syn_total = session.query(Synonym).count()
        resolved = session.query(Synonym).filter_by(status=STATUS_RESOLVED).count()
        extids = session.query(ExternalIdentifier).count()
        srcs = session.query(Source).count()
        print("=== moldedup stats ===")
        print(f"  molecules            : {mols}")
        print(f"  synonyms (total)     : {syn_total}")
        print(f"  synonyms (resolved)  : {resolved}")
        print(f"  synonyms (to review) : {syn_total - resolved}")
        print(f"  external identifiers : {extids}")
        print(f"  sources              : {srcs}")
    finally:
        session.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ingest.py", description="Molecular name dedup pipeline")
    p.add_argument("--db-url", help="SQLAlchemy URL (default $DATABASE_URL or sqlite:///moldedup.db)")
    p.add_argument("--cache", help="HTTP cache sqlite path")
    p.add_argument("--min-interval", type=float, help="min seconds between PubChem requests")
    p.add_argument("--log-level", default="INFO")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("init", help="create database tables")
    sp.set_defaults(func=cmd_init)

    sp = sub.add_parser("ingest", help="batch-import names from a CSV")
    sp.add_argument("csv")
    sp.add_argument("--column", help="CSV column holding the name (default 'name' or col 0)")
    sp.add_argument("--source", help="provenance label for this batch")
    sp.add_argument("--limit", type=int, help="only ingest the first N names")
    sp.add_argument("--no-header", action="store_true", help="treat the CSV as headerless (col 0 = name)")
    sp.set_defaults(func=cmd_ingest)

    sp = sub.add_parser("resolve", help="resolve + ingest a single name")
    sp.add_argument("name")
    sp.add_argument("--source")
    sp.set_defaults(func=cmd_resolve)

    sp = sub.add_parser("review", help="list names flagged for manual review")
    sp.add_argument("--limit", type=int)
    sp.set_defaults(func=cmd_review)

    sp = sub.add_parser("stats", help="print counts")
    sp.set_defaults(func=cmd_stats)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    _setup_logging(args.log_level)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
