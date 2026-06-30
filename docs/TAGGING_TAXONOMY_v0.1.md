# MeatCODE — Tagging Taxonomy v0.1

*Owner: Lior · Status: draft for review (Daniel sign-off + Asana "Define tagging taxonomy v0.1") · 2026-06-30*

---

## 1. Summary (the one-screen version)

Every item we ingest (starting with **literature sources**, later molecules, claims, experts) gets tagged along a small set of **controlled, faceted axes**. "Faceted" = each item carries tags on several independent axes at once, not one category. This is what makes the corpus searchable, filterable, and — critically — what lets us see **white spaces** (combinations no source covers).

v0.1 is deliberately **narrow to meaty process flavor** (the MVP scope) and **anchors on what already exists**: your `topics_hierarchy.csv` and the schema's existing facet tables/ENUMs. We are formalizing vocabularies, not rebuilding.

**The seven tagging axes (each maps to a real table/column already in the schema):**

| # | Facet (axis) | What it answers | Backed by (existing schema) |
|---|---|---|---|
| 1 | **Topic** | What subject is this about? | `topics` + `source_topics` (your hierarchy) |
| 2 | **Sensory attribute** | What does it smell/taste like? | `sensory_attributes` + `source_sensory_attributes` |
| 3 | **Analytical method** | How was it measured? | `analytical_methods` + `source_methods` |
| 4 | **Product context** | What product / protein / cook? | `product_contexts`, ENUMs `protein_source` / `cooking_method` / `ingredient_category` |
| 5 | **Process / reaction** | Which flavor-forming pathway? | `reactions` + ENUM `reaction_kind` |
| 6 | **Molecule role** | Precursor, volatile, masker…? | `molecule_role_tags` + ENUM `molecule_role` |
| 7 | **Evidence / relevance** | How strong, how relevant? | ENUMs `evidence_strength`, `actionability` + `trust_tier` |

**Tagging minimum for a source to count as "tagged":** ≥1 Topic, ≥1 Product context, and ≥1 Process *or* Sensory attribute. Methods and evidence where applicable.

---

## 2. Principles

1. **Controlled, not free-text.** Tags come from defined lists with stable `slug`s. Free text goes in notes, never in the tag fields. (Prevents "Maillard" / "maillard reaction" / "MRPs" fragmenting the corpus.)
2. **Faceted.** A paper on *hexanal in pea-protein burgers measured by GC-O* is tagged Topic=`lipid_oxidation`, Sensory=`beany`/`green`, Method=`gc_olfactometry`, Product=`plant_protein`+`burger`, Process=`lipid_oxidation`, Molecule role=`off_note_volatile`. Each axis is independent.
3. **Anchored on the existing hierarchy.** The Topic axis **is** your `topics_hierarchy.csv` (root branches: `analytics`, `flavor_chemistry`, …). Drop your updated topics `.md` into `db/taxonomy/` and it becomes the canonical Topic source; this doc references it, doesn't duplicate it.
4. **MVP-narrow.** Scope is positive meaty process flavor. Plant off-notes are tagged where they connect to process flavor (masking, precursor design), not exhaustively.
5. **Machine-first, human-gated.** The pipeline (Layer C typed extraction) proposes tags; a review gate confirms borderline ones. The vocabulary must be small enough for Claude to apply reliably.

---

## 3. The facets in detail (v0.1 controlled vocabularies)

### Axis 1 — Topic *(anchor on existing hierarchy)*
Source of truth: `db/taxonomy/topics_hierarchy.csv` (and your incoming `.md`). Already deep and good — e.g. `flavor_chemistry > Process flavor > Maillard > Sulfur chemistry > Thiols`. **No new list here; v0.1 keeps your hierarchy as-is.** Open decision: whether the `analytics` branch (GC-MS, SPME, AEDA, QDA, omics…) stays inside Topic *or* is promoted to be the Method axis (Axis 3). **Recommendation: promote analytics terms to the Method facet** and keep Topic for science subjects, so "what it's about" and "how it was measured" don't collide.

