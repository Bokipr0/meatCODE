-- 0021 · 2026-10-29 · Owner-requested demo activation policy; preserve older history.
BEGIN;
SET LOCAL lock_timeout='3s';
SET LOCAL statement_timeout='15s';
ALTER TABLE user_research.sessions DROP CONSTRAINT sessions_consent_version_check;
ALTER TABLE user_research.sessions ADD CONSTRAINT sessions_consent_version_check CHECK
 (consent_version IN ('2026-10-28','2026-10-29','2026-10-29-chat-v1','2026-10-29-journey-v1','2026-10-29-demo-v1'));
ALTER TABLE user_research.oracle_turns DROP CONSTRAINT oracle_turns_consent_version_check;
ALTER TABLE user_research.oracle_turns ADD CONSTRAINT oracle_turns_consent_version_check CHECK
 (consent_version IN ('2026-10-29-chat-v1','2026-10-29-journey-v1','2026-10-29-demo-v1'));
COMMENT ON COLUMN user_research.sessions.consent_version IS 'Policy version: demo-v1 denotes owner-directed first-use activation, journey/chat versions denote explicit opt-in. Do not interpret demo as checkbox consent.';
COMMIT;
