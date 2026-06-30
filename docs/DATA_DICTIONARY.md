# MeatCODE Data Dictionary

> Derived from `db/airtable_to_postgres_mapping.md` + the schema files in `db/`. Items marked (verify)
> need a live check against Neon once `DATABASE_URL` is in `.env`; then this becomes authoritative.

## Core tables (row counts: ~500 sources reported live 2026-06-30 — verify; others per migration mapping)
| Table | Purpose | Key columns |
|---|---|---|
| `sources` | Papers/books/patents/reports | name, url, year, venue, authors, doi, abstract, journal, citation_count, trust_tier, top_keywords, search_vec, dimensions_id, dimensions_topics, external_id |
| `molecules` | Precursors / volatiles | name, category, taste, use_notes, melting_point, water_solubility, compound_id, aliases[], odour_source_url, external_id |
| `odours` | Sensory descriptors | name, odour_category, external_id |
| `experts` | People directory | name, affiliation, country, research_field, relevance_score, h_index, total_papers, email, orcid, keywords, outreach_status, org_type, linkedin_url, openalex_id, dimensions_id, current_org, external_id |
| `claims` | Evidence statements | claim_text, stance(ENUM), confidence, evidence_snippet, external_id |
| `topics` | Hierarchical taxonomy | id, parent_id, root_branch (e.g. flavor_chemistry) |

## Join tables
`source_molecules`, `molecule_odours`, `claim_sources`, `claim_molecules`, `source_topics`,
`claim_topics_v2`, `expert_relations`, `source_experts`, plus the v2 sensory / method / context links.

## ENUMs (schema v2)
`source_type`, `expert_org_type`, `evidence_strength`, `actionability`, `molecule_role`,
`reaction_kind`, `cooking_method`, `protein_source`, `fat_source`, `ingredient_category`,
`participant_role`, `stance`.

## Relevance tiers
Very Relevant ≥80% · Mid 60–80% · Little <60% (`trust_tier` / relevance score).

## Retrievability (trust-critical)
The Oracle's RAG (`server/reaktzia-mvp/retrieval.py`) ranks `sources` via
`ts_rank_cd(search_vec, websearch_to_tsquery(...))`. **A source is only citable if it has a populated
`search_vec` (built from name/abstract).** A row with no abstract is invisible to citations.
TODO (verify live): count sources with non-null `abstract` and non-null `search_vec` — that's the real
"how big is the citable corpus" number, distinct from the raw row count.
