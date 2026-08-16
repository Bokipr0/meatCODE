# 📣 TEAM BROADCAST — MeatCODE

_From: Project Coordinator (with Lior) · As of: **2026-08-16**_

> Standing notification channel for the whole agent team. The Coordinator refreshes this whenever there's
> progress every agent should know. **Read this at the start of your session** (after CLAUDE.md +
> PROJECT_STATE.md). Full history is in `AGENT_UPDATE_LOG.md`; this is the short "what you need to know now."

---

## 🧩 2026-08-16 (pm) · ORACLE CAPABILITY DEMOS + LIVE CORPUS FILTER + FIRST-CLASS ANALYTICS — landed in the repo, awaiting deploy-dev
A 4-lane parallel run shipped Lior's demo-polish sprint (full detail: AGENT_UPDATE_LOG.md top entry; state: PROJECT_STATE.md). What every agent must know now:
- **NEW `GET /api/corpus?phase=<juice|lipid|analytics>&topics=<slugs>`** is the corpus-filter endpoint — per-slug + `phase_topics` live counts, deduped `totals`, ≤50 rows. It drives the Research sub-topic chips, the new Analytics scene, and the Oracle "explore the lipid corpus" demo. Additive; other UIs may ignore it.
- **NEW `POST /api/compare`** (1–2 molecule profiles side-by-side; corpus misses return `in_corpus:false`) + **`GET /api/molecule-profile/{id}`** (alias of `/api/molecules/{id}`). These power the inline Oracle "Compare molecules" demo (renders inside the chat — never navigates away) — a real backend-backed version of screen-flow **Flow 2 (Comparison)**.
- **Research chips are live:** `#research-sub` juice/lipid sub-cards carry `data-topics` (real taxonomy slugs — see `db/research_chip_map.json`), toggle multi-select, and re-query the corpus on every change; 0-count chips grey out. **UI/UX: reuse this pattern when you touch Research — don't re-hardcode counts.**
- **Analytics is a first-class `#analytics` scene** now (not Dev-Area-only), reachable from the Research "Analytics" tile. Still **preview** on real-but-partial data (GC-MS = Meaty Volatile Library real; others thinner) — keep the honest labels.
- **The 4 Oracle starter chips are capability demos** (Maillard route · lipid corpus · simulate · compare). The **simulate demo is the MOCK path** (`synthetic:true`) — the synthetic banner is mandatory; never present it as chemistry.
- **The `dev_banner` "DEV · staging" ribbon was removed** from the mockup (Lior's request); the `dev_banner` flag is now inert (cleanup follow-up).
- **Open decision (Lior):** `/api/corpus` counts are **ungated**; Data recommends the `relevance_llm≥60` Oracle gate so Research and the Oracle count the same corpus (one-line change; MVP_BOARD decision #9).
- **Still the critical path: B1 (deploy) + B2 (quarantine write-back).** These demos are invisible to reviewers until B1 lands.

## 🧪 2026-08-16 · MAILLARD SIMULATOR — architecture settled, backend live in mock mode
Lior's Maillard chemistry simulator now has a designed path into MeatCODE. Full design of record: `platform_docs/MAILLARD_INTEGRATION.md` · wire contract: `server/maillard/CONTRACT.md` · journey wireframe: `UI-UX Designer/maillard_sim_wireframe.html`.
- **Hard constraint every lane must respect:** production is Render `runtime: python` and **cannot spawn Docker**. The simulator must be its own `runtime: docker` service (or a local dev container), reached through the same-origin **`/api/simulate`** proxy — never called directly from the browser.
- **`POST /api/simulate` · `GET /api/simulate/{job_id}` · `GET /api/simulate/health` exist now**, behind auth + the `maillard_sim` flag (OFF in prod → 404). Default `MAILLARD_MODE=mock`: deterministic, and every response is stamped `synthetic:true` with a disclaimer. **Never present mock output as chemistry.**
- Submit→poll, not WebSocket: fast runs return inline (≤8 s), slow ones return `202` + a job id.
- **⚠️ Known mismatch to fix before building the UI:** the wireframe uses **mM**; the contract accepts only `mg, g, mmol, mol, ppm, ppb, percent`, and the key is `ph` (lowercase). Align these first or every submit 400s.
- **Scope discipline:** Advisory's recommendation is **Phase 1 only, flagged, on demo data** for 31 Aug; prod `#simulate` keeps its synthetic label. **B1 (deploy) and B2 (write-back) still outrank this** — a simulator inside an undeployed app demos to nobody.

## 🚀 2026-08-15 · 5-AGENT RUN LANDED — Dev Area · consensus · canonical IDs · eval baseline · Oracle-first
All five lanes shipped Lior's task list in one parallel run (full detail: AGENT_UPDATE_LOG.md top entry; state: PROJECT_STATE.md). What every agent must know:
- **Dev Area exists** (`app/dev/`): hub + KG screen + fingerprint placeholder + analytics zone, reachable from a new topbar button **gated behind `ff-dev_area`** (OFF in prod — rules in `platform_docs/DEV_AREA.md`). Placeholders must say they're placeholders.
- **Landing flipped back: Oracle is home again.** Nav = Oracle · Research · Simulate. The v12.6/12.7 "Home is the landing" notes below are now historical.
- **`/api/ask` gained `event: consensus`** (agree/oppose/neutral per source) + per-source `claims` in the sources payload — additive, UIs may ignore. **UI/UX: a consensus chip ("N support · M oppose") is the natural next render.**
- **Molecules are getting canonical IDs** (CAS 110 from MVL, PubChem CID pilot 20/20 — scaling next). Check `is_junk` before using molecule rows. 4 chemistry fields exist but are NULL until a curation source is chosen — don't invent values.
- **RAG eval baseline is on record** (`analysis/rag_eval/`): groundedness 3.4 · cite-acc 4.8 · coverage 4.1 — zero invented citations, but depth largely uncited-general-knowledge. Improvements must beat these numbers.
- **Open Lior decisions:** topic aliases (off-note / plant-protein / sensory → existing topics, ~239 papers) · GC-MS reference-data source · usage log · benchmark gold set. **B1 (deploy) + B2 (quarantine write-back) are still the critical path.**

## 🧭 2026-08-15 · Screen-flow design pass landed (board A2) — design only, in `UI-UX Designer/`
The **6 cross-navigation screen flows** (Oracle↔Data · Data↔Oracle · Protocols→Data · Sim↔Data) are now designed: an interactive **wireframe** (`UI-UX Designer/screen_flows_wireframes.html`) + a **journey/IA spec** (`UI-UX Designer/SCREEN_FLOWS_user_journeys.md`). **No live-mockup or deployed-file changes** — review candidates for Lior. Advances board **A2**.
- **Architectural takeaway for every lane:** all six flows are one **"entity + context handoff bus"** — capture→stash→route→consume + breadcrumb. Generalize the existing `mc_mol_focus_id` into `mcHandoff()/mcConsumeHandoff()`; it's the shared dependency of all six.
- **Build order when greenlit:** P0 = bus + Flow 3 (Data→Oracle, zero backend) + Flow 1 (Oracle→Raw table). Flow 2 (Comparison) = client-side over `/api/molecules/{id}` behind a `data_compare` flag. **Flow 4 (Protocols→Data) is design-only until `/api/protocols` + a protocols table exist (Data Eng / Full-Stack).** Flows 5/6 (Sim↔Data) preview-gated (sim is hardcoded, emits names not ids).

---

## 🚨 2026-07-23 · NEW TASK BOARD + 3 THINGS THAT CHANGE HOW YOU WORK · READ BEFORE ANYTHING ELSE

Lior + Daniel set the end-of-August task list. **Open deliverables now live in `MVP_BOARD.md`** (repo root):
8 MVP lanes · 5 action items · 2 blocking gaps, each with owner, status and critical-path marking.
**Read `MVP_BOARD.md` after PROJECT_STATE.md and update your rows when you finish something.**

### 1. ✅ DECIDED — GC-MS (J2) ships as an **honest preview**
The long-open "P0 vs preview?" question is **answered: preview.** Build the fingerprint + by-cut comparison
on **clearly-labelled reference data — not a live analytical engine.** This matches the team's own
recommendation and is what makes 31 Aug realistic. Do **not** scope a real GC-MS pipeline for August.
⚠️ Still open (gates the work): **where do reference profiles per cut come from** — WUR, literature-mined,
or synthetic-and-labelled? Don't guess; flag it to Lior.

### 2. 🔄 PROCESS CHANGE — `deploy.command` is RETIRED. Dev and production are now split.
Every "run `deploy.command`" instruction elsewhere in this repo is **stale**. The new flow:
- Work happens on the **`dev`** git branch (never `main`).
- **`deploy-dev.command`** → pushes to the private staging site (`meatcode-dev`, own Neon dev DB, own key).
- **`promote-to-prod.command`** → the only path to the public site (shows a diff, asks for `yes`, tags the release).
- **`rollback-prod.command`** / the Release Center's Version history → revert production to any previous release.
- Full runbook: `platform_docs/TWO_ENVIRONMENT_WORKFLOW.md`.

### 3. 🎛️ NEW — feature flags. Ship unfinished work safely.
`Release Center/features.json` holds one entry per feature with a **dev** and a **prod** boolean; the app turns
each ON flag into a `body.ff-<key>` class. Lior toggles them in the **Release Center** (`release-center.command`,
or press **H** in the dev app) — full guide: `platform_docs/RELEASE_CENTER.md`.
**Convention going forward: anything half-built or "preview" ships behind a flag, ON in dev / OFF in prod.**
That explicitly includes the **GC-MS preview**, the simulation demo, and the knowledge-graph view.

### 🎯 Your lane's next move (from `MVP_BOARD.md`)
| Lane | Do this next | Why |
|---|---|---|
| **Full-Stack** | **B1 — deploy the v12.1→v12.7 backlog** (`deploy-dev` → verify → `promote-to-prod`) | **[CRITICAL PATH]** A month of finished work is not live. Nothing on the board is demoable until this lands. Then: GC-MS preview endpoints (A1/A3) behind a flag, `/api/protocols`, and the usage-log decision (lane 7). |
| **Data Engineer** | **B2 — close quarantine → `relevance_llm` write-back**, then back-tag + retrievability count | **[CRITICAL PATH]** Same problem as MVP lane 2 ("Database quality"). Retrieval still gates on unreviewed scores. Then: define the **A1 fingerprint schema** with Full-Stack. |
| **UI/UX Designer** | **A2 — scenario & user screen-flow creation** | Highest leverage on the board: it decides what must exist by 31 Aug **and what doesn't**. Then: lock ONE design system, GC-MS preview UI (flagged), J3 knowledge-graph view, honest preview labels. |
| **Algorithm Expert** | **A4 — RAG development → the benchmark harness** (gold set vs GPT/Claude/Perplexity) | The only evidence for success criterion 1, and the thing Daniel can actually show. |
| **Advisory** | Mid-Aug **scope-freeze gate** + P1 validation protocol + a reviewer-facing "what this is / what it isn't" doc | Lane 8 is thin for outsiders; mid-Sept validation needs it. |

**Sequencing note:** A1 (fingerprint schema) blocks A3 (by-cut comparison); A5 (knowledge graph) blocks MVP lane 5
(white-space mapping). Don't start the dependents until the parent lands.

**Open decisions for Lior + Daniel** (don't assume — ask): GC-MS reference-data source · do users upload real
GC-MS data in v1 or pick a bundled sample? · anonymous usage/question log, yes or no? · greenlight the benchmark gold set?

---

## 🎯 PROJECT GOALS — the MVP north star (broadcast 2026-07-22) · READ THIS FIRST
Lior set the **MVP definition + 5 user journeys**. Full doc: **`docs/MeatCODE_MVP_Definition_and_User_Journeys.md`** · per-lane gap analysis: **`docs/MVP_ALIGNMENT.md`**. This is now the bar every lane is judged against.

**Objective:** a credible, source-backed prototype — **internal demo by end of August**, refined early September, opened to selected **external P1 expert users for validation by mid-September**.

**5 success criteria:** (1) Scientific Oracle — source-backed, **benchmark-competitive vs general AI**; (2) GC–MS Interpretation — upload → molecules → sensory → pathways → insight; (3) Knowledge Discovery — literature/molecules/pathways/protocols/experts/orgs; (4) Research Planning — question → literature/ideas/protocols/gaps/collaborators; (5) Collaboration — experts/orgs.

**Where the 5 journeys actually stand (honest):**
- 🟢 **J1 Oracle** — working skeleton (grounded, cites real sources).
- 🔴 **J2 GC-MS** — hollow (no data / UI / endpoint / algorithm). Team recommendation: **mark PREVIEW / Phase-2**, not a mid-Sept P0.
- 🟡 **J3 Literature** — partial (Database + molecule-detail; no knowledge-graph view yet).
- 🟠 **J4 Research Planning** — design-only (static funnel, no protocols backend).
- 🟢 **J5 Expert Discovery** — working (Map + filters; experts under-enriched).

**The P0 spine — do these, in order:**
1. **Data Engineer** — close **corpus trust**: quarantine→`relevance_llm` write-back + back-tag the ~489 untagged (39% gate →) + run the retrievability count. *Unblocks everything; you can't benchmark an ungoverned corpus.*
2. **Algorithm Expert** — build the **benchmark harness** (30–50 expert-authored gold Qs, MeatCODE vs GPT/Claude/Perplexity, blind-rated). The only proof of criterion 1. Then reranking → pgvector hybrid.
3. **Full-Stack Engineer** — **DEPLOY the backlog** (a month of committed work — Oracle v11 → v12.7: Home, detail pages, `molecules/{id}`, suggestions, Inventory — is NOT live) + verify via `/api/version`; then scaffold the GC-MS upload path (preview) + `/api/protocols`.
4. **UI/UX Designer** — lock **ONE** design system (promote/merge the v8/v9/lean/research-screenflow fragments), add the **J3 knowledge-graph view**, reframe Research into a **J4 planning flow**, and label J2/J4/Simulate as honest previews.
5. **Advisory** — P1 onboarding/validation protocol + a **mid-Aug scope-freeze gate** (Daniel signs off the corpus + the credible-vs-preview split).

**Open decisions for Lior + Daniel:** Is GC-MS (J2) in scope for mid-Sept, or a labeled Phase-2 preview? · Greenlight the benchmark eval? · Close the quarantine write-back now? · Run `deploy.command` to land the backlog?

⚠️ **Top risk:** the working lanes sit on an **ungoverned corpus** (39% pass the gate; Daniel's quarantines don't block retrieval) and the Oracle's "benchmark-competitive" claim has **no measurement yet**. Corpus trust + the benchmark are the two things that make P1 validation real.

---

## 🆕 Latest — 2026-07-22 (read PROJECT_STATE + AGENT_UPDATE_LOG for detail; the sections further down predate this)
The product surface moved several times today — trust PROJECT_STATE.md over this older body:
- **2026-07-22 12:17 · nav trim + wider answer + related-molecule chips (PROJECT_STATE "Follow-up v12.5").** Parallel UI/UX + Full-Stack run: **Database + Map removed from the top nav** (screens kept, reachable via other journeys); **Oracle answer widened** (760→1080px); **"Related molecules" chips** at the end of each answer from a **new `GET /api/molecule-suggestions`** endpoint. Verified (mockup `node --check`, server `py_compile`, contract matches). **Awaiting `deploy.command`.**
- **2026-07-22 · data-audit "AI Review" layer** on the recurring snapshot (PROJECT_STATE) — flags that enrichment/scoring is still largely unwritten (composite_score=0, tags 26–74%).
- **2026-07-21 · lean-v1 design port (v12.4)** + **advisory Oracle-notes pass** (ORACLE eyebrow removed, new subtitle, sources moved below/blue/collapsible). All awaiting deploy.
- ⚠️ **Multiple sessions keep editing `app/meatcode_mockup.html` un-committed between hand-offs** — commit/push (or hand off through the Coordinator) more often to avoid rebasing/merge churn.

---

## Where we are, in one line
The Oracle is **live, private, always-on, and genuinely grounded** — it retrieves from our own corpus and
cites real sources — and just gained a round of UX polish (dictation, chat history, honest status copy).
The open frontier is **corpus trust**: only ~39% of sources pass the relevance gate, and Daniel's
rejections still don't block retrieval.

## ✅ Latest progress (newest first)

**2026-07-20 — Oracle v11, a 3-agent parallel run**
- **UI/UX Designer** — four features shipped in the mockup: **dictation** (Web Speech API mic, feature-detected
  so unsupported browsers see no dead control), **bigger Oracle-only save icon** (34px target), **rebuilt
  sidebar** with **Pinned above History** (localStorage-persisted, dedupe + re-bump, 25/list cap, click
  re-populates the question), and a **copy scrub** — "Searching the database and asking Claude…" →
  **"Digging the MeatCODE database…"**, with **zero user-facing model mentions left**.
- **Data Engineer** (scope completed by Coordinator after the agent was interrupted) — added an additive
  `event: status` (`retrieving` → `answering`) to `/api/ask`, moving the SSE headers ahead of retrieval so the
  "digging" phase is *honest* rather than a guess. Scrubbed the raw API error to a plain-language message
  (real diagnostic still goes to stderr/Render logs).
- **Advisory** — `docs/oracle_chat_history_design.md`: because the site sits behind ONE shared Basic Auth
  credential, the backend has **no per-user identity**, so localStorage is the *correct* architecture, not a
  shortcut. Documents its honest limits + privacy exposure; **defer real accounts past the validation year**.

**2026-07-20 — expired sign-in diagnosed.** The bare "Load failed" after ~2 weeks idle was just an expired
cached Basic Auth login (server, Neon, key and model all verified healthy). Now reports in plain language.

**2026-07-08 — the grounding milestone.** `/api/ask` went from `sources: []` (zero retrieval, answering from
training) to real retrieval: top-6 via `ts_rank_cd`/`websearch_to_tsquery`, gated to citable +
`relevance_llm ≥ 60`, two-tier AND→OR fallback (0-source misses **10/14 → 0/14**), grounded + inline-cited,
refusing when the corpus doesn't cover the question. Plus relational tagging live (146 tags / 541 links),
corpus relevance verified vs the taxonomy bible, and the grounding/relevance decision docs.

**2026-07-08 — infra.** Render moved to Starter (always-on, no spin-down) and put behind an optional
`SITE_PASSWORD` Basic Auth gate. The every-2-days scheduled task was repurposed from the LLM audit to a
**raw, no-interpretation Neon snapshot** (`pipeline/export_snapshot.py` → 5-sheet xlsx).

## 📊 Headline numbers
818 sources · **790 citable (96.6%)** · 329 tagged (40.2%) · **226 high-confidence off-topic (27.6%)** ·
only **319/818 (39%)** pass the `relevance_llm ≥ 60` Oracle gate.

## ⚠️ Top risk — the quarantine write-back gap (still open)
Confirmed quarantines write **only to `source_audits`, NOT to `sources.relevance_llm`** — so a source Daniel
rejects is **still retrievable and citable by the Oracle**. Close this before any external/WUR demo.

## 👉 Your next move, by agent
- **Data Engineer** — close the quarantine→`relevance_llm` write-back; finish tagging (**329/818**) then
  re-run `promote_tags.py`; narrow the `sensory` (93.2% off-topic — human-olfaction contamination) and
  `off-note` (48.8%) ingest queries; keep pushing the corpus toward 1,000+.
- **Algorithm Expert** — real-browser test of the grounded Oracle; reranking over a wider pool;
  semantic/embedding search as the corpus grows; hand-label the retrieval gold set.
- **UI/UX Designer** — dictation needs a real-browser test (Chrome/Safari, HTTPS or localhost; Firefox
  unsupported by design); decide recognition language (`en-US` hardcoded — Hebrew/toggle?); v9 vs canonical
  are byte-identical on JS, so a promote stays deploy-safe.
- **Advisory** — carry the chat-history/privacy disclosures into the UI (two device-local lines + a visible
  Clear-history control); keep the Prediction/Simulate surface framed as hypothesis-generation.

## 🙋 Needs Lior / Daniel
- **Lior:** run `deploy.command` so v11 + the sign-in fix reach the live site · decide the
  quarantine→`relevance_llm` write-back · promote v9 → canonical?
- **Daniel + Lior:** **decide whether to add an anonymous server-side question log** (question + timestamp +
  retrieval hit/miss, no identity) — Advisory calls it the single best validation-year evidence source, but
  it carries privacy weight and needs UI disclosure.
- **Daniel:** review `docs/audits/relevance_check_2026-07-08.xlsx` (226 off-topic + quarantine IDs
  #252/#308/#341/#380) · sign off tagging taxonomy v0.1 + hub architecture v0.1.

## 🧭 Working reminders
Canonical repo = `meatCODE/` (read CLAUDE.md → PROJECT_STATE.md → this broadcast). Neon = data · Asana =
tasks. Deploy via `deploy.command`. Site is behind Basic Auth — an expired login looks like "Load failed";
just refresh and re-enter the password. Every agent stamps files it edits + appends to `AGENT_UPDATE_LOG.md`.
