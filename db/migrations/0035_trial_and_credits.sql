-- Last updated: 2026-11-22 UTC · Claude (Sonnet 5.5) · NEW — free trial sessions on MeatCODE's key, then the person's own credits
--
-- * app_usage_log.kind     'answer' (a person's question answered) | 'helper' (small supporting calls). The free trial
--                          counts ANSWERS only; with billed_to='trial' it records which calls were on MeatCODE's own key.
-- * claude_connections.needs_credits(+_at)  set when Claude refuses a call billed to the person's own organization for
--                          lack of credit (HTTP 402 / user_profile_not_billable); cleared by the next successful billed
--                          call. Drives the highlighted "Add credits" button.
-- Idempotent, additive. Not applied automatically — apply to dev first.

ALTER TABLE app_usage_log ADD COLUMN IF NOT EXISTS kind TEXT;
ALTER TABLE claude_connections ADD COLUMN IF NOT EXISTS needs_credits BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE claude_connections ADD COLUMN IF NOT EXISTS needs_credits_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS app_usage_log_trial_idx ON app_usage_log (user_id, created_at)
    WHERE billed_to = 'trial' AND kind = 'answer';
