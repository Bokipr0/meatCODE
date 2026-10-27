# MeatCODE schema reference

_Last updated: 2026-10-26 · Codex / Advisory · read-only live inspection._

This inventory describes inspected production and dev branches. It is metadata documentation, not a database backup or executable migration. The JSON includes all constraints, indexes and view definitions. No user rows, connection strings or API keys are included.

## production

49 base tables; 16 views. Extensions: pg_session_jwt 0.5.0, plpgsql 1.0

### public.analytical_methods

Type: BASE TABLE; rows: 13

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| slug | text | NO |
| name | text | NO |
| category | text | NO |
| description | text | YES |
| created_at | timestamptz | YES |

- PRIMARY KEY (id)
- UNIQUE (slug)

### public.claim_experiments

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| claim_id | int8 | NO |
| experiment_id | int8 | NO |

- FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE
- FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE CASCADE
- PRIMARY KEY (claim_id, experiment_id)

### public.claim_molecules

Type: BASE TABLE; rows: 41

| Column | Type | Nullable |
|---|---|---|
| claim_id | int8 | NO |
| molecule_id | int8 | NO |

- FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE
- FOREIGN KEY (molecule_id) REFERENCES molecules(id) ON DELETE CASCADE
- PRIMARY KEY (claim_id, molecule_id)

### public.claim_reactions

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| claim_id | int8 | NO |
| reaction_id | int8 | NO |

- FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE
- PRIMARY KEY (claim_id, reaction_id)
- FOREIGN KEY (reaction_id) REFERENCES reactions(id) ON DELETE CASCADE

### public.claim_sensory_attributes

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| claim_id | int8 | NO |
| attribute_id | int8 | NO |

- FOREIGN KEY (attribute_id) REFERENCES sensory_attributes(id) ON DELETE CASCADE
- FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE
- PRIMARY KEY (claim_id, attribute_id)

### public.claim_sources

Type: BASE TABLE; rows: 69

| Column | Type | Nullable |
|---|---|---|
| claim_id | int8 | NO |
| source_id | int8 | NO |

- FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE
- PRIMARY KEY (claim_id, source_id)
- FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE

### public.claim_topics

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| claim_id | int8 | NO |
| topic | text | NO |

- FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE
- PRIMARY KEY (claim_id, topic)

### public.claim_topics_v2

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| claim_id | int8 | NO |
| topic_id | int8 | NO |

- FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE
- PRIMARY KEY (claim_id, topic_id)
- FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE

### public.claims

Type: BASE TABLE; rows: 45

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| claim_text | text | NO |
| stance | claim_stance | NO |
| confidence | numeric | YES |
| notes | text | YES |
| created_at | timestamptz | YES |
| updated_at | timestamptz | YES |
| external_id | text | YES |
| evidence_snippet | text | YES |
| external_key | text | YES |

- CHECK (((confidence IS NULL) OR ((confidence >= (0)::numeric) AND (confidence <= (1)::numeric))))
- PRIMARY KEY (id)

### public.experiment_ingredients

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| experiment_id | int8 | NO |
| ingredient_id | int8 | NO |
| amount_pct | numeric | YES |
| notes | text | YES |

- FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE CASCADE
- FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE
- PRIMARY KEY (experiment_id, ingredient_id)

### public.experiment_methods

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| experiment_id | int8 | NO |
| method_id | int8 | NO |

- FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE CASCADE
- FOREIGN KEY (method_id) REFERENCES analytical_methods(id) ON DELETE CASCADE
- PRIMARY KEY (experiment_id, method_id)

### public.experiment_molecules

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| experiment_id | int8 | NO |
| molecule_id | int8 | NO |
| detected | bool | YES |
| concentration | numeric | YES |
| concentration_unit | text | YES |
| notes | text | YES |

- FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE CASCADE
- FOREIGN KEY (molecule_id) REFERENCES molecules(id) ON DELETE CASCADE
- PRIMARY KEY (experiment_id, molecule_id)

### public.experiment_product_contexts

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| experiment_id | int8 | NO |
| context_id | int8 | NO |
| role | text | NO |

- FOREIGN KEY (context_id) REFERENCES product_contexts(id) ON DELETE CASCADE
- FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE CASCADE
- PRIMARY KEY (experiment_id, context_id, role)
- CHECK ((role = ANY (ARRAY['primary'::text, 'alternative'::text, 'reference'::text])))

### public.experiment_reactions

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| experiment_id | int8 | NO |
| reaction_id | int8 | NO |

- FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE CASCADE
- PRIMARY KEY (experiment_id, reaction_id)
- FOREIGN KEY (reaction_id) REFERENCES reactions(id) ON DELETE CASCADE

### public.experiment_sensory_attributes

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| experiment_id | int8 | NO |
| attribute_id | int8 | NO |
| intensity | numeric | YES |

- FOREIGN KEY (attribute_id) REFERENCES sensory_attributes(id) ON DELETE CASCADE
- FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE CASCADE
- PRIMARY KEY (experiment_id, attribute_id)

### public.experiments

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| source_id | int8 | NO |
| name | text | NO |
| dataset_url | text | YES |
| description | text | YES |
| notes | text | YES |
| created_at | timestamptz | YES |
| updated_at | timestamptz | YES |

- PRIMARY KEY (id)
- FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE

### public.expert_relations

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| expert_a_id | int8 | NO |
| expert_b_id | int8 | NO |
| relation_type | text | NO |
| notes | text | YES |

- CHECK ((expert_a_id <> expert_b_id))
- FOREIGN KEY (expert_a_id) REFERENCES experts(id) ON DELETE CASCADE
- FOREIGN KEY (expert_b_id) REFERENCES experts(id) ON DELETE CASCADE
- PRIMARY KEY (expert_a_id, expert_b_id, relation_type)

### public.experts

Type: BASE TABLE; rows: 3129

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| name | text | NO |
| affiliation | text | YES |
| email | text | YES |
| research_field | research_field | YES |
| outreach_status | outreach_status | NO |
| trust_tier | text | YES |
| notes | text | YES |
| created_at | timestamptz | YES |
| updated_at | timestamptz | YES |
| org_type | expert_org_type | YES |
| organization_id | int8 | YES |
| external_id | text | YES |
| country | text | YES |
| relevance_score | numeric | YES |
| h_index | int4 | YES |
| total_papers | int4 | YES |
| orcid | text | YES |
| key_research | text | YES |
| keywords | text | YES |
| linkedin_url | text | YES |
| knowledge_gaps | text | YES |
| openalex_id | text | YES |
| dimensions_id | text | YES |
| current_org | text | YES |
| dimensions_topics | _text | YES |

- PRIMARY KEY (id)
- FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE SET NULL

### public.ingest_log

Type: BASE TABLE; rows: 6

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| started_at | timestamptz | YES |
| source | text | NO |
| topic_slug | text | YES |
| inserted_experts | int4 | YES |
| updated_experts | int4 | YES |
| inserted_sources | int4 | YES |
| updated_sources | int4 | YES |
| notes | text | YES |

- PRIMARY KEY (id)

### public.ingredient_molecules

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| ingredient_id | int8 | NO |
| molecule_id | int8 | NO |
| proportion_pct | numeric | YES |
| notes | text | YES |

- FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE
- FOREIGN KEY (molecule_id) REFERENCES molecules(id) ON DELETE CASCADE
- PRIMARY KEY (ingredient_id, molecule_id)
- CHECK (((proportion_pct IS NULL) OR ((proportion_pct >= (0)::numeric) AND (proportion_pct <= (100)::numeric))))

