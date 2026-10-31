-- 0027 · 2026-10-31 · Reassert the established production-only policy after schema repair.
-- Preflight: no nonproduction events or Oracle turns. Adds missing checks; deletes no data.
BEGIN;
SET LOCAL lock_timeout='3s';
SET LOCAL statement_timeout='15s';
DO $policy$
DECLARE target text;
BEGIN
 IF current_database()<>'research_prod' THEN
  RAISE EXCEPTION 'This migration requires the dedicated research_prod database';
 END IF;
 FOREACH target IN ARRAY ARRAY['sessions','events','feedback','oracle_turns','withdrawals','clarity_exports'] LOOP
  IF NOT EXISTS(SELECT 1 FROM pg_constraint WHERE conname='research_production_only'
    AND conrelid=format('user_research.%I',target)::regclass) THEN
   EXECUTE format('ALTER TABLE user_research.%I ADD CONSTRAINT research_production_only CHECK (environment=''prod'')',target);
  END IF;
 END LOOP;
END $policy$;
COMMENT ON SCHEMA user_research IS 'Production-only research intake. Development/local activity is rejected by HTTP policy and database checks; no scientific data dependency.';
COMMIT;
