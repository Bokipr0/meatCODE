# MeatCODE — Agent Update Log

_Last updated: 2026-07-05 ~21:20 UTC · Project Coordinator + Advisory · weekly sync + doc-consistency fix_

> **Every agent appends an entry here at the end of any working session — newest at the top.**
> This is the detailed audit trail of who changed what, when, and why. The short in-file
> "Last updated" stamp is the quick marker; this log is the full story. Use UTC (`date -u`).
> `PROJECT_STATE.md` = current state; this file = the running history. Don't delete past entries.

## Entry template (copy this)
```
## YYYY-MM-DD HH:MM UTC · <agent / session label> · <short area>
- What:    <what changed, concretely>
- Files:   <paths touched>
- Why:     <reason / which task or request>
- Result:  <outcome, what works now>
- Next:    <follow-ups left open, if any>
```

---

## 2026-07-05 ~21:35 UTC · Project Coordinator · PARALLEL team run — corpus white-space analysis (consolidated)
Data Engineer (empirical) + Advisory (strategic) ran simultaneously on disjoint files against the shared objective, then reported back for the coordinator to consolidate and reconcile.

### Data Engineer · corpus coverage — `analysis/white_space_analysis.py` + `analysis/white_space_data.md`
- What:   Per-topic & per-branch tagged-source counts + high-relevance (`relevance_llm≥60`) shares, tagged-vs-untagged split, thin-layer counts (claims, molecule categories). Re-runnable, SELECT-only.
- Result: 818 sources but only **329 (40%) tagged** in `source_topics` (489 untagged legacy). Branch coverage: analytics 134 (54% high-rel, best); meat_analogs 43 (14%, thinnest). **5 HIGH-priority topics with ZERO tagged sources**: PINN, LMMA/TVP, Precision fermentation, Pre-rigor biochemistry, Cooking. claims=45; molecules 799 but 784 uncategorized.
- Next:   Back-tag the 489 legacy sources before treating any "0" as a confirmed gap; categorize molecules.

### Advisory · white-space map — `docs/white_space_map.md`
- What:   First strategic white-space map (grouped by branch/theme) + ranked 10 highest-leverage research questions + 3 WUR-GC-MS quick-wins; every gap framed as an unvalidated hypothesis (trust-first).
- Result: Top leverage — thiamine/sulfur precursor engineering in plant bases; Maillard×lipid cross-talk in plant matrices; mechanism-first precursor/peptide design; a_w effects on 2-acetyl-1-pyrroline/furanthiols in HMMA; bitter-blocker×aroma-masking synergy; process-formed vs pre-added flavor robustness; heme-analogue degradation; matrix→aroma-release kinetics.
- Next:   Re-rank once DE numbers fold in; Daniel sign-off; consider quick-win #3 (targeted synthesis over the existing 818) first.

### Coordinator reconciliation
- **The two halves agree:** Advisory's analog/plant-chemistry questions map directly onto the DE's empirical finding that `meat_analogs` is the thinnest, weakest-quality branch and that analog topics (precision fermentation, LMMA/TVP) have zero tagged coverage.
- **Shared caveat:** only 40% of sources are tagged, so empirical "gaps" are PROVISIONAL until the 489 legacy sources are back-tagged — that back-tag is the #1 prerequisite before this map is treated as authoritative. The thin 45-claims layer also means some "gaps" may be an extraction-pipeline gap, not a true literature gap.

