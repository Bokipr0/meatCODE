# 📣 TEAM BROADCAST — MeatCODE

_From: Project Coordinator · As of: **2026-07-20 ~13:10 UTC**_

> Standing notification channel for the whole agent team. The Coordinator refreshes this whenever there's
> progress every agent should know. **Read this at the start of your session** (after CLAUDE.md +
> PROJECT_STATE.md). Full history is in `AGENT_UPDATE_LOG.md`; this is the short "what you need to know now."

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
