-- =============================================================================
-- 0010 — Molecule structural identity columns (InChIKey / SMILES / formula)
--        + identity-resolution provenance (id_match_method / id_needs_review).
-- Last updated: 2026-08-15 · Data Engineer agent · initial version
--
-- WHY
--   molecules had 799 rows but only 110 cas_number and 20 pubchem_cid values:
--   the 2026-08-15 pilot (pipeline/pubchem_cids.py) only did EXACT-name PubChem
--   lookups, which fail on stereo-annotated / parenthetical / synonym-form names
--   ("(E,Z)-3,6-nonadien-1-ol", "3-methylindole (skatole)", ...).
--   pipeline/enrich_molecules_structure.py now resolves identity through a
--   confidence-ordered ladder and needs somewhere to record the *structure* it
--   resolved and *how* it got there.
--
-- WHAT
--   molecules:
--     inchikey          text     Standard InChIKey — the canonical chemical identity
--                                (never CAS/CID/name; matches the moldedup convention).
--     smiles            text     PubChem SMILES (isomeric where available).
--     molecular_formula text     PubChem MolecularFormula.
--     id_match_method   text     Which ladder rung resolved the row, e.g.
--                                'exact_name' · 'cas_lookup:110-62-3' ·
--                                'normalized_name:strip_parenthetical(skatole)' ·
--                                'mvl_cas:66-25-1' · 'synonym_registry' ·
--                                'autocomplete:trans,trans-2,4-heptadienal' ·
--                                'ambiguous:3 cids [1234, 5678, 9012] via exact_name' ·
--                                'unresolved:no PubChem match'.
--     id_needs_review   boolean  true for AMBIGUOUS (>1 PubChem CID — never guessed)
--                                and UNRESOLVED names, and for CAS mismatches.
--   Plus a non-unique index on inchikey so duplicate-detection stays cheap.
--   (inchikey is deliberately NOT unique: true duplicates are reported to a human,
--    not auto-merged.)
--
-- REVERSIBLE: additive only — no DROPs, no destructive updates, no defaults on
--   existing data other than id_needs_review=false.
--   To undo:  ALTER TABLE molecules DROP COLUMN inchikey, DROP COLUMN smiles,
--             DROP COLUMN molecular_formula, DROP COLUMN id_match_method,
--             DROP COLUMN id_needs_review;
--             DROP INDEX IF EXISTS ix_molecules_inchikey;
--
-- Applied to Neon: 2026-08-15 — BOTH branches (production + dev).
-- =============================================================================
BEGIN;

ALTER TABLE molecules
    ADD COLUMN IF NOT EXISTS inchikey          text,
    ADD COLUMN IF NOT EXISTS smiles            text,
    ADD COLUMN IF NOT EXISTS molecular_formula text,
    ADD COLUMN IF NOT EXISTS id_match_method   text,
    ADD COLUMN IF NOT EXISTS id_needs_review   boolean NOT NULL DEFAULT false;

CREATE INDEX IF NOT EXISTS ix_molecules_inchikey ON molecules (inchikey);

COMMIT;
