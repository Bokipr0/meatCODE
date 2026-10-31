-- Dedicated production intake. No archive table is created, dropped or required.
BEGIN;
SET LOCAL lock_timeout='3s';
SET LOCAL statement_timeout='15s';
DO $guard$ BEGIN
 IF current_database()<>'research_prod' THEN RAISE EXCEPTION 'Requires dedicated research_prod'; END IF;
END $guard$;

ALTER TABLE user_research.sessions
  ADD COLUMN IF NOT EXISTS withdrawn_at timestamptz,
  ALTER COLUMN consent_version DROP NOT NULL,
  ALTER COLUMN consent_at DROP NOT NULL;
DO $state$ BEGIN
 IF NOT EXISTS (SELECT FROM pg_constraint WHERE conrelid='user_research.sessions'::regclass AND conname='session_capture_or_withdrawn') THEN
  ALTER TABLE user_research.sessions ADD CONSTRAINT session_capture_or_withdrawn CHECK (
    (withdrawn_at IS NULL AND consent_version IS NOT NULL AND consent_at IS NOT NULL) OR
    (withdrawn_at IS NOT NULL AND consent_version IS NULL AND consent_at IS NULL
     AND tester_label IS NULL AND user_ref IS NULL AND clarity_ref IS NULL
     AND created_at=withdrawn_at AND last_seen_at=withdrawn_at));
 END IF;
END $state$;

-- An older server inserts the legacy marker and then deletes the session in
-- the same transaction. Materialize its marker AFTER its delete, before commit.
CREATE OR REPLACE FUNCTION user_research.mirror_old_withdrawal() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $fn$ BEGIN
 INSERT INTO user_research.sessions(session_id,environment,consent_at,created_at,last_seen_at,withdrawn_at)
 VALUES(NEW.session_id,NEW.environment,NULL,NEW.withdrawn_at,NEW.withdrawn_at,NEW.withdrawn_at)
 ON CONFLICT(session_id,environment) DO NOTHING;
 RETURN NULL;
END $fn$;
-- Older binaries may repeat a DELETE even when their legacy INSERT did nothing.
CREATE OR REPLACE FUNCTION user_research.keep_recent_marker() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $fn$ BEGIN
 IF OLD.withdrawn_at > now()-interval '90 days' THEN RETURN NULL; END IF;
 RETURN OLD;
END $fn$;
REVOKE ALL ON FUNCTION user_research.mirror_old_withdrawal(),user_research.keep_recent_marker() FROM PUBLIC;
DO $legacy$ BEGIN
 IF to_regclass('user_research.withdrawals') IS NOT NULL THEN
  LOCK TABLE user_research.withdrawals IN SHARE ROW EXCLUSIVE MODE;
  IF EXISTS (SELECT FROM user_research.withdrawals w JOIN user_research.sessions s USING(session_id,environment)
      WHERE s.withdrawn_at IS NULL) THEN RAISE EXCEPTION 'Active session overlaps legacy withdrawal; review before migration'; END IF;
  INSERT INTO user_research.sessions(session_id,environment,consent_at,created_at,last_seen_at,withdrawn_at)
   SELECT session_id,environment,NULL,withdrawn_at,withdrawn_at,withdrawn_at FROM user_research.withdrawals
   WHERE withdrawn_at > now()-interval '90 days' ON CONFLICT DO NOTHING;
  IF NOT EXISTS (SELECT FROM pg_trigger WHERE tgrelid='user_research.withdrawals'::regclass AND tgname='mirror_old_withdrawal') THEN
   CREATE CONSTRAINT TRIGGER mirror_old_withdrawal AFTER INSERT ON user_research.withdrawals
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION user_research.mirror_old_withdrawal();
  END IF;
  CREATE OR REPLACE TRIGGER keep_recent_marker BEFORE DELETE ON user_research.sessions
    FOR EACH ROW WHEN (OLD.withdrawn_at IS NOT NULL) EXECUTE FUNCTION user_research.keep_recent_marker();
 END IF;
END $legacy$;
COMMENT ON COLUMN user_research.sessions.withdrawn_at IS 'Non-null marks a deleted session: no tester name, consent, user reference, chats or notes. Reject late writes until retention cleanup.';
COMMIT;
