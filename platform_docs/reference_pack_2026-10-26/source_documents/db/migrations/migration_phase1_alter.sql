-- =============================================================================
-- Migration Phase 1 — schema additions for Airtable migration
-- Adds 19 columns from Airtable that didn't exist in v1/v2 schema,
-- plus external_id bridge columns for linked-record resolution.
-- Idempotent: uses IF NOT EXISTS everywhere.
-- =============================================================================

BEGIN;

-- 1. external_id bridge columns on every main table
ALTER TABLE sources    ADD COLUMN IF NOT EXISTS external_id  TEXT;
ALTER TABLE molecules  ADD COLUMN IF NOT EXISTS external_id  TEXT;
ALTER TABLE odours     ADD COLUMN IF NOT EXISTS external_id  TEXT;
ALTER TABLE experts    ADD COLUMN IF NOT EXISTS external_id  TEXT;
ALTER TABLE claims     ADD COLUMN IF NOT EXISTS external_id  TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_sources_external   ON sources(external_id)   WHERE external_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_molecules_external ON molecules(external_id) WHERE external_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_odours_external    ON odours(external_id)    WHERE external_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_experts_external   ON experts(external_id)   WHERE external_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_claims_external    ON claims(external_id)    WHERE external_id IS NOT NULL;

-- 2. New columns on `sources`
ALTER TABLE sources
    ADD COLUMN IF NOT EXISTS search_query    TEXT,
    ADD COLUMN IF NOT EXISTS citation_count  INTEGER,
    ADD COLUMN IF NOT EXISTS top_keywords    TEXT,
    ADD COLUMN IF NOT EXISTS external_key    TEXT;

-- 3. New columns on `molecules`
ALTER TABLE molecules
    ADD COLUMN IF NOT EXISTS taste              TEXT,
    ADD COLUMN IF NOT EXISTS use_notes          TEXT,
    ADD COLUMN IF NOT EXISTS melting_point      TEXT,
    ADD COLUMN IF NOT EXISTS water_solubility   TEXT,
    ADD COLUMN IF NOT EXISTS compound_id        TEXT,
    ADD COLUMN IF NOT EXISTS odour_source_url   TEXT,
    ADD COLUMN IF NOT EXISTS external_key       TEXT;

CREATE INDEX IF NOT EXISTS idx_molecules_compound_id ON molecules(compound_id) WHERE compound_id IS NOT NULL;

-- 4. New columns on `odours`
ALTER TABLE odours
    ADD COLUMN IF NOT EXISTS odour_category TEXT;

-- 5. New columns on `claims`
ALTER TABLE claims
    ADD COLUMN IF NOT EXISTS evidence_snippet TEXT,
    ADD COLUMN IF NOT EXISTS external_key    TEXT;

-- 6. New columns on `experts`
ALTER TABLE experts
    ADD COLUMN IF NOT EXISTS country         TEXT,
    ADD COLUMN IF NOT EXISTS relevance_score NUMERIC(4,3),
    ADD COLUMN IF NOT EXISTS h_index         INTEGER,
    ADD COLUMN IF NOT EXISTS total_papers    INTEGER,
    ADD COLUMN IF NOT EXISTS orcid           TEXT,
    ADD COLUMN IF NOT EXISTS key_research    TEXT,
    ADD COLUMN IF NOT EXISTS keywords        TEXT,
    ADD COLUMN IF NOT EXISTS linkedin_url    TEXT,
    ADD COLUMN IF NOT EXISTS knowledge_gaps  TEXT,
    ADD COLUMN IF NOT EXISTS openalex_id     TEXT;

CREATE INDEX IF NOT EXISTS idx_experts_country  ON experts(country);
CREATE INDEX IF NOT EXISTS idx_experts_openalex ON experts(openalex_id) WHERE openalex_id IS NOT NULL;

-- 7. Outreach status normalization — Airtable has 'Auto-discovered'.
--    Add it to the existing ENUM so import doesn't fail.
ALTER TYPE outreach_status ADD VALUE IF NOT EXISTS 'auto_discovered' BEFORE 'not_contacted';
ALTER TABLE sources ADD COLUMN IF NOT EXISTS trust_tier TEXT;

COMMIT;
