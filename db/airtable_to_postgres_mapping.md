# Airtable → Postgres Migration Mapping

**Source:** Airtable base `GFI database` (appcS9K0FZK2DIPbZ)
**Target:** Postgres `neondb` on Neon (with v1 + v2 schema applied)
**Strategy:** ID-preserving migration via Airtable record IDs stored in `external_id` columns, then linked-records resolved by `external_id` lookup.

## Row counts

| Airtable table | Rows | Postgres destination |
|---|---|---|
| Molecules | 799 | `molecules` |
| Odours | 639 | `odours` |
| Experts | 374 | `experts` |
| Claims | 45 | `claims` |
| Sources | 34 | `sources` |

---

## Column-level mapping

### Sources (Airtable) → `sources` (Postgres)

| Airtable field | Type | Postgres column | Action |
|---|---|---|---|
| `Name` | singleLineText | `name` | Direct |
| `URL` | url | `url` | Direct |
| `Year` | number | `year` | Direct (cast to SMALLINT) |
| `Venue` | singleLineText | `venue` | Direct |
| `Authors` | multilineText | `authors` | Direct |
| `query` | singleLineText | `search_query` | **NEW column** — the search that surfaced this paper |
| `citation_count` | number | `citation_count` | **NEW column** |
| `trust_tier` | singleSelect | `trust_tier` | Direct (free-form TEXT, already exists) |
| `top_keywords` | multilineText | `top_keywords` | **NEW column** |
| `source_id` | singleLineText | `external_key` | **NEW column** — Airtable's user-facing key |
| `Claims 2` | multipleRecordLinks | → `claim_sources` | Resolve via `external_id` |
| `Molecules` | multipleRecordLinks | → `source_molecules` | Resolve via `external_id` |
| (Airtable record id) | recXXX | `external_id` | Stored as the migration bridge |

### Molecules (Airtable) → `molecules` (Postgres)

| Airtable field | Type | Postgres column | Action |
|---|---|---|---|
| `Name` | singleLineText | `name` | Direct |
| `category` | singleLineText | `category` | Direct |
| `mentions_count` | count | — | Skip (computed in Postgres via JOIN) |
| `smell` | singleLineText | — | Skip (denormalized cache; real data in `Odours` link) |
| `taste` | singleLineText | `taste` | **NEW column** |
| `use` | singleLineText | `use_notes` | **NEW column** (rename — `use` is a SQL keyword) |
| `melting_point` | singleLineText | `melting_point` | **NEW column** |
| `water_solubility` | singleLineText | `water_solubility` | **NEW column** |
| `compound_id` | singleLineText | `compound_id` | **NEW column** (odour.org.uk dedup key) |
| `aliases` | multilineText (newline-sep) | `aliases` | Split on newlines → TEXT[] |
| `odour_source_url` | url | `odour_source_url` | **NEW column** |
| `molecule_key` | singleLineText | `external_key` | **NEW column** |
| `Sources` | multipleRecordLinks | → `source_molecules` | Resolve via `external_id` |
| `Claims` | multipleRecordLinks | → `claim_molecules` | Resolve via `external_id` |
| `Odours` | multipleRecordLinks | → `molecule_odours` | Resolve via `external_id` |
| (record id) | recXXX | `external_id` | Bridge |

### Odours (Airtable) → `odours` (Postgres)

| Airtable field | Type | Postgres column | Action |
|---|---|---|---|
| `Name` | singleLineText | `name` | Direct |
| `odour_category` | singleLineText | `odour_category` | **NEW column** |
| `compound_ids` | singleLineText | — | Skip (derivable from `molecule_odours` join) |
| `Molecules` | multipleRecordLinks | → `molecule_odours` | Resolve via `external_id` (other side already covered) |
| (record id) | recXXX | `external_id` | Bridge |

### Claims (Airtable) → `claims` (Postgres)

