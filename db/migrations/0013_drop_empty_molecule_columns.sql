-- =============================================================================
-- 0013 — Drop the never-populated molecule scaffolding columns (Lior request).
-- Last updated: 2026-08-27 · Data Engineer agent
--
-- DATA SAFETY (count() ignores NULLs, so 0 = every row empty)
--   familiar_names       0 / 799   ← dropped
--   reacts_with          0 / 799   ← dropped
--   solubility_notes     0 / 799   ← dropped
--   reaction_rate_notes  0 / 799   ← dropped
--   Verified identical on BOTH Neon branches (production + dev).
--
--   NOT DROPPED — these two carry real data and were deliberately left in place:
--     found_in       110 / 799  (cooked meats reported, from meaty_volatile_library)
--     pathway_step   110 / 799  (Maillard / Lipid oxidation / Both — the formation
--                                route label the KG uses to separate the two
--                                chemistries; expensive to reproduce, cheap to keep)
--   Dropping either needs an explicit decision from Lior.
--
-- STRUCTURAL SAFETY
--   information_schema.view_column_usage → NO view reads any of the four columns.
--   Repo grep over server/ app/ kg/ pipeline/ analysis/ db/ → zero references
--   outside the migration that created them (0009). Nothing to rebuild.
--
-- These four came from 0009 as "schema ready for curation"; the curation source
-- never materialized, so they are scaffolding, not data.
--
-- REVERSIBLE: re-add with
--   ALTER TABLE molecules
--     ADD COLUMN familiar_names text[], ADD COLUMN reacts_with text[],
--     ADD COLUMN solubility_notes text, ADD COLUMN reaction_rate_notes text;
--   (No values are lost — there were none.)
--
-- Applied to Neon: 2026-08-27 — production + dev.
-- =============================================================================
BEGIN;

ALTER TABLE molecules
    DROP COLUMN IF EXISTS familiar_names,
    DROP COLUMN IF EXISTS reacts_with,
    DROP COLUMN IF EXISTS solubility_notes,
    DROP COLUMN IF EXISTS reaction_rate_notes;

COMMIT;

-- Verification (expect: 0 remaining, 799 rows, every view still queryable)
-- SELECT count(*) FROM information_schema.columns
--  WHERE table_schema='public' AND table_name='molecules'
--    AND column_name IN ('familiar_names','reacts_with','solubility_notes','reaction_rate_notes');
-- SELECT count(*) FROM molecules;