### Axis 2 — Sensory attribute *(starter controlled list)*
Meaty/positive: `meaty`, `roasted`, `grilled/charred`, `brothy/bouillon`, `umami`, `kokumi`, `fatty`, `nutty`, `caramel`, `sulfurous/eggy`, `blood/metallic-meaty`.
Off-notes (process-relevant): `beany`, `green`, `cardboard`, `metallic`, `bitter`, `astringent`, `oxidized/rancid`, `soapy`, `painty`.
*(Maps to existing `odours` / `sensory_attributes`. Keep ≤ ~30 at v0.1; expand with evidence.)*

### Axis 3 — Analytical method *(from your `analytics` branch)*
`gc_ms`, `gc_olfactometry`, `hs_spme`, `safe`, `aeda`, `lc_ms`, `hplc`, `gcxgc`, `e_nose`, `qda`, `cata_rata`, `threshold_oav`, `proteomics`, `lipidomics`, `metabolomics`, `volatilomics`, `nmr`, `ftir`, `ms`. *(Reuse the slugs already in `topics_hierarchy.csv`.)*

### Axis 4 — Product context *(three sub-dimensions, controlled)*
- **Protein source** (ENUM `protein_source`): `beef`, `pork`, `chicken`, `fish`, `plant_protein` (PPI/SPI), `cultivated`, `fermentation_biomass`, `blended/hybrid`.
- **Product form**: `burger`, `sausage`, `nugget`, `deli/cured`, `broth/stock`, `bacon`, `mince`, `whole_cut`, `fat/tallow`.
- **Cooking method** (ENUM `cooking_method`): `grill`, `roast`, `fry`, `boil`, `sous_vide`, `extrusion`, `smoke`.

### Axis 5 — Process / reaction *(ENUM `reaction_kind`)*
`maillard`, `strecker`, `lipid_oxidation`, `thiamine_degradation`, `nucleotide_degradation`, `caramelization`, `maillard_lipid_interaction`, `fermentation`, `enzymatic`.

### Axis 6 — Molecule role *(ENUM `molecule_role`, when a source/record is about a compound)*
`precursor`, `volatile`, `key_impact_odorant`, `off_note_volatile`, `masking_agent`, `taste_active` (e.g. kokumi peptide), `intermediate`.

### Axis 7 — Evidence & relevance
- **Evidence strength** (ENUM `evidence_strength`): `strong` (peer-reviewed, replicated/independent), `moderate`, `preliminary`, `anecdotal/applied`.
- **Actionability** (ENUM `actionability`): `directly_actionable`, `informative`, `background`.
- **Relevance tier** (pipeline `trust_tier`): Very ≥80% · Mid 60–80% · Little <60%.

---

## 4. Tagging rules

- **Per source minimum:** ≥1 Topic, ≥1 Product context, ≥1 Process *or* Sensory. Method + Molecule role + Evidence when the source supports it.
- **Granularity:** tag the most specific node that's true (e.g. `thiols`, not just `maillard`); ancestors are implied by the hierarchy.
- **Who assigns:** pipeline Layer C proposes → auto-accept if confidence ≥ threshold → else review-queue gate (the same approval flow that demos well for Daniel).
- **Slugs:** lowercase, underscore, stable. New terms get a slug + a one-line definition before use.

## 5. Governance & versioning
- Adding a term = PR to `db/taxonomy/` + one-line definition + which facet. No silent additions.
- Version bumps: v0.1 → v0.2 when a facet's vocabulary materially changes. Log the change in this file's header.
- Dedupe + controlled vocabulary is itself an Asana Phase-1 data-quality task — this doc is its spec.

## 6. Open questions for Lior
1. **Method as its own facet vs. inside Topic?** (Recommendation: promote — see Axis 1/3.)
2. Drop your topics **`.md`** into `db/taxonomy/`; I'll reconcile it as the canonical Topic axis and flag any collisions with the facet slugs above.
3. Confirm the v0.1 **sensory** starter list (Axis 2) is the right ~30 — add/remove before we tag at scale.
4. Confirm scope call: how much off-note vocabulary to include now vs. defer (currently: only process-flavor-connected).
