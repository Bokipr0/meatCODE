-- =============================================================================
-- Dimensions.ai integration — schema additions
-- Adds bridge columns and indexes for Dimensions IDs, plus a small ingest log.
-- Idempotent: safe to run more than once.
-- =============================================================================
BEGIN;

-- ── experts ────────────────────────────────────────────────────────────────
ALTER TABLE experts
    ADD COLUMN IF NOT EXISTS dimensions_id     TEXT,
    ADD COLUMN IF NOT EXISTS current_org       TEXT,
    ADD COLUMN IF NOT EXISTS dimensions_topics TEXT[];

CREATE UNIQUE INDEX IF NOT EXISTS idx_experts_dimensions
    ON experts(dimensions_id) WHERE dimensions_id IS NOT NULL;

-- speed up the ORCID lookup we'll do every upsert
CREATE INDEX IF NOT EXISTS idx_experts_orcid
    ON experts(orcid) WHERE orcid IS NOT NULL;

-- ── sources ────────────────────────────────────────────────────────────────
ALTER TABLE sources
    ADD COLUMN IF NOT EXISTS dimensions_id     TEXT,
    ADD COLUMN IF NOT EXISTS doi               TEXT,
    ADD COLUMN IF NOT EXISTS abstract          TEXT,
    ADD COLUMN IF NOT EXISTS journal           TEXT,
    ADD COLUMN IF NOT EXISTS dimensions_topics TEXT[];

CREATE UNIQUE INDEX IF NOT EXISTS idx_sources_dimensions
    ON sources(dimensions_id) WHERE dimensions_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_sources_doi
    ON sources(doi) WHERE doi IS NOT NULL;

-- ── ingest log ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ingest_log (
    id                BIGSERIAL PRIMARY KEY,
    started_at        TIMESTAMPTZ DEFAULT now(),
    source            TEXT NOT NULL,           -- 'dimensions', 'openalex', etc.
    topic_slug        TEXT,
    inserted_experts  INTEGER DEFAULT 0,
    updated_experts   INTEGER DEFAULT 0,
    inserted_sources  INTEGER DEFAULT 0,
    updated_sources   INTEGER DEFAULT 0,
    notes             TEXT
);

CREATE INDEX IF NOT EXISTS idx_ingest_log_source_topic
    ON ingest_log(source, topic_slug, started_at DESC);

COMMIT;
