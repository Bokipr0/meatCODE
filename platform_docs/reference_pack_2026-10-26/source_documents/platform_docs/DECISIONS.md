<!-- Last updated: 2026-10-18 · Codex / Advisory · recorded Lior's three-model pilot architecture and benchmark gate. -->

# MeatCODE — decision log

**Rules:** one row per decision · newest first · cite a source someone can open · if a decision is
reversed, keep the old row and mark it **SUPERSEDED by <date>**. "Proposed" ≠ decided — those go in
the last section.

Sources: **Gmail** (thread subject), **Asana** (task/status), **Repo** (file), **Lior** (stated directly to Claude).

## Decided

| Date | Decision | Who | Why | Source |
|---|---|---|---|---|
| 2026-10-18 | Pilot a three-model engineered RAG: local Qwen extraction (M1), local custom validation/curation plus deterministic checks (M2), and cloud-hosted GPT reasoning over approved evidence (M3). Place the protected artifact vault in controlled Neon storage; keep Neon authoritative and graph/vector layers derived. Benchmark against the current baseline before scaling further. | Lior | Separate extraction, checking, and reasoning responsibilities; make storage placement explicit; test whether added engineering produces a measurable quality benefit before paying the operational complexity of scaling | Lior stated directly; Repo `platform_docs/ENGINEERED_RAG_ARCHITECTURE.md` and `platform_docs/diagrams/meatcode-engineered-rag-architecture.svg` |
| 2026-10-01 | Run internal experiments before opening externally; publisher restrictions don't apply inside the experimental environment but do apply to anything published | Daniel (recorded by Yochai) | Unblock the KG/extraction work while rights are unresolved | Asana status update "Oct 1" |
| 2026-10-01 | Oracle gives a focused answer with sources and a research framework — not a full research proposal; asks follow-up questions when details are missing; plain chat UI is enough for v1 | Team (Asana status) | Knowledge should lead to real professional action | Asana status update "Oct 1" |
| 2026-09-22 | Staged extraction budget: title+abstract for the whole corpus (~250–500k tokens) first, full text only for 30–50 manually tagged papers | Yochai (proposal adopted in planning) | Keep cost inside the experiment budget | Gmail "Fwd: knowledge graph" |
| 2026-09-14 | Hold a joint October meeting with WUR to validate Pablo's Maillard simulator; accept AKA Foods' offer of Atlas sandbox access | Daniel | External validation of the simulator; a possible data source for the Oracle | Gmail "Updates from Thursday: reaction simulator and AKA Foods' Atlas" |
| 2026-08-27 | Molecule target properties live as columns + a `molecule_properties` provenance table (value, unit, derivation, method, conditions, source, confidence); computed values marked `system_derived`, never presented as measured | Lior | Every number must say who measured it, and how | Repo `db/migrations/0011`, `0012` |
| 2026-08-27 | Columns are dropped only after three checks: `count(col)=0`, no dependent views, repo grep clean | Lior + Data Engineer | A view check can't see Python/JS — a "safe" drop would have broken the server | Repo `db/migrations/0014` |
| 2026-07-23 | GC-MS / molecular tool ships as an honest **preview** on clearly labelled reference data, not a live analytical engine | Lior | Validation year; no real reference profiles yet | Repo `MVP_BOARD.md` |
| 2026-07-23 | Two environments: `dev` → staging, `main` → production; promote with `promote-to-prod.command`, roll back to `prod-*` tags | Lior | Never break the public site by accident | Repo `platform_docs/TWO_ENVIRONMENT_WORKFLOW.md` |
| 2026-07-22 | MVP definition + 5 user journeys adopted as the bar | Lior + Daniel | One shared definition of "done" | Repo `docs/MeatCODE_MVP_Definition_and_User_Journeys.md` |
| 2026-07-20 | Oracle never says it couldn't find something or names its corpus; cites a source only where it truly supports a point; fills gaps from general knowledge **uncited**. Citations are never invented. | Lior | Answers were opening with "the corpus doesn't cover this", advertising gaps to stakeholders | Repo `AGENT_UPDATE_LOG.md` 2026-07-20 13:40 |
| ~~2026-07-08~~ | ~~Oracle answers only from retrieved sources and refuses when uncovered~~ — **SUPERSEDED by 2026-07-20** (the retrieval gate `relevance_llm ≥ 60` itself still stands) | Lior | — | Repo `platform_docs/DECISION_grounded_answers_and_relevance.md` |
| 2026-07-08 | Retrieval gate: only sources that are citable **and** `relevance_llm ≥ 60` can be retrieved | Lior | An ungoverned corpus means confidently cited garbage | same |
| 2026-06-30 | Product UI uses GFI seaweed-teal; wine/pomegranate retired | Lior | One brand with GFI | Repo `CLAUDE.md` |
| 2026-06-30 | Three homes: git repo (code/docs/status) · Neon (data) · Asana (tasks); canonical repo `Bokipr0/meatCODE` | Lior | Stop agents drifting across scattered copies | Repo `CLAUDE.md`, `ROLES.md` |

