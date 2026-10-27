# SYSTEM SNAPSHOT — generated 2026-10-11 15:33 UTC

> **Generated file — do not hand-edit.** Regenerate with `Release Center/refresh-handoff.command` (or `python3 orchestration/build_system_snapshot.py`). Everything here was read live from Neon, git and the repo at the time above. No secrets are written — only whether they are present.

## What is live right now (verified, not assumed)

- **Production** runs commit `c563d1666798` = `prod-20260921-1717`, branch `main`, env `prod`, started 2026-09-21T14:18:08+00:00, model `claude-sonnet-4-6`.
- **`dev` on GitHub** is at `881f3a164957`. Dev is AHEAD of production — run `promote-to-prod.command` to ship it (see PROJECT_STATE for what's waiting).

## Neon Postgres — key metrics

| Metric | production (`.env`) | dev branch (`.env.dev`) |
|---|---:|---:|
| sources | 818 | 818 |
| sources ≥ relevance gate (60) | 319 | 319 |
| sources with DOI | 769 | 769 |
| molecules (non-junk) | 798 | 798 |
| molecules with InChIKey | 590 | 590 |
| molecules with CAS | 568 | 568 |
| experts | 3129 | 3129 |
| paper↔molecule links (source_molecules) | 23 | 23 |
| claims | 45 | 45 |
| molecule_properties (provenanced values) | 3650 | 3650 |
|   … citing a paper (source_id set) | 0 | 0 |
| experiments | 0 | 0 |
| processes (T/pH/time conditions) | 0 | 0 |
| B2 check: quarantined sources still ≥ gate (should be 0) | 4 | 4 |
| data-quality audits: last run | 2026-07-08 | 2026-07-08 |

`molecules` has **38** columns on production.

<details><summary>All tables with row counts (production)</summary>

| Table | Rows |
|---|---:|
| `analytical_methods` | 13 |
| `claim_experiments` | 0 |
| `claim_molecules` | 41 |
| `claim_reactions` | 0 |
| `claim_sensory_attributes` | 0 |
| `claim_sources` | 69 |
| `claim_topics` | 0 |
| `claim_topics_v2` | 0 |
| `claims` | 45 |
| `experiment_ingredients` | 0 |
| `experiment_methods` | 0 |
| `experiment_molecules` | 0 |
| `experiment_product_contexts` | 0 |
| `experiment_reactions` | 0 |
| `experiment_sensory_attributes` | 0 |
| `experiments` | 0 |
| `expert_relations` | 0 |
| `experts` | 3129 |
| `ingest_log` | 6 |
| `ingredient_molecules` | 0 |
| `ingredients` | 0 |
| `matrix_profiles` | 0 |
| `meaty_volatile_library` | 273 |
| `molecule_odours` | 2263 |
| `molecule_properties` | 3650 |
| `molecule_role_tags` | 0 |
| `molecule_sensory_attributes` | 0 |
| `molecules` | 799 |
| `odours` | 639 |
| `organizations` | 37 |
| `processes` | 0 |
| `product_contexts` | 10 |
| `reaction_participants` | 0 |
| `reaction_topics` | 0 |
| `reactions` | 8 |
| `sensory_attributes` | 21 |
| `source_audits` | 40 |
| `source_experts` | 0 |
| `source_ingredients` | 0 |
| `source_methods` | 0 |
| `source_molecules` | 23 |
| `source_product_contexts` | 0 |
| `source_reactions` | 0 |
| `source_sensory_attributes` | 0 |
| `source_tags` | 3457 |
| `source_topics` | 569 |
| `sources` | 818 |
| `tags` | 571 |
| `topics` | 112 |

Views (16): `leaf_topics`, `parent_topics`, `topic_hierarchy`, `v_claim_evidence`, `v_experiment_record`, `v_experts_3tier`, `v_intelligence_record`, `v_meaty_molecules_ranked`, `v_mvl_gaps`, `v_mvl_x_molecules_by_cas`, `v_mvl_x_molecules_by_name`, `v_mvl_x_molecules_fuzzy`, `v_precursors`, `v_reaction_participants_named`, `v_relevance_summary`, `v_sources_3tier`
</details>

## Schema migrations — 13 numbered files in `db/migrations/` (0002–0014)

Latest: `0010_molecule_structure_identity.sql`, `0011_molecule_target_properties.sql`, `0012_molecule_target_properties_seed.sql`, `0013_drop_empty_molecule_columns.sql`, `0014_drop_taste_use_notes.sql`

## GitHub

- Remote: `https://github.com/Bokipr0/meatCODE.git`
- Local branches: `dev`, `main` · checked out: **`dev`**
- Production release tags (4): `prod-20260722-2307`, `prod-20260831-1501`, `prod-20260921-1647`, `prod-20260921-1717`

## Render

- Services declared (uncommented) in `render.yaml`: `meatcode-oracle`
- Production URL: https://meatcode-oracle.onrender.com (health: `/api/health`, version: `/api/version`)
- Staging service `meatcode-dev` is created in the Render dashboard (branch `dev`), not in render.yaml.

## Secrets present on this machine (names only)

- `.env`: `ANTHROPIC_API_KEY`, `DATABASE_URL`
- `.env.dev`: `DATABASE_URL`
- `.env.prod`: _absent or empty_

## Feature flags — 16 in `Release Center/features.json`

| Flag | Kind | Status | dev | prod | Added |
|---|---|---|:-:|:-:|---|
| `new_logo` | feature | preview | ✅ | — | 2026-07-23 |
| `dev_banner` | feature | live | — | — | 2026-07-23 |
| `highlight_inventory` | feature | live | ✅ | — | 2026-07-23 |
| `dev_area` | feature | live | ✅ | — | 2026-08-15 |
| `backup_center` | feature | live | ✅ | — | 2026-09-21 |
| `papers_browser` | feature | preview | ✅ | — | 2026-10-05 |
| `maillard_sim` | feature | preview | ✅ | — | 2026-08-16 |
| `knowledge_graph` | screen | preview | ✅ | — | 2026-08-15 |
| `fingerprint` | screen | placeholder | ✅ | — | 2026-08-15 |
| `analytics` | screen | preview | ✅ | ✅ | 2026-08-15 |
| `compare` | screen | preview | ✅ | — | 2026-08-15 |
| `versions` | screen | live | ✅ | — | 2026-08-15 |
| `oracle_redesign` | screen | preview | ✅ | ✅ | 2026-08-15 |
| `analytics_workspace` | screen | preview | ✅ | — | 2026-08-31 |
| `research_reaction_network` | screen | preview | ✅ | — | 2026-08-31 |
| `analytics_module` | screen | preview | ✅ | — | 2026-08-31 |

## Server API — 37 routes in `server/meatcode_server.py` (local `dev` checkout — production may lag; see 'What is live')

`/api/ask`, `/api/backup`, `/api/companies`, `/api/compare`, `/api/consensus-demo`, `/api/corpus`, `/api/data-backup`, `/api/db-facets`, `/api/expert-facets`, `/api/experts`, `/api/experts/{id}`, `/api/flags`, `/api/flags/all`, `/api/flags/set`, `/api/flags/upsert`, `/api/health`, `/api/molecule-profile/{id}`, `/api/molecule-suggestions`, `/api/molecules`, `/api/molecules/{id}`, `/api/papers-browser`, `/api/papers-browser/export.csv`, `/api/papers-browser/facets`, `/api/papers-browser/pdf`, `/api/papers-browser/rows`, `/api/papers/recent`, `/api/papers/{id}`, `/api/reaction-network`, `/api/release/deploy-dev`, `/api/release/history`, `/api/release/promote`, `/api/release/rollback`, `/api/simulate`, `/api/simulate/health`, `/api/sources`, `/api/templates`, `/api/version`

## Coordination files (the agent spine)

| File | Lines | Last-updated stamp |
|---|---:|---|
| `ROLES.md` | 69 | 2026-10-11 |
| `CLAUDE.md` | 147 | 2026-10-11 |
| `PROJECT_STATE.md` | 82 | 2026-10-11 |
| `MVP_BOARD.md` | 69 | 2026-09-01 |
| `TEAM_BROADCAST.md` | 223 | — |
| `AGENT_UPDATE_LOG.md` | 1003 | 2026-10-11 |

## Agent skills versioned in the repo — 9 in `orchestration/skills/`

`data-engineer`, `integrate-dimensions-ai`, `meatcode-agent-team`, `meatcode-curate-state`, `meatcode-daily-sync`, `meatcode-schema-change`, `project-board-sync`, `reaktzia-mockup`, `weekly-progress-brief`

