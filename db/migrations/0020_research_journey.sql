-- 0020 · 2026-10-29 · Consent-scoped journey references and submission timing.
-- Additive nullable columns preserve unknown history and rolling old-client compatibility.
BEGIN;
SET LOCAL lock_timeout='3s';
SET LOCAL statement_timeout='15s';
ALTER TABLE user_research.sessions DROP CONSTRAINT sessions_consent_version_check;
ALTER TABLE user_research.sessions ADD CONSTRAINT sessions_consent_version_check CHECK
 (consent_version IN ('2026-10-28','2026-10-29','2026-10-29-chat-v1','2026-10-29-journey-v1'));
ALTER TABLE user_research.oracle_turns DROP CONSTRAINT oracle_turns_consent_version_check;
ALTER TABLE user_research.oracle_turns ADD CONSTRAINT oracle_turns_consent_version_check CHECK
 (consent_version IN ('2026-10-29-chat-v1','2026-10-29-journey-v1'));
ALTER TABLE user_research.sessions ADD COLUMN IF NOT EXISTS user_ref uuid;
ALTER TABLE user_research.sessions ADD COLUMN IF NOT EXISTS clarity_ref uuid;
ALTER TABLE user_research.sessions ADD COLUMN IF NOT EXISTS tester_label varchar(80);
ALTER TABLE user_research.sessions DROP CONSTRAINT IF EXISTS ur_distinct_journey_refs;
ALTER TABLE user_research.sessions ADD CONSTRAINT ur_distinct_journey_refs CHECK
 (user_ref IS DISTINCT FROM session_id AND clarity_ref IS DISTINCT FROM session_id
 AND (user_ref IS NULL OR clarity_ref IS NULL OR user_ref<>clarity_ref));
ALTER TABLE user_research.oracle_turns ADD COLUMN IF NOT EXISTS elapsed_ms bigint CHECK(elapsed_ms BETWEEN 0 AND 86400000);
ALTER TABLE user_research.events ADD COLUMN IF NOT EXISTS elapsed_ms bigint CHECK(elapsed_ms BETWEEN 0 AND 86400000);
ALTER TABLE user_research.feedback ADD COLUMN IF NOT EXISTS elapsed_ms bigint CHECK(elapsed_ms BETWEEN 0 AND 86400000);
ALTER TABLE user_research.events DROP CONSTRAINT events_name_check;
ALTER TABLE user_research.events ADD CONSTRAINT events_name_check CHECK
 (name IN ('session.started','scene.viewed','module.clicked','oracle.submitted','oracle.completed','oracle.failed','feedback.submitted'));
ALTER TABLE user_research.events DROP CONSTRAINT events_scene_check;
ALTER TABLE user_research.events ADD CONSTRAINT events_scene_check CHECK
 (scene IN ('oracle','research','science','ecosystem','simulate','analytics','database','map','papers','dev','inventory','other'));
CREATE INDEX IF NOT EXISTS ur_sessions_clarity_ref ON user_research.sessions(environment,clarity_ref) WHERE clarity_ref IS NOT NULL;
COMMENT ON COLUMN user_research.sessions.user_ref IS 'Optional consented tab pseudonym; not an account identifier or session deletion capability.';
COMMENT ON COLUMN user_research.sessions.clarity_ref IS 'Opaque reference sent as Clarity research_reference tag only after explicit journey-sharing consent; never session_id.';
COMMENT ON COLUMN user_research.oracle_turns.elapsed_ms IS 'Browser-observed elapsed milliseconds since joining this tab testing journey, sampled on question submission; NULL means unknown.';
COMMENT ON SCHEMA user_research IS 'Private consented product telemetry, optional Oracle transcripts and journey references; isolated from scientific evidence.';
COMMIT;