## Positions stated, not yet team decisions

| Date | Position | Holder | Status | Source |
|---|---|---|---|---|
| 2026-10-18 | **SUPERSEDED IN PART by Lior's 2026-10-18 pilot decision** — initial advisory recommendation: Neon remains authoritative and Render stateless; rights-sensitive PDFs, GROBID, exact passages, and restricted extraction stay in an encrypted local lane; hosted reasoning receives only approved content; graph/vector systems remain projections | Codex / Advisory | Lior retained local M1/M2, cloud M3, Neon authority, and derived indexes, but selected a Neon-hosted protected artifact vault; cloud-storage rights, retention, access, backup, and deletion approval remain open | Repo `platform_docs/LOCAL_CLOUD_HOSTING_DECISION.md`; `reports/MeatCODE local cloud architecture.md`; `platform_docs/ENGINEERED_RAG_ARCHITECTURE.md` |
| 2026-10-17 | Use a governed batch pipeline: local GROBID and controlled full-text workspace; parallel claim/numeric extraction; independent checking and deterministic validation; Neon remains the only production system of record; retrieval/graph tools consume approved projections only | Codex / Advisory for Lior | Architecture recommendation complete; awaiting Lior and Daniel/Yochai sign-off; pilot evidence still required | Repo `platform_docs/DATA_PROCESSING_ARCHITECTURE.md` |
| 2026-09-07 | "Our current plan": extract facts and relationships with provenance; **never store, reproduce or share article full text**; answers cite and link to the original; MeatCODE stays open and non-commercial. The working rule the team follows, framed by Daniel as a plan pending legal advice | Daniel | Operating rule; formal rights decision still open (Asana "Legal – publisher rights") | Gmail "Data paywall – Summarized (Meatcode)" |
| 2026-10-05 | Adopt Prof. Ram's *pattern* (GROBID → offline extraction → graph-aware retrieval) but keep a chemistry-specific schema and stay on Postgres + pgvector instead of adding a graph DB | Lior | Sent to Ram; no reply. Needs Daniel/Yochai approval (Asana "Choose tool stack", overdue) | Gmail "MeatCODE — follow-up on LightRAG proposal"; Repo `platform_docs/RAG_BUILD_VS_BUY.md` |
| 2026-09-14 | GROBID → LightRAG, embeddings only *propose* links, relations come from text-level extraction | Prof. Yoav Ram | Proposal under review; Yochai–Ram meeting 2026-10-12 | Gmail "Fwd: knowledge graph" |
| 2026-09-10 | Approach publishers with an informal exploratory enquiry, not a formal licence request ("you can't un-ask") | Omer Brandes (legal) | Advice; no decision visible | Gmail "Data paywall – Summarized" |
| 2026-08 | Public launch of the *project* (not the platform) moved from end-Sept to end-Oct 2026 | Lior | Stated by Lior; not found in email or Asana | Lior |

## Waiting for a decision (owner · Asana due)

- Publisher rights for articles — Daniel · 2026-10-08 (overdue)
- MVP definition + acceptance test — Daniel · 2026-10-08 (overdue)
- Choose tool stack for the hub — Lior · 2026-09-30 (overdue)
- Is the expert DB public? — Daniel · 2026-10-15
- Extraction-only vs full-text linkage — Daniel · 2026-10-31
- Open-source licence (code, data, model, knowledge layer) — Daniel · 2026-10-31
- Experimental Platform status — Daniel · 2026-10-14
- Research corpus counts gated to `relevance_llm ≥ 60`? — Lior (repo `MVP_BOARD.md` #9)
