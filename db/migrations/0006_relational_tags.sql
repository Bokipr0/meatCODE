-- =============================================================================
-- 0006 — Relational tagging system for the 5 multi-valued source tags.
-- ONE unified vocabulary table `tags` (category-typed) + ONE junction `source_tags`.
-- Categories: pathway | method | sensory_descriptor | matrix | compound_class.
-- (study_type + main_claim stay as plain columns on `sources` — single/free-text.)
-- Junction-keep decision: KEEP source_topics (taxonomy) + source_molecules; source_tags
-- is the new home for these 5 tag categories; the pre-existing EMPTY junctions
-- (source_reactions / source_methods / source_sensory_attributes / source_product_contexts)
-- are SUPERSEDED by source_tags — left in place (not dropped) as legacy.
-- Data is loaded (re-runnably) by pipeline/promote_tags.py from the sources.* TEXT[] columns.
-- Idempotent. Applied to Neon: 2026-07-08.
-- =============================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS tags (
    id         BIGSERIAL PRIMARY KEY,
    category   TEXT NOT NULL,   -- pathway|method|sensory_descriptor|matrix|compound_class
    name       TEXT NOT NULL,   -- display form (as extracted, trimmed)
    slug       TEXT NOT NULL,   -- normalized key for dedupe (lower, non-alnum→'-')
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (category, slug)
);

CREATE TABLE IF NOT EXISTS source_tags (
    source_id BIGINT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    tag_id    BIGINT NOT NULL REFERENCES tags(id)    ON DELETE CASCADE,
    PRIMARY KEY (source_id, tag_id)
);

CREATE INDEX IF NOT EXISTS idx_tags_category    ON tags (category);
CREATE INDEX IF NOT EXISTS idx_source_tags_tag  ON source_tags (tag_id);

COMMIT;
