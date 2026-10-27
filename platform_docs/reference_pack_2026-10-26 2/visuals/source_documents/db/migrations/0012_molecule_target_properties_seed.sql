-- =============================================================================
-- 0012 — Deliver the molecule TARGET PROPERTIES as data (seed).
-- Last updated: 2026-08-27 · Data Engineer agent
--
-- WHAT THIS FILE IS
--   A single, self-contained, idempotent SQL file that delivers Lior's target
--   property list into `molecules` + `molecule_properties`. It needs NO Python and
--   NO RDKit — paste it into the Neon SQL Editor (or TablePlus/Postico) and run.
--   Re-running it is safe: every write is an UPDATE ... FROM or an upsert.
--
-- WHAT IT CONTAINS
--   §0  the 0011 DDL, guarded by IF NOT EXISTS (so this file also bootstraps a
--       fresh branch on its own).
--   §1  the ONLY values that cannot be produced inside Postgres: the 590
--       structure-derived descriptors (molecular_weight, formal_charge, tpsa,
--       logp, functional_groups, reactive_groups) computed by RDKit 2026.03.5
--       from `molecules.smiles`. Materialized here as a literal VALUES list.
--   §2  odour thresholds — derived in pure SQL from `meaty_volatile_library`.
--   §3  `molecule_properties` provenance rows — derived in pure SQL from §1/§2,
--       so the 3,650 rows are generated, not pasted.
--   §4  verification queries (run them; they should print the numbers in the
--       comments).
--
-- PROVENANCE RULES (docs/full_text_parallel_evidence_extraction_strategy.md)
--   * raw expression always preserved;
--   * value normalized ONLY when unambiguous — ranges, matrix-qualified values
--     and ">"/"<" limits keep value_num NULL and carry a flag;
--   * no unit conversion at extraction time;
--   * computed values are derivation='system_derived' and are never presented as
--     measurements (logp carries flag 'estimated_not_measured', confidence 0.60).
--
-- LEFT NULL ON PURPOSE — no non-fabricated source exists:
--   pka · isoelectric_point · redox_potential_v · sequence_conformation ·
--   boiling_point · vapor_pressure · oav · color · odor_threshold_ppb
--   (that column asserts ppb; the MVL states no unit — 110 rows are flagged
--    'unit_not_stated_in_source' and normalize the moment the unit is confirmed).
--
-- SAFETY: additive + idempotent. No DROP. No destructive UPDATE. Row count of
--   `molecules` is never changed (799).
-- Applied to Neon: 2026-08-27 — production + dev branches.
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- §0  Schema (same as migration 0011; guarded so this file is self-contained)
-- ---------------------------------------------------------------------------
ALTER TABLE molecules
    ADD COLUMN IF NOT EXISTS molecular_weight      numeric,
    ADD COLUMN IF NOT EXISTS formal_charge         integer,
    ADD COLUMN IF NOT EXISTS functional_groups     text[],
    ADD COLUMN IF NOT EXISTS reactive_groups       text[],
    ADD COLUMN IF NOT EXISTS pka                   numeric,
    ADD COLUMN IF NOT EXISTS isoelectric_point     numeric,
    ADD COLUMN IF NOT EXISTS tpsa                  numeric,
    ADD COLUMN IF NOT EXISTS logp                  numeric,
    ADD COLUMN IF NOT EXISTS redox_potential_v     numeric,
    ADD COLUMN IF NOT EXISTS sequence_conformation text,
    ADD COLUMN IF NOT EXISTS boiling_point         text,
    ADD COLUMN IF NOT EXISTS vapor_pressure        text,
    ADD COLUMN IF NOT EXISTS odor_threshold_raw    text,
    ADD COLUMN IF NOT EXISTS odor_threshold_ppb    numeric,
    ADD COLUMN IF NOT EXISTS oav                   numeric,
    ADD COLUMN IF NOT EXISTS color                 text;

