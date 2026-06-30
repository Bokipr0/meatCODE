-- =============================================================================
-- Reaktzia MVP — full-text search for the Oracle
-- Adds tsvector column to sources, a GIN index, and a backfill trigger.
-- Idempotent: safe to run more than once.
-- =============================================================================
BEGIN;

-- 1. Add the tsvector column (English config — fine for the Reaktzia corpus,
--    which is overwhelmingly English-language scientific literature).
ALTER TABLE sources
    ADD COLUMN IF NOT EXISTS search_vec tsvector;

-- 2. Backfill for existing rows. We combine title (column 'name') and abstract
--    with title weighted higher so a query that hits the title ranks above
--    one that only hits the abstract.
UPDATE sources
SET search_vec =
    setweight(to_tsvector('english', coalesce(name,     '')), 'A') ||
    setweight(to_tsvector('english', coalesce(abstract, '')), 'B')
WHERE search_vec IS NULL;

-- 3. Trigger so new inserts / updates automatically refresh search_vec.
CREATE OR REPLACE FUNCTION sources_search_vec_refresh() RETURNS trigger AS $$
BEGIN
    NEW.search_vec :=
        setweight(to_tsvector('english', coalesce(NEW.name,     '')), 'A') ||
        setweight(to_tsvector('english', coalesce(NEW.abstract, '')), 'B');
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sources_search_vec ON sources;
CREATE TRIGGER trg_sources_search_vec
    BEFORE INSERT OR UPDATE OF name, abstract
    ON sources
    FOR EACH ROW
    EXECUTE FUNCTION sources_search_vec_refresh();

-- 4. GIN index for fast searches.
CREATE INDEX IF NOT EXISTS idx_sources_search_vec
    ON sources USING GIN(search_vec);

-- 5. Quick sanity check (printed in psql output if run manually):
--    SELECT count(*) FROM sources WHERE search_vec IS NOT NULL;

COMMIT;
