-- =============================================================================
-- 0014 — Drop molecules.taste and molecules.use_notes (Lior, explicit go-ahead).
-- Last updated: 2026-08-27 · Data Engineer agent
--
-- ⚠ THIS ONE IS NOT LIKE 0013. Both columns held DATA and were LIVE IN CODE.
--   taste       13 / 799 non-null   ('acidic, fatty/oily', 'bitter', 'pungent, burning', …)
--   use_notes   15 / 799 non-null   ('solvent', 'flavoring agent, nutritional', …)
--   Lior confirmed the loss is intended on 2026-08-27. Values are NOT recoverable
--   from elsewhere in the DB — if they are ever wanted back they must be re-curated.
--
-- STRUCTURAL SAFETY — TWO checks, because the usual one was not enough:
--   1. information_schema.view_column_usage → NO view reads either column.
--   2. Repo grep → they WERE read by application code, which the catalog cannot
--      see. Postgres would have dropped them happily and the app would have
--      500'd at runtime. Every reference was removed and verified FIRST:
--        server/meatcode_server.py
--          · 3 SELECTs (the /api/molecules list, the molecule-suggestions ranker,
--            and _molecule_detail — which backs GET /api/molecules/{id}, the
--            /api/molecule-profile/{id} alias AND POST /api/compare)
--          · COMPARE_FIELD_ORDER rows "Taste / descriptor" and "Use notes"
--        kg/build_kg.py
--          · the molecule SELECT and its positional unpack
--            `for mid, name, cat, taste, notes in molecules` (a drop here would
--             have raised ValueError, not a SQL error)
--        app/meatcode_mockup.html
--          · molecule-detail meta line, detail tag chips, related-molecule chip
--            subtitle (all .filter(Boolean), so they degrade rather than break)
--      Verified after editing: py_compile clean on both modules, 10/10 mockup
--      inline scripts pass `node --check`, zero remaining code references.
--
-- ORDER OF OPERATIONS: code first, then the column. Deploy the code change before
--   (or with) this migration — a server still running the old SELECTs will 500 the
--   moment the columns disappear.
--
-- REVERSIBLE (structure only — the 28 values are gone):
--   ALTER TABLE molecules ADD COLUMN taste text, ADD COLUMN use_notes text;
--
-- Applied to Neon: 2026-08-27 — production + dev.
-- =============================================================================
BEGIN;

ALTER TABLE molecules
    DROP COLUMN IF EXISTS taste,
    DROP COLUMN IF EXISTS use_notes;

COMMIT;

-- Verification (expect: 0 remaining, 799 rows, 38 columns, all views queryable)
-- SELECT count(*) FROM information_schema.columns
--  WHERE table_schema='public' AND table_name='molecules'
--    AND column_name IN ('taste','use_notes');
-- SELECT count(*) FROM molecules;
