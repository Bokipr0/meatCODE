-- Last updated: 2026-11-21 21:50 UTC · Claude (Opus 5.5) · applied to Neon branch kg-lightrag (br-crimson-fog-alm2s63w); role NOLOGIN until Phase 4; PG16+ SET ROLE fix
-- Run on the kg-lightrag branch only. Idempotent. Applied 2026-11-21 via the Neon connector (as neondb_owner).
CREATE EXTENSION IF NOT EXISTS vector;
-- Created NOLOGIN: no password exists yet. In Phase 4 enable it from a trusted shell, never in chat/logs:
--   ALTER ROLE lightrag_kg LOGIN PASSWORD '<generated>';
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'lightrag_kg') THEN
    CREATE ROLE lightrag_kg NOLOGIN;
  END IF;
END $$;
GRANT lightrag_kg TO CURRENT_USER;                      -- PG16+: owner must be able to SET ROLE to hand over the schema
CREATE SCHEMA IF NOT EXISTS lightrag_kg AUTHORIZATION lightrag_kg;
-- Least privilege: the KG role owns only its schema and cannot read scientific tables.
REVOKE ALL ON SCHEMA public FROM lightrag_kg;
GRANT USAGE ON SCHEMA public TO lightrag_kg;           -- needed to resolve the vector type only
ALTER ROLE lightrag_kg SET search_path = lightrag_kg, public;
