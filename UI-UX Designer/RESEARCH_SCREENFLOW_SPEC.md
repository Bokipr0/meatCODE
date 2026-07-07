_Last updated: 2026-07-05 16:22 UTC · UI/UX Designer (screenflow spec) · Research screenflow IA — Oracle-as-connective-tissue unifying Literature + Molecular + Expert DBs + RAG chatbot_

# MeatCODE — Research Screenflow & Information Architecture Spec

> **Scope.** This is the designer-grade spec for the MeatCODE **Research** experience — the primary
> interface that unifies four interconnected resources into one navigable workspace:
> **(1) Literature DB · (2) Molecular / mechanistic DB · (3) Expert map · (4) the Oracle RAG chatbot.**
> A partner agent is building the interactive HTML prototype; **this spec is the source of truth for the
> IA and screenflow that guides it.** It respects the GFI seaweed-teal design system and the existing
> 4-region app-shell (topbar 64 / context panel 248 / canvas / dock 88).
>
> **Reality anchor (from PROJECT_STATE.md — do not over-promise in the UI):**
> corpus ≈ **818 sources** (ranked by `priority_score`, Oracle filters `relevance_llm ≥ 60`),
> **~374 curated experts** surfaced (of 3,129 raw), **799 molecules** (mostly untagged, 45 claims).
> Oracle is **phased keyword-RAG → pgvector hybrid** (today: FTS `search_vec`, ranked retrieval, SSE
> streaming). Molecular pathways and claims are **thin** — the UI must frame prediction/mechanism as
> *hypothesis-generation, cited*, never as settled authority. **Narrow-MVP discipline is a design constraint,
> not a footnote.**

---

## 1. Design goal & principles

**Goal.** Let a researcher land on any one of the four resources and *fluidly cross to the other three
without losing context* — with the Oracle as the connective tissue that both answers questions and
hands off into structured entities. Every fact on screen should be one click from its source and from
its neighbours in the knowledge graph.

**Principles**

1. **Oracle-as-connective-tissue.** The Oracle is not a separate "chatbot tab" — it is the seam that
   stitches the resources together. Every Oracle answer resolves into **entity chips** (molecules,
   papers, experts) that are live jump-points; and every entity screen has an **"Ask the Oracle about
   this"** affordance that pre-seeds a scoped question. The chatbot is the graph's query language made
   conversational.

2. **Everything cross-linked (the graph is the product).** No resource is a dead end. A paper shows its
   molecules and authors; a molecule shows its papers and expert authors; an expert shows their papers
   and orgs. The user should never have to re-search to move between related entities — the link is
   already on the card.

3. **Source-backed & traceable.** Nothing appears without provenance. Oracle claims carry inline
   citation markers that are themselves entity links; molecule/pathway assertions cite the paper(s) they
   came from; expert relevance shows *why* they ranked. Given the thin claims table, **"we don't have
   enough sources yet" is a first-class UI state**, not an error.

4. **Narrow-MVP discipline.** Ship the four resources + their cross-links well before adding Toolbench/
   Simulate depth. Prediction/Simulate stay visibly **Preview**. Filters and entity screens show only
   fields the DB actually populates; empty fields are hidden, not faked.

5. **One workspace, one context.** The left context panel is a persistent "where am I / what's related"
   rail, not per-domain chrome. Cross-jumps update the breadcrumb, never a full-page reload feeling.

---

## 2. Resource relationship model (entity-link map)

The four resources are four views onto **one knowledge graph**. Three entity types + the Oracle as a
traversal layer over all of them.

