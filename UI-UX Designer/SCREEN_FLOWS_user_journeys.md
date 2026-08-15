_Last updated: 2026-08-15 14:59 UTC · Advisory · screen-flow user journeys + IA (6 cross-nav flows)_

# MeatCODE — Screen-Flow User Journeys & IA (6 cross-navigation flows)

> **Scope.** This is the journey + information-architecture spec for the **six cross-navigation screen
> flows** that wire MeatCODE's standalone scenes into one end-to-end experience. A partner UI/UX agent
> owns the interactive wireframe (`screen_flows_wireframes.html`); **this file owns the journeys, the
> context-handoff model, states/edges, MVP mapping, and build-readiness.** It **extends** the 5 canonical
> MVP journeys (`docs/MeatCODE_MVP_Definition_and_User_Journeys.md`) and the Research screenflow IA
> (`UI-UX Designer/RESEARCH_SCREENFLOW_SPEC.md`) — it does not duplicate or contradict them.
>
> **Reality anchor (from `PROJECT_STATE.md` + the live code, verified this session).**
> Scenes that actually exist in `app/meatcode_mockup.html`: `home · oracle · map · research ·
> research-sub · database · toolbench · toolbench-tools · simulate · molecule-detail · protocol-detail`.
> Live `GET` endpoints in `server/meatcode_server.py`: `/api/experts`, `/api/experts/{id}`,
> `/api/expert-facets`, `/api/molecules` (list; `offset`/`meta`/`q`), `/api/molecules/{id}` (detail —
> returns `{…, mentions_count, papers[]}`), `/api/molecule-suggestions`, `/api/sources`, `/api/companies`,
> `/api/db-facets`, `/api/papers/{id}`, `/api/papers/recent`. Live `POST`: `/api/ask` (grounded RAG, SSE:
> `status → sources → chunk → done`). **Does NOT exist:** `/api/protocols` (the `protocol-detail` scene is a
> hardcoded template), any compare/diff endpoint, any GC-MS or simulation compute endpoint (the `simulate`
> results table is **hardcoded HTML** with real molecule *names* but **no molecule ids**). Feature flags live
> in `Release Center/features.json` (per-env `dev`/`prod` booleans; the mockup reads `/api/flags` for the
> current env). **Keep this spec honest to that — do not assume backends the server lacks.**

---

## 0. Cross-flow model — the one architectural insight (read this first)

All six flows are the **same operation** with different endpoints. Each is a jump from a *source scene* to a
*target scene* that carries a small **selection + context payload**, and the target renders an **arrival
state** derived from that payload. Formalize this once and all six become instances of it.

**The entity + context handoff bus.** A cross-nav jump is four moves:

1. **Capture** — the source scene captures the user's selection as a typed payload:
   `{ type: 'molecule'|'source'|'expert'|'protocol'|'sim', ids: [...], names: [...], query?, filter?, simInputs? }`.
2. **Stash** — write the payload to a shared client-side context store. **This already exists in embryonic
   form**: `localStorage` keys `mc_mol_focus_id` / `mc_mol_focus_name` (consumed by `mcOpenMoleculeDetail()`),
   plus `mc_recent_molecules_v1` / `mc_recent_protocols_v1`. Generalize these into a single
   `mcHandoff(payload)` / `mcConsumeHandoff()` pair keyed by target scene.
3. **Route** — navigate by `location.hash = '#<target>'`; the existing `setScene()` dispatcher fires the
   scene's on-enter hook (as `mcOpenMoleculeDetail()` already does for `#molecule-detail`).
4. **Consume** — the target scene reads the payload on enter, sets its **arrival state** (pre-filtered table /
   pre-seeded ask box / pre-loaded sim inputs / compare columns), renders a **breadcrumb** back to the source,
   and clears the one-shot payload so a manual visit later starts clean.

**Why this matters.** The MVP's edges are thin (co-authorship empty, molecule↔paper sparse — see the Research
spec §2). The connective value of MeatCODE is therefore **not** a dense knowledge graph; it is these
*deliberate, context-preserving jumps* between the four resources + the Oracle + the sim. The handoff bus **is**
the product's "one investigation, not six screens" story. Build the bus once (a ~30-line `mcHandoff` helper +
a shared breadcrumb component) and every flow below is wiring on top of it. **Recommended: ship the bus as the
first task; it is the shared dependency of all six flows and the partner's wireframe.**

