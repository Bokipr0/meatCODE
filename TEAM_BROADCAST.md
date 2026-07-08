# 📣 TEAM BROADCAST — MeatCODE

_From: Project Coordinator · As of: **2026-07-08 ~10:10 UTC**_

> Standing notification channel for the whole agent team. The Coordinator refreshes this whenever there's
> progress every agent should know. **Read this at the start of your session** (after CLAUDE.md +
> PROJECT_STATE.md). Full history is in `AGENT_UPDATE_LOG.md`; this is the short "what you need to know now."

---

## Where we are, in one line
MeatCODE is **live on Render**, the corpus is **quality-audited and now relationally tagged**, and the
product mockup has a **promote-ready v9** — but the **Oracle still isn't retrieving from our library yet**,
and that's the team's single highest priority.

## ✅ Latest progress (newest first)
- **Relational tagging system is live** (Data Engineer + Algorithm Expert): unified `tags` + `source_tags`
  junction (migrations 0005/0006), `promote_tags.py` → **146 tags, 541 links across 72 sources**. The
  "connect sources by shared tags" query works live. Usage/retrieval guide: `docs/tagging_relational_guide.md`.
- **v9 mockup ready** (UI/UX Designer): v8 polish forward-ported onto the newer canonical (Database scene,
  Simulate/Prediction, Oracle history, live company card). Deploy-safety diff verified — cosmetic only,
  API contract byte-identical. Awaiting Lior's OK to promote → `app/meatcode_mockup.html` + redeploy.
- **Data-audit loop running** (scheduled): every 2 days, 20 sources, oldest-and-riskiest-first → xlsx for
  Daniel. Latest run 2026-07-08: 10 keep / 9 review / 1 quarantine.
- **Advisory decision docs added**: `DECISION_grounded_answers_and_relevance.md` (how grounding + the
  relevance gate + Daniel's sign-off fit together) and `daniel_review_workflow.md` (Daniel's xlsx loop).
- **Earlier this phase**: corpus 496→818 (scored, FTS, taxonomy bible); expert map live + filterable with
  per-expert actions; backend consolidated to the single `meatcode_server.py`; deployed on Render.

## ⚠️ Top priority — read this
The live Oracle **`POST /api/ask` currently hard-codes `sources: []` → it retrieves NOTHING** and answers
from Claude's general training. `sources.search_vec` (FTS) is populated but no live code path queries it.
Grounded, cited answers are the MVP promise, so wiring retrieval is the #1 job — start from
`docs/tagging_relational_guide.md` §3.1 (tag hard-filter + FTS).

## 👉 Your next move, by agent
- **Data Engineer** — finish `tag_sources.py` (only **72/818** tagged in Neon), then re-run `promote_tags.py`
  to pick up the rest; keep pushing corpus toward 1,000+; normalize `experts.country`.
- **Algorithm Expert** — wire `/api/ask` retrieval (tag filter + FTS + rerank → grounded, cited answer);
  hand-label `analysis/retrieval_gold.csv` and run the eval.
- **UI/UX Designer** — hold for Lior's go on promoting **v9**; then promote + redeploy via `deploy.command`;
  reconnect Claude-in-Chrome for screenshot verification.
- **Advisory** — grounding/relevance decision + Daniel workflow are posted; keep PROJECT_STATE consistent
  as retrieval lands; keep framing the Prediction/Simulate surface as hypothesis-generation, not authority.

## 🙋 Needs Lior / Daniel
- **Lior:** promote v9? · `ANTHROPIC_API_KEY`/deploy for live Oracle · finish the local tagging run.
- **Daniel:** sign off the audit xlsx (keep/review/quarantine) + tagging taxonomy v0.1 + hub architecture v0.1.

## 🧭 Working reminders
Canonical repo = `meatCODE/` (read CLAUDE.md → PROJECT_STATE.md → this broadcast). Neon = data · Asana =
tasks. Deploy via `deploy.command`. Every agent stamps files it edits + appends to `AGENT_UPDATE_LOG.md`.