```
                         ┌─────────────────────────────────────────┐
                         │              THE ORACLE (RAG)            │
                         │  reads all 3 entity types, returns an     │
                         │  answer whose citations & chips ARE the   │
                         │  entities below (bi-directional handoff)  │
                         └───────▲───────────▲───────────▲──────────┘
                                 │           │           │
              ask-about / cite   │           │           │  ask-about / cite
                                 │           │           │
        ┌────────────────────────┴──┐  ┌─────┴────────┐  ┌┴─────────────────────────┐
        │        PAPER (Literature) │  │  MOLECULE     │  │      EXPERT               │
        │  sources / literature DB  │  │ molecular DB  │  │  expert map               │
        ├───────────────────────────┤  ├──────────────┤  ├───────────────────────────┤
        │ • title, venue, year      │  │ • name (mono)│  │ • name, org, country      │
        │ • priority_score          │  │ • class/role │  │ • relevance_score         │
        │ • relevance_llm           │  │ • pathway*   │  │ • h_index, #papers        │
        │ • topics (taxonomy)       │  │ • claims* 45 │  │ • topics                  │
        │ • abstract / search_vec   │  │ (*thin data) │  │ (co-auth edges: empty)    │
        └──────────┬────────────────┘  └──────┬───────┘  └───────────┬───────────────┘
                   │                          │                      │
                   │  mentions / measures     │  studied in          │
                   ├──────────────────────────┤                      │
                   │        PAPER  ── mentions ──▶  MOLECULE          │
                   │                                                  │
                   │  authored by                       authored by   │
                   ├───────────────────────────────────┬─────────────┤
                   └──▶  PAPER  ── authored by ──▶ EXPERT ◀─ works on ─┘
                                                          │
                             EXPERT ── studies ──▶ MOLECULE (via their papers)
```

**Edge inventory the prototype should expose (only where data exists; else hide the link):**

| From | Edge | To | Source of truth | Today's data reality |
|------|------|----|----|----|
| Paper | mentions / measures | Molecule | `source_topics` + molecule links | Partial — molecules mostly untagged; show when present |
| Paper | authored by | Expert | authorship | Present (curated experts) |
| Molecule | appears in | Paper | reverse of above | Thin — surface "papers referencing" list, may be short |
| Molecule | studied by | Expert | via papers | Derived; show best-effort |
| Expert | wrote | Paper | authorship | Present |
| Expert | affiliated with | Org | `experts.org` | Present (country data sparse) |
| Expert | co-authored with | Expert | `expert_relations` | **EMPTY — do not render fake edges** (per STATE.md) |
| Oracle | cites | Paper / Molecule / Expert | RAG retrieval over `search_vec`, `relevance_llm ≥ 60` | Present for papers; entity-chip extraction for molecules/experts is the design ask |

> **Design consequence:** because co-authorship edges are empty and molecule↔paper links are sparse,
> the **Oracle is the primary cross-linker in the MVP** — it is often the only edge available between,
> say, a molecule and an expert. That is *why* Principle 1 elevates it to connective tissue rather than
> treating it as a peer tab.

---

## 3. Three primary user journeys

Each journey starts in a different resource and must reach all four. Cross-jumps are marked **⟶⟶**.

### Journey A — Question-first (the headline flow: Oracle as entry + connector)

1. User opens **Research** workspace → focus is on the Oracle ask-bar (hero).
2. Types: *"What drives the roasted, meaty note in plant-based patties?"*
3. Oracle streams an **answer block** (SSE): prose with inline citation markers `[1][2]` + a
   **"Entities in this answer"** strip below it: molecule chips (`2-acetyl-1-pyrroline`,
   `furanthiols`), paper chips (top-3 cited sources), expert chips (authors of those sources).
4. **⟶⟶ Molecule:** user clicks the `2-acetyl-1-pyrroline` chip → **Molecule detail** opens (canvas
   swaps, breadcrumb: `Oracle answer › 2-AP`). Context panel now lists this molecule's papers + experts.
5. **⟶⟶ Literature:** from the molecule's "Appears in" list, user opens a **Paper detail** →
   breadcrumb extends `… › Paper: Maillard×lipid cross-talk`.
6. **⟶⟶ Expert:** from the paper's author list, user opens an **Expert profile** → sees their other
   papers + org, all on-topic.
7. **⟶⟶ Back to Oracle:** the expert card's **"Ask the Oracle about this researcher's work"** seeds a
   new scoped question — loop closes. The user has traversed all four resources without one manual search.

### Journey B — Molecule-first (mechanism-driven researcher)

1. User enters via **Database › Molecular** (or a molecule chip from anywhere) → filter rail: class,
   flavor role, "has cited claims" toggle.
2. Picks `furanthiols` → **Molecule detail**: name (monospace), role, a **cited pathway/claims** panel
   (each assertion carries its paper citation; if none, show the "hypothesis — not yet source-backed"
   empty state, honestly).
