# moldedup — molecular name deduplication pipeline

Resolve many different names of the same molecule into **one canonical record**,
keyed by the **Standard InChIKey**. Every synonym points to exactly one molecule.

- Canonical identity = **Standard InChIKey** (never CAS, CID or a name).
- Names are resolved through **PubChem PUG REST** (pluggable — add ChEBI/HMDB/KEGG later).
- Ambiguous names are **flagged for manual review**, never guessed.
- **SQLite for dev, PostgreSQL for prod**, via SQLAlchemy ORM.
- Caching, retries, timeouts, rate-limiting, logging, batch imports, a CLI, and unit tests.

---

## Install

```bash
cd molecular_pipeline
python3 -m pip install -r requirements.txt      # SQLAlchemy + requests
# optional, for tests:      python3 -m pip install pytest
# optional, for Postgres:   python3 -m pip install psycopg2-binary
```

## Quickstart

```bash
python ingest.py init                                   # create the tables (SQLite by default)
python ingest.py ingest sample_molecules.csv            # batch import a CSV of names
python ingest.py resolve "vanillin"                     # resolve one name and show the record
python ingest.py review                                 # names needing manual review
python ingest.py stats                                  # counts
```

`vanillin`, `Vanillin`, and `4-hydroxy-3-methoxybenzaldehyde` all collapse to a
**single** molecule (InChIKey `MWOOGOJBHIARFG-UHFFFAOYSA-N`), with each name kept
as a synonym.

### PostgreSQL (production)

```bash
export DATABASE_URL="postgresql+psycopg2://user:pass@host:5432/dbname"
python ingest.py init
python ingest.py ingest molecules.csv --source "flavor DB import"
```

The CSV can have a header (default column `name`, override with `--column`) or be
header-less (`--no-header`, first column is the name).

---

## Data model (normalized)

| Table | Purpose |
|---|---|
| `molecules` | one row per unique **Standard InChIKey** (+ InChI, CID, SMILES, formula, MW, IUPAC/preferred name) |
| `synonyms` | many names → one molecule; `normalized_name` is unique and answers "seen this name?"; `status` = resolved / unresolved / ambiguous |
| `external_identifiers` | CAS · CID · ChEBI · HMDB · KEGG · … per molecule |
| `sources` | provenance — which import/resolver introduced each synonym & identifier |

## The ingestion algorithm

For every name: **normalize → check existing synonym → resolve via PubChem →
get InChIKey → find molecule by InChIKey → attach (if found) or create (if not) →
store all identifiers, synonyms and provenance.** Unresolved and ambiguous names
are written as review-flagged synonyms with no molecule (surface them with
`python ingest.py review`).

## Architecture (modular / extensible)

```
moldedup/
  config.py            settings (env-overridable)
  models.py            SQLAlchemy ORM (the 4 tables)
  db.py                engine / session / init_db
  normalize.py         name normalization
  ratelimit.py         min-interval limiter
  cache.py             persistent HTTP cache (incl. negatives)
  pipeline.py          IngestionPipeline — the dedup logic
  cli.py               argparse CLI
  resolvers/
    base.py            Resolver ABC + ResolutionResult
    pubchem.py         PubChem PUG REST resolver
ingest.py              CLI entrypoint  →  python ingest.py ...
tests/                 pytest suite (network-free, fake resolver + mocked HTTP)
```

**Add a resolver** by subclassing `Resolver` and implementing
`resolve(name) -> ResolutionResult`. The pipeline depends only on that interface,
so ChEBI / HMDB / ChemSpider / KEGG resolvers drop in without changing the pipeline.
You can compose them (try PubChem, then fall back to ChEBI) behind one `Resolver`.

## Configuration (env vars)

`DATABASE_URL`, `MOLDEDUP_TIMEOUT`, `MOLDEDUP_MIN_INTERVAL`, `MOLDEDUP_MAX_RETRIES`,
`MOLDEDUP_BACKOFF`, `MOLDEDUP_CACHE`, `MOLDEDUP_CACHE_TTL`, `MOLDEDUP_LOG_LEVEL`.

## Tests

```bash
python3 -m pytest -q          # from molecular_pipeline/
```
Tests are network-free: the pipeline is exercised with a fake resolver and the
PubChem parser with a mocked HTTP session.

## Notes / limitations

- PubChem renamed the SMILES property fields in 2024; the resolver tries the
  classic names then falls back to the modern `SMILES` / `ConnectivitySMILES`.
- Salts/stereoisomers legitimately have different InChIKeys → they are *different*
  molecules by design. Standardize inputs upstream if you want them merged.
- CAS/ChEBI/HMDB/KEGG are harvested from PubChem synonyms; a dedicated resolver can
  provide richer cross-references later.
