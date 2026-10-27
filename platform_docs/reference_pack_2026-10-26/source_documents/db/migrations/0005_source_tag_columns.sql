-- =============================================================================
-- 0005 — Add per-source tagging columns to `sources` (schema only; left NULL).
-- Requested tags: Pathway · Method · Sensory Descriptor · Matrix · Study type ·
-- (Main) Compound class · Main claim. To be populated later (LLM extraction / curation).
-- Multi-valued tags are TEXT[]; single-value ones are TEXT. Idempotent (IF NOT EXISTS).
-- NOTE: "Min Compound class" read as "Main Compound class" → column `compound_class`.
-- Applied to Neon: 2026-07-07.
-- =============================================================================
BEGIN;

ALTER TABLE sources
    ADD COLUMN IF NOT EXISTS pathway            TEXT[],   -- e.g. Maillard, lipid oxidation, Strecker
    ADD COLUMN IF NOT EXISTS method             TEXT[],   -- e.g. GC-MS, GC-O, SPME, sensory panel
    ADD COLUMN IF NOT EXISTS sensory_descriptor TEXT[],   -- e.g. roasted, meaty, sulfurous
    ADD COLUMN IF NOT EXISTS matrix             TEXT[],   -- e.g. beef, plant-protein, model system
    ADD COLUMN IF NOT EXISTS compound_class     TEXT[],   -- e.g. pyrazines, aldehydes, thiols
    ADD COLUMN IF NOT EXISTS study_type         TEXT,     -- e.g. review, experimental, patent, modeling
    ADD COLUMN IF NOT EXISTS main_claim         TEXT;     -- one-line core finding of the source

COMMENT ON COLUMN sources.pathway            IS 'Reaction/formation pathways (tag set) — to be filled.';
COMMENT ON COLUMN sources.method             IS 'Analytical / experimental methods (tag set) — to be filled.';
COMMENT ON COLUMN sources.sensory_descriptor IS 'Sensory / aroma descriptors (tag set) — to be filled.';
COMMENT ON COLUMN sources.matrix             IS 'Food matrix / system studied (tag set) — to be filled.';
COMMENT ON COLUMN sources.compound_class     IS 'Main compound class(es) (tag set) — to be filled.';
COMMENT ON COLUMN sources.study_type         IS 'Study type (single) — to be filled.';
COMMENT ON COLUMN sources.main_claim         IS 'Main claim / key finding (single line) — to be filled.';

COMMIT;
