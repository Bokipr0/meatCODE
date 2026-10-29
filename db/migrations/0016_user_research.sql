-- Last updated: 2026-10-28 15:51 UTC · Data/Backend · isolated consent-based product research storage.
-- Additive schema only: no scientific tables, existing columns, views or corpus data altered.
-- Preflight: 0016 unused locally/current main; schema absence checked before application.
-- Applied and verified 2026-10-28: DEV first, then production; five tables/twelve indexes, no retained test rows.
-- Reproduce via pipeline/user_research/migrate.py; verify.py always rolls back fixtures.
BEGIN;
SET LOCAL lock_timeout = '3s';
SET LOCAL statement_timeout = '15s';
CREATE SCHEMA IF NOT EXISTS user_research;
REVOKE ALL ON SCHEMA user_research FROM PUBLIC;

CREATE TABLE IF NOT EXISTS user_research.sessions (
    session_id uuid NOT NULL,
    environment text NOT NULL CHECK (environment IN ('dev','prod')),
    consent_version text NOT NULL CHECK (consent_version = '2026-10-28'),
    consent_at timestamptz NOT NULL DEFAULT now(),
    created_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (session_id, environment)
);
CREATE TABLE IF NOT EXISTS user_research.events (
    event_id uuid NOT NULL,
    environment text NOT NULL CHECK (environment IN ('dev','prod')),
    session_id uuid NOT NULL,
    name text NOT NULL CHECK (name IN ('session.started','scene.viewed','oracle.submitted',
                                      'oracle.completed','oracle.failed','feedback.submitted')),
    scene text NOT NULL CHECK (scene IN ('oracle','research','science','ecosystem','simulate',
                                        'analytics','database','map','papers','dev','other')),
    duration_ms integer CHECK (duration_ms BETWEEN 0 AND 3600000),
    error_code text CHECK (error_code IN ('network','model_unavailable','session_expired','unknown')),
    source_count integer CHECK (source_count BETWEEN 0 AND 1000),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (event_id, environment),
    FOREIGN KEY (session_id,environment) REFERENCES user_research.sessions(session_id,environment) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS user_research.feedback (
    event_id uuid NOT NULL,
    environment text NOT NULL CHECK (environment IN ('dev','prod')),
    session_id uuid NOT NULL,
    rating text NOT NULL CHECK (rating IN ('helpful','neutral','unhelpful')),
    category text NOT NULL CHECK (category IN ('answer','usability','bug','other')),
    comment text NOT NULL DEFAULT '' CHECK (char_length(comment) <= 2000),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (event_id, environment),
    FOREIGN KEY (session_id,environment) REFERENCES user_research.sessions(session_id,environment) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS user_research.withdrawals (
    session_id uuid NOT NULL,
    environment text NOT NULL CHECK (environment IN ('dev','prod')),
    withdrawn_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (session_id, environment)
);
CREATE TABLE IF NOT EXISTS user_research.clarity_exports (
    export_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    environment text NOT NULL CHECK (environment IN ('dev','prod')),
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
CREATE INDEX IF NOT EXISTS ur_sessions_last_seen ON user_research.sessions(last_seen_at);
CREATE INDEX IF NOT EXISTS ur_events_session_time ON user_research.events(environment,session_id,created_at);
CREATE INDEX IF NOT EXISTS ur_events_created ON user_research.events(created_at);
CREATE INDEX IF NOT EXISTS ur_feedback_created ON user_research.feedback(created_at);
CREATE INDEX IF NOT EXISTS ur_withdrawals_created ON user_research.withdrawals(withdrawn_at);
CREATE INDEX IF NOT EXISTS ur_exports_created ON user_research.clarity_exports(imported_at);
REVOKE ALL ON ALL TABLES IN SCHEMA user_research FROM PUBLIC;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA user_research FROM PUBLIC;
COMMENT ON SCHEMA user_research IS 'Consent-based product research; isolated from scientific evidence. No prompt/answer/replay storage.';
COMMENT ON TABLE user_research.feedback IS 'Explicit first-party tester feedback; never forwarded to Clarity.';
COMMENT ON TABLE user_research.withdrawals IS 'Minimal 90-day tombstones prevent late requests recreating withdrawn sessions.';
COMMENT ON TABLE user_research.clarity_exports IS 'Sanitized dashboard aggregates only; no raw Clarity session recordings/replays.';
COMMIT;
