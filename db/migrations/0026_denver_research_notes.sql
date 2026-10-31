-- 0026 · 2026-10-31 · Plain-text Denver notes, without fabricated ratings.
-- Existing feedback and its 90-day retention/session-deletion paths are preserved.
BEGIN;
SET LOCAL lock_timeout='3s';
SET LOCAL statement_timeout='15s';
DO $guard$ BEGIN
 IF current_database()<>'research_prod' THEN RAISE EXCEPTION 'Requires dedicated research_prod'; END IF;
END $guard$;
ALTER TABLE user_research.feedback ADD COLUMN IF NOT EXISTS source text NOT NULL DEFAULT 'feedback' CHECK(source IN ('feedback','denver'));
ALTER TABLE user_research.feedback ADD COLUMN IF NOT EXISTS context jsonb NOT NULL DEFAULT '{}'::jsonb CHECK(jsonb_typeof(context)='object');
ALTER TABLE user_research.feedback ALTER COLUMN rating DROP NOT NULL;
DO $guard$ BEGIN
 IF NOT EXISTS(SELECT 1 FROM pg_constraint WHERE conrelid='user_research.feedback'::regclass AND conname='feedback_rating_or_note') THEN
  ALTER TABLE user_research.feedback ADD CONSTRAINT feedback_rating_or_note CHECK(source='denver' OR rating IS NOT NULL);
 END IF;
END $guard$;
COMMENT ON COLUMN user_research.feedback.context IS 'Server-checked note anchors, capture elapsed time, and explicit missing-context status. Never an account identity.';
COMMIT;
