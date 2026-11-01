-- Reviewed sheet data for the authenticated Ecosystem module.
BEGIN;
SET LOCAL lock_timeout = '3s';
CREATE SCHEMA IF NOT EXISTS ecosystem_module;
REVOKE ALL ON SCHEMA ecosystem_module FROM PUBLIC;
CREATE TABLE IF NOT EXISTS ecosystem_module.inbox_snapshot (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    workbook_id text NOT NULL,
    checked_at timestamptz NOT NULL,
    inbox jsonb NOT NULL CHECK (jsonb_typeof(inbox) = 'object'
      AND inbox ?& ARRAY['experts', 'events', 'courses', 'news', 'eco'])
);
REVOKE ALL ON ecosystem_module.inbox_snapshot FROM PUBLIC;
COMMIT;
