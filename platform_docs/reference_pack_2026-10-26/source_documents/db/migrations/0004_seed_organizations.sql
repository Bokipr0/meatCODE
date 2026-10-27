-- =============================================================================
-- 0004 — Seed `organizations` with the meaty-flavor ecosystem (companies + NGOs).
-- Curated, verifiable core fields only (name · org_type · country · website · short
-- factual description). No fabricated founding years / product claims (trust-first).
-- Idempotent: unique index on lower(name) + ON CONFLICT DO NOTHING → safe to re-run.
-- org_type enum: company | academy | ngo_gov | culinary.
-- Applied to Neon: 2026-07-07. Review/extend freely — this is a starter set.
-- =============================================================================
BEGIN;

CREATE UNIQUE INDEX IF NOT EXISTS ux_organizations_lower_name ON organizations (lower(name));

INSERT INTO organizations (name, org_type, country, website, description) VALUES
-- ── Flavor & fragrance houses ──
('Givaudan',              'company', 'Switzerland',  'givaudan.com',        'Global flavor & fragrance house; meaty/savory reaction-flavor systems.'),
('dsm-firmenich',         'company', 'Switzerland',  'dsm-firmenich.com',   'Flavor, fragrance & nutrition group (2023 DSM + Firmenich merger).'),
('International Flavors & Fragrances', 'company', 'United States', 'iff.com', 'Flavor & specialty ingredients major; savory and plant-protein flavor.'),
('Symrise',               'company', 'Germany',      'symrise.com',         'Flavor & fragrance and food-ingredient company; savory systems.'),
('Kerry Group',           'company', 'Ireland',      'kerry.com',           'Taste & nutrition company; savory flavors, yeast extracts, hydrolysates.'),
('Takasago',              'company', 'Japan',        'takasago.com',        'Flavor & fragrance house with savory/reaction-flavor expertise.'),
('Mane',                  'company', 'France',       'mane.com',            'Flavor & fragrance house; taste and reaction-flavor technologies.'),
('Robertet',              'company', 'France',       'robertet.com',        'Flavor & fragrance house focused on natural ingredients.'),
('Sensient Technologies', 'company', 'United States', 'sensient.com',       'Flavors and colors manufacturer; savory taste systems.'),
('ADM',                   'company', 'United States', 'adm.com',            'Ingredient & nutrition major; plant proteins, flavors, fermentation.'),
('Ingredion',             'company', 'United States', 'ingredion.com',      'Ingredient solutions company; plant-protein and texturant systems.'),
-- ── Alternative-meat companies ──
('Beyond Meat',           'company', 'United States', 'beyondmeat.com',     'Plant-based meat company (burgers, sausages, ground).'),
('Impossible Foods',      'company', 'United States', 'impossiblefoods.com','Plant-based meat company; heme (leghemoglobin) flavor approach.'),
('Redefine Meat',         'company', 'Israel',       'redefinemeat.com',    'Plant-based whole-cut meat via industrial 3D printing.'),
('Aleph Farms',           'company', 'Israel',       'aleph-farms.com',     'Cultivated meat company (cultivated beef).'),
('Believer Meats',        'company', 'Israel',       'believermeats.com',   'Cultivated meat company (formerly Future Meat Technologies).'),
('Chunk Foods',           'company', 'Israel',       'chunkfoods.com',      'Plant-based whole-cut meat via fermentation.'),
('Planted',               'company', 'Switzerland',  'planted.com',         'Plant-based whole-cut meat via extrusion & fermentation.'),
('Mosa Meat',             'company', 'Netherlands',  'mosameat.com',        'Cultivated beef company; produced the first cultured hamburger.'),
('UPSIDE Foods',          'company', 'United States', 'upsidefoods.com',    'Cultivated meat company (cultivated chicken).'),
('Eat Just',              'company', 'United States', 'ju.st',              'Plant-based egg (JUST Egg) and cultivated meat (GOOD Meat).'),
('Quorn',                 'company', 'United Kingdom','quorn.co.uk',         'Mycoprotein-based meat alternative brand.'),
('Nestle',                'company', 'Switzerland',  'nestle.com',          'Food & beverage major; plant-based lines (Garden Gourmet, Sweet Earth).'),
-- ── Fermentation / ingredient tech ──
('Perfect Day',           'company', 'United States', 'perfectday.com',     'Precision-fermentation dairy proteins.'),
('The EVERY Company',     'company', 'United States', 'theeverycompany.com','Precision-fermentation egg and functional proteins.'),
('Formo',                 'company', 'Germany',      'formo.bio',           'Precision-fermentation dairy/cheese alternatives.'),
('MycoTechnology',        'company', 'United States', 'mycotechcorp.com',   'Mycelium-fermentation platform; bitter-blocking and protein.'),
('Novonesis',             'company', 'Denmark',      'novonesis.com',       'Biosolutions & enzymes (2024 Novozymes + Chr. Hansen merger).'),
('Ginkgo Bioworks',       'company', 'United States', 'ginkgobioworks.com', 'Synthetic-biology / cell-programming platform.'),
-- ── NGOs / non-profits ──
('The Good Food Institute','ngo_gov','United States','gfi.org',             'Nonprofit accelerating alternative proteins (science, policy, industry).'),
('GFI Israel',            'ngo_gov', 'Israel',       'gfi.org.il',          'Good Food Institute Israel chapter (SciTech; MeatCODE host).'),
('GFI Europe',            'ngo_gov', 'United Kingdom','gfieurope.org',      'Good Food Institute Europe chapter.'),
('GFI India',             'ngo_gov', 'India',        'gfi-india.org',       'Good Food Institute India chapter.'),
('GFI APAC',              'ngo_gov', 'Singapore',    'gfi-apac.org',        'Good Food Institute Asia-Pacific chapter.'),
('GFI Brazil',            'ngo_gov', 'Brazil',       'gfi.org.br',          'Good Food Institute Brazil chapter.'),
('ProVeg International',   'ngo_gov', 'Germany',      'proveg.com',          'Food-awareness nonprofit promoting plant-based and alt-protein.'),
('New Harvest',           'ngo_gov', 'United States', 'new-harvest.org',    'Nonprofit funding open cellular-agriculture research.')
ON CONFLICT DO NOTHING;

COMMIT;
