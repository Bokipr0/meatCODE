-- Last updated: 2026-11-24 UTC · Yochai (PM) with Claude · NEW — Ecosystem directory people table
--
-- One row per person for the Ecosystem Directory (flag ecosystem_directory). Built by
-- pipeline/ecosystem/build_directory.py from public.experts (all batches) plus Daniel's Ecosystem Master workbook,
-- with high-confidence de-duplication and paper links. PUBLIC FIELDS ONLY: no email, no relationship / outreach /
-- LinkedIn-message data, no Master group membership. public.experts is not modified.
-- master_ids and name_keys are internal (re-sync and matching); the API never returns them.
-- Idempotent, additive. Apply to a Neon branch first, then dev, then production.
CREATE SCHEMA IF NOT EXISTS ecosystem_module;

CREATE TABLE IF NOT EXISTS ecosystem_module.directory_people (
    id            TEXT        PRIMARY KEY,   -- lowest merged experts.id as digits, else 'm-<Master Contact ID>'
    name          TEXT        NOT NULL,
    org           TEXT,                      -- display affiliation
    orgs          TEXT[]      NOT NULL DEFAULT '{}',   -- every affiliation seen (search)
    role          TEXT,
    about         TEXT,                      -- short public expertise line
    country       TEXT,                      -- ISO 3166-1 alpha-2
    sector        TEXT        NOT NULL DEFAULT 'unknown' CHECK (sector IN ('academic','industry','ngo','unknown')),
    topics        TEXT[]      NOT NULL DEFAULT '{}',   -- taxonomy topic slugs (db/taxonomy/keywords_topics.json)
    domains       TEXT[]      NOT NULL DEFAULT '{}',   -- free-text technical domains
    h_index       INTEGER,
    orcid         TEXT,
    openalex_id   TEXT,
    linkedin_url  TEXT,
    website_urls  TEXT[]      NOT NULL DEFAULT '{}',
    papers        INTEGER[]   NOT NULL DEFAULT '{}',   -- sources.id matched by author name
    expert_ids    INTEGER[]   NOT NULL DEFAULT '{}',   -- merged public.experts rows
    master_ids    TEXT[]      NOT NULL DEFAULT '{}',   -- internal: Master Contact IDs
    sources       TEXT[]      NOT NULL DEFAULT '{}',   -- openalex | dimensions | dd_list | gfi_contacts
    name_keys     TEXT[]      NOT NULL DEFAULT '{}',   -- internal: normalised first+last keys
    built_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS directory_people_country_idx ON ecosystem_module.directory_people (country);
CREATE INDEX IF NOT EXISTS directory_people_sector_idx ON ecosystem_module.directory_people (sector);
