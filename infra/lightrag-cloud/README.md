_Last updated: 2026-11-22 02:40 UTC · Claude (Fable 5.2) · rewritten to the deployed state after cleanup of one-off setup scripts_

# MeatCODE cloud knowledge graph (Render + Neon)

Design: `reports/LightRAG cloud deployment.md`. History: `AGENT_UPDATE_LOG.md` (21–22 Nov 2026). The graph is a candidate layer; it never writes to Neon scientific data.

## What runs (Render Blueprint `meatcode-lightrag-sandbox`, branch `lightrag-sandbox`, file `infra/lightrag-cloud/render.yaml`)
| Service | Role | Built from |
|---|---|---|
| `meatcode-lightrag` (web) | LightRAG 1.5.7, graph on a 10 GB disk; page login (AUTH_ACCOUNTS) + X-API-Key for programs | `Dockerfile.lightrag`, `entrypoint-lightrag.sh` |
| `meatcode-lightrag-ollama` (private) | bge-m3 embeddings, 1024-d | `Dockerfile.ollama`, `entrypoint-ollama.sh` |
| `meatcode-grobid` (private) | GROBID 0.8.2, pinned image | image only |
| `meatcode-kg-intake` (web) | keyed upload page, rights gate, guarded worker | `infra/kg-intake/`, `pipeline/grobid/{batch_worker,claims,ingestion_control}.py`, `pipeline/grobid/mcp/core.py` |

Staging site `dev-meatCODE` reads the graph through `server/graph_oracle.py` (`KG_ORACLE_REMOTE_URL`, `KG_ORACLE_REMOTE_API_KEY`).
Neon: branch `kg-lightrag` (`br-crimson-fog-alm2s63w`, child of dev): role/schema `lightrag_kg` (`neon/init_kg.sql`, applied; role NOLOGIN) and private bucket `lightrag-seed` (baseline archive). Reserved for the Phase-4 Postgres-backed workspace (`neon/lightrag_pg.env.example`); built by re-ingestion on a NEW service, never by repointing this one.

## Files kept here
- `render.yaml`, Dockerfiles, entrypoints: what Render builds. Nothing else is needed for the services to run.
- `kgctl.py` (+ test): control CLI (documents, entities, relations, export, query; destructive actions need `--yes`).
- `verify_replica.py`: compares a running instance with `data/backups/lightrag-baseline-20261121/MANIFEST.json`.
- `check_private.sh`: run before any commit; the GitHub repo is public.
- `.env.kg`, `.env.intake`: local keys (git-ignored, chmod 600). All service secrets live in Render.

## Not yet verified
A real upload through intake → GROBID → LightRAG; `verify_replica.py` against the live service; disk-restore drill; the Graph Oracle page on staging end to end.
