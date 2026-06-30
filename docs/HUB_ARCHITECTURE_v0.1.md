# MeatCODE — Hub Architecture v0.1

*Owner: Lior · Status: draft for review (Daniel sign-off + Asana "Define hub architecture" & "Choose tool stack") · 2026-06-30*
*Scope decision: **tight MVP** — four surfaces (Oracle · Literature · Expert · Molecular). Toolbench / Simulate / For-You are roadmap, not built in 2026.*

---

## 1. Summary (the one-screen version)

The MeatCODE hub at MVP is **one source-backed knowledge surface** over a single Postgres database, with four entry points and an AI Oracle that answers in plain language with citations *from our corpus, not the open web*. It deliberately ships **four** of the seven domains the full vision shows — the four that are data-backed today — and frames the rest as "later." This is the deck's #1 risk control (don't build the full vision early) made concrete.

- **Data:** Neon Postgres, one connected schema (sources · molecules · odours · claims · experts · topics + facet tables).
- **Intelligence:** Oracle = retrieval over the corpus → Claude answer with cited sources (SSE streaming).
- **Surfaces:** internal (Streamlit) · stakeholder self-serve (Metabase) · product (mockup → Next.js).
- **MVP done =** a stakeholder can ask the Oracle a real R&D question and get a useful, cited answer; and can browse/filter the literature, experts, and molecules behind it.

---

## 2. Sitemap (MVP)

```
Home / Welcome
  └─ global search + tag filters (from Tagging Taxonomy v0.1)
①  Oracle            ask a question → cited, streamed answer (+ follow-ups, white-space hints)
②  Literature DB     browse / filter sources by facet · per-source page · white-space map
③  Expert & Org      searchable directory + network map · per-expert page
④  Molecular DB      precursors / volatiles / pathways · per-molecule page (sensory, methods, sources)
   — — — roadmap (visible, not built) — — —
   Toolbench (protocols/benchmarks) · Simulate (process-flavor sandbox) · For You (personalized)
```
Cross-cutting: one global search, shared facet filters, "save" for any item. Every object page cross-links (a molecule lists its sources, experts, sensory notes; a source lists its molecules, topics, claims).

## 3. Data architecture

**Single source of truth: Neon Postgres** (see `docs/DATA_DICTIONARY.md` for column-level detail). Core entities and how they connect:

```
sources ──< source_topics >── topics (hierarchy)
   │  │ │
   │  │ └─< source_sensory_attributes >── sensory_attributes
   │  └───< source_methods >── analytical_methods
   │       < source_product_contexts >── product_contexts
   │  ──< source_molecules >── molecules ──< molecule_odours >── odours
   │                              └─ molecule_role_tags
   └──< source_experts >── experts ──< expert_relations >── experts (co-authorship)
claims ──< claim_sources / claim_molecules / claim_topics_v2 >  (evidence statements)
reactions (reaction_kind) · processes · matrix_profiles · ingredients · organizations
```
- **Tagging** is the join layer (Tagging Taxonomy v0.1) — it's what powers filtering and white-space analysis.
- **Relevance/trust:** `trust_tier` (Very/Mid/Little) on sources, set by the pipeline.
- **Retrievability constraint (trust-critical):** the Oracle can only cite a source that has a populated `search_vec` (built from name + abstract). A row with no abstract is invisible to citations. *Action: verify how many of the ~500 live sources have non-null `abstract` + `search_vec` — that's the real citable-corpus size.*

## 4. The Oracle pipeline (the centrepiece)

```
question → retrieve top-K sources (Postgres FTS: ts_rank_cd over search_vec)
        → build a grounded prompt (sources injected, "answer only from these")
        → Claude streams answer + inline citations  → SSE (sources → chunk → done)
```
**Two backends, both in the repo:**
- `server/meatcode_server.py` — thin, SDK-only, **no citations** (fast demo / Neon-asleep fallback). *Wired + ready now (`run_oracle.command`).*
- `server/reaktzia-mvp/` — FastAPI + Neon + **real cited papers** (needs `DATABASE_URL` in `.env`).

**Phasing** (from `docs/Reaktzia_NextSteps…`): keyword RAG (now) → pgvector hybrid (BM25 + cosine) → Next.js SSE product → auth + feedback loop. Hallucination control = cite-or-say-unknown, confidence tags, review gate (the deck's AI-reliability mitigation).

## 5. Core user journeys (MVP must serve these 3)

1. **Plant-based R&D scientist — debug an off-note.** "Why does my pea burger taste cardboardy?" → Oracle returns the cardboard-aroma molecules (2-pentylfuran, 2,4-decadienal, hexanal), the lipoxygenase pathway as likely source, and cited masking strategies → drills into Molecular DB + Literature.
2. **Flavor formulator — design a reaction base.** "Char-grilled beef base" → top Maillard/Strecker products, precursor amino acids + sugars, heat/time/pH ranges, with sources → saves the molecule set.
3. **Researcher / GFI — map who & what's missing.** Search a topic → Expert directory + network map of who works on it; Literature white-space view shows under-studied facet combinations (e.g. "bitter-blocker × hexanal masking — no paper tests both").

## 6. UI concept (defer to design track)
The visual/UX layer lives in the parallel design work — `app/meatcode_mockup.html` (current) and the `UI-UX Designer/` v8 candidate. **This doc owns information architecture + data + journeys; it does not re-decide UI.** One open item to resolve there: the brand direction (v8 proposes GFI seaweed-teal; confirm vs. the earlier wine/pomegranate before promoting).

## 7. Tool stack (answers Asana "Choose tool stack")
- **Database:** Neon Postgres — single source of truth.
- **Internal analysis:** Streamlit (`analysis/streamlit_dashboard.py`) — fast, Lior-facing.
- **Stakeholder self-serve:** **Metabase** (recommended) on Neon — lets Daniel/advisors slice data without making Lior the bottleneck.
- **Product surface:** HTML mockup now → **Next.js** (Vercel) for the real Oracle/Map/Research.
- **AI:** Claude via the two servers above. Pipeline: Dimensions.ai-fed, Layer C extraction + Layer E store, 3-tier relevance.
- **Three homes (infra):** Git repo (code/docs/status) · Neon (data) · Asana (tasks). See `CLAUDE.md`.

## 8. MVP definition of done & dependencies
**Done when:** a stakeholder asks the Oracle a real question and gets a useful cited answer, and can browse the literature/experts/molecules behind it, on a shareable surface.
**In:** Oracle (cited), Literature DB + filters, Expert directory + map, Molecular DB. **Out (roadmap):** Toolbench, Simulate, For-You, accounts/community.
**Critical dependency:** literature collection — from ~500 to 1,000–2,000 sources, *with abstracts* (only those are citable). Everything above is gated on corpus depth, not on more features.

## 9. Open questions for Lior / Daniel
1. Confirm the **four-surface MVP** cut (this doc) vs. showing more domains for the WUR-level demos.
2. Approve **Metabase** as the stakeholder layer (small self-host cost).
3. Run the **citable-corpus check** (sources with abstract + `search_vec`) — sets realistic Oracle expectations.
4. Confirm whether the **Prediction/Simulate** surface in the mockup is framed as "hypothesis generator" (the corpus can't yet back a predictive model).