CREATE TABLE IF NOT EXISTS molecule_properties (
    id              bigserial PRIMARY KEY,
    molecule_id     bigint NOT NULL REFERENCES molecules(id) ON DELETE CASCADE,
    property        text   NOT NULL,
    value_raw       text,
    value_num       numeric,
    unit_raw        text,
    unit_norm       text,
    basis           text,
    uncertainty     text,
    replicate_count integer,
    derivation      text NOT NULL
        CHECK (derivation IN ('reported','author_derived','graph_estimated','system_derived')),
    method          text,
    conditions      jsonb,
    source_id       bigint REFERENCES sources(id) ON DELETE SET NULL,
    source_ref      text,
    source_location text,
    confidence      numeric CHECK (confidence >= 0 AND confidence <= 1),
    flags           text[],
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX  IF NOT EXISTS ix_molprop_molecule ON molecule_properties (molecule_id);
CREATE INDEX  IF NOT EXISTS ix_molprop_property ON molecule_properties (property);
CREATE UNIQUE INDEX IF NOT EXISTS ux_molprop_mol_prop_src
    ON molecule_properties (molecule_id, property, COALESCE(source_ref, ''));

-- ---------------------------------------------------------------------------
-- §1  Structure-derived descriptors — 590 rows.
--     These are the ONLY literal values in this file: Postgres cannot compute a
--     TPSA or a Crippen logP, so they are materialized from RDKit here.
--     Order: (molecule_id, molecular_weight, formal_charge, tpsa, logp,
--             functional_groups, reactive_groups)
-- ---------------------------------------------------------------------------
UPDATE molecules m
   SET molecular_weight  = v.mw,
       formal_charge     = v.charge,
       tpsa              = v.tpsa,
       logp              = v.logp,
       functional_groups = v.fg,
       reactive_groups   = v.rg,
       updated_at        = now()
  FROM (VALUES
  (2,160.263,0,13.14,2.7908,ARRAY['disulfide','furan']::text[],ARRAY['disulfide_bridge']::text[]),
  (3,126.155,0,34.14,0.8005,ARRAY['ketone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (5,104.199,0,0.0,1.8951,ARRAY['alkene','disulfide']::text[],ARRAY['allylic_ch','disulfide_bridge']::text[]),
  (6,140.226,0,20.23,2.2813,ARRAY['alcohol','alkene','primary_alcohol']::text[],ARRAY['allylic_ch','bis_allylic_ch']::text[]),
  (7,177.338,0,12.03,2.4841,ARRAY['secondary_amine','thioether']::text[],ARRAY['free_amine_nucleophile']::text[]),
  (8,122.127,0,42.85,0.6792,ARRAY['ketone','pyrazine']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (10,128.174,0,0.0,2.8398,ARRAY['benzene_ring']::text[],NULL),
  (12,131.178,0,15.79,2.4763,ARRAY['benzene_ring','pyrrole']::text[],NULL),
  (13,161.204,0,29.96,2.3173,ARRAY['alkene','ketone','pyridine']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (14,152.237,0,20.23,2.1136,ARRAY['alcohol','alkene']::text[],ARRAY['allylic_ch']::text[]),
  (16,138.282,0,0.0,2.0721,ARRAY['thioether']::text[],NULL),
  (17,88.15,0,20.23,1.0248,ARRAY['alcohol','primary_alcohol']::text[],NULL),
  (18,102.133,0,37.3,1.1171,ARRAY['carboxylic_acid']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (21,126.199,0,17.07,2.3218,ARRAY['aldehyde','alkene']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (22,154.253,0,9.23,2.7677,ARRAY['alkene','ether']::text[],ARRAY['allylic_ch']::text[]),
  (24,135.21,0,12.89,2.5134,ARRAY['pyridine']::text[],NULL),
  (25,80.09,0,25.78,0.4766,ARRAY['pyrazine']::text[],NULL),
  (28,177.338,0,12.03,2.4841,ARRAY['secondary_amine','thioether']::text[],ARRAY['free_amine_nucleophile']::text[]),
  (30,90.078,0,57.53,-0.5482,ARRAY['alcohol','carboxylic_acid']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (31,128.196,0,13.14,2.1426,ARRAY['furan','thioether']::text[],NULL),
  (32,116.185,0,17.07,1.0809,ARRAY['ketone','thioether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (33,138.17,0,35.01,1.0476,ARRAY['ether','pyrazine']::text[],NULL),
  (34,106.124,0,17.07,1.4991,ARRAY['aldehyde','benzene_ring']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (36,130.187,0,26.3,1.5956,ARRAY['ester','ether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (37,86.09,0,26.3,0.3234,ARRAY['ester','ether','lactone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (38,110.156,0,17.07,1.7077,ARRAY['aldehyde','alkene']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (39,86.09,0,34.14,0.1644,ARRAY['ketone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (40,142.154,0,46.53,1.1538,ARRAY['alkene','ester','ether','lactone']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (41,64.065,0,34.14,-0.6702,NULL,NULL),
  (46,46.025,0,37.3,-0.2992,ARRAY['carboxylic_acid']::text[],NULL),
  (47,184.323,0,17.07,4.1062,ARRAY['aldehyde']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (50,166.22,0,25.67,2.3079,ARRAY['ether','furan']::text[],NULL),
  (51,107.156,0,12.89,1.6984,ARRAY['pyridine']::text[],NULL),
  (52,86.09,0,34.14,0.1644,ARRAY['ketone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (53,206.27,0,38.92,2.6703,ARRAY['furan','pyrazine','thioether']::text[],NULL),
  (54,154.253,0,9.23,2.7677,ARRAY['alkene','ether']::text[],ARRAY['allylic_ch']::text[]),
  (55,192.306,0,25.78,2.9905,ARRAY['pyrazine']::text[],NULL),
  (56,136.198,0,25.78,1.6558,ARRAY['pyrazine']::text[],NULL),
  (58,154.253,0,20.23,2.1935,ARRAY['alcohol']::text[],NULL),
  (59,136.15,0,26.3,1.5077,ARRAY['aldehyde','benzene_ring','ether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (60,129.184,0,22.12,1.5418,ARRAY['ether','thiazole','thioether']::text[],NULL),
  (61,134.182,0,25.78,1.682,ARRAY['alkene','pyrazine']::text[],NULL),
  (63,115.201,0,12.36,1.5401,ARRAY['thioether']::text[],NULL),
  (66,168.28,0,20.23,2.5836,ARRAY['alcohol']::text[],NULL),
  (67,152.197,0,35.01,1.6086,ARRAY['ether','pyrazine']::text[],NULL),
  (68,134.2,0,26.3,0.8694,ARRAY['ester','ether','thiol']::text[],ARRAY['carbonyl_electrophile','thiol_nucleophile']::text[]),
  (69,154.253,0,20.23,2.1935,ARRAY['alcohol']::text[],NULL),
  (70,108.144,0,25.78,1.039,ARRAY['pyrazine']::text[],NULL),
  (72,109.128,0,32.86,1.2173,ARRAY['ketone','pyrrole']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (73,113.185,0,12.89,1.7055,ARRAY['thiazole','thioether']::text[],NULL),
  (74,136.238,0,0.0,3.3089,ARRAY['alkene']::text[],ARRAY['allylic_ch','bis_allylic_ch']::text[]),
  (77,72.063,0,34.14,-0.2257,ARRAY['aldehyde','ketone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (80,135.166,0,22.0,1.4646,ARRAY['ketone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (81,128.127,0,46.53,0.7637,ARRAY['alkene','ester','ether','lactone']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (82,142.154,0,35.53,0.8521,ARRAY['alkene','ether','ketone']::text[],ARRAY['carbonyl_electrophile','michael_acceptor']::text[]),
  (83,142.154,0,46.53,1.1538,ARRAY['alkene','ether','ketone']::text[],ARRAY['carbonyl_electrophile','michael_acceptor']::text[]),
  (84,180.363,0,0.0,3.5868,ARRAY['disulfide','thioether']::text[],ARRAY['disulfide_bridge']::text[]),
  (85,100.186,0,0.0,2.0271,ARRAY['alkene','thioether']::text[],ARRAY['allylic_ch']::text[]),
  (87,118.245,0,0.0,2.4965,ARRAY['thiol']::text[],ARRAY['thiol_nucleophile']::text[]),
  (88,121.183,0,12.89,1.9524,ARRAY['pyridine']::text[],NULL),
  (89,135.21,0,12.89,2.2801,ARRAY['pyridine']::text[],NULL),
  (90,330.512,0,37.3,6.7729,ARRAY['alkene','carboxylic_acid']::text[],ARRAY['allylic_ch','bis_allylic_ch','carbonyl_electrophile']::text[]),
  (91,138.21,0,13.14,2.9306,ARRAY['furan']::text[],NULL),
  (92,256.43,0,26.3,5.2506,ARRAY['ester','ether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (93,74.123,0,20.23,0.6347,ARRAY['alcohol','primary_alcohol']::text[],NULL),
  (94,166.176,0,46.53,1.6034,ARRAY['benzene_ring','ether','ketone','phenol']::text[],ARRAY['carbonyl_electrophile','phenolic_antioxidant']::text[]),
  (95,164.339,0,0.0,3.1856,ARRAY['thioether','thiol']::text[],ARRAY['thiol_nucleophile']::text[]),
  (96,120.242,0,0.0,1.7693,ARRAY['thioether','thiol']::text[],ARRAY['thiol_nucleophile']::text[]),
  (98,102.133,0,29.46,0.1561,ARRAY['alcohol','ether']::text[],NULL),
  (100,126.199,0,17.07,2.3218,ARRAY['alkene','ketone']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (101,214.349,0,26.3,3.9362,ARRAY['ester','ether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (102,130.237,0,0.0,2.3452,ARRAY['thioether','thiol','thiophene']::text[],ARRAY['thiol_nucleophile']::text[]),
  (104,127.212,0,12.89,2.0684,ARRAY['thiazole','thioether']::text[],NULL),
  (105,169.293,0,12.89,3.1025,ARRAY['thiazole','thioether']::text[],NULL),
  (106,90.191,0,0.0,1.7163,ARRAY['thiol']::text[],ARRAY['thiol_nucleophile']::text[]),
  (108,169.293,0,12.89,3.0481,ARRAY['thiazole','thioether']::text[],NULL),
  (109,132.228,0,17.07,1.6739,ARRAY['ketone','thiol']::text[],ARRAY['carbonyl_electrophile','thiol_nucleophile']::text[]),
  (110,86.09,0,34.14,0.1644,ARRAY['ketone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (111,152.197,0,35.01,1.6086,ARRAY['ether','pyrazine']::text[],NULL),
  (112,107.156,0,12.89,1.644,ARRAY['pyridine']::text[],NULL),
  (113,220.356,0,12.53,4.2466,ARRAY['alkene','ether']::text[],ARRAY['allylic_ch']::text[]),
  (114,34.083,0,0.0,0.1128,NULL,NULL),
  (116,128.215,0,20.23,2.1152,ARRAY['alcohol','alkene','primary_alcohol']::text[],ARRAY['allylic_ch']::text[]),
  (117,84.118,0,17.07,1.1515,ARRAY['aldehyde','alkene']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (118,128.127,0,46.53,0.7637,ARRAY['alkene','ether','ketone']::text[],ARRAY['carbonyl_electrophile','michael_acceptor']::text[]),
  (121,146.236,0,17.07,1.4636,ARRAY['alkene','ketone','thioether','thiol']::text[],ARRAY['carbonyl_electrophile','michael_acceptor','thiol_nucleophile']::text[]),
  (123,95.101,0,32.86,0.8272,ARRAY['aldehyde','pyrrole']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (124,112.153,0,17.07,1.5606,ARRAY['aldehyde','thioether','thiophene']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (125,183.32,0,12.89,3.4382,ARRAY['thiazole','thioether']::text[],NULL),
  (126,129.184,0,29.43,0.7207,ARRAY['ketone','thioether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (127,62.137,0,0.0,0.9792,ARRAY['thioether']::text[],NULL),
  (128,228.376,0,26.3,4.4704,ARRAY['ester','ether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (129,114.188,0,17.07,2.0116,ARRAY['ketone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (130,154.253,0,9.23,2.7441,ARRAY['ether']::text[],NULL),
  (131,178.279,0,25.78,2.682,ARRAY['pyrazine']::text[],NULL),
  (132,226.36,0,26.3,4.2464,ARRAY['alkene','ester','ether']::text[],ARRAY['allylic_ch','carbonyl_electrophile']::text[]),
  (133,107.112,0,36.93,1.4597,ARRAY['furan','nitrile']::text[],NULL),
  (134,194.278,0,35.01,2.608,ARRAY['ether','pyrazine']::text[],NULL),
  (135,173.3,0,35.25,3.0174,NULL,NULL),
  (136,130.231,0,20.23,2.3392,ARRAY['alcohol','primary_alcohol']::text[],NULL),
  (137,116.16,0,26.3,1.3496,ARRAY['ester','ether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (138,142.154,0,35.53,0.8521,ARRAY['alkene','ether','ketone']::text[],ARRAY['carbonyl_electrophile','michael_acceptor']::text[]),
  (140,84.118,0,17.07,1.1515,ARRAY['alkene','ketone']::text[],ARRAY['carbonyl_electrophile','michael_acceptor']::text[]),
  (141,122.171,0,25.78,1.4019,ARRAY['pyrazine']::text[],NULL),
  (142,140.226,0,17.07,2.7119,ARRAY['aldehyde','alkene']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (143,88.106,0,37.3,-0.0438,ARRAY['alcohol','ketone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (144,126.243,0,0.0,3.3668,NULL,NULL),
  (145,60.052,0,37.3,0.0909,ARRAY['carboxylic_acid']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (146,112.197,0,0.0,2.3649,ARRAY['thioether','thiophene']::text[],NULL),
  (147,120.217,0,20.23,1.1219,ARRAY['alcohol','primary_alcohol','thioether']::text[],NULL),
  (148,112.197,0,0.0,2.3649,ARRAY['thioether','thiophene']::text[],NULL),
  (150,124.183,0,17.07,2.0978,ARRAY['alkene','ketone']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (151,120.242,0,0.0,2.1616,ARRAY['disulfide']::text[],ARRAY['disulfide_bridge']::text[]),
  (152,112.197,0,0.0,2.3105,ARRAY['thioether','thiophene']::text[],NULL),
  (153,136.154,0,42.85,0.9876,ARRAY['ketone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (154,85.131,0,12.89,1.1431,ARRAY['thiazole','thioether']::text[],NULL),
  (155,150.312,0,0.0,3.1878,ARRAY['disulfide']::text[],ARRAY['disulfide_bridge']::text[]),
  (156,71.123,0,12.03,0.3698,ARRAY['secondary_amine']::text[],ARRAY['free_amine_nucleophile']::text[]),
  (157,151.165,0,39.19,1.2583,ARRAY['ester','ether','pyridine']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (158,116.185,0,9.23,1.568,ARRAY['alkene','ether','thiol']::text[],ARRAY['allylic_ch','thiol_nucleophile']::text[]),
  (159,108.14,0,20.23,1.1789,ARRAY['alcohol','benzene_ring','primary_alcohol']::text[],NULL),
  (160,124.183,0,17.07,2.0978,ARRAY['alkene','ketone']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (163,132.206,0,0.0,2.4837,ARRAY['benzene_ring']::text[],NULL),
  (164,168.28,0,9.23,2.8476,ARRAY['ether']::text[],NULL),
  (166,124.139,0,30.21,1.8723,ARRAY['furan','ketone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (167,152.237,0,17.07,2.878,ARRAY['aldehyde','alkene']::text[],ARRAY['allylic_ch','bis_allylic_ch','carbonyl_electrophile']::text[]),
  (168,134.269,0,0.0,2.2025,ARRAY['thioether']::text[],NULL),
  (169,115.157,0,22.12,1.1517,ARRAY['ether','thiazole','thioether']::text[],NULL),
  (171,72.107,0,17.07,0.9854,ARRAY['aldehyde']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (173,74.123,0,20.23,0.7788,ARRAY['alcohol','primary_alcohol']::text[],NULL),
  (176,154.253,0,20.23,2.1935,ARRAY['alcohol']::text[],NULL),
  (177,134.269,0,0.0,2.2009,ARRAY['thioether']::text[],NULL),
  (179,118.201,0,17.07,1.3285,ARRAY['ketone','thioether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (180,83.134,0,23.79,1.7002,ARRAY['nitrile']::text[],NULL),
  (181,100.161,0,17.07,1.7656,ARRAY['aldehyde']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (182,168.196,0,44.24,1.1106,ARRAY['ether','pyrazine']::text[],NULL),
  (183,172.268,0,26.3,2.91,ARRAY['ester','ether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (184,165.236,0,22.12,2.2887,ARRAY['ether','pyridine']::text[],NULL),
  (186,69.107,0,12.36,0.851,NULL,NULL),
  (187,146.211,0,26.3,1.055,ARRAY['ether','ketone','thioether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (190,102.202,0,0.0,1.8824,ARRAY['alkene','thiol']::text[],ARRAY['allylic_ch','thiol_nucleophile']::text[]),
  (192,181.285,0,12.89,3.0182,ARRAY['benzene_ring','thiazole','thioether']::text[],NULL),
  (194,166.336,0,0.0,3.1967,ARRAY['disulfide','thioether']::text[],ARRAY['disulfide_bridge']::text[]),
  (196,98.101,0,33.37,0.7719,ARRAY['alcohol','furan','primary_alcohol']::text[],NULL),
  (197,154.253,0,17.07,3.102,ARRAY['aldehyde','alkene']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (198,120.242,0,0.0,1.4664,ARRAY['thioether']::text[],NULL),
  (200,122.258,0,0.0,2.4076,ARRAY['disulfide']::text[],ARRAY['disulfide_bridge']::text[]),
  (201,180.363,0,0.0,3.2376,ARRAY['thioether']::text[],NULL),
  (202,138.21,0,17.07,2.4879,ARRAY['aldehyde','alkene']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (206,126.199,0,20.23,1.8896,ARRAY['alcohol','alkene']::text[],ARRAY['allylic_ch']::text[]),
  (207,152.237,0,17.07,2.878,ARRAY['aldehyde','alkene']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (209,111.1,0,43.1,0.8772,ARRAY['ketone','oxazole']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (210,154.234,0,17.07,2.5675,ARRAY['ketone','thioether','thiophene']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (213,99.158,0,12.89,1.4515,ARRAY['thiazole','thioether']::text[],NULL),
  (214,108.144,0,25.78,1.0934,NULL,NULL),
  (215,100.161,0,20.23,1.335,ARRAY['alcohol','alkene','primary_alcohol']::text[],ARRAY['allylic_ch']::text[]),
  (216,134.2,0,26.3,0.9125,ARRAY['ester','ether','thioether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (218,116.16,0,26.3,1.348,ARRAY['ester','ether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (219,136.198,0,25.78,1.6751,ARRAY['pyrazine']::text[],NULL),
  (220,112.128,0,26.3,0.878,ARRAY['alkene','ester','ether','lactone']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (222,154.253,0,17.07,2.9579,ARRAY['aldehyde','alkene']::text[],ARRAY['allylic_ch','carbonyl_electrophile']::text[]),
  (223,84.118,0,17.07,1.1515,ARRAY['aldehyde','alkene']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (228,108.144,0,25.78,1.0934,ARRAY['pyrazine']::text[],NULL),
  (229,109.128,0,22.12,1.0902,ARRAY['ether','pyridine']::text[],NULL),
  (230,68.075,0,13.14,1.2796,ARRAY['furan']::text[],NULL),
  (231,104.174,0,17.07,0.9384,ARRAY['aldehyde','thioether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (233,130.231,0,20.23,2.3376,ARRAY['alcohol']::text[],NULL),
  (234,87.122,0,20.31,0.0945,ARRAY['amide']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (235,127.168,0,29.96,1.3457,ARRAY['ketone','thiazole','thioether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (237,114.213,0,0.0,2.0916,ARRAY['alkene','thioether']::text[],ARRAY['allylic_ch']::text[]),
  (238,328.496,0,37.3,6.5489,ARRAY['alkene','carboxylic_acid']::text[],ARRAY['allylic_ch','bis_allylic_ch','carbonyl_electrophile']::text[]),
  (239,128.215,0,17.07,2.5458,ARRAY['ketone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (240,74.123,0,20.23,0.7772,ARRAY['alcohol']::text[],NULL),
  (241,147.177,0,18.07,2.1294,ARRAY['furan']::text[],NULL),
  (242,116.185,0,17.07,1.0809,ARRAY['ketone','thioether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (243,152.237,0,17.07,2.878,ARRAY['aldehyde','alkene']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (244,152.193,0,29.46,1.9632,ARRAY['benzene_ring','ether','phenol']::text[],ARRAY['phenolic_antioxidant']::text[]),
  (245,120.242,0,0.0,2.16,ARRAY['disulfide']::text[],ARRAY['disulfide_bridge']::text[]),
  (246,171.265,0,22.12,2.3502,ARRAY['ether','thiazole','thioether']::text[],NULL),
  (248,144.214,0,37.3,2.2874,ARRAY['carboxylic_acid']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (249,120.242,0,0.0,1.8124,ARRAY['thioether']::text[],NULL),
  (251,112.172,0,17.07,1.9317,ARRAY['aldehyde','alkene']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (253,130.187,0,26.3,1.7381,ARRAY['ester','ether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (254,138.17,0,35.01,1.0476,ARRAY['ether','pyrazine']::text[],NULL),
  (255,62.137,0,0.0,0.9361,ARRAY['thiol']::text[],ARRAY['thiol_nucleophile']::text[]),
  (258,150.221,0,13.14,3.0967,ARRAY['alkene','furan']::text[],ARRAY['allylic_ch']::text[]),
  (259,96.085,0,30.21,1.0921,ARRAY['aldehyde','furan']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (260,280.452,0,37.3,5.8845,ARRAY['alkene','carboxylic_acid']::text[],ARRAY['allylic_ch','bis_allylic_ch','carbonyl_electrophile']::text[]),
  (261,169.293,0,12.89,3.0481,ARRAY['thiazole','thioether']::text[],NULL),
  (262,138.21,0,17.07,2.4879,ARRAY['aldehyde','alkene']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (263,126.18,0,17.07,1.869,ARRAY['aldehyde','thioether','thiophene']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (265,142.198,0,26.3,1.8822,ARRAY['ester','ether','lactone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (266,136.198,0,25.78,1.6558,ARRAY['pyrazine']::text[],NULL),
  (269,166.224,0,35.01,1.9987,ARRAY['ether','pyrazine']::text[],NULL),
  (271,98.17,0,0.0,2.0565,ARRAY['thioether','thiophene']::text[],NULL),
  (272,113.16,0,21.59,1.212,ARRAY['ether']::text[],NULL),
  (273,152.197,0,35.01,1.4377,ARRAY['ether','pyrazine']::text[],NULL),
  (274,152.197,0,35.01,1.4377,ARRAY['ether','pyrazine']::text[],NULL),
  (275,138.21,0,17.07,2.4879,ARRAY['aldehyde','alkene']::text[],ARRAY['allylic_ch','bis_allylic_ch','carbonyl_electrophile']::text[]),
  (277,116.16,0,37.3,1.6513,ARRAY['carboxylic_acid']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (279,111.144,0,26.03,1.5999,ARRAY['oxazole']::text[],NULL),
  (280,222.372,0,20.23,4.0861,ARRAY['alcohol','alkene']::text[],ARRAY['allylic_ch']::text[]),
  (281,122.127,0,42.85,0.6792,ARRAY['ketone','pyrazine']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (282,121.139,0,29.96,1.2842,ARRAY['ketone','pyridine']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (283,170.252,0,34.14,2.3609,ARRAY['ketone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (284,97.117,0,26.03,1.2914,ARRAY['oxazole']::text[],NULL),
  (285,102.158,0,17.07,0.6924,ARRAY['ketone','thioether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (286,184.323,0,17.07,4.1062,ARRAY['ketone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (287,135.191,0,12.89,2.2963,ARRAY['benzene_ring','thiazole','thioether']::text[],NULL),
  (288,152.197,0,35.01,1.6086,ARRAY['ether','pyrazine']::text[],NULL),
  (292,126.199,0,20.23,1.8896,ARRAY['alcohol','alkene']::text[],ARRAY['allylic_ch']::text[]),
  (293,146.28,0,0.0,2.7398,ARRAY['alkene','disulfide']::text[],ARRAY['allylic_ch','disulfide_bridge']::text[]),
  (295,114.188,0,17.07,2.1557,ARRAY['ketone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (297,129.228,0,12.36,1.9286,ARRAY['thioether']::text[],NULL),
  (299,197.281,0,12.89,3.7011,ARRAY['benzene_ring','pyridine']::text[],NULL),
  (301,182.379,0,0.0,3.836,ARRAY['disulfide']::text[],ARRAY['disulfide_bridge']::text[]),
  (304,136.154,0,42.85,0.9876,ARRAY['ketone','pyrazine']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (306,124.143,0,35.01,0.623,ARRAY['ether','pyrazine']::text[],NULL),
  (308,108.144,0,25.78,1.0934,ARRAY['pyrazine']::text[],NULL),
  (310,154.253,0,20.23,2.5037,ARRAY['alcohol','alkene']::text[],ARRAY['allylic_ch']::text[]),
  (311,138.17,0,35.01,1.102,ARRAY['ether','pyrazine']::text[],NULL),
  (314,87.147,0,12.36,1.1091,NULL,NULL),
  (315,113.185,0,12.36,1.6653,ARRAY['alkene']::text[],ARRAY['allylic_ch']::text[]),
  (316,122.258,0,0.0,2.4076,ARRAY['disulfide']::text[],ARRAY['disulfide_bridge']::text[]),
  (318,120.217,0,20.23,0.9331,ARRAY['alcohol','primary_alcohol','thiol']::text[],ARRAY['thiol_nucleophile']::text[]),
  (319,161.204,0,29.96,2.3173,ARRAY['alkene','ketone','pyridine']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (320,130.231,0,20.23,2.3376,ARRAY['alcohol']::text[],NULL),
  (321,152.149,0,46.53,1.1788,ARRAY['benzene_ring','ester','ether','phenol']::text[],ARRAY['carbonyl_electrophile','phenolic_antioxidant']::text[]),
  (322,93.129,0,12.89,1.39,ARRAY['pyridine']::text[],NULL),
  (323,170.252,0,26.3,2.6624,ARRAY['ester','ether','lactone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (324,141.195,0,29.96,1.6541,ARRAY['ketone','thiazole','thioether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (325,138.166,0,40.46,0.927,ARRAY['alcohol','benzene_ring','phenol','primary_alcohol']::text[],ARRAY['phenolic_antioxidant']::text[]),
  (326,198.306,0,26.3,3.4662,ARRAY['alkene','ester','ether']::text[],ARRAY['allylic_ch','carbonyl_electrophile']::text[]),
  (327,156.269,0,20.23,2.7513,ARRAY['alcohol','alkene','primary_alcohol']::text[],ARRAY['allylic_ch']::text[]),
  (328,169.293,0,12.89,3.0481,ARRAY['thiazole','thioether']::text[],NULL),
  (329,136.198,0,25.78,1.7103,ARRAY['pyrazine']::text[],NULL),
  (331,142.242,0,20.23,2.5053,ARRAY['alcohol','alkene','primary_alcohol']::text[],ARRAY['allylic_ch']::text[]),
  (332,154.253,0,17.07,3.102,ARRAY['aldehyde','alkene']::text[],ARRAY['allylic_ch','carbonyl_electrophile']::text[]),
  (333,124.255,0,0.0,2.0296,ARRAY['disulfide','thioether']::text[],ARRAY['disulfide_bridge']::text[]),
  (334,168.148,0,66.76,1.099,ARRAY['benzene_ring','carboxylic_acid','ether','phenol']::text[],ARRAY['carbonyl_electrophile','phenolic_antioxidant']::text[]),
  (335,118.201,0,17.07,1.3269,ARRAY['aldehyde','thioether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (336,144.214,0,37.3,2.4315,ARRAY['carboxylic_acid']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (337,120.151,0,17.07,1.428,ARRAY['aldehyde','benzene_ring']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (341,152.237,0,17.07,2.878,ARRAY['aldehyde','alkene']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (342,124.183,0,17.07,2.0978,ARRAY['aldehyde','alkene']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (343,126.111,0,50.44,0.6538,ARRAY['phenol']::text[],ARRAY['phenolic_antioxidant']::text[]),
  (345,200.322,0,37.3,3.9919,ARRAY['carboxylic_acid']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (346,127.212,0,12.89,2.0956,ARRAY['thiazole','thioether']::text[],NULL),
  (347,114.188,0,17.07,2.1557,ARRAY['aldehyde']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (348,126.18,0,17.07,1.9507,ARRAY['ketone','thioether','thiophene']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (349,143.573,0,32.86,1.8707,ARRAY['ketone','pyrrole']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (353,197.281,0,12.89,3.7011,ARRAY['benzene_ring','pyridine']::text[],NULL),
  (357,122.167,0,20.23,1.9546,ARRAY['benzene_ring','phenol']::text[],ARRAY['phenolic_antioxidant']::text[]),
  (358,112.197,0,0.0,2.3649,ARRAY['thioether','thiophene']::text[],NULL),
  (359,127.212,0,12.89,2.2665,ARRAY['thiazole','thioether']::text[],NULL),
  (361,168.236,0,29.6,2.0892,ARRAY['aldehyde','alkene','ether']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (362,142.242,0,17.07,2.9359,ARRAY['aldehyde']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (363,120.151,0,17.07,1.8892,ARRAY['benzene_ring','ketone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (365,128.196,0,13.14,2.1851,ARRAY['furan','thiol']::text[],ARRAY['thiol_nucleophile']::text[]),
  (366,148.161,0,26.28,2.4634,ARRAY['furan']::text[],NULL),
  (367,138.21,0,17.07,2.4879,ARRAY['aldehyde','alkene']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (369,114.188,0,17.07,1.8675,ARRAY['aldehyde']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (370,138.17,0,35.01,1.1837,ARRAY['ether','pyrazine']::text[],NULL),
  (373,128.215,0,17.07,2.5458,ARRAY['ketone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (374,196.29,0,26.3,3.2422,ARRAY['alkene','ester','ether']::text[],ARRAY['allylic_ch','carbonyl_electrophile']::text[]),
  (375,220.356,0,17.07,4.2943,ARRAY['alkene','ketone']::text[],ARRAY['allylic_ch','carbonyl_electrophile']::text[]),
  (376,127.212,0,12.89,2.0139,ARRAY['thiazole','thioether']::text[],NULL),
  (377,188.024,0,32.86,1.9798,ARRAY['ketone','pyrrole']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (378,126.271,0,0.0,2.2756,ARRAY['disulfide']::text[],ARRAY['disulfide_bridge']::text[]),
  (380,141.239,0,12.89,2.2679,ARRAY['thiazole','thioether']::text[],NULL),
  (381,86.134,0,20.23,0.9433,ARRAY['alcohol','alkene']::text[],ARRAY['allylic_ch']::text[]),
  (382,100.117,0,37.3,1.0372,ARRAY['alkene','carboxylic_acid']::text[],ARRAY['allylic_ch','carbonyl_electrophile']::text[]),
  (384,98.145,0,17.07,1.3755,ARRAY['ketone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (385,122.258,0,0.0,2.0153,ARRAY['thioether','thiol']::text[],ARRAY['thiol_nucleophile']::text[]),
  (386,136.154,0,42.85,0.9876,ARRAY['ketone','pyrazine']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (387,132.253,0,0.0,2.283,ARRAY['alkene','thioether','thiol']::text[],ARRAY['allylic_ch','thiol_nucleophile']::text[]),
  (388,152.237,0,17.07,2.878,ARRAY['aldehyde','alkene']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (389,126.271,0,0.0,2.2756,ARRAY['disulfide']::text[],ARRAY['disulfide_bridge']::text[]),
  (390,124.183,0,17.07,2.0978,ARRAY['alkene','ketone']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (391,167.252,0,26.03,2.7519,ARRAY['oxazole']::text[],NULL),
  (392,120.151,0,17.07,1.428,ARRAY['aldehyde','benzene_ring']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (393,124.139,0,29.46,1.4008,ARRAY['benzene_ring','ether','phenol']::text[],ARRAY['phenolic_antioxidant']::text[]),
  (395,59.044,-1,40.13,-1.2438,NULL,ARRAY['carbonyl_electrophile']::text[]),
  (396,86.134,0,17.07,1.3755,ARRAY['ketone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (398,116.204,0,20.23,1.9475,ARRAY['alcohol']::text[],NULL),
  (401,86.134,0,17.07,1.3755,ARRAY['aldehyde']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (403,46.069,0,20.23,-0.0014,ARRAY['alcohol','primary_alcohol']::text[],NULL),
  (404,108.144,0,25.78,1.039,ARRAY['pyrazine']::text[],NULL),
  (405,96.129,0,13.14,1.8964,ARRAY['furan']::text[],NULL),
  (406,146.255,0,17.07,2.1071,ARRAY['aldehyde','thioether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (407,121.139,0,29.96,1.2842,ARRAY['ketone','pyridine']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (409,152.149,0,46.53,1.2133,ARRAY['aldehyde','benzene_ring','ether','phenol']::text[],ARRAY['carbonyl_electrophile','phenolic_antioxidant']::text[]),
  (410,154.325,0,0.0,3.0558,ARRAY['disulfide']::text[],ARRAY['disulfide_bridge']::text[]),
  (412,165.192,0,63.32,0.641,ARRAY['benzene_ring','carboxylic_acid','primary_amine']::text[],ARRAY['carbonyl_electrophile','free_amine_nucleophile']::text[]),
  (413,140.226,0,20.23,2.2813,ARRAY['alcohol','alkene','primary_alcohol']::text[],ARRAY['allylic_ch']::text[]),
  (416,97.117,0,26.03,1.2914,ARRAY['oxazole']::text[],NULL),
  (419,126.199,0,17.07,2.3218,ARRAY['aldehyde','alkene']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (421,60.096,0,20.23,0.3887,ARRAY['alcohol','primary_alcohol']::text[],NULL),
  (422,122.171,0,25.78,1.6,ARRAY['pyrazine']::text[],NULL),
  (423,154.253,0,20.23,2.6698,ARRAY['alcohol','alkene']::text[],ARRAY['allylic_ch']::text[]),
  (424,152.309,0,0.0,2.8066,ARRAY['disulfide','thioether']::text[],ARRAY['disulfide_bridge']::text[]),
  (426,148.296,0,0.0,2.591,ARRAY['thioether']::text[],NULL),
  (427,114.169,0,13.14,1.7094,ARRAY['furan','thiol']::text[],ARRAY['thiol_nucleophile']::text[]),
  (428,88.15,0,20.23,1.1689,ARRAY['alcohol','primary_alcohol']::text[],NULL),
  (429,158.285,0,20.23,3.1178,ARRAY['alcohol']::text[],NULL),
  (430,100.142,0,20.23,1.4537,ARRAY['phenol','thioether','thiophene']::text[],ARRAY['phenolic_antioxidant']::text[]),
  (433,98.145,0,17.07,1.5416,ARRAY['aldehyde','alkene']::text[],ARRAY['allylic_ch','carbonyl_electrophile']::text[]),
  (434,122.171,0,25.78,1.4291,ARRAY['pyrazine']::text[],NULL),
  (435,121.183,0,12.89,2.205,ARRAY['pyridine']::text[],NULL),
  (436,94.204,0,0.0,1.6274,ARRAY['disulfide']::text[],ARRAY['disulfide_bridge']::text[]),
  (437,128.215,0,17.07,2.5458,ARRAY['aldehyde']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (440,154.253,0,17.07,2.9579,ARRAY['aldehyde','alkene']::text[],ARRAY['allylic_ch','carbonyl_electrophile']::text[]),
  (441,150.225,0,25.78,1.9835,ARRAY['pyrazine']::text[],NULL),
  (442,117.151,0,15.79,2.1679,ARRAY['benzene_ring','pyrrole']::text[],NULL),
  (445,112.128,0,26.3,0.878,ARRAY['alkene','ether','ketone']::text[],ARRAY['carbonyl_electrophile','michael_acceptor']::text[]),
  (446,108.231,0,0.0,1.6252,ARRAY['thioether','thiol']::text[],ARRAY['thiol_nucleophile']::text[]),
  (447,172.268,0,26.3,2.9084,ARRAY['ester','ether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (448,140.226,0,17.07,2.7119,ARRAY['aldehyde','alkene']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (449,141.239,0,12.89,2.3416,ARRAY['thiazole','thioether']::text[],NULL),
  (452,222.444,0,0.0,4.4079,ARRAY['thioether']::text[],NULL),
  (453,138.122,0,57.53,0.9103,ARRAY['aldehyde','benzene_ring','phenol']::text[],ARRAY['carbonyl_electrophile','phenolic_antioxidant']::text[]),
  (454,166.224,0,35.01,1.9639,ARRAY['ether','pyrazine']::text[],NULL),
  (455,78.136,0,20.23,-0.0915,ARRAY['alcohol','primary_alcohol','thiol']::text[],ARRAY['thiol_nucleophile']::text[]),
  (456,220.356,0,20.23,4.0062,ARRAY['alcohol','alkene']::text[],ARRAY['allylic_ch','bis_allylic_ch']::text[]),
  (460,302.458,0,37.3,5.9927,ARRAY['alkene','carboxylic_acid']::text[],ARRAY['allylic_ch','bis_allylic_ch','carbonyl_electrophile']::text[]),
  (461,135.21,0,12.89,2.5134,ARRAY['pyridine']::text[],NULL),
  (463,88.062,0,54.37,-0.34,ARRAY['carboxylic_acid','ketone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (465,152.237,0,17.07,2.878,ARRAY['aldehyde','alkene']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (466,122.171,0,25.78,1.3474,ARRAY['pyrazine']::text[],NULL),
  (467,124.143,0,35.01,0.7936,ARRAY['ether','pyrazine']::text[],NULL),
  (468,99.158,0,12.89,1.4515,ARRAY['thiazole','thioether']::text[],NULL),
  (469,148.271,0,20.23,1.9005,ARRAY['alcohol','primary_alcohol','thioether']::text[],NULL),
  (470,182.307,0,17.07,3.8822,ARRAY['aldehyde','alkene']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (471,152.237,0,17.07,2.878,ARRAY['aldehyde','alkene']::text[],ARRAY['allylic_ch','bis_allylic_ch','carbonyl_electrophile']::text[]),
  (472,206.27,0,38.92,2.6703,ARRAY['furan','pyrazine','thioether']::text[],NULL),
  (473,134.222,0,0.0,3.1184,ARRAY['benzene_ring']::text[],NULL),
  (474,88.15,0,20.23,1.0248,ARRAY['alcohol','primary_alcohol']::text[],NULL),
  (475,141.239,0,12.89,2.3223,ARRAY['thiazole','thioether']::text[],NULL),
  (476,138.21,0,13.14,3.0123,ARRAY['furan']::text[],NULL),
  (477,164.204,0,29.46,2.4339,ARRAY['alkene','benzene_ring','ether','phenol']::text[],ARRAY['phenolic_antioxidant']::text[]),
  (478,144.214,0,26.3,2.1282,ARRAY['ester','ether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (479,156.269,0,17.07,3.326,ARRAY['ketone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (480,198.306,0,26.3,3.4662,ARRAY['alkene','ester','ether']::text[],ARRAY['allylic_ch','carbonyl_electrophile']::text[]),
  (481,186.295,0,26.3,3.2985,ARRAY['ester','ether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (484,142.242,0,17.07,2.9359,ARRAY['ketone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (485,155.266,0,12.89,2.5763,ARRAY['thiazole','thioether']::text[],NULL),
  (486,108.14,0,20.23,1.7006,ARRAY['benzene_ring','phenol']::text[],ARRAY['phenolic_antioxidant']::text[]),
  (487,164.204,0,29.46,2.1293,ARRAY['alkene','benzene_ring','ether','phenol']::text[],ARRAY['allylic_ch','phenolic_antioxidant']::text[]),
  (488,126.111,0,50.44,0.5844,ARRAY['alcohol','aldehyde','furan','primary_alcohol']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (490,139.223,0,12.89,2.4029,ARRAY['alkene','thiazole','thioether']::text[],NULL),
  (491,178.279,0,25.78,2.8261,ARRAY['pyrazine']::text[],NULL),
  (493,192.302,0,17.07,3.6582,ARRAY['alkene','ketone']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (494,152.149,0,46.53,1.2133,ARRAY['aldehyde','benzene_ring','ether','phenol']::text[],ARRAY['carbonyl_electrophile','phenolic_antioxidant']::text[]),
  (496,141.239,0,12.89,2.2679,ARRAY['thiazole','thioether']::text[],NULL),
  (497,72.107,0,17.07,0.8413,ARRAY['aldehyde']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (498,72.107,0,9.23,0.7968,ARRAY['ether']::text[],NULL),
  (499,136.198,0,25.78,1.7375,ARRAY['pyrazine']::text[],NULL),
  (500,155.2,0,12.89,2.7486,ARRAY['benzene_ring','pyridine']::text[],NULL),
  (501,152.237,0,17.07,2.878,ARRAY['aldehyde','alkene']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (502,149.193,0,22.0,1.6369,ARRAY['ketone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (503,110.116,0,35.01,0.4852,ARRAY['ether','pyrazine']::text[],NULL),
  (504,136.238,0,0.0,3.475,ARRAY['alkene']::text[],ARRAY['allylic_ch']::text[]),
  (506,192.302,0,17.07,3.5141,ARRAY['alkene','ketone']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (508,163.22,0,29.96,2.4076,ARRAY['ketone','pyridine']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (509,167.252,0,26.03,2.9697,ARRAY['oxazole']::text[],NULL),
  (510,144.264,0,0.0,2.7784,ARRAY['thioether','thiophene']::text[],NULL),
  (511,106.215,0,0.0,1.4239,ARRAY['thioether']::text[],NULL),
  (512,107.112,0,29.96,0.8941,ARRAY['aldehyde','pyridine']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (513,156.269,0,20.23,2.4395,ARRAY['alcohol']::text[],NULL),
  (514,130.187,0,26.3,1.5956,ARRAY['ester','ether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (515,155.266,0,12.89,2.8833,ARRAY['thiazole','thioether']::text[],NULL),
  (516,156.269,0,17.07,3.326,ARRAY['aldehyde']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (517,126.199,0,17.07,2.3218,ARRAY['alkene','ketone']::text[],ARRAY['carbonyl_electrophile','michael_acceptor']::text[]),
  (518,104.218,0,0.0,1.9623,ARRAY['thiol']::text[],ARRAY['thiol_nucleophile']::text[]),
  (523,88.106,0,37.3,0.8711,ARRAY['carboxylic_acid']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (524,168.236,0,26.3,2.4384,ARRAY['alkene','ester','ether','lactone']::text[],ARRAY['allylic_ch','carbonyl_electrophile']::text[]),
  (525,166.22,0,30.21,2.3725,NULL,NULL),
  (526,155.266,0,12.89,2.658,ARRAY['thiazole','thioether']::text[],NULL),
  (527,90.191,0,0.0,1.7594,ARRAY['thioether']::text[],NULL),
  (528,88.15,0,20.23,1.1689,ARRAY['alcohol','primary_alcohol']::text[],NULL),
  (529,126.111,0,50.44,1.1878,ARRAY['furan','ketone','phenol']::text[],ARRAY['carbonyl_electrophile','phenolic_antioxidant']::text[]),
  (530,113.16,0,20.31,0.6287,ARRAY['amide']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (532,136.238,0,0.0,3.3089,ARRAY['alkene']::text[],ARRAY['allylic_ch']::text[]),
  (533,130.187,0,26.3,1.5956,ARRAY['ester','ether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (534,133.15,0,26.03,2.1362,ARRAY['benzene_ring','oxazole']::text[],NULL),
  (535,128.196,0,13.14,2.3099,ARRAY['furan','thioether']::text[],NULL),
  (536,88.15,0,20.23,1.0248,ARRAY['alcohol','primary_alcohol']::text[],NULL),
  (537,142.198,0,26.3,1.8822,ARRAY['ester','ether','lactone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (538,120.242,0,0.0,1.814,ARRAY['thioether']::text[],NULL),
  (542,102.133,0,37.3,1.2612,ARRAY['carboxylic_acid']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (543,178.279,0,25.78,2.6004,ARRAY['pyrazine']::text[],NULL),
  (545,136.198,0,25.78,1.7103,ARRAY['pyrazine']::text[],NULL),
  (546,94.117,0,25.78,0.785,ARRAY['pyrazine']::text[],NULL),
  (547,99.133,0,21.59,0.8235,ARRAY['ether']::text[],NULL),
  (548,141.239,0,12.89,2.4857,ARRAY['thiazole','thioether']::text[],NULL),
  (549,129.184,0,22.12,1.4601,ARRAY['ether','thiazole','thioether']::text[],NULL),
  (551,138.17,0,35.01,1.1837,ARRAY['ether','pyrazine']::text[],NULL),
  (554,84.143,0,0.0,1.7481,ARRAY['thioether','thiophene']::text[],NULL),
  (555,386.664,0,20.23,7.3887,ARRAY['alcohol','alkene']::text[],ARRAY['allylic_ch']::text[]),
  (557,115.157,0,22.12,1.1517,ARRAY['ether','thiazole','thioether']::text[],NULL),
  (558,196.319,0,25.78,2.7054,ARRAY['pyrazine','thioether']::text[],NULL),
  (561,166.224,0,35.01,1.8278,ARRAY['ether','pyrazine']::text[],NULL),
  (562,143.211,0,33.12,0.9863,ARRAY['alcohol','primary_alcohol','thiazole','thioether']::text[],NULL),
  (563,88.15,0,20.23,1.0248,ARRAY['alcohol','primary_alcohol']::text[],NULL),
  (564,124.143,0,35.01,0.7936,ARRAY['ether','pyrazine']::text[],NULL),
  (565,150.225,0,25.78,1.9098,ARRAY['pyrazine']::text[],NULL),
  (566,186.295,0,26.3,3.3001,ARRAY['ester','ether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (567,127.168,0,29.96,1.3457,ARRAY['ketone','thiazole','thioether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (568,76.145,0,0.0,1.0181,NULL,NULL),
  (569,125.171,0,29.1,0.8427,ARRAY['alkene','ketone','secondary_amine']::text[],ARRAY['allylic_ch','carbonyl_electrophile','free_amine_nucleophile','michael_acceptor']::text[]),
  (571,166.224,0,35.01,1.6837,ARRAY['ether','pyrazine']::text[],NULL),
  (572,126.199,0,17.07,2.3218,ARRAY['aldehyde','alkene']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (574,100.186,0,0.0,2.0255,ARRAY['alkene','thioether']::text[],ARRAY['allylic_ch']::text[]),
  (575,129.184,0,22.12,1.5418,ARRAY['ether','thiazole','thioether']::text[],NULL),
  (577,48.11,0,0.0,0.546,ARRAY['thiol']::text[],ARRAY['thiol_nucleophile']::text[]),
  (578,114.1,0,46.53,0.3752,ARRAY['alkene','ether','ketone']::text[],ARRAY['carbonyl_electrophile','michael_acceptor']::text[]),
  (579,114.169,0,13.14,1.8767,ARRAY['furan','thiol']::text[],ARRAY['thiol_nucleophile']::text[]),
  (580,160.241,0,0.0,3.1285,ARRAY['benzene_ring','thiol']::text[],ARRAY['thiol_nucleophile']::text[]),
  (581,172.268,0,26.3,2.7643,ARRAY['ester','ether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (582,126.18,0,17.07,1.869,ARRAY['aldehyde','thioether','thiophene']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (583,220.356,0,20.23,4.6853,ARRAY['benzene_ring','phenol']::text[],ARRAY['phenolic_antioxidant']::text[]),
  (584,172.268,0,37.3,3.2117,ARRAY['carboxylic_acid']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (586,44.053,0,17.07,0.2052,ARRAY['aldehyde']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (587,148.252,0,17.07,1.7291,ARRAY['disulfide','ketone']::text[],ARRAY['carbonyl_electrophile','disulfide_bridge']::text[]),
  (588,108.144,0,25.78,1.0934,ARRAY['pyrazine']::text[],NULL),
  (590,122.171,0,25.78,1.3474,ARRAY['pyrazine']::text[],NULL),
  (592,198.306,0,26.3,3.3221,ARRAY['alkene','ester','ether']::text[],ARRAY['allylic_ch','carbonyl_electrophile']::text[]),
  (593,94.117,0,25.78,0.785,ARRAY['pyrazine']::text[],NULL),
  (596,242.322,0,35.01,3.7758,ARRAY['benzene_ring','ether','pyrazine']::text[],NULL),
  (597,142.11,0,70.67,0.3594,ARRAY['phenol']::text[],ARRAY['phenolic_antioxidant']::text[]),
  (599,113.185,0,12.89,1.7599,ARRAY['thiazole','thioether']::text[],NULL),
  (600,130.168,0,37.3,1.0918,ARRAY['alkene','ketone','thioether']::text[],ARRAY['carbonyl_electrophile','michael_acceptor']::text[]),
  (601,103.124,0,23.79,1.5583,ARRAY['benzene_ring','nitrile']::text[],NULL),
  (602,140.226,0,17.07,2.5678,ARRAY['aldehyde','alkene']::text[],ARRAY['allylic_ch','carbonyl_electrophile']::text[]),
  (603,146.299,0,0.0,3.3198,ARRAY['thioether']::text[],NULL),
  (604,165.236,0,22.12,2.2887,ARRAY['ether','pyridine']::text[],NULL),
  (605,113.185,0,12.89,1.7599,ARRAY['thiazole','thioether']::text[],NULL),
  (606,150.177,0,29.46,2.0438,ARRAY['alkene','benzene_ring','ether','phenol']::text[],ARRAY['phenolic_antioxidant']::text[]),
  (607,158.285,0,20.23,3.1194,ARRAY['alcohol','primary_alcohol']::text[],NULL),
  (608,141.195,0,29.96,1.6541,ARRAY['ketone','thiazole','thioether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (609,124.183,0,13.14,2.6222,ARRAY['furan']::text[],NULL),
  (610,190.286,0,17.07,3.4342,ARRAY['alkene','ketone']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (611,160.282,0,17.07,2.4972,ARRAY['aldehyde','thioether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (612,127.187,0,21.59,1.6021,ARRAY['ether']::text[],NULL),
  (613,100.117,0,37.3,1.0372,ARRAY['alkene','carboxylic_acid']::text[],ARRAY['carbonyl_electrophile','michael_acceptor']::text[]),
  (614,116.16,0,26.3,1.2055,ARRAY['ester','ether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (615,162.279,0,9.23,1.929,ARRAY['ether','thioether']::text[],NULL),
  (616,136.198,0,25.78,1.6558,ARRAY['pyrazine']::text[],NULL),
  (617,140.207,0,17.07,2.3408,ARRAY['ketone','thioether','thiophene']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (618,86.134,0,17.07,1.2314,ARRAY['ketone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (619,114.169,0,13.14,1.8767,ARRAY['furan','thiol']::text[],ARRAY['thiol_nucleophile']::text[]),
  (620,194.255,0,26.28,3.306,ARRAY['furan','thioether']::text[],NULL),
  (621,86.134,0,17.07,1.2314,ARRAY['aldehyde']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (622,121.183,0,12.89,2.0341,ARRAY['pyridine']::text[],NULL),
  (623,104.174,0,17.07,0.9384,ARRAY['aldehyde','thioether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (625,154.253,0,20.23,2.5037,ARRAY['alcohol','alkene']::text[],ARRAY['allylic_ch']::text[]),
  (627,126.111,0,50.44,0.4546,ARRAY['alcohol','furan','ketone','primary_alcohol']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (629,110.156,0,17.07,1.7077,ARRAY['aldehyde','alkene']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (630,124.208,0,0.0,2.1164,ARRAY['benzene_ring','thiol']::text[],ARRAY['thiol_nucleophile']::text[]),
  (631,130.187,0,26.3,1.5956,ARRAY['ester','ether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (632,107.156,0,12.89,1.644,ARRAY['pyridine']::text[],NULL),
  (633,134.182,0,25.78,1.5263,ARRAY['pyrazine']::text[],NULL),
  (634,98.145,0,17.07,1.3755,ARRAY['ketone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (635,122.167,0,20.23,1.2214,ARRAY['alcohol','benzene_ring','primary_alcohol']::text[],NULL),
  (638,136.198,0,25.78,1.6558,ARRAY['pyrazine']::text[],NULL),
  (640,186.295,0,26.3,3.156,ARRAY['ester','ether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (641,200.322,0,26.3,3.6902,ARRAY['ester','ether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (642,170.252,0,26.3,2.6624,ARRAY['ester','ether','lactone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (644,100.117,0,26.3,0.3643,ARRAY['ether','ketone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (645,140.207,0,17.07,2.2591,ARRAY['ketone','thioether','thiophene']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (646,59.112,0,3.24,0.1778,ARRAY['tertiary_amine']::text[],NULL),
  (647,160.263,0,13.14,2.9581,ARRAY['disulfide','furan']::text[],ARRAY['disulfide_bridge']::text[]),
  (648,100.161,0,17.07,1.7656,ARRAY['ketone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (649,182.379,0,0.0,3.0514,ARRAY['thioether','thiol']::text[],ARRAY['thiol_nucleophile']::text[]),
  (650,164.252,0,25.78,2.436,ARRAY['pyrazine']::text[],NULL),
  (651,124.143,0,35.01,0.8753,ARRAY['ether','pyrazine']::text[],NULL),
  (652,112.128,0,37.3,1.1813,ARRAY['alkene','ketone']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (653,122.258,0,0.0,2.4076,ARRAY['disulfide']::text[],ARRAY['disulfide_bridge']::text[]),
  (655,134.269,0,0.0,2.2025,ARRAY['thioether']::text[],NULL),
  (656,170.296,0,17.07,3.7161,ARRAY['ketone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (658,126.155,0,37.3,1.5714,ARRAY['alkene','ketone']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (660,124.183,0,17.07,2.0978,ARRAY['alkene','ketone']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (662,140.138,0,50.44,0.9078,ARRAY['phenol']::text[],ARRAY['phenolic_antioxidant']::text[]),
  (663,224.344,0,26.3,3.8783,ARRAY['alkene','ester','ether']::text[],ARRAY['allylic_ch','carbonyl_electrophile']::text[]),
  (664,124.208,0,0.0,2.1164,ARRAY['benzene_ring','thiol']::text[],ARRAY['thiol_nucleophile']::text[]),
  (665,144.258,0,20.23,2.7277,ARRAY['alcohol']::text[],NULL),
  (666,106.19,0,20.23,0.7318,ARRAY['alcohol','primary_alcohol','thioether']::text[],NULL),
  (667,110.112,0,30.21,1.4005,ARRAY['aldehyde','furan']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (668,76.164,0,0.0,1.3262,ARRAY['thiol']::text[],ARRAY['thiol_nucleophile']::text[]),
  (669,88.15,0,20.23,1.1673,ARRAY['alcohol']::text[],NULL),
  (670,109.128,0,32.86,1.1356,ARRAY['aldehyde','pyrrole']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (671,90.191,0,0.0,1.5722,ARRAY['thiol']::text[],ARRAY['thiol_nucleophile']::text[]),
  (674,88.106,0,26.3,0.5694,ARRAY['ester','ether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (675,110.112,0,30.21,1.4822,ARRAY['furan','ketone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (676,212.333,0,26.3,3.7122,ARRAY['alkene','ester','ether']::text[],ARRAY['allylic_ch','carbonyl_electrophile']::text[]),
  (677,240.387,0,26.3,4.4924,ARRAY['alkene','ester','ether']::text[],ARRAY['allylic_ch','carbonyl_electrophile']::text[]),
  (679,140.226,0,17.07,2.7119,ARRAY['aldehyde','alkene']::text[],ARRAY['allylic_ch','carbonyl_electrophile']::text[]),
  (681,120.242,0,0.0,1.8124,ARRAY['thioether']::text[],NULL),
  (682,155.266,0,12.89,2.7941,ARRAY['thiazole','thioether']::text[],NULL),
  (684,278.436,0,37.3,5.6605,ARRAY['alkene','carboxylic_acid']::text[],ARRAY['allylic_ch','bis_allylic_ch','carbonyl_electrophile']::text[]),
  (686,86.134,0,17.07,1.2314,ARRAY['aldehyde']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (688,135.166,0,43.09,1.4714,ARRAY['benzene_ring','ketone','primary_amine']::text[],ARRAY['carbonyl_electrophile','free_amine_nucleophile']::text[]),
  (689,163.311,0,12.03,2.094,ARRAY['secondary_amine','thioether']::text[],ARRAY['free_amine_nucleophile']::text[]),
  (690,140.226,0,17.07,2.7119,ARRAY['aldehyde','alkene']::text[],ARRAY['allylic_ch','carbonyl_electrophile']::text[]),
  (691,90.147,0,17.07,0.5052,ARRAY['ketone','thiol']::text[],ARRAY['carbonyl_electrophile','thiol_nucleophile']::text[]),
  (692,135.21,0,12.89,2.4242,ARRAY['pyridine']::text[],NULL),
  (693,112.084,0,50.44,0.9778,ARRAY['carboxylic_acid','furan']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (694,150.202,0,13.14,3.0081,ARRAY['furan','thioether','thiophene']::text[],NULL),
  (695,125.171,0,26.03,2.0172,ARRAY['oxazole']::text[],NULL),
  (696,90.078,0,57.53,-0.5482,ARRAY['alcohol','carboxylic_acid']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (697,142.198,0,34.14,1.7248,ARRAY['ketone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (698,74.079,0,37.3,-0.4323,ARRAY['alcohol','ketone','primary_alcohol']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (700,132.253,0,0.0,2.2846,ARRAY['alkene','thioether','thiol']::text[],ARRAY['allylic_ch','thiol_nucleophile']::text[]),
  (701,138.21,0,17.07,2.4879,ARRAY['aldehyde','alkene']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (702,190.286,0,17.07,3.4342,ARRAY['alkene','ketone']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (704,194.278,0,35.01,2.3822,ARRAY['ether','pyrazine']::text[],NULL),
  (705,102.177,0,20.23,1.559,ARRAY['alcohol','primary_alcohol']::text[],NULL),
  (706,108.144,0,25.78,1.0934,ARRAY['pyrazine']::text[],NULL),
  (708,166.224,0,35.01,1.917,ARRAY['ether','pyrazine']::text[],NULL),
  (711,150.225,0,25.78,1.9098,ARRAY['pyrazine']::text[],NULL),
  (712,88.106,0,37.3,0.727,ARRAY['carboxylic_acid']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (714,128.196,0,13.14,2.3099,ARRAY['furan','thioether']::text[],NULL),
  (715,136.198,0,25.78,1.6558,ARRAY['pyrazine']::text[],NULL),
  (716,178.279,0,25.78,2.682,ARRAY['pyrazine']::text[],NULL),
  (717,122.171,0,25.78,1.3474,ARRAY['pyrazine']::text[],NULL),
  (718,150.181,0,42.85,1.2416,ARRAY['ketone','pyrazine']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (719,172.268,0,26.3,2.9084,ARRAY['ester','ether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (720,164.252,0,25.78,2.436,ARRAY['pyrazine']::text[],NULL),
  (721,134.269,0,0.0,2.1594,ARRAY['thioether','thiol']::text[],ARRAY['thiol_nucleophile']::text[]),
  (722,156.269,0,17.07,3.326,ARRAY['ketone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (724,114.144,0,26.3,1.102,ARRAY['ester','ether','lactone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (725,100.117,0,34.14,0.5545,ARRAY['ketone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (726,128.259,0,0.0,3.7569,NULL,NULL),
  (727,111.144,0,44.08,1.632,ARRAY['alkene']::text[],ARRAY['allylic_ch']::text[]),
  (729,149.193,0,22.0,1.5552,ARRAY['aldehyde']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (730,162.323,0,0.0,2.9795,ARRAY['thioether']::text[],NULL),
  (732,134.178,0,17.07,2.1976,ARRAY['benzene_ring','ketone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (733,67.091,0,15.79,1.0147,ARRAY['pyrrole']::text[],NULL),
  (734,155.241,0,21.59,2.2382,ARRAY['ether']::text[],NULL),
  (735,79.102,0,12.89,1.0816,ARRAY['pyridine']::text[],NULL),
  (736,99.133,0,29.43,0.6661,ARRAY['ketone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (739,98.145,0,17.07,1.5416,ARRAY['aldehyde','alkene']::text[],ARRAY['allylic_ch','carbonyl_electrophile','michael_acceptor']::text[]),
  (741,151.19,0,26.03,2.4031,ARRAY['furan','thiazole','thioether']::text[],NULL),
  (742,155.222,0,29.96,1.9625,ARRAY['ketone','thiazole','thioether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (743,122.171,0,25.78,1.4019,ARRAY['pyrazine']::text[],NULL),
  (744,156.269,0,20.23,2.4395,ARRAY['alcohol']::text[],NULL),
  (745,111.144,0,29.43,0.8102,ARRAY['ketone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (746,123.155,0,22.12,1.4803,ARRAY['ether','pyridine']::text[],NULL),
  (747,144.258,0,20.23,2.7293,ARRAY['alcohol','primary_alcohol']::text[],NULL),
  (748,125.171,0,26.03,1.9355,ARRAY['oxazole']::text[],NULL),
  (749,120.195,0,0.0,2.6119,ARRAY['benzene_ring']::text[],NULL),
  (750,128.215,0,20.23,2.1136,ARRAY['alcohol','alkene']::text[],ARRAY['allylic_ch']::text[]),
  (751,142.242,0,20.23,2.5053,ARRAY['alcohol','alkene','primary_alcohol']::text[],ARRAY['allylic_ch']::text[]),
  (752,86.134,0,17.07,1.2314,ARRAY['aldehyde']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (753,136.15,0,37.3,1.3137,ARRAY['benzene_ring','carboxylic_acid']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (754,154.253,0,20.23,2.5037,ARRAY['alcohol','alkene']::text[],ARRAY['allylic_ch']::text[]),
  (755,126.199,0,20.23,1.8912,ARRAY['alcohol','alkene','primary_alcohol']::text[],ARRAY['allylic_ch','bis_allylic_ch']::text[]),
  (756,154.253,0,17.07,2.6477,ARRAY['ketone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (757,108.14,0,20.23,1.7006,ARRAY['benzene_ring','phenol']::text[],ARRAY['phenolic_antioxidant']::text[]),
  (760,125.171,0,26.03,2.0172,ARRAY['oxazole']::text[],NULL),
  (762,282.468,0,37.3,6.1085,ARRAY['alkene','carboxylic_acid']::text[],ARRAY['allylic_ch','carbonyl_electrophile']::text[]),
  (763,198.35,0,17.07,4.4963,ARRAY['ketone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (764,100.117,0,26.3,0.7119,ARRAY['ester','ether','lactone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (765,150.177,0,29.46,2.0438,ARRAY['alkene','benzene_ring','ether','phenol']::text[],ARRAY['phenolic_antioxidant']::text[]),
  (766,104.174,0,17.07,0.9384,ARRAY['aldehyde','thioether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (767,198.306,0,26.3,3.4426,ARRAY['ester','ether','lactone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (769,136.198,0,25.78,1.6014,ARRAY['pyrazine']::text[],NULL),
  (770,108.231,0,0.0,1.6699,ARRAY['thioether']::text[],NULL),
  (771,142.198,0,29.6,1.533,ARRAY['aldehyde','ether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (772,124.139,0,30.21,1.4111,ARRAY['furan','ketone']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (774,140.207,0,17.07,2.2591,ARRAY['ketone','thioether','thiophene']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (775,140.207,0,13.14,2.2362,ARRAY['furan','thioether']::text[],NULL),
  (776,149.237,0,12.89,2.8143,ARRAY['pyridine']::text[],NULL),
  (778,226.322,0,26.28,4.2888,ARRAY['disulfide','furan']::text[],ARRAY['disulfide_bridge']::text[]),
  (780,140.226,0,17.07,2.7119,ARRAY['aldehyde','alkene']::text[],ARRAY['allylic_ch','carbonyl_electrophile']::text[]),
  (781,135.142,-1,40.13,-0.021,ARRAY['benzene_ring']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (782,144.214,0,26.3,2.1298,ARRAY['ester','ether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (783,140.138,0,39.44,1.3427,ARRAY['ester','ether','furan']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (785,44.053,0,17.07,0.2052,ARRAY['aldehyde']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (786,73.12,0,12.36,0.719,NULL,NULL),
  (787,140.211,0,25.78,1.5069,ARRAY['pyrazine','thioether']::text[],NULL),
  (788,158.241,0,26.3,2.5183,ARRAY['ester','ether']::text[],ARRAY['carbonyl_electrophile']::text[]),
  (789,126.199,0,17.07,2.3218,ARRAY['alkene','ketone']::text[],ARRAY['allylic_ch','carbonyl_electrophile']::text[]),
  (790,178.231,0,18.46,2.4323,ARRAY['alkene','benzene_ring','ether']::text[],ARRAY['allylic_ch']::text[]),
  (791,258.39,0,25.78,4.1347,ARRAY['benzene_ring','pyrazine','thioether']::text[],NULL),
  (793,90.191,0,0.0,1.7594,ARRAY['thioether']::text[],NULL),
  (795,134.182,0,25.78,1.5263,ARRAY['pyrazine']::text[],NULL),
  (796,112.172,0,17.07,1.9317,ARRAY['aldehyde','alkene']::text[],ARRAY['allylic_ch','carbonyl_electrophile']::text[]),
  (798,98.17,0,0.0,2.0565,ARRAY['thioether','thiophene']::text[],NULL),
  (799,60.121,0,0.0,0.7332,ARRAY['thioether']::text[],NULL)
) AS v(id, mw, charge, tpsa, logp, fg, rg)
 WHERE m.id = v.id;

-- ---------------------------------------------------------------------------
-- §2  Odour thresholds — derived in pure SQL from `meaty_volatile_library`
--     (Sohail et al., 2022 review, Tables 1-2). Unambiguous normalized-name
--     matches only: a compound whose MVL entries disagree on the threshold is
--     skipped rather than arbitrated. Expect 110 rows.
-- ---------------------------------------------------------------------------
WITH mv AS (
    SELECT lower(regexp_replace(compound, '[ ,\-]', '', 'g')) AS norm,
           min(entry_no)                  AS entry_no,
           min(NULLIF(odor_threshold,'')) AS thr,
           min(source_table)              AS tbl,
           min(source_pdf)                AS pdf
      FROM meaty_volatile_library
     GROUP BY 1
    HAVING count(DISTINCT COALESCE(odor_threshold, '')) = 1
)
UPDATE molecules m
   SET odor_threshold_raw = mv.thr,
       updated_at         = now()
  FROM mv
 WHERE lower(regexp_replace(m.name, '[ ,\-]', '', 'g')) = mv.norm
   AND mv.thr IS NOT NULL
   AND NOT m.is_junk;

-- ---------------------------------------------------------------------------
-- §3a  Provenance rows for the structure-derived descriptors (6 x 590 = 3,540).
--      Generated from §1, not pasted.
-- ---------------------------------------------------------------------------
INSERT INTO molecule_properties
    (molecule_id, property, value_raw, value_num, unit_raw, unit_norm,
     derivation, method, source_ref, confidence, flags)
SELECT m.id, p.property, p.value_raw, p.value_num, p.unit_raw, p.unit_norm,
       'system_derived', p.method, 'rdkit:2026.03.5', p.confidence, p.flags
  FROM molecules m
  CROSS JOIN LATERAL (VALUES
    ('molecular_weight',  m.molecular_weight::text,              m.molecular_weight,
     'g/mol'::text, 'g/mol'::text,
     'RDKit Descriptors.MolWt (2026.03.5)',   1.00, NULL::text[]),
    ('formal_charge',     m.formal_charge::text,                 m.formal_charge::numeric,
     NULL, NULL,
     'RDKit GetFormalCharge (2026.03.5)',     1.00, NULL),
    ('tpsa',              m.tpsa::text,                          m.tpsa,
     'A^2', 'A^2',
     'RDKit CalcTPSA (2026.03.5)',            1.00, ARRAY['polarity_proxy']),
    -- Crippen logP is an ESTIMATOR. Flagged and down-weighted so retrieval can
    -- never quote it as a measured partition coefficient.
    ('logp',              m.logp::text,                          m.logp,
     'log10 octanol/water', 'log10 octanol/water',
     'RDKit Crippen.MolLogP (2026.03.5)',     0.60, ARRAY['estimated_not_measured']),
    ('functional_groups', array_to_string(m.functional_groups, ','), NULL,
     NULL, NULL,
     'SMARTS substructure match (27 patterns)', 0.95, NULL),
    ('reactive_groups',   array_to_string(m.reactive_groups, ','),   NULL,
     NULL, NULL,
     'SMARTS substructure match (9 patterns)',  0.95, NULL)
  ) AS p(property, value_raw, value_num, unit_raw, unit_norm, method, confidence, flags)
 WHERE m.molecular_weight IS NOT NULL
ON CONFLICT (molecule_id, property, COALESCE(source_ref, '')) DO UPDATE SET
    value_raw = EXCLUDED.value_raw, value_num  = EXCLUDED.value_num,
    unit_raw  = EXCLUDED.unit_raw,  unit_norm  = EXCLUDED.unit_norm,
    derivation= EXCLUDED.derivation, method    = EXCLUDED.method,
    confidence= EXCLUDED.confidence, flags     = EXCLUDED.flags;

-- ---------------------------------------------------------------------------
-- §3b  Provenance rows for the odour thresholds (110).
--      Normalization rule: a value becomes numeric ONLY if it is a bare number.
--      "4.6 ~ 5.0, paraffin oil" -> value_num NULL, flags
--      {matrix_qualified, range_not_point_value, unit_not_stated_in_source},
--      conditions {"matrix":"paraffin oil"}. Nothing is converted or guessed.
-- ---------------------------------------------------------------------------
WITH mv AS (
    SELECT lower(regexp_replace(compound, '[ ,\-]', '', 'g')) AS norm,
           min(entry_no)                  AS entry_no,
           min(NULLIF(odor_threshold,'')) AS thr,
           min(source_table)              AS tbl,
           min(source_pdf)                AS pdf
      FROM meaty_volatile_library
     GROUP BY 1
    HAVING count(DISTINCT COALESCE(odor_threshold, '')) = 1
),
matched AS (
    SELECT m.id AS molecule_id, mv.entry_no, mv.thr, mv.tbl, mv.pdf,
           btrim(split_part(mv.thr, ',', 1)) AS head,
           CASE WHEN strpos(mv.thr, ',') > 0
                THEN btrim(substr(mv.thr, strpos(mv.thr, ',') + 1)) END AS matrix
      FROM molecules m
      JOIN mv ON lower(regexp_replace(m.name, '[ ,\-]', '', 'g')) = mv.norm
     WHERE mv.thr IS NOT NULL AND NOT m.is_junk
),
parsed AS (
    SELECT *,
           (head ~* 'greater than|less than|[<>]')            AS is_limit,
           -- NB: the character class must include the EN and EM dashes; the MVL
           -- writes ranges as "4.6-9" (en dash), not a plain ASCII hyphen.
           (head ~ '[~–—-]' OR head ~* '\yto\y')              AS looks_range
      FROM matched
)
INSERT INTO molecule_properties
    (molecule_id, property, value_raw, value_num, unit_raw, unit_norm,
     derivation, method, conditions, source_ref, source_location, confidence, flags)
SELECT molecule_id,
       'odor_threshold',
       thr,
       CASE WHEN NOT is_limit AND NOT looks_range AND head ~ '^[0-9]+(\.[0-9]+)?$'
            THEN head::numeric END,
       NULL, NULL,                       -- unit deliberately not asserted
       'reported',
       'literature compilation (odour threshold as tabulated)',
       CASE WHEN matrix IS NOT NULL THEN jsonb_build_object('matrix', matrix) END,
       'mvl:entry_no=' || entry_no,
       pdf || ' · ' || tbl,
       0.80,
       array_remove(ARRAY[
           CASE WHEN matrix IS NOT NULL              THEN 'matrix_qualified'      END,
           CASE WHEN is_limit                        THEN 'limit_not_point_value' END,
           CASE WHEN NOT is_limit AND looks_range    THEN 'range_not_point_value' END,
           'unit_not_stated_in_source'
       ], NULL)
  FROM parsed
ON CONFLICT (molecule_id, property, COALESCE(source_ref, '')) DO UPDATE SET
    value_raw  = EXCLUDED.value_raw,  value_num       = EXCLUDED.value_num,
    derivation = EXCLUDED.derivation, method          = EXCLUDED.method,
    conditions = EXCLUDED.conditions, source_location = EXCLUDED.source_location,
    confidence = EXCLUDED.confidence, flags           = EXCLUDED.flags;

COMMIT;

-- ---------------------------------------------------------------------------
-- §4  Verification — run these; the expected numbers are in the comments.
-- ---------------------------------------------------------------------------
-- 799
SELECT count(*) AS molecules_rows FROM molecules;

-- molecular_weight 590 | formal_charge 590 | tpsa 590 | logp 590
-- functional_groups 578 | reactive_groups 350 | odor_threshold_raw 110
--   (fg < 590 and rg < 590 are CORRECT: 12 molecules match none of the 27
--    functional-group SMARTS and 240 carry no flavour-chemistry reactive handle —
--    e.g. saturated alkanes. An empty match is stored as NULL, not as an empty array.)
-- pka/isoelectric_point/redox_potential_v/sequence_conformation/
-- boiling_point/vapor_pressure/odor_threshold_ppb/oav/color = 0 (by design)
SELECT count(molecular_weight) mw, count(formal_charge) chg, count(tpsa) tpsa,
       count(logp) logp, count(functional_groups) fg, count(reactive_groups) rg,
       count(odor_threshold_raw) thr, count(pka) pka, count(oav) oav
  FROM molecules WHERE NOT is_junk;

-- 3,650 total: 6 x 590 system_derived + 110 reported
SELECT property, derivation, count(*), count(value_num) AS numeric_norm,
       round(avg(confidence), 2) AS avg_conf
  FROM molecule_properties GROUP BY 1, 2 ORDER BY 1;

-- estimated_not_measured 590 | polarity_proxy 590 |
-- unit_not_stated_in_source 110 | range_not_point_value 12 | matrix_qualified 5
SELECT unnest(flags) AS flag, count(*) FROM molecule_properties GROUP BY 1 ORDER BY 2 DESC;

-- INDEPENDENT CROSS-CHECK: RDKit MW vs the moldedup schema's own MW.
-- Expect 136 compared, 0 mismatched. A non-zero mismatch means §1 is stale.
SELECT count(*) AS compared,
       count(*) FILTER (WHERE abs(m.molecular_weight - d.molecular_weight) > 0.5) AS mismatched
  FROM molecules m
  JOIN moldedup.molecules d ON d.inchikey = m.inchikey
 WHERE m.molecular_weight IS NOT NULL AND d.molecular_weight IS NOT NULL;
