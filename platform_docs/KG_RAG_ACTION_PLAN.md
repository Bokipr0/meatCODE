# KG + RAG Action Plan

_2026-08-27 · verified live against Neon · **updated: the no-schema-change constraint was lifted by
Lior; migration 0011 is applied to both branches** — see `db/migrations/0011_molecule_target_properties.sql`_

**Headline finding:** three of the four things you asked for need **no new tables** — the schema
already has them and they are simply **empty**. The fourth (the molecule property list) had no home
at all; it now does.

> **Status update (2026-08-27):** migration 0011 added the 16 target-property columns plus
> `molecule_properties` (per-value source · method · conditions · uncertainty · confidence).
> Populated: 590 molecules with structure-derived descriptors, 110 with reported odour thresholds,
> **3,650 provenance rows**, cross-checked against `moldedup.molecules` with 0 MW mismatches.
> Rows 4–6 of the checklist below are therefore **done**; the rest stands.

---

## 1. Data Completion Checklist

| Target | Home (exists today) | Live count | Action |
|---|---|---|---|
| Molecule identity | `molecules.inchikey/smiles/molecular_formula` | **590 / 799** | Resolve the 209 gaps; `id_needs_review` is set on 798 rows — clear it as reviewed. |
| Molecular weight, functional groups, charge, pKa, pI, polarity, hydrophobicity, redox potential | **no column, and no `jsonb` on `molecules`** | 0 | **Conflict → schema wins.** All are deterministic functions of `smiles`. Compute with RDKit at KG-build time, cache to `kg/derived_properties.parquet`. Never persist to Neon. |
| Melting/boiling point, vapour pressure, solubility, logP | `melting_point`, `water_solubility` only | **10 / 799** | Only the two existing columns are fillable. Boiling point / vapour pressure / partition coefficient **have no column — out of scope** until you approve a migration. |
| Odour descriptors | `odours` + `molecule_odours` | **639 odours, 2,263 links, 785/799 molecules** | ✅ **Already done.** Do not rebuild. |
| Odour threshold, OAV, colour, uncertainty, confidence | no column | 0 | Out of scope under the constraint. Flag for decision. |
| Measurement method / conditions | `processes` (`temperature_c`, `time_min`, `ph`, `water_activity`, `oxygen_available`, `fat_phase_pct`) | **0 rows** | **Highest leverage item on this list.** The conditions spine exists and is empty. Populate from extraction. |
| Experts: research field + key research | `experts.research_field`, `key_research` | **17 / 3,129** | Derive from `dimensions_topics` (**2,755 filled**) — mapping only, no new column. |
| Sources | `sources.*` fully tagged | **818 / 818**, `main_claim` 818 | One claim per paper. Papers hold 5–20 → route extraction into `claims` (45 rows, `stance` supports 39 / contradicts 6). |

**Verification rule:** every populated field carries `id_match_method`-style provenance or a
`claim_sources` row. No value enters Neon without a traceable origin. `"Yizhou.md"` was not found in
the repo — the nearest artefact is `Yizhou_Meeting_Questions.docx` in the parent folder.

---

## 2. Query Definitions

```sql
SELECT * FROM molecules WHERE id = ?;
```

```sql
-- (a) Identity completeness gate
SELECT count(*) FILTER (WHERE inchikey IS NOT NULL) AS resolved,
       count(*) FILTER (WHERE id_needs_review)      AS needs_review,
       count(*)                                     AS total
FROM molecules WHERE NOT is_junk;

-- (b) Odours <-> molecules  (populated — read path)
SELECT m.id, m.name, array_agg(o.name ORDER BY o.name) AS odours
FROM molecules m
JOIN molecule_odours mo ON mo.molecule_id = m.id
JOIN odours o           ON o.id = mo.odour_id
WHERE NOT m.is_junk GROUP BY m.id, m.name;

-- (c) Molecules <-> Reactions  (reaction_participants = 0 rows — write path)
INSERT INTO reaction_participants (reaction_id, molecule_id, role, notes)
SELECT r.id, m.id, ?, ?          -- role: 'precursor' | 'product' | 'catalyst'
FROM reactions r, molecules m
WHERE r.slug = ? AND m.inchikey = ?
ON CONFLICT DO NOTHING;

-- (d) Molecules <-> Mechanism (conditions-bound path via processes + claims)
SELECT c.id, c.claim_text, c.stance, c.confidence,
       p.temperature_c, p.ph, p.time_min, s.id AS source_id
FROM claims c
JOIN claim_molecules cm ON cm.claim_id = c.id
JOIN claim_sources   cs ON cs.claim_id = c.id
JOIN sources         s  ON s.id = cs.source_id
LEFT JOIN processes  p  ON p.source_id = s.id
WHERE cm.molecule_id = ? AND s.relevance_llm >= 60;

-- (e) Expert field backfill from existing topics (no new column)
UPDATE experts SET research_field = ?, key_research = ?
WHERE id = ? AND research_field IS NULL;
```

---

## 3. Knowledge-Graph Construction Options

```
Odours <-> molecules
Molecules <-> Reactions
Molecules <-> Mechanism
```

| Option | Fit | Note |
|---|---|---|
| **A. Postgres + Python projection** (current `kg/build_kg.py`) | Every edge above is already a join table. | Recommended. |
| B. Neo4j / property graph | Only pays off at routine ≥3-hop traversal. | *Placeholder — proprietary/managed tier not evaluated.* |
| C. RDF + SPARQL | Best ontology rigour, worst velocity. | Not before 2027. |

---

## 4. Implementation Recommendation

**Python script over Postgres (Option A).** The graph is already relational; a graph DB would add an
export/sync surface without adding an answerable question. Extraction artefacts stay on disk as
`batches/Bxx/` CSV/JSON per the full-text strategy; **only checker-approved rows are written to Neon**
— which also keeps the corpus copyright-safe, since no full text is stored anywhere in the schema.

---

## 5. Timeline & Parallel Workstreams

| Lane | Owner | Week 1 | Week 2 |
|---|---|---|---|
| Identity | Data | Close 209 InChIKey gaps, clear `id_needs_review` | Derived-properties parquet (RDKit) |
| Conditions | Data | Populate `processes` from the 20–50 paper pilot | ≥100 rows with pH/temp/time |
| Claims | Algorithm | Multi-claim extraction into `claims` + `stance` | Fill `reaction_participants` |
| Experts | Data | `dimensions_topics` → `research_field` (2,755) | Manual top-100 `key_research` |
| Eval | Algorithm | Gold set from the pilot | Re-run vs baseline 3.4 / 4.8 / 4.1 |

**Does not displace B1 (deploy) or B2 (quarantine write-back) — both remain critical path.**