### public.ingredients

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| name | text | NO |
| category | ingredient_category | NO |
| supplier | text | YES |
| description | text | YES |
| created_at | timestamptz | YES |
| updated_at | timestamptz | YES |

- UNIQUE (name)
- PRIMARY KEY (id)

### public.leaf_topics

Type: VIEW; rows: view - not counted

| Column | Type | Nullable |
|---|---|---|
| id | int8 | YES |
| slug | text | YES |
| name | text | YES |
| root_branch | text | YES |
| level | int2 | YES |


### public.matrix_profiles

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| source_id | int8 | YES |
| experiment_id | int8 | YES |
| protein_source | protein_source | YES |
| fat_source | fat_source | YES |
| water_activity | numeric | YES |
| emulsion_structure | text | YES |
| gel_network | text | YES |
| fiber_structure | text | YES |
| encapsulation | text | YES |
| release_kinetics | text | YES |
| flavor_binding | text | YES |
| notes | text | YES |

- CHECK (((source_id IS NOT NULL) OR (experiment_id IS NOT NULL)))
- FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE CASCADE
- PRIMARY KEY (id)
- FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE
- CHECK (((water_activity IS NULL) OR ((water_activity >= (0)::numeric) AND (water_activity <= (1)::numeric))))

### public.meaty_volatile_library

Type: BASE TABLE; rows: 273

| Column | Type | Nullable |
|---|---|---|
| entry_no | int4 | NO |
| cas_number | text | YES |
| compound | text | NO |
| likely_process | text | YES |
| chemical_group | text | YES |
| subgroup | text | YES |
| ri_polar | numeric | YES |
| ri_non_polar | numeric | YES |
| odor_descriptor | text | YES |
| odor_threshold | text | YES |
| cooked_meats_reported | text | YES |
| source_table | text | YES |
| source_classification | text | YES |
| source_pdf | text | YES |
| notes | text | YES |
| beef_relevance_score | numeric | YES |

- PRIMARY KEY (entry_no)

### public.molecule_odours

Type: BASE TABLE; rows: 2263

| Column | Type | Nullable |
|---|---|---|
| molecule_id | int8 | NO |
| odour_id | int8 | NO |

- FOREIGN KEY (molecule_id) REFERENCES molecules(id) ON DELETE CASCADE
- FOREIGN KEY (odour_id) REFERENCES odours(id) ON DELETE CASCADE
- PRIMARY KEY (molecule_id, odour_id)

### public.molecule_properties

Type: BASE TABLE; rows: 3650

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| molecule_id | int8 | NO |
| property | text | NO |
| value_raw | text | YES |
| value_num | numeric | YES |
| unit_raw | text | YES |
| unit_norm | text | YES |
| basis | text | YES |
| uncertainty | text | YES |
| replicate_count | int4 | YES |
| derivation | text | NO |
| method | text | YES |
| conditions | jsonb | YES |
| source_id | int8 | YES |
| source_ref | text | YES |
| source_location | text | YES |
| confidence | numeric | YES |
| flags | _text | YES |
| created_at | timestamptz | NO |

- CHECK (((confidence >= (0)::numeric) AND (confidence <= (1)::numeric)))
- CHECK ((derivation = ANY (ARRAY['reported'::text, 'author_derived'::text, 'graph_estimated'::text, 'system_derived'::text])))
- FOREIGN KEY (molecule_id) REFERENCES molecules(id) ON DELETE CASCADE
- PRIMARY KEY (id)
- FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE SET NULL

### public.molecule_role_tags

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| molecule_id | int8 | NO |
| source_id | int8 | YES |
| experiment_id | int8 | YES |
| role | molecule_role | NO |
| notes | text | YES |

- CHECK (((source_id IS NOT NULL) OR (experiment_id IS NOT NULL)))
- FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE CASCADE
- FOREIGN KEY (molecule_id) REFERENCES molecules(id) ON DELETE CASCADE
- PRIMARY KEY (id)
- FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE

### public.molecule_sensory_attributes

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| molecule_id | int8 | NO |
| attribute_id | int8 | NO |

- FOREIGN KEY (attribute_id) REFERENCES sensory_attributes(id) ON DELETE CASCADE
- FOREIGN KEY (molecule_id) REFERENCES molecules(id) ON DELETE CASCADE
- PRIMARY KEY (molecule_id, attribute_id)

### public.molecules

Type: BASE TABLE; rows: 799

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| name | text | NO |
| category | text | YES |
| cas_number | text | YES |
| pubchem_cid | text | YES |
| notes | text | YES |
| created_at | timestamptz | YES |
| updated_at | timestamptz | YES |
| external_id | text | YES |
| melting_point | text | YES |
| water_solubility | text | YES |
| compound_id | text | YES |
| odour_source_url | text | YES |
| external_key | text | YES |
| found_in | _text | YES |
| pathway_step | text | YES |
| is_junk | bool | NO |
| inchikey | text | YES |
| smiles | text | YES |
| molecular_formula | text | YES |
| id_match_method | text | YES |
| id_needs_review | bool | NO |
| molecular_weight | numeric | YES |
| formal_charge | int4 | YES |
| functional_groups | _text | YES |
| reactive_groups | _text | YES |
| pka | numeric | YES |
| isoelectric_point | numeric | YES |
| tpsa | numeric | YES |
| logp | numeric | YES |
| redox_potential_v | numeric | YES |
| sequence_conformation | text | YES |
| boiling_point | text | YES |
| vapor_pressure | text | YES |
| odor_threshold_raw | text | YES |
| odor_threshold_ppb | numeric | YES |
| oav | numeric | YES |
| color | text | YES |

- PRIMARY KEY (id)

### public.odours

Type: BASE TABLE; rows: 639

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| name | text | NO |
| notes | text | YES |
| created_at | timestamptz | YES |
| updated_at | timestamptz | YES |
| external_id | text | YES |
| odour_category | text | YES |

- UNIQUE (name)
- PRIMARY KEY (id)

### public.organizations

Type: BASE TABLE; rows: 37

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| name | text | NO |
| org_type | expert_org_type | NO |
| country | text | YES |
| website | text | YES |
| description | text | YES |
| created_at | timestamptz | YES |
| updated_at | timestamptz | YES |

- UNIQUE (name)
- PRIMARY KEY (id)

### public.parent_topics

Type: VIEW; rows: view - not counted

| Column | Type | Nullable |
|---|---|---|
| id | int8 | YES |
| slug | text | YES |
| name | text | YES |
| root_branch | text | YES |
| level | int2 | YES |


### public.processes

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| source_id | int8 | YES |
| experiment_id | int8 | YES |
| cooking_method | cooking_method | YES |
| step_label | text | YES |
| temperature_c | numeric | YES |
| time_min | numeric | YES |
| ph | numeric | YES |
| water_activity | numeric | YES |
| oxygen_available | bool | YES |
| fat_phase_pct | numeric | YES |
| aqueous_phase_pct | numeric | YES |
| notes | text | YES |

- CHECK (((source_id IS NOT NULL) OR (experiment_id IS NOT NULL)))
- FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE CASCADE
- CHECK (((ph IS NULL) OR ((ph >= (0)::numeric) AND (ph <= (14)::numeric))))
- PRIMARY KEY (id)
- FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE
- CHECK (((water_activity IS NULL) OR ((water_activity >= (0)::numeric) AND (water_activity <= (1)::numeric))))

