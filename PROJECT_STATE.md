# PROJECT_STATE — MeatCODE

> Living technical status. **Every agent reads this after CLAUDE.md and updates it before pushing.**
> Asana owns *tasks & priorities*; this file owns *technical reality* — what's built, what's broken,
> what's in flight. Keep it short and current, not a changelog.

_Last updated: 2026-08-31 (pm) · Project Coordinator — Demo-prep run: `#analytics` is now a GC-MS/NMR measurements browser; `#simulate` "Predict outcomes" is LIVE → `/api/simulate` (mock, synthetic-labelled); adapter accepts mM; 10-min run-of-show shipped. Awaiting deploy-dev. See AGENT_UPDATE_LOG.md._

## Demo-prep — GC-MS/NMR measurements browser + Pablo's simulator LIVE (mock) — shipped to the repo 2026-08-31 (awaiting deploy-dev)
3-lane parallel build for the demo (UI/UX → mockup · Full-Stack → maillard/adapter · Advisory → docs). Disjoint from the same-day dev-zone **Analytics workspace** (`app/dev/analytics_workspace.html`, board A3, upload→compare) — this run is the in-product surfaces.
- **Mockup** (`app/meatcode_mockup.html`): the `#analytics` scene is now a **measurements browser** — GC-MS + NMR cards open a detail view with an inline-SVG placeholder spectrum (GC-MS chromatogram / NMR ¹H, loudly "illustrative"), an honest "what it measures/detects" block, and the method's live `/api/corpus` slice; planned methods get an honest "no reference spectrum yet". The **`#simulate` scene is now live**: "Predict outcomes" (`#simPredictBtn`) POSTs `/api/simulate` (mock) and renders ranked synthetic compounds + off-notes + the mandatory **SYNTHETIC** banner + disclaimer (editable precursors/conditions; 200/202-poll/404/error handled). 10/10 inline `node --check`.
- **Simulator backend** (`server/maillard/adapter.py`): accepts `mM`/`mmol/L` units (the form's units — was 400ing every submit) and the mock is now demo-worthy (precursor-aware, meaty-forward ranking for Cys×Ribose; deterministic; 100% synthetic-labelled). `CONTRACT.md` §2 synced. Verified over HTTP (health=mock; flag-off→404; mM accepted). `server/meatcode_server.py` unchanged (validation delegates to the adapter).
- **Docs**: `docs/meatcode_demo_runofshow_2026-08-31.md` — a balanced 10-min live run-of-show (Oracle → Research/corpus → GC-MS/NMR → Simulator → Compare) with click-paths, timing, honest framing, fallbacks, and a **deploy-first pre-demo checklist**.
- **Demo gate:** `/api/corpus`, `/api/compare`, `/api/simulate` are 404 on prod — run the demo on **deploy-dev staging** or **run-local localhost**, `maillard_sim` ON, Neon awake. **NOT deployed.**

## Oracle capability demos + live corpus filter + first-class Analytics scene — shipped to the repo 2026-08-16 (awaiting deploy-dev)
4-lane parallel run (UI/UX → mockup · Full-Stack → server · Data → db/ chip-map · Advisory → docs/). Disjoint files, zero collisions; the API contract held with zero slug corrections.
- **Server** (`server/meatcode_server.py`): NEW `GET /api/corpus?phase=<juice|lipid|analytics>&topics=<slugs>` (per-slug + `phase_topics` live counts, deduped `totals{papers,molecules}`, ≤50 rows; module-level `CORPUS_PHASES` slug sets; `phase_topics` labels read from the taxonomy bible) · NEW `POST /api/compare` (1–2 molecules → side-by-side `fields[].differs`; corpus misses return `in_corpus:false`, no invented chemistry) · NEW `GET /api/molecule-profile/{id}` (thin alias of `/api/molecules/{id}` via a shared `_molecule_detail()`). SELECT-only, auth-gated, `py_compile` clean, route-shadow verified. **⚠ corpus counts currently UNGATED** — Data recommends the Oracle's `relevance_llm≥60` gate so Research and the Oracle count the same corpus (open decision).
- **Mockup** (`app/meatcode_mockup.html`): `#research-sub` juice/lipid sub-cards are now a real toggle multi-select carrying `data-topics`, debounce-querying `/api/corpus` to re-render the live count + per-card counts (0-count greyed); Analytics promoted to a first-class **`#analytics` scene** (6 live-corpus method chips) reachable from the Research tile (the `dev/analytics.html` link is dropped); the four Oracle starters became capability demos (Maillard route schematic + grounded `/api/ask` · Explore the lipid corpus · Predict with the simulator [MOCK — synthetic banner required] · Compare molecules inline — never navigates away); `#ffDevBanner` removed. 10/10 inline scripts pass `node --check`, tags balanced.
- **Data** (`db/research_chip_map.json` + `db/CORPUS_FILTER_NOTES.md`): 24 chips → 40 real taxonomy slugs, all validated against `keywords_topics.json` (0 corrections); 9 thin chips flagged for grey-out; `/api/corpus` SQL specced. Note: no taxonomy slug finer than `lipid_oxidation_topic` for lactones/cholesterol-oxidation/rancidity/methyl-ketones.
- **Docs** (`docs/oracle_demos_and_corpus_filter_2026-08-16.md`, Advisory): contract summary + 5 honesty rules (mock simulator banner, 0-count grey-out, preview Analytics, illustrative schematic, keep the prod/staging distinction) + reviewer-facing framing + test paths. **B1/B2 remain the critical path — this run does not reorder the spine.**
- **NOT deployed.** `deploy-dev.command` → verify staging → `promote-to-prod.command`. (`server/maillard/adapter.py` is in the repo but wasn't staged in-sandbox; the mock simulate path is intact — verify live at deploy.)

## Lior review follow-ups — 2026-08-15 evening (awaiting deploy-dev)
- **Neon DEV branch synced with prod enrichment** (migration 0009 + values copied by id: CAS 110 · CIDs 20 · junk 1 · abstracts 30 · source_topics 569). Root cause of "CAS missing": enrichment had only reached the production branch; Lior was viewing dev. `.env.dev` now points local runs at the dev branch.
- **Oracle v10 static redesign** — `app/dev/oracle_redesign.html`: the approved wireframe Oracle look + v9 history rail, fully clickable (chips/citations/entities/rail all forward), honestly labelled static.
- **Dev zone gained Versions + Compare** — `app/dev/versions.html` (prod snapshot list + "re-migrate to this version"; live rollback only on the local cockpit, read-only banner on hosted dev) and `app/dev/compare.html` (Flow-2 side-by-side port). Server: `GET /api/release/history` now readable when `APP_ENV=dev` (prod 404; writes stay local-admin; git-less hosts degrade gracefully).

## 5-agent run — Lior's task list — shipped to the repo 2026-08-15 (awaiting deploy-dev)
- **Mockup** (`app/meatcode_mockup.html`): Oracle **attach button (client-side preview**, honest tooltip, no fake upload) · **Dev Area button** on all 14 topbars gated behind **`ff-dev_area`** (flag added to `Release Center/features.json`, ON dev / OFF prod) · **Home removed from nav — Oracle is the landing again** (#home kept in-file, unreachable) · **Research = Juice · Lipid · Analytics** tiles with same-hue darkening hover (Matrix/Volatiles tiles removed, scenes intact).
- **Dev Area** (`app/dev/`, new, static): hub (Features = live flags read-only · Screens · Documents · the 6 user screen flows as diagrams) + **knowledge-graph screen** (embeds `/kg/kg_explorer.html`) + **Meat Fingerprint placeholder** (canvas radar, loudly labelled demo) + **Analytics zone** (GC-MS/HPLC/Olfactory/NMR/Spectroscopy cards, honest status chips).
- **Server** (`server/meatcode_server.py`): `/api/ask` emits additive **`event: consensus`** (agree/oppose/neutral per retrieved source, guarded — failure can never break the stream) · retrieved sources now carry their **`claims`** records · new auth-gated `GET /api/consensus-demo?q=`. Backward-compatible; py_compile + live SSE smoke test clean.
- **Data (Neon, migration 0009 applied):** molecules += 7 columns (canonical-ID + chemistry scaffolding + `is_junk`); **CAS 0→110** (MVL backfill), **PubChem CIDs 20-pilot** (network open — scale next), `Decline` flagged junk; `sources.tailored_abstract` **0→30**; topic backfill **untagged 489→252** (+240 source_topics). Nothing fabricated; 4 chemistry fields left NULL awaiting a curation source. Paper ingestion **blocked** (no Dimensions creds/ingester).
- **RAG eval baseline** (`analysis/rag_eval/`): 8 questions, closed-corpus, verifier-scored — **groundedness 3.4 · citation-accuracy 4.8 · coverage 4.1 (/10)**; zero invented citation ids; all questions needed the OR-fallback; thiamine degradation = confirmed corpus hole. This is the pre-improvement baseline on record.
- **Docs/board:** `platform_docs/DEV_AREA.md` + `platform_docs/KG_DECISION.md` (new) · MVP_BOARD refreshed (A1/A4/A5 🟡, new A6/A7; **B1 deploy + B2 quarantine write-back remain the critical path**).
- **NOT deployed.** Lior: `deploy-dev.command` → check staging (flip ff-dev_area if needed) → `promote-to-prod.command`.

## 🎯 MVP alignment — north star through mid-September (set 2026-07-22)
Lior's **MVP Definition & 5 User Journeys** (`docs/MeatCODE_MVP_Definition_and_User_Journeys.md`) is now the bar: a credible source-backed prototype, **internal demo end of August**, **external P1 expert validation mid-September**. All 5 lanes assessed their status against it — full gap analysis in **`docs/MVP_ALIGNMENT.md`**, broadcast in `TEAM_BROADCAST.md`.

**Journey status (honest):** 🟢 J1 Oracle (working skeleton) · 🔴 J2 GC-MS (hollow — no data/UI/endpoint/algorithm; team rec: **preview/Phase-2**) · 🟡 J3 Literature (Database + molecule-detail; no knowledge-graph) · 🟠 J4 Research Planning (design-only, no protocols backend) · 🟢 J5 Expert Discovery (Map + filters; experts under-enriched).

**P0 spine (ordered, cross-lane):** (1) **Data** — close corpus trust: quarantine→`relevance_llm` write-back + back-tag 489 (39% gate →) + retrievability count; (2) **Algorithm** — build the benchmark harness (gold set vs GPT/Claude/Perplexity) proving criterion 1; (3) **Full-Stack** — deploy the month-long committed backlog + verify live, then scaffold GC-MS upload (preview) + `/api/protocols`; (4) **UI/UX** — lock one design system + J3 knowledge-graph + J4 planning flow + honest previews; (5) **Advisory** — P1 validation protocol + mid-Aug scope-freeze gate.

**Open decisions (Lior + Daniel):** ~~GC-MS scope (P0 vs preview)?~~ → **DECIDED 2026-07-23: preview** (honest, clearly-labelled reference data — not a live analytical engine) · greenlight the benchmark eval? · close the quarantine write-back now? · deploy the backlog (`deploy-dev` → `promote-to-prod`)?

> 📋 **Open deliverables for the 31 Aug demo now live in `MVP_BOARD.md`** (8 MVP lanes · 5 action items · 2 blocking gaps, with owners + critical path). Agents: read it after this file and update your rows as you finish.

## Screen-flow design pass — 6 cross-nav flows (wireframes + journey spec) — 2026-08-15 · design only, in `UI-UX Designer/`
Parallel UI/UX + Advisory run (Coordinator-orchestrated) on Lior's ask to wire the standalone screens into one end-to-end experience. **Design/exploration only — no live-mockup or deployed-file changes.** Advances board item **A2 (scenario & user screen-flow creation)**.
- `UI-UX Designer/screen_flows_wireframes.html` — interactive wireframe, 6 hash-routed scenes (Flow-Map · Oracle answer · Raw Data table · **Data Comparison** [net-new] · Protocol detail · Simulate), every transition clickable with a **"carry banner"** naming the context handed across. Verified (6/6 sections, 192/192 divs, inline script `node --check` clean).
- `UI-UX Designer/SCREEN_FLOWS_user_journeys.md` — journey + IA spec; unifying **"entity + context handoff bus"** (`mcHandoff()/mcConsumeHandoff()`, generalizing the existing `mc_mol_focus_id`). **Buildable-now:** Flow 3 (Data→Oracle, zero backend), Flow 1 (Oracle→Raw table), Flow 2 (Comparison, client-side over `/api/molecules/{id}`). **Preview/flag:** Flows 5/6 (Sim↔Data). **Design-only:** Flow 4 (Protocols→Data — no `/api/protocols` / protocols table).
- Recommended P0 for 31 Aug: handoff bus + Flow 3 + Flow 1; Flow 2 as a `data_compare`-flagged stretch. Review candidates — awaiting Lior's go before any port into the live mockup.

## Follow-up v12.7 — Data off top nav + Inventory Option A — shipped to the repo 2026-07-22 (awaiting deploy)
- **Data removed from the top nav** (Lior: not an upper-category button). Top nav across all topbars is now **Home · Oracle · Research · Simulate**; the load-time pass removes Database + Map chips + injects Home. The Home **Data tile** (→#database) and the `#database` scene + in-content routes are kept — Data is reachable off-nav. setScene's dynamic active state updated to match.
- **Inventory = Option A (slide-over drawer)** built into Home + wired **client-side only** (shared-password → no per-user identity, same as Lab Stash — no server store): `#invBtn` → drawer with Articles · Protocols · Sentences. **Sentences** = real Lab Stash (`window.MCStash.list()`). **Articles** = new `mc_saved_articles_v1` + a bookmark on `#molecule-detail` linked papers (`window.mcSaveArticle`). **Protocols** = new `mc_saved_protocols_v1` + a save button on `#protocol-detail`. Live counts; versioned/try-catch/dedupe/cap. Articles+Protocols start empty until saved (by design).
- Files: `app/meatcode_mockup.html` only (no backend). Verified: 7/7 `node --check`; nav + tile + Inventory + stores confirmed. **Not deployed — run `deploy.command`.**

## Follow-up v12.6 — Home landing module + detail pages + molecule endpoint — shipped to the repo 2026-07-22 (awaiting deploy)
Parallel UI/UX + Full-Stack run on Lior's Home-module request (modelled on `UI-UX Designer/meatcode_lean_v1.html`) + his annotated-screenshot follow-ups.
- **`#home` is the new landing** (loads first; logo → Home). Nav across all topbars is now **Home · Oracle · Data · Research · Simulate** (the pass drops only Map, relabels Database→"Data", prepends Home, reorders; `setScene` now sets `.domain.active` dynamically). Map + the DB detail stay reachable via in-content journeys.
- **Working ask box**: type + Enter (or Ask) → routes to `#oracle` and streams the answer there (reuses `askOracle`); plus a **mic dictation** button reusing the Oracle's Web Speech (en-US, feature-detected). Four tiles → Oracle/Data/Research/Simulate.
- **"Pick up where you left off"** = recently-used **chats · molecules · protocols** (no experts; new `mc_recent_molecules_v1` / `mc_recent_protocols_v1` tracking + seeds), each routing into a detail page.
- **New detail pages**: `#molecule-detail` (live via new **`GET /api/molecules/{id}`** → `{…,mentions_count,papers[]}`, breadcrumb + linked papers + Ask-Oracle/See-on-Map crosslinks) and `#protocol-detail` (**representative template — no protocol backend yet**).
- **Inventory**: delivered as **2 review variants** (A slide-over drawer · B inline board), NOT wired — awaiting Lior's pick, then build + connect.
- Files: `app/meatcode_mockup.html` (UI/UX) + `server/meatcode_server.py` (Full-Stack, new `/api/molecules/{id}`, list endpoint not shadowed). Verified: mockup 7/7 `node --check`; server `py_compile`; contract matches. **Not deployed — run `deploy.command`.** Open: protocol data source; repoint Related-molecule chips to `#molecule-detail`?; port to `MeatCODE_mockup_v9.html`.

## Follow-up v12.5 — nav trim + wider Oracle answer + related-molecule chips — shipped to the repo 2026-07-22 (awaiting deploy)
Parallel UI/UX + Full-Stack run (Coordinator-orchestrated) on Lior's 3 asks; frontend and backend split by file so they ran with zero overlap.
- **Database + Map removed from the top nav, screens kept.** A load-time JS pass drops the "Database"/"Map" `.domain` chips across all 11 topbars (nav → **Oracle · Research · Simulate**); the `#database`/`#map` scenes and every in-content route into them (dock, "See on Map", breadcrumbs, the new molecule chips) are intact — reachable via other journeys, just not the top bar.
- **Wider Oracle answer:** `#oracle .oracle-wrap` max-width 760→**1080px** (the answer card fills it); heading/ask-box/starters kept to a centered 780px; the no-page-scroll fixed shell (only `#oracleAnswerSlot` scrolls) preserved.
- **Related-molecule chips at the end of each answer:** new **`GET /api/molecule-suggestions?q=&limit=6&exclude=`** (`server/meatcode_server.py`, SELECT-only) ranks name-in-`q` > category(family)-in-`q` > top-by-`mentions_count` and returns a bare array `[{id,name,category,taste,mentions_count}]`; the mockup fetches it when an answer completes and renders a teal "Related molecules" chip row (loading/empty/error states, same-origin guard, no fabrication), each chip routing into `#database` molecules for that molecule.
- Files: `app/meatcode_mockup.html` (UI/UX) + `server/meatcode_server.py` (Full-Stack). Verified: mockup 6/6 inline `<script>` `node --check`; server `py_compile` clean; frontend request == backend response shape; both committed to disk. **Not deployed — run `deploy.command`** (publishes the endpoint + frontend together; the endpoint is 404 until then, and the chip row simply stays hidden). Hand-off: not yet ported into `UI-UX Designer/MeatCODE_mockup_v9.html`.

## Data audit — honest "AI Review" layer added 2026-07-22
- `pipeline/ai_review.py` (new) appends a 6th **"AI Review"** sheet to each `data/snapshots/*.xlsx`: an AI model's straightforward, fully honest opinion on the data's filtration & tagging — per-table validity / what's missing / how to tag it better, plus cross-cutting issues and ranked fixes. A deterministic profiler (fill rates, fully-empty/constant/partial columns, value distributions) grounds every number; the narrative is AI-authored. Modes: `--review-json` (inject a pre-written opinion — fast, primary path), API auto-mode (`python3 pipeline/ai_review.py FILE` — self-contained, ~60s), `--profile` (print facts only), `--all`/`--force` (bulk). The five raw sheets stay raw — opinion lives only in the new sheet.
- Applied retroactively to **all 8 existing snapshots** (0708 = pre-tagging variant; 0710–0722 = mature-tagging variant). `export_snapshot.py` gained opt-in `--with-ai-review` (default still raw-only). Scheduled task `meatcode-data-audit` updated to author + inject the review every run.
- What the review flags (unchanged data reality, now written down): ingestion is clean but **enrichment/scoring is largely unwritten** — Sources `composite_score=0` & `review_status=pending` for every row, `trust_tier`/`evidence_strength`/`actionability` empty, domain tags only 26–74% filled; Experts are name+affiliation only (no email/country/h-index, `dimensions_topics` stubbed to 'fermentation'); Molecules carry no structure (SMILES/CAS/formula/CID empty); Odours ~45% 'Other'; Organizations clean. Consistent with the known quarantine/write-back gap.

## Follow-up v12.4 — lean-v1 design port — shipped to the repo 2026-07-21 (awaiting deploy)
Restyled (not replaced) the live Database + Oracle to match `UI-UX Designer/meatcode_lean_v1.html`:
- **Database (molecules/experts/companies):** lean `.filterbar` (pill search + live `.fchip` category chips + right sort) + `Data / <Entity>` breadcrumb + `.tbl` card + ghost `⤓ Export (.xlsx)`. Columns: Molecules MOLECULE·CLASS·SOURCES·RELEVANCE(bar from `priority_score`); Experts NAME·AFFILIATION·COUNTRY·H-INDEX(bar, no relevance col); Companies NAME·COUNTRY·WEBSITE. Pagination + Toolbench bookmark kept. Molecules default `Fats`→`All`.
- **Oracle center:** lean centered header + `.oracle-box` + `.answer` card; real SSE sources as coral paper pills (`[id]` kept); follow-ups as "→" chips. Left rail/streaming/Lab Stash/no-scroll all preserved. **No fabricated molecule/expert chips** (honest provenance).
- Verified: 10/10 script blocks parse, both mockups byte-identical, all live wiring intact. **Not deployed — `deploy.command`.**
- ⚠️ Parallel-session hygiene: a concurrent session's *uncommitted* Export/Import WIP was absent (working file was at the 13:19 commit). Multiple Cowork sessions are editing the same mounted files — commit/push between hand-offs to avoid losing WIP.

## Follow-up v12.3 — shipped to the repo 2026-07-21 (awaiting deploy)
- **No page-scroll, centered frames in every tab** (Oracle/Research/Database/Simulate): each scene's `.canvas` is the bounded internal scroller (`min-height:0`+`overflow:auto`) inside the fixed `64px 1fr`/100vh shell; Oracle rebuilt so `#oracleAnswerSlot` is the sole scroller. Page scroll is now structurally impossible — only inner answer/table areas scroll. `.sim-wrap` centered (was left-jammed).
- **Toolbench replaces the search bar:** `.topbar-search` deleted everywhere (in-table molecule search kept); a wrench "Toolbench" button on every topbar opens one drawer with 3 persisted sections — **Saved molecules** (new `mc_saved_molecules_v1` + a bookmark button on each molecules row), **Saved sentences** (`mc_lab_stash_v1`, now via a single-owner `window.MCStash`), **Marked chats** (pinned `mc_oracle_history_v1`). Redundant bottom-left Lab Stash button removed; highlight-to-save unchanged.
- Verified: 10/10 script blocks parse, both mockups byte-identical. **Not deployed — run `deploy.command`.**

## Follow-up v12.2 — shipped to the repo 2026-07-21 (awaiting deploy)
- **Full-screen shell:** app grid `64px 1fr 88px`→`64px 1fr`; the bottom **dock + dev flow-bar removed** (`display:none`), so the platform uses the whole viewport with no page scroll. (Fixed a sync gap: the hide block was in LIVE but missing from v9 — now matched.)
- **Ask button now works for every question** (was stuck-disabled after the first): re-enable moved to `.finally()` + an `input` listener that enables Ask on typed text.
- **Chatbox narrowed** (`rows=2→1`, min-height 64→46px — `rows` was the real lever; no auto-grow JS).
- **Chats + Lab Stash cache**: already exists in `localStorage` (verified solid). `docs/client_cache_design.md` (new) documents it + the key finding — data "disappearing" is the **Safari Private window** (ephemeral localStorage), not a bug; recommends an Export/Import JSON button for durability, accounts deferred.
- Verified: 10/10 script blocks parse, both mockups byte-identical. Deployment confirmed current (commit e8e3e2f). **Not deployed yet — run `deploy.command`.**

## Follow-up v12.1 — shipped to the repo 2026-07-20 (awaiting deploy)
- **Molecules fully categorized (799/799):** `pipeline/categorize_molecules.py` (new) filled every `molecules.category` into a 15-class meat-flavor chemical taxonomy (LLM Haiku for 40 + offline name-heuristic bulk-UPDATE for 748). Distribution is aroma-sensible (Sulfur 210 · Pyrazines 131 · Nitrogen 106 · Furans/Aldehydes 59 … Fats 12), only 2.7% "Other". The Molecules category filter + Fats default are now meaningful. (`Fats` is legitimately small — the corpus is mostly volatiles.)
- **Experts Relevance sort removed** (button + config `defaultSort`→`h_index`); Map's relevance sort + "Top-rated only" filter kept.
- **Fixed-viewport Oracle UX:** app is now a static 100vh shell (only inner regions scroll — long answers no longer stretch the page); left rail is a full-height column with **profile + Lab Stash always visible**; **Oracle is the default landing scene** and the logo routes to it; the ask box is shorter and **clears after each question**. Both mockups verified (10/10 script blocks parse, byte-identical). **Not deployed — run `deploy.command`.**

## Platform batch v12 — shipped to the repo 2026-07-20 (awaiting deploy)
8 UI features (parallel run) in `app/meatcode_mockup.html` + v9: Experts relevance **column** removed; Companies **Website** link column; Molecules table defaults to **Fats** (⚠️ only 10/799 categorized — UI shows "10 of 799" + one-click "show all") and is **paginated 50/page**; Oracle **Lab Stash** (highlight→save snippets, `localStorage` `mc_lab_stash_v1`, panel by profile); Simulate **OAV row + Suggested-next-steps deleted**; Research **Saved Queries deleted**; nav reordered **Oracle·Research·Database·Simulate·Map**; **alarm bell removed** + search widened; Oracle **chat rename** + **answer scrolls in its own pane** (no more whole-page stretch). Backend: `GET /api/molecules` gained `offset` + `meta=1` ({items,total}) — verified live (50/page, total 799, Fats=10). All script blocks parse + byte-identical across both mockups; server `py_compile` clean. **Not deployed yet — run `deploy.command`.** Open decision: LLM-categorize the 784 NULL `molecules.category` so the Fats default is representative.

## Oracle v11 — shipped to the repo 2026-07-20 (awaiting deploy)
Four user-requested Oracle features, built by a 3-agent parallel run:
- **Voice dictation** in the ask box (Web Speech API; button hidden where unsupported) — needs a real-browser test.
- **Save/bookmark icon enlarged** to a 34px target, scoped to the Oracle sidebar only.
- **Sidebar rebuilt as dynamic Pinned-above-History** — asking appends to History, the bookmark promotes a chat to Pinned; persisted in `localStorage` (`mc_oracle_history_v1`, 25/list cap, try/catch throughout). Deliberately client-side: the site is behind ONE shared password, so there is **no per-user identity** to key server-side history to — see `docs/oracle_chat_history_design.md`.
- **No model name shown to users**: "Searching the database and asking Claude…" → **"Digging the MeatCODE database…"**; server error text is now vendor-neutral (real diagnostic kept in Render logs). `POST /api/ask` gained an **additive** `event: status` (`retrieving`/`answering`) so the phase label is honest; fully backward-compatible.
Verified: 10/10 inline script blocks parse in both mockups (byte-identical), server `py_compile` clean, SSE order `status→sources→status→chunk→done`. **Not yet deployed — run `deploy.command`.**
Open decision for Lior + Daniel: whether to add an anonymous server-side question log (no identity) as validation-year evidence.

---

## 📣 Latest team broadcast — see `TEAM_BROADCAST.md` (current as of 2026-08-16)
**Every agent: read [`TEAM_BROADCAST.md`](TEAM_BROADCAST.md)** for the current "what you must know now" plus the
MVP north-star goals. Recent headlines: the 2026-08-16 Oracle capability demos + live `GET /api/corpus` filter
+ first-class `#analytics` scene, and the Maillard-simulator architecture (mock mode, flag-gated). **The #1
risks remain B1 (deploy the backlog) + B2 (quarantine write-back).**

---

## Where we are
**MVP push (set 2026-07-22):** a credible, source-backed prototype — **internal demo end of August 2026**,
external **P1 expert validation mid-September**. The bar is `docs/MeatCODE_MVP_Definition_and_User_Journeys.md`;
open deliverables (8 lanes · action items · 2 blocking gaps, with owners) live in `MVP_BOARD.md`. Journey
status and the P0 spine are in the "🎯 MVP alignment" section above.
**The two critical-path blockers (unchanged):** **B1 — deploy the built backlog** (a month of verified work,
v12.1 → the 2026-08-16 demos, is committed but NOT live) and **B2 — close the quarantine → `relevance_llm`
write-back** (Daniel-rejected sources are still retrievable). Nothing else is demoable to reviewers until B1
lands. (The underlying GFI roadmap still runs in phases to Mar 2027; the MVP is the near-term focus.)

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
- **Grounded retrieval — SHIPPED (2026-07-08 → 2026-08-15).** `POST /api/ask` now retrieves from the corpus
  (`sources.search_vec` FTS, gated to `relevance_llm >= 60`, with an AND→OR fallback for the
  `websearch_to_tsquery` 0-result problem), grounds the answer in only those sources, cites real
  `sources.id`, and refuses ("the corpus doesn't cover this") rather than fall back to open/training
  knowledge. It also gained the additive `event: status` (retrieving/answering) and `event: consensus`
  (agree/oppose/neutral per source). A closed-corpus RAG eval **baseline** is on record
  (`analysis/rag_eval/`: groundedness 3.4 · cite-acc 4.8 · coverage 4.1 /10 — zero invented citations, but
  depth still largely uncited general knowledge). **Still open (Algorithm/Data):** the gold-set benchmark vs
  GPT/Claude/Perplexity (the only proof of "benchmark-competitive"), reranking / pgvector-hybrid, and closing
  the quarantine write-back (B2). Design of record: `docs/DECISION_grounded_answers_and_relevance.md`,
  `docs/daniel_review_workflow.md`.
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

## Next (highest leverage first) — the P0 spine for the 31 Aug MVP
Full board with owners/status in `MVP_BOARD.md`. In order:
1. **B1 · Deploy the backlog** (Lior) — `deploy-dev.command` → verify staging → `promote-to-prod.command`.
   A month of committed, verified work is invisible to reviewers until this lands. **[critical path]**
2. **B2 · Close the quarantine → `relevance_llm` write-back** (Data) — Daniel-rejected sources must actually
   drop out of Oracle retrieval, not just sit in `source_audits`. **[critical path]**
3. **Benchmark harness** (Algorithm) — 30–50 expert-authored gold questions, MeatCODE vs GPT/Claude/Perplexity,
   blind-rated. The only proof of criterion 1 ("benchmark-competitive"). Then reranking → pgvector hybrid.
4. **Corpus trust** (Data) — back-tag the remaining untagged sources (~252 left) + run the retrievability
   count, so Research and the Oracle count the same governed corpus.
5. **GC-MS preview + `/api/protocols`** (Full-Stack + Data) — scaffold the fingerprint / by-cut preview on
   clearly-labelled reference data (decision 2026-07-23: preview, not a live engine), pending the
   reference-data-source decision.
6. **UI/UX** — lock ONE design system, add the J3 knowledge-graph view, reframe Research into a J4 planning
   flow, and label J2 / J4 / Simulate as honest previews.

## Decisions (most recent first)
- **2026-07-23** — **GC-MS / molecular tool ships as an honest PREVIEW** for the MVP — fingerprint + by-cut
  comparison on clearly-labelled reference data, not a live analytical engine. Resolves the long-open
  "GC-MS: P0 vs preview?" question. Open sub-decision: reference-profile source (WUR / literature-mined /
  synthetic-and-labelled). See `MVP_BOARD.md`.
- **2026-07-23** — **Deploy is a split dev→prod flow.** `deploy.command` and `sync_meatcode.command` are
  retired; use the `Release Center/` scripts: `deploy-dev.command` (→ private staging) then
  `promote-to-prod.command` (→ public site), with `rollback-prod.command` to undo.
- **2026-07-22** — **MVP definition + 5 user journeys adopted** as the bar (internal demo end-Aug, P1
  validation mid-Sept). Open deliverables tracked in `MVP_BOARD.md`; the P0 spine leads with B1 (deploy) +
  B2 (quarantine write-back). See `docs/MeatCODE_MVP_Definition_and_User_Journeys.md` + `docs/MVP_ALIGNMENT.md`.
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
- **B1 — the built backlog is not deployed.** A month of verified work (v12.1 → the 2026-08-16 Oracle demos)
  is committed but not live; reviewers see none of it until `deploy-dev` → `promote-to-prod`. **[critical path]**
- **B2 — quarantine write-back gap.** Confirmed quarantines write only to `source_audits`, NOT to
  `sources.relevance_llm`, so a source Daniel rejects is still retrievable and citable by the Oracle. Close
  before any external / WUR demo. **[critical path]**
- **Corpus governance undercuts "benchmark-competitive":** ~818 sources (790 citable), but only **~39% pass
  the `relevance_llm >= 60` gate**, ~252 still untagged, and molecules / experts are thinly enriched
  (chemistry fields NULL until a curation source is chosen — don't invent values). The Simulate / Prediction
  and GC-MS surfaces imply models the data can't yet back — keep them **labelled synthetic / preview**, framed
  as hypothesis-generation, never as authority or chemistry.
- **`/api/corpus` counts are currently UNGATED** (open decision #9 in `MVP_BOARD.md`): Data recommends applying
  the Oracle's `relevance_llm >= 60` gate so Research and the Oracle count the same corpus; Full-Stack shipped
  it ungated. One-line SQL change — awaiting Lior's call.
- **Data reality (per the AI-Review snapshots):** ingestion is clean but enrichment / scoring is largely
  unwritten (Sources `composite_score = 0`, tags 26–74% filled; Experts name + affiliation only; Molecules no
  structure yet). Paper ingestion is blocked (no Dimensions creds / ingester).
- **Neon auto-sleep** bites concurrent multi-agent access; keep warm or front with `meatcode_server.py`.
- **Parallel-session hygiene:** multiple Cowork sessions edit the same mounted files — commit / push (or hand
  off through the Coordinator) between sessions to avoid losing uncommitted WIP.
