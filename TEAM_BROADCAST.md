# 📣 TEAM BROADCAST — MeatCODE

_From: Project Coordinator · As of: **2026-07-22 22:15 UTC**_

> Standing notification channel for the whole agent team. The Coordinator refreshes this whenever there's
> progress every agent should know. **Read this at the start of your session** (after CLAUDE.md +
> PROJECT_STATE.md). Full history is in `AGENT_UPDATE_LOG.md`; this is the short "what you need to know now."

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