## 2026-07-05 ~21:20 UTC · Project Coordinator + Advisory · weekly sync + doc-consistency fix
- What:    (Advisory) Corrected a stale line in PROJECT_STATE.md that still claimed "two Oracle backends coexist (reaktzia-mvp/ + meatcode_server.py)" — reaktzia-mvp/ was deleted 2026-07-05, so it's now documented as the single `server/meatcode_server.py` backend. (Coordinator) Read the full week of AGENT_UPDATE_LOG + PROJECT_STATE, wrote a management status note for Daniel, and prepared an Asana reconciliation proposal (not yet applied — awaiting Lior's OK before mutating the board).
- Files:   `PROJECT_STATE.md` (backend line + last-updated stamp), `docs/2026-07-05_status_for_daniel.md` (new), this log.
- Why:     Lior dispatched (via the Agent Command Center) a weekly-sync order: summarize what each agent did, reconcile Asana with reality, draft a Daniel note; Advisory to keep infra/docs consistent.
- Result:  Daniel-ready status note saved; PROJECT_STATE now matches the single-backend reality. Week's throughput captured: corpus 496→818 + scoring + FTS (Data Engineer); live/filterable expert map + per-expert actions (Data Engineer + UI Designer); backend consolidation + template refold + conn-leak fix; v8 polish + 4 new screens (UI Designer); Oracle hybrid-RAG decision (Algorithm Expert); infra/three-homes + define docs (Advisory).
- Next:    Lior to confirm the Asana reconciliation (below) so the Coordinator can apply it; Daniel sign-off on tagging taxonomy v0.1 + hub architecture v0.1 + Oracle build; push via sync_meatcode.command.
- Asana reconciliation proposed (repo shows delivered, Asana still open): "Choose tool stack for knowledge hub infrastructure", "Define hub architecture (sitemap, schema, journeys, UI concept)", "Define tagging taxonomy v0.1", "Define literature search scope and create search strings" → mark complete. Phase-1 build milestones (Literature DB v1, Molecular DB alpha, Expert map v1) remain legitimately in-progress (e.g. corpus 818/1,000+), so leave open.

- What:    Per Lior ("remove the agents that are on my server", confirmed full-feature removal), stripped the entire agent-team dashboard from the backend. Deleted `server/agents.py` and `app/agent_dashboard.html`; removed from `server/meatcode_server.py` the `import agents`, the `/agents` pretty-URL route, all GET routes (`/api/agents`, `/api/team/run[s]`, `/api/updates`) and POST routes (`/api/agents`, `/api/team/run`, `/api/team/broadcast`), and the `/agents` startup-banner line; reverted `run_oracle.command` to open only the mockup; cleared the gitignored runtime state (`data/agents_roster.json`, `data/agent_runs.json`).
- Files:   deleted `server/agents.py`, `app/agent_dashboard.html`; edited `server/meatcode_server.py`, `run_oracle.command`; cleaned `data/`.
- Why:     Lior wants the agent system off his server; he keeps the standalone Claude-Artifact build (`app/agent_team_artifact.html`, published) separately.
- Result:  Server booted (dummy key) and verified: KEPT — `/api/health` ok, `/templates/` serves, `/api/experts` returns live Neon (Thomas Hofmann); GONE — `/api/agents`, POST `/api/team/run`, and `/agents` all 404. Kept `ThreadingHTTPServer` + the `pg_rows` connection-leak fix (general improvements, not agent-specific — flagged for Lior in case he wants those reverted too). The Data Engineer's `/api/experts` filters + `/api/expert-facets` are untouched.
- Next:    None required. If Lior later wants live agents in a pinned/always-on form, that needs the backend hosted (Render/Railway) — the standalone artifact can't do it (sandboxed).

## 2026-07-05 ~20:25 UTC · Project Coordinator · PARALLEL team run — expert-map filter buttons (consolidated)
Two specialists ran simultaneously on one objective (new, clickable expert-map buttons wired to Neon via `meatcode_server.py`), each owning a disjoint file against a fixed API contract, then reported back for the coordinator to log.

### Data Engineer · expert API filters — `server/meatcode_server.py`
- What:   Extended `GET /api/experts` with optional `q` (name/affiliation ILIKE substring), `country` (case-insensitive exact), `sort` (`relevance` default | `h_index` | `papers`; unknown→relevance), `min_relevance` (float), `limit` (default 200, clamp 1..500) — all parameterized SQL, base `relevance_score IS NOT NULL` kept. Added `GET /api/expert-facets` → `{countries:[{country,count}], total}` for the UI's country buttons.
- Why:    Back the new UI filter controls with a matching contract, built in parallel with the front-end.
- Result: `py_compile` clean; verified live vs Neon — `q=schieberle`→Schieberle; `country=Germany&sort=h_index`→Hofmann(68)/Schieberle(63)/Selke(33); `min_relevance=0.9`→only ≥0.9; facets sum to the 374 curated experts. All existing endpoints + 503-fallback unchanged.
- Next:   `experts.country` is inconsistently coded (ISO vs full name, "US" vs "USA") → facet buttons fragment; needs a normalization pass.

