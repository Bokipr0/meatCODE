# Database migrations

The Neon Postgres schema is **reproducible from this folder**. Every schema change is a file here.

## Convention
- Filename: `NNNN_short_description.sql` (zero-padded, sequential). e.g. `0007_add_source_embeddings.sql`.
- **Forward-only.** Don't edit an applied migration — add a new one.
- Idempotent where practical (`IF NOT EXISTS` / `IF EXISTS`).
- Header comment: what it does + why + date + author/agent.

## Baseline
The SQL files in `db/` are the historical baseline (not yet renumbered into this folder):
`gfi_schema.sql` → `gfi_schema_v2_migration.sql` → `migration_phase1_alter.sql` → `add_dimensions_columns.sql`,
plus seeds (`gfi_seed_taxonomies.sql`, `seed_topics_v2.sql`, `seed_meaty_volatile_library.sql`).

## Applying
Use `pipeline/apply_sql.py` (reads `DATABASE_URL` from `.env`). For risky changes, apply to a **Neon
branch** first, validate, then to main.

## Rule
No ad-hoc `ALTER`/`CREATE` run directly against the DB that isn't captured as a migration file here.
If you change the schema, you write the file — otherwise the next agent can't reproduce it.
