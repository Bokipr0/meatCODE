-- Last updated: 2026-11-21 UTC · Claude (Sonnet 5.5) · NEW — individual user accounts + Claude "Linked billing" connections
--
-- Adds three tables behind the `user_accounts` feature flag. NOT APPLIED automatically: the Data Engineer /
-- Lior applies this to dev first (see platform_docs/CLAUDE_LINKED_BILLING_SETUP.md). Idempotent — safe to re-run.
-- Nothing here stores a Claude/OpenAI/Anthropic secret: a linked billing connection is just two opaque IDs
-- (the user profile in OUR Claude org + the connection id Anthropic returns). Passwords are scrypt hashes;
-- session tokens are stored only as SHA-256 hashes.

CREATE TABLE IF NOT EXISTS app_users (
    id             BIGSERIAL PRIMARY KEY,
    email          TEXT        NOT NULL,
    password_hash  TEXT        NOT NULL,
    display_name   TEXT,
    disabled       BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login_at  TIMESTAMPTZ
);
CREATE UNIQUE INDEX IF NOT EXISTS app_users_email_lower_uq ON app_users (lower(email));

CREATE TABLE IF NOT EXISTS app_sessions (
    token_hash  TEXT PRIMARY KEY,                       -- sha256(hex) of the cookie token; the raw token is never stored
    user_id     BIGINT      NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at  TIMESTAMPTZ NOT NULL,
    user_agent  TEXT
);
CREATE INDEX IF NOT EXISTS app_sessions_user_idx    ON app_sessions (user_id);
CREATE INDEX IF NOT EXISTS app_sessions_expires_idx ON app_sessions (expires_at);

CREATE TABLE IF NOT EXISTS claude_connections (
    user_id             BIGINT PRIMARY KEY REFERENCES app_users(id) ON DELETE CASCADE,
    user_profile_id     TEXT,                           -- "uprof_…" — the record in OUR Claude org that stands for this user
    connection_id       TEXT,                           -- "ocon_…" — returned by Anthropic when the user approves
    status              TEXT        NOT NULL DEFAULT 'unlinked'
                        CHECK (status IN ('unlinked', 'pending', 'linked', 'revoked')),
    -- in-flight authorization (cleared on callback): state + PKCE verifier, valid 10 minutes
    pending_state_hash  TEXT,
    pending_verifier    TEXT,
    pending_expires_at  TIMESTAMPTZ,
    linked_at           TIMESTAMPTZ,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_error          TEXT
);
-- Anthropic's rule: one Claude organization <-> one user profile, so one profile id must never be shared.
CREATE UNIQUE INDEX IF NOT EXISTS claude_connections_profile_uq
    ON claude_connections (user_profile_id) WHERE user_profile_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS claude_connections_state_idx
    ON claude_connections (pending_state_hash) WHERE pending_state_hash IS NOT NULL;