### UI/UX Designer · expert-map filter controls — `app/meatcode_mockup.html`
- What:   New `#mcFilterBar` in the Map scene: search input (300ms debounce → `q`), country `<select>` (top-8 from `/api/expert-facets` → `country`), sort buttons Relevance/H-index/Papers (→ `sort`), "Top-rated only" toggle (→ `min_relevance=0.9`), Reset, live result count + loading/empty/error states. On change → refetch `/api/experts`, reuse the existing loader's mapping via a new `window.mcApplyExperts` export (no duplicated logic), re-render list+globe (each call guarded); never blanks on empty/error.
- Why:    Wire the static expert map to the live, filterable endpoints per the shared contract.
- Result: all inline `<script>` blocks pass `node --check`; fetch URLs/params grep-match the contract; file serves over HTTP (200). Live in-browser click-test not possible in the sandbox.
- Next:   Browser click-test with the server running; optional URL-hash filter state for shareable views.

## 2026-07-05 ~20:10 UTC · agent-dashboard session · STANDALONE Claude-Artifact build (the deliverable Lior asked for)
- What:    Recalibrated after feedback: Lior wanted a STANDALONE single-file HTML he can connect to Claude as an Artifact — not a server-wired page. Built `app/agent_team_artifact.html`: one self-contained file (inline CSS/JS, no external requests, CSP-safe) with the full platform — pick/edit/add agents, select multiple, one goal, one-click **parallel** run, per-agent progress cards, Project Coordinator broadcast, recent-runs history, and a Team-activity feed. Agents run for real via the Claude Artifact runtime API `window.claude.complete()`; opened outside an artifact it auto-detects and falls back to **Demo mode** (clearly-labelled simulated output) so the UI is fully explorable. State persists in `localStorage` (no server/data files).
- Files:   `app/agent_team_artifact.html` (new — the standalone artifact). The earlier server-wired `app/agent_dashboard.html` + `server/agents.py` stay as the on-prem variant.
- Why:     Lior: "create a standalone html that I can connect to claude artifact" with the agent-team features.
- Result:  Rendered + driven live in a headless browser (Demo mode): layout clean/on-brand, banner correctly explains demo vs live, selecting Data Engineer + UI Designer + the expert-map goal → both ran in parallel to `done`, Coordinator broadcast rendered and posted to the activity feed, run button re-enabled. To go live: paste the file into a Claude.ai conversation as an Artifact (where `window.claude.complete` exists) — no server needed.
- Next:    Optional: swap the localStorage activity log to sync with the real AGENT_UPDATE_LOG when run on-prem; add a per-deliverable copy/export; a "sync round" so workers see each other's drafts before the coordinator.

