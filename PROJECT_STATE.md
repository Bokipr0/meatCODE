# PROJECT_STATE — MeatCODE

## 2026-10-29 · Private dashboard environment/access correction — live

Screenshot showed Development selected on the production dashboard after unlocking. Corrected
startup to use the server's own environment automatically; hosted environment picker becomes
read-only, while local administrators retain cross-environment selection. Locked, empty and
unavailable states now have separate wording; totals remain unknown until successful loading.
Python suite and two browser dashboard suites passed. Runtime 2bbba3f verified live on both sites,
with Render production deploy dep-dbhns1g473hc73csuuk0. No credential/database/schema changes.
Shared conversations remain in private user_research.oracle_turns inside existing dev/prod
Neon databases; no fully independent research database/branch was provisioned by this fix.

## 2026-10-29 · Dataset guide saved locally; publication remains manual

One-page dataset PDF regenerated in platform_docs alongside Markdown and editable SVG.
Local Git configuration points to Bokipr0/meatCODE; Release Center deploy-dev and promote-to-prod
scripts remain present. No push/deployment performed for this document; remote sync not verified.

## 2026-10-29 · Oracle transcript research live

Added separately consented Oracle questions, answers, clarifications and citation capture into
private Neon user_research.oracle_turns, with an administrator-only paginated transcript viewer.
Consent renews to 2026-10-29-chat-v1; checkbox is unchecked and historical chats are not imported.
Clarity remains masked; no chat text reaches Clarity or PostHog. Migration0019 applied to both
existing databases; scientific inventories and Necmettin's private-data denial verified unchanged.
61 Python tests passed per database in rollback-only fixtures; browser capture/dashboard privacy
checks and synthetic local HTTP save/read/withdraw/late-write rejection passed. Runtime e98349d
verified live on dev/main (Render dep-dbhmk8k9v7es73bib4sg / dep-dbhml0a9lscs739vbnb0).
Hosted transcript routes deny unauthenticated access; authenticated hosted capture awaits fresh
tester opt-in. Local private dashboard reads production successfully, with zero transcripts yet.
This uses existing private schemas, not a newly provisioned independent Neon branch. Retention
includes chat in the existing manual 90-day maintenance; no automatic purge was scheduled.
Current feature switches preserved; unrelated in-progress documentation edits left untouched.
Details: platform_docs/ORACLE_CHAT_RESEARCH.md. Rollback prod-20261029-before-oracle-chat.

## 2026-10-29 · Dataset guide architecture illustration

Replaced the safe-updates text section with a compact vector diagram in the same one-page PDF:
master publishes to Oracle/Ecosystem/Simulation, each shows its data areas, proposed revisions
return via Lior-only approval. Editable SVG saved in platform_docs/diagrams/meatcode-dataset-modules.svg.
Permission table retained; final PDF visually checked, one page. No infrastructure changes.

## 2026-10-29 · Dataset guide permission comparison added

Updated `platform_docs/DATASET_ROLES_ONE_PAGE.md/.pdf` with owner, contributor, viewer and
publisher comparison across read/edit/approval/publication/access-management permissions.
Preserved Lior-only revision approval and distinction between proposed and existing grants.
PDF verified visually and remains one page. Documentation only; no database/access changes.

## 2026-10-29 15:17 UTC · Neon implementation access check

Implementation explicitly requested. No Neon connector tools, CLI login, or configured
NEON_API_KEY/NEON_API_TOKEN available; existing SQL connections are present but cannot create
the planned independent Neon projects. In-app Neon console opens at sign-in; left ready for
Lior. No database/project/permission changes made in this check. Existing backup and provisioning
plan above remain the prepared handoff; account connection is required to continue.

## 2026-10-29 15:03 UTC · Governed datasets: backup complete, provisioning pending

User requires explicit Lior approval of each child contribution revision before master publication;
retain baseline vs later provenance and component/project/contributor tags. Accepted master changes
may propagate asynchronously to other modules. New roles/project design documented in
`platform_docs/DATASET_ROLES_ONE_PAGE.pdf` and `DATASET_PROVISIONING_PLAN.md`.
Configured production/dev database snapshots saved privately in `data/backups/20261029T150102Z/`:
58/65 tables, custom archives and hashes verified readable, full restore not yet tested.
Neon control-plane plugin remains not installed/connected: no module projects, grants, migrations,
runtime switches or sync workers provisioned. Mandatory-approval digest is undecided, not scheduled.

## 2026-10-29 · Release Center repaired and requested modules OFF — verified live

User requested diagnosis/fix of toggles/publishing/deployment and disabling Analytics/Simulate. Git authentication verified by actual pushes; no key rotation. Earlier local divergence was reconciled, but changes had not been pushed. Old GUI only launched Terminal and never observed publishing exit status. New local-only tracked job API requires same-origin custom header and explicit confirmation, rejects concurrent releases, returns real sanitized errors, and GUI verifies the hosted target commit before claiming live. Direct scripts retain prompts; cockpit jobs use the existing GUI confirmation. Scripts fail on Git errors, preserve existing lock files, check ancestry before staging, and create deployable markers after skip-render commits. Canonical Release Center paths are preferred over archived copies. Launcher reuses a healthy local cockpit.

Fixed concurrent flag-save loss with serialized read-modify-write and atomic fsync/replace. Thirty-toggle isolated regression and24 concurrent real-HTTP saves preserve all values/metadata. Simulate navigation, starter and deep links now follow maillard_sim; Analytics navigation/deep links/direct workspace routes follow analytics. Both dev and prod saved flags analytics/analytics_module/analytics_workspace/maillard_sim are false. Existing research tracking remains true.

Published through actual repaired staging and promote job routes (both exited0). Both Render services verified live on41872cbe0bb7cfea01ed76409a515ec361f2bc27, with all four flags false and healthy /api/health. Stagingdep-dbhlsp29lscs739ttusg; productiondep-dbhlth4s728c73da8n40; rollbacktagprod-20261029-1557. No new production Traceback/ERROR logs.55 offline tests pass,5 live-only skips; browser checks cover disabled navigation/direct links and visible failed-push/verified-live states. Local HTTP /analytics and /api/simulate return404. Local cockpit restarted with final handlers. Verification: data/verification/release-center-repair-2026-10-29.json; operations: platform_docs/RELEASE_CENTER_REPAIR_2026-10-29.md. Final documentation/test/local-launcher updates may use skip-render; running app source remains the verified41872cb release.


