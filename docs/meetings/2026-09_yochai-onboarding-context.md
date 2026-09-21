# Yochai onboarding — meeting context (Sep 2026)

_Last updated: 2026-09-02 · meeting context pack · both summaries captured from Wispr Flow shared notes (owner: Lior Teper). Transcripts are access-restricted to owner/invitees, so these are from the Flow Summaries, not verbatim transcripts. Original notes were in Hebrew; rendered here in English._

**Why this file exists:** running context on onboarding **Yochai Maytal** as a MeatCODE collaborator — what was discussed, what was decided, and (especially) the links/materials Lior promised to send Yochai so he understands the project scope. Read this before the next Yochai-related conversation.

---

## Meeting 1 — "MeatCODE sync & Yochai kick-off" (2026-09-01)
Attendees: Lior Teper, Yochai Maytal. (Full standalone note: `docs/meetings/2026-09-01_meatcode-sync-yochai-kickoff.md`.)

**Key points**
- Kick-off with Yochai: scientific background (reverse-engineering meaty flavor), MVP goals, niche audience, live platform demo.
- **Launch pushed end-September → end-October** (better prep + case studies). Target: updated Asana work plan with clear tasks by end-Sept / early-Oct.
- Audience: **academia + data-holding flavor houses** first; product companies later. Intent to set up **Givaudan & IFF** calls (Yochai ~5 min from Givaudan, Switzerland; Planetech + ETH/GFI alt-protein nearby). Future audience ~1,000–2,000, niche, non-simultaneous.
- Science: hypothesis that a **peptide cocktail + lipid fraction (incl. phospholipids)** may suffice for meaty flavor without a full meat matrix; Anton's fatty-acid experiments no breakthrough; **phospholipids likely critical** (micro-reactor). MVP = knowledge platform + molecular DB + experts DB + simulator placeholder.
- Platform: demoed landing + Oracle chat (Claude Sonnet placeholder) with sources; ~Perplexity/NotebookLM feel. Legal: fact extraction without copyright infringement (with counsel). Collaboration friction since moving to GFI's **org account** broke cloud-code sharing.

**Decisions:** launch → end-Oct · MVP by end-2026, mature/"no-brainer" by end-2027 · scope narrowed to **meat (focus beef)**, not all alt-protein · initial focus academia + data-holding flavor houses.

---

## Meeting 2 — "Flavor Chemistry Data Pipeline Planning" (2026-09-02)
Attendees: Lior Teper, Yochai (Speaker 1).

**Key points**
- **Tooling:** moving off **Airtable** (slow/limited); **ClickUp** recommended as all-in-one work management (long learning curve, removes other integrations); **Grobid** to convert PDF → XML/markup for reliable extraction.
- **Three-dataset architecture:**
  - **Expert** — static Excel table, scraped from Google Scholar, OpenAlex, ScienceDirect.
  - **Molecular** — precursors only, **PubChem as source of truth**; bottleneck = synonym multiplicity → needs cross-matching algorithm.
  - **Sources** — papers classified via a JSON of topics/keywords with **manual priority** (low/med/high).
  - **Taxonomy** hand-built by Lior + Daniel, 5 branches: analytics, flavor chemistry, ingredients, meat-analogs, meat-science.
- **Quality ≠ relevance:** relevance depends on target audience; plan = per-paper agent + human-expert review until validated, then automate.
- **Future direction:** evaluating **Karpathy's "LLM Wiki"** as a possible **replacement for RAG** (unrestricted associative linking, filter later); possible integration in ~1–2 months.

**Decision:** relevance won't be defined until the **target audience/users are defined**.

---

## ⭐ Promised to send Yochai (extra links / knowledge — so he grasps the scope)
From Meeting 2:
- [ ] **GFI map**
- [ ] **Karpathy's LLM Wiki**
- [ ] **Papers on RAG**
- [ ] **The Grobid tool**

Still open from Meeting 1:
- [ ] **Platform link**
- [ ] **Questionnaire**
- [ ] **MeatCODE one-pager**
- [ ] Move the **MeatCODE ChatGPT project** into the GFI account and share it with Yochai

## Other open action items — Lior
- [ ] Set up **Givaudan & IFF** calls (via the new Givaudan contact).
- [ ] Update the client in **Asana** with a clear work plan + tasks (end-Sept / early-Oct).
- [ ] **Validate Pablo's simulator.**
- [ ] Keep researching **information-distillation architectures** + the quality-vs-relevance distinction.
- [ ] Schedule a **dedicated ~1-hour meeting** on priority / quality / relevance.
- [ ] Clarify with Yochai his **areas of expertise** + expected integration pain points.

## Action items — Yochai
- [ ] Go through the **GitHub repo** and digest the material with an AI agent.
- [ ] (from kick-off) Check with **Mike** how to get around the org cloud-code issues; propose an alternative UI/UX platform for cross-model collaboration; hold the follow-up online meeting; agree a defined role split before the flight + exam period.
