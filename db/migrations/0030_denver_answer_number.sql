-- Session-scoped ordinal for answers completed while Denver rating is enabled.
BEGIN;
SET LOCAL lock_timeout='3s';
DO $guard$ BEGIN
 IF current_database()<>'research_prod' THEN RAISE EXCEPTION 'Requires dedicated research_prod'; END IF;
END $guard$;
ALTER TABLE user_research.oracle_turns ADD COLUMN IF NOT EXISTS answer_number integer
 CHECK (answer_number IS NULL OR (answer_number > 0 AND status='complete'));
CREATE UNIQUE INDEX IF NOT EXISTS ur_completed_answer_number ON user_research.oracle_turns(environment,session_id,answer_number)
 WHERE answer_number IS NOT NULL;
COMMIT;
