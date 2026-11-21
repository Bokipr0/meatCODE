_Last updated: 2026-11-21 21:58 UTC · Claude (Opus 5.5) · §0 update: Neon branch + bucket live, push/upload script ready · prev 21:34 Sonnet 5.5_

## 0. UPDATE 21:58 UTC (supersedes §4 rows for Neon/seed)
- Neon `kg-lightrag` = `br-crimson-fog-alm2s63w` (parent dev `br-orange-fog-alnxovak`, project `holy-mode-78356834`); init_kg.sql applied (role NOLOGIN). Private bucket `lightrag-seed`, key `baseline-20261121/rag_storage.tar.gz` (upload pending).
- Lior decided: seed may go to that private bucket; Render via in-app browser; push via `data/lightrag-cloud/publish-lightrag-sandbox.command` (branch `lightrag-sandbox`).
- GitHub repo is PUBLIC. Render/Neon-storage hosts blocked by session egress.

# HANDOFF: MeatCODE LightRAG cloud sandbox (as of 2026-11-21, ~22:45 local)

Self-contained brief for the next agent. Read it fully before acting. Contains no secrets; never add any.
Repo root: `/Users/lior/Documents/Claude/Projects/Claude Database/meatCODE` (branch `dev`, remote `https://github.com/Bokipr0/meatCODE.git`).
Sibling docs: `reports/LightRAG cloud deployment.md` (design + gates), `research_notes/LightRAG cloud deployment/*.md` (3 audits), `infra/lightrag-cloud/README.md` (runbook/status table).

## 1. Who/what
- User: Lior at GFI Israel. MeatCODE = GFI Israel's validation-stage platform for engineering meaty flavor (process-flavor chemistry). Key repo docs: `START_HERE.md`, `ROLES.md`, `CLAUDE.md`, `PROJECT_STATE.md` (newer than the October snapshots; `MVP_BOARD.md` and most of `TEAM_BROADCAST.md` are stale).
- Architecture: Git = code truth; Neon = scientific system of record (graph/vector layers are derived projections, never scientific authority); Render = stateless runtime (`main`->prod `meatcode-oracle`, `dev`->staging `meatcode`); Asana = priorities. Deploys are done by Lior via `Release Center/*.command`.
- Rules that apply: never invent chemistry/citations/validation claims; unknown scientific values stay NULL; publisher-derived full text must not be publicly exposed; Neon schema changes are additive, numbered migrations, staging first; staging and production Neon branches differ (prod has a 96-person expert import and Neon Auth tables; dev has pgvector + `lightrag_demo`).
- Pronouns: use they/them for the user unless stated. Do not put the user's name/email/project details into external service requests.

## 2. The request in this thread
1. Lior has a local LightRAG app (`~/LightRAG`, 1.5.7, port 9621) and asked to move it to the cloud: "Neon if possible, otherwise another sandbox" where Lior can feed it data.
2. Research (3 subagents + report) concluded: **Neon can store LightRAG state (pgvector/KV/graph/doc-status, Object Storage) but cannot run it** (Neon Functions = Node/TS only; no Python/GROBID/Ollama). So hybrid: Render Docker service + persistent disk first; Neon-backed rebuild later by **re-ingestion** (LightRAG cannot convert file stores -> Postgres).
3. Lior approved: two Render services (authenticated LightRAG + private Ollama bge-m3), preserve the current graph AND embedding space, create a Neon KG branch, and build a working verified pipeline with control over the KG (edit, add files). Latest instruction: **use `standard` plans; wire the GROBID worker to the hosted URL; "create the neon + render api"** (interpreted as: set up API access/provisioning for both).

