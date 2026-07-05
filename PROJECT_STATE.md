# PROJECT_STATE — MeatCODE

> Living technical status. **Every agent reads this after CLAUDE.md and updates it before pushing.**
> Asana owns *tasks & priorities*; this file owns *technical reality* — what's built, what's broken,
> what's in flight. Keep it short and current, not a changelog.

_Last updated: 2026-07-05 by Claude (advisory: corrected the stale "two backends" line to reflect the single `meatcode_server.py`; + Project Coordinator weekly sync — see AGENT_UPDATE_LOG.md and docs/2026-07-05_status_for_daniel.md)_

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
- **Single backend** (`server/meatcode_server.py`): `reaktzia-mvp/` was deleted 2026-07-05 — one stdlib
  server now serves the mockup + assets, the Oracle (`POST /api/ask`, SSE), and the Neon-backed
  expert/paper endpoints. _(Corrected 2026-07-05, advisory: this file previously listed "two backends".)_
- **Oracle live-demo wired**: `meatcode_server.py` serves the repo root so `app/meatcode_mockup.html` +
  assets load; model → `claude-sonnet-4-6`; `.env` read from repo root. `run_oracle.command` (double-click)
  starts the server and opens the mockup. Verified: compiles cleanly + SSE contract matches the mockup
  (`POST /api/ask` → `sources/chunk/done`, payload `{question}`). Pending only Lior adding
  `ANTHROPIC_API_KEY` to `meatCODE/.env` and running it.
- **Postgres schema** migrated (literature, molecules, experts, protocols, outputs — one schema).
- **Dimensions.ai ingester** added to the pipeline.
- **`docs/DATA_DICTIONARY.md`** (column-level schema map) and **`db/migrations/`** (forward-only migration convention) added.
- **Neon wiring:** `db/connect.py` shared accessor for all agents; `reaktzia-mvp/server.py` now also reads `.env` from the repo root, so a single `meatCODE/.env` powers both the server and agents. Live connection verified 2026-06-30.
- **FTS applied live:** `db/migrations/0001_sources_fts_search_vec.sql` run against Neon — `sources.search_vec` was missing (Oracle retrieval would have errored); now populated 496/496 + GIN index + auto-refresh trigger. Ranked retrieval confirmed working.
- **Taxonomy = governing bible:** `db/taxonomy/keywords_topics.json` (91 keywords, 5 branches) is the single source of truth. `db/taxonomy.py` is the one loader every script imports (no hardcoded topic lists); `pipeline/sync_taxonomy.py` upserts it into the `topics` table (synced live — 91 updated, 112 rows). `pipeline/openalex_ingest.py` now defaults its queries from the taxonomy and tags each new source to canonical topics via `source_topics`. Rule documented in CLAUDE.md.
- **Corpus expanded 496 → 828 sources (+332)** via `openalex_ingest.py` (now multi-source; **Europe PMC** default since OpenAlex full-text search was returning 503, OpenAlex selectable when healthy). All from 75 HIGH-priority taxonomy queries, deduped by DOI/provider-id, all citable (`search_vec`), all tagged to canonical branches (analytics 136, flavor_ingredients 67, meat_science 52, meat_analogs 43, flavor_chemistry 34). Next options: deeper pass (`--per-topic 15`) + MED topics toward 1,000; back-tag the original 496 to the taxonomy for uniform sorting.
- **Quality + priority scoring live (2026-07-01):** migration `0002_source_scoring.sql` added `priority_score`, `is_review`, `relevance_llm`. `pipeline/score_priority.py` = deterministic composite (relevance proxy · venue tier · review-type · citations/year · recency · taxonomy-tagged) + dedupe (removed 10 dupes → 818). `pipeline/score_relevance.py` = LLM gate (Haiku) scoring all 818 for meaty-process-flavor relevance 0-100; `priority_score` blends 60% LLM + 40% deterministic. Result: 45 sources ≥80, and **202 flagged <40 (keyword-matched but off-topic — nutrition/contaminants/health) = review/quarantine shortlist.** Use: rank hub/Oracle by `priority_score DESC`; Oracle should filter `relevance_llm >= 60` so it never cites off-topic papers. Tunable weights at top of score_priority.py.
- **Expert map now live-data-backed (2026-07-01):** `reaktzia-mvp` gained `GET /api/experts` (ranked, curated) + `GET /api/experts/{id}`; verified over HTTP. `app/meatcode_mockup.html` fetches them on load, replaces the demo `RESEARCHERS` in place (globe + list + detail), ranks by real `relevance_score`, falls back to demo data if the server is offline. Surfaces the **374 curated experts** (relevance-scored), not all 3,129 raw authors. Caveats: co-authorship edges cleared (`expert_relations` empty — no fake links); globe uses country→centroid coords w/ jitter (country data sparse).
- **`reaktzia-mvp/` deleted; `server/meatcode_server.py` is now the SOLE backend (2026-07-05).** It serves the repo (mockup + assets), the Oracle (`POST /api/ask`, SSE), and reads Neon for `GET /api/experts`, `/api/experts/{id}`, `/api/papers/{id}` (psycopg2 + `DATABASE_URL` from `.env`; degrades to 503→demo data if DB missing). `run_oracle.command` double-click starts it on :8000 and opens `app/meatcode_mockup.html` → interactive live expert map + Oracle. Verified end-to-end over HTTP.
- **Expert-map FILTERS shipped (2026-07-05, parallel team run — Data Eng + UI Designer):** `GET /api/experts` now accepts `q` / `country` / `sort`(relevance|h_index|papers) / `min_relevance` / `limit`; new `GET /api/expert-facets` returns country counts. The mockup's Map scene gained a `#mcFilterBar` (search, country select, sort buttons, "Top-rated only" toggle, reset, live count + loading/empty/error states) wired to those endpoints, reusing `window.mcApplyExperts` to re-render list+globe. Both sides verified (server live vs Neon; mockup `node --check` + HTTP load); **browser click-test still pending**. Known data issue: `experts.country` mixes ISO codes and full names → fragmented country facets; normalization pass recommended.
- **First white-space map (2026-07-05, parallel team run — Data Eng + Advisory):** `analysis/white_space_analysis.py` + `analysis/white_space_data.md` (empirical: 329/818 sources tagged; meat_analogs thinnest at 14% high-rel; **5 HIGH-priority topics with 0 tagged sources**) and `docs/white_space_map.md` (strategic map + ranked 10 research questions + 3 WUR quick-wins; gaps framed as hypotheses). The two AGREE — analog/plant-chemistry is the biggest gap (thiamine/sulfur route in plant bases, Maillard×lipid cross-talk, a_w effects on 2-AP/furanthiols, mechanism-first precursor design). ⚠️ **Provisional**: only ~40% of sources are tagged in `source_topics` — back-tag the 489 legacy sources before treating gaps as confirmed; molecules 784/799 uncategorized; claims only 45. Next: back-tag + re-rank, then Daniel sign-off.
- **New mockup** (`app/meatcode_mockup.html`, Jun 30) adds a Protocol Library and an aroma Prediction
  surface on top of Map / Oracle / Research.
