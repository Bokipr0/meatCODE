-- 0018 — Necmettin Karakaya architecture-review access (2026-10-29).
-- User explicitly requested read/view access, never editing. Applied DEV then PROD.
-- Additive role/grants only: no scientific records, schema objects or existing roles changed.
-- Current scientific relations only; no future-table default grants or user_research access.
-- Password/login activation is supplied privately by the provisioner, never committed.
BEGIN;
SET LOCAL lock_timeout='3s';
SET LOCAL statement_timeout='15s';
CREATE ROLE necmettin_review_ro NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
    NOINHERIT NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 3;
COMMENT ON ROLE necmettin_review_ro IS 'Architecture review: Necmettin Karakaya <necmettin.karakaya@gmail.com>; SELECT-only current scientific tables/views; excludes private user_research.';
ALTER ROLE necmettin_review_ro SET default_transaction_read_only=on;
ALTER ROLE necmettin_review_ro SET statement_timeout='15s';
ALTER ROLE necmettin_review_ro SET idle_in_transaction_session_timeout='30s';
DO $$
DECLARE namespace text;
BEGIN
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO necmettin_review_ro',current_database());
    FOREACH namespace IN ARRAY ARRAY['public','moldedup','lightrag_demo'] LOOP
        IF EXISTS(SELECT 1 FROM pg_namespace WHERE nspname=namespace) THEN
            EXECUTE format('GRANT USAGE ON SCHEMA %I TO necmettin_review_ro',namespace);
            EXECUTE format('GRANT SELECT ON ALL TABLES IN SCHEMA %I TO necmettin_review_ro',namespace);
        END IF;
    END LOOP;
END $$;
COMMIT;
