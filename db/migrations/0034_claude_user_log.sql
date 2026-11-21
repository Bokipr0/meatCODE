-- Last updated: 2026-11-21 UTC · Claude (Sonnet 5.5) · NEW — tie every billed Claude request to that specific Claude user, with last use
--
-- What MeatCODE holds about a person's Claude connection is NOT a secret: it is two opaque ids Claude hands out
-- (user_profile_id + connection_id, already in claude_connections). This migration keeps them current and makes each
-- logged request carry them:
--   * claude_connections.last_used_at  — last time a request was billed to this person's Claude organization.
--   * app_usage_log gains the Claude identity (user_profile_id, connection_id) as it was AT THE TIME of the call, the
--     login session it ran in (session_ref = first 12 hex of the stored session hash), and — for answers — the person's
--     input and the answer text. Helper calls (decisions, consensus, intent) keep tokens/route only.
-- NOTE: this supersedes the "metadata only" comment in 0032: from now on answers' input/output text is stored under the
-- person's profile (disclosed on /connect). Idempotent, additive. Not applied automatically — apply to dev first.

ALTER TABLE claude_connections ADD COLUMN IF NOT EXISTS last_used_at TIMESTAMPTZ;

ALTER TABLE app_usage_log ADD COLUMN IF NOT EXISTS user_profile_id TEXT;
ALTER TABLE app_usage_log ADD COLUMN IF NOT EXISTS connection_id   TEXT;
ALTER TABLE app_usage_log ADD COLUMN IF NOT EXISTS session_ref     TEXT;
ALTER TABLE app_usage_log ADD COLUMN IF NOT EXISTS input_text      TEXT;
ALTER TABLE app_usage_log ADD COLUMN IF NOT EXISTS output_text     TEXT;

CREATE INDEX IF NOT EXISTS app_usage_log_profile_idx ON app_usage_log (user_profile_id, created_at DESC);
CREATE INDEX IF NOT EXISTS app_usage_log_session_idx ON app_usage_log (session_ref, created_at);