| Airtable field | Type | Postgres column | Action |
|---|---|---|---|
| `claim_text` | multilineText | `claim_text` | Direct |
| `stance` | singleSelect | `stance` | Direct (already an ENUM in Postgres) |
| `confidence` | number | `confidence` | Direct |
| `evidence_snippet` | multilineText | `evidence_snippet` | **NEW column** |
| `source_id` | singleLineText | — | Skip (use `Sources` link instead) |
| `claim_key` | singleLineText | `external_key` | **NEW column** |
| `Topic` | multipleSelects | → `claim_topics` | Insert one row per topic, free-text. Backfill into `topics`+`claim_topics_v2` later. |
| `Sources` | multipleRecordLinks | → `claim_sources` | Resolve via `external_id` |
| `Molecules` | multipleRecordLinks | → `claim_molecules` | Resolve via `external_id` |
| (record id) | recXXX | `external_id` | Bridge |

### Experts (Airtable) → `experts` (Postgres)

| Airtable field | Type | Postgres column | Action |
|---|---|---|---|
| `Name` | singleLineText | `name` | Direct |
| `Affiliation` | singleLineText | `affiliation` | Direct |
| `Country` | singleLineText | `country` | **NEW column** |
| `Research Field` | singleSelect | `research_field` | Direct (cast to ENUM; values may need normalization) |
| `Relevance Score` | number | `relevance_score` | **NEW column** |
| `H-Index` | number | `h_index` | **NEW column** |
| `Total Papers` | number | `total_papers` | **NEW column** |
| `Email` | email | `email` | Direct |
| `ORCID` | singleLineText | `orcid` | **NEW column** |
| `Key Research` | multilineText | `key_research` | **NEW column** |
| `Keywords` | multilineText | `keywords` | **NEW column** |
| `Co-Authors in Network` | multilineText | — | Skip (free-text names; not reliable for `expert_relations`) |
| `Outreach Status` | singleSelect | `outreach_status` | Direct (ENUM; values need normalization — Airtable has `Auto-discovered` which we'll map to `not_contacted`) |
| `LinkedIn URL` | url | `linkedin_url` | **NEW column** |
| `Knowledge Gaps` | multilineText | `knowledge_gaps` | **NEW column** |
| `OpenAlex Author ID` | singleLineText | `openalex_id` | **NEW column** |
| `Expert Type` | singleSelect | `org_type` | Map to existing `expert_org_type` ENUM (NGO/academic/industry/culinary) |
| `Related Researchers` | multipleRecordLinks | → `expert_relations` | One row per link, `relation_type='related'` |
| `From field: Related Researchers` | multipleRecordLinks | — | Skip (inverse of above; same data) |
| (record id) | recXXX | `external_id` | Bridge |

---

## ENUM value mappings

Airtable single-select values may not exactly match Postgres ENUM values. Normalization needed:

### `Outreach Status`
| Airtable value | Postgres value |
|---|---|
| Auto-discovered | not_contacted |
| Shortlisted | shortlisted |
| Outreach Sent | outreach_sent |
| Replied | replied |
| Meeting Scheduled | meeting_scheduled |
| Advisor | advisor |
| Not a fit | not_a_fit |

### `Research Field`
Airtable values vary; normalize via lookup or default to `other`. Will inspect actual values during the import.

### `Expert Type` → `org_type`
| Airtable value | Postgres value |
|---|---|
| NGO | ngo_gov |
| Academic / Academy | academy |
| Industry / Company | company |
| Culinary | culinary |

### `stance` (Claims)
Airtable select values match Postgres ENUM directly: `supports`, `refutes`, `mixed`, `neutral`.

---

## Migration steps

1. **Add `external_id` + new columns** — one ALTER TABLE script
2. **Import main tables** verbatim into staging schema (Python script via Airtable MCP), preserving record IDs
3. **Insert into Postgres tables** with `external_id` populated
4. **Resolve linked records** — for each multipleRecordLinks field, look up `external_id` → `id` and INSERT into the matching join table
5. **Verify counts** — row counts should match what's in Airtable
6. **(Later, optional)** Drop `external_id` columns once we're confident no re-migration is needed
