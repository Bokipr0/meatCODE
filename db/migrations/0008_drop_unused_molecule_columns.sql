-- =============================================================================
-- 0008 — Drop unused columns from `molecules` (Lior request).
-- aliases / formula / smiles were 100% empty (0 non-null of 799), not read by the
-- app/server; canonical formula/SMILES now live in the moldedup schema.
-- `aliases` was referenced only in DEAD alias-matching branches of two unused MVL
-- cross-ref views (empty column → branches never matched); those views are rebuilt
-- without the dead branches (behavior-preserving). Applied to Neon: 2026-07-21.
-- =============================================================================
BEGIN;
DROP VIEW IF EXISTS v_mvl_gaps;
DROP VIEW IF EXISTS v_mvl_x_molecules_fuzzy;
ALTER TABLE molecules
    DROP COLUMN IF EXISTS aliases,
    DROP COLUMN IF EXISTS formula,
    DROP COLUMN IF EXISTS smiles;
CREATE VIEW v_mvl_gaps AS
 SELECT entry_no, compound, cas_number, likely_process, chemical_group,
        beef_relevance_score, odor_descriptor
   FROM meaty_volatile_library mvl
  WHERE NOT (EXISTS ( SELECT 1 FROM molecules m
          WHERE lower(m.name) = lower(mvl.compound)
             OR (m.cas_number IS NOT NULL AND m.cas_number = mvl.cas_number)))
  ORDER BY beef_relevance_score DESC NULLS LAST;
CREATE VIEW v_mvl_x_molecules_fuzzy AS
 SELECT mvl.entry_no, mvl.compound AS mvl_compound, mvl.beef_relevance_score,
        m.id AS molecule_id, m.name AS molecule_name,
        CASE WHEN lower(m.name) = lower(mvl.compound) THEN 'exact_name'::text
             WHEN m.cas_number = mvl.cas_number THEN 'cas_match'::text
             ELSE NULL::text END AS match_type
   FROM meaty_volatile_library mvl
   JOIN molecules m ON lower(m.name) = lower(mvl.compound) OR m.cas_number = mvl.cas_number;
COMMIT;
