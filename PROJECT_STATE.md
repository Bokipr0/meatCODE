# PROJECT_STATE — MeatCODE

> Living technical status. **Every agent reads this after CLAUDE.md and updates it before pushing.**
> Asana owns *tasks & priorities*; this file owns *technical reality* — what's built, what's broken,
> what's in flight. Keep it short and current, not a changelog.

_Last updated: 2026-06-30 by Claude (art-director session: UI/UX v8 polish pass; data dictionary, migrations convention, source count)_

---

## Where we are
Phase 0 → Phase 1 hinge (per Asana: "MeatCODE – Open Flavor & Aroma Initiative", owned by Daniel).
Roadmap runs in 4 phases to Mar 2027: Phase 0 setup (May–Jun) · Phase 1 foundation build (Jun–Aug) ·
Phase 2 MVP hub (Sep–Nov) · Phase 3 validation (Nov–Jan) · Phase 4 scale-up proposal (Jan–Mar).

## Done
- **Repo established** (`Bokipr0/meatCODE`) as the single source of truth; three-homes model adopted
  (Git = code/docs, Neon = data, Asana = tasks). iCloud retired as shared memory.
- **Pipeline ↔ Layer C+E wired**: typed extraction (Layer C) + SQLite store (Layer E), `--mock` flag,
  cache check before Claude calls, run logging. Toggle via `USE_LAYER_C` / `USE_LAYER_E`.
- **3-tier relevance filtration**: Very (≥80%) / Mid (60–80%) / Little (<60%).
- **Streamlit dashboard** (6 tabs: Overview, Sources & Relevance, Molecules, Review Queue, Run History,
  Pipeline Controls).
- **Expert network map v3**: co-authorship lines, connection badges, network stats.
- **Two Oracle backends** coexist: `reaktzia-mvp/` (FastAPI + Neon + RAG, real cited papers) and the
  thin `meatcode_server.py` (SDK-only, SSE streaming, for fast demos / Neon-asleep fallback).
- **Oracle live-demo wired** (2026-06-30, advisory session): `meatcode_server.py` now serves the repo
  root so `app/meatcode_mockup.html` + assets load; model → `claude-sonnet-4-6`; `.env` read from repo
  root. `run_oracle.command` (double-click) starts the server and opens the mockup. Verified: compiles
  cleanly + SSE contract matches the mockup (`POST /api/ask` → `sources/chunk/done`, payload `{question}`).
  Pending only Lior adding `ANTHROPIC_API_KEY` to `meatCODE/.env` and running it. (Thin = no citations;
  RAG-with-citations = the `reaktzia-mvp/` server once `DATABASE_URL` is in `.env`.)
- **Postgres schema** migrated (literature, molecules, experts, protocols, outputs — one schema).
- **Dimensions.ai ingester** added to the pipeline.
- **`docs/DATA_DICTIONARY.md`** (column-level schema map) and **`db/migrations/`** (forward-only migration convention) added.
- **Neon wiring:** `db/connect.py` shared accessor for all agents; `reaktzia-mvp/server.py` now also reads `.env` from the repo root, so a single `meatCODE/.env` powers both the server and agents. Live connection verified 2026-06-30.
- **FTS applied live:** `db/migrations/0001_sources_fts_search_vec.sql` run against Neon — `sources.search_vec` was missing (Oracle retrieval would have errored); now populated 496/496 + GIN index + auto-refresh trigger. Ranked retrieval confirmed working.
- **Taxonomy = governing bible:** `db/taxonomy/keywords_topics.json` (91 keywords, 5 branches) is the single source of truth. `db/taxonomy.py` is the one loader every script imports (no hardcoded topic lists); `pipeline/sync_taxonomy.py` upserts it into the `topics` table (synced live — 91 updated, 112 rows). `pipeline/openalex_ingest.py` now defaults its queries from the taxonomy and tags each new source to canonical topics via `source_topics`. Rule documented in CLAUDE.md.
- **Corpus expanded 496 → 828 sources (+332)** via `openalex_ingest.py` (now multi-source; **Europe PMC** default since OpenAlex full-text search was returning 503, OpenAlex selectable when healthy). All from 75 HIGH-priority taxonomy queries, deduped by DOI/provider-id, all citable (`search_vec`), all tagged to canonical branches (analytics 136, flavor_ingredients 67, meat_science 52, meat_analogs 43, flavor_chemistry 34). Next options: deeper pass (`--per-topic 15`) + MED topics toward 1,000; back-tag the original 496 to the taxonomy for uniform sorting.
- **Quality + priority scoring live (2026-07-01):** migration `0002_source_scoring.sql` added `priority_score`, `is_review`, `relevance_llm`. `pipeline/score_priority.py` = deterministic composite (relevance proxy · venue tier · review-type · citations/year · recency · taxonomy-tagged) + dedupe (removed 10 dupes → 818). `pipeline/score_relevance.py` = LLM gate (Haiku) scoring all 818 for meaty-process-flavor relevance 0-100; `priority_score` blends 60% LLM + 40% deterministic. Result: 45 sources ≥80, and **202 flagged <40 (keyword-matched but off-topic — nutrition/contaminants/health) = review/quarantine shortlist.** Use: rank hub/Oracle by `priority_score DESC`; Oracle should filter `relevance_llm >= 60` so it never cites off-topic papers. Tunable weights at top of score_priority.py.
- **New mockup** (`app/meatcode_mockup.html`, Jun 30) adds a Protocol Library and an aroma Prediction
  surface on top of Map / Oracle / Research.
