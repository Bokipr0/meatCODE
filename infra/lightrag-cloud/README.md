_Last updated: 2026-11-21 21:34 UTC · Claude (Sonnet 5.5) · runbook and status table_

# LightRAG cloud sandbox (Render + private Ollama; Neon KG branch for Phase 4)

Design and rationale: `reports/LightRAG cloud deployment.md`. This folder is the implementation.

| File | Purpose | Status |
|---|---|---|
| `make_baseline.py` | Freeze local graph + manifest (counts, sha256, embedding config) | **Done**: `data/backups/lightrag-baseline-20261121/` |
| `Dockerfile.lightrag`, `entrypoint-lightrag.sh` | LightRAG 1.5.7; refuses to start without a >=32-char API key; seeds an *empty* disk from a SHA-verified archive | Written, not built |
| `Dockerfile.ollama`, `entrypoint-ollama.sh` | Private bge-m3 (1024-d) embeddings, same space as baseline | Written, not built |
| `render.yaml` | Separate Blueprint (2 services, 2 disks); root `render.yaml` untouched | Written, **not deployed** |
| `kgctl.py` (+`test_kgctl.py`) | Control CLI: upload, delete doc, entity/relation create/edit/merge/delete, export, query, audit log | **Verified** against real LightRAG 1.5.7 |
| `verify_replica.py` | Checks any instance against the baseline manifest | **Verified** on a local replica |
| `provision_render.py` | Creates both Render services via API; dry-run by default, idempotent, refuses an accidental empty graph | Tested offline; **not applied** |
| `neon/` | `create_kg_branch.sh`, `init_kg.sql`, PG-backend env template | Written, **not run** (needs `neon login`) |

## Verified so far (2026-11-21)
- Baseline: 7,579 nodes / 10,284 edges / 33 docs (32 processed, 1 failed), archive sha256 `b55a2e38...6fabe6d38a`.
- Restore from archive into a clean dir, served by LightRAG 1.5.7 with API key: unauthenticated -> 403; counts match baseline.
- `kgctl` entity create/edit/relation/merge/delete round-trip on throwaway entities left graph at exactly baseline counts.
- Live `~/LightRAG/rag_storage` is byte-identical to the baseline (untouched).
- **Not yet verified:** `query` (needs real LLM key), upload/ingest, Docker builds, Render, Neon.

## Findings that change the plan
- LightRAG caps graph reads at `MAX_GRAPH_NODES=1000` by default - exports silently truncate. Set to 20000 in `render.yaml`.
- The baseline contains 1 failed doc; it was carried over as-is (use `kgctl reprocess-failed` deliberately).

## Hosted GROBID worker (wired 2026-11-21)
`pipeline/grobid/batch_worker.py --lightrag-url https://meatcode-lightrag.onrender.com` (key in `LIGHTRAG_API_KEY`):
- refuses non-local URLs unless `https://` with a >=32-char key (the key is never sent over http);
- pauses ingestion if the hosted graph holds any document not in the baseline or the worker's ledger
  (anything added via WebUI/`kgctl upload` bypasses DOI/hash/overlap checks);
- skips the local `~/LightRAG/.env` key probe (the hosted service owns its credential; role config is still verified via `/health`).
Use a separate ledger: `cp -R data/grobid/batch data/grobid/batch-cloud` then `--output data/grobid/batch-cloud`. GROBID parsing stays local; only cleaned body text is sent. `overnight.py` / `background_worker.py` remain local-only.
Tests: 28 pass (`python3 -m unittest` in `pipeline/grobid`); not yet exercised against a real hosted instance.

## Needs you (cannot be done from this machine)
1. **Commit + push** (Lior, from the Mac; agents don't run git): `infra/lightrag-cloud/`, `pipeline/grobid/batch_worker.py`, `test_batch_worker.py`, `.gitignore`. Render can only build what is on GitHub; `dev` auto-deploys staging, so use a branch or commit only those paths.
1. **Render**: create the Blueprint from `infra/lightrag-cloud/render.yaml`. Two standard instances + 15 GB disks is recurring cost (you approved the two-service shape; confirm the plan size). Set `LIGHTRAG_API_KEY` (e.g. `python3 -c "import secrets;print(secrets.token_urlsafe(48))"`), `LLM_BINDING_API_KEY`, `KEYWORD_LLM_BINDING_API_KEY`.
2. **Seed archive**: the baseline archive is 120 MB of unpublished corpus-derived data; upload it to a *private* bucket (e.g. your existing S3 backup bucket) and give Render a short-lived presigned URL + the SHA-256 above. Corpus includes publisher-derived text - confirm the rights decision before it leaves your machine.
3. **Neon**: run `neon login`, then `neon/create_kg_branch.sh` (parent = development branch, never production).

## Backups
Before any destructive `kgctl` action on the hosted instance, snapshot the Render disk (Dashboard -> Disks -> Snapshot) and note the time in `kg_audit.jsonl` context.

## Feeding it
`kgctl upload paper.pdf` goes straight through LightRAG's own pipeline and **bypasses** the guarded GROBID DOI/hash/overlap checks. For governed bulk feeds, point `pipeline/grobid/batch_worker.py` at the hosted URL (not yet wired - next step).
