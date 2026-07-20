# PROJECT_STATE — MeatCODE

> Living technical status. **Every agent reads this after CLAUDE.md and updates it before pushing.**
> Asana owns *tasks & priorities*; this file owns *technical reality* — what's built, what's broken,
> what's in flight. Keep it short and current, not a changelog.

_Last updated: 2026-07-20 12:49 UTC · Project Coordinator — parallel team run: Oracle v11 (dictation · dynamic pinned-above-history sidebar · bigger save icon · "Digging the MeatCODE database" copy + additive SSE `status` event). Prev: 2026-07-08 ~10:10 UTC team broadcast; see AGENT_UPDATE_LOG.md_

## Oracle v11 — shipped to the repo 2026-07-20 (awaiting deploy)
Four user-requested Oracle features, built by a 3-agent parallel run:
- **Voice dictation** in the ask box (Web Speech API; button hidden where unsupported) — needs a real-browser test.
- **Save/bookmark icon enlarged** to a 34px target, scoped to the Oracle sidebar only.
- **Sidebar rebuilt as dynamic Pinned-above-History** — asking appends to History, the bookmark promotes a chat to Pinned; persisted in `localStorage` (`mc_oracle_history_v1`, 25/list cap, try/catch throughout). Deliberately client-side: the site is behind ONE shared password, so there is **no per-user identity** to key server-side history to — see `docs/oracle_chat_history_design.md`.
- **No model name shown to users**: "Searching the database and asking Claude…" → **"Digging the MeatCODE database…"**; server error text is now vendor-neutral (real diagnostic kept in Render logs). `POST /api/ask` gained an **additive** `event: status` (`retrieving`/`answering`) so the phase label is honest; fully backward-compatible.
Verified: 10/10 inline script blocks parse in both mockups (byte-identical), server `py_compile` clean, SSE order `status→sources→status→chunk→done`. **Not yet deployed — run `deploy.command`.**
Open decision for Lior + Daniel: whether to add an anonymous server-side question log (no identity) as validation-year evidence.

---

## 📣 Latest team broadcast — 2026-07-20 ~13:10 UTC
Project Coordinator has notified the team. **Every agent: read [`TEAM_BROADCAST.md`](TEAM_BROADCAST.md)** for what shipped and your next move. Headline: **Oracle v11 shipped** (dictation · pinned-above-history sidebar · honest `event: status` phases · zero user-facing model mentions) on top of the **grounded retrieval** milestone; site is always-on + password-gated; expired-sign-in now reported in plain language. **⚠️ Open #1 risk: confirmed quarantines write only to `source_audits`, NOT `sources.relevance_llm` — Daniel-rejected sources remain retrievable. Close before WUR.** Open decision for Lior + Daniel: anonymous server-side question log?

---

## Where we are
Phase 0 → Phase 1 hinge (per Asana: "MeatCODE – Open Flavor & Aroma Initiative", owned by Daniel).
Roadmap runs in 4 phases to Mar 2027: Phase 0 setup (May–Jun) · Phase 1 foundation build (Jun–Aug) ·
Phase 2 MVP hub (Sep–Nov) · Phase 3 validation (Nov–Jan) · Phase 4 scale-up proposal (Jan–Mar).

## Done
- **Data-audit loop — BUILT + VERIFIED (2026-07-07, parallel team):** recurring every-2-days source
  authentication. `pipeline/audit_sources.py` (Data Engineer) selects 20 sources by dynamic priority
  (importance × staleness × uncertainty), pulls each one's info + tags + connected taxonomy queries, and
  writes verdicts to the new `source_audits` table (migration `0003`, **applied live to Neon**) + a dated
  `docs/audits/` report. `pipeline/audit_judge.py` (Algorithm Expert) = Haiku judge (tag/relevance/quality
  → keep|review|quarantine, safe fallback, never crashes the batch) + `update_weights` self-reweighting.
  `docs/data_audit_loop.md` (Advisory) = design of record; `analysis/audit_eval.md` = gold-set validation
  method. Verified end-to-end vs live Neon (150-candidate pull, DB write path OK, table left clean).
  Registered as a scheduled task (`0 9 */2 * *`) running `--n 20`. Cost ≈20 Haiku judgements/run (cents/mo).
  Directly targets the corpus-quality risk (40% tagged, 202 flagged <40) + the Asana "validate source
  quality" task. NOTE: `audit_sources.py` was made self-sufficient (direct psycopg2 fallback) because the
  local `db/connect.py` **source** is missing (only `.pyc` survived a sync) — do a `git pull` on the Mac.
  Next: hand-label `analysis/audit_gold.csv` (30–50) to measure quarantine precision before enabling
  auto-apply; wire quarantines into the dashboard Review Queue tab.
