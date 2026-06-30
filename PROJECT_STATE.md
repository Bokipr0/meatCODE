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
- **Postgres schema** migrated (literature, molecules, experts, protocols, outputs — one schema).
- **Dimensions.ai ingester** added to the pipeline.
- **`docs/DATA_DICTIONARY.md`** (column-level schema map) and **`db/migrations/`** (forward-only migration convention) added.
- **New mockup** (`app/meatcode_mockup.html`, Jun 30) adds a Protocol Library and an aroma Prediction
  surface on top of Map / Oracle / Research.
- **Art-direction pass v8** (`UI-UX Designer/MeatCODE_mockup_v8_UIUX-polish.html`): teal-consistency
  fixes (avatar / bubbles / globe), emoji→SVG icons, personas realigned to the 4 real audiences,
  dashboard now fronts all 5 domains, Simulate marked *Preview*, molecular names monospaced.
  Candidate — awaiting Lior's approval to promote to `app/meatcode_mockup.html`. See `UI-UX Designer/DESIGN_NOTES_v8.md`.

## In flight
- Repo scaffold first push (this session). Pending local copy of two iCloud-only files
  (`analysis/streamlit_dashboard.py`, `app/expert_network_map.html`) — see Open items.
- Phase 0 closeout items still open in Asana: tagging taxonomy v0.1, hub architecture doc (sitemap +
  schema + journeys + UI), first mini-demo asset.

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
- **2026-06-30** — Canonical repo is a fresh `Bokipr0/meatCODE` (not the old `Airtable-rag`), to shed
  Airtable-migration baggage. Architecture = three homes: Git (code/docs) · Neon (data) · Asana (tasks).
  A single `PROJECT_STATE.md` is the cross-agent technical-status handoff.
- **2026-06-30** — Canonical local working tree for ALL agents is
  `/Users/lior/Documents/Claude/Projects/Claude Database/meatCODE` (already mounted into every cowork
  session). All agents read/edit/commit/push here; never edit MeatCODE files in the parent folder or iCloud.

## Open items / risks
- **Two artifacts not yet in repo** (were iCloud cloud-only during setup): copy from the GFI Database
  iCloud folder before first push — `streamlit_dashboard.py` → `analysis/`, `expert_network_map.html` → `app/`.
- **Source gap** — ~500 sources now in Neon (Lior, 2026-06-30; up from the 34 migrated). Still short of
  the 1,000–2,000 target, and the *citable* count is what matters: verify how many have non-null
  `abstract` + `search_vec` (only those surface in the Oracle's RAG). The Prediction surface in the
  mockup implies a model this corpus can't yet back — frame it as hypothesis-generation, not authority.
- **Neon auto-sleep** will bite concurrent multi-agent access; keep warm or front with `meatcode_server.py`.
- `__pycache__/` + `.DS_Store` copied into `server/reaktzia-mvp/` are permission-locked; `.gitignore`
  excludes them so they won't be committed.