### public.product_contexts

Type: BASE TABLE; rows: 10

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| slug | text | NO |
| name | text | NO |
| category | text | NO |
| description | text | YES |
| created_at | timestamptz | YES |

- PRIMARY KEY (id)
- UNIQUE (slug)

### public.reaction_participants

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| reaction_id | int8 | NO |
| molecule_id | int8 | YES |
| ingredient_id | int8 | YES |
| role | participant_role | NO |
| notes | text | YES |

- CHECK ((((molecule_id IS NOT NULL) AND (ingredient_id IS NULL)) OR ((molecule_id IS NULL) AND (ingredient_id IS NOT NULL))))
- FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE
- FOREIGN KEY (molecule_id) REFERENCES molecules(id) ON DELETE CASCADE
- PRIMARY KEY (id)
- FOREIGN KEY (reaction_id) REFERENCES reactions(id) ON DELETE CASCADE

### public.reaction_topics

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| reaction_id | int8 | NO |
| topic_id | int8 | NO |

- PRIMARY KEY (reaction_id, topic_id)
- FOREIGN KEY (reaction_id) REFERENCES reactions(id) ON DELETE CASCADE
- FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE

### public.reactions

Type: BASE TABLE; rows: 8

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| slug | text | NO |
| name | text | NO |
| kind | reaction_kind | NO |
| parent_id | int8 | YES |
| description | text | YES |
| created_at | timestamptz | YES |

- FOREIGN KEY (parent_id) REFERENCES reactions(id) ON DELETE SET NULL
- PRIMARY KEY (id)
- UNIQUE (slug)

### public.sensory_attributes

Type: BASE TABLE; rows: 21

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| slug | text | NO |
| name | text | NO |
| parent_id | int8 | YES |
| is_off_note | bool | NO |
| description | text | YES |
| created_at | timestamptz | YES |

- FOREIGN KEY (parent_id) REFERENCES sensory_attributes(id) ON DELETE SET NULL
- PRIMARY KEY (id)
- UNIQUE (slug)

### public.source_audits

Type: BASE TABLE; rows: 40

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| source_id | int8 | NO |
| run_id | text | YES |
| audited_at | timestamptz | NO |
| tag_score | int4 | YES |
| relevance_score | int4 | YES |
| quality_score | int4 | YES |
| verdict | text | YES |
| tag_issues | jsonb | YES |
| notes | text | YES |
| weights_snapshot | jsonb | YES |
| audit_priority | float8 | YES |

- PRIMARY KEY (id)
- FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE
- CHECK ((verdict = ANY (ARRAY['keep'::text, 'review'::text, 'quarantine'::text])))

### public.source_experts

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| source_id | int8 | NO |
| expert_id | int8 | NO |
| role | text | NO |

- FOREIGN KEY (expert_id) REFERENCES experts(id) ON DELETE CASCADE
- PRIMARY KEY (source_id, expert_id, role)
- CHECK ((role = ANY (ARRAY['author'::text, 'corresponding'::text, 'inventor'::text, 'reviewer'::text, 'editor'::text])))
- FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE

### public.source_ingredients

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| source_id | int8 | NO |
| ingredient_id | int8 | NO |

- FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE
- PRIMARY KEY (source_id, ingredient_id)
- FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE

### public.source_methods

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| source_id | int8 | NO |
| method_id | int8 | NO |

- FOREIGN KEY (method_id) REFERENCES analytical_methods(id) ON DELETE CASCADE
- PRIMARY KEY (source_id, method_id)
- FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE

### public.source_molecules

Type: BASE TABLE; rows: 23

| Column | Type | Nullable |
|---|---|---|
| source_id | int8 | NO |
| molecule_id | int8 | NO |

- FOREIGN KEY (molecule_id) REFERENCES molecules(id) ON DELETE CASCADE
- PRIMARY KEY (source_id, molecule_id)
- FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE

### public.source_product_contexts

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| source_id | int8 | NO |
| context_id | int8 | NO |
| role | text | NO |

- FOREIGN KEY (context_id) REFERENCES product_contexts(id) ON DELETE CASCADE
- PRIMARY KEY (source_id, context_id, role)
- CHECK ((role = ANY (ARRAY['primary'::text, 'alternative'::text, 'reference'::text])))
- FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE

### public.source_reactions

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| source_id | int8 | NO |
| reaction_id | int8 | NO |

- PRIMARY KEY (source_id, reaction_id)
- FOREIGN KEY (reaction_id) REFERENCES reactions(id) ON DELETE CASCADE
- FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE

### public.source_sensory_attributes

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| source_id | int8 | NO |
| attribute_id | int8 | NO |

- FOREIGN KEY (attribute_id) REFERENCES sensory_attributes(id) ON DELETE CASCADE
- PRIMARY KEY (source_id, attribute_id)
- FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE

### public.source_tags

Type: BASE TABLE; rows: 3457

| Column | Type | Nullable |
|---|---|---|
| source_id | int8 | NO |
| tag_id | int8 | NO |

- PRIMARY KEY (source_id, tag_id)
- FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE
- FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE

### public.source_topics

Type: BASE TABLE; rows: 569

| Column | Type | Nullable |
|---|---|---|
| source_id | int8 | NO |
| topic_id | int8 | NO |

- PRIMARY KEY (source_id, topic_id)
- FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE
- FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE

### public.sources

Type: BASE TABLE; rows: 818

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| name | text | NO |
| year | int2 | YES |
| authors | text | YES |
| affiliation | text | YES |
| venue | text | YES |
| url | text | YES |
| abstract | text | YES |
| notes | text | YES |
| created_at | timestamptz | YES |
| updated_at | timestamptz | YES |
| source_type | source_type | YES |
| doi | text | YES |
| metadata | jsonb | YES |
| external_id | text | YES |
| search_query | text | YES |
| citation_count | int4 | YES |
| top_keywords | text | YES |
| external_key | text | YES |
| trust_tier | text | YES |
| composite_score | float4 | YES |
| review_status | text | YES |
| dimensions_id | text | YES |
| journal | text | YES |
| dimensions_topics | _text | YES |
| search_vec | tsvector | YES |
| priority_score | numeric | YES |
| is_review | bool | YES |
| relevance_llm | int2 | YES |
| pathway | _text | YES |
| method | _text | YES |
| sensory_descriptor | _text | YES |
| matrix | _text | YES |
| compound_class | _text | YES |
| study_type | text | YES |
| main_claim | text | YES |
| tailored_abstract | text | YES |

- PRIMARY KEY (id)

### public.tags

Type: BASE TABLE; rows: 571

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| category | text | NO |
| name | text | NO |
| slug | text | NO |
| created_at | timestamptz | YES |

- UNIQUE (category, slug)
- PRIMARY KEY (id)

### public.topic_hierarchy

Type: VIEW; rows: view - not counted

| Column | Type | Nullable |
|---|---|---|
| root_branch | text | YES |
| parent_name | text | YES |
| child_name | text | YES |
| child_slug | text | YES |


### public.topics

Type: BASE TABLE; rows: 112

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| slug | text | NO |
| name | text | NO |
| parent_id | int8 | YES |
| root_branch | text | NO |
| level | int2 | NO |
| description | text | YES |
| created_at | timestamptz | YES |

