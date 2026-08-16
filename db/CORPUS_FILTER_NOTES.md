_Last updated: 2026-08-16 14:50 UTC · Data Engineer · Research chip→slug rationale + /api/corpus SQL spec + honest thin-chip list. All 40 distinct slugs (51 uses across 24 chips) validated vs the taxonomy bible — 0 corrections needed._

# Corpus filter notes — Research chips → taxonomy slugs → `/api/corpus`

**Companion to `db/research_chip_map.json`.** That JSON is the chip→slug contract the mockup and
`server/meatcode_server.py` code against; this file is the *why*, the *SQL the endpoint should run*,
and the *honest coverage flags*.

> **Live counts are the endpoint's job, not this file's.** Every count a reviewer sees comes from
> `GET /api/corpus?phase=&topics=<slug,slug>` hitting Neon at request time. The `backing` field in the
> JSON (`strong|medium|thin`) is a **design-time coverage hint**, never a number. If `/api/corpus`
> returns 0 for a slug, the UI greys that chip **regardless** of its `backing` hint. (There are no Neon
> credentials in the build sandbox, and that is fine — this map is validated against the taxonomy bible;
> the counts are validated at runtime.)

---

## 1. Slug validation result

Every `topic_slug` in `research_chip_map.json` was checked against the taxonomy bible
(`db/taxonomy/keywords_topics.json`, 91 keywords / 5 branches) with a throwaway loader that asserts
presence and cross-checks each chip's declared `branches` against the bible-derived branches:

- **24 chips** across 3 phases (Juice 9 · Lipid 9 · Analytics 6), **40 distinct slugs**.
- **All 40 slugs exist in the bible. 0 corrections were required** — the provisional mapping was already
  clean, so the UI/server slug contract stays **stable** (no reconciliation needed from the Coordinator).
- Every chip's `branches` array equals the union of its slugs' real branches in the bible.
- `backing` tally: **5 strong · 10 medium · 9 thin.**

Because nothing was renamed, there is no slug drift for Full-Stack or UI to absorb.

---

## 2. Why each phase maps to those branches

**Juice = the aqueous Maillard-precursor story.** Water-soluble precursors and what they become on
heating. Chips lean on **`flavor_chemistry`** (primary sugars, amino acids, Strecker degradation,
peptides, pyrazine/furan products) for the precursor→Maillard chemistry, on **`flavor_ingredients`**
for the hydrolysate/seasoning routes that deliver that chemistry as ingredients (HVP, yeast extract,
enzymatic processing, salt enhancers, bitter blockers, reaction/process flavors), and on
**`meat_science`** for the aroma/brining anchors (`meat_aroma`, `brining`). One chip reaches into
**`meat_analogs`** (`plant_based_proteins`) because "plant-juice volatiles" is inherently an analog topic.

**Lipid = the lipid-oxidation story.** Fat-derived aldehydes/ketones/lactones and the routes that make
them. Chips lean on **`flavor_chemistry`** (`lipid_oxidation_topic`, `beta_oxidation`,
`lipoxygenase_pathway`, `maillard_lipid`), plus the **`flavor_ingredients`** fat-structuring anchor
(`structured_fats_topic`) and the **`meat_science`** heat anchor (`thermal`, for frying). This is
the branch the corpus is thinnest on (see §4), so Lipid honestly skews medium/thin.

**Analytics = the analytics branch of methods, 1:1.** Every Analytics chip maps straight into the
**`analytics`** branch — GC-MS/HS-SPME/GC-O, HPLC/LC-MS, the olfactory/sensory cluster (GC-O, sniffing,
AEDA, QDA, threshold testing, consumer panel), NMR, MS/FTIR, and the omics cluster. This is the
richest, entirely HIGH-priority branch, so Analytics chips carry the strongest backing.

---

## 3. The SQL `/api/corpus` should run

Confirmed live schema (read from `server/meatcode_server.py`, the `/api/molecules/{id}` +
`/api/db-facets` handlers): `sources(id, relevance_llm, priority_score, year, …)` ⋈
`source_topics(source_id, topic_id)` ⋈ `topics(id, slug, name)`; molecules via
`source_molecules(molecule_id, source_id)` ⋈ `molecules(id, is_junk, …)`. `/api/corpus` does **not**
exist yet — this is the spec for Full-Stack to implement (SELECT-only, parameterized, same `pg_rows`
pattern as the other endpoints).

The endpoint takes `topics=<slug,slug,…>` (the chip's `topic_slugs`) and optional `phase=` (use it to
scope/validate which slugs are legal for that phase against `research_chip_map.json`; the actual filter
is the slug list). Bind the slug list once as a `text[]` (`%(slugs)s`).

### 3a. Per-slug source counts — drives each chip's badge and the grey-out
`LEFT JOIN` off the *requested* slug list so a 0-count slug still returns a row (→ UI greys it) instead
of silently vanishing:

```sql
SELECT req.slug,
       COUNT(DISTINCT s.id) AS source_count
FROM   unnest(%(slugs)s::text[]) AS req(slug)
LEFT   JOIN topics        t  ON t.slug = req.slug
LEFT   JOIN source_topics st ON st.topic_id = t.id
LEFT   JOIN sources       s  ON s.id = st.source_id
       AND (s.relevance_llm IS NULL OR s.relevance_llm >= 60)   -- Oracle relevance gate; see note
GROUP  BY req.slug;
```

### 3b. Deduped total sources across the selected slugs — the phase/selection headline
A source tagged to two selected slugs must count **once** → `COUNT(DISTINCT s.id)`:

```sql
SELECT COUNT(DISTINCT s.id) AS total_sources
FROM   sources       s
JOIN   source_topics st ON st.source_id = s.id
JOIN   topics        t  ON t.id = st.topic_id
WHERE  t.slug = ANY(%(slugs)s)
  AND  (s.relevance_llm IS NULL OR s.relevance_llm >= 60);
```

### 3c. Molecule total — distinct molecules mentioned by those sources
Join through `source_molecules`; respect the `is_junk` flag from migration 0009 so quarantined junk
molecules never inflate the count:

```sql
SELECT COUNT(DISTINCT sm.molecule_id) AS total_molecules
FROM   source_molecules sm
JOIN   sources       s  ON s.id = sm.source_id
JOIN   source_topics st ON st.source_id = s.id
JOIN   topics        t  ON t.id = st.topic_id
JOIN   molecules     m  ON m.id = sm.molecule_id
WHERE  t.slug = ANY(%(slugs)s)
  AND  (s.relevance_llm IS NULL OR s.relevance_llm >= 60)
  AND  (m.is_junk IS NOT TRUE);
```

### Suggested response shape
```json
{ "phase": "lipid",
  "slugs": ["lipid_oxidation_topic", "beta_oxidation"],
  "per_slug": [ {"slug": "lipid_oxidation_topic", "source_count": 0},
                {"slug": "beta_oxidation", "source_count": 0} ],
  "total_sources": 0, "total_molecules": 0 }
```
(zeros above are placeholders — the real numbers come from Neon at runtime.)

**On the relevance gate.** The `(relevance_llm IS NULL OR relevance_llm >= 60)` clause mirrors the
Oracle's `ORACLE_MIN_RELEVANCE = 60` gate (NULL = not-yet-scored, passes) so the Research corpus count
agrees with what the Oracle will actually retrieve and cite — otherwise a chip could advertise 20
sources while the Oracle finds 3. If Full-Stack instead wants a *raw tagged* count, drop that one AND
clause from all three queries and label it as "tagged (not relevance-filtered)". **Caveat (B2, still
open):** until the quarantine → `relevance_llm` write-back lands, this gate does not yet suppress
Daniel-rejected sources, so a gated count can still include rejected rows. That is a corpus-trust gap
being closed on the critical path, not a bug in this SQL.

---

## 4. Backing hints — the basis, and the honest thin-chip list

**Basis (branch richness, from `PROJECT_STATE.md`).** The +332-source ingest tagged **analytics 136 ·
flavor_ingredients 67 · meat_science 52 · meat_analogs 43 · flavor_chemistry 34**; the white-space
analysis found **analytics richest**, **meat_analogs thinnest (14% high-rel)**, **5 HIGH-priority topics
with 0 tagged sources**, only **~40% of 818 sources tagged**, and only **39% pass the relevance gate**.
So the rubric is: analytics HIGH-priority slugs → **strong**; HIGH-priority `flavor_ingredients` /
`meat_science` slugs, or a 3-slug set with a HIGH anchor → **medium**; slugs resting on
`flavor_chemistry` MED level-3/4 topics (e.g. `lipid_oxidation_topic`, `beta_oxidation`,
`pyrazine_chemistry`) or on the thinnest branch (`meat_analogs`), or a single narrow slug → **thin**.

**Thin chips (backing = `thin`, 9) — grey these when `/api/corpus` returns 0.** These are the greying
candidates a reviewer would otherwise catch as clickable-but-empty:

| Chip | Slug(s) | Why thin |
|---|---|---|
| `juice-plant-volatiles` | lipoxygenase_pathway, plant_based_proteins | LOX = fc MED L3 niche; plant_based_proteins sits in the thinnest branch. Also a documented **white-space** ("plant-juice volatiles"). |
| `juice-free-amino-acids` | amino_acids, peptide | both fc MED L3, thinnest-tagged branch |
| `juice-polar-topnotes` | pyrazine_chemistry, furan_chemistry | both fc MED L3; **molecule-rich but topic-tagging is thin** — the count will read low even though these compounds are everywhere |
| `juice-bitterness` | bitter_blockers | single specialized ingredient topic |
| `lipid-maillard-crosstalk` | maillard_lipid | single slug; flagged **white-space** ("Maillard × lipid cross-talk") |
| `lipid-methyl-ketones` | beta_oxidation | single fc MED L3 niche route |
| `lipid-lactones` | lipid_oxidation_topic | single broad slug — coarse proxy (see below) |
| `lipid-cholesterol-oxidation` | lipid_oxidation_topic | single broad slug — coarse proxy |
| `lipid-rancidity-markers` | lipid_oxidation_topic | single broad slug — coarse proxy |

**Coarse single-slug proxies — extra honesty flag.** `lipid-lactones`, `lipid-cholesterol-oxidation`
and `lipid-rancidity-markers` **all resolve to `lipid_oxidation_topic` alone**, so they return the
*identical* source set. The taxonomy has no finer slug for lactones / cholesterol oxidation / rancidity,
so the slug is a broad umbrella and the chip label is more specific than the data. Even when the slug
returns rows, these three over-claim specificity — the UI may want to badge or de-duplicate them, and
these are prime candidates for new MED-level taxonomy topics if Lior wants that granularity (see Next).

**Medium chips are "expect some rows, not many"** — most of Juice/Lipid. Treat the live count as truth.
**Strong chips are the analytics cluster** — the branch the corpus is deepest on, all HIGH-priority.
`analytics-nmr` is the one analytics chip marked **medium**, not strong: it is a single slug and NMR is
genuinely thinner than GC-MS/omics in flavor work.

---

## 5. One-line reminder

**Live per-topic and molecule counts come from `GET /api/corpus` against Neon at runtime — not from this
file. `backing` is only a design-time coverage hint; the endpoint's count is the source of truth, and a
0-count chip greys out no matter what its hint says.**