- **Art-direction pass v8** (`UI-UX Designer/MeatCODE_mockup_v8_UIUX-polish.html`): teal-consistency
  fixes (avatar / bubbles / globe), emoji→SVG icons, personas realigned to the 4 real audiences,
  dashboard now fronts all 5 domains, Simulate marked *Preview*, molecular names monospaced.
  Candidate — awaiting Lior's approval to promote to `app/meatcode_mockup.html`. See `UI-UX Designer/DESIGN_NOTES_v8.md`.

## In flight
- Repo scaffold first push (this session). Pending local copy of two iCloud-only files
  (`analysis/streamlit_dashboard.py`, `app/expert_network_map.html`) — see Open items.
- Phase 0 closeout items: **tagging taxonomy v0.1** → drafted `docs/TAGGING_TAXONOMY_v0.1.md` (7 faceted
  axes anchored on existing topics + schema ENUMs; awaiting Lior's topics `.md` + sensory-list confirm).
  **Hub architecture** → drafted `docs/HUB_ARCHITECTURE_v0.1.md` (tight 4-surface MVP: Oracle/Literature/
  Expert/Molecular; sitemap, data model, journeys, tool stack). Both awaiting Daniel sign-off. First
  mini-demo asset = the live Oracle (`run_oracle.command`), pending Lior's `.env` key.

## Next (highest leverage first)
1. **Literature collection — the crux.** Get from ~34 to 1,000–2,000 high-value sources (Asana due Jul 31).
   Everything downstream (Oracle quality, molecular DB, white-space analysis) depends on it.
2. **Tool-stack + hub-architecture docs** (Asana, due Jun 30) — largely answered by this repo's
   three-homes model; write it up formally for Daniel's approval.
3. Tag + summarize first 30–50 sources with the standard template.
4. Load Anthropic credits and run the live pipeline end-to-end (not `--mock`).
5. Drop `.env` (`DATABASE_URL`) into the repo → run the **retrievability check** (count sources with
   non-null `abstract` + `search_vec`); that's the true size of the citable corpus.

## Decisions (most recent first)
- **2026-06-30** — Design deliverables live in `meatCODE/UI-UX Designer/`. Product brand is unified on
  GFI seaweed-teal (wine/pomegranate retired). v8 polish is a review candidate; promoting it to the
  canonical `app/meatcode_mockup.html` needs Lior's go.
- **2026-06-30** — Canonical repo is a fresh `Bokipr0/meatCODE` (not the old `Airtable-rag`), to shed
  Airtable-migration baggage. Architecture = three homes: Git (code/docs) · Neon (data) · Asana (tasks).
  A single `PROJECT_STATE.md` is the cross-agent technical-status handoff.
- **2026-06-30** — Canonical local working tree for ALL agents is
  `/Users/lior/Documents/Claude/Projects/Claude Database/meatCODE` (already mounted into every cowork
  session). All agents read/edit/commit/push here; never edit MeatCODE files in the parent folder or iCloud.

## Open items / risks
- **Two artifacts not yet in repo** (were iCloud cloud-only during setup): copy from the GFI Database
  iCloud folder before first push — `streamlit_dashboard.py` → `analysis/`, `expert_network_map.html` → `app/`.
- **Source corpus (verified live 2026-06-30):** 496 sources (462 with abstracts), 799 molecules,
  **3,129 experts** (Dimensions ingest — far above the old 374), 45 claims. The Prediction surface in
  the mockup implies a model this corpus can't yet back — frame as hypothesis-generation, not authority.
  Still short of the 1,000–2,000 source target (Phase 1 crux).
- **Oracle recall — tune next:** `reaktzia-mvp/retrieval.py` uses `websearch_to_tsquery`, which ANDs all
  terms, so a full natural-language question often matches **0 rows** and the Oracle silently falls back
  to no-sources. Switch to keyword extraction or OR/`|` query semantics to lift recall before any expert demo.
- **Neon auto-sleep** will bite concurrent multi-agent access; keep warm or front with `meatcode_server.py`.
- `__pycache__/` + `.DS_Store` copied into `server/reaktzia-mvp/` are permission-locked; `.gitignore`
  excludes them so they won't be committed.