- FOREIGN KEY (parent_id) REFERENCES topics(id) ON DELETE SET NULL
- PRIMARY KEY (id)
- UNIQUE (slug)

### public.v_claim_evidence

Type: VIEW; rows: view - not counted

| Column | Type | Nullable |
|---|---|---|
| claim_id | int8 | YES |
| claim_text | text | YES |
| stance | claim_stance | YES |
| confidence | numeric | YES |
| source_id | int8 | YES |
| source_name | text | YES |
| source_type | source_type | YES |
| source_year | int2 | YES |
| molecule_id | int8 | YES |
| molecule_name | text | YES |


### public.v_experiment_record

Type: VIEW; rows: view - not counted

| Column | Type | Nullable |
|---|---|---|
| experiment_id | int8 | YES |
| experiment_name | text | YES |
| source_id | int8 | YES |
| source_name | text | YES |
| methods | _text | YES |
| sensory_attributes | _text | YES |
| molecules | _text | YES |
| process_summary | _text | YES |


### public.v_experts_3tier

Type: VIEW; rows: view - not counted

| Column | Type | Nullable |
|---|---|---|
| id | int8 | YES |
| external_id | text | YES |
| name | text | YES |
| affiliation | text | YES |
| country | text | YES |
| research_field | research_field | YES |
| h_index | int4 | YES |
| total_papers | int4 | YES |
| relevance_score | numeric | YES |
| outreach_status | outreach_status | YES |
| relevance_tier | text | YES |


### public.v_intelligence_record

Type: VIEW; rows: view - not counted

| Column | Type | Nullable |
|---|---|---|
| source_id | int8 | YES |
| title | text | YES |
| source_type | source_type | YES |
| year | int2 | YES |
| product_context | _text | YES |
| alternative_product | _text | YES |
| chemistry_topics | _text | YES |
| reactions | _text | YES |
| analytical_methods | _text | YES |
| sensory_attributes | _text | YES |
| molecules | _text | YES |
| ingredients | _text | YES |
| process_summary | _text | YES |
| matrix_summary | _text | YES |


### public.v_meaty_molecules_ranked

Type: VIEW; rows: view - not counted

| Column | Type | Nullable |
|---|---|---|
| molecule_id | int8 | YES |
| molecule_name | text | YES |
| category | text | YES |
| beef_relevance_score | numeric | YES |
| likely_process | text | YES |
| chemical_group | text | YES |
| subgroup | text | YES |
| reference_odor | text | YES |
| cooked_meats_reported | text | YES |
| my_odours | _text | YES |


### public.v_mvl_gaps

Type: VIEW; rows: view - not counted

| Column | Type | Nullable |
|---|---|---|
| entry_no | int4 | YES |
| compound | text | YES |
| cas_number | text | YES |
| likely_process | text | YES |
| chemical_group | text | YES |
| beef_relevance_score | numeric | YES |
| odor_descriptor | text | YES |


### public.v_mvl_x_molecules_by_cas

Type: VIEW; rows: view - not counted

| Column | Type | Nullable |
|---|---|---|
| entry_no | int4 | YES |
| compound | text | YES |
| cas_number | text | YES |
| beef_relevance_score | numeric | YES |
| molecule_id | int8 | YES |
| molecule_name | text | YES |


### public.v_mvl_x_molecules_by_name

Type: VIEW; rows: view - not counted

| Column | Type | Nullable |
|---|---|---|
| entry_no | int4 | YES |
| mvl_compound | text | YES |
| mvl_cas | text | YES |
| likely_process | text | YES |
| chemical_group | text | YES |
| beef_relevance_score | numeric | YES |
| mvl_odor | text | YES |
| molecule_id | int8 | YES |
| molecule_name | text | YES |
| molecule_category | text | YES |
| odour_org_uk_id | text | YES |


### public.v_mvl_x_molecules_fuzzy

Type: VIEW; rows: view - not counted

| Column | Type | Nullable |
|---|---|---|
| entry_no | int4 | YES |
| mvl_compound | text | YES |
| beef_relevance_score | numeric | YES |
| molecule_id | int8 | YES |
| molecule_name | text | YES |
| match_type | text | YES |


### public.v_precursors

Type: VIEW; rows: view - not counted

| Column | Type | Nullable |
|---|---|---|
| reaction_id | int8 | YES |
| reaction_name | text | YES |
| reaction_kind | reaction_kind | YES |
| participant_role | participant_role | YES |
| participant_name | text | YES |
| participant_type | text | YES |


### public.v_reaction_participants_named

Type: VIEW; rows: view - not counted

| Column | Type | Nullable |
|---|---|---|
| reaction_id | int8 | YES |
| reaction_name | text | YES |
| reaction_kind | reaction_kind | YES |
| participant_role | participant_role | YES |
| participant_name | text | YES |
| participant_type | text | YES |


### public.v_relevance_summary

Type: VIEW; rows: view - not counted

| Column | Type | Nullable |
|---|---|---|
| entity | text | YES |
| relevance_tier | text | YES |
| n | int8 | YES |


### public.v_sources_3tier

Type: VIEW; rows: view - not counted

| Column | Type | Nullable |
|---|---|---|
| id | int8 | YES |
| external_id | text | YES |
| name | text | YES |
| year | int2 | YES |
| venue | text | YES |
| url | text | YES |
| citation_count | int4 | YES |
| composite_score | float4 | YES |
| review_status | text | YES |
| trust_tier | text | YES |
| relevance_tier | text | YES |


## dev

56 base tables; 16 views. Extensions: pg_session_jwt 0.5.0, plpgsql 1.0, vector 0.8.0

### lightrag_demo.batches

Type: BASE TABLE; rows: 1

| Column | Type | Nullable |
|---|---|---|
| batch_id | text | NO |
| created_at | timestamptz | NO |
| embedding_model | text | NO |
| embedding_dimension | int4 | NO |
| manifest | jsonb | NO |
| review_state | text | NO |

- CHECK ((embedding_dimension = 1024))
- PRIMARY KEY (batch_id)
- CHECK ((review_state = 'extracted_demo'::text))

### lightrag_demo.chunks

Type: BASE TABLE; rows: 194

| Column | Type | Nullable |
|---|---|---|
| batch_id | text | NO |
| chunk_id | text | NO |
| document_id | text | NO |
| chunk_order | int4 | YES |

- FOREIGN KEY (batch_id, document_id) REFERENCES lightrag_demo.documents(batch_id, document_id)
- PRIMARY KEY (batch_id, chunk_id)

### lightrag_demo.documents

Type: BASE TABLE; rows: 3

| Column | Type | Nullable |
|---|---|---|
| batch_id | text | NO |
| document_id | text | NO |
| source_id | int4 | NO |
| doi | text | NO |

- FOREIGN KEY (batch_id) REFERENCES lightrag_demo.batches(batch_id)
- PRIMARY KEY (batch_id, document_id)
- FOREIGN KEY (source_id) REFERENCES sources(id)

### lightrag_demo.embeddings

Type: BASE TABLE; rows: 7582

| Column | Type | Nullable |
|---|---|---|
| batch_id | text | NO |
| item_id | text | NO |
| kind | text | NO |
| entity_id | text | YES |
| relation_id | text | YES |
| content | text | NO |
| content_sha256 | text | NO |
| embedding | vector | NO |
| search_vec | tsvector | YES |