**Shared identity join.** Every jump needs a stable key. Molecules, sources, experts, and companies all have
real ids from the DB endpoints — those flows can carry ids. **The two weak joins are (a) the Oracle answer's
prose→entity resolution (already solved for molecules via `/api/molecule-suggestions`; not yet for sources
beyond the cited `sources[]` list), and (b) the simulation, whose rows are names with no ids.** Wherever an id
is missing, the flow must fall back to a **name→id resolution shim** (`/api/molecules?q=<name>`) and degrade
honestly when the name doesn't resolve.

**Universal edge states (apply to every flow; not repeated in full below).**
- **Loading** — target scene shows a skeleton of its arrival state, never a blank flash (Neon cold-start can add a few seconds).
- **Empty / no-match** — the payload resolved to zero rows (e.g. a cited molecule not in `molecules`, a sim name that doesn't join): show a first-class "nothing to show for this selection" state with a one-click "show all / clear filter" escape, **never** a silent empty table.
- **Error** — endpoint 404/500 or DB unreachable: keep the user on a usable screen with a plain-language notice + retry; degrade to the un-filtered target rather than a dead end.
- **Single vs multi-select** — flows 1, 2, 5 can carry >1 id; the target must render a *set* (filtered list / N compare columns / N rows highlighted). Flows 3, 6 are single-entity.
- **Back / return** — a running breadcrumb (`Oracle answer › Molecules (3 cited)`) whose hops are clickable; the payload is one-shot so Back restores the source scene state, not a re-consumed jump.

---

## 1. Flow 1 — Oracle → Raw table data

**MVP mapping:** extends **J1 (Scientific Question)** into **J3 (Knowledge Discovery)** — the answer becomes a
door into the raw corpus.

**User goal / trigger.** A researcher reads an Oracle answer and wants to *audit or browse the underlying raw
rows* — "show me every molecule/source this answer leaned on, in the real table, so I can sort, filter and
export." Trust move: see the data behind the prose.

**Entry point.** `#oracle`, **answered** state. The answer already carries two id-bearing artifacts: the SSE
`sources` event (each cited paper with its id) and the **related-molecule chip row** rendered from
`/api/molecule-suggestions` (each chip already routes into `#database` molecules — this partial jump ships
today, per PROJECT_STATE v12.5).

**Step-by-step journey.**
1. Answer completes; below it sit **"Sources used (N)"** and **"Related molecules"** rows.
2. User clicks **"Open these in the table →"** (net-new affordance) on either group, or clicks a single chip.
3. **Capture:** `{ type:'molecule'|'source', ids:[…cited ids…], query:<original question, for the breadcrumb> }`.
4. **Route** to `#database`, **Consume** selects the correct tab (Molecules or Sources) and applies the id set.
5. **Arrival state:** Database scene, correct tab, **filtered to exactly the cited rows**, breadcrumb
   `Oracle answer › Molecules (3 cited)`, and the existing **⤓ Export (.xlsx)** available on the filtered set.

**Context handed off.** Entity type + the list of cited ids (molecule ids from suggestions, source ids from the
SSE `sources` payload) + the question string for the breadcrumb label.

**States & edges.** Multi-select is the default here. If a cited molecule name has no `molecules` row →
that chip is simply absent from the set (never a broken row); if *none* resolve → the "no matching rows,
show all molecules" empty state. Loading = the table's own skeleton. Back returns to the exact answer.

**Build-readiness — BUILDABLE NOW (thin gap).** The molecule half already ships (chip→DB jump). To filter the
table to a **specific set of ids** the list endpoints need a small `ids=` query param (`/api/molecules?ids=…`,
`/api/sources?ids=…`) — *or*, as a zero-backend MVP, filter the returned page **client-side** to the cited id
set. The Sources-tab jump (from the SSE `sources[]`) is net-new wiring but needs **no new endpoint**.
**Recommend a feature flag** (`oracle_to_table`) while the `ids=` filter and the Sources jump settle.

---

## 2. Flow 2 — Oracle → Data Comparison  *(net-new screen)*

**MVP mapping:** extends **J1 → J3** and supports **J4 (Research Planning)** — comparing candidates is a
planning act.

**User goal / trigger.** After an answer (or a direct ask like *"compare 2-furfurylthiol vs
2-acetyl-1-pyrroline"*), the user wants a **side-by-side** of 2+ entities on shared attributes — class, taste,
mentions_count, top papers, relevance — instead of opening each detail page in turn.

**Entry point.** `#oracle` answered state (multi-select 2+ related-molecule chips), **or** the Database table
(check-select 2+ rows → "Compare"), **or** a molecule-detail "Compare with…" affordance. Primary entry for
this flow: the Oracle chip row.

**Step-by-step journey.**
1. User selects 2–4 molecule chips (checkbox/long-press multi-select) and clicks **"Compare (3) →"**.
2. **Capture:** `{ type:'molecule', ids:[a,b,c] }` (a compare payload — a *set*, order preserved).
3. **Route** to `#compare` (the net-new scene), **Consume** reads the id set.
4. **Arrival state:** a **columns-per-entity** layout (one column each), rows = shared attributes; values
   fetched by calling the **existing** `/api/molecules/{id}` once per selected id and aligning the fields;
   differing cells subtly highlighted; each column header links to that molecule-detail; an **"Ask the Oracle
   to compare these"** button seeds a scoped question back into Flow 3's target.

**Context handed off.** The ordered id set (2–4). No query needed; the compare view *is* the query.

**States & edges.** Min 2 / soft-max 4 columns (beyond that the layout scrolls horizontally). If an id fails to
resolve, its column shows an honest "couldn't load this entity" placeholder rather than dropping silently
(keeps the comparison count truthful). Loading = per-column skeletons that fill independently. Empty attribute
cells are shown as "—", **not** hidden (a comparison needs the gaps visible). Back returns to the source
selection with the chips still selected.

**Build-readiness — BUILDABLE NOW as a client-side compose; net-new UI.** No compare endpoint is *required* for
molecules: the screen is an **N-way fan-out over `/api/molecules/{id}`** aligned client-side. A dedicated
`/api/compare?type=molecule&ids=…` is a **nice-to-have optimization** (one round-trip, server-side field
alignment), not a blocker — mark it **design-only / phase-2**. Expert and source comparison would reuse the
same pattern over `/api/experts/{id}` and `/api/papers/{id}`. **Ship behind `data_compare` flag** (net-new
scene, dev-first) — this is the highest-wow net-new flow and the cleanest to keep flag-gated.

---

## 3. Flow 3 — Raw Data → Oracle

**MVP mapping:** extends **J3 (Discovery) → J1 (Oracle)**; also the return-loop of Research Journey A/B/C.

**User goal / trigger.** From a Database row (or molecule-detail), the user wants to **ask the Oracle about
that specific entity** without retyping — "explain the meaty relevance of this molecule / summarize what this
paper found." Context pre-filled.

**Entry point.** `#database` row context-menu / row action, **or** `#molecule-detail` (which per the Research
spec already specs an **"Ask the Oracle about this"** button), **or** a Sources/paper row.

**Step-by-step journey.**
1. User clicks **"Ask the Oracle about this →"** on a molecule/source/expert row or detail page.
2. **Capture:** `{ type, id, name, query:<templated question> }` — e.g. molecule → *"What is the sensory role
   and meaty relevance of {name}, and which sources support it?"*; paper → *"Summarize the key findings of
   {title} relevant to meaty flavor."*
3. **Route** to `#oracle`, **Consume** pre-fills the ask box with the templated question (editable), then
   invokes the existing `askOracle()` to stream a grounded answer.
4. **Arrival state:** Oracle scene, ask box pre-seeded and visible, answer streaming; the answer's own
   sources/chips then feed **Flow 1/2** — closing the loop the Research spec describes.

**Context handed off.** Entity type + id + name + the templated (editable) question string.

**States & edges.** Single-entity. The user can edit the seeded question before it fires (do **not** auto-send
without showing the text — the user must see what's being asked). If the corpus doesn't cover the entity, the
Oracle's existing honest "the corpus doesn't cover this" refusal is the empty state — correct behavior, not an
error. Breadcrumb `Molecules › {name} › Oracle`. Back returns to the row.

**Build-readiness — FULLY BUILDABLE NOW, zero new backend.** `/api/ask` exists and is grounded; `askOracle()`
and ask-box pre-seed already exist (Home already pre-seeds and routes into Oracle). This flow is **pure
front-end wiring** — the lowest-effort, highest-trust flow of the six. **No flag strictly needed** (it degrades
to a normal Oracle ask), though gating under `data_to_oracle` during rollout is cheap insurance.

---

## 4. Flow 4 — Protocols → Data

**MVP mapping:** extends **J4 (Experimental Design / Research Planning)** — a protocol is only useful if its
referenced molecules, sources and benchmarks are one click away.

**User goal / trigger.** Reading a protocol, the user wants to jump to the **Data it references**: the target
molecules/volatiles, the source papers it's built on, and any benchmark rows — to verify or go deeper.

**Entry point.** `#protocol-detail`.

**Step-by-step journey (target design).**
1. Protocol detail shows **"Referenced molecules"**, **"Source papers"**, **"Benchmarks"** sections.
2. User clicks a referenced molecule / source.
3. **Capture:** `{ type:'molecule'|'source', ids:[…], query:'Protocol: {protocol name}' }`.
4. **Route + Consume** → `#molecule-detail` (single) or `#database` filtered (set), breadcrumb
   `Protocols › {protocol} › {molecule}`.
5. **Arrival state:** the molecule/source data screen, scoped to the protocol's referenced entities.

**Context handed off.** The protocol's referenced entity ids (molecules, sources).

**States & edges.** Same set/empty/error rules as Flow 1. Because the protocol corpus is fake today, the
"referenced entities" list is itself representative, so every edge here is provisional until the backend lands.

**Build-readiness — DESIGN-ONLY (blocked on backend).** `protocol-detail` is a **hardcoded template**;
**`/api/protocols` does not exist** and there is **no protocols table** (confirmed in PROJECT_STATE + MVP_ALIGNMENT
— J4 is design-only). The **target side is real** (molecule/source endpoints exist), so the moment a protocols
table + `/api/protocols/{id}` (returning real referenced molecule/source ids) ships, this flow is a thin wiring
job on the existing bus. **Until then: build the UI against fixture data, clearly label the protocol scene a
preview, and gate the whole flow behind a `protocols` feature flag (dev-only).** Do **not** imply the protocol
references are real corpus links in the 31 Aug demo.

---

## 5. Flow 5 — Simulation → Data

**MVP mapping:** extends **J2-adjacent / Simulate (preview) → J3 (Discovery)** — turn a prediction into
inspectable raw rows.

**User goal / trigger.** After a simulation run, the user wants to open the **predicted compounds as real
Database rows** — "these six volatiles you predicted: show me their real corpus entries, mentions, and papers."

**Entry point.** `#simulate`, results table (the hardcoded "Predicted volatile profile" table — real names like
`2-Methyl-3-furanthiol`, `2-Acetyl-1-pyrroline`, `2-Furfurylthiol`, no ids).

**Step-by-step journey.**
1. Each predicted-compound row gets an **"Open in Database →"** action (and a header **"Open all predicted →"**).
2. **Capture:** `{ type:'molecule', names:[…predicted compound names…] }` — **names, not ids** (the sim has no ids).
3. **Resolve:** the bus runs a **name→id shim** (`/api/molecules?q=<name>` per compound, best-match) to turn
   names into ids; unresolved names are flagged.
4. **Route + Consume** → `#database` molecules filtered to the resolved id set (or `#molecule-detail` for a
   single row), breadcrumb `Simulate › Cys×Ribose 110°C › Molecules (5 of 6 matched)`.
5. **Arrival state:** Database molecules scoped to the predicted compounds that exist in the corpus, with an
   honest "1 predicted compound not found in the corpus" note.

**Context handed off.** The list of predicted compound **names** + the sim run label (for the breadcrumb).

**States & edges.** Multi-select by nature. **The critical edge is name-resolution failure** — surface
"X of Y matched" explicitly; unmatched compounds get a "not in corpus yet" chip rather than vanishing (this is
also useful white-space signal). Loading = per-name resolution can be async. Error in resolution → fall back to
a `q=<first compound>` text filter so the user still lands somewhere sensible.

**Build-readiness — BUILDABLE NOW with a name-resolution shim; but sim is PREVIEW.** Target `/api/molecules`
exists and takes `q`. The gap is **the sim emits no molecule ids** and its table is hardcoded — so this flow is
a **preview→real bridge**: it works, but it sits on top of a simulation that is itself a labeled preview (no
compute engine). **Two honest options:** (a) client-side name→id resolution now (no backend change, fuzzy,
degrades gracefully); (b) when the sim is eventually made data-backed, have it **emit table-ready rows carrying
molecule ids** (a shared molecule-id join) so resolution becomes exact. **Ship behind `sim_to_data` flag,
dev-only, and keep the sim's "order-of-magnitude estimate, not first-principles" preview framing intact.**

---

## 6. Flow 6 — Data → Simulation

**MVP mapping:** extends **J3 (Discovery) → Simulate (preview)** and feeds **J4 (Experimental Design)** — take a
precursor from the corpus into a "what would this cook into?" run.

**User goal / trigger.** From a Database molecule (a **precursor** — an amino acid / reducing sugar / thiamine),
the user wants to **pre-load it into the Simulator** as a reaction input instead of re-typing the setup.

**Entry point.** `#database` molecules row, **or** `#molecule-detail`, with a **"Simulate with this precursor →"**
action.

**Step-by-step journey.**
1. User clicks **"Simulate with this →"** on a molecule row/detail.
2. **Capture:** `{ type:'sim-input', simInputs:{ precursor:{ id, name } } }`.
3. **Route + Consume** → `#simulate`, **pre-fill** the precursor field with the molecule (the sim's
   "Precursors" block already lists precursor rows — inject one), leave conditions at defaults, focus the
   **Predict** button. Breadcrumb `Molecules › {name} › Simulate`.
4. **Arrival state:** Simulate scene with the chosen precursor loaded, ready to predict.

**Context handed off.** The molecule id + name as a `precursor` sim input.

**States & edges.** Single-entity. **Semantic guard (important):** most `molecules` rows are *product volatiles*
(the corpus is mostly volatiles — Sulfur 210, Pyrazines 131…), **not precursors**. Loading a product volatile as
a "precursor" is chemically wrong. So this action should be **offered only on precursor-class molecules** (amino
acids, reducing sugars, thiamine) — or, if offered broadly, it must warn "this is a predicted product, not a
typical precursor." Empty/edge: if the molecule isn't a recognized precursor, disable the action with a tooltip
rather than silently loading a nonsensical run.

**Build-readiness — BUILDABLE NOW as UI pre-fill only; sim stays PREVIEW.** The Simulate scene is a hardcoded UI
with **no compute engine** — pre-filling a precursor is a **front-end-only** change (inject a `sim-prec` row from
the payload). No backend exists to *run* a real prediction, so the value is "smoother setup," not new science.
**Ship behind `data_to_sim` flag, dev-only**, gate the action to precursor-class molecules, and keep the sim's
preview label. When a real sim engine lands, this same handoff feeds it real inputs unchanged.

---

## 7. Priority / sequencing for the 31 Aug internal demo

The bar for the demo (per `MVP_ALIGNMENT.md`) is **make J1/J3/J5 credible; keep J2/J4/Simulate honest
previews.** These flows should reinforce that split, not paper over it. Ranked by **leverage × low effort**:

**Build the bus first (shared dependency).** Generalize `mc_mol_focus_id` into `mcHandoff()/mcConsumeHandoff()`
+ one breadcrumb component. ~½ day; unblocks all six flows and the partner's wireframe.

**P0 — ship for the demo (zero/low new backend, all reinforce credible journeys):**
1. **Flow 3 (Data → Oracle)** — *fully buildable now, zero backend.* The cleanest proof of the connected-platform
   thesis; every row becomes a question. Highest trust, lowest effort. **Do this first.**
2. **Flow 1 (Oracle → Raw table data)** — *buildable now;* molecule half already ships. Add the Sources jump +
   a client-side (or `ids=`) filter. Turns the Oracle answer into an auditable table — directly strengthens J1's
   "source-backed" claim.

**P1 — high-wow stretch, still buildable, flag-gated:**
3. **Flow 2 (Oracle → Data Comparison)** — *net-new scene, client-side over existing `/api/molecules/{id}`.* The
   most impressive net-new capability; no new endpoint required. Behind `data_compare`. Do if P0 lands early.

**Preview-only / do not over-promise at the demo:**
- **Flows 5 & 6 (Sim ↔ Data)** — buildable as name-resolution / UI pre-fill bridges, but they hang off the
  **Simulate preview**. Include only as clearly-labeled preview polish, feature-flagged (`sim_to_data`,
  `data_to_sim`), never as a headline.
- **Flow 4 (Protocols → Data)** — **design-only**; blocked on `/api/protocols` + a protocols table (neither
  exists). Build the UI on fixtures behind the `protocols` flag; do not present protocol references as real
  corpus links until the backend ships.

**One-line recommendation.** Ship the **handoff bus + Flow 3 + Flow 1** for 31 Aug (all buildable now, all
reinforce the credible J1/J3 spine), stretch to **Flow 2 comparison** behind a flag, and keep **Flows 4/5/6
explicitly preview/flag-gated** so the demo stays honest to what the backend can actually do.

---

_End of spec. Owned by Advisory. The wireframe (`screen_flows_wireframes.html`), `PROJECT_STATE.md`,
`AGENT_UPDATE_LOG.md`, and `TEAM_BROADCAST.md` are owned by other agents — this file does not edit them._
