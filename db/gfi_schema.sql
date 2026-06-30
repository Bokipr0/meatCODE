-- =============================================================================
-- GFI Flavor Intelligence Database — v1 schema
-- Generated from Airtable base "GFI database".
-- This is the base schema. Run gfi_schema_v2_migration.sql AFTER this.
-- =============================================================================

BEGIN;

-- =============================================================================
-- 1. ENUM TYPES
-- =============================================================================

CREATE TYPE claim_stance AS ENUM (
    'supports', 'refutes', 'mixed', 'neutral'
);

CREATE TYPE research_field AS ENUM (
    'flavor_chemistry', 'meat_science', 'food_science',
    'analytical_chemistry', 'sensory_science',
    'fermentation', 'plant_protein', 'cell_culture',
    'culinary', 'other'
);

CREATE TYPE outreach_status AS ENUM (
    'not_contacted', 'shortlisted', 'outreach_sent',
    'replied', 'meeting_scheduled', 'advisor', 'not_a_fit'
);

-- trust_tier choices were empty in Airtable; left as free-form TEXT.


-- =============================================================================
-- 2. CORE TABLES
-- =============================================================================

-- 2.1 Sources (papers, articles, patents — pre-typed)
CREATE TABLE sources (
    id           BIGSERIAL PRIMARY KEY,
    name         TEXT NOT NULL,            -- title of the paper / patent
    year         SMALLINT,
    authors      TEXT,                     -- free-text author list (formal authorship comes in v2)
    affiliation  TEXT,
    venue        TEXT,                     -- journal, conference, patent office
    url          TEXT,
    abstract     TEXT,
    notes        TEXT,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_sources_year   ON sources (year);
CREATE INDEX idx_sources_venue  ON sources (venue);

-- 2.2 Molecules (flavor-active compounds)
CREATE TABLE molecules (
    id           BIGSERIAL PRIMARY KEY,
    name         TEXT NOT NULL,
    category     TEXT,                     -- 'Fats' | 'Proteins' | 'Sugars' | 'Unclassified' | ...
    aliases      TEXT[],                   -- alternate names, synonyms
    formula      TEXT,                     -- chemical formula
    smiles       TEXT,                     -- SMILES notation
    cas_number   TEXT,
    pubchem_cid  TEXT,
    notes        TEXT,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_molecules_name      ON molecules (name);
CREATE INDEX idx_molecules_category  ON molecules (category);
CREATE INDEX idx_molecules_cas       ON molecules (cas_number);

-- 2.3 Odours (molecule-level descriptors: floral, woody, sulfurous, ...)
CREATE TABLE odours (
    id           BIGSERIAL PRIMARY KEY,
    name         TEXT NOT NULL UNIQUE,
    notes        TEXT,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);

-- 2.4 Claims (extracted scientific assertions with stance/confidence)
CREATE TABLE claims (
    id           BIGSERIAL PRIMARY KEY,
    claim_text   TEXT NOT NULL,
    stance       claim_stance NOT NULL DEFAULT 'neutral',
    confidence   NUMERIC(3,2) CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
    notes        TEXT,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_claims_stance ON claims (stance);

-- 2.5 Experts (researcher / chef / industry contact directory)
CREATE TABLE experts (
    id              BIGSERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    affiliation     TEXT,                  -- free-text; v2 adds organization_id FK
    email           TEXT,
    research_field  research_field,
    outreach_status outreach_status NOT NULL DEFAULT 'not_contacted',
    trust_tier      TEXT,                  -- empty in Airtable; left as free-form
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_experts_name           ON experts (name);
CREATE INDEX idx_experts_research_field ON experts (research_field);
CREATE INDEX idx_experts_outreach       ON experts (outreach_status);


-- =============================================================================
-- 3. M2M JOIN TABLES
-- =============================================================================

-- 3.1 Claim ↔ Source (a claim is supported by N sources)
CREATE TABLE claim_sources (
    claim_id  BIGINT NOT NULL REFERENCES claims(id)  ON DELETE CASCADE,
    source_id BIGINT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    PRIMARY KEY (claim_id, source_id)
);
CREATE INDEX idx_claim_sources_source ON claim_sources (source_id);

-- 3.2 Claim ↔ Molecule (a claim is about N molecules)
CREATE TABLE claim_molecules (
    claim_id    BIGINT NOT NULL REFERENCES claims(id)    ON DELETE CASCADE,
    molecule_id BIGINT NOT NULL REFERENCES molecules(id) ON DELETE CASCADE,
    PRIMARY KEY (claim_id, molecule_id)
);
CREATE INDEX idx_claim_molecules_molecule ON claim_molecules (molecule_id);

-- 3.3 Source ↔ Molecule (a source mentions N molecules)
CREATE TABLE source_molecules (
    source_id   BIGINT NOT NULL REFERENCES sources(id)   ON DELETE CASCADE,
    molecule_id BIGINT NOT NULL REFERENCES molecules(id) ON DELETE CASCADE,
    PRIMARY KEY (source_id, molecule_id)
);
CREATE INDEX idx_source_molecules_molecule ON source_molecules (molecule_id);

-- 3.4 Molecule ↔ Odour (a molecule has N odour descriptors)
CREATE TABLE molecule_odours (
    molecule_id BIGINT NOT NULL REFERENCES molecules(id) ON DELETE CASCADE,
    odour_id    BIGINT NOT NULL REFERENCES odours(id)    ON DELETE CASCADE,
    PRIMARY KEY (molecule_id, odour_id)
);
CREATE INDEX idx_molecule_odours_odour ON molecule_odours (odour_id);

-- 3.5 Claim ↔ Topic (free-text topic tagging — replaced by topics table in v2)
CREATE TABLE claim_topics (
    claim_id BIGINT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    topic    TEXT   NOT NULL,
    PRIMARY KEY (claim_id, topic)
);

-- 3.6 Expert ↔ Expert (collaboration / advisor / co-author relationships)
CREATE TABLE expert_relations (
    expert_a_id   BIGINT NOT NULL REFERENCES experts(id) ON DELETE CASCADE,
    expert_b_id   BIGINT NOT NULL REFERENCES experts(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,           -- 'collaborator' | 'advisor' | 'co_author' | ...
    notes         TEXT,
    PRIMARY KEY (expert_a_id, expert_b_id, relation_type),
    CHECK (expert_a_id <> expert_b_id)
);
CREATE INDEX idx_expert_relations_b ON expert_relations (expert_b_id);


-- =============================================================================
-- 4. ANALYST-FRIENDLY VIEWS
-- =============================================================================

-- One row per (claim, source, molecule) — the basic evidence join.
CREATE VIEW v_claim_evidence AS
SELECT
    c.id          AS claim_id,
    c.claim_text,
    c.stance,
    c.confidence,
    s.id          AS source_id,
    s.name        AS source_name,
    s.year        AS source_year,
    m.id          AS molecule_id,
    m.name        AS molecule_name
FROM claims c
LEFT JOIN claim_sources   cs ON cs.claim_id   = c.id
LEFT JOIN sources         s  ON s.id          = cs.source_id
LEFT JOIN claim_molecules cm ON cm.claim_id   = c.id
LEFT JOIN molecules       m  ON m.id          = cm.molecule_id;


COMMIT;

-- =============================================================================
-- After this runs successfully, run gfi_schema_v2_migration.sql to add the
-- 13 core entities (topics, sensory_attributes, product_contexts,
-- analytical_methods, organizations, ingredients, reactions, experiments, etc.)
-- =============================================================================