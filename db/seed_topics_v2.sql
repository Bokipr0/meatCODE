-- =============================================================================
-- GFI Topics — v2 expansion
-- Adds ~66 new topics across all 5 root branches:
--   flavor_chemistry, analytics, meat_science, meat_analogs, flavor_ingredients
--
-- Idempotent: ON CONFLICT (slug) DO NOTHING means safe to re-run.
-- Run AFTER gfi_seed_taxonomies.sql (which created the level-1/2/3 base set).
-- =============================================================================

BEGIN;

-- =============================================================================
-- 1. FLAVOR_CHEMISTRY expansions
-- =============================================================================

-- 1a. Heme sub-topics (under existing 'heme')
INSERT INTO topics (slug, name, parent_id, root_branch, level) VALUES
    ('myoglobin',     'Myoglobin',     (SELECT id FROM topics WHERE slug='heme'), 'flavor_chemistry', 2),
    ('hemoglobin',    'Hemoglobin',    (SELECT id FROM topics WHERE slug='heme'), 'flavor_chemistry', 2),
    ('leghemoglobin', 'Leghemoglobin', (SELECT id FROM topics WHERE slug='heme'), 'flavor_chemistry', 2)
ON CONFLICT (slug) DO NOTHING;

-- 1b. Process_flavor sub-topics (alongside maillard, maillard_lipid, oil_chemistry)
INSERT INTO topics (slug, name, parent_id, root_branch, level) VALUES
    ('caramelization_topic', 'Caramelization',
        (SELECT id FROM topics WHERE slug='process_flavor'), 'flavor_chemistry', 2)
ON CONFLICT (slug) DO NOTHING;

-- 1c. Maillard sub-topics (level 3, expand existing branch)
INSERT INTO topics (slug, name, parent_id, root_branch, level) VALUES
    ('strecker_degradation_topic', 'Strecker degradation',  (SELECT id FROM topics WHERE slug='maillard'), 'flavor_chemistry', 3),
    ('pyrazine_chemistry',         'Pyrazine chemistry',    (SELECT id FROM topics WHERE slug='maillard'), 'flavor_chemistry', 3),
    ('furan_chemistry',            'Furan chemistry',       (SELECT id FROM topics WHERE slug='maillard'), 'flavor_chemistry', 3),
    ('amadori_rearrangement',      'Amadori rearrangement', (SELECT id FROM topics WHERE slug='maillard'), 'flavor_chemistry', 3),
    ('heyns_rearrangement',        'Heyns rearrangement',   (SELECT id FROM topics WHERE slug='maillard'), 'flavor_chemistry', 3)
ON CONFLICT (slug) DO NOTHING;

-- 1d. Sulfur chemistry sub-topics (level 4, under existing 'sulfur_chemistry')
INSERT INTO topics (slug, name, parent_id, root_branch, level) VALUES
    ('thiols',       'Thiols',       (SELECT id FROM topics WHERE slug='sulfur_chemistry'), 'flavor_chemistry', 4),
    ('polysulfides', 'Polysulfides', (SELECT id FROM topics WHERE slug='sulfur_chemistry'), 'flavor_chemistry', 4),
    ('thiophenes',   'Thiophenes',   (SELECT id FROM topics WHERE slug='sulfur_chemistry'), 'flavor_chemistry', 4),
    ('disulfides',   'Disulfides',   (SELECT id FROM topics WHERE slug='sulfur_chemistry'), 'flavor_chemistry', 4)
ON CONFLICT (slug) DO NOTHING;

-- 1e. Oil chemistry sub-topics (level 3, alongside lipid_oxidation_topic)
INSERT INTO topics (slug, name, parent_id, root_branch, level) VALUES
    ('lipoxygenase_pathway', 'Lipoxygenase pathway (LOX)', (SELECT id FROM topics WHERE slug='oil_chemistry'), 'flavor_chemistry', 3),
    ('beta_oxidation',       'β-oxidation',                (SELECT id FROM topics WHERE slug='oil_chemistry'), 'flavor_chemistry', 3)
ON CONFLICT (slug) DO NOTHING;


-- =============================================================================
-- 2. ANALYTICS expansions
-- =============================================================================

-- 2a. Chromatography sub-topics (alongside gcms_topic / lcms_topic / hplc_topic)
INSERT INTO topics (slug, name, parent_id, root_branch, level) VALUES
    ('gc_olfactometry', 'GC-Olfactometry (GC-O)',
        (SELECT id FROM topics WHERE slug='chromatography'), 'analytics', 2),
    ('hs_spme_topic',   'HS-SPME',
        (SELECT id FROM topics WHERE slug='chromatography'), 'analytics', 2),
    ('safe_topic',      'SAFE (Solvent-Assisted Flavor Evaporation)',
        (SELECT id FROM topics WHERE slug='chromatography'), 'analytics', 2)
ON CONFLICT (slug) DO NOTHING;

