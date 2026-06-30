-- =============================================================================
-- GFI Flavor Intelligence Database — v2 migration
-- Adds the 13 core entities and their relationships on top of gfi_schema.sql.
--
--   Paper / Patent / Report   -> sources (extended) + source_type enum
--   Molecule                  -> molecules (existing)
--   Precursor                 -> reaction_participants (role='precursor')
--                                + molecule_role_tags
--   Reaction / pathway        -> reactions, reaction_participants
--   Ingredient                -> ingredients, ingredient_molecules
--   Matrix                    -> matrix_profiles
--   Process condition         -> processes
--   Product type              -> product_contexts, source_product_contexts,
--                                experiment_product_contexts
--   Sensory attribute         -> sensory_attributes (+ four M2M tables)
--   Analytical method         -> analytical_methods (+ M2M tables)
--   Expert / organization     -> experts (extended) + organizations
--   Claim / insight           -> claims (existing) + claim_experiments,
--                                claim_reactions, claim_sensory_attributes
--   Experiment / dataset      -> experiments, experiment_*
--
-- Run once, on top of v1. Wrapped in a single transaction.
-- =============================================================================

BEGIN;

-- =============================================================================
-- 1. NEW ENUM TYPES
-- =============================================================================

CREATE TYPE source_type AS ENUM (
    'article', 'patent', 'report',
    'osint_news', 'osint_culinary', 'ongoing_research'
);

CREATE TYPE expert_org_type AS ENUM (
    'company', 'academy', 'ngo_gov', 'culinary'
);

CREATE TYPE evidence_strength AS ENUM ('low', 'medium', 'high');

CREATE TYPE actionability AS ENUM ('low', 'medium', 'medium_high', 'high');

CREATE TYPE molecule_role AS ENUM (
    'precursor', 'intermediate', 'product',
    'catalyst', 'inhibitor', 'matrix_component', 'sourcing_marker'
);

CREATE TYPE reaction_kind AS ENUM (
    'maillard', 'lipid_oxidation', 'strecker_degradation', 'caramelization',
    'enzymatic_hydrolysis', 'fermentation', 'thermal_degradation',
    'oxidation', 'reduction', 'condensation', 'pyrolysis', 'other'
);

CREATE TYPE cooking_method AS ENUM (
    'pan_frying', 'grilling', 'roasting', 'boiling_stewing',
    'pressure_cooking', 'microwave', 'sous_vide',
    'extrusion_low_moisture', 'extrusion_high_moisture',
    'fermentation', 'enzymatic_hydrolysis', 'aging', 'storage_oxidation'
);

CREATE TYPE protein_source AS ENUM (
    'soy', 'pea', 'wheat_gluten', 'faba', 'mycoprotein',
    'animal_derived', 'hybrid', 'other'
);

CREATE TYPE fat_source AS ENUM (
    'tallow', 'pork_fat', 'chicken_fat', 'coconut_oil',
    'canola_rapeseed', 'sunflower', 'oleogel', 'structured_fat', 'other'
);

CREATE TYPE ingredient_category AS ENUM (
    'protein_isolate', 'protein_concentrate', 'fat', 'oil',
    'flavor_compound_blend', 'yeast_extract', 'enzyme_preparation',
    'reaction_flavor', 'extract', 'seasoning', 'colorant', 'other'
);

CREATE TYPE participant_role AS ENUM (
    'precursor', 'intermediate', 'product',
    'catalyst', 'inhibitor', 'cofactor'
);


-- =============================================================================
-- 2. EXTEND EXISTING TABLES
-- =============================================================================

-- 2.1 sources: source-type model + evaluation layer
ALTER TABLE sources
    ADD COLUMN IF NOT EXISTS source_type        source_type,
    ADD COLUMN IF NOT EXISTS doi                TEXT,
    ADD COLUMN IF NOT EXISTS patent_number      TEXT,
    ADD COLUMN IF NOT EXISTS assignee           TEXT,
    ADD COLUMN IF NOT EXISTS jurisdiction       TEXT,
    ADD COLUMN IF NOT EXISTS species_reference  TEXT,
    ADD COLUMN IF NOT EXISTS evidence_strength  evidence_strength,
    ADD COLUMN IF NOT EXISTS actionability      actionability,
    ADD COLUMN IF NOT EXISTS usefulness_tags    TEXT[],
    ADD COLUMN IF NOT EXISTS metadata           JSONB DEFAULT '{}'::jsonb;