## 2026-07-05 ~19:40 UTC · agent-dashboard session · agent-team management platform (server-wired variant)
- What:    Built Lior an agent-team control panel on top of `meatcode_server.py`. Pick a set of role-scoped agents (Data Engineer / UI-UX Designer / Project Coordinator / Oracle Researcher — editable + extendable), hand them ONE goal, hit Run: each agent runs **simultaneously** (one background thread each) as a Claude call with its own mandate + live PROJECT_STATE context, aware of its teammates so deliverables fit together. Progress streams into per-agent cards; a Project Coordinator pass then synthesises the run and appends a real entry to this very log ("broadcast to the team"). Recent-runs history + an activity feed (parsed from AGENT_UPDATE_LOG) round it out. Switched the server to ThreadingHTTPServer so parallel runs + polling don't block the Oracle stream.
- Files:   `server/agents.py` (new — roster, threaded orchestration, JSON persistence in gitignored `data/`, coordinator broadcast, log parser); `server/meatcode_server.py` (new routes: GET `/api/agents`,`/api/team/run[s]`,`/api/updates`; POST `/api/agents`,`/api/team/run`,`/api/team/broadcast`; `/agents` pretty URL; ThreadingHTTPServer); `app/agent_dashboard.html` (new — minimalist on-brand control panel); `run_oracle.command` (also opens `/agents`).
- Why:     Lior wants one easy management platform to choose agents, dispatch multiple workers on a shared problem in one click, watch their progress on the big goals, and have a coordinator spread the latest updates to the team.
- Result:  Smoke-tested end-to-end with a DUMMY key (no spend, no real log entry): roster seeds, `/agents` serves, POST run spawns parallel threads, both agents dispatched + statuses captured (401 → error path), run finalized to `done`, history + `data/` persistence + updates feed all correct (feed now skips the template heading). The success path (real Claude output + real coordinator log append) is the product itself — runs on Lior's real key from the dashboard. v1 boundary: agents produce **text deliverables/plans**, they do NOT auto-edit the repo/DB yet.
- Next:    (1) Optional "Apply" action per deliverable to actually land an agent's SQL/HTML (the deliberate opt-in beyond v1's read-only safety boundary). (2) Optional "sync round" where workers see each other's first outputs before the coordinator. (3) Consider bumping the Oracle/agent model Sonnet 4.6 → Sonnet 5.

## 2026-07-05 ~19:00 UTC · deploy-templates session · template layer refolded onto the sole backend
- What:    After `reaktzia-mvp/` was deleted (it held the template static-mount + listing added earlier that day), rebuilt that functionality onto `server/meatcode_server.py` — the stdlib `http.server` that `run_oracle.command` launches. Added `GET /api/templates` (lists `app/templates/*.html`), `GET /api/papers/recent[?limit]` (Neon), a `/templates/…` pretty-URL rewrite → `app/templates/…` (bare `/templates/` serves the gallery), and enriched `GET /api/health` to the `{ok, db_ok, has_anthropic_key, model}` shape `meatcode-api.js` reads. Fixed a real connection leak in `pg_rows` (psycopg2 `with connect()` commits but never closes → leaks one Neon connection per request; now `try/finally conn.close()`). Repointed the template folder's docs/status strings from the deleted `reaktzia-mvp` to `meatcode_server.py` / `run_oracle.command`.
- Files:   `server/meatcode_server.py`; `app/templates/README.md`, `index.html`, `meatcode-api.js` (stamps + reaktzia→meatcode_server refs).
- Why:     Lior deleted `reaktzia-mvp/` and asked to make the template-serving work through `meatcode_server.py` under `run_oracle.command`.
- Result:  Booted the server (dummy key) and smoke-tested live: `/api/health` returns the connector shape; `/api/templates` lists both reference templates; `/api/papers/recent` returned **real Neon papers** (DB is wired via repo `.env`); `/templates/`, `/templates/meatcode-api.js`, and `/templates/example-oracle.html` all serve. `/api/ask` streaming path is unchanged from the working mockup wiring (not re-tested — needs a real key). Templates now gain live Claude+Neon access with `<script src="meatcode-api.js"></script>` + `data-mc-*`, gallery at `http://localhost:8000/templates/`.
- Next:    Optional: the earlier server-improvement assessment (raise Oracle `max_tokens`, singleton Anthropic client, `/api/ask` `k`-clamp, prompt caching, model bump Sonnet 4.6→Sonnet 5) still stands; none are required for the templates to work.

---

