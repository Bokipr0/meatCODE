-- =============================================================================
-- GFI Flavor Intelligence Database — Taxonomy Seed
-- Populates the lookup/dimension tables from the Miro mind map:
--   topics, sensory_attributes, product_contexts, analytical_methods, reactions
--
-- Run AFTER gfi_schema.sql + gfi_schema_v2_migration.sql.
-- Idempotent — uses ON CONFLICT (slug) DO NOTHING, so re-running is safe.
-- =============================================================================

BEGIN;

-- =============================================================================
-- 1. TOPICS (hierarchical taxonomy — Knowledge Hub branches)
-- =============================================================================

-- Level 1 (top of each root branch)
INSERT INTO topics (slug, name, parent_id, root_branch, level) VALUES
    -- flavor_chemistry root branch
    ('matrix_interactions',       'Matrix interactions',       NULL, 'flavor_chemistry', 1),
    ('metallic',                  'Metallic',                  NULL, 'flavor_chemistry', 1),
    ('heme',                      'Heme',                      NULL, 'flavor_chemistry', 1),
    ('modeling',                  'Modeling',                  NULL, 'flavor_chemistry', 1),
    ('process_flavor',            'Process flavor',            NULL, 'flavor_chemistry', 1),
    -- analytics root branch
    ('chromatography',            'Chromatography',            NULL, 'analytics', 1),
    ('sensory_analysis',          'Sensory analysis',          NULL, 'analytics', 1),
    ('omics',                     'Omics',                     NULL, 'analytics', 1),
    -- meat_science root branch
    ('meat_flavor',               'Meat flavor',               NULL, 'meat_science', 1),
    ('meat_aroma',                'Meat aroma',                NULL, 'meat_science', 1),
    ('culinary_aspects',          'Culinary aspects',          NULL, 'meat_science', 1),
    ('processing',                'Processing',                NULL, 'meat_science', 1),
    -- meat_analogs root branch
    ('meat_analogs',              'Meat analogs',              NULL, 'meat_analogs', 1),
    -- flavor_ingredients root branch
    ('flavor_house',              'Flavor house',              NULL, 'flavor_ingredients', 1),
    ('yeast_extract_topic',       'Yeast extract',             NULL, 'flavor_ingredients', 1),
    ('enzymatic_processing',      'Enzymatic processing',      NULL, 'flavor_ingredients', 1),
    ('fermentation_topic',        'Fermentation',              NULL, 'flavor_ingredients', 1)
ON CONFLICT (slug) DO NOTHING;

-- Level 2 (children of level-1)
INSERT INTO topics (slug, name, parent_id, root_branch, level) VALUES
    -- modeling children
    ('pinn',                      'PINN (Physics-Informed NN)', (SELECT id FROM topics WHERE slug='modeling'), 'flavor_chemistry', 2),
    ('ai_ml',                     'AI / ML',                    (SELECT id FROM topics WHERE slug='modeling'), 'flavor_chemistry', 2),
    -- process_flavor children
    ('maillard',                  'Maillard',                   (SELECT id FROM topics WHERE slug='process_flavor'), 'flavor_chemistry', 2),
    ('maillard_lipid',            'Maillard-Lipid interaction', (SELECT id FROM topics WHERE slug='process_flavor'), 'flavor_chemistry', 2),
    ('oil_chemistry',             'Oil chemistry',              (SELECT id FROM topics WHERE slug='process_flavor'), 'flavor_chemistry', 2),
    -- chromatography children
    ('gcms_topic',                'GCMS',                       (SELECT id FROM topics WHERE slug='chromatography'), 'analytics', 2),
    ('lcms_topic',                'LCMS',                       (SELECT id FROM topics WHERE slug='chromatography'), 'analytics', 2),
    ('hplc_topic',                'HPLC',                       (SELECT id FROM topics WHERE slug='chromatography'), 'analytics', 2),
    -- sensory_analysis children
    ('tasting_topic',             'Tasting',                    (SELECT id FROM topics WHERE slug='sensory_analysis'), 'analytics', 2),
    ('sniffing_topic',            'Sniffing',                   (SELECT id FROM topics WHERE slug='sensory_analysis'), 'analytics', 2),
    ('consumer_panel_topic',      'Consumer panel',             (SELECT id FROM topics WHERE slug='sensory_analysis'), 'analytics', 2),
    -- omics children
    ('peptidomics_topic',         'Peptidomics',                (SELECT id FROM topics WHERE slug='omics'), 'analytics', 2),
    ('lipidomics_topic',          'Lipidomics',                 (SELECT id FROM topics WHERE slug='omics'), 'analytics', 2),
    ('metabolomics_topic',        'Metabolomics',               (SELECT id FROM topics WHERE slug='omics'), 'analytics', 2),
    -- culinary_aspects children
    ('cooking',                   'Cooking',                    (SELECT id FROM topics WHERE slug='culinary_aspects'), 'meat_science', 2),
    ('grill',                     'Grill',                      (SELECT id FROM topics WHERE slug='culinary_aspects'), 'meat_science', 2),
    -- processing children
    ('ageing',                    'Ageing',                     (SELECT id FROM topics WHERE slug='processing'), 'meat_science', 2),
    ('fermentation_meat',         'Fermentation (meat)',        (SELECT id FROM topics WHERE slug='processing'), 'meat_science', 2),
    ('thermal',                   'Thermal',                    (SELECT id FROM topics WHERE slug='processing'), 'meat_science', 2)