## 2026-10-29 · Necmettin scientific database access — applied and verified

User explicitly requested read/view-only database access based on Necmettin’s latest mail. Verified recipientnecmettin.karakaya@gmail.com from29 October14:22 UTC email (Gmail1a1880a20ff84799); he already has Neon project Viewer access. Applied numbered migration0018 DEV then production, using SQL-only rolecreation to avoid neon_superuser membership. Role necmettin_review_ro has SELECT on current public/moldedup and dev lightrag_demo relations;69 production and76 dev relations verified with actual restricted login. INSERT/UPDATE/DELETE fail42501 even with transaction read-only default disabled. Private user_research feedback denied; no CREATE/admin/membership/sequence-write/future-table grants. Scientific records unchanged. First verification query error caused rollback before any grant; corrected run applied and passed both branches.

Direct connection credentials saved mode0600 outside repo/webroot in /private/tmp/meatcode-necmettin-readonly-20261029.env for Lior’s secure handoff; values never printed, committed or emailed. No outbound message sent. Necmettin’s receipt/login remains unverified. See platform_docs/NECMETTIN_READONLY_ACCESS.md and ignored credential-free verification data/verification/necmettin-readonly-2026-10-29.json. Research-storage branch setup remains a separate pending task; this change affects reviewer SQL privileges only.


## 2026-10-29 · Production capture confirmed; independent storage prepared; local publication repaired

After Lior opted in, production Neon and PostHog agree:1 session.started,7 scene.viewed,1 oracle.submitted,1 oracle.completed and1 feedback.submitted. Server research routes and /api/ask return200. No prompt/answer/comment contents or session capabilities read. Hosted Oracle completion is now observed; actual Microsoft recordings still unverified.

Requested independent research storage is prepared in platform_docs/research_storage_2026-10-29: dedicated-connection routing, strict no-fallback mode, maintenance/import/dashboard consistency and bounded research-only copy preserving withdrawal protection.54 offline tests pass (5 live-only skips). Branch creation/copy/switch NOT performed: Neon account connection is missing. Suggested official Neon plugin; automatic control of com.openai.codex installation UI was denied by app safety. User must click Install/authorize; no secret requested in chat.

The screenshot's push failure was divergent Git history (local2 ahead,11 behind), not demonstrated authentication failure. Saved backup branchcodex/local-before-reconcile-20261029-f6bd1ac, merged remote release without force/reset, preserved local-only history and published Science/Ecosystem/Oracle files. Local merge7b2b8d9;50 checks passed. Fixed launchers to fetch/check history BEFORE git add/commit and to show actual push errors. Bash syntax passes and git push --dry-run confirms a normal fast-forward is possible. No actual push of the newly reconciled local backlog was performed; production remains the verified20acea3 application release.


## 2026-10-29 · LIVE release — Clarity/PostHog and private testing dashboard

User explicitly authorized redeploy/update and separately approved enabling the private administrator dashboard. Published the reviewed changes from a clean checkout, preserving newer Science/Ecosystem/guided Oracle and original local work. Both dev and production now run20acea3e648e0e3feba40845cae3936951867b07; verified /api/version, user_testing+analytics flags, healthy startup and protected research routes401 without site login. Staging deploydep-dbhkm9h9q7ns73d280qg and productiondep-dbhkn5vb9u1s73a0nsv0 are live. Rollback tagprod-20261029-analytics-live-testing. No new production ERROR/Traceback logs found after deployment.

Public PostHog settings, USER_RESEARCH_ENABLED=true and distinct RESEARCH_ADMIN_TOKEN values are configured on both Render services; admin values remain only in secure Render settings and ignored local .env/.env.dev, never chat/Git. Dashboard /research-dashboard requires normal site login plus the corresponding administrator value retrieved privately from Render Environment. Local Release Center administrators retain token-free local access. No site password or Anthropic key was changed.

Fifty offline checks passed (five database-only skips); actual staging HTML browser privacy suite passed. Prior real local SDK delivery is queryable in PostHog; first-party HTTP→Neon capture/deletion checks passed and probes removed. Protected hosted-page checks require the user's signed-in browser: user initially did not see the privacy control before final production deployment; fresh production opt-in confirmation requested. Actual hosted Microsoft recordings and successful live Oracle model call remain unverified. Health labels key/database checks configuration-only. Do not claim a valid model credential from key presence.

Correction: Render environment-update API operations themselves triggered redeploys of then-current source; prior notes saying no deploy was triggered were inaccurate. Missing Clarity source was resolved by publishing the new Git commit, not by those earlier old-source redeploys. Local original checkout remains intentionally untouched/stale; do not blanket-push it over the clean published release. Credential-free verification is under data/verification/research-deployment-2026-10-29.json and research-hosted-public-checks-2026-10-29.json.


## 2026-10-29 · Authorized release — analytics and live testing

Lior explicitly requested redeployment and update. Applied the reviewed analytics release to a clean checkout of current dev/main6394c039749a; preserved newer Science/Ecosystem/guided Oracle. Added consent-gated Clarity/PostHog, isolated research API/storage/consent0017, private live dashboard and prior sidebar/Analytics/Release Center fixes. Latest main/dev were identical before release. Offline50-test suite passed with5 live-only skips; previous rollback-only Neon tests and real local HTTP/provider checks passed. Local dev SDK test is queryable in PostHog. Public provider settings already saved on both Render services. Publishing staging first, then production only after verification; do not infer deployment success from this preparation entry. User authorization overrides standing agent-no-publication convention for this release. No secret value committed.


> Living technical status. **Every agent reads this after CLAUDE.md and updates it before pushing.**
> Asana owns *tasks & priorities*; this file owns *technical reality* — what's built, what's broken,
> what's in flight. Keep it short and current, not a changelog.

