-- =============================================================================
-- 0007 — Drop unused patent/assessment columns from `sources` (Lior request).
-- All 7 columns were 100% empty (0 non-null of 818). They were referenced only by
-- the unused analytical view v_intelligence_record (no code/objects depend on it),
-- so that view is rebuilt WITHOUT the 4 empty columns it listed. Applied to Neon 2026-07-21.
-- =============================================================================
BEGIN;
DROP VIEW IF EXISTS v_intelligence_record;
ALTER TABLE sources
    DROP COLUMN IF EXISTS patent_number,
    DROP COLUMN IF EXISTS assignee,
    DROP COLUMN IF EXISTS jurisdiction,
    DROP COLUMN IF EXISTS species_reference,
    DROP COLUMN IF EXISTS evidence_strength,
    DROP COLUMN IF EXISTS actionability,
    DROP COLUMN IF EXISTS usefulness_tags;
CREATE VIEW v_intelligence_record AS
 SELECT id AS source_id,
    name AS title,
    source_type,
    year,
    ( SELECT array_agg(pc.name ORDER BY pc.name) AS array_agg
           FROM source_product_contexts spc
             JOIN product_contexts pc ON pc.id = spc.context_id
          WHERE spc.source_id = s.id AND spc.role = 'primary'::text) AS product_context,
    ( SELECT array_agg(pc.name ORDER BY pc.name) AS array_agg
           FROM source_product_contexts spc
             JOIN product_contexts pc ON pc.id = spc.context_id
          WHERE spc.source_id = s.id AND spc.role = 'alternative'::text) AS alternative_product,
    ( SELECT array_agg(t.name ORDER BY t.name) AS array_agg
           FROM source_topics st
             JOIN topics t ON t.id = st.topic_id
          WHERE st.source_id = s.id AND t.root_branch = 'flavor_chemistry'::text) AS chemistry_topics,
    ( SELECT array_agg(r.name ORDER BY r.name) AS array_agg
           FROM source_reactions sr
             JOIN reactions r ON r.id = sr.reaction_id
          WHERE sr.source_id = s.id) AS reactions,
    ( SELECT array_agg(am.name ORDER BY am.name) AS array_agg
           FROM source_methods sm
             JOIN analytical_methods am ON am.id = sm.method_id
          WHERE sm.source_id = s.id) AS analytical_methods,
    ( SELECT array_agg(sa.name ORDER BY sa.name) AS array_agg
           FROM source_sensory_attributes ssa
             JOIN sensory_attributes sa ON sa.id = ssa.attribute_id
          WHERE ssa.source_id = s.id) AS sensory_attributes,
    ( SELECT array_agg(m.name ORDER BY m.name) AS array_agg
           FROM source_molecules sm
             JOIN molecules m ON m.id = sm.molecule_id
          WHERE sm.source_id = s.id) AS molecules,
    ( SELECT array_agg(i.name ORDER BY i.name) AS array_agg
           FROM source_ingredients si
             JOIN ingredients i ON i.id = si.ingredient_id
          WHERE si.source_id = s.id) AS ingredients,
    ( SELECT array_agg(format('%s @ %s°C, %s min'::text, p.cooking_method, p.temperature_c, p.time_min)) AS array_agg
           FROM processes p
          WHERE p.source_id = s.id) AS process_summary,
    ( SELECT array_agg(format('protein=%s, fat=%s'::text, mp.protein_source, mp.fat_source)) AS array_agg
           FROM matrix_profiles mp
          WHERE mp.source_id = s.id) AS matrix_summary
   FROM sources s;
;
COMMIT;