- FOREIGN KEY (batch_id, entity_id) REFERENCES lightrag_demo.entities(batch_id, entity_id)
- FOREIGN KEY (batch_id) REFERENCES lightrag_demo.batches(batch_id)
- FOREIGN KEY (batch_id, relation_id) REFERENCES lightrag_demo.relations(batch_id, relation_id)
- CHECK ((((kind = 'entity'::text) AND (entity_id IS NOT NULL) AND (relation_id IS NULL)) OR ((kind = 'relation'::text) AND (relation_id IS NOT NULL) AND (entity_id IS NULL))))
- CHECK ((kind = ANY (ARRAY['entity'::text, 'relation'::text])))
- PRIMARY KEY (batch_id, item_id)

### lightrag_demo.entities

Type: BASE TABLE; rows: 3418

| Column | Type | Nullable |
|---|---|---|
| batch_id | text | NO |
| entity_id | text | NO |
| entity_type | text | YES |
| description | text | NO |

- FOREIGN KEY (batch_id) REFERENCES lightrag_demo.batches(batch_id)
- PRIMARY KEY (batch_id, entity_id)

### lightrag_demo.evidence

Type: BASE TABLE; rows: 8932

| Column | Type | Nullable |
|---|---|---|
| batch_id | text | NO |
| item_id | text | NO |
| chunk_id | text | NO |

- FOREIGN KEY (batch_id, chunk_id) REFERENCES lightrag_demo.chunks(batch_id, chunk_id)
- FOREIGN KEY (batch_id, item_id) REFERENCES lightrag_demo.embeddings(batch_id, item_id)
- PRIMARY KEY (batch_id, item_id, chunk_id)

### lightrag_demo.relations

Type: BASE TABLE; rows: 4164

| Column | Type | Nullable |
|---|---|---|
| batch_id | text | NO |
| relation_id | text | NO |
| source_entity | text | NO |
| target_entity | text | NO |
| description | text | NO |
| keywords | text | YES |
| weight | float8 | YES |

- FOREIGN KEY (batch_id) REFERENCES lightrag_demo.batches(batch_id)
- FOREIGN KEY (batch_id, source_entity) REFERENCES lightrag_demo.entities(batch_id, entity_id)
- FOREIGN KEY (batch_id, target_entity) REFERENCES lightrag_demo.entities(batch_id, entity_id)
- PRIMARY KEY (batch_id, relation_id)

### public.analytical_methods

Type: BASE TABLE; rows: 13

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| slug | text | NO |
| name | text | NO |
| category | text | NO |
| description | text | YES |
| created_at | timestamptz | YES |

- PRIMARY KEY (id)
- UNIQUE (slug)

### public.claim_experiments

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| claim_id | int8 | NO |
| experiment_id | int8 | NO |

- FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE
- FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE CASCADE
- PRIMARY KEY (claim_id, experiment_id)

### public.claim_molecules

Type: BASE TABLE; rows: 41

| Column | Type | Nullable |
|---|---|---|
| claim_id | int8 | NO |
| molecule_id | int8 | NO |

- FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE
- FOREIGN KEY (molecule_id) REFERENCES molecules(id) ON DELETE CASCADE
- PRIMARY KEY (claim_id, molecule_id)

### public.claim_reactions

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| claim_id | int8 | NO |
| reaction_id | int8 | NO |

- FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE
- PRIMARY KEY (claim_id, reaction_id)
- FOREIGN KEY (reaction_id) REFERENCES reactions(id) ON DELETE CASCADE

### public.claim_sensory_attributes

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| claim_id | int8 | NO |
| attribute_id | int8 | NO |

- FOREIGN KEY (attribute_id) REFERENCES sensory_attributes(id) ON DELETE CASCADE
- FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE
- PRIMARY KEY (claim_id, attribute_id)

### public.claim_sources

Type: BASE TABLE; rows: 69

| Column | Type | Nullable |
|---|---|---|
| claim_id | int8 | NO |
| source_id | int8 | NO |

- FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE
- PRIMARY KEY (claim_id, source_id)
- FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE

### public.claim_topics

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| claim_id | int8 | NO |
| topic | text | NO |

- FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE
- PRIMARY KEY (claim_id, topic)

### public.claim_topics_v2

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| claim_id | int8 | NO |
| topic_id | int8 | NO |

- FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE
- PRIMARY KEY (claim_id, topic_id)
- FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE

### public.claims

Type: BASE TABLE; rows: 45

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| claim_text | text | NO |
| stance | claim_stance | NO |
| confidence | numeric | YES |
| notes | text | YES |
| created_at | timestamptz | YES |
| updated_at | timestamptz | YES |
| external_id | text | YES |
| evidence_snippet | text | YES |
| external_key | text | YES |

- CHECK (((confidence IS NULL) OR ((confidence >= (0)::numeric) AND (confidence <= (1)::numeric))))
- PRIMARY KEY (id)

### public.experiment_ingredients

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| experiment_id | int8 | NO |
| ingredient_id | int8 | NO |
| amount_pct | numeric | YES |
| notes | text | YES |

- FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE CASCADE
- FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE
- PRIMARY KEY (experiment_id, ingredient_id)

### public.experiment_methods

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| experiment_id | int8 | NO |
| method_id | int8 | NO |

- FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE CASCADE
- FOREIGN KEY (method_id) REFERENCES analytical_methods(id) ON DELETE CASCADE
- PRIMARY KEY (experiment_id, method_id)

### public.experiment_molecules

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| experiment_id | int8 | NO |
| molecule_id | int8 | NO |
| detected | bool | YES |
| concentration | numeric | YES |
| concentration_unit | text | YES |
| notes | text | YES |

- FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE CASCADE
- FOREIGN KEY (molecule_id) REFERENCES molecules(id) ON DELETE CASCADE
- PRIMARY KEY (experiment_id, molecule_id)

### public.experiment_product_contexts

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| experiment_id | int8 | NO |
| context_id | int8 | NO |
| role | text | NO |

- FOREIGN KEY (context_id) REFERENCES product_contexts(id) ON DELETE CASCADE
- FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE CASCADE
- PRIMARY KEY (experiment_id, context_id, role)
- CHECK ((role = ANY (ARRAY['primary'::text, 'alternative'::text, 'reference'::text])))

### public.experiment_reactions

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| experiment_id | int8 | NO |
| reaction_id | int8 | NO |

- FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE CASCADE
- PRIMARY KEY (experiment_id, reaction_id)
- FOREIGN KEY (reaction_id) REFERENCES reactions(id) ON DELETE CASCADE

### public.experiment_sensory_attributes

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| experiment_id | int8 | NO |
| attribute_id | int8 | NO |
| intensity | numeric | YES |

- FOREIGN KEY (attribute_id) REFERENCES sensory_attributes(id) ON DELETE CASCADE
- FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE CASCADE
- PRIMARY KEY (experiment_id, attribute_id)

### public.experiments

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| source_id | int8 | NO |
| name | text | NO |
| dataset_url | text | YES |
| description | text | YES |
| notes | text | YES |
| created_at | timestamptz | YES |
| updated_at | timestamptz | YES |

- PRIMARY KEY (id)
- FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE

### public.expert_relations

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| expert_a_id | int8 | NO |
| expert_b_id | int8 | NO |
| relation_type | text | NO |
| notes | text | YES |

- CHECK ((expert_a_id <> expert_b_id))
- FOREIGN KEY (expert_a_id) REFERENCES experts(id) ON DELETE CASCADE
- FOREIGN KEY (expert_b_id) REFERENCES experts(id) ON DELETE CASCADE
- PRIMARY KEY (expert_a_id, expert_b_id, relation_type)