_Last updated: 2026-10-26 · Yochai (PM) with Claude — Science replaces Research in the top nav (flag research_nav_hidden: Research chip hidden, not deleted), on dev for staging. Prior: 2026-10-25 20:40 UTC — Ecosystem people + papers LIVE from Neon (GET /api/ecosystem/people), checked on staging by Yochai and PROMOTED to production (main fe504c6, tag prod-20261025-2033). Prior: 2026-10-25 19:25 UTC — Science + Ecosystem + guided Oracle PROMOTED to production (flags science_module / ecosystem_module / oracle_guided now dev ON / prod ON) after Yochai's staging check. Prior: 2026-10-05 · Project Coordinator — NEW dev-only **Papers browser** module (flag `papers_browser`, dev ON / prod OFF): top-nav chip + `#papers` scene + `/api/papers-browser/*`. Awaiting deploy-dev. See AGENT_UPDATE_LOG.md._

## Science + Ecosystem + guided Oracle — LIVE in production 2026-10-25 (flags dev ON / prod ON)
**Nav (26 Oct, on dev):** Science replaces Research — flag `research_nav_hidden` hides the Research chip in every topbar while `science_module` is on (Hidden, not deleted: `#research`, its wizard and in-content links such as Science's "Molecular map" card still work). Prod nav after promotion: Oracle · Science · Ecosystem · Simulate.
Three Chat-designed modules are now part of the platform, re-skinned onto the live tokens and tethered by a handoff bus
(`app/modules/mc-bridge.js` ↔ `window.mcOpenModule` in the mockup). **Science** (`science_module`): top-nav chip →
`#science` iframes `app/modules/science.html` (Foundations tour + Precursors; every Ask → the real Oracle, Experts →
Ecosystem). **Ecosystem** (`ecosystem_module`): chip → `#ecosystem` iframes `app/modules/ecosystem.html` (People
directory + Radar on the sanitised 8 Oct snapshot `ecosystem_data.json`; only Approved/Merged inbox rows shown — 4 Radar
items today; intro + correction/removal by email to `ECOSYSTEM_CONTACT_EMAIL`; `/api/ecosystem/bootstrap` + `/intent`,
404 when off). **Guided Oracle** (`oracle_guided`): `POST /api/ask` with `guided:true` may answer with a new `ask` SSE
event (≤3 questions, tap options, Just answer); answers open with "Working from:" and end with Open in Science / Experts
on this. Verified locally (stand-in model) + flag-off in prod mode; staging checked by Yochai 25 Oct, then promoted.
**Live data (25 Oct, in production since fe504c6):** People + papers now come LIVE from Neon via `GET /api/ecosystem/people` (server/ecosystem.py `live_people`, SELECT-only, 10-min cache) — 155 people / 109 papers vs the snapshot's 153/108 (+ José M. Lorenzo, Igor Tomašević, whose accents the 8 Oct match missed). The 8 Oct copy stays only as a labelled fallback. `source_experts` is EMPTY in Neon, so the link is a normalised author-name match (rule in the module docstring); filling `source_experts` would make it exact.
**Open:** `ECOSYSTEM_CONTACT_EMAIL` on both Render services; Radar content approval (4 reviewed items today);
fill `source_experts` in the pipeline so the people↔papers link is exact. See
AGENT_UPDATE_LOG.md 2026-10-25.

## Papers browser — dev module for the whole `sources` table — shipped to the repo 2026-10-05 (awaiting deploy-dev)
Top-nav **Papers** chip (flag `papers_browser`, dev:true / prod:false) → in-app `#papers` scene iframing `app/dev/papers_browser.html`. Browse all 818 papers 50/page, sort/filter (search, year, relevance, review status, study type, topic, tag, audit lenses No DOI / No abstract / Untagged / In-Oracle-corpus), shareable URL state, column picker (default minimal), tick rows across pages → CSV (server) / XLSX (client SheetJS), "Export filtered" + "Download entire table" CSV (UTF-8 BOM, formula-injection-safe), per-paper Open link + best-effort Unpaywall open-access PDF (links only; needs `UNPAYWALL_EMAIL`, optional). Backend `server/papers_browser.py` + routes in `meatcode_server.py`; **all routes 404 when the flag is off** (so prod exposes nothing until `papers_browser.prod` is flipped). Read-only by design — write-back (quarantine/flag) deliberately deferred (see `platform_docs/PAPERS_BROWSER.md`). Design notes: `UI-UX Designer/PAPERS_BROWSER_DESIGN_NOTES.md`. Verified live vs Neon (818 / 50 per page, filters, CSV parse, flag-off 404, jsdom end-to-end); real-browser render + `.xlsx` output still need a staging click-test. **Not deployed — `deploy-dev.command`.** Open: set `UNPAYWALL_EMAIL` on the Render dev service; Daniel/Lior decisions in the advisory doc §6.

## "Backups" button — one-click download, dev-only for now — shipped to the repo 2026-09-21 (awaiting deploy-dev)
All 15 topbars in `app/meatcode_mockup.html` gained a **Backups** button (next to Dev Area) opening a small menu with **Repo backup** (`/api/backup`) and **Data backup** (`/api/data-backup`) links — plain downloads, no extra auth beyond the site password already in effect. Gated by new flag **`backup_center`** (`Release Center/features.json`, `dev:true, prod:false`) — same mechanism as `dev_area`, so the button is invisible on prod until Lior flips that flag's `prod` to `true` and runs `promote-to-prod.command`. ⚠️ Note the flag only hides the *button* — the two API endpoints themselves are already live on prod behind the site password (by design, from the prior work); this doesn't currently lock the endpoints to dev-only too. Verified: JSON valid, 13/13 inline scripts `node --check` clean, exact div/svg/path tag balance, 15/15/15/15 button/menu/link counts confirmed. **Not deployed — `deploy-dev.command`** → click-test on staging → stays off prod unless Lior asks to flip it.

## Actual Neon data downloadable via the server — shipped to the repo 2026-09-21 (awaiting deploy-dev)
`server/meatcode_server.py` gained `GET /api/data-backup`: a real `pg_dump` (schema+every row, gzip'd, directly restorable) if the binary is on the host, else a zip of one CSV per table (all 47 tables, every row — data only, honestly labelled as such in the zip's README). Same shared site-password gate as the rest of the site — no new auth. This is distinct from the existing `pipeline/export_snapshot.py` xlsx (a curated 50/20/20/20/20-row sample) — this endpoint is the full data. Verified locally (fallback path exercised since this sandbox lacks `pg_dump`; row counts cross-checked exactly against live Neon — sources 818, molecules 799). **Not deployed.** Live URL once promoted: `https://meatcode-oracle.onrender.com/api/data-backup`. Open: confirm which path (pg_dump vs CSV fallback) Render's python runtime actually takes once deployed.

## Repo backup downloadable via the server — shipped to the repo 2026-09-21 (awaiting deploy-dev)
`server/meatcode_server.py` gained `GET /api/backup`: streams a zip of the repo's git-tracked files at HEAD (`git archive --format=zip HEAD`) straight from the running Render instance. Secrets/gitignored data can't leak (archive walks the commit tree, not disk); same shared-password gate as the rest of the site, so Daniel/Yochai can pull a clean backup themselves once they have the site credentials — no per-user auth added. Degrades to a `503` if git isn't available on the host; never a 500. Verified locally (`py_compile` + live `curl` round-trip, valid zip, correct filename). **Not deployed — `deploy-dev.command` → confirm on staging → `promote-to-prod.command`.** Live URL once promoted: `https://meatcode-oracle.onrender.com/api/backup`.

## Research wizard + Analytics module — built → LIVE-integrated → polished (2026-08-31 → 09-01, flag-gated, awaiting deploy-dev)
Multi-run arc (Coordinator-orchestrated; per-run detail in `AGENT_UPDATE_LOG.md`). Both surfaces are now wired into the live platform as **same-origin iframes gated by flags**, plus a new read-only endpoint. Dev pages carry an **`?embed=1` embed-mode** (hides their standalone chrome, keeps in-content honesty labels).

**Research — reaction-network journey replaces the phase-picker** (flag `ff-research_reaction_network`, dev ON / prod OFF)
- New dev page `app/dev/research_reaction_network.html`: a no-page-scroll **3-step wizard** — Step 1 pick **Lipid / Aqueous precursors** (auto-advances) → Step 2 **Heat + Reaction Network** (curated precursor→reaction→volatile graph, "oven·180 °C"; nodes light-by-default→color on hover; click → inline compound profile → **"Dive into the full database corpus →"** `target="_top"` → `#database` molecule table) → Step 3 **Analytical + Sensory** profiles (scalable inline SVG) with **"Compare with your own data →"** `target="_top"` → `#analytics`. Network fills the width; volatiles capped to top-8 by corpus mentions; "← Back" pill on steps 2–3. Distinct from Simulate (explores our data, not a predictor).
- Backend: NEW read-only **`GET /api/reaction-network?branch=lipid|aqueous`** (`server/reaction_network.py`) — curated precursor/reaction skeleton **enriched with real Neon volatiles from `meaty_volatile_library`** (honest `backed` flags), SELECT-only, degrades gracefully. Verified vs live Neon.
- Integration: the mockup's **`#research` scene iframes the wizard** (`?embed=1`) when the flag is ON; OFF keeps the old phase-picker. Research nav chip unchanged.

**Analytics — a real 4th top-nav module** (flag `ff-analytics_module`, dev ON / prod OFF)
- New dev page `app/dev/analytics_workspace.html`: guided **bring-your-own GC-MS/NMR → compare to reference** preview, simplified to **2 steps** — (1) choose method (GC-MS/NMR) + upload → **Compare Samples** → (2) analytical + sensory results (default reference). Honest illustrative preview (no real parsing).
- Integration: **"Analytics" added as the 3rd nav chip** (Oracle · Research · **Analytics** · Simulate — additive, flag-gated, and the **"NEW" badge moved here from Simulate**) → an in-app **`#analytics` scene that iframes the workspace**. ⚠️ **This REPLACES the 2026-08-31 measurements-browser `#analytics`** — that markup was swapped for the workspace iframe. Full-Stack added a `/analytics` pretty-URL + **`X-Frame-Options: SAMEORIGIN`**. The `#analytics` left context panel was removed (full-width); Oracle history gained hover-✕ delete.

**Deploy path (flag-first):** `deploy-dev` → staging review (Research shows the wizard, Analytics chip opens the workspace scene) → flip each flag's `prod` in the Release Center → `promote-to-prod`. **NOT deployed.** This delivers board **A2 (screen-flow) + A3 (bring-your-own-data compare) + A7 (Analytics scene)**.

## Demo-prep — GC-MS/NMR measurements browser + Pablo's simulator LIVE (mock) — shipped to the repo 2026-08-31 (awaiting deploy-dev)

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


## Archived local-only entries preserved during reconciliation

These entries predate the verified publication above; their original status statements are historical.

## 2026-10-29 · PostHog and live research dashboard — local code, configured accounts

- **Native dashboard exists:** https://eu.posthog.com/project/325792/dashboard/1066277 (private MeatCODE Live Testing), six validated saved insights. EU project325792, latest official vendored posthog-js1.442.0, public runtime settings saved to original prod and dev Render services with merge-only updates. No app deployment was triggered.
- **Local dashboard/API ready:** /research-dashboard, three-second refresh over real Neon; admin-only data beyond shared site password, local loopback cockpit exception, no analytics SDK on admin page, no-store/read-only/bounded SQL and hash session labels. Hosted RESEARCH_ADMIN_TOKEN has not been generated/configured; hosted private reads remain closed.
- **Data migration live:** forward0017 applied DEV then PROD for fresh explicit2026-10-29 consent; historical consents remain unchanged. Five private research tables/scientific schema preserved. Backend45-test production suite passed; client privacy/dashboard fixtures passed. Independent actual local HTTP→dev Neon capture/feed/deletion/late-write410/cross-origin403/cleanup passed. Provider fixture tests are not delivery evidence.
- **Clarity exact cause:** both hosted services still run6394c039749a; that source lacks wrapper, routes and research flag. October28 manual redeploy reused older source. Public tag200 is reachable only, not installed/recording. Publish reconciled source; waiting does not install code.
- **Oracle status caution:** invalid-key logs were Oct28 at12:39 UTC; production manual deploy at16:36 UTC happened later. Latest model success remains unverified; do not present old401 as a fresh failure.
- **Real SDK delivery QA:** one consented local dev session sent session.started + scene.viewed to EU ingestion; two HTTP200 responses, zero page errors, Clarity blocked, no model/private content or Neon fixture. QA-only automation-detection override; production SDK unchanged. Forced dashboard refresh now confirms one session.started event; hostedcapture remains unverified.
- **Publication:** combined Oct29 package under platform_docs/user_research_2026-10-29 preserves newer remote Science/Ecosystem/guided Oracle and all previous research/UI guards; clean patch reapplication matches bytes. Local checkout is stale; avoid wholesale publish. ROLES/CLAUDE/team skill reserve Git and publication for Lior. Current guide: platform_docs/POSTHOG_LIVE_TESTING.md. No model call, private-key copy or code publication by agents.


_Last updated: 2026-10-28 15:58 UTC · Codex / Coordinator · isolated user research schema live; Clarity code local; production credential rejected._

> Living technical status: **what's built, what's live, what's broken.** Short on purpose.
> Tasks and priorities → Asana (mirrored in `platform_docs/ASANA_SNAPSHOT.md`). History → `AGENT_UPDATE_LOG.md`.
> Decisions and why → `platform_docs/DECISIONS.md`. People → `platform_docs/PEOPLE.md`.


## How this file stays true

| Claim type | Verified against | Re-verified by |
|---|---|---|
| What's live on production | `https://meatcode-oracle.onrender.com/api/version` (commit) vs git tags | `SYSTEM_SNAPSHOT.md` → "What is live right now" |
| What's on dev only | `origin/main..dev` commit list | same |
| Data numbers | live Neon, both branches | `SYSTEM_SNAPSHOT.md` |
| Task status | Asana project 1215201551726181 | `ASANA_SNAPSHOT.md` (daily sync) |

Status key: ✅ **live on prod** · 🟡 **on dev only** (committed, not promoted) · 🚩 **on prod but flag OFF** · 📄 **in repo, not committed** · ❌ **open/broken**

---


## Current verification — 2026-10-28

- **Original production Oracle still rejects its configured key.** Fresh28 October12:39 UTC guided-decision/answer logs return 401 invalid x-api-key. Production/dev use the same 6394c039749a and model, with separate environment credentials. User confirmed changing dev only. A valid key must be saved/deployed on original MeatCODE srv-d96ftplaeets73da7vng and tested with a real signed-in answer. Presence in health is not model access. Source now makes Render environment authoritative over dotenv and labels health configuration-only; unpublished, no credential changed.
- **Research storage is live:** additive migration0016 created isolated user_research schema on both Neon branches (five tables, 12 indexes, no PUBLIC grants), preserving scientific tables. Rollback tests and independent schema verification passed; all research/test rows are zero after cleanup.
- **Clarity integration is local, not hosted:** supplied project z4upnrbddu; explicit opt-in, whole-body masking, advertising denied, metadata-only events, submitted first-party feedback and deletion controls. No prompts/answers/attachments/account identities in events. Existing scientific download excludes research data; static private exports blocked. Actual local HTTP→dev Neon persistence, deduplication, deletion and late-write rejection verified. Local server restarted.
- **Operations and limits:** private JSONL export, manual90-day cleanup and server-token dashboard aggregate import provided. No scheduler or real Microsoft export/recording test; no token configured. Shared Clarity project aggregates cover both domains; they are not production-filtered records or raw replay copies. Feedback is separate from scientific evidence/model training.
- **Publication package:** platform_docs/user_research_2026-10-28/README.md and USER_RESEARCH_CLARITY.md. Combined current-main patch preserves newer Science/Ecosystem/guided Oracle and prior Oct27 fixes. Reconcile stale checkout; Lior publishes through Release Center. No Git/commit/deploy or key mutation by agents.


## Current verification — 2026-10-27

**2026-10-28 clarification:** Lior confirmed the service updated was **dev-meatCODE** at meatcode.onrender.com. This resolves the service-identity question; it does not establish that original production received the key change. Render still returns original production's latest deploy as dep-dbg8rgd9fdbs73d4bnj0 (2026-10-27 11:41:48UTC), with no newer deploy as of this check. Direct repair to original **MeatCODE**, srv-d96ftplaeets73da7vng, at meatcode-oracle.onrender.com: set a valid ANTHROPIC_API_KEY through Render, save/deploy, then verify an authenticated Oracle answer. No key read/copied/changed or deployment triggered by agent.

**Dev follow-up:** user-observed staging answer is supported by11:53UTC request/generated-answer follow-up logs; same commit/model as production. Credential/config difference is the current lead. User says already deployed; no newer original-production deployment returned after12:41Zurich, so service identity is being clarified.

- **Production build is live; Oracle answers are broken.** Original MeatCODE `srv-d96ftplaeets73da7vng` at meatcode-oracle.onrender.com runs main/`6394c039749a`, model `claude-sonnet-4-6`. User's updated-key manual deployment `dep-dbg8rgd9fdbs73d4bnj0` went live11:41:48UTC. Signed-in test then failed; matching guided-decision/answer logs at11:43:09/13UTC show **401 authentication_error invalid x-api-key** on the new instance. Fresh valid key + deployed environment + successful actual request still needed. Health only checks configured strings, not model authentication or DB connectivity.
- **Local changes ready, not published:** Simulate's three requested sidebar sections removed; Analytics nav follows the canonical Analytics zone switch (explicit OFF overrides legacy ON); Release Center distinguishes saved settings from observed production build/switch state. Local server restarted with the changes at localhost:8000. Analytics remains a labelled demo/illustrative workspace.
- **Publication requires reconciliation:** remote main has newer Science/Ecosystem/guided Oracle code absent from this checkout. Main-safe narrow patches, visual proof and verification: `platform_docs/release_fixes_2026-10-27/README.md`. Both patches applied together and syntax checks passed against inspected remote snapshots. Do not publish the stale local checkout wholesale. Lior owns normal dev→staging→production publication.
- **Separate Yochai resource:** `meatcode-oracle-0o99.onrender.com` remains a distinct missing-ANTHROPIC_API_KEY startup failure; do not confuse it with original production's rejected key. Local Oracle key also returned401; local retrieval itself returned sources.

The following older deployment/feature tables are historical snapshots; they do not establish today's live commit, key validity or feature visibility. Asana remains authoritative for task priorities.


## 1. Historical production baseline — verified 2026-10-11

At that historical check, production ran **`prod-20260921-1717`** (commit `c563d16`), started **2026-09-21**, model `claude-sonnet-4-6`, password gate on. `/api/health` → db ok, key present.

| Capability | Status | Note |
|---|---|---|
| Grounded Oracle chat (multi-turn, SSE, real citations, consensus event, attach + dictation) | ✅ | Retrieval: Postgres FTS, `relevance_llm ≥ 60` gate. Prompt answers uncited gaps from general knowledge (decision 2026-07-20). |
| Research, Database (molecules · experts · companies), Map, molecule/protocol detail pages | ✅ | |
| Analytics scene, Oracle v11 design | ✅ | the only two flags ON in prod |
| `/api/corpus`, `/api/compare`, `/api/molecules/{id}`, `/api/reaction-network` | ✅ | code on prod |
| `/api/backup` (repo zip), `/api/data-backup` (full Neon data) | ✅ | behind the site password; **no button on prod** (flag `backup_center` OFF) |
| Maillard simulator (`/api/simulate`) | 🚩 | mock mode, flag `maillard_sim` OFF → 404 on prod. Real simulator needs a `runtime: docker` Render service (not created). |
| Research reaction-network wizard · Analytics bring-your-own-data workspace · Compare · KG explorer · Fingerprint · Dev Area · Versions | 🚩 | built and on prod, hidden behind flags (dev ON / prod OFF) |
| Migrations 0011–0014 (molecule properties, drops) | ✅ | applied to both Neon branches; code on prod |

**Correction to every older doc:** "B1 — deploy the backlog" (the critical path through August) is **done**. Promotions on 2026-08-31 and 2026-09-21 shipped it. Entries in the archive marked "awaiting deploy-dev" up to 2026-09-21 are live.


## 2. Historical dev-only snapshot — recheck before promotion 🟡

| Commit | Date | What |
|---|---|---|
| `4635fa9` | 2026-09-21 | **Backups** topbar button (flag `backup_center`) |
| `881f3a1` | 2026-10-05 | **Papers browser** — browse/filter/export all 818 papers, Unpaywall open-access links (flag `papers_browser`) · `platform_docs/RAG_BUILD_VS_BUY.md` |

Both are flag-gated, so promoting changes nothing visible on prod until a flag's `prod` is flipped.


## 3. In the repo, not yet committed 📄

_2026-10-26 · Advisory: simplified adaptive architecture to nine objects/two flows in
`platform_docs/diagrams/meatcode-adaptive-simple.svg` (PNG preview), with matching one-page
`platform_docs/ADAPTIVE_ORACLE_SIMPLE.pdf` and editable Markdown. Supersedes the expanded visual
for review; earlier files preserved. Design only._

_2026-10-26 · Codex / Advisory: added editable adaptive-memory architecture SVG/PNG under
`platform_docs/diagrams/meatcode-adaptive-architecture.*` and verified one-page
`platform_docs/ADAPTIVE_ORACLE_ONE_PAGE.pdf` with editable Markdown source. Proposed user-scoped
SQL memory/optional vector lookup remains separate from scientific evidence. Documentation only._

_2026-10-26 12:57 UTC · Codex / Advisory: Render now connected. Failed resource is separate
`meatcode-oracle` / srv-dbf5eb5g1s2s73ei0td0 at meatcode-oracle-0o99.onrender.com (main,
Starter, Oregon). Original production is MeatCODE at meatcode-oracle.onrender.com and is live
on 6394c039749a. New resource build passes; startup exits1 because ANTHROPIC_API_KEY is not set.
Reuse this resource for Yochai after key/database/site-gate provisioning; no new server needed.
It still follows main, so an independent branch/env track remains to configure consistently with
its Blueprint. Diagnosis doc updated; no deployment/settings/secret changes made._

_2026-10-26 12:45 UTC · Codex / Advisory: added `platform_docs/ARCHITECTURE_EXPANDED_VALIDATION.md`,
working design v0.1 expanding Lior’s clean-arrows map. Records user-described local-PC Qwen M1,
separates M2 model from human review and deterministic checks, and specifies proposed candidate
contracts, supervised-learning loop, selective automation and publication/retrieval boundaries.
Includes three Mermaid diagrams. Design only; exact M2 variant, thresholds and training schedule
remain open pending Lior’s further requirements. No runtime, data, schema or deployment change._

_2026-10-26 12:42 UTC · Codex / Advisory: investigated screenshot of failed main-linked Render Blueprint.
Public production still responds on main/6394c039749a. Remote main includes newer Yochai
Science/Ecosystem changes absent from this local checkout; no Git sync performed. Screenshot
service identity and exact error remain unconfirmed: Render connection/sign-in needed for logs.
Prepared `platform_docs/YOCHAI_DEPLOYMENT_DIAGNOSIS.md` and inactive sandbox YAML under
`platform_docs/deployment_templates/`, recommending independent service/branch/database credentials.
No deployment, production settings, permissions, credentials or code changed._

_2026-10-26 12:33 UTC · Codex / Advisory: current internal reference pack at
`platform_docs/reference_pack_2026-10-26/` (entry: READ_ME_FIRST.md), plus ZIP in platform_docs.
Live production now reports main/6394c039749a, Claude Sonnet 4.6, password gate on; older release
statements below remain historical. Read-only Neon: production 49 base tables/16 views, dev 56/16;
818 sources, 799 molecule rows, 3,129 experts, 45 claims, 3,650 properties. Dev demo remains the
3-document frozen import (3,418 entities/4,164 relations/7,582 vectors), while local LightRAG now
has 5,101 nodes/6,240 edges. Added one-pager, actual UI screenshot, current architecture/schema
visuals and full inspected schema metadata with curated source docs. No model/benchmark run,
production retrieval audit, Git/deployment or data changes. Docker not restarted._

_2026-10-20 21:33 UTC · Codex / Data: GROBID annotation failure for `Meat Flavour - NAMQ2.pdf`
was caused by an image-only scan (41 pages, no text), not MCP health. Local OCR derivative
`Meat Flavour - NAMQ2 - searchable.pdf` saved in Downloads and ignored `data/grobid/ocr/`.
Full-text extraction and reference annotation both now return HTTP 200; TEI: 91 body paragraphs,
132 references. Original preserved; OCR accuracy not adjudicated; no LightRAG/Neon writes._

_2026-10-20 21:19 UTC · Codex / Data + Full-Stack: connected GROBID to the existing
Codex `MCP_DOCKER` gateway/profile `meatcode`, preserving Playwright. Local adapter:
`pipeline/grobid/mcp/`; three tools: status, PDF listing, PDF parsing. Exact read-only input bind:
`/Users/lior/LightRAG/inputs`; writable output: ignored `data/grobid/mcp/`. Config backed up;
startup timeout and scoped bind allowlists set. Actual gateway tool calls passed: healthy 0.8.2,
PDF listing and parsing to valid TEI (26 paragraphs, 62 refs) plus 22,096-character cleaned body.
Five unit tests passed. No Neon/LightRAG/production writes. Reload MCP or restart Codex to load
these tools into the current chat; setup instructions in `pipeline/grobid/mcp/README.md`._

_2026-10-20 21:03 UTC · Codex / Full-Stack: configured existing GROBID 0.8.2 Docker image as
`meatcode-grobid` at **http://localhost:8070** with loopback port binding and health check.
Two duplicate unexposed processes stopped; their containers preserved. Compose file:
`pipeline/grobid/compose.yaml`; launcher: `Release Center/start-grobid.command`; usage:
`pipeline/grobid/README.md`. Health/version passed; one local PDF parsed to valid 96,780-byte
TEI XML in 27.64s. Smoke files under ignored `data/grobid/`. No Neon/LightRAG/production changes.
Docker MCP Toolkit v0.43.3 confirmed installed; no MCP connection/configuration was changed._

_2026-10-20 20:54 UTC · Codex / Advisory: added `platform_docs/LIGHTRAG_CURATION_AND_SCALING.md`.
Current local files show 4 processed / 1 failed document status records, 206 chunks, 3,759 nodes
and 4,531 undirected edges (not a Neon refresh). Of the nodes, 1,687 are typed person; 122 of
141 person-linked chunks contain bibliography XML markers. Only 94 nodes and 2 edges have
evidence from multiple documents; this is a reuse diagnostic, not a complete connection-quality
metric. Recommend clean TEI section extraction, a separate bibliography network, canonical IDs,
individual condition-specific claims, measured M2 review, and bounded graph retrieval. Proposal
only; no graph, code, schema, deployment, score-cutoff policy or external system changed._

_2026-10-18 11:57 UTC · Codex / Design: cleaned the attached architecture picture’s connectors and handwritten annotations; saved `platform_docs/diagrams/MeatCODE-Architecture-Clean-Arrows.png` and a Downloads copy. Visual-only edit; system status unchanged._

_2026-10-18 11:48 UTC · Codex / Design: exported the current architecture overview as `platform_docs/diagrams/MeatCODE-Architecture-8K.png` (7680×4320); copy saved to Lior’s Downloads. Diagram content and system status unchanged._

_2026-10-18 10:14 UTC · Codex / Data-RAG-Design: at Lior’s explicit request, removed the
provisional relevance-score gate from local Oracle FTS, both eval runners, and Papers browser’s
Oracle-eligibility labels/filters. Applied additive migration **0015** to **Neon dev only** and
imported the existing LightRAG graph into `lightrag_demo`: **3 documents, 194 chunk metadata rows,
3,418 entities, 4,164 relations, 7,582 vector(1024) embeddings, 8,932 evidence links**. Original
BGE-M3 embeddings reused; raw chunk text and scientific source/property tables unchanged. Exact
DOI→source IDs 275/833/857; immutable batch `lightrag-0fea952f5db82becdc87501f`. Second import
returned `verified_existing`, with no duplicates. Local Oracle on `localhost:8000` now uses dev
vector/graph retrieval; authenticated dev `/api/kg-demo/status` and `/search` added. A semantic
query returned 15 evidence items from source 275 in `vector_graph` mode; `/api/ask` retrieved the
same evidence but Claude returned **401 invalid x-api-key**. Lior chose to keep Claude configured
and repair credentials; no Qwen/provider switch. Thirteen tests, compilation and JS syntax checks
pass. Live evidence saved under ignored `data/benchmarks/2026-10-18-pilot/`. Added minimal icon-led
overview SVG/PNG, detailed flow and interactive viewer under `platform_docs/diagrams/meatcode-rag-demo-*`.
Implementation, arrow contract and self-service instructions: `platform_docs/LIGHTRAG_DEMO_IMPLEMENTATION.md`;
import/start script: `Release Center/demo-lightrag.command`. Production, credentials, Asana and
Git/release state unchanged. Local code still needs publication through the normal dev workflow._

_2026-10-18 09:53 UTC · Codex / Advisory: revised the architecture visual into an icon-led,
low-text overview with no component-card borders and no benchmark panel. Connector routes were
moved away from icons and labels. Per Lior's correction, the protected artifact vault is labelled
as Neon storage; the earlier advisory local-vault recommendation is superseded in that respect.
Cloud storage of exact or publisher-controlled passages still requires explicit rights, retention,
access, backup, and deletion approval. No implementation or external system changed._

_2026-10-18 09:47 UTC · Codex / RAG: added `analysis/rag_eval/PROTOCOL.md`,
`benchmark.py` and `test_benchmark.py`: controlled direct/vector/graph and cross-model protocol,
ingestion/retrieval/answer metrics, proposed thresholds, results template, local inventory, frozen
smoke packet preparation and real Oracle SSE capture. Five tests pass; comparative runs, model
adapters, reviewed gold, import/schema and serving integration are not implemented. Local ignored
packet: `data/benchmarks/2026-10-18-pilot/`. LightRAG inspected read-only: 3 processed / 3 failed
documents, 194 chunks, 3,418 nodes, 4,164 edges, 1,024-dimensional vectors, no dangling graph chunk
references detected. Exact DOI matches to Neon dev sources **275/833/857** verified; relevance
**55/32/38**, so all three fail the existing Oracle ≥60 gate. A shared approved corpus is needed
before a fair controlled comparison. Neon dev inspected read-only: pgvector absent; 818 sources,
319 pass relevance. Latest Architecture chat and live benchmark task inspected. No schema, data,
deployment, extraction workspace or Asana changes; no paid model run._

_2026-10-18 09:43 UTC · Codex / Advisory: Lior selected the pilot model split: local Qwen
extraction (M1), local custom validation/curation plus deterministic checks (M2), and cloud-hosted
GPT reasoning over approved evidence (M3), with Neon authoritative and graph/vector layers derived.
Added `platform_docs/ENGINEERED_RAG_ARCHITECTURE.md` plus editable SVG and PNG under
`platform_docs/diagrams/`. The diagram separates controlled ingestion, governed knowledge,
interactive serving, and the apples-to-apples benchmark/scale gate. This is an architecture artifact,
not an implementation. No Asana, Neon, schema, deployment, production data, or external system changed._

_2026-10-18 08:56 UTC · Codex / Advisory: added
`platform_docs/LOCAL_CLOUD_HOSTING_DECISION.md` and the supporting
`reports/MeatCODE local cloud architecture.md`. The proposed hybrid v1 keeps Neon authoritative and
Render stateless, while rights-sensitive PDFs, GROBID, exact passages, and restricted extraction
remain local; retrieval and graph systems stay rebuildable projections. This is awaiting Lior and
Daniel/Yochai approval and is not implemented. No Asana task, Neon data, schema, deployment, or
external system changed._

_2026-10-17 20:42 UTC · Codex / Advisory: added
`platform_docs/DATA_PROCESSING_ARCHITECTURE.md`, a concrete governed batch design for local parsing,
parallel evidence extraction, identity resolution, checking, deterministic validation, dev-first
Neon admission, retrieval, audit and failure handling. The architecture recommendation is complete;
implementation still requires the 10-paper pilot and the evidence listed in that record. No schema,
database, deployment, production data, Asana task, or external system was changed._

_2026-10-17 12:29 UTC · Codex / Advisory: Lior confirmed continued use of `Bokipr0/meatCODE`.
Local checkout already points to that remote on `dev`. Folder/connection review recorded in
`platform_docs/GITHUB_READINESS.md`; no remote configuration, publication, or live-system changes.
The external-system status elsewhere in this file remains verified as of 2026-10-11._

The 2026-10-11 handoff + context-sync work: `START_HERE.md`, `platform_docs/{SYSTEMS_MAP,SYSTEM_SNAPSHOT,DECISIONS,PEOPLE,ASANA_SNAPSHOT}.md`, `orchestration/` (snapshot script, skills, setup guide, memory seed), meeting notes, this file. → Lior: `deploy-dev.command`.


## 4. Data layer (numbers: `SYSTEM_SNAPSHOT.md`)

- **Literature:** 818 sources, all tagged (pathway/method/matrix/compound class/sensory/study type), one `main_claim` each; **319** pass the Oracle gate. Tailored abstracts: 30.
- **Molecules:** 798 non-junk · 590 with InChIKey (PubChem) · 568 CAS · 3,650 provenanced property values (RDKit-derived + 110 literature odour thresholds) · 2,263 molecule↔odour links. **Precursor view (`v_precursors`) is empty.**
- **Experts:** 3,129 records; enrichment thin (`research_field` ~17).
- **The gap:** **23** paper↔molecule links; `experiments`, `processes`, `reaction_participants` = 0; no property value cites a paper yet.


## 5. Open problems ❌ (verified 2026-10-11)

1. **B2 — quarantine write-back.** 4 sources quarantined on 2026-07-07/08 (ids 252, 308, 341, 380) still have `relevance_llm` 62–75, so the Oracle can still cite them. And the data-quality audit loop **hasn't run since 2026-07-08** (40 sources audited of 818).
2. **Paper↔molecule bridge** (23 links) — blocks the knowledge graph, white-space map and condition-aware answers. Plan: 10-paper GROBID extraction pilot into the existing tables (`RAG_BUILD_VS_BUY.md`).
3. **RAG quality** — baseline groundedness **3.4** · citation accuracy **4.8** · coverage **4.1** /10 (8 questions, zero invented citations). No comparison vs generic AI tools yet (Asana task due 2026-11-06).
4. **Publisher rights unresolved** (Asana, Daniel, overdue 2026-10-08). Written position (Daniel, 2026-09-07): extract facts with provenance, never store/reproduce/share full text. Don't open external access to publisher-derived content until resolved.
5. **Single point of failure** — Neon, Render, GitHub and the Anthropic key all sit on Lior's logins (Yochai flagged 2026-09-20; Asana continuity task closed 2026-09-21 — confirm what access Daniel/Yochai actually have).
6. **Stale docs** — `MVP_BOARD.md` and `TEAM_BROADCAST.md` (1 Sep) still frame the end-of-August demo; superseded by this file + Asana.


## 6. What's next (from Asana + this audit)

Lior's 19 open Asana tasks and the evidence for each are in `ASANA_SNAPSHOT.md` §3. The highest-leverage items now:

1. **Close B2** — write quarantine verdicts to `relevance_llm` and re-run the audit loop (Data Engineer).
2. **Promote dev** (Papers browser + Backups button) once reviewed on staging.
3. **Choose tool stack** (overdue 2026-09-30) — the recommendation exists (`RAG_BUILD_VS_BUY.md`); needs Daniel/Yochai sign-off.
4. **10-paper extraction pilot** → re-run the RAG eval against 3.4 / 4.8 / 4.1.
5. **Prepare the 10–15 min architecture overview for Rebecca** (asked by Daniel, 2026-10-11).


## 7. Upcoming (from Gmail/Calendar, 2026-10-11)

- **2026-10-12 13:00** — Yochai meets Prof. Yoav Ram (TAU, Sherman 328); Lior invited. Ram hasn't replied to Lior's 2026-10-05 email.
- **Next 2 weeks** — Daniel scheduling: WUR simulator-validation meeting (Pablo, Prof. Fogliano, Bei Wang) and an AKA Foods Atlas pilot call.
- **Weekly Core Sync** — Sundays 12:30 (Yochai, Daniel; Lior optional).
