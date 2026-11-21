-- Last updated: 2026-11-22 UTC · Claude (Sonnet 5.5) · NEW — live DEV feature switches
--
-- The Release Center saves a toggle to features.json, which a server only sees after a deploy. For the DEV column it now
-- ALSO writes a row here; a dev server merges these rows into its flags within seconds, so a dev toggle changes the dev
-- site at once. The CHECK makes production overrides impossible by construction: prod flips only through promote.
-- Idempotent, additive. Not applied automatically — apply to dev first.
CREATE TABLE IF NOT EXISTS feature_flag_overrides (
    env         TEXT        NOT NULL CHECK (env = 'dev'),
    key         TEXT        NOT NULL,
    value       BOOLEAN     NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (env, key)
);