-- 2b. Sensory analysis sub-topics
INSERT INTO topics (slug, name, parent_id, root_branch, level) VALUES
    ('aeda',              'Aroma Extract Dilution Analysis (AEDA)',
        (SELECT id FROM topics WHERE slug='sensory_analysis'), 'analytics', 2),
    ('electronic_nose',   'Electronic nose',
        (SELECT id FROM topics WHERE slug='sensory_analysis'), 'analytics', 2),
    ('electronic_tongue', 'Electronic tongue',
        (SELECT id FROM topics WHERE slug='sensory_analysis'), 'analytics', 2),
    ('qda',               'QDA (Quantitative Descriptive Analysis)',
        (SELECT id FROM topics WHERE slug='sensory_analysis'), 'analytics', 2),
    ('time_intensity',    'Time-intensity analysis',
        (SELECT id FROM topics WHERE slug='sensory_analysis'), 'analytics', 2),
    ('threshold_testing', 'Threshold testing / odor activity values',
        (SELECT id FROM topics WHERE slug='sensory_analysis'), 'analytics', 2)
ON CONFLICT (slug) DO NOTHING;

-- 2c. Spectroscopy — NEW level-1 sub-branch under analytics
INSERT INTO topics (slug, name, parent_id, root_branch, level) VALUES
    ('spectroscopy', 'Spectroscopy', NULL, 'analytics', 1)
ON CONFLICT (slug) DO NOTHING;

INSERT INTO topics (slug, name, parent_id, root_branch, level) VALUES
    ('nmr',               'NMR spectroscopy',  (SELECT id FROM topics WHERE slug='spectroscopy'), 'analytics', 2),
    ('ftir',              'FTIR',              (SELECT id FROM topics WHERE slug='spectroscopy'), 'analytics', 2),
    ('mass_spectrometry', 'Mass spectrometry', (SELECT id FROM topics WHERE slug='spectroscopy'), 'analytics', 2)
ON CONFLICT (slug) DO NOTHING;

-- 2d. Omics sub-topics (alongside peptidomics/lipidomics/metabolomics)
INSERT INTO topics (slug, name, parent_id, root_branch, level) VALUES
    ('volatilomics',     'Volatilomics',    (SELECT id FROM topics WHERE slug='omics'), 'analytics', 2),
    ('proteomics_topic', 'Proteomics',      (SELECT id FROM topics WHERE slug='omics'), 'analytics', 2),
    ('genomics',         'Genomics',        (SELECT id FROM topics WHERE slug='omics'), 'analytics', 2),
    ('transcriptomics',  'Transcriptomics', (SELECT id FROM topics WHERE slug='omics'), 'analytics', 2)
ON CONFLICT (slug) DO NOTHING;


-- =============================================================================
-- 3. MEAT_SCIENCE expansions
-- =============================================================================

-- 3a. Meat flavor sub-topics
INSERT INTO topics (slug, name, parent_id, root_branch, level) VALUES
    ('myoglobin_meat', 'Myoglobin (meat)',              (SELECT id FROM topics WHERE slug='meat_flavor'), 'meat_science', 2),
    ('marbling',       'Marbling / intramuscular fat',  (SELECT id FROM topics WHERE slug='meat_flavor'), 'meat_science', 2)
ON CONFLICT (slug) DO NOTHING;

-- 3b. Connective tissue — NEW level-1 branch under meat_science
INSERT INTO topics (slug, name, parent_id, root_branch, level) VALUES
    ('connective_tissue', 'Connective tissue chemistry', NULL, 'meat_science', 1)
ON CONFLICT (slug) DO NOTHING;

INSERT INTO topics (slug, name, parent_id, root_branch, level) VALUES
    ('collagen', 'Collagen', (SELECT id FROM topics WHERE slug='connective_tissue'), 'meat_science', 2),
    ('elastin',  'Elastin',  (SELECT id FROM topics WHERE slug='connective_tissue'), 'meat_science', 2)
ON CONFLICT (slug) DO NOTHING;

-- 3c. Processing sub-topics (alongside ageing/fermentation_meat/thermal)
INSERT INTO topics (slug, name, parent_id, root_branch, level) VALUES
    ('curing',     'Curing',                 (SELECT id FROM topics WHERE slug='processing'), 'meat_science', 2),
    ('smoking',    'Smoking',                (SELECT id FROM topics WHERE slug='processing'), 'meat_science', 2),
    ('brining',    'Brining / salting',      (SELECT id FROM topics WHERE slug='processing'), 'meat_science', 2),
    ('pre_rigor',  'Pre-rigor biochemistry', (SELECT id FROM topics WHERE slug='processing'), 'meat_science', 2),
    ('post_rigor', 'Post-rigor biochemistry',(SELECT id FROM topics WHERE slug='processing'), 'meat_science', 2)
ON CONFLICT (slug) DO NOTHING;


-- =============================================================================
-- 4. MEAT_ANALOGS — fleshing out the previously empty branch
-- =============================================================================