## 2026-07-05 ~18:10 UTC · data-eng / advisory session · corpus scoring + live expert map + server consolidation
- What:    (1) Applied FTS migration 0001 — `sources.search_vec` now 496/496 citable + trigger. (2) Expanded corpus 496→818 via a multi-source ingester (Europe PMC default; OpenAlex full-text search was returning 503) driven by the taxonomy bible, deduped + tagged to `source_topics`. (3) Made the taxonomy the governing bible: `db/taxonomy.py` loader + `pipeline/sync_taxonomy.py` (topics synced). (4) Quality/priority scoring: migration 0002 added `priority_score`/`is_review`/`relevance_llm`; `score_priority.py` (composite + dedupe -10 rows) and `score_relevance.py` (LLM/Haiku gate — all 818 scored, 202 flagged <40 off-topic). (5) Expert map now live-data-backed: `meatcode_server.py` serves Neon-backed `GET /api/experts`, `/api/experts/{id}`, `/api/papers/{id}` (+ `/api/health`); mockup fetches real curated experts into globe/list/detail with demo fallback.
- Files:   db/migrations/0001_*,0002_*; db/connect.py, db/taxonomy.py, db/taxonomy/keywords_topics.json, docs/DATA_DICTIONARY.md; pipeline/openalex_ingest.py, sync_taxonomy.py, score_priority.py, score_relevance.py; server/meatcode_server.py; app/meatcode_mockup.html; run_oracle.command; CLAUDE.md; PROJECT_STATE.md
- Why:     Lior: connect Neon to server+agents, expand DB by taxonomy, verify/prioritize paper quality, and make the expert map interactive with real Neon experts off meatcode_server.
- Result:  All verified live over HTTP against Neon. `reaktzia-mvp/` deleted → `server/meatcode_server.py` is the sole backend; `run_oracle.command` launches it and opens the mockup with a working live expert map + Oracle. Corpus: 818 sources (all citable); experts 3,129 (374 curated surfaced on the map).
- Next:    Foundational older-reviews pass (corpus is recency-skewed); optionally quarantine the 202 low-relevance papers; normalize `experts.country` (ISO↔name) for better globe placement; deeper ingest toward 1,000–2,000.

---

## 2026-07-05 ~13:30 UTC · Claude Design session · New screen handoff (Home / Map / Oracle / Research)
- What:    Produced 4 high-fidelity screen designs against the MeatCODE Design System (Claude
           Design, outside the mounted sandbox) — Home (workspace dashboard), Community Map,
           Food Oracle (ask/empty state only), Research phase picker. Packaged as a dev handoff
           with screenshots, annotated source, and exact design-token values.
- Files:   `UI-UX Designer/design_handoffs/2026-07-05_home-map-oracle-research/` (new — README.md,
           screenshots/, source/). Filed into the repo + logged by the deploy-templates session
           (2026-07-05) — the handoff was prepared outside git write access.
- Why:     Lior's request to hand deployed/designed screens to the agent team for implementation.
           These four screens are the "templates I created in Claude Design" that the deploy-templates
           session built the serving infrastructure for (`app/templates/` + `meatcode-api.js`).
- Result:  Bundle ready to build from — README is self-sufficient (layout, colors, type, tokens,
           per-screen component notes, explicitly flagged gaps).
