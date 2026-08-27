-- =============================================================================
-- 0011 — Molecule target-property columns + `molecule_properties` observation
--        table (per-value provenance).
-- Last updated: 2026-08-27 · Data Engineer agent · initial version
--
-- WHY
--   Lior's target property list (structure · molecular weight · functional groups ·
--   charge · pKa · pI · polarity · hydrophobicity · redox potential · reactive
--   groups · sequence/conformation · melting/boiling point · vapour pressure ·
--   solubility · partition coefficients · odour descriptors · odour threshold ·
--   taste · OAV · colour, each with source · method · conditions · uncertainty ·
--   confidence) had no home in the schema. Already covered and NOT duplicated
--   here: structure (`smiles`/`inchikey`/`molecular_formula`), `melting_point`,
--   `water_solubility`, `taste`, and odour descriptors (`molecule_odours`, 2,263
--   links over 785 molecules).
--
-- WHAT
--   (a) molecules += 16 nullable columns holding the CANONICAL value of each
--       target property (fast read path for the app/KG).
--   (b) NEW molecule_properties — one row per property PER SOURCE, carrying the
--       provenance quintet the flat columns cannot hold: source · measurement
--       method · conditions · uncertainty · confidence, plus `derivation`
--       (reported | author_derived | graph_estimated | system_derived) and the
--       raw expression/unit as stated. This implements the "Numeric observations"
--       contract in docs/full_text_parallel_evidence_extraction_strategy.md:
--       normalize only unambiguous quantities, always keep the raw value, and
--       never let a computed value masquerade as a measured one.
--
--   Flat column = "what we currently believe"; molecule_properties = "why, and
--   who said so". A flat value with no molecule_properties row is unsourced.
--
-- DATA SAFETY
--   Purely additive: no DROP, no destructive UPDATE, all new columns nullable
--   with no default (no table rewrite, no NOT NULL failure on 799 existing rows).
--
-- STRUCTURAL SAFETY
--   Adding columns cannot break a dependent view. The 6 views that read
--   `molecules` (v_mvl_gaps, v_mvl_x_molecules_by_cas / _by_name / _fuzzy,
--   v_meaty_molecules_ranked, v_precursors) all use explicit column lists and
--   are unaffected. No FK or generated column touches the new names.
--
-- REVERSIBLE
--   ALTER TABLE molecules DROP COLUMN molecular_weight, ... ;
--   DROP TABLE molecule_properties;
--
-- Applied to Neon: 2026-08-27 — production branch.
-- =============================================================================
BEGIN;

-- ---------------------------------------------------------------------------
-- (a) Canonical value columns
-- ---------------------------------------------------------------------------
ALTER TABLE molecules
    ADD COLUMN IF NOT EXISTS molecular_weight      numeric,   -- g/mol, from structure
    ADD COLUMN IF NOT EXISTS formal_charge         integer,   -- net formal charge from structure
    ADD COLUMN IF NOT EXISTS functional_groups     text[],    -- SMARTS-matched group names
    ADD COLUMN IF NOT EXISTS reactive_groups       text[],    -- flavour-chemistry reactive handles
    ADD COLUMN IF NOT EXISTS pka                   numeric,   -- strongest acidic pKa
    ADD COLUMN IF NOT EXISTS isoelectric_point     numeric,   -- pI (amino acids / peptides only)
    ADD COLUMN IF NOT EXISTS tpsa                  numeric,   -- polarity proxy: TPSA, Angstrom^2
    ADD COLUMN IF NOT EXISTS logp                  numeric,   -- hydrophobicity / octanol-water logP
    ADD COLUMN IF NOT EXISTS redox_potential_v     numeric,   -- standard redox potential, volts
    ADD COLUMN IF NOT EXISTS sequence_conformation text,      -- peptides/proteins only
    ADD COLUMN IF NOT EXISTS boiling_point         text,      -- raw as reported (units vary)
    ADD COLUMN IF NOT EXISTS vapor_pressure        text,      -- raw as reported (units vary)
    ADD COLUMN IF NOT EXISTS odor_threshold_raw    text,      -- exactly as stated in the source
    ADD COLUMN IF NOT EXISTS odor_threshold_ppb    numeric,   -- normalized ONLY when unambiguous
    ADD COLUMN IF NOT EXISTS oav                   numeric,   -- odour activity value (needs matrix conc.)
    ADD COLUMN IF NOT EXISTS color                 text;

COMMENT ON COLUMN molecules.tpsa IS
    'Topological polar surface area (A^2) — the computable stand-in for "polarity". Exact from structure.';
COMMENT ON COLUMN molecules.logp IS
    'Crippen MolLogP — an ESTIMATE from structure, not a measured partition coefficient. See molecule_properties.derivation=system_derived.';
COMMENT ON COLUMN molecules.odor_threshold_ppb IS
    'Normalized only where the source stated a single unambiguous number. Ranges ("4.6-9") and matrix-qualified values ("200, refined vegetable oil") stay in odor_threshold_raw with value_num NULL.';
COMMENT ON COLUMN molecules.oav IS
    'Odour activity value = concentration in matrix / odour threshold. Left NULL: the concentration side requires the experiments/processes tables, which are empty. Do not fabricate.';

-- ---------------------------------------------------------------------------
-- (b) Per-observation provenance
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS molecule_properties (
    id              bigserial PRIMARY KEY,
    molecule_id     bigint NOT NULL REFERENCES molecules(id) ON DELETE CASCADE,
    property        text   NOT NULL,          -- 'molecular_weight' | 'logp' | 'odor_threshold' | ...
    value_raw       text,                     -- the expression exactly as stated
    value_num       numeric,                  -- normalized value, ONLY when deterministic
    unit_raw        text,
    unit_norm       text,
    basis           text,                     -- denominator/basis where relevant
    uncertainty     text,                     -- as reported (+/-, CI, range)
    replicate_count integer,
    derivation      text NOT NULL
        CHECK (derivation IN ('reported','author_derived','graph_estimated','system_derived')),
    method          text,                     -- measurement or computation method
    conditions      jsonb,                    -- {"temperature_c":..,"ph":..,"matrix":".."} as stated
    source_id       bigint REFERENCES sources(id) ON DELETE SET NULL,
    source_ref      text,                     -- when not a `sources` row, e.g. 'mvl:entry_no=1'
    source_location text,                     -- table/page/span
    confidence      numeric CHECK (confidence >= 0 AND confidence <= 1),
    flags           text[],                   -- ambiguity flags per the extraction strategy
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_molprop_molecule  ON molecule_properties (molecule_id);
CREATE INDEX IF NOT EXISTS ix_molprop_property  ON molecule_properties (property);
CREATE UNIQUE INDEX IF NOT EXISTS ux_molprop_mol_prop_src
    ON molecule_properties (molecule_id, property, COALESCE(source_ref, ''));

COMMENT ON TABLE molecule_properties IS
    'One row per property per source. Implements the Numeric-observations contract in docs/full_text_parallel_evidence_extraction_strategy.md: raw value always preserved, normalization only when unambiguous, derivation distinguishes reported vs computed.';

COMMIT;