3. **⟶⟶ Literature:** "Appears in N papers" → filtered Paper list for this molecule.
4. **⟶⟶ Expert:** "Studied by" → experts who authored those papers (derived edge).
5. **⟶⟶ Oracle:** **"Ask the Oracle about furanthiols in plant bases"** → answer that *re-cites* the
   same papers, confirming traceability, and may surface adjacent molecules as new chips → user can
   branch again.

### Journey C — Expert-first (partnership / network-driven, e.g. WUR scouting)

1. User enters via **Map** (expert map, live-data-backed) → globe + ranked list + `#mcFilterBar`
   (search / country / sort: relevance·h_index·papers / top-rated toggle).
2. Selects an expert (e.g. a Wageningen author) → **Expert profile**: relevance rationale, org, topics,
   their papers.
3. **⟶⟶ Literature:** opens one of their **Papers** → Paper detail.
4. **⟶⟶ Molecule:** from that paper, jumps to a **Molecule** it measures.
5. **⟶⟶ Oracle:** **"What has this group contributed on <molecule>?"** → cited synthesis across their
   corpus. Cross-jumps complete; user can add the expert to a shortlist (nice-to-have).

> All three journeys converge on the same loop: **any entity → its neighbours → the Oracle → new
> entities.** The Oracle is both an entry point (A) and a return/synthesis point (B, C).

---

## 4. Annotated wireframes (mapped to the 4-region app-shell)

**App-shell regions (from `meatcode_mockup.html`, do not change):**
`TOPBAR 64px` (brand + GFI co-brand + global search + bell/profile) ·
`CONTEXT PANEL 248px` (left; persistent "where am I + related") ·
`CANVAS` (center; the active screen) ·
`DOCK 88px` (bottom; tool/domain switch).

### 4.1 Research workspace / home (the unified hub)

```
┌───────────────────────────────────────────────────────────────────────────── TOPBAR 64 ──┐
│ [MeatCODE]  ·GFI       ⌕ global search (papers · molecules · experts)          🔔  (avatar) │
├───────── CONTEXT 248 ──────────┬────────────────── CANVAS ──────────────────────────────────┤
│ RESEARCH                        │  eyebrow: RESEARCH · your workspace                          │
│ ○ Ask the Oracle   ← active     │  ┌──────────────────────────────────────────────────────┐  │
│ ○ Literature (818)              │  │  ORACLE ASK-BAR (hero)                                 │  │
│ ○ Molecules (799)               │  │  “Ask across 818 sources, 374 experts, 799 molecules…” │  │
│ ○ Experts (374)                 │  │  [ ask ▷ ]        chips: try “roasted note in analogs” │  │
│ ─────────────────               │  └──────────────────────────────────────────────────────┘  │
│ RELATED (context-aware)         │  THREE RESOURCE CARDS (cross-links, not silos):             │
│  · none yet — ask or pick       │  ┌── Literature ──┐ ┌── Molecular ──┐ ┌── Expert Map ──┐    │
│                                 │  │ teal accent    │ │ coral accent  │ │ olive accent   │    │
│                                 │  │ 818 · ranked   │ │ 799 · 45 cited│ │ 374 · ranked   │    │
│                                 │  │ → browse/filter│ │ → browse      │ │ → globe+list   │    │
│                                 │  └────────────────┘ └───────────────┘ └────────────────┘    │
│                                 │  RECENT ENTITIES (breadcrumb memory) · SAVED (nice-to-have) │
├──────────────────────────────── DOCK 88 ──────────────────────────────────────────────────────┤
│  [Map]   [Oracle]   [Research●]   [Toolbench]   [Simulate ·Preview]                            │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
```
**Annotations.** The hub leads with the Oracle ask-bar (Principle 1). The three resource cards use the
existing per-domain accent language (teal/coral/olive). The context panel's **RELATED** block is the
persistent cross-link surface — it fills in as the user traverses. Counts are pulled live so the UI
never lies about corpus size.

### 4.2 Oracle answer with cross-links (the connective screen)

