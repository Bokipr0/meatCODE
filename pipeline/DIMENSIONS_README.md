# Dimensions.ai → Neon ingester

Pulls researchers and recent publications from Dimensions for each topic in your
flavor-science taxonomy and merges them into `experts` and `sources`.

## What it does

For each topic (Maillard, meat aroma, off-note, plant protein, sensory, fermentation):

1. Search Dimensions researchers — pulls top 25 by relevance, including `h_index`,
   `total_publications`, ORCID, current org.
2. Search Dimensions publications — pulls up to 80 papers from 2018 onward,
   including DOI, abstract, citations, authors.
3. **Upsert** — finds existing rows by ORCID / DOI / dimensions_id and updates
   them in place; inserts new ones with the topic tagged in the
   `dimensions_topics` array.
4. Logs the run to a new `ingest_log` table.

Safe to re-run. Existing rows from the Airtable migration are not duplicated.

## One-time setup

```bash
pip install psycopg2-binary certifi
```

Run the schema additions once:

```bash
psql "$DATABASE_URL" -f add_dimensions_columns.sql
```

This adds:

- `experts.dimensions_id`, `current_org`, `dimensions_topics`
- `sources.dimensions_id`, `doi`, `abstract`, `journal`, `dimensions_topics`
- unique partial indexes on `dimensions_id` and `doi`
- `ingest_log` table for run tracking

## Run

```bash
export DIMENSIONS_API_KEY="your-key-here"
export DATABASE_URL="postgresql://neondb_owner:...@...neon.tech/neondb?sslmode=require"

# Dry run on one topic first — fetches from Dimensions, doesn't write
python3 dimensions_ingest.py --dry-run --topics maillard

# Full run, all topics
python3 dimensions_ingest.py

# Or limit topics
python3 dimensions_ingest.py --topics maillard,meat-aroma

# Or change scope
python3 dimensions_ingest.py --researchers 50 --papers 150 --year-from 2020
```

## After a run

Check what came in:

```sql
-- last 5 ingest runs
SELECT * FROM ingest_log ORDER BY id DESC LIMIT 5;

-- experts gained from Dimensions, by topic
SELECT unnest(dimensions_topics) AS topic, COUNT(*) AS n
FROM experts
WHERE dimensions_id IS NOT NULL
GROUP BY 1 ORDER BY n DESC;

-- papers gained
SELECT unnest(dimensions_topics) AS topic, COUNT(*) AS n
FROM sources
WHERE dimensions_id IS NOT NULL
GROUP BY 1 ORDER BY n DESC;

-- highest-cited new papers from this ingest
SELECT name, year, citation_count, journal
FROM sources
WHERE dimensions_id IS NOT NULL
ORDER BY citation_count DESC NULLS LAST
LIMIT 20;
```

## Tuning

- **Topic queries** live in `TOPIC_QUERIES` at the top of `dimensions_ingest.py` —
  add a slug + DSL search expression there to extend coverage.
- **Rate limits**: the script handles 429s with backoff. Free academic keys are
  ~30 req/min; the full run makes ~12 requests + ~6 short pauses.
- **Token lifetime**: Dimensions JWTs last ~1 hour. The full run takes ~3–5
  minutes, so we acquire one token at start and reuse it.
- **Deduplication**: order of preference is ORCID > DOI > dimensions_id. If a
  researcher already exists from the Airtable migration with an ORCID match,
  their existing row gets enriched with h_index / current_org / total_papers
  rather than duplicated.

## Future steps (not in this script)

- Co-author graph → populate `expert_relations` join table with
  `relation_type = 'co_author'`.
- Author → paper linkage → populate the missing `source_authors` join table.
- Patents / grants — Dimensions also exposes these; same DSL pattern.