- **Art-direction pass v8** (`UI-UX Designer/MeatCODE_mockup_v8_UIUX-polish.html`): teal-consistency
  fixes (avatar / bubbles / globe), emoji→SVG icons, personas realigned to the 4 real audiences,
  dashboard now fronts all 5 domains, Simulate marked *Preview*, molecular names monospaced.
  Candidate — awaiting Lior's approval to promote to `app/meatcode_mockup.html`. See `UI-UX Designer/DESIGN_NOTES_v8.md`.
- **Agent-team platform — STANDALONE Claude-Artifact build (2026-07-05):** `app/agent_team_artifact.html`
  is a single self-contained file (inline CSS/JS, no external requests, `localStorage` state) with the whole
  platform — pick/edit/add agents, multi-select, one goal, one-click **parallel** run, per-agent progress,
  Project Coordinator broadcast, runs history, activity feed. Agents run via the Claude Artifact runtime
  `window.claude.complete()`; outside an artifact it falls back to a clearly-labelled **Demo mode**. To use:
  paste into a Claude.ai conversation as an Artifact — no server. Verified live in a headless browser (demo).
  This is the standalone deliverable Lior asked for (the pinned artifact runs sandboxed = **Demo mode only**;
  it cannot reach Claude or Neon — live runs would need a hosted backend).
  **Published to claude.ai artifacts (2026-07-05):** https://claude.ai/code/artifact/39bb2bad-9d15-4655-8c12-097e261401b0
  (default-private, in Lior's pinned area; source of truth stays `app/agent_team_artifact.html` — re-publish from there on changes).
- **Server-wired agent dashboard REMOVED (2026-07-05):** the on-prem control panel (`app/agent_dashboard.html`
  + `server/agents.py` + the `/agents` page and `/api/agents`, `/api/team/*`, `/api/updates` routes) was
  deleted from `meatcode_server.py` at Lior's request. The server is back to Oracle + expert map + templates.
  Verified after removal: `/api/health`, `/templates/`, and `/api/experts` (live Neon) all still work; every
  agent route now 404s. `ThreadingHTTPServer` and the `pg_rows` connection-leak fix were kept (both are
  general server improvements, not agent-specific). The standalone artifact above is untouched.
- **Claude Design templates deployable (2026-07-05):** `app/templates/` is served by the sole backend
  `server/meatcode_server.py` — `/templates/…` pretty-URL rewrite (bare `/templates/` = gallery) plus
  `GET /api/templates` (self-populating listing) and `GET /api/papers/recent`. Any exported Design `.html`
  dropped in gains the same live Claude+Neon access as the mockup by including
  `<script src="meatcode-api.js"></script>` — the connector wraps `/api/ask` (SSE) + `health/paper/recentPapers`
  and adds zero-JS `data-mc-*` auto-wiring. Launch via `run_oracle.command`; gallery at
  `http://localhost:8000/templates/`. Smoke-tested live (health/templates/recent/gallery all serve; recent
  returned real Neon papers). See `app/templates/README.md` + `example-oracle.html`/`oracle-demo.html`.
  (The earlier `reaktzia-mvp` static-mount version of this was lost when that folder was deleted; refolded here.)
- **New screen designs handed off (2026-07-05, Claude Design session):** Home, Community Map,
  Food Oracle (empty/ask state screenshotted; answered + loading + modal states present in source),
  and Research phase picker — high-fidelity, on the MeatCODE Design System tokens. Packaged at
  `UI-UX Designer/design_handoffs/2026-07-05_home-map-oracle-research/` (README + screenshots +
  annotated source). These are the Claude Design templates the `app/templates/` serving work targets.
  Awaiting Lior's go on build target (deploy-as-served-HTML wired to Claude/Neon vs. Next.js rebuild),
  same review gate as the v8 polish pass.

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