ON CONFLICT (slug) DO NOTHING;

-- Level 3 (grandchildren — Maillard children + Oil chemistry children)
INSERT INTO topics (slug, name, parent_id, root_branch, level) VALUES
    -- Maillard sub-topics
    ('peptide',                   'Peptide',                    (SELECT id FROM topics WHERE slug='maillard'), 'flavor_chemistry', 3),
    ('amino_acids',               'Amino acids',                (SELECT id FROM topics WHERE slug='maillard'), 'flavor_chemistry', 3),
    ('primary_sugars',            'Primary sugars',             (SELECT id FROM topics WHERE slug='maillard'), 'flavor_chemistry', 3),
    ('vitamins',                  'Vitamins',                   (SELECT id FROM topics WHERE slug='maillard'), 'flavor_chemistry', 3),
    ('sulfur_chemistry',          'Sulfur chemistry',           (SELECT id FROM topics WHERE slug='maillard'), 'flavor_chemistry', 3),
    -- Oil chemistry sub-topics
    ('lipid_oxidation_topic',     'Lipid oxidation',            (SELECT id FROM topics WHERE slug='oil_chemistry'), 'flavor_chemistry', 3)
ON CONFLICT (slug) DO NOTHING;


-- =============================================================================
-- 2. SENSORY ATTRIBUTES (with off-notes hierarchy)
-- =============================================================================

-- Main targets — flat list, no parent
INSERT INTO sensory_attributes (slug, name, parent_id, is_off_note) VALUES
    ('beefy',         'Beefy',         NULL, FALSE),
    ('brothy',        'Brothy',        NULL, FALSE),
    ('roasted',       'Roasted',       NULL, FALSE),
    ('grilled',       'Grilled',       NULL, FALSE),
    ('fatty',         'Fatty',         NULL, FALSE),
    ('bloody_serumy', 'Bloody / serumy', NULL, FALSE),
    ('metallic_sa',   'Metallic',      NULL, FALSE),
    ('liver_like',    'Liver-like',    NULL, FALSE),
    ('umami',         'Umami',         NULL, FALSE),
    ('kokumi',        'Kokumi',        NULL, FALSE),
    ('juicy',         'Juicy',         NULL, FALSE),
    ('smoky_charred', 'Smoky / charred', NULL, FALSE),
    ('brown_cooked',  'Brown / cooked', NULL, FALSE)
ON CONFLICT (slug) DO NOTHING;

-- Off-notes parent (the umbrella category)
INSERT INTO sensory_attributes (slug, name, parent_id, is_off_note) VALUES
    ('off_notes', 'Off-notes', NULL, TRUE)
ON CONFLICT (slug) DO NOTHING;

-- Off-notes children (point at off_notes parent, all flagged is_off_note=TRUE)
INSERT INTO sensory_attributes (slug, name, parent_id, is_off_note) VALUES
    ('beany',                 'Beany',                 (SELECT id FROM sensory_attributes WHERE slug='off_notes'), TRUE),
    ('green_grassy',          'Green / grassy',        (SELECT id FROM sensory_attributes WHERE slug='off_notes'), TRUE),
    ('bitter',                'Bitter',                (SELECT id FROM sensory_attributes WHERE slug='off_notes'), TRUE),
    ('astringent',            'Astringent',            (SELECT id FROM sensory_attributes WHERE slug='off_notes'), TRUE),
    ('musty_earthy',          'Musty / earthy',        (SELECT id FROM sensory_attributes WHERE slug='off_notes'), TRUE),
    ('rancid_oxidized',       'Rancid / oxidized',     (SELECT id FROM sensory_attributes WHERE slug='off_notes'), TRUE),
    ('sulfurous_cabbage_eggy','Sulfurous / cabbage / eggy', (SELECT id FROM sensory_attributes WHERE slug='off_notes'), TRUE)
ON CONFLICT (slug) DO NOTHING;


-- =============================================================================
-- 3. PRODUCT CONTEXTS
-- =============================================================================