```
┌── CONTEXT 248 ─────────────┬──────────────────── CANVAS ───────────────────────────────────┐
│ ANSWER CONTEXT              │  Q: What drives the roasted, meaty note in plant patties?      │
│  Sources used: 6            │  ┌─────────────────── ORACLE ANSWER BLOCK ──────────────────┐ │
│  Relevance filter: ≥60      │  │ Roasted/meaty character in plant bases is driven largely  │ │
│  Retrieval: FTS (keyword)   │  │ by Maillard products — pyrazines and 2-AP [1] — and       │ │
│ ─────────────               │  │ sulfur-bearing furanthiols formed via the thiamine        │ │
│ ENTITIES IN ANSWER          │  │ route [2]. Lipid oxidation cross-talk modulates … [3].    │ │
│  Molecules                  │  │  [1] and [3] are CLICKABLE → open that Paper detail        │ │
│   ⬡ 2-acetyl-1-pyrroline    │  └───────────────────────────────────────────────────────────┘ │
│   ⬡ furanthiols             │  ENTITIES IN THIS ANSWER  (the connective strip):              │
│  Papers                     │   [⬡ 2-AP] [⬡ furanthiols]   ← molecule chips ⟶ Molecule       │
│   ▤ Maillard×lipid…  [1]    │   [▤ Paper 1] [▤ Paper 2] [▤ Paper 3]  ← ⟶ Literature          │
│   ▤ Thiamine route… [2]     │   [◐ Expert A] [◐ Expert B]           ← ⟶ Expert profile        │
│  Experts                    │  ─────────────────────────────────────────────────────────    │
│   ◐ (authors of above)      │  Follow-up ask ▷   ·   ⚑ Not enough sources? → shows honestly  │
└─────────────────────────────┴────────────────────────────────────────────────────────────────┘
```
**Annotations.** Inline `[n]` markers ARE paper links (citation→entity). The **ENTITIES IN THIS ANSWER**
strip is the heart of the whole design — it converts a prose answer into graph jump-points across all
three resources. Context panel exposes retrieval provenance (source count, `relevance_llm ≥ 60` filter,
"keyword/FTS" so we don't imply semantic search we don't have yet). Empty-answer state is explicit.

### 4.3 Molecule detail

```
┌── CONTEXT 248 ─────────────┬──────────────────── CANVAS ───────────────────────────────────┐
│ Breadcrumb                  │  ⬡  2-acetyl-1-pyrroline            (name in MONOSPACE)         │
│ Oracle answer › 2-AP        │  class: N-heterocycle · role: roasted/popcorn note              │
│ ─────────────               │  ┌── CITED PATHWAY / CLAIMS ──────────────────────────────────┐ │
│ RELATED                     │  │ Proline + reducing sugar → … 2-AP  [cited: Paper 2]        │ │
│  Papers referencing (N)     │  │ ⚑ if no claim rows: “Hypothesis — not yet source-backed”   │ │
│   ▤ …                       │  └────────────────────────────────────────────────────────────┘ │
│  Studied by (experts)       │  APPEARS IN  ▤ Paper A · ▤ Paper B …      ⟶ Literature          │
│   ◐ …                       │  STUDIED BY  ◐ Expert X · ◐ Expert Y      ⟶ Expert profile      │
│                             │  ────────────────────────────────────────────────────────      │
│                             │  [ Ask the Oracle about 2-AP ▷ ]         ⟶ Oracle (scoped)      │
└─────────────────────────────┴────────────────────────────────────────────────────────────────┘
```
**Cross-nav affordances:** APPEARS IN → Literature · STUDIED BY → Expert · "Ask the Oracle" → Oracle.
Claims panel is honest about thin data.

### 4.4 Literature / paper detail

```
┌── CONTEXT 248 ─────────────┬──────────────────── CANVAS ───────────────────────────────────┐
│ Breadcrumb                  │  ▤  Maillard × lipid cross-talk in plant bases                 │
│ … › Paper                   │  venue · year · priority_score ●●●●○ · relevance_llm 84        │
│ ─────────────               │  topics (taxonomy chips): flavor_chemistry · meat_analogs      │
│ RELATED                     │  ┌── ABSTRACT ───────────────────────────────────────────────┐ │
│  Molecules mentioned        │  │ …                                                          │ │
│   ⬡ 2-AP · ⬡ furanthiols    │  └────────────────────────────────────────────────────────────┘ │
│  Authors                    │  MOLECULES MEASURED  ⬡ 2-AP · ⬡ …        ⟶ Molecule            │
│   ◐ …                       │  AUTHORS  ◐ Expert A · ◐ Expert B        ⟶ Expert profile      │
│                             │  ────────────────────────────────────────────────────────      │
│                             │  [ Ask the Oracle about this paper ▷ ]   ⟶ Oracle (scoped)      │
└─────────────────────────────┴────────────────────────────────────────────────────────────────┘
```
**Annotations.** `priority_score` + `relevance_llm` shown as trust signals (both exist in DB). Taxonomy
chips are filter-jump-points back into Literature. MOLECULES MEASURED / AUTHORS are the cross-edges.