### public.experts

Type: BASE TABLE; rows: 3129

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| name | text | NO |
| affiliation | text | YES |
| email | text | YES |
| research_field | research_field | YES |
| outreach_status | outreach_status | NO |
| trust_tier | text | YES |
| notes | text | YES |
| created_at | timestamptz | YES |
| updated_at | timestamptz | YES |
| org_type | expert_org_type | YES |
| organization_id | int8 | YES |
| external_id | text | YES |
| country | text | YES |
| relevance_score | numeric | YES |
| h_index | int4 | YES |
| total_papers | int4 | YES |
| orcid | text | YES |
| key_research | text | YES |
| keywords | text | YES |
| linkedin_url | text | YES |
| knowledge_gaps | text | YES |
| openalex_id | text | YES |
| dimensions_id | text | YES |
| current_org | text | YES |
| dimensions_topics | _text | YES |

- PRIMARY KEY (id)
- FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE SET NULL

### public.ingest_log

Type: BASE TABLE; rows: 6

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| started_at | timestamptz | YES |
| source | text | NO |
| topic_slug | text | YES |
| inserted_experts | int4 | YES |
| updated_experts | int4 | YES |
| inserted_sources | int4 | YES |
| updated_sources | int4 | YES |
| notes | text | YES |

- PRIMARY KEY (id)

### public.ingredient_molecules

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| ingredient_id | int8 | NO |
| molecule_id | int8 | NO |
| proportion_pct | numeric | YES |
| notes | text | YES |

- FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE
- FOREIGN KEY (molecule_id) REFERENCES molecules(id) ON DELETE CASCADE
- PRIMARY KEY (ingredient_id, molecule_id)
- CHECK (((proportion_pct IS NULL) OR ((proportion_pct >= (0)::numeric) AND (proportion_pct <= (100)::numeric))))

### public.ingredients

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| name | text | NO |
| category | ingredient_category | NO |
| supplier | text | YES |
| description | text | YES |
| created_at | timestamptz | YES |
| updated_at | timestamptz | YES |

- UNIQUE (name)
- PRIMARY KEY (id)

### public.leaf_topics

Type: VIEW; rows: view - not counted

| Column | Type | Nullable |
|---|---|---|
| id | int8 | YES |
| slug | text | YES |
| name | text | YES |
| root_branch | text | YES |
| level | int2 | YES |


### public.matrix_profiles

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| source_id | int8 | YES |
| experiment_id | int8 | YES |
| protein_source | protein_source | YES |
| fat_source | fat_source | YES |
| water_activity | numeric | YES |
| emulsion_structure | text | YES |
| gel_network | text | YES |
| fiber_structure | text | YES |
| encapsulation | text | YES |
| release_kinetics | text | YES |
| flavor_binding | text | YES |
| notes | text | YES |

- CHECK (((source_id IS NOT NULL) OR (experiment_id IS NOT NULL)))
- FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE CASCADE
- PRIMARY KEY (id)
- FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE
- CHECK (((water_activity IS NULL) OR ((water_activity >= (0)::numeric) AND (water_activity <= (1)::numeric))))

### public.meaty_volatile_library

Type: BASE TABLE; rows: 273

| Column | Type | Nullable |
|---|---|---|
| entry_no | int4 | NO |
| cas_number | text | YES |
| compound | text | NO |
| likely_process | text | YES |
| chemical_group | text | YES |
| subgroup | text | YES |
| ri_polar | numeric | YES |
| ri_non_polar | numeric | YES |
| odor_descriptor | text | YES |
| odor_threshold | text | YES |
| cooked_meats_reported | text | YES |
| source_table | text | YES |
| source_classification | text | YES |
| source_pdf | text | YES |
| notes | text | YES |
| beef_relevance_score | numeric | YES |

- PRIMARY KEY (entry_no)

### public.molecule_odours

Type: BASE TABLE; rows: 2263

| Column | Type | Nullable |
|---|---|---|
| molecule_id | int8 | NO |
| odour_id | int8 | NO |

- FOREIGN KEY (molecule_id) REFERENCES molecules(id) ON DELETE CASCADE
- FOREIGN KEY (odour_id) REFERENCES odours(id) ON DELETE CASCADE
- PRIMARY KEY (molecule_id, odour_id)

### public.molecule_properties

Type: BASE TABLE; rows: 3650

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| molecule_id | int8 | NO |
| property | text | NO |
| value_raw | text | YES |
| value_num | numeric | YES |
| unit_raw | text | YES |
| unit_norm | text | YES |
| basis | text | YES |
| uncertainty | text | YES |
| replicate_count | int4 | YES |
| derivation | text | NO |
| method | text | YES |
| conditions | jsonb | YES |
| source_id | int8 | YES |
| source_ref | text | YES |
| source_location | text | YES |
| confidence | numeric | YES |
| flags | _text | YES |
| created_at | timestamptz | NO |

- CHECK (((confidence >= (0)::numeric) AND (confidence <= (1)::numeric)))
- CHECK ((derivation = ANY (ARRAY['reported'::text, 'author_derived'::text, 'graph_estimated'::text, 'system_derived'::text])))
- FOREIGN KEY (molecule_id) REFERENCES molecules(id) ON DELETE CASCADE
- PRIMARY KEY (id)
- FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE SET NULL

### public.molecule_role_tags

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| molecule_id | int8 | NO |
| source_id | int8 | YES |
| experiment_id | int8 | YES |
| role | molecule_role | NO |
| notes | text | YES |

- CHECK (((source_id IS NOT NULL) OR (experiment_id IS NOT NULL)))
- FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE CASCADE
- FOREIGN KEY (molecule_id) REFERENCES molecules(id) ON DELETE CASCADE
- PRIMARY KEY (id)
- FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE

### public.molecule_sensory_attributes

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| molecule_id | int8 | NO |
| attribute_id | int8 | NO |

- FOREIGN KEY (attribute_id) REFERENCES sensory_attributes(id) ON DELETE CASCADE
- FOREIGN KEY (molecule_id) REFERENCES molecules(id) ON DELETE CASCADE
- PRIMARY KEY (molecule_id, attribute_id)

### public.molecules

Type: BASE TABLE; rows: 799

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| name | text | NO |
| category | text | YES |
| cas_number | text | YES |
| pubchem_cid | text | YES |
| notes | text | YES |
| created_at | timestamptz | YES |
| updated_at | timestamptz | YES |
| external_id | text | YES |
| melting_point | text | YES |
| water_solubility | text | YES |
| compound_id | text | YES |
| odour_source_url | text | YES |
| external_key | text | YES |
| found_in | _text | YES |
| pathway_step | text | YES |
| is_junk | bool | NO |
| inchikey | text | YES |
| smiles | text | YES |
| molecular_formula | text | YES |
| id_match_method | text | YES |
| id_needs_review | bool | NO |
| molecular_weight | numeric | YES |
| formal_charge | int4 | YES |
| functional_groups | _text | YES |
| reactive_groups | _text | YES |
| pka | numeric | YES |
| isoelectric_point | numeric | YES |
| tpsa | numeric | YES |
| logp | numeric | YES |
| redox_potential_v | numeric | YES |
| sequence_conformation | text | YES |
| boiling_point | text | YES |
| vapor_pressure | text | YES |
| odor_threshold_raw | text | YES |
| odor_threshold_ppb | numeric | YES |
| oav | numeric | YES |
| color | text | YES |

