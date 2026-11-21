-- Last updated: 2026-11-21 UTC · Claude (Sonnet 5.5) · NEW — Claude-first accounts: a person can start with "Link your Claude organization" and no email/password
--
-- * app_users.email / password_hash become optional (a Claude-only profile has neither until the person adds them).
-- * app_users.claude_only marks those profiles. The existing UNIQUE index on lower(email) already allows many NULLs.
-- * app_sessions.pending: the session handed out when linking STARTS. It is not authorization — it only lets the
--   browser finish the Claude approval; the server turns it into a normal session when the link completes.
-- Idempotent, additive, nothing existing is rewritten. Not applied automatically — apply to dev first.

ALTER TABLE app_users    ALTER COLUMN email         DROP NOT NULL;
ALTER TABLE app_users    ALTER COLUMN password_hash DROP NOT NULL;
ALTER TABLE app_users    ADD COLUMN IF NOT EXISTS claude_only BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE app_sessions ADD COLUMN IF NOT EXISTS pending     BOOLEAN NOT NULL DEFAULT FALSE;