### 4.5 Expert profile

```
┌── CONTEXT 248 ─────────────┬──────────────────── CANVAS ───────────────────────────────────┐
│ Breadcrumb                  │  ◐  Dr. A. Researcher            org · country                  │
│ Map › Expert                │  relevance_score ●●●●● · h_index · #papers    (WHY it ranked)   │
│ ─────────────               │  topics: flavor_chemistry · analytics                          │
│ RELATED                     │  ┌── PAPERS (N, on-topic) ──────────────────────────────────┐ │
│  Papers (N)                 │  │ ▤ … ▤ …                                   ⟶ Literature     │ │
│  Molecules (derived)        │  └────────────────────────────────────────────────────────────┘ │
│  Org / colleagues           │  STUDIES (molecules, via papers) ⬡ …      ⟶ Molecule           │
│   (co-auth edges EMPTY →    │  ────────────────────────────────────────────────────────      │
│    show org, not fake links)│  [ Ask the Oracle about their work ▷ ]   ⟶ Oracle (scoped)     │
│                             │  [ + Add to shortlist ]  (nice-to-have)                        │
└─────────────────────────────┴────────────────────────────────────────────────────────────────┘
```
**Annotations.** Relevance rationale visible (Principle 3). **No fake co-authorship graph** — the
`expert_relations` table is empty, so we show org affiliation instead. PAPERS → Literature, STUDIES →
Molecule, "Ask the Oracle" → Oracle.

---

## 5. IA & navigation model

**Recommendation: make Research the unified hub; keep Map & Oracle as deep-view entry points into it.**

- **Research becomes the container**, not a peer of Map/Oracle. Inside Research live the four resources
  as *views*: `Ask the Oracle` · `Literature` · `Molecules` · `Experts`. This resolves the long-standing
  "two competing nav systems" issue flagged in DESIGN_NOTES_v8 (top domain bar vs. bottom dock overlap).

- **Dock (88px)** stays the top-level switch between *modes of work*: `Map` (spatial expert view),
  `Oracle` (conversational full-screen), `Research●` (the unified workspace — default), `Toolbench`,
  `Simulate ·Preview`. **Map and Oracle in the dock are the same data as the Research views**, just
  presented in their native full-screen form — clicking an entity in either drops the user into the
  Research workspace with breadcrumb intact. (I.e. the dock switches *presentation*, Research switches
  *resource*, and they share one entity model.)

- **Context panel (248px)** is repurposed as the **persistent IA rail**: top half = the four resource
  views (with live counts), bottom half = **RELATED** (context-aware neighbours of the current entity) +
  breadcrumb memory. This is what makes cross-linking feel continuous rather than like page hops.

- **Breadcrumb model.** A single running trail across resources, e.g.
  `Oracle answer › 2-AP › Paper: Maillard×lipid › Expert: A. Researcher`. Each hop is clickable to
  return. The trail persists across resource switches (that's the whole point — the user's *investigation*
  is the unit, not the screen). Cap the visible trail at ~4 with a "…" overflow.

- **Global search (topbar)** is a unified typeahead across all three entity types (papers · molecules ·
  experts), grouped by type, each result a direct jump into its detail screen. It is the non-conversational
  twin of the Oracle.

- **Toolbench / Simulate** stay out of the core loop for the MVP (narrow-MVP discipline); Simulate stays
  labelled **Preview**.

---

## 6. Component inventory (for the prototype agent)

