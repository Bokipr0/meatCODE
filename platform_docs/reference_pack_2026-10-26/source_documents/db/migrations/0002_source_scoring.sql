-- =============================================================================
-- 0002 — Source scoring columns for quality/priority ranking. Idempotent.
--   priority_score : composite 0-100 (deterministic; blends LLM relevance when present)
--   is_review      : review / meta-analysis flag (high-value entry points)
--   relevance_llm  : 0-100 relevance to meaty process flavor, filled by score_relevance.py
-- Applied to Neon: 2026-07-01.
-- =============================================================================
BEGIN;
ALTER TABLE sources
    ADD COLUMN IF NOT EXISTS priority_score numeric,
    ADD COLUMN IF NOT EXISTS is_review      boolean,
    ADD COLUMN IF NOT EXISTS relevance_llm  smallint;
CREATE INDEX IF NOT EXISTS idx_sources_priority ON sources (priority_score DESC NULLS LAST);
COMMIT;
