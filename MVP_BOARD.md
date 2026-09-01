_Last updated: 2026-08-31 (pm) · Project Coordinator · Demo-prep — GC-MS/NMR measurements browser + Pablo's simulator live (mock) + 10-min run-of-show; B1 (deploy) is now a hard demo gate_

# MVP_BOARD — what's open for end of August

> **Agents: read this after `CLAUDE.md` and `PROJECT_STATE.md`.** This file is the shared open-items
> list for the end-of-August MVP. `PROJECT_STATE.md` = technical reality (what's built/broken);
> **this file = what still has to be delivered, by lane.** Update your rows when you finish something.
> Lior views the same board as a Cowork dashboard (`meatcode-mvp-board`).

**Dates:** internal demo **31 Aug 2026** · external P1 expert validation **mid-Sept**.

**Scope decision (2026-07-23, Lior):** the **GC-MS / molecular tool ships as an honest preview** —
fingerprint + by-cut comparison on clearly-labelled reference data, *not* a live analytical engine.
This resolves the open "GC-MS: P0 vs preview?" question in `PROJECT_STATE.md`.

**Demo readiness (2026-08-31, Coordinator):** the two demo modules landed — the in-product **GC-MS/NMR measurements browser** (`#analytics`) and **Pablo's simulator live in mock** (`#simulate` → `/api/simulate`, synthetic-labelled) — plus a 10-min run-of-show (`docs/meatcode_demo_runofshow_2026-08-31.md`). A separate same-day dev-zone **Analytics workspace** (`app/dev/analytics_workspace.html`, A3) covers the bring-your-own-data upload→compare flow. **Hard demo gate: B1 (deploy)** — `/api/corpus`, `/api/compare`, `/api/simulate` are 404 on prod, so demo on `deploy-dev` staging or localhost with `maillard_sim` ON.

Status key: 🟢 working · 🟡 in progress · 🔴 blocked · ⚪ not started · **[CP]** = critical path

---

## End of August MVP — the eight lanes

| # | Lane | Owner | Status | What's actually needed |
|---|---|---|---|---|
| 1 | UX / UI | UI/UX Designer | 🟡 | Lock ONE design system; J3 knowledge-graph view; J4 planning flow; honest "preview" states. **2026-08-16 demo-polish:** Research sub-topic chips now dynamic (live `GET /api/corpus`) with honest 0-count grey-out; dev/staging ribbon removed from the mockup. |
| 2 | Database contents — quantity & quality **[CP]** | Data Engineer | 🔴 | **Still blocked by the quarantine write-back (B2)** — that stays the critical gap. Enrichment finally moving: molecule **canonical IDs** underway (CAS backfill from MVL, familiar_names/found_in/pathway_step/reacts_with/solubility/reaction-rate columns, `is_junk` flag), tailored abstracts (30 papers) + topic-tag fill in this run. |
| 3 | Oracle | Algorithm + Full-Stack | 🟢 | Grounded RAG live and citing real source IDs. Next: the benchmark harness. **2026-08-16:** four starter chips are now capability demos — Maillard synthesis route (grounded `/api/ask` + illustrative schematic) · Explore the lipid corpus (`/api/corpus`) · Predict with the simulator (`/api/simulate`, **MOCK/synthetic — banner required**) · Compare molecules (inline via `/api/compare` + `/api/molecules/{id}`, never navigates away). |
| 4 | GC-MS / molecular tool **[CP]** | Full-Stack + Data | ⚪ | Scoped as PREVIEW. **Open:** reference profiles per cut — WUR, literature-mined, or synthetic-and-labelled? |
| 5 | Literature white-space mapping (initial) | Data + UI/UX | ⚪ | Depends on the knowledge graph — **A5's KG MVP now exists**, but the gap view isn't credible until the paper↔molecule bridge is densified (see A5). "Initial" = a first credible gap view, not a graph product. |
| 6 | Simulation — synthetic demo | UI/UX | ⚪ | **The `#simulate` scene is still hardcoded/synthetic and must be visibly labelled synthetic** — that requirement stands. **New (2026-08-16): a real Maillard chemistry simulator now exists** (working Docker prototype: precursors + conditions → aroma compounds with ppb yields, confidence, 16 reaction families, Monte-Carlo, 1–10 s/run) — **but it is not connected to the platform**. Integration is tracked separately as **A8**; until A8 ships behind its flag, lane 6 stays synthetic-and-labelled in prod. **2026-08-16:** the Oracle "Predict with the simulator" chip is the `/api/simulate` mock path — the synthetic-label/banner requirement applies there too; it is not a second engine. |
| 7 | Feedback & usage collection | Full-Stack | ⚪ | **Needs Lior's call:** anonymous server-side question log (no identity)? Cheapest validation-year evidence. |
| 8 | Documentation | All lanes | 🟡 | Internal docs are strong. **2026-08-16:** a reviewer-facing "what this is / what it isn't" block now exists in `docs/oracle_demos_and_corpus_filter_2026-08-16.md` §4 — starting point for the consolidated mid-Sept reviewer hand-out; still needs lifting into a standalone doc. |

## Action items (from the meeting)

| # | Item | Feeds | Status | Note |
|---|---|---|---|---|
| A1 | Placeholder — meat data fingerprint **[CP]** | GC-MS preview | 🟡 | **Placeholder screen now exists in the Dev Area** (clearly labelled). The schema is still the real work — define it **before** any further UI; everything else keys off it. |
| A2 | Scenario & user screen-flow creation | UI/UX | ⚪ | Highest leverage for the least work — it decides what must exist by 31 Aug, and what doesn't. A dedicated section now exists in the Dev Area hub to hold it. |
| A3 | Meat profile comparison vs user data, by cuts **[CP]** | GC-MS preview | ⚪ | Blocked on A1 + decision: do users upload real GC-MS data in v1, or pick a sample? |
| A4 | RAG development | Oracle | 🟡 | This run: **consensus agree/oppose SSE event** in `/api/ask` + a **closed-corpus verify+score eval harness (8 questions)** + claim records surfaced into retrieval. The full gold-set benchmark vs GPT/Claude/Perplexity is still the evidence Daniel can show. |
| A5 | Knowledge graph for white-gap mapping (dev side) | White-space | 🟡 | **KG MVP built** (molecule KG + paper KG, projected from Postgres — no graph DB) + explorer screen in the Dev Area. **Bottleneck is the bridge:** 23 curated → **712 mined** edges, still only **~13% of molecules / ~34% of papers** linked — the roasted/nutty query finds perfect chemistry, 0 papers. Next: densify via claim extraction on ~50 papers (needs canonical IDs first). See `platform_docs/KG_DECISION.md`. |
| A6 | Dev Area — internal workbench (`app/dev/`) | All lanes | 🟡 | New this run: hub with Features / Screens / Documents / User-screen-flow sections, gated behind `ff-dev_area` (**OFF in prod**). Hosts the KG explorer + fingerprint placeholder. Rule: placeholders must say they're placeholders. See `platform_docs/DEV_AREA.md`. |
| A7 | Analytics zone screen (GC-MS · HPLC · Olfactory · NMR · Spectroscopy) | Full-Stack + UI/UX | 🟡 | **Promoted 2026-08-16 to a first-class in-product `#analytics` scene**, reachable from the Research "Analytics" tile (no longer Dev-Area-only). Still **preview on real-but-partial data**: GC-MS backed by the Meaty Volatile Library; HPLC/Olfactory/NMR/Spectroscopy thinner or planned. Each method card live-queries `/api/corpus?phase=analytics`; every panel keeps its honest backing/placeholder label; the scene stays labelled *preview* until all panels are wired. See `docs/oracle_demos_and_corpus_filter_2026-08-16.md`. |
| A8 | **Maillard simulator integration** (Research → precursors → "Predict reaction" → results) | Simulation (lane 6) | 🟡 | **Started 2026-08-16, Phase 1 only.** Owners: **Full-Stack** (`server/maillard/CONTRACT.md` + `adapter.py`, `/api/simulate` proxy, `maillard_sim` flag, second *disabled* render.yaml service) · **UI/UX** (`UI-UX Designer/maillard_sim_wireframe.html`) · **Lior** (the simulator's chemistry + the prod flag) · **Advisory** (`platform_docs/MAILLARD_INTEGRATION.md`, the design of record). **Hard constraint:** prod is Render `runtime: python` and **cannot spawn Docker** — the simulator must be its own Docker service (or dev-only local) behind a same-origin proxy. **Prerequisite:** a frozen input/output contract — if `CONTRACT.md` is still moving on 24 Aug, Phase 1 does not land. **Realistic for 31 Aug: Phase 1, flagged (dev ON / prod OFF), on 3–5 cached demo formulations.** Comparison = Phase 2, Bayesian optimisation = 2027, history/collaboration = blocked on per-user identity. **Must not displace B1/B2.** |
| A9 | **Oracle demos & corpus filter** (dynamic Research chips · first-class `#analytics` · dev-banner removal · 4 Oracle capability demos) | UI/UX + Full-Stack | 🟡 | **Shipped 2026-08-16, demo-polish (awaiting deploy-dev).** New `GET /api/corpus?phase=&topics=`; `POST /api/compare` + `GET /api/molecule-profile/{id}` alias for inline compare; reuses `/api/ask` + `/api/simulate` (mock). Honesty rules: mock simulator always bannered · 0-count chips grey out · Analytics stays *preview*. **Open decision:** corpus counts are currently ungated — gate to `relevance_llm≥60` to match the Oracle? (one-line change). **Does not reorder the spine — B1/B2 stay [CP].** Design of record: `docs/oracle_demos_and_corpus_filter_2026-08-16.md`. |

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
5. **Maillard simulator — show it externally in mid-Sept?** It has no validation against lab data. Advisory recommends showing it framed as *"a model we're building — tell us if the chemistry is plausible"*, not as a capability. (Gates A8's external exposure. Full argument: `platform_docs/MAILLARD_INTEGRATION.md` §8.)
6. **Do we pay for a second Render service** (~$7/mo, `runtime: docker`) for the simulator? Advisory recommends **dev-only local until 31 Aug**, paid only if it goes into the mid-Sept sessions.
7. **Where do simulation runs live** — `localStorage` (client-side, no identity needed) or Neon? Advisory: client-side for Phase 1, and decide this together with decision 3 (anonymous usage log) — they're the same privacy question.
8. **Retire the "<3 s feels instant" requirement?** Runs take 1–10 s; the honest target is *immediate acknowledgement + real progress + median under 5 s*. Someone has to actually strike "<3 s" from the brief.
9. **Research corpus counts — gate to the Oracle's `relevance_llm≥60`, or show all tagged sources?** Data recommends gating so Research and the Oracle count the same corpus (more honest — excludes the ~28% high-confidence off-topic sources); Full-Stack shipped it ungated (larger browse counts). One-line SQL change in `GET /api/corpus`. (Surfaced by the 2026-08-16 Oracle-demos run.)