| Component | Purpose | Key states / notes |
|-----------|---------|--------------------|
| **Entity card** | Compact card for a paper / molecule / expert in lists & related-rails | 3 type variants (▤ paper teal · ⬡ molecule coral · ◐ expert olive); shows the 1–2 trust signals that exist (priority_score / relevance) |
| **Cross-link chip** | Inline jump-point to a related entity (in Oracle strip, related rail, detail lists) | typed icon + label; hover = preview tooltip; click = navigate + extend breadcrumb |
| **Citation→entity link** | The `[n]` marker inside Oracle prose that IS a paper link | numbered; on click opens that Paper detail; on hover shows title |
| **Oracle answer block** | Streamed answer + provenance + ENTITIES strip | states: idle · streaming (SSE) · answered · **no-sources (honest empty)** · error; provenance line shows source count + `relevance_llm ≥ 60` + "keyword/FTS" |
| **Breadcrumb trail** | Persistent cross-resource investigation path | clickable hops, 4 + overflow, survives resource switches |
| **Filter rail** | Left/inline filters for Literature & Molecules; reuse Map's `#mcFilterBar` pattern for Experts | only DB-backed facets (topics, priority band, country, sort); live count; loading/empty/error states |
| **Related rail (context panel section)** | Context-aware neighbours of current entity | groups: Papers / Molecules / Experts; hides empty groups (e.g. co-auth) |
| **"Ask the Oracle about this" button** | Entity → scoped Oracle question seed | present on every detail screen; pre-fills ask-bar, switches to Oracle answer view |
| **Resource-view switcher** | The 4 views inside Research (context-panel top) | active state; live counts |
| **Empty/honest-data state** | When claims/edges/sources are thin | "Hypothesis — not yet source-backed" / "Not enough sources yet" — a designed state, not an error toast |

All components inherit tokens from `meatcode_mockup.html` `:root` (teal `--wine #00736E`, deep
`--wine-deep #015A56`, coral `--brass #C77E5F`, olive `--olive #7A8C5F`, cream `--bg #FAF6EF`, Varela
Round, `--shadow`, 12–14px radii, pill/rounded shapes).

---

## 7. Handoff notes to the prototype agent

**Build order (must-have → nice-to-have):**

1. **MUST — the Oracle answer + ENTITIES strip (§4.2).** This is the connective-tissue proof. Even with
   mock chips, it demonstrates the whole thesis. Wire the `[n]` citation → Paper detail link.
2. **MUST — the three detail screens (Molecule §4.3, Paper §4.4, Expert §4.5)** with their cross-nav
   affordances (APPEARS IN / MOLECULES MEASURED / AUTHORS / STUDIES / "Ask the Oracle"). These make the
   graph traversable end-to-end.
3. **MUST — the persistent breadcrumb + context-panel RELATED rail (§5).** Without it, cross-jumps feel
   like disconnected pages and the "one investigation" story collapses.
4. **MUST — the Research hub (§4.1)** as the default landing, leading with the Oracle ask-bar.
5. **SHOULD — global typeahead search** across the three entity types.
6. **NICE — shortlist/save, follow-up threading in the Oracle, hover-preview tooltips on chips.**

**Guardrails (do not violate):**
- **Never render `expert_relations` co-authorship edges** — table is empty; show org affiliation instead.
- **Frame molecule claims/pathways as cited hypotheses** — only 45 claims exist; use the honest empty
  state when a molecule has none.
- **Show real corpus counts** (≈818 / 799 / 374) — no rounded-up "1,000+" in the Research surface.
- **Label Oracle retrieval as keyword/FTS** in the provenance line (pgvector hybrid is future).
- **Keep Simulate as Preview.** Stay inside the 4-region app-shell and the teal token set — no wine palette.

**Data hooks that already exist (reuse, don't rebuild):**
- `GET /api/ask` (SSE: `sources/chunk/done`) — Oracle answer + its source list (feeds the ENTITIES strip).
- `GET /api/experts`, `/api/experts/{id}`, `/api/expert-facets` — Expert profile + Map filter rail.
- `GET /api/papers/{id}`, `/api/papers/recent` — Paper detail + Literature list.
- Molecule endpoints are **not yet built** — prototype the Molecule screen against mock/fixture data and
  flag it for the data-eng agent (this is the one resource whose API is missing).

---

_End of spec. Owned by the UI/UX Designer (screenflow). Prototype HTML, PROJECT_STATE.md, and
AGENT_UPDATE_LOG.md are owned by other agents — this file does not edit them._
