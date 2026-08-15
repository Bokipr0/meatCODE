# Claim layer — how the paper claim record should grow

_Last updated: 2026-08-15 · Algorithm Expert · written alongside the consensus/claims wiring in server/meatcode_server.py; recommendation for the Data Engineer's next schema pass._

## 1. What exists today (verified live against Neon, 2026-08-15)

| Table | Rows | Columns |
|---|---|---|
| `claims` | 45 | `id`, `claim_text`, `stance` (enum: `supports` / `contradicts` / …), `confidence` (numeric 0–1), `notes`, `evidence_snippet`, `external_id`, `external_key`, timestamps |
| `claim_sources` | 69 | `claim_id`, `source_id` |
| `claim_molecules` | 41 | `claim_id`, `molecule_id` |

The rows are Airtable-era imports (`external_id` like `rec0V…`): one-sentence assertions
("Linoleic Acid contributes to taste characteristics (acidic, fatty/oily) in meat products",
confidence 0.40), stance-tagged, linked to a handful of sources and molecules.

**What now reads it (new, this session):** the Oracle's retrieval path. When `/api/ask` (or
`GET /api/consensus-demo`) retrieves a source that has rows in `claim_sources`, each claim's
`{id, claim_text, stance, confidence}` is attached to that source in the `sources` SSE payload
under an additive `"claims"` key (`_claims_for_sources()` in `server/meatcode_server.py`).
Coverage today is thin by construction — 69 links over 818 sources — so most retrievals carry
no claims. That is the honest state; the point of this note is how to grow it.

## 2. Why grow it

A claim record is the unit the whole "open and authentic processing" story runs on:
- the consensus signal ("N papers support · M oppose") currently has to *infer* stances with a
  model call at question time; typed claims make it a lookup;
- the KG (`kg/build_kg.py` already reads all three tables) can walk question → claim →
  sources/molecules instead of mining free text;
- contradictions between papers become queryable ("show claims where sources disagree"),
  which is exactly the white-space/validation evidence Daniel needs.

## 3. Recommended schema growth (aligned with the whiteboard: conditions · measurement · normalized axis · evidence tier)

Keep `claims` as the head record; add typed satellites rather than overloading `claim_text`.

### 3a. `claims` — three new columns (migration, additive only)

```sql
ALTER TABLE claims
  ADD COLUMN subject_molecule_id BIGINT REFERENCES molecules(id),  -- the claim's primary subject, when it is about one compound
  ADD COLUMN normalized_axis TEXT,      -- the ONE axis the claim moves, controlled vocab (see 3d)
  ADD COLUMN evidence_tier TEXT CHECK (evidence_tier IN ('T1_experimental','T2_review','T3_inferred'));
```

- `evidence_tier` (whiteboard "evidence tier"): **T1** = the linked source measured it directly;
  **T2** = asserted in a review; **T3** = model-extracted/mined, unverified by a human. Existing
  45 rows backfill to `T3` (they came from an automated Airtable pass) until reviewed.
- `stance` stays on `claims` for the claim's own polarity, but note §3e: per-source stance
  belongs on the junction.

### 3b. `claim_conditions` — the "under what conditions" record (whiteboard: conditions)

A claim like "2-methyl-3-furanthiol forms from thiamine" is only reproducible with conditions.
One row per condition:

```sql
CREATE TABLE claim_conditions (
  id BIGSERIAL PRIMARY KEY,
  claim_id BIGINT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
  condition_type TEXT NOT NULL,   -- controlled: temperature | time | ph | water_activity |
                                  -- matrix | precursor_conc | atmosphere | process_step
  value_raw TEXT NOT NULL,        -- exactly as the paper says: "140 °C, 30 min"
  value_num NUMERIC,              -- normalized numeric value where parseable (140)
  unit TEXT                       -- normalized unit ("C", "min", "aw", "%")
);
```

`value_raw` is never lost; `value_num`+`unit` are the queryable normalization ("all claims
about furanthiol formation between 120–160 °C").

### 3c. `claim_measurements` — what was actually measured (whiteboard: measurement)

```sql
CREATE TABLE claim_measurements (
  id BIGSERIAL PRIMARY KEY,
  claim_id BIGINT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
  quantity TEXT NOT NULL,         -- controlled: concentration | odor_threshold | OAV |
                                  -- sensory_score | RI | identification_only
  value_raw TEXT,                 -- "12.3 µg/kg"
  value_num NUMERIC,
  unit TEXT,                      -- normalized ("ug_kg", "ng_L", "OAV")
  method TEXT                     -- free text now; later FK into the tags(category='method') vocab
                                  -- (GC-MS, GC-O/AEDA, SPME…) so methodology is queryable
);
```

### 3d. `normalized_axis` — the comparable dimension (whiteboard: normalized axis)

The axis is what lets two claims from different papers land on the same chart. Start with a
small controlled vocabulary (extend by decision, not ad hoc):
`aroma_intensity` · `compound_concentration` · `formation_rate` · `consumer_liking` ·
`off_note_intensity` · `threshold`. Direction lives in `stance` (supports = moves it up /
confirms; contradicts = the reverse), so a claim reads as: *subject X moves axis A, under
conditions C, measured as M, at tier T*.

### 3e. Per-source stance on the junction (needed for honest consensus)

Two papers can link to the same claim while disagreeing about it. Move disagreement where it
belongs:

```sql
ALTER TABLE claim_sources
  ADD COLUMN stance TEXT CHECK (stance IN ('supports','contradicts','neutral')),
  ADD COLUMN evidence_snippet TEXT;   -- the sentence in THAT source, for click-through provenance
```

Once populated, the Oracle's consensus event can come from SQL for claim-covered sources
(a count over `claim_sources.stance`) and fall back to the current Haiku classification only
for uncovered ones — cheaper and auditable.

## 4. How it gets populated (pipeline, not typing)

1. **Extraction**: extend the Layer-C typed extraction (or `tag_sources.py` pattern) with a
   claim schema — for each source with an abstract, emit 0–3 claims: `claim_text`, subject
   molecule (matched against `molecules.name`), `normalized_axis`, conditions, measurement,
   stance-toward-claim. Tier every extracted row `T3_inferred`, `confidence` from the model.
2. **Verification loop**: reuse the existing audit-loop pattern (`pipeline/audit_judge.py`) +
   Daniel's xlsx sign-off to promote reviewed rows to `T1`/`T2` — same governance as
   `relevance_llm`.
3. **Order of attack**: the ~45 sources with `relevance_llm >= 80` first; that seeds the
   claim graph exactly where the Oracle retrieves most often.

## 5. Contract with the server (what NOT to break)

- `_claims_for_sources()` selects `c.id, c.claim_text, c.stance::text, c.confidence` — all
  additions above are additive; do not rename these four.
- Keep junction PKs/uniques on (`claim_id`,`source_id`) and (`claim_id`,`molecule_id`).
- New columns should be NULLable so the 45 legacy rows stay valid; use the meatcode-schema-change
  skill / numbered migration convention in `db/migrations/`.
