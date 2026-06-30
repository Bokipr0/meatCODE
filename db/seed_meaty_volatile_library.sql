-- 1) Make sure Neon has the columns the sync writes to
ALTER TABLE sources ADD COLUMN IF NOT EXISTS composite_score REAL DEFAULT 0.0;
ALTER TABLE sources ADD COLUMN IF NOT EXISTS review_status   TEXT DEFAULT 'pending';

-- 2) Three-tier view for SOURCES, ranked by composite_score
CREATE OR REPLACE VIEW v_sources_3tier AS
SELECT
    id, external_id, name, year, venue, url, citation_count,
    composite_score, review_status, trust_tier,
    CASE
        WHEN composite_score >= 0.70 THEN '1_high'
        WHEN composite_score >= 0.50 THEN '2_mid'
        ELSE                                '3_low'
    END AS relevance_tier
FROM sources
ORDER BY composite_score DESC;

-- 3) Three-tier view for EXPERTS, ranked by relevance_score (already in your schema)
CREATE OR REPLACE VIEW v_experts_3tier AS
SELECT
    id, external_id, name, affiliation, country,
    research_field, h_index, total_papers, relevance_score,
    outreach_status,
    CASE
        WHEN relevance_score >= 0.80 THEN '1_high'
        WHEN relevance_score >= 0.60 THEN '2_mid'
        ELSE                              '3_low'
    END AS relevance_tier
FROM experts
ORDER BY relevance_score DESC;

-- 4) Combined dashboard: how many sources/experts per tier
CREATE OR REPLACE VIEW v_relevance_summary AS
SELECT 'sources' AS entity, relevance_tier, COUNT(*) AS n
FROM   v_sources_3tier GROUP BY relevance_tier
UNION ALL
SELECT 'experts' AS entity, relevance_tier, COUNT(*) AS n
FROM   v_experts_3tier GROUP BY relevance_tier
ORDER BY entity, relevance_tier;