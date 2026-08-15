-- =============================================================================
-- 0009 — Molecule enrichment columns + deterministic MVL backfill + junk flag
--        + sources.tailored_abstract.
-- Last updated: 2026-08-15 · Data Engineer agent · initial version
--
-- WHAT
--   molecules: adds familiar_names text[], found_in text[], pathway_step text,
--     reacts_with text[], solubility_notes text, reaction_rate_notes text,
--     is_junk boolean NOT NULL DEFAULT false.
--     (cas_number / pubchem_cid / water_solubility already exist.)
--   sources: adds tailored_abstract text (filled by pipeline/tailor_abstracts.py).
--
-- BACKFILL (deterministic, zero fabrication — everything comes from
--   meaty_volatile_library rows already in the DB, joined by normalized name:
--   lowercase, spaces/hyphens/commas stripped; only names that map to exactly
--   ONE MVL entry are used):
--     cas_number   ← mvl.cas_number            (only where molecules.cas_number IS NULL)
--     pathway_step ← mvl.likely_process        ('Maillard' / 'Lipid oxidation' / 'Both')
--     found_in     ← mvl.cooked_meats_reported (citation brackets [..] stripped,
--                                               split on commas)
--   familiar_names / reacts_with / solubility_notes / reaction_rate_notes have
--   no derivable source in the DB today → left NULL (schema ready for curation).
--
-- JUNK FLAG
--   is_junk = true for rows whose name is a common-English extraction artifact.
--   Reference list = JUNK_NAMES in kg/build_kg.py. No rows are deleted —
--   downstream (KG build, UI) can filter WHERE NOT is_junk.
--
-- REVERSIBLE: additive only — no DROPs, no destructive updates (cas_number is
--   filled only where NULL). To undo: ALTER TABLE ... DROP COLUMN for the new
--   columns.
-- Applied to Neon: 2026-08-15.
-- =============================================================================
BEGIN;

ALTER TABLE molecules
    ADD COLUMN IF NOT EXISTS familiar_names      text[],
    ADD COLUMN IF NOT EXISTS found_in            text[],
    ADD COLUMN IF NOT EXISTS pathway_step        text,
    ADD COLUMN IF NOT EXISTS reacts_with         text[],
    ADD COLUMN IF NOT EXISTS solubility_notes    text,
    ADD COLUMN IF NOT EXISTS reaction_rate_notes text,
    ADD COLUMN IF NOT EXISTS is_junk             boolean NOT NULL DEFAULT false;

ALTER TABLE sources
    ADD COLUMN IF NOT EXISTS tailored_abstract text;

-- ---------------------------------------------------------------------------
-- Backfill from meaty_volatile_library (unambiguous normalized-name matches only)
-- ---------------------------------------------------------------------------
WITH mv AS (
    SELECT lower(regexp_replace(compound, '[ ,\-]', '', 'g')) AS norm,
           min(entry_no)                                      AS entry_no,
           min(NULLIF(cas_number, ''))                        AS cas_number,
           min(likely_process)                                AS likely_process,
           min(cooked_meats_reported)                         AS cooked_meats_reported
      FROM meaty_volatile_library
     GROUP BY 1
    HAVING count(DISTINCT COALESCE(cas_number,     ''))  = 1
       AND count(DISTINCT COALESCE(likely_process, ''))  = 1
),
mv_parsed AS (
    SELECT norm, cas_number, likely_process,
           (SELECT array_agg(DISTINCT btrim(x) ORDER BY btrim(x))
              FROM unnest(string_to_array(
                     regexp_replace(cooked_meats_reported, '\[[^\]]*\]', '', 'g'),
                     ',')) AS x
             WHERE btrim(x) <> '') AS found_in_arr
      FROM mv
)
UPDATE molecules m
   SET cas_number   = COALESCE(m.cas_number,   v.cas_number),
       pathway_step = COALESCE(m.pathway_step, v.likely_process),
       found_in     = COALESCE(m.found_in,     v.found_in_arr)
  FROM mv_parsed v
 WHERE lower(regexp_replace(m.name, '[ ,\-]', '', 'g')) = v.norm;

-- ---------------------------------------------------------------------------
-- Flag non-molecule junk rows (reference: kg/build_kg.py JUNK_NAMES)
-- ---------------------------------------------------------------------------
UPDATE molecules
   SET is_junk = true
 WHERE lower(btrim(name)) IN (
    'decline', 'increase', 'decrease', 'control', 'response', 'sample', 'mixture',
    'extract', 'residue', 'fraction', 'volatile', 'volatiles', 'compound', 'compounds',
    'flavour', 'flavor', 'aroma', 'odour', 'odor', 'taste', 'texture', 'quality'
 );

COMMIT;