- **Database section + map upgrade shipped (2026-07-07, parallel team — Data Eng + UI):** Backend
  (`server/meatcode_server.py`) added read-only `GET /api/molecules`, `/api/sources`, `/api/companies`,
  `/api/db-facets` (SELECT-only). Frontend (`app/meatcode_mockup.html`): IA made more minimal — **Database**
  promoted to a top-level domain, **Toolbench moved inside Research**; new `#database` scene with 4 tabs
  (Molecules/Experts/Companies/Sources), live filter/sort, row-detail modal, and **client-side XLSX export**
  (SheetJS). Map enlarged, defaults to **top-15-by-relevance** experts, country-click expands that area,
  dot→short profile with "View full profile" → routes into the Database. Verified end-to-end (endpoints
  return live Neon rows; mockup serves 268 KB; all 5 inline scripts pass `node --check`). ⚠️ TWO DATA GAPS:
  (1) **Companies tab — SEEDED (2026-07-07)** — `organizations` was empty; now backfilled with 37 curated
  orgs (29 companies + 8 NGOs) via `db/migrations/0004_seed_organizations.sql` (applied live); `/api/companies`
  returns them, filterable by country. (`experts.org_type` still NULL — expert↔org linkage is a separate optional enrichment.)
- **Per-source tag columns added (2026-07-07, `0005`):** `sources` gained `pathway`, `method`, `sensory_descriptor`, `matrix`, `compound_class` (`TEXT[]`) + `study_type`, `main_claim` (`TEXT`) — all NULL, to be filled later by an LLM extraction/curation pass. ("Min Compound class" read as Main Compound class.)
- **Relational tagging system live (2026-07-08, `0006`):** unified `tags(category, name, slug)` + `source_tags(source_id, tag_id)` junction for the 5 multi-valued tags (pathway/method/sensory_descriptor/matrix/compound_class); `study_type`+`main_claim` stay columns. `pipeline/promote_tags.py` (re-runnable) promotes the flat `sources.*` arrays → **571 tags / 3,457 links across 748 sources** (all 818 tagged 2026-07-08). Junctions kept: `source_topics` + `source_molecules` + new `source_tags`; empty legacy junctions (source_reactions/methods/sensory/product_contexts) superseded (left as legacy). How-to-query + retrieval guide: `docs/tagging_relational_guide.md`. **Tagging complete: 818/818** (`tag_sources.py` gained `--workers` concurrency and was run from the sandbox — Lior's local PyCharm run failed on Python-3.9 `psycopg2` missing). ⚠️ **Oracle `/api/ask` still sends `sources: []`** (no live retrieval); `search_vec` populated but unwired — wiring tag+FTS retrieval is the concrete next step. (2) **Sources `sort=citations` surfaces off-topic
  papers** (raw citations favor off-domain reviews) — default the Sources tab to `priority_score`/relevance.
  Data-entry (write-back) intentionally deferred (unsafe unauthenticated writes); browser click-test pending.
- **Render deploy LIVE + Database-tab same-origin fix (2026-07-07):** `meatcode-oracle.onrender.com` is
  running the real server (keys set, `/api/health` OK) — first live public URL for the platform:
  `https://meatcode-oracle.onrender.com/app/meatcode_mockup.html`. Hardened the bare root (`/` no longer
  directory-lists the repo — 302s to the mockup; dotfiles/`.git`/`.command`/`.env` blocked). Same day, fixed
  a same-origin bug that showed Database/Experts/Companies as "offline" on the deployed site: an
  `API_BASE === ''` (same-origin) guard was falsy and silently fell back to the visitor's own `localhost`;
  fixed in 3 places in `app/meatcode_mockup.html`. Verified: those tabs now load live Neon data on the
  deployed URL, not just on localhost.
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
- **Research screenflow design (2026-07-05, parallel UI/UX team run):** two specialists on disjoint files —
  `UI-UX Designer/RESEARCH_SCREENFLOW_SPEC.md` (IA/wireframe spec: Oracle as connective tissue unifying
  Literature + Molecular + Expert + RAG into ONE entity graph; Research becomes the hub, Map/Oracle become
  full-screen views over one entity model; 3 cross-jumping journeys; 5 annotated wireframes on the 4-region
  shell; component inventory; grounded in real corpus counts + honest empty-states) and
  `UI-UX Designer/research_screenflow_prototype.html` (self-contained interactive prototype, 5 scenes —
  Workspace / Oracle answer / Molecule / Paper / Expert — linked by color-coded clickable entity chips +
  breadcrumb; teal v8 tokens + 4-region shell; representative hardcoded data). Both are review candidates in
  `UI-UX Designer/`. Spec flags one gap: molecule API endpoints (`/api/molecules…`) don't exist yet — data-eng follow-up.

## In flight
- **Grounded retrieval + relevance verification (2026-07-08, parallel team run — Data Engineer +
  Algorithm Expert + Advisory):** Closing the Oracle's ungrounded-answer gap — `POST /api/ask` still
  hard-codes an empty sources list and streams a raw Claude answer with **zero corpus retrieval**
  (`server/meatcode_server.py`; also flagged in the `0006` Done entry above and in
  `docs/tagging_relational_guide.md` §3). Algorithm Expert is wiring `/api/ask` to retrieve from
  `sources.search_vec` (FTS, live since migration `0001`) filtered to `relevance_llm >= 60`, per the
  four-step design in `docs/DECISION_Oracle_Answer_Engine.docx` (understand → find → rerank top few →
  write-with-citations-or-refuse). Data Engineer is verifying corpus relevance against the taxonomy bible
  (`db/taxonomy/keywords_topics.json`) and refreshing the audit-run xlsx Daniel reviews
  (`pipeline/export_audit_xlsx.py`). Advisory wrote the connecting architecture:
  `docs/DECISION_grounded_answers_and_relevance.md` (the grounding contract + the relevance gate + how they
  connect — including a flagged gap: confirmed quarantines don't yet suppress Oracle retrieval) and
  `docs/daniel_review_workflow.md` (Daniel's keep/quarantine/back-tag sign-off loop, step by step). Not yet
  landed in code as of this entry — retrieval wiring + the quarantine write-back are still open; see those
  docs' Open risks for the full list before this is demo-ready for WUR or other external reviewers.
- **v9 mockup — v8 polish on the newer canonical (2026-07-08, art-director):** `UI-UX Designer/MeatCODE_mockup_v9.html`
  = the deployed `app/meatcode_mockup.html` (Database scene + Simulate engine + Toolbench-in-Research + Oracle
  history) with the v8 polish forward-ported (teal avatar, SVG bell, 4-audience personas, dashboard
  accents/stat-strip fronting all 5 domains, teal globe/bubbles). Verified (balanced markup, 5 scripts
  `node --check` OK), not browser-rendered. Review candidate — promote → `app/meatcode_mockup.html` + redeploy if approved.
- **Lean v1 mockup — 4-category funnel IA (2026-07-07, art-director):** `UI-UX Designer/meatcode_lean_v1.html`
  — a less-busy alternative collapsing the 5 domains into **Home / Oracle / Data / Map**, each a
  chooser→refine→detail funnel; single top nav (dock retired); Data consolidates papers/molecules/protocols/
  pathways; Simulate + Prediction out of primary nav. 7 scenes, verified (balanced markup, JS `node --check`
  OK), not yet browser-rendered. The rich canonical `app/meatcode_mockup.html` stays the north-star. Review
  candidate — awaiting Lior's call on Data scope + Simulate handling.
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
- **2026-07-08** — Grounding contract adopted for the Oracle: it may answer ONLY from retrieved sources
  that are both citable (`search_vec` populated) and score `relevance_llm >= 60`; it must cite what it
  uses and refuse ("the corpus doesn't cover this") rather than fall back to open/training knowledge. This
  is the project's front-line mitigation for the AI-reliability/hallucination risk. The recurring audit
  loop + Daniel's xlsx sign-off is the relevance gate that keeps that contract trustworthy — an
  ungoverned corpus would just mean confidently-cited garbage. See
  `docs/DECISION_grounded_answers_and_relevance.md` + `docs/daniel_review_workflow.md`.
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
- **Oracle recall / grounding — the live fix in progress:** `POST /api/ask` currently retrieves nothing at
  all (empty sources list, raw Claude answer — see the in-flight item above); the old
  `reaktzia-mvp/retrieval.py` this bullet used to point at was deleted 2026-07-05. The fix being wired now
  uses `sources.search_vec` FTS + `relevance_llm >= 60`, with a tag-based fallback planned for the
  documented `websearch_to_tsquery` 0-result problem (ANDs every term, so natural-language questions often
  match nothing). See `docs/DECISION_grounded_answers_and_relevance.md` and
  `docs/tagging_relational_guide.md` §3.
- **Neon auto-sleep** will bite concurrent multi-agent access; keep warm or front with `meatcode_server.py`.
- `__pycache__/` + `.DS_Store` copied into `server/reaktzia-mvp/` are permission-locked; `.gitignore`
  excludes them so they won't be committed.
