-- Last updated: 2026-11-21 UTC · Claude (Sonnet 5.5) · NEW — per-user usage log for requests billed to the user's own Claude organization
--
-- One row per Claude call made on a signed-in individual's behalf (flag `user_accounts`). METADATA ONLY: route,
-- model, token counts, status. Never the question, the answer or any source text. Powers the profile pop-out's
-- "usage" block. Idempotent. Not applied automatically — apply to dev first.

CREATE TABLE IF NOT EXISTS app_usage_log (
    id             BIGSERIAL PRIMARY KEY,
    user_id        BIGINT      NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    route          TEXT        NOT NULL,                  -- e.g. /api/ask
    model          TEXT,
    input_tokens   INTEGER     NOT NULL DEFAULT 0,
    output_tokens  INTEGER     NOT NULL DEFAULT 0,
    billed_to      TEXT        NOT NULL DEFAULT 'user_profile',
    status         TEXT        NOT NULL DEFAULT 'ok' CHECK (status IN ('ok', 'error'))
);
CREATE INDEX IF NOT EXISTS app_usage_log_user_time_idx ON app_usage_log (user_id, created_at DESC);
