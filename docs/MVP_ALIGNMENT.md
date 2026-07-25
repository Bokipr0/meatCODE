<!-- Last updated: 2026-07-22 22:15 UTC · Project Coordinator · team alignment against the MVP definition (parallel readouts from all 5 lanes consolidated). Companion to docs/MeatCODE_MVP_Definition_and_User_Journeys.md + TEAM_BROADCAST.md. -->

# MeatCODE — MVP Alignment (all lanes, 2026-07-22)

The team was broadcast Lior's **MVP Definition & 5 User Journeys** (`docs/MeatCODE_MVP_Definition_and_User_Journeys.md`) — north star: a credible, source-backed prototype, **internal demo end of August**, refined early Sept, **external P1 expert validation mid-September**. Each of the 5 specialist lanes assessed where it stands against the 5 criteria + 5 journeys. This is the consolidated gap analysis. **Nothing was code-changed by this pass** — it's alignment.

## Journey status — honest snapshot

| Journey | Status today | Owner(s) | Biggest gap to credible |
|---|---|---|---|
| **J1 Scientific Question (Oracle)** | 🟢 Working skeleton — grounded RAG live, cites real sources, refuses off-corpus | Algorithm · Fullstack · Data | No **benchmark** proving "≥ general AI"; only 39% of corpus passes the relevance gate; grounding prompt was relaxed 07-20 (silent uncited training answers) |
| **J2 GC-MS Interpretation** | 🔴 Hollow — only descriptive UI labels; no data, no upload, no parser, no algorithm | Data · Fullstack · UI · Algorithm | **Everything** — needs a GC-MS reference layer (CAS/RI/OAV/sensory/pathway), an upload→parse→interpret path, and a UI |
| **J3 Literature Exploration** | 🟡 Partial-working — Database + `molecule-detail` (live linked papers) | Data · UI · Fullstack | No **knowledge-graph view**; graph edges thin (paper↔molecule/topic only); tagging 40% |
| **J4 Experimental Design** | 🟠 Design-only — Research funnel is static localStorage, no backend | UI · Fullstack · Data | No protocols corpus/table; no question→gaps→ideas→protocols→collaborators flow |
| **J5 Expert Discovery** | 🟢 Working — Map globe + filters over 374 curated experts | Data · UI · Fullstack | Experts under-enriched (email/h-index/topics stubbed, `org_type` NULL); no collaborate flow |

**One-line read (Advisory):** make **J1 / J3 / J5 truly credible**, and **mark J2 + J4 (+ Simulate) clearly as "preview."** GC-MS is a Phase-2 headline, not a realistic mid-Sept P0 — real spectral interpretation in ~7 weeks while corpus trust is still open would sink both.

## The P0 spine to mid-September (cross-lane, ordered)
1. **Corpus trust — Data Engineer (unblocks everything).** Close the **quarantine → `relevance_llm` write-back** (Daniel-rejected sources are still citable today), back-tag the ~489 untagged sources (39%→), run the retrievability count, triage the 202 off-topic. *Nothing is credible until the Oracle cites only vetted sources — and you can't benchmark an ungoverned corpus.*
2. **Prove the Oracle — Algorithm Expert.** Build the missing **benchmark harness**: 30–50 expert-authored gold Q&As, MeatCODE vs GPT/Claude/Perplexity, blind-rated by Daniel/P1 on usefulness + correctness + source-backing. This is criterion 1's literal bar and it has **zero measurement apparatus today**. Then reranking → pgvector hybrid to move the score.
3. **Deploy the backlog — Full-Stack Engineer.** A month of committed work (Oracle v11 → v12.7: Home, detail pages, `molecules/{id}`, molecule-suggestions, Inventory) is **not live** — every new endpoint the frontend calls is 404 until `deploy.command` runs + `/api/version` confirms. Human-gated single point of failure.
4. **Harden the credible journeys + honest previews — UI/UX + Fullstack.** Lock **one** design system (promote/merge the v8/v9/lean/research-screenflow fragments), add the J3 knowledge-graph view, reframe Research into a J4 planning flow, and label J2/J4/Simulate as previews with honest empty states.
5. **P1 validation readiness — Advisory.** Onboarding + validation protocol (task scripts, privacy lines, the anonymous-question-log decision) and a **mid-Aug scope-freeze gate** where Daniel signs off the corpus + the credible-vs-preview split.

## Cross-lane sequencing
- **Data Eng first** (write-back + tagging) → unblocks Oracle credibility *and* the benchmark.
- **Algorithm** runs the gold-set eval once the corpus is frozen — the evidence for criterion 1.
- **Full-Stack/UI** deploy the backlog, wire J4 to `/api/*` + stand up `/api/protocols`, normalize expert countries, mark previews.
- **Advisory** writes the P1 validation protocol before any external access; owns the mid-Aug gate.