## 3. Done and verified
- **Baseline** (immutable, chmod 444): `data/backups/lightrag-baseline-20261121/{rag_storage.tar.gz,MANIFEST.json}` (`data/` is git-ignored). 7,579 nodes / 10,284 edges / 33 docs (32 processed, 1 failed). Archive sha256 `b55a2e38e766bbfe0f3a5295342766ce2796be758d9256c18f2dd65fabe6d38a`, 120 MB. Config: Sonnet `claude-sonnet-4-6` for all reasoning roles via Anthropic's OpenAI-compatible endpoint; embeddings Ollama `bge-m3:latest`, dim 1024, ctx 8192. Live `~/LightRAG/rag_storage` verified byte-identical to baseline (only the two largest files hashed) and untouched.
- **`infra/lightrag-cloud/`** (all untracked in git):
  - `make_baseline.py`, `Dockerfile.lightrag` + `entrypoint-lightrag.sh` (refuses start without >=32-char `LIGHTRAG_API_KEY`; seeds an EMPTY disk from `SEED_ARCHIVE_URL` after sha256 check), `Dockerfile.ollama` + `entrypoint-ollama.sh`, `render.yaml` (separate blueprint, both `standard`, frankfurt, disks 10 GB + 5 GB, `MAX_GRAPH_NODES=20000`), `env.example`, `.env.cloud.example`.
  - `kgctl.py` + `test_kgctl.py` (6 tests): CLI over LightRAG API (header `X-API-Key`). **Verified against a real LightRAG 1.5.7 replica**: entity create/edit/merge/delete + relation create round-trip left counts exactly at baseline.
  - `verify_replica.py`: compares a running instance to MANIFEST; all 4 checks PASS on the local replica (auth enforced = 403 without key, version, doc counts, graph 7579/10284).
  - `provision_render.py` + `test_provision_render.py` (5 tests): Render API provisioner; dry-run default, `--apply` to create; idempotent by service name; ollama created first; refuses silent empty graph (needs seed vars or `--empty`); masks secrets in output. Dry-run output inspected; **Render payload schema NOT validated against a live account**.
  - `neon/create_kg_branch.sh` (refuses parent matching prod/main; uses `neonctl` 9.9.3 via npx, reads `NEON_API_KEY`), `neon/init_kg.sql` (pgvector, role `lightrag_kg`, schema `lightrag_kg`, least privilege), `neon/lightrag_pg.env.example` (Phase-4 PG adapters: PGKVStorage, PGVectorStorage, PGDocStatusStorage, PGTableGraphStorage). **Not run.**
- **GROBID worker wired** (`pipeline/grobid/batch_worker.py`, `test_batch_worker.py`; both untracked/new): `validate_target` (non-local URL must be https, no embedded creds, key >=32 chars; also checked at startup in `main()` before any network call), `hosted_unreviewed` (pauses ingestion if the hosted graph has documents not in baseline inventory or the ledger), local `~/LightRAG/.env` key probe skipped for hosted targets (role config still checked via hosted `/health`). 28 tests pass across `test_batch_worker test_ingestion_control test_overnight test_claims test_repository_rescue`. **Not exercised against a real hosted instance.**
- `.gitignore` additions: `.env.kg`, `.env.cloud`, `infra/lightrag-cloud/kg_audit.jsonl`.

## 4. NOT done / blocked
| Item | Blocker |
|---|---|
| Create Neon branch `kg-lightrag`, run `init_kg.sql` | No Neon credentials on this machine (`neonctl me` -> not signed in; no `NEON_API_KEY`). Need project ID + **development** branch name as parent. Never parent on production. |
| Create the two Render services | No `RENDER_API_KEY`; no Render CLI. The native Render/Neon plugins are disabled by workspace policy. Render builds from GitHub, and `infra/` is untracked locally. |
| Code Render can build | **Agents never run git here (repo CLAUDE.md); Lior publishes from his Mac via `Release Center/`.** The earlier idea of an agent creating/pushing a `lightrag-sandbox` branch is WITHDRAWN. Lior must commit `infra/lightrag-cloud` (and the worker changes) and push; note `dev`->staging auto-deploys and the tree has ~140 unrelated uncommitted entries, so ask him to commit only these paths, or use a branch he creates. |
| Seed archive to Render | Open question: archive contains publisher-derived text. Needs a private bucket + short-lived presigned URL, or start empty (`--empty`) with rights-cleared/open-access papers only. Lior has not answered. Report says a rights decision (cloud storage, model processing, geography, retention, deletion) is a hard gate before publisher material leaves the machine. |
| `kgctl query`, upload/ingest, Docker builds, Render run, hosted GROBID flow | Unverified (query needs a real LLM key; no Docker build attempted). |
| Phase 4 Neon-backed workspace; Graph Oracle adaptation | Later gates; Graph Oracle (`app/modules/graph-oracle.*`, `server/graph_oracle.py`) reads a local GraphML and local snapshots/outbox, so it needs adapting before cutover. |

