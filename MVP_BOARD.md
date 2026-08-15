_Last updated: 2026-08-15 · Advisory · statuses refreshed against the 5-agent run (dev area · KG · consensus/eval · canonical IDs)_

# MVP_BOARD — what's open for end of August

> **Agents: read this after `CLAUDE.md` and `PROJECT_STATE.md`.** This file is the shared open-items
> list for the end-of-August MVP. `PROJECT_STATE.md` = technical reality (what's built/broken);
> **this file = what still has to be delivered, by lane.** Update your rows when you finish something.
> Lior views the same board as a Cowork dashboard (`meatcode-mvp-board`).

**Dates:** internal demo **31 Aug 2026** · external P1 expert validation **mid-Sept**.

**Scope decision (2026-07-23, Lior):** the **GC-MS / molecular tool ships as an honest preview** —
fingerprint + by-cut comparison on clearly-labelled reference data, *not* a live analytical engine.
This resolves the open "GC-MS: P0 vs preview?" question in `PROJECT_STATE.md`.

Status key: 🟢 working · 🟡 in progress · 🔴 blocked · ⚪ not started · **[CP]** = critical path

---

## End of August MVP — the eight lanes

| # | Lane | Owner | Status | What's actually needed |
|---|---|---|---|---|
| 1 | UX / UI | UI/UX Designer | 🟡 | Lock ONE design system; J3 knowledge-graph view; J4 planning flow; honest "preview" states. |
| 2 | Database contents — quantity & quality **[CP]** | Data Engineer | 🔴 | **Still blocked by the quarantine write-back (B2)** — that stays the critical gap. Enrichment finally moving: molecule **canonical IDs** underway (CAS backfill from MVL, familiar_names/found_in/pathway_step/reacts_with/solubility/reaction-rate columns, `is_junk` flag), tailored abstracts (30 papers) + topic-tag fill in this run. |
| 3 | Oracle | Algorithm + Full-Stack | 🟢 | Grounded RAG live and citing real source IDs. Next: the benchmark harness. |
| 4 | GC-MS / molecular tool **[CP]** | Full-Stack + Data | ⚪ | Scoped as PREVIEW. **Open:** reference profiles per cut — WUR, literature-mined, or synthetic-and-labelled? |
| 5 | Literature white-space mapping (initial) | Data + UI/UX | ⚪ | Depends on the knowledge graph — **A5's KG MVP now exists**, but the gap view isn't credible until the paper↔molecule bridge is densified (see A5). "Initial" = a first credible gap view, not a graph product. |
| 6 | Simulation — synthetic demo | UI/UX | ⚪ | Must be visibly labelled synthetic so reviewers don't read it as validated modelling. |
| 7 | Feedback & usage collection | Full-Stack | ⚪ | **Needs Lior's call:** anonymous server-side question log (no identity)? Cheapest validation-year evidence. |
| 8 | Documentation | All lanes | 🟡 | Internal docs are strong; a reviewer-facing "what this is / what it isn't" doc is missing for mid-Sept. |

## Action items (from the meeting)

| # | Item | Feeds | Status | Note |
|---|---|---|---|---|
| A1 | Placeholder — meat data fingerprint **[CP]** | GC-MS preview | 🟡 | **Placeholder screen now exists in the Dev Area** (clearly labelled). The schema is still the real work — define it **before** any further UI; everything else keys off it. |
| A2 | Scenario & user screen-flow creation | UI/UX | ⚪ | Highest leverage for the least work — it decides what must exist by 31 Aug, and what doesn't. A dedicated section now exists in the Dev Area hub to hold it. |
| A3 | Meat profile comparison vs user data, by cuts **[CP]** | GC-MS preview | ⚪ | Blocked on A1 + decision: do users upload real GC-MS data in v1, or pick a sample? |
| A4 | RAG development | Oracle | 🟡 | This run: **consensus agree/oppose SSE event** in `/api/ask` + a **closed-corpus verify+score eval harness (8 questions)** + claim records surfaced into retrieval. The full gold-set benchmark vs GPT/Claude/Perplexity is still the evidence Daniel can show. |
| A5 | Knowledge graph for white-gap mapping (dev side) | White-space | 🟡 | **KG MVP built** (molecule KG + paper KG, projected from Postgres — no graph DB) + explorer screen in the Dev Area. **Bottleneck is the bridge:** 23 curated → **712 mined** edges, still only **~13% of molecules / ~34% of papers** linked — the roasted/nutty query finds perfect chemistry, 0 papers. Next: densify via claim extraction on ~50 papers (needs canonical IDs first). See `platform_docs/KG_DECISION.md`. |
| A6 | Dev Area — internal workbench (`app/dev/`) | All lanes | 🟡 | New this run: hub with Features / Screens / Documents / User-screen-flow sections, gated behind `ff-dev_area` (**OFF in prod**). Hosts the KG explorer + fingerprint placeholder. Rule: placeholders must say they're placeholders. See `platform_docs/DEV_AREA.md`. |
| A7 | Analytics zone screen (GC-MS · HPLC · Olfactory · NMR · Spectroscopy) | Full-Stack + UI/UX | 🟡 | New this run: Dev Area screen scaffolding the instrument panels (pairs with the Research-area Analytics tile). Panels not wired to data — must carry placeholder labels until they are. |

## Flagged by Claude — not on the list, but blocking

| # | Item | Owner | Status | Why it matters |
|---|---|---|---|---|
| B1 | Deploy the backlog (v12.1 → v12.7) **[CP]** | Lior | 🔴 | A month of built, verified work is not live. `deploy-dev` → check staging → `promote-to-prod`. Nothing here is demoable until this lands. |
| B2 | Close quarantine → `relevance_llm` write-back **[CP]** | Data Engineer | 🔴 | Audits write to `source_audits` but never back to `sources.relevance_llm`, so retrieval still gates on unreviewed scores. Must close before external validation. |

---

## Open decisions for Lior + Daniel
1. **GC-MS reference data source** — WUR collaboration, literature-mined, or synthetic-and-labelled? (Gates A1 + A3.)
2. **Do users upload real GC-MS data in the v1 preview,** or only choose a bundled sample?
3. **Anonymous usage/question log** — yes or no? (Gates lane 7.)
4. **Benchmark harness greenlight** — build the gold set now? (Gates A4 and the credibility story.)