- PRIMARY KEY (id)

### public.odours

Type: BASE TABLE; rows: 639

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| name | text | NO |
| notes | text | YES |
| created_at | timestamptz | YES |
| updated_at | timestamptz | YES |
| external_id | text | YES |
| odour_category | text | YES |

- UNIQUE (name)
- PRIMARY KEY (id)

### public.organizations

Type: BASE TABLE; rows: 37

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| name | text | NO |
| org_type | expert_org_type | NO |
| country | text | YES |
| website | text | YES |
| description | text | YES |
| created_at | timestamptz | YES |
| updated_at | timestamptz | YES |

- UNIQUE (name)
- PRIMARY KEY (id)

### public.parent_topics

Type: VIEW; rows: view - not counted

| Column | Type | Nullable |
|---|---|---|
| id | int8 | YES |
| slug | text | YES |
| name | text | YES |
| root_branch | text | YES |
| level | int2 | YES |


### public.processes

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| source_id | int8 | YES |
| experiment_id | int8 | YES |
| cooking_method | cooking_method | YES |
| step_label | text | YES |
| temperature_c | numeric | YES |
| time_min | numeric | YES |
| ph | numeric | YES |
| water_activity | numeric | YES |
| oxygen_available | bool | YES |
| fat_phase_pct | numeric | YES |
| aqueous_phase_pct | numeric | YES |
| notes | text | YES |

- CHECK (((source_id IS NOT NULL) OR (experiment_id IS NOT NULL)))
- FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE CASCADE
- CHECK (((ph IS NULL) OR ((ph >= (0)::numeric) AND (ph <= (14)::numeric))))
- PRIMARY KEY (id)
- FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE
- CHECK (((water_activity IS NULL) OR ((water_activity >= (0)::numeric) AND (water_activity <= (1)::numeric))))

### public.product_contexts

Type: BASE TABLE; rows: 10

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| slug | text | NO |
| name | text | NO |
| category | text | NO |
| description | text | YES |
| created_at | timestamptz | YES |

- PRIMARY KEY (id)
- UNIQUE (slug)

### public.reaction_participants

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| reaction_id | int8 | NO |
| molecule_id | int8 | YES |
| ingredient_id | int8 | YES |
| role | participant_role | NO |
| notes | text | YES |

- CHECK ((((molecule_id IS NOT NULL) AND (ingredient_id IS NULL)) OR ((molecule_id IS NULL) AND (ingredient_id IS NOT NULL))))
- FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE
- FOREIGN KEY (molecule_id) REFERENCES molecules(id) ON DELETE CASCADE
- PRIMARY KEY (id)
- FOREIGN KEY (reaction_id) REFERENCES reactions(id) ON DELETE CASCADE

### public.reaction_topics

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| reaction_id | int8 | NO |
| topic_id | int8 | NO |

- PRIMARY KEY (reaction_id, topic_id)
- FOREIGN KEY (reaction_id) REFERENCES reactions(id) ON DELETE CASCADE
- FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE

### public.reactions

Type: BASE TABLE; rows: 8

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| slug | text | NO |
| name | text | NO |
| kind | reaction_kind | NO |
| parent_id | int8 | YES |
| description | text | YES |
| created_at | timestamptz | YES |

- FOREIGN KEY (parent_id) REFERENCES reactions(id) ON DELETE SET NULL
- PRIMARY KEY (id)
- UNIQUE (slug)

### public.sensory_attributes

Type: BASE TABLE; rows: 21

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| slug | text | NO |
| name | text | NO |
| parent_id | int8 | YES |
| is_off_note | bool | NO |
| description | text | YES |
| created_at | timestamptz | YES |

- FOREIGN KEY (parent_id) REFERENCES sensory_attributes(id) ON DELETE SET NULL
- PRIMARY KEY (id)
- UNIQUE (slug)

### public.source_audits

Type: BASE TABLE; rows: 40

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| source_id | int8 | NO |
| run_id | text | YES |
| audited_at | timestamptz | NO |
| tag_score | int4 | YES |
| relevance_score | int4 | YES |
| quality_score | int4 | YES |
| verdict | text | YES |
| tag_issues | jsonb | YES |
| notes | text | YES |
| weights_snapshot | jsonb | YES |
| audit_priority | float8 | YES |

- PRIMARY KEY (id)
- FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE
- CHECK ((verdict = ANY (ARRAY['keep'::text, 'review'::text, 'quarantine'::text])))

### public.source_experts

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| source_id | int8 | NO |
| expert_id | int8 | NO |
| role | text | NO |

- FOREIGN KEY (expert_id) REFERENCES experts(id) ON DELETE CASCADE
- PRIMARY KEY (source_id, expert_id, role)
- CHECK ((role = ANY (ARRAY['author'::text, 'corresponding'::text, 'inventor'::text, 'reviewer'::text, 'editor'::text])))
- FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE

### public.source_ingredients

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| source_id | int8 | NO |
| ingredient_id | int8 | NO |

- FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE
- PRIMARY KEY (source_id, ingredient_id)
- FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE

### public.source_methods

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| source_id | int8 | NO |
| method_id | int8 | NO |

- FOREIGN KEY (method_id) REFERENCES analytical_methods(id) ON DELETE CASCADE
- PRIMARY KEY (source_id, method_id)
- FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE

### public.source_molecules

Type: BASE TABLE; rows: 23

| Column | Type | Nullable |
|---|---|---|
| source_id | int8 | NO |
| molecule_id | int8 | NO |

- FOREIGN KEY (molecule_id) REFERENCES molecules(id) ON DELETE CASCADE
- PRIMARY KEY (source_id, molecule_id)
- FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE

### public.source_product_contexts

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| source_id | int8 | NO |
| context_id | int8 | NO |
| role | text | NO |

- FOREIGN KEY (context_id) REFERENCES product_contexts(id) ON DELETE CASCADE
- PRIMARY KEY (source_id, context_id, role)
- CHECK ((role = ANY (ARRAY['primary'::text, 'alternative'::text, 'reference'::text])))
- FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE

### public.source_reactions

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| source_id | int8 | NO |
| reaction_id | int8 | NO |

- PRIMARY KEY (source_id, reaction_id)
- FOREIGN KEY (reaction_id) REFERENCES reactions(id) ON DELETE CASCADE
- FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE

### public.source_sensory_attributes

Type: BASE TABLE; rows: 0

| Column | Type | Nullable |
|---|---|---|
| source_id | int8 | NO |
| attribute_id | int8 | NO |

- FOREIGN KEY (attribute_id) REFERENCES sensory_attributes(id) ON DELETE CASCADE
- PRIMARY KEY (source_id, attribute_id)
- FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE

### public.source_tags

Type: BASE TABLE; rows: 3457

| Column | Type | Nullable |
|---|---|---|
| source_id | int8 | NO |
| tag_id | int8 | NO |

- PRIMARY KEY (source_id, tag_id)
- FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE
- FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE

### public.source_topics

Type: BASE TABLE; rows: 569

| Column | Type | Nullable |
|---|---|---|
| source_id | int8 | NO |
| topic_id | int8 | NO |

- PRIMARY KEY (source_id, topic_id)
- FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE
- FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE

### public.sources