INSERT INTO product_contexts (slug, name, category) VALUES
    -- animal-based products
    ('ground_beef_burger',           'Ground beef / burger',                 'animal'),
    ('steak_whole_cut',              'Steak / whole cut',                    'animal'),
    ('sausage_emulsion',             'Sausage / emulsion',                   'animal'),
    -- plant-based analogues
    ('chicken_analogue',             'Chicken analogue',                     'plant_analogue'),
    ('pork_analogue',                'Pork analogue',                        'plant_analogue'),
    -- hybrid / cultivated
    ('hybrid_blended_meat',          'Hybrid / blended meat',                'hybrid'),
    ('cultivated_fermentation',      'Cultivated / fermentation-derived',    'hybrid'),
    -- ingredient-level products
    ('fat_systems',                  'Fat systems',                          'ingredient'),
    ('broths_stocks_extracts',       'Broths / stocks / extracts',           'ingredient'),
    ('dry_seasonings_process_flavors','Dry seasonings / process flavors',    'ingredient')
ON CONFLICT (slug) DO NOTHING;


-- =============================================================================
-- 4. ANALYTICAL METHODS
-- =============================================================================

INSERT INTO analytical_methods (slug, name, category) VALUES
    -- chromatography
    ('gcms',              'GC-MS',                       'chromatography'),
    ('lcms',              'LC-MS',                       'chromatography'),
    ('hplc',              'HPLC',                        'chromatography'),
    ('hs_spme_gc_ms',     'HS-SPME-GC-MS',               'chromatography'),
    ('gc_o',              'GC-Olfactometry',             'chromatography'),
    -- sensory
    ('tasting_panel',         'Tasting panel',                'sensory'),
    ('sniffing_panel',        'Sniffing panel',               'sensory'),
    ('consumer_panel',        'Consumer panel',               'sensory'),
    ('trained_sensory_panel', 'Trained sensory panel',        'sensory'),
    ('descriptive_analysis',  'Descriptive analysis',         'sensory'),
    -- omics
    ('peptidomics',       'Peptidomics',                 'omics'),
    ('lipidomics',        'Lipidomics',                  'omics'),
    ('metabolomics',      'Metabolomics',                'omics')
ON CONFLICT (slug) DO NOTHING;


-- =============================================================================
-- 5. REACTIONS / PATHWAYS
-- =============================================================================

-- Top-level pathways (no parent)
INSERT INTO reactions (slug, name, kind, parent_id, description) VALUES
    ('maillard_rxn',             'Maillard reaction',             'maillard',             NULL,
        'Non-enzymatic browning between reducing sugars and amino acids; primary driver of cooked / roasted aromas.'),
    ('lipid_oxidation_rxn',      'Lipid oxidation',               'lipid_oxidation',      NULL,
        'Oxidative degradation of unsaturated fatty acids producing aldehydes and other volatiles; key in fatty / rancid notes.'),
    ('caramelization_rxn',       'Caramelization',                'caramelization',       NULL,
        'Thermal degradation of sugars in the absence of amino acids; sweet / caramel / nutty notes.'),
    ('thermal_degradation_rxn',  'Thermal degradation',           'thermal_degradation',  NULL,
        'Generic high-heat breakdown of proteins, lipids, and other matrix components.'),
    ('enzymatic_hydrolysis_rxn', 'Enzymatic hydrolysis',          'enzymatic_hydrolysis', NULL,
        'Protease/lipase-driven cleavage of macromolecules into flavor-active peptides, amino acids, fatty acids.'),
    ('fermentation_rxn',         'Fermentation',                  'fermentation',         NULL,
        'Microbial metabolism producing flavor-active acids, alcohols, esters, sulfur compounds.')
ON CONFLICT (slug) DO NOTHING;

-- Child reactions (sub-pathways of Maillard)
INSERT INTO reactions (slug, name, kind, parent_id, description) VALUES
    ('strecker_degradation_rxn', 'Strecker degradation',          'strecker_degradation',
        (SELECT id FROM reactions WHERE slug='maillard_rxn'),
        'Reaction of amino acids with α-dicarbonyls from Maillard, producing Strecker aldehydes (e.g., methional, phenylacetaldehyde).'),
    ('maillard_lipid_rxn',       'Maillard-Lipid interaction',    'other',
        (SELECT id FROM reactions WHERE slug='maillard_rxn'),
        'Cross-talk between Maillard intermediates and lipid oxidation products; important for meat-like aroma generation.')
ON CONFLICT (slug) DO NOTHING;


COMMIT;

-- =============================================================================
-- Verification queries — run these after the seed completes
-- =============================================================================

-- SELECT root_branch, COUNT(*) AS n FROM topics GROUP BY root_branch ORDER BY root_branch;
-- SELECT is_off_note, COUNT(*) AS n FROM sensory_attributes GROUP BY is_off_note;
-- SELECT category, COUNT(*) AS n FROM product_contexts GROUP BY category;
-- SELECT category, COUNT(*) AS n FROM analytical_methods GROUP BY category;
-- SELECT kind, COUNT(*) AS n FROM reactions GROUP BY kind ORDER BY kind;
