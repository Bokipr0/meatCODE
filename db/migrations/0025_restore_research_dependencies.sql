-- 0025 · 2026-10-31 · Restore missing research intake dependencies.
-- Preflight: research_prod has sessions/events/oracle_turns; feedback, withdrawals,
-- and clarity_exports are absent. No existing rows or scientific objects altered.
-- Additive, idempotent repair of contracts from 0016/0020/0022. Prod research only.
BEGIN;
SET LOCAL lock_timeout='3s';
SET LOCAL statement_timeout='15s';
DO $guard$ BEGIN
 IF current_database()<>'research_prod' THEN
  RAISE EXCEPTION 'Requires dedicated research_prod database';
 END IF;
END $guard$;
CREATE TABLE IF NOT EXISTS user_research.feedback (
    event_id uuid NOT NULL,
    environment text NOT NULL CHECK (environment = 'prod'),
    session_id uuid NOT NULL,
    rating text NOT NULL CHECK (rating IN ('helpful','neutral','unhelpful')),
    category text NOT NULL CHECK (category IN ('answer','usability','bug','other')),
    comment text NOT NULL DEFAULT '' CHECK (char_length(comment) <= 2000),
    elapsed_ms bigint CHECK (elapsed_ms BETWEEN 0 AND 86400000),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (event_id, environment),
    FOREIGN KEY (session_id,environment) REFERENCES user_research.sessions(session_id,environment) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS user_research.withdrawals (
    session_id uuid NOT NULL,
    environment text NOT NULL CHECK (environment = 'prod'),
    withdrawn_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (session_id, environment)
);
CREATE TABLE IF NOT EXISTS user_research.clarity_exports (
    export_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    environment text NOT NULL CHECK (environment = 'prod'),
    project_id text NOT NULL CHECK (project_id ~ '^[a-zA-Z0-9]{1,32}$'),
    export_date date NOT NULL,
    num_of_days smallint NOT NULL CHECK (num_of_days BETWEEN 1 AND 3),
    dimensions text[] NOT NULL DEFAULT ARRAY['Browser','Device','OS']::text[]
        CHECK (dimensions = ARRAY['Browser','Device','OS']::text[]),
    attempts smallint NOT NULL DEFAULT 0 CHECK (attempts BETWEEN 0 AND 10),
    status text NOT NULL CHECK (status IN ('pending','complete','failed')),
    aggregates jsonb,
    imported_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT clarity_export_daily_unique UNIQUE(environment,project_id,export_date,num_of_days),
    CHECK (aggregates IS NULL OR jsonb_typeof(aggregates) = 'array')
);
ALTER TABLE user_research.feedback ADD COLUMN IF NOT EXISTS elapsed_ms bigint CHECK (elapsed_ms BETWEEN 0 AND 86400000);
CREATE INDEX IF NOT EXISTS ur_feedback_created ON user_research.feedback(created_at);
CREATE INDEX IF NOT EXISTS ur_withdrawals_created ON user_research.withdrawals(withdrawn_at);
CREATE INDEX IF NOT EXISTS ur_exports_created ON user_research.clarity_exports(imported_at);
REVOKE ALL ON user_research.feedback,user_research.withdrawals,user_research.clarity_exports FROM PUBLIC;
REVOKE ALL ON SEQUENCE user_research.clarity_exports_export_id_seq FROM PUBLIC;
GRANT SELECT,INSERT,UPDATE,DELETE ON user_research.feedback,user_research.withdrawals,user_research.clarity_exports TO research_prod_writer;
GRANT USAGE,SELECT ON SEQUENCE user_research.clarity_exports_export_id_seq TO research_prod_writer;
GRANT SELECT ON user_research.feedback,user_research.withdrawals,user_research.clarity_exports TO research_prod_reader;
COMMENT ON TABLE user_research.feedback IS 'Private first-party feedback, joined to the tester session; never forwarded to analytics providers.';
COMMENT ON TABLE user_research.withdrawals IS 'Minimal tombstones prevent late requests recreating withdrawn sessions. Repair cannot reconstruct previously missing tombstones.';
COMMIT;