## 5. Next steps (in order, ask Lior before each outward action)
1. Lior supplies keys by filling `infra/lightrag-cloud/.env.cloud` (chmod 600) with `RENDER_API_KEY`, `NEON_API_KEY` (+ seed vars if seeding). Never ask for keys in chat or echo them.
2. Get answers to the 3 open questions above (branch push, seed archive, Neon project/dev-branch ID).
3. Ask Lior to commit/push `infra/lightrag-cloud/` + `pipeline/grobid/batch_worker.py` + `test_batch_worker.py` + `.gitignore` himself (agents don't run git). Render can only build what is on GitHub.
4. From `infra/lightrag-cloud` run `python3 provision_render.py --repo https://github.com/Bokipr0/meatCODE --branch lightrag-sandbox --anthropic-key-from ~/LightRAG/.env` (dry-run), review, then `--apply`. If the Render API rejects the payload, fix the schema (compare with Render API docs) rather than weakening safeguards. Reusing the local Anthropic key on Render is a credential transfer: mention it to Lior.
5. After deploy: `python3 verify_replica.py --manifest data/backups/lightrag-baseline-20261121/MANIFEST.json` with `KG_URL`/`KG_API_KEY` set (env or `.env.kg`); run a restart-persistence test and a disk restore drill; then `kgctl query` with a real key.
6. Create the Neon branch via `neon/create_kg_branch.sh` (dev parent), run `init_kg.sql`. Only use it in Phase 4 on a NEW Render service with empty workspace + re-ingestion; do not repoint the baseline service.
7. Hosted feed: `cp -R data/grobid/batch data/grobid/batch-cloud`, then `python3 pipeline/grobid/batch_worker.py --once --lightrag-url https://<service>.onrender.com --output data/grobid/batch-cloud` with `LIGHTRAG_API_KEY` exported. Check `--status` first; resolve any `submitted`/`submission_unknown`/`failed` ledger rows locally first (they block ingestion by design). One PDF (`1HNlGHoC6Qh3H6wZQuf3qbYPa-whzqGSV.pdf`) is `review_required` (no reliable DOI); 528 Rebecca PDFs are staged but staging is not admission.

## 6. Local-machine state and gotchas
- Local LightRAG was NOT running when checked (port 9621 empty); Ollama is running with `qwen3.5:9b` and `bge-m3:latest`. Do not modify `~/LightRAG`; it is the rollback reference.
- A throwaway replica lived under the session scratchpad; it was stopped (port 9631 free). Don't `pkill -f lightrag-server` by name (could hit a live instance); kill by port with `lsof -ti :PORT | xargs kill`.
- Test invocation: run from the directory (`cd infra/lightrag-cloud && python3 -m unittest test_kgctl test_provision_render`). Don't use `python -I` for these (it strips the cwd from the import path).
- LightRAG defaults that bit us: `MAX_GRAPH_NODES=1000` silently truncates `/graphs` (set 20000 in cloud); API-key auth returns 403 without `X-API-Key`; `/health` shows `auth_mode: disabled` even when the API key is enforced (that field refers to account auth). Graph edit endpoints: `/graph/entity/{create,edit,delete}`, `/graph/entities/merge`, `/graph/relation/{create,edit,delete}` (DELETE with JSON body); docs: `/documents/{upload,text,paginated,delete_document,reprocess_failed,status_counts,pipeline_status}`.
- Render disks attach to one service instance (no horizontal scaling, no sharing with a worker); that's why query + ingestion stay in one service for the pilot.
- Support counts for any scientific graph claim must be distinct validated paper IDs, not LightRAG `weight`. Graph size is not scientific correctness; nothing here updates Neon scientific data or canonical knowledge.
- Git: **agents do not run git in this repo** (parent and repo CLAUDE.md); Lior publishes via `Release Center/`. ~140 uncommitted/untracked entries from other work exist, so any commit must be path-specific. Session-end protocol from CLAUDE.md: stamp changed files, append to `AGENT_UPDATE_LOG.md` (newest first), update `PROJECT_STATE.md`. All three were done for this thread at 2026-11-21 21:34 UTC.
- Live-state facts gathered earlier (may have changed): prod `meatcode-oracle` commit `38c1cda4f7eb`, staging `236eec1241bd`; migration `0031` applied on Neon dev (not prod); `user_accounts` flag off; research logs live in a dedicated `research_prod` DB. Render `/api/health` checks are configuration-only.
- Original Codex session transcript (may be cleaned up): `/var/folders/h9/jz3l27k97xn_1f5s0th8kyhh0000gn/T/orca-handoff-5fba14da4f2edce4-501/580e1c8d351383ec759bb5465677949ea2f17c0e4a2a9ef956e26cf1c901bd8e.txt` (read-only).