## Open decisions for Lior + Daniel
- **Is GC-MS (J2) in scope for mid-Sept, or a labeled Phase-2 preview?** (Team recommendation: preview.)
- **Greenlight the benchmark eval** (expert gold set + blind rating) as the proof of "benchmark-competitive"?
- **Close the quarantine write-back** now (the #1 credibility risk before external users).
- **Deploy cadence** — run `deploy.command` now to land the month-long backlog; consider deploy notifications.

---

## Per-lane readouts (verbatim, lightly edited)

### Data Engineer — corpus / Neon / pipeline / scoring
- **Done:** 818 sources (all citable), 799 molecules (799/799 categorized), 374 curated experts, 37 orgs; grounded RAG gate + OR-fallback; relational tagging (571 tags / 3,457 links / 748 sources) + priority/relevance scoring + 2-day audit loop; read-only DB API serves live Neon (J3/J5 browse works).
- **Gaps:** GC-MS reference data = NONE (no CAS/SMILES/RI/OAV/structured sensory → J2 blocked); protocols corpus = NONE (J4); pathways/precursors only as free-text tags, not structured links; knowledge-graph edges thin (no molecule↔pathway, expert↔molecule/topic/org → J3/J5); experts under-enriched.
- **Top 3:** (1) build a GC-MS reference layer (top 100–200 volatiles: CAS+RI+OAV+sensory+precursor/pathway); (2) close corpus-credibility gaps (retrievability count, triage 202 off-topic, quarantine write-back, back-tag 489); (3) protocols table + minimal graph edges (expert↔topic/org).
- **#1 risk:** J2 has zero underlying data and can't lean on the literature corpus — a curated reference build (sourcing + curation) is the longest pole; unstarted, J2 stays a hardcoded mockup.

### UI/UX Designer — mockup / screens / design system
- **Done:** J1 Oracle (grounded answers, source pills, related-molecule chips, dictation); J3 partial (Database + live molecule-detail); J5 (Map globe + filters + profiles); Home landing + Inventory + Toolbench; nav Home·Oracle·Research·Simulate.
- **Gaps:** J2 GC-MS — no screen at all; J3 knowledge-graph absent (only the expert globe); J4 no research-planning flow; protocol detail is an explicit mock; J5 org/collaboration depth thin.
- **Top 3:** (1) build the J2 GC-MS interpretation screen (most demo-able missing criterion); (2) add a J3 knowledge-graph view; (3) reframe Research into a J4 planning flow + de-mock protocol detail.
- **#1 risk:** two of five criteria (J2, J4) have zero UI + J3's graph is missing = heavy net-new design before end-Aug; compounded by **design fragmentation** (canonical vs unpromoted v8/v9/lean/research-screenflow). Mitigation: lock one design system + promote/merge now.

### Algorithm Expert — Oracle retrieval / RAG / eval
- **Done:** grounded RAG live (top-6 `ts_rank_cd` over `search_vec`, `relevance_llm≥60`, AND→OR fallback fixed 71%→0% empty-source misses); retrieval-only eval harness (14 Qs); library sized honestly (319/818 pass the gate); citation-id correctness end-to-end.
- **Gaps:** no benchmark harness proving "≥ GPT/Claude/Perplexity" (criterion 1's bar); GC-MS interpretation unbuilt; no semantic/hybrid search or reranking (lexical FTS only); no research-gap detection (J4); quarantine leak + the 07-20 relaxed grounding (silent uncited training answers erode provenance).
- **Top 3:** (1) build the benchmark harness (20–40 Qs, blind expert/rubric scoring vs general AIs); (2) reranking → pgvector hybrid; (3) close credibility joints (quarantine write-back + revisit relaxed grounding).
- **#1 risk:** criterion 1's success metric has zero measurement apparatus, and the one edge (provenance) was just weakened — build the benchmark first; it's both the proof and the compass.

### Full-Stack Engineer — frontend + backend + deploy + integration
- **Done:** Oracle J1 wired end-to-end (grounded SSE, resolving citations); J3 API surface complete + live (molecules/{id}, suggestions, sources, companies, experts, facets, papers — SELECT-only); J5 experts+facets+Map; deploy/ops hardened (Render always-on, password gate, `/api/health`+`/api/version`, no-cache, dir-listing off).
- **Gaps:** J2 GC-MS zero implementation (no upload/parser/endpoint); the big committed backlog is NOT live (last confirmed `e8e3e2f`); J4 Research is static (no `/api/*` calls); no protocol backend; uneven loading/empty/error coverage on the static pages.
- **Top 3:** (1) deploy + verify the backlog live (`deploy.command` → `/api/version` → smoke-test); (2) scaffold GC-MS J2 end-to-end (`POST /api/gcms` → parse → match molecules → interpret via grounded Oracle → UI); (3) wire J4 Research to the API + stand up `/api/protocols`.
- **#1 risk:** the demo hinges on a manual, un-run `deploy.command` on Lior's Mac — until it fires, every endpoint the new frontend calls is 404 live and the app silently underdelivers.

### Advisory — strategy / architecture / sequencing / risk
- **Where it stands:** J1/J3/J5 demo-ready in skeleton; J2 hollow; J4 design-only; the working lanes sit on an ungoverned corpus (39% gate / 40% tagged / quarantines don't block retrieval).
- **P0 spine:** (1) close corpus trust; (2) prove Oracle via a gold-set benchmark vs ungrounded baseline; (3) harden J3+J5 + ship the deploy backlog. Make J1/J3/J5 credible; mark **J2, J4, Simulate "preview."** GC-MS **not P0**.
- **Sequencing:** Data Eng → Algorithm → Full-Stack/UI → Advisory P1 protocol; **mid-Aug gate**: Daniel signs off corpus + credible-vs-preview split, freeze scope.
- **Top risks:** (1) corpus-trust gap → write-back + tagging + sign-off; (2) "benchmark-competitive" asserted not proven → build the eval now, narrow honestly if weak; (3) broad-but-hollow demo → ruthless P0/preview split + single mockup owner + deploy discipline.
