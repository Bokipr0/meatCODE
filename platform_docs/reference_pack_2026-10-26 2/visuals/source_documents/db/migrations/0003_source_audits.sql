-- =============================================================================
-- Last updated: 2026-07-07 10:32 UTC · Data Engineer (audit loop) · create source_audits
-- 0003 — source_audits: one row per audited source per run. Additive + idempotent.
--   Powers the recurring data-authentication loop (pipeline/audit_sources.py):
--   every run selects sources by dynamic audit priority, judges tags/relevance/
--   quality, and records the verdict here so the corpus keeps improving over time.
--   FULLY ADDITIVE — creates one new table + indexes only. Does NOT alter, drop,
--   or touch any existing table. Safe to re-run (CREATE ... IF NOT EXISTS).
-- =============================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS source_audits (
    id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_id        bigint NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    run_id           text,                                   -- groups one audit batch (uuid)
    audited_at       timestamptz NOT NULL DEFAULT now(),
    tag_score        int,                                    -- 0-100: tagging correctness
    relevance_score  int,                                    -- 0-100: on-topic for meaty process flavor
    quality_score    int,                                    -- 0-100: venue / citations / evidence
    verdict          text CHECK (verdict IN ('keep', 'review', 'quarantine')),
    tag_issues       jsonb,                                  -- list[str] of flagged tag problems
    notes            text,                                   -- judge rationale (short)
    weights_snapshot jsonb,                                  -- audit-priority weights used this run
    audit_priority   double precision                        -- dynamic selection score (higher = audited first)
);

-- Selection + reporting indexes (all IF NOT EXISTS = re-runnable).
CREATE INDEX IF NOT EXISTS idx_source_audits_source_id  ON source_audits (source_id);
CREATE INDEX IF NOT EXISTS idx_source_audits_audited_at ON source_audits (audited_at DESC);
CREATE INDEX IF NOT EXISTS idx_source_audits_verdict    ON source_audits (verdict);
CREATE INDEX IF NOT EXISTS idx_source_audits_run_id     ON source_audits (run_id);

COMMENT ON TABLE  source_audits IS 'Recurring data-authentication audit trail: one row per source per audit run (pipeline/audit_sources.py).';
COMMENT ON COLUMN source_audits.audit_priority IS 'Dynamic priority the source was selected by (staleness + priority_score + relevance/tag gaps).';
COMMENT ON COLUMN source_audits.weights_snapshot IS 'Snapshot of the audit-priority weights in effect for this run (lets weight evolution be reproduced).';

COMMIT;