INSERT INTO topics (slug, name, parent_id, root_branch, level) VALUES
    ('plant_based_proteins',    'Plant-based proteins',                     (SELECT id FROM topics WHERE slug='meat_analogs'), 'meat_analogs', 2),
    ('cultivated_meat',         'Cultivated / cell-based meat',             (SELECT id FROM topics WHERE slug='meat_analogs'), 'meat_analogs', 2),
    ('precision_fermentation',  'Precision fermentation',                   (SELECT id FROM topics WHERE slug='meat_analogs'), 'meat_analogs', 2),
    ('mycoprotein_analog',      'Mycoprotein',                              (SELECT id FROM topics WHERE slug='meat_analogs'), 'meat_analogs', 2),
    ('hybrid_products',         'Hybrid products (animal + plant)',         (SELECT id FROM topics WHERE slug='meat_analogs'), 'meat_analogs', 2),
    ('printed_meat',            '3D-printed meat',                          (SELECT id FROM topics WHERE slug='meat_analogs'), 'meat_analogs', 2),
    ('hmma',                    'HMMA (high-moisture meat analogs)',        (SELECT id FROM topics WHERE slug='meat_analogs'), 'meat_analogs', 2),
    ('lmma',                    'LMMA (low-moisture meat analogs / TVP)',   (SELECT id FROM topics WHERE slug='meat_analogs'), 'meat_analogs', 2),
    ('off_note_masking',        'Off-note masking',                         (SELECT id FROM topics WHERE slug='meat_analogs'), 'meat_analogs', 2),
    ('beany_note_reduction',    'Beany note reduction',                     (SELECT id FROM topics WHERE slug='meat_analogs'), 'meat_analogs', 2),
    ('heme_analogues',          'Heme analogues (synthetic biology)',       (SELECT id FROM topics WHERE slug='meat_analogs'), 'meat_analogs', 2)
ON CONFLICT (slug) DO NOTHING;


-- =============================================================================
-- 5. FLAVOR_INGREDIENTS expansions
-- =============================================================================

-- Level-1 peers (alongside flavor_house, yeast_extract_topic, enzymatic_processing, fermentation_topic)
INSERT INTO topics (slug, name, parent_id, root_branch, level) VALUES
    ('hvp_topic',                  'Hydrolyzed Vegetable Protein (HVP)',     NULL, 'flavor_ingredients', 1),
    ('reaction_flavors_topic',     'Reaction flavors / process flavors',     NULL, 'flavor_ingredients', 1),
    ('liquid_smoke',               'Liquid smoke',                            NULL, 'flavor_ingredients', 1),
    ('encapsulated_flavors',       'Encapsulated flavors',                    NULL, 'flavor_ingredients', 1),
    ('maillard_intermediates_ing', 'Maillard intermediates as ingredients',   NULL, 'flavor_ingredients', 1),
    ('modulators',                 'Flavor modulators',                       NULL, 'flavor_ingredients', 1),
    ('plant_fat_alternatives',     'Plant-fat alternatives',                  NULL, 'flavor_ingredients', 1)
ON CONFLICT (slug) DO NOTHING;

-- Modulator children (level 2)
INSERT INTO topics (slug, name, parent_id, root_branch, level) VALUES
    ('salt_enhancers',   'Salt enhancers',   (SELECT id FROM topics WHERE slug='modulators'), 'flavor_ingredients', 2),
    ('umami_enhancers',  'Umami enhancers',  (SELECT id FROM topics WHERE slug='modulators'), 'flavor_ingredients', 2),
    ('kokumi_enhancers', 'Kokumi enhancers', (SELECT id FROM topics WHERE slug='modulators'), 'flavor_ingredients', 2),
    ('bitter_blockers',  'Bitter blockers',  (SELECT id FROM topics WHERE slug='modulators'), 'flavor_ingredients', 2)
ON CONFLICT (slug) DO NOTHING;

-- Plant-fat-alternatives children (level 2)
INSERT INTO topics (slug, name, parent_id, root_branch, level) VALUES
    ('oleogels_topic',         'Oleogels',         (SELECT id FROM topics WHERE slug='plant_fat_alternatives'), 'flavor_ingredients', 2),
    ('structured_fats_topic',  'Structured fats',  (SELECT id FROM topics WHERE slug='plant_fat_alternatives'), 'flavor_ingredients', 2)
ON CONFLICT (slug) DO NOTHING;


COMMIT;

-- =============================================================================
-- Verification — paste into TablePlus to confirm counts
-- =============================================================================
--
-- SELECT root_branch, COUNT(*) AS topics_count
-- FROM topics
-- GROUP BY root_branch
-- ORDER BY root_branch;
--
-- Expected after this seed runs on top of v1 seed:
--   analytics            ~24 rows  (was 13, +11)
--   flavor_chemistry     ~28 rows  (was 14, +14)
--   flavor_ingredients   ~17 rows  (was 4,  +13)
--   meat_analogs         ~12 rows  (was 1,  +11)
--   meat_science         ~17 rows  (was 9,  +8)
--   ----------------------------------------
--   TOTAL                ~98 rows  (was 41, +57 new)
-- =============================================================================
