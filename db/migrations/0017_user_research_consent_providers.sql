-- Last updated: 2026-10-29 10:49 UTC · Data/Backend · preserve old consents while allowing explicit provider-consent renewal.
-- Forward-only: migration0016 is unchanged. No scientific tables or stored rows altered.
-- Existing 2026-10-28 records remain historical; new app capture requires explicit 2026-10-29 consent.
-- Applied DEV then production 2026-10-29 after constraint/record-count checks; all probes rolled back.
BEGIN;
SET LOCAL lock_timeout = '3s';
SET LOCAL statement_timeout = '15s';
ALTER TABLE user_research.sessions DROP CONSTRAINT sessions_consent_version_check;
ALTER TABLE user_research.sessions ADD CONSTRAINT sessions_consent_version_check
    CHECK (consent_version IN ('2026-10-28','2026-10-29'));
COMMIT;