CREATE UNIQUE INDEX IF NOT EXISTS idx_sources_doi_unique     ON sources (doi)            WHERE doi IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_sources_patent_unique  ON sources (patent_number)  WHERE patent_number IS NOT NULL;
CREATE INDEX        IF NOT EXISTS idx_sources_type            ON sources (source_type);
CREATE INDEX        IF NOT EXISTS idx_sources_evidence        ON sources (evidence_strength);
CREATE INDEX        IF NOT EXISTS idx_sources_species         ON sources (species_reference);

-- 2.2 experts: organization affiliation + culinary org type
ALTER TABLE experts
    ADD COLUMN IF NOT EXISTS org_type        expert_org_type,
    ADD COLUMN IF NOT EXISTS organization_id BIGINT;          -- FK added after org table

CREATE INDEX IF NOT EXISTS idx_experts_org_type ON experts (org_type);


-- =============================================================================
-- 3. NEW LOOKUP / DIMENSION TABLES
-- =============================================================================

-- 3.1 Topics (hierarchical taxonomy from the Miro mind map)
CREATE TABLE topics (
    id           BIGSERIAL PRIMARY KEY,
    slug         TEXT UNIQUE NOT NULL,
    name         TEXT NOT NULL,
    parent_id    BIGINT REFERENCES topics(id) ON DELETE SET NULL,
    root_branch  TEXT NOT NULL,           -- 'flavor_chemistry' | 'analytics' | 'meat_science' | ...
    level        SMALLINT NOT NULL DEFAULT 0,
    description  TEXT,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_topics_parent      ON topics (parent_id);
CREATE INDEX idx_topics_root_branch ON topics (root_branch);

-- 3.2 Sensory attributes (with off-note hierarchy via parent_id)
CREATE TABLE sensory_attributes (
    id           BIGSERIAL PRIMARY KEY,
    slug         TEXT UNIQUE NOT NULL,
    name         TEXT NOT NULL,
    parent_id    BIGINT REFERENCES sensory_attributes(id) ON DELETE SET NULL,
    is_off_note  BOOLEAN NOT NULL DEFAULT FALSE,
    description  TEXT,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_sensory_parent  ON sensory_attributes (parent_id);
CREATE INDEX idx_sensory_offnote ON sensory_attributes (is_off_note);

-- 3.3 Product contexts (Ground beef burger, Steak, Chicken analogue, ...)
CREATE TABLE product_contexts (
    id          BIGSERIAL PRIMARY KEY,
    slug        TEXT UNIQUE NOT NULL,
    name        TEXT NOT NULL,
    category    TEXT NOT NULL,            -- 'animal' | 'plant_analogue' | 'hybrid' | 'ingredient'
    description TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_product_contexts_category ON product_contexts (category);

-- 3.4 Analytical methods (HS-SPME-GC-MS, sensory panel, omics, ...)
CREATE TABLE analytical_methods (
    id          BIGSERIAL PRIMARY KEY,
    slug        TEXT UNIQUE NOT NULL,
    name        TEXT NOT NULL,
    category    TEXT NOT NULL,            -- 'chromatography' | 'sensory' | 'omics' | 'spectroscopy' | 'other'
    description TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_methods_category ON analytical_methods (category);


-- =============================================================================
-- 4. NEW CORE ENTITIES
-- =============================================================================

-- 4.1 Organizations (resolves Companies / Academy / NGO·GOV / Culinary branch)
CREATE TABLE organizations (
    id          BIGSERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    org_type    expert_org_type NOT NULL,
    country     TEXT,
    website     TEXT,
    description TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_orgs_type    ON organizations (org_type);
CREATE INDEX idx_orgs_country ON organizations (country);

ALTER TABLE experts
    ADD CONSTRAINT fk_experts_organization
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE SET NULL;

-- 4.2 Ingredients (composite materials: yeast extract, soy isolate, tallow, ...)
CREATE TABLE ingredients (
    id          BIGSERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    category    ingredient_category NOT NULL,
    supplier    TEXT,
    description TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_ingredients_category ON ingredients (category);

-- An ingredient is composed of molecules (optional w/w proportion)
CREATE TABLE ingredient_molecules (
    ingredient_id   BIGINT NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
    molecule_id     BIGINT NOT NULL REFERENCES molecules(id)   ON DELETE CASCADE,
    proportion_pct  NUMERIC(6,3) CHECK (proportion_pct IS NULL OR proportion_pct BETWEEN 0 AND 100),
    notes           TEXT,
    PRIMARY KEY (ingredient_id, molecule_id)
);
CREATE INDEX idx_ingredient_molecules_molecule ON ingredient_molecules (molecule_id);

-- 4.3 Reactions / pathways (parent_id allows: pathway -> sub-reactions)
CREATE TABLE reactions (
    id           BIGSERIAL PRIMARY KEY,
    slug         TEXT UNIQUE NOT NULL,
    name         TEXT NOT NULL,
    kind         reaction_kind NOT NULL,
    parent_id    BIGINT REFERENCES reactions(id) ON DELETE SET NULL,
    description  TEXT,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_reactions_kind   ON reactions (kind);
CREATE INDEX idx_reactions_parent ON reactions (parent_id);

-- A molecule (or ingredient) participating in a reaction with a specific role.
-- This is where "Precursor" lives: role = 'precursor'.
CREATE TABLE reaction_participants (
    id            BIGSERIAL PRIMARY KEY,
    reaction_id   BIGINT NOT NULL REFERENCES reactions(id) ON DELETE CASCADE,
    molecule_id   BIGINT REFERENCES molecules(id)   ON DELETE CASCADE,
    ingredient_id BIGINT REFERENCES ingredients(id) ON DELETE CASCADE,
    role          participant_role NOT NULL,
    notes         TEXT,
    -- exactly one of molecule_id / ingredient_id must be set
    CHECK (
        (molecule_id IS NOT NULL AND ingredient_id IS NULL)
     OR (molecule_id IS NULL AND ingredient_id IS NOT NULL)
    )
);
CREATE INDEX idx_rxn_part_reaction   ON reaction_participants (reaction_id);
CREATE INDEX idx_rxn_part_molecule   ON reaction_participants (molecule_id);
CREATE INDEX idx_rxn_part_ingredient ON reaction_participants (ingredient_id);
CREATE INDEX idx_rxn_part_role       ON reaction_participants (role);

-- 4.4 Experiments / datasets (the unit of empirical observation within a source)
CREATE TABLE experiments (
    id           BIGSERIAL PRIMARY KEY,
    source_id    BIGINT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    dataset_url  TEXT,                   -- if a public dataset (Zenodo, OSF, supp. info)
    description  TEXT,
    notes        TEXT,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_experiments_source ON experiments (source_id);

-- 4.5 Process conditions (cooking / extrusion / aging / storage steps)
-- Linked to either a source (paper-level summary) or an experiment (specific run).
CREATE TABLE processes (
    id                BIGSERIAL PRIMARY KEY,
    source_id         BIGINT REFERENCES sources(id)     ON DELETE CASCADE,
    experiment_id     BIGINT REFERENCES experiments(id) ON DELETE CASCADE,
    cooking_method    cooking_method,
    step_label        TEXT,           -- 'cook', 'post-extrusion flavoring', 'storage', ...
    temperature_c     NUMERIC(6,2),
    time_min          NUMERIC(8,2),
    ph                NUMERIC(4,2)   CHECK (ph IS NULL OR ph BETWEEN 0 AND 14),
    water_activity    NUMERIC(4,3)   CHECK (water_activity IS NULL OR water_activity BETWEEN 0 AND 1),
    oxygen_available  BOOLEAN,
    fat_phase_pct     NUMERIC(5,2),
    aqueous_phase_pct NUMERIC(5,2),
    notes             TEXT,
    CHECK (source_id IS NOT NULL OR experiment_id IS NOT NULL)
);
CREATE INDEX idx_processes_source     ON processes (source_id);
CREATE INDEX idx_processes_experiment ON processes (experiment_id);
CREATE INDEX idx_processes_method     ON processes (cooking_method);

-- 4.6 Matrix profiles (formulation snapshot)
CREATE TABLE matrix_profiles (
    id                  BIGSERIAL PRIMARY KEY,
    source_id           BIGINT REFERENCES sources(id)     ON DELETE CASCADE,
    experiment_id       BIGINT REFERENCES experiments(id) ON DELETE CASCADE,
    protein_source      protein_source,
    fat_source          fat_source,
    water_activity      NUMERIC(4,3) CHECK (water_activity IS NULL OR water_activity BETWEEN 0 AND 1),
    emulsion_structure  TEXT,         -- 'O/W', 'W/O', 'W/O/W', 'gel', ...
    gel_network         TEXT,
    fiber_structure     TEXT,
    encapsulation       TEXT,
    release_kinetics    TEXT,
    flavor_binding      TEXT,
    notes               TEXT,
    CHECK (source_id IS NOT NULL OR experiment_id IS NOT NULL)
);
CREATE INDEX idx_matrix_source     ON matrix_profiles (source_id);
CREATE INDEX idx_matrix_experiment ON matrix_profiles (experiment_id);
CREATE INDEX idx_matrix_protein    ON matrix_profiles (protein_source);
CREATE INDEX idx_matrix_fat        ON matrix_profiles (fat_source);


-- =============================================================================
-- 5. NEW M2M JOIN TABLES
-- =============================================================================

-- 5.1 Topics
CREATE TABLE source_topics (
    source_id BIGINT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    topic_id  BIGINT NOT NULL REFERENCES topics(id)  ON DELETE CASCADE,
    PRIMARY KEY (source_id, topic_id)
);
CREATE INDEX idx_source_topics_topic ON source_topics (topic_id);

-- New normalized claim ↔ topic table. Old free-text claim_topics stays in place
-- until the post-migration backfill (see TODO at the bottom of this file).
CREATE TABLE claim_topics_v2 (
    claim_id BIGINT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    topic_id BIGINT NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    PRIMARY KEY (claim_id, topic_id)
);
CREATE INDEX idx_claim_topics_v2_topic ON claim_topics_v2 (topic_id);

CREATE TABLE reaction_topics (
    reaction_id BIGINT NOT NULL REFERENCES reactions(id) ON DELETE CASCADE,
    topic_id    BIGINT NOT NULL REFERENCES topics(id)    ON DELETE CASCADE,
    PRIMARY KEY (reaction_id, topic_id)
);

-- 5.2 Sensory attributes
CREATE TABLE source_sensory_attributes (
    source_id    BIGINT NOT NULL REFERENCES sources(id)            ON DELETE CASCADE,
    attribute_id BIGINT NOT NULL REFERENCES sensory_attributes(id) ON DELETE CASCADE,
    PRIMARY KEY (source_id, attribute_id)
);
CREATE INDEX idx_source_sensory_attribute ON source_sensory_attributes (attribute_id);

CREATE TABLE claim_sensory_attributes (
    claim_id     BIGINT NOT NULL REFERENCES claims(id)             ON DELETE CASCADE,
    attribute_id BIGINT NOT NULL REFERENCES sensory_attributes(id) ON DELETE CASCADE,
    PRIMARY KEY (claim_id, attribute_id)
);

CREATE TABLE molecule_sensory_attributes (
    molecule_id  BIGINT NOT NULL REFERENCES molecules(id)          ON DELETE CASCADE,
    attribute_id BIGINT NOT NULL REFERENCES sensory_attributes(id) ON DELETE CASCADE,
    PRIMARY KEY (molecule_id, attribute_id)
);

CREATE TABLE experiment_sensory_attributes (
    experiment_id BIGINT NOT NULL REFERENCES experiments(id)        ON DELETE CASCADE,
    attribute_id  BIGINT NOT NULL REFERENCES sensory_attributes(id) ON DELETE CASCADE,
    intensity     NUMERIC(5,2),                  -- 0..100 panel score, optional
    PRIMARY KEY (experiment_id, attribute_id)
);

-- 5.3 Product contexts
CREATE TABLE source_product_contexts (
    source_id  BIGINT NOT NULL REFERENCES sources(id)          ON DELETE CASCADE,
    context_id BIGINT NOT NULL REFERENCES product_contexts(id) ON DELETE CASCADE,
    role       TEXT NOT NULL DEFAULT 'primary'
               CHECK (role IN ('primary','alternative','reference')),
    PRIMARY KEY (source_id, context_id, role)
);
CREATE INDEX idx_spc_context ON source_product_contexts (context_id);

CREATE TABLE experiment_product_contexts (
    experiment_id BIGINT NOT NULL REFERENCES experiments(id)      ON DELETE CASCADE,
    context_id    BIGINT NOT NULL REFERENCES product_contexts(id) ON DELETE CASCADE,
    role          TEXT NOT NULL DEFAULT 'primary'
                  CHECK (role IN ('primary','alternative','reference')),
    PRIMARY KEY (experiment_id, context_id, role)
);

-- 5.4 Analytical methods
CREATE TABLE source_methods (
    source_id BIGINT NOT NULL REFERENCES sources(id)            ON DELETE CASCADE,
    method_id BIGINT NOT NULL REFERENCES analytical_methods(id) ON DELETE CASCADE,
    PRIMARY KEY (source_id, method_id)
);

CREATE TABLE experiment_methods (
    experiment_id BIGINT NOT NULL REFERENCES experiments(id)        ON DELETE CASCADE,
    method_id     BIGINT NOT NULL REFERENCES analytical_methods(id) ON DELETE CASCADE,
    PRIMARY KEY (experiment_id, method_id)
);

-- 5.5 Reactions on sources / experiments / claims
CREATE TABLE source_reactions (
    source_id   BIGINT NOT NULL REFERENCES sources(id)   ON DELETE CASCADE,
    reaction_id BIGINT NOT NULL REFERENCES reactions(id) ON DELETE CASCADE,
    PRIMARY KEY (source_id, reaction_id)
);

CREATE TABLE experiment_reactions (
    experiment_id BIGINT NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    reaction_id   BIGINT NOT NULL REFERENCES reactions(id)   ON DELETE CASCADE,
    PRIMARY KEY (experiment_id, reaction_id)
);

CREATE TABLE claim_reactions (
    claim_id    BIGINT NOT NULL REFERENCES claims(id)    ON DELETE CASCADE,
    reaction_id BIGINT NOT NULL REFERENCES reactions(id) ON DELETE CASCADE,
    PRIMARY KEY (claim_id, reaction_id)
);

-- 5.6 Ingredients on sources / experiments
CREATE TABLE source_ingredients (
    source_id     BIGINT NOT NULL REFERENCES sources(id)     ON DELETE CASCADE,
    ingredient_id BIGINT NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
    PRIMARY KEY (source_id, ingredient_id)
);

CREATE TABLE experiment_ingredients (
    experiment_id BIGINT NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    ingredient_id BIGINT NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
    amount_pct    NUMERIC(6,3),
    notes         TEXT,
    PRIMARY KEY (experiment_id, ingredient_id)
);

-- 5.7 Molecule role tagging in a source/experiment context
CREATE TABLE molecule_role_tags (
    id            BIGSERIAL PRIMARY KEY,
    molecule_id   BIGINT NOT NULL REFERENCES molecules(id) ON DELETE CASCADE,
    source_id     BIGINT REFERENCES sources(id)     ON DELETE CASCADE,
    experiment_id BIGINT REFERENCES experiments(id) ON DELETE CASCADE,
    role          molecule_role NOT NULL,
    notes         TEXT,
    CHECK (source_id IS NOT NULL OR experiment_id IS NOT NULL)
);
CREATE INDEX idx_mol_role_molecule    ON molecule_role_tags (molecule_id);
CREATE INDEX idx_mol_role_source      ON molecule_role_tags (source_id);
CREATE INDEX idx_mol_role_experiment  ON molecule_role_tags (experiment_id);
CREATE INDEX idx_mol_role_role        ON molecule_role_tags (role);

-- 5.8 Experts on sources (formal authorship beyond the free-text "authors" string)
CREATE TABLE source_experts (
    source_id BIGINT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    expert_id BIGINT NOT NULL REFERENCES experts(id) ON DELETE CASCADE,
    role      TEXT NOT NULL DEFAULT 'author'
              CHECK (role IN ('author','corresponding','inventor','reviewer','editor')),
    PRIMARY KEY (source_id, expert_id, role)
);
CREATE INDEX idx_source_experts_expert ON source_experts (expert_id);

-- 5.9 Experiment ↔ Molecule (measurement / detection at experiment level)
CREATE TABLE experiment_molecules (
    experiment_id      BIGINT NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    molecule_id        BIGINT NOT NULL REFERENCES molecules(id)   ON DELETE CASCADE,
    detected           BOOLEAN DEFAULT TRUE,
    concentration      NUMERIC,
    concentration_unit TEXT,                       -- 'ppm', 'mg/kg', 'µg/L', 'peak_area_pct'
    notes              TEXT,
    PRIMARY KEY (experiment_id, molecule_id)
);

-- 5.10 Claim ↔ Experiment (a claim grounded in a specific experiment, not just a paper)
CREATE TABLE claim_experiments (
    claim_id      BIGINT NOT NULL REFERENCES claims(id)      ON DELETE CASCADE,
    experiment_id BIGINT NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    PRIMARY KEY (claim_id, experiment_id)
);


-- =============================================================================
-- 6. updated_at TRIGGER (quality-of-life — fixes existing v1 tables too)
-- =============================================================================

CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_sources_updated         BEFORE UPDATE ON sources         FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_molecules_updated       BEFORE UPDATE ON molecules       FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_odours_updated          BEFORE UPDATE ON odours          FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_claims_updated          BEFORE UPDATE ON claims          FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_experts_updated         BEFORE UPDATE ON experts         FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_organizations_updated   BEFORE UPDATE ON organizations   FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_ingredients_updated     BEFORE UPDATE ON ingredients     FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_experiments_updated     BEFORE UPDATE ON experiments     FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- =============================================================================
-- 7. ANALYST-FRIENDLY VIEWS
-- =============================================================================

-- Drop and recreate v1 views that referenced superseded structures.
DROP VIEW IF EXISTS v_claim_evidence;

CREATE VIEW v_claim_evidence AS
SELECT
    c.id          AS claim_id,
    c.claim_text,
    c.stance,
    c.confidence,
    s.id          AS source_id,
    s.name        AS source_name,
    s.source_type,
    s.year        AS source_year,
    m.id          AS molecule_id,
    m.name        AS molecule_name
FROM claims c
LEFT JOIN claim_sources   cs ON cs.claim_id   = c.id
LEFT JOIN sources         s  ON s.id          = cs.source_id
LEFT JOIN claim_molecules cm ON cm.claim_id   = c.id
LEFT JOIN molecules       m  ON m.id          = cm.molecule_id;

-- The unified intelligence record — one row per source.
-- Materializes the example object you described.
CREATE OR REPLACE VIEW v_intelligence_record AS
SELECT
    s.id                                                  AS source_id,
    s.name                                                AS title,
    s.source_type,
    s.year,
    s.species_reference,
    s.evidence_strength,
    s.actionability,
    s.usefulness_tags,
    (SELECT array_agg(pc.name ORDER BY pc.name)
       FROM source_product_contexts spc
       JOIN product_contexts pc ON pc.id = spc.context_id
      WHERE spc.source_id = s.id AND spc.role = 'primary')      AS product_context,
    (SELECT array_agg(pc.name ORDER BY pc.name)
       FROM source_product_contexts spc
       JOIN product_contexts pc ON pc.id = spc.context_id
      WHERE spc.source_id = s.id AND spc.role = 'alternative')  AS alternative_product,
    (SELECT array_agg(t.name ORDER BY t.name)
       FROM source_topics st
       JOIN topics t ON t.id = st.topic_id
      WHERE st.source_id = s.id AND t.root_branch = 'flavor_chemistry') AS chemistry_topics,
    (SELECT array_agg(r.name ORDER BY r.name)
       FROM source_reactions sr
       JOIN reactions r ON r.id = sr.reaction_id
      WHERE sr.source_id = s.id)                                 AS reactions,
    (SELECT array_agg(am.name ORDER BY am.name)
       FROM source_methods sm
       JOIN analytical_methods am ON am.id = sm.method_id
      WHERE sm.source_id = s.id)                                 AS analytical_methods,
    (SELECT array_agg(sa.name ORDER BY sa.name)
       FROM source_sensory_attributes ssa
       JOIN sensory_attributes sa ON sa.id = ssa.attribute_id
      WHERE ssa.source_id = s.id)                                AS sensory_attributes,
    (SELECT array_agg(m.name ORDER BY m.name)
       FROM source_molecules sm
       JOIN molecules m ON m.id = sm.molecule_id
      WHERE sm.source_id = s.id)                                 AS molecules,
    (SELECT array_agg(i.name ORDER BY i.name)
       FROM source_ingredients si
       JOIN ingredients i ON i.id = si.ingredient_id
      WHERE si.source_id = s.id)                                 AS ingredients,
    (SELECT array_agg(format('%s @ %s°C, %s min',
                              p.cooking_method, p.temperature_c, p.time_min))
       FROM processes p WHERE p.source_id = s.id)                AS process_summary,
    (SELECT array_agg(format('protein=%s, fat=%s',
                              mp.protein_source, mp.fat_source))
       FROM matrix_profiles mp WHERE mp.source_id = s.id)        AS matrix_summary
FROM sources s;

-- Reactions and their participants (precursor / intermediate / product)
CREATE OR REPLACE VIEW v_reaction_participants_named AS
SELECT
    r.id                                                AS reaction_id,
    r.name                                              AS reaction_name,
    r.kind                                              AS reaction_kind,
    rp.role                                             AS participant_role,
    COALESCE(m.name, i.name)                            AS participant_name,
    CASE WHEN m.id IS NOT NULL THEN 'molecule' ELSE 'ingredient' END AS participant_type
FROM reactions r
JOIN reaction_participants rp ON rp.reaction_id = r.id
LEFT JOIN molecules   m ON m.id = rp.molecule_id
LEFT JOIN ingredients i ON i.id = rp.ingredient_id;

-- Convenience: precursors only
CREATE OR REPLACE VIEW v_precursors AS
SELECT * FROM v_reaction_participants_named WHERE participant_role = 'precursor';

-- Convenience: rolled-up experiment record
CREATE OR REPLACE VIEW v_experiment_record AS
SELECT
    e.id                                  AS experiment_id,
    e.name                                AS experiment_name,
    s.id                                  AS source_id,
    s.name                                AS source_name,
    (SELECT array_agg(am.name) FROM experiment_methods em
       JOIN analytical_methods am ON am.id = em.method_id WHERE em.experiment_id = e.id) AS methods,
    (SELECT array_agg(sa.name) FROM experiment_sensory_attributes esa
       JOIN sensory_attributes sa ON sa.id = esa.attribute_id WHERE esa.experiment_id = e.id) AS sensory_attributes,
    (SELECT array_agg(m.name)  FROM experiment_molecules em
       JOIN molecules m ON m.id = em.molecule_id WHERE em.experiment_id = e.id) AS molecules,
    (SELECT array_agg(format('%s @ %s°C, %s min', p.cooking_method, p.temperature_c, p.time_min))
       FROM processes p WHERE p.experiment_id = e.id) AS process_summary
FROM experiments e
JOIN sources s ON s.id = e.source_id;


COMMIT;

-- =============================================================================
-- POST-MIGRATION TODOs (run as separate scripts — NOT auto-executed)
--
--   1. Backfill experts.org_type from existing affiliation strings, then
--      populate organizations and link experts.organization_id.
--
--   2. Backfill sources.source_type from heuristics on venue / url
--      (e.g., '%patents.google.com%' -> 'patent').
--
--   3. Migrate the legacy claim_topics rows:
--        a) For each distinct claim_topics.topic, INSERT into topics if missing.
--        b) INSERT INTO claim_topics_v2 SELECT claim_id, topics.id ...
--        c) DROP TABLE claim_topics;
--           ALTER TABLE claim_topics_v2 RENAME TO claim_topics;
--
--   4. Seed the lookup tables (topics / sensory_attributes / product_contexts /
--      analytical_methods / reactions) from the Miro mind map. A separate
--      seed file (gfi_seed_taxonomies.sql) is the natural next step.
-- =============================================================================