Type: BASE TABLE; rows: 818

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| name | text | NO |
| year | int2 | YES |
| authors | text | YES |
| affiliation | text | YES |
| venue | text | YES |
| url | text | YES |
| abstract | text | YES |
| notes | text | YES |
| created_at | timestamptz | YES |
| updated_at | timestamptz | YES |
| source_type | source_type | YES |
| doi | text | YES |
| metadata | jsonb | YES |
| external_id | text | YES |
| search_query | text | YES |
| citation_count | int4 | YES |
| top_keywords | text | YES |
| external_key | text | YES |
| trust_tier | text | YES |
| composite_score | float4 | YES |
| review_status | text | YES |
| dimensions_id | text | YES |
| journal | text | YES |
| dimensions_topics | _text | YES |
| search_vec | tsvector | YES |
| priority_score | numeric | YES |
| is_review | bool | YES |
| relevance_llm | int2 | YES |
| pathway | _text | YES |
| method | _text | YES |
| sensory_descriptor | _text | YES |
| matrix | _text | YES |
| compound_class | _text | YES |
| study_type | text | YES |
| main_claim | text | YES |
| tailored_abstract | text | YES |

- PRIMARY KEY (id)

### public.tags

Type: BASE TABLE; rows: 571

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| category | text | NO |
| name | text | NO |
| slug | text | NO |
| created_at | timestamptz | YES |

- UNIQUE (category, slug)
- PRIMARY KEY (id)

### public.topic_hierarchy

Type: VIEW; rows: view - not counted

| Column | Type | Nullable |
|---|---|---|
| root_branch | text | YES |
| parent_name | text | YES |
| child_name | text | YES |
| child_slug | text | YES |


### public.topics

Type: BASE TABLE; rows: 112

| Column | Type | Nullable |
|---|---|---|
| id | int8 | NO |
| slug | text | NO |
| name | text | NO |
| parent_id | int8 | YES |
| root_branch | text | NO |
| level | int2 | NO |
| description | text | YES |
| created_at | timestamptz | YES |

- FOREIGN KEY (parent_id) REFERENCES topics(id) ON DELETE SET NULL
- PRIMARY KEY (id)
- UNIQUE (slug)

### public.v_claim_evidence

Type: VIEW; rows: view - not counted

| Column | Type | Nullable |
|---|---|---|
| claim_id | int8 | YES |
| claim_text | text | YES |
| stance | claim_stance | YES |
| confidence | numeric | YES |
| source_id | int8 | YES |
| source_name | text | YES |
| source_type | source_type | YES |
| source_year | int2 | YES |
| molecule_id | int8 | YES |
| molecule_name | text | YES |


### public.v_experiment_record

Type: VIEW; rows: view - not counted

| Column | Type | Nullable |
|---|---|---|
| experiment_id | int8 | YES |
| experiment_name | text | YES |
| source_id | int8 | YES |
| source_name | text | YES |
| methods | _text | YES |
| sensory_attributes | _text | YES |
| molecules | _text | YES |
| process_summary | _text | YES |


### public.v_experts_3tier

Type: VIEW; rows: view - not counted

| Column | Type | Nullable |
|---|---|---|
| id | int8 | YES |
| external_id | text | YES |
| name | text | YES |
| affiliation | text | YES |
| country | text | YES |
| research_field | research_field | YES |
| h_index | int4 | YES |
| total_papers | int4 | YES |
| relevance_score | numeric | YES |
| outreach_status | outreach_status | YES |
| relevance_tier | text | YES |


### public.v_intelligence_record

Type: VIEW; rows: view - not counted

| Column | Type | Nullable |
|---|---|---|
| source_id | int8 | YES |
| title | text | YES |
| source_type | source_type | YES |
| year | int2 | YES |
| product_context | _text | YES |
| alternative_product | _text | YES |
| chemistry_topics | _text | YES |
| reactions | _text | YES |
| analytical_methods | _text | YES |
| sensory_attributes | _text | YES |
| molecules | _text | YES |
| ingredients | _text | YES |
| process_summary | _text | YES |
| matrix_summary | _text | YES |


### public.v_meaty_molecules_ranked

Type: VIEW; rows: view - not counted

| Column | Type | Nullable |
|---|---|---|
| molecule_id | int8 | YES |
| molecule_name | text | YES |
| category | text | YES |
| beef_relevance_score | numeric | YES |
| likely_process | text | YES |
| chemical_group | text | YES |
| subgroup | text | YES |
| reference_odor | text | YES |
| cooked_meats_reported | text | YES |
| my_odours | _text | YES |


### public.v_mvl_gaps

Type: VIEW; rows: view - not counted

| Column | Type | Nullable |
|---|---|---|
| entry_no | int4 | YES |
| compound | text | YES |
| cas_number | text | YES |
| likely_process | text | YES |
| chemical_group | text | YES |
| beef_relevance_score | numeric | YES |
| odor_descriptor | text | YES |


### public.v_mvl_x_molecules_by_cas

Type: VIEW; rows: view - not counted

| Column | Type | Nullable |
|---|---|---|
| entry_no | int4 | YES |
| compound | text | YES |
| cas_number | text | YES |
| beef_relevance_score | numeric | YES |
| molecule_id | int8 | YES |
| molecule_name | text | YES |


### public.v_mvl_x_molecules_by_name

Type: VIEW; rows: view - not counted

| Column | Type | Nullable |
|---|---|---|
| entry_no | int4 | YES |
| mvl_compound | text | YES |
| mvl_cas | text | YES |
| likely_process | text | YES |
| chemical_group | text | YES |
| beef_relevance_score | numeric | YES |
| mvl_odor | text | YES |
| molecule_id | int8 | YES |
| molecule_name | text | YES |
| molecule_category | text | YES |
| odour_org_uk_id | text | YES |


### public.v_mvl_x_molecules_fuzzy

Type: VIEW; rows: view - not counted

| Column | Type | Nullable |
|---|---|---|
| entry_no | int4 | YES |
| mvl_compound | text | YES |
| beef_relevance_score | numeric | YES |
| molecule_id | int8 | YES |
| molecule_name | text | YES |
| match_type | text | YES |


### public.v_precursors

Type: VIEW; rows: view - not counted

| Column | Type | Nullable |
|---|---|---|
| reaction_id | int8 | YES |
| reaction_name | text | YES |
| reaction_kind | reaction_kind | YES |
| participant_role | participant_role | YES |
| participant_name | text | YES |
| participant_type | text | YES |


### public.v_reaction_participants_named

Type: VIEW; rows: view - not counted

| Column | Type | Nullable |
|---|---|---|
| reaction_id | int8 | YES |
| reaction_name | text | YES |
| reaction_kind | reaction_kind | YES |
| participant_role | participant_role | YES |
| participant_name | text | YES |
| participant_type | text | YES |


### public.v_relevance_summary

Type: VIEW; rows: view - not counted

| Column | Type | Nullable |
|---|---|---|
| entity | text | YES |
| relevance_tier | text | YES |
| n | int8 | YES |


### public.v_sources_3tier

Type: VIEW; rows: view - not counted

| Column | Type | Nullable |
|---|---|---|
| id | int8 | YES |
| external_id | text | YES |
| name | text | YES |
| year | int2 | YES |
| venue | text | YES |
| url | text | YES |
| citation_count | int4 | YES |
| composite_score | float4 | YES |
| review_status | text | YES |
| trust_tier | text | YES |
| relevance_tier | text | YES |