- Next:    (1) Decide the build target — deploy as server-served HTML wired to the live Claude+Neon
           backend via `meatcode-api.js` (matches Lior's stated goal), or recreate as React in the
           planned Next.js frontend (handoff author's assumption). (2) Oracle's answered/loading
           states are designed in the source file (typing dots, streamed answer + CiteChips, paper
           modal) but only the empty/ask state was screenshotted. (3) Map's ranked list showed two
           variants (plain "MATCH" vs. numeric score) — the numeric-score version is in the source.

## 2026-07-05 13:30 UTC · deploy-templates session · Claude Design templates → live server
- What:    Made Claude Design templates deployable so their elements talk to Claude + Neon through the same FastAPI server the canonical mockup uses. Added a static mount + listing endpoint to the server, a shared drop-in connector script, a self-populating gallery, a README, and two reference templates.
- Files:   `server/reaktzia-mvp/server.py` (added `StaticFiles` import, `/api/templates` listing endpoint, `/templates` static mount of `app/templates/`, updated root + docstring), `app/templates/meatcode-api.js` (new — SSE `ask()` mirroring the mockup's proven parser, plus `health`/`paper`/`recentPapers` and zero-JS `data-mc-*` auto-wiring), `app/templates/index.html` (new — gallery that self-populates from `/api/templates`), `app/templates/README.md` (new — 3-step deploy + wiring docs), `app/templates/example-oracle.html` + `oracle-demo.html` (reference templates).
- Why:     Lior asked to deploy all templates built in Claude Design so their elements interact with his Claude/MCP the same way the HTML mockup does.
- Result:  Any exported Claude Design `.html` dropped into `app/templates/` is served at `http://127.0.0.1:8000/templates/`, appears in the gallery automatically, and gains live Claude+DB access by including `<script src="meatcode-api.js"></script>` and either `data-mc-*` attributes or the `MeatCODE.*` JS API. Verified: server.py parses; template path-resolution + listing logic confirmed against the real folder (index.html correctly excluded). Full uvicorn boot not run in-sandbox (fastapi/psycopg2/anthropic not installed here) — runs via `run_server.command` on the Mac as usual.
- Next:    Getting the actual Claude Design projects into the repo needs a manual export (DesignSync needs an interactive claude.ai login not available in cowork) — export each template's HTML and drop it in `app/templates/`, or use Design's "Send to Claude Code Web". Templates that need endpoints beyond ask/papers will need new `/api/*` routes.

---

## 2026-07-01 11:18 UTC · art-director session · UI/UX v8 polish + dashboard upgrade + repo consolidation
- What:    Art-direction pass on the product mockup, in two rounds, plus consolidating design work into the repo and fixing the parent-folder routing that causes agent drift.
- Files:   `UI-UX Designer/MeatCODE_mockup_v8_UIUX-polish.html` (new candidate, moved in from a loose out-of-repo folder), `UI-UX Designer/DESIGN_NOTES_v8.md` (new), parent `Claude Database/CLAUDE.md` (added redirect banner → `meatCODE/`), `PROJECT_STATE.md` (v8 entry + decision), this log.
- Why:     Lior asked Claude to act as standing art director — improve visuals + screen flow; then "keep working it" (round 1 read as too subtle); then centralize everything under meatCODE.
- Result:  Round 1 — avatar wine→teal (all scenes), research bubbles + globe recolored to teal/coral/olive, emoji bell→SVG icon, onboarding personas realigned to the 4 real audiences, dashboard now fronts all 5 domains, Simulate marked "Preview", molecular names monospaced. Round 2 (dashboard) — per-domain color accents (left border + tinted icon chip), hover-lift cards, hero eyebrow + 4-metric stat strip, accented "For you" cards. Markup verified balanced (11/11 sections, 1065/1065 divs). v8 base was byte-identical to canonical `app/meatcode_mockup.html`, so it's a clean superset.
- Next:    Lior reopen/refresh the file; then choose: (a) promote v8 → `app/meatcode_mockup.html`, (b) carry the richer treatment into Oracle/Map/Research/Toolbench, or (c) the deferred structural round (nav dedup, cross-domain links, second typeface). Reconnect Claude-in-Chrome so future passes are screenshot-verified. Push via `sync_meatcode.command`.

## 2026-06-30 13:05 UTC · advisory session · Decision doc → Word (.docx)
- What:    Generated a polished Word version of the Oracle answer-engine decision doc (wine-accent headings, footer, US-Letter). Validated OK (50 paragraphs).
- Files:   `docs/DECISION_Oracle_Answer_Engine.docx` (new; mirrors the .md).
- Why:     Lior asked for a docx for sharing/review (Daniel-friendly).
- Result:  Shareable Word doc alongside the markdown source.
- Next:    Same as decision doc — review, then build the pipeline + golden eval set.

## 2026-06-30 12:55 UTC · advisory session · Oracle answer-engine decision doc
- What:    Reviewed Lior's proposed "tag-summoned expert agents + consensus vote" retrieval design; consulted the Algorithm Expert sub-agent (independent, same conclusion). Wrote a plain-English decision doc.
- Files:   `docs/DECISION_Oracle_Answer_Engine.md` (new).
- Why:     Lior asked for a subjective expert view + a non-expert-friendly write-up.
- Result:  Recommendation: keep the goal, drop the agent-swarm. Build single-pass tag-aware hybrid RAG (understand→retrieve[pgvector+full-text+soft tags]→rerank→grounded answer with persona + citations). Reserve multi-agent for rare multi-field questions, done as sequential decomposition, later.
- Next:    Lior/Daniel review; if agreed → embed citable sources into pgvector + build the 4-step pipeline + a 30–50 Q golden eval set this month.

## 2026-06-30 12:45 UTC · advisory session · Repo cleanup
- What:    Deleted junk + one exact duplicate from `meatCODE/`.
- Files:   Removed 6 `.DS_Store`, `server/__pycache__/` + `server/reaktzia-mvp/__pycache__/` (.pyc), and the duplicate `docs/MeatCODE for WUR.pdf` (kept the canonical `docs/decks/` copy).
- Why:     Lior asked to clean irrelevant files.
- Result:  Folder decluttered; no source/content/schema touched. (Note: sandbox can't delete on the mount — used the Cowork delete-permission flow.)
- Next:    Optional cleanup pending Lior's call — `pipeline/migrate_airtable.py` (one-time, already run) and `app/assets/MeatCODE_Atlas_ChordDiagram_v7_GFI.svg` (verify the mockup still uses it).

## 2026-06-30 12:23 UTC · advisory session · Update tracking (stamps + log)
- What:    Added the file-update conventions; created this log; created `meatCODE/.env` (empty key fields ready to fill).
- Files:   `CLAUDE.md` (new "File-update conventions" section + end-of-session steps), `AGENT_UPDATE_LOG.md` (new), `.env` (new, gitignored).
- Why:     Lior's request — every agent should stamp files it edits with a last-updated note, and keep a detailed shared update log.
- Result:  Convention is documented for all agents; `.env` is in place awaiting Lior's `ANTHROPIC_API_KEY`.
- Next:    Lior pastes his Anthropic key into `.env`, then runs `run_oracle.command`.

## 2026-06-30 ~12:00 UTC · advisory session · Oracle wiring + MVP design docs
- What:    Made the thin Oracle server demo-ready and drafted the two Phase-0 "define" docs.
- Files:   `server/meatcode_server.py` (serve repo root so `app/meatcode_mockup.html` loads; model → `claude-sonnet-4-6`; load `.env` from repo root), `run_oracle.command` (new double-click launcher), `docs/TAGGING_TAXONOMY_v0.1.md` (new), `docs/HUB_ARCHITECTURE_v0.1.md` (new), `PROJECT_STATE.md` (Oracle + docs status).
- Why:     Lior's "Oracle answering by tomorrow" + define tagging taxonomy v0.1 + hub architecture.
- Result:  Server compiles + SSE contract matches the mockup; taxonomy (7 faceted axes on existing schema) and tight-MVP architecture (Oracle/Literature/Expert/Molecular) drafted.
- Next:    Lior's key → live test; his topics `.md` to lock the Topic axis; Daniel sign-off on both docs.

## 2026-06-30 (approx, earlier) · setup + art-director sessions · Repo established
- What:    Built the single-source-of-truth repo and core conventions (summary of prior sessions).
- Files:   `CLAUDE.md`, `PROJECT_STATE.md`, `README.md`, `.gitignore`, `.env.example`; migrated code/docs/mockup/SQL/pipeline into the tree; added `db/connect.py`, `docs/DATA_DICTIONARY.md`, `db/migrations/`; `UI-UX Designer/` v8 mockup candidate; `sync_meatcode.command`.
- Why:     Consolidate scattered copies into one mounted repo all agents share; back it with GitHub `Bokipr0/meatCODE`.
- Result:  `meatCODE/` is the canonical working location; three-homes model (Git / Neon / Asana) adopted.
- Next:    First GitHub push from Lior's Mac; copy two iCloud-only files in; verify citable-corpus size in Neon.
