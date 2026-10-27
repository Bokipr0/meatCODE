# MeatCODE — repository connection review

_Last updated: 2026-10-17 12:29 UTC · Codex / Advisory · local folder review and existing repository confirmed by Lior_

Lior confirmed on 2026-10-17 that this folder should continue using **Bokipr0/meatCODE**.
The local checkout already has `origin` configured as `https://github.com/Bokipr0/meatCODE.git`.
No new repository, reinitialization, or remote replacement is needed.

## What this folder contains

| Area | Purpose |
|---|---|
| `app/`, `UI-UX Designer/` | Canonical HTML product interface, preview screens, design references and handoffs |
| `server/` | Python HTTP server, grounded Oracle retrieval and streaming, database APIs, papers browser, simulator adapter |
| `db/` | SQL migrations, seeds and the governing taxonomy |
| `pipeline/`, `molecular_pipeline/` | Literature ingestion, relevance and quality scoring, extraction, molecule identity and enrichment |
| `kg/`, `analysis/` | Graph construction/exploration, evaluation harnesses and research analyses |
| `docs/`, `platform_docs/`, `Strategy RAG/` | Product scope, scientific strategy, architecture, meetings and operating decisions |
| `orchestration/`, root coordination documents | Agent roles, project context, reusable skills and handoff tooling |
| `Release Center/`, `render.yaml` | Feature flags, local runs, staging publication, production promotion and rollback |
| `data/` | Ignored local exports, caches, extraction inputs and packed skills |

The product is GFI Israel's source-backed knowledge platform for meaty flavour and aroma science.
Its main scientific goal is to connect literature, molecules, conditions and provenance so the
Oracle and research tools can support useful scientific work. Some surfaces remain previews.

## The connection to preserve

- **GitHub:** code, versioned documents, SQL and project history.
- **Neon Postgres:** live scientific records; connecting GitHub does not copy or back up Neon.
- **Render:** documented deployment flow is `dev` → staging and `main` → production.
- **Asana:** task ownership and priorities.
- **Local secrets / Render settings:** credentials are separate from the repository.

The Release Center scripts push to `origin`. In particular, `deploy-dev.command` stages all
eligible changes, commits and pushes `dev`; it also triggers the documented staging deployment.
It should not be treated as a read-only connection check.

## Locally verified on 2026-10-17

- Checkout: `dev`, tracking `origin/dev`; HEAD `881f3a1` (2026-10-05).
- Existing Git history contains 217 tracked files at review time, with modified documents and
  untracked handoff material from the October context refresh. Those working files are not yet
  represented in the current commit.
- `.env` and `.env.dev` are ignored; only `.env.example` is tracked among `.env*` paths.
  `data/` contents are ignored apart from `.gitkeep`.
- Existing tracked material includes internal Word documents, a contact spreadsheet and a deck.
  The documented repository is private; current GitHub visibility was not checked remotely.
- The README has stale quick-start instructions referencing the removed `server/reaktzia-mvp/`
  directory. The current server is `server/meatcode_server.py` and the documented local launcher
  is `Release Center/run-local.command`.

## Context and limits

The latest consolidated external-system verification in the folder is dated **2026-10-11**.
It reports 818 literature sources, 319 passing the Oracle relevance gate, 798 non-junk molecules,
and 23 paper–molecule links. These are dated snapshot figures, not a fresh database audit.
That state identifies corpus quarantine enforcement, evidence extraction and publisher rights
as open issues. Older plans and boards contain superseded dates and deployment claims.

This review covered the folder inventory, canonical onboarding/state documents, architecture
and strategy references, code entry points, ignore rules and release scripts. It was not an
exhaustive reading of every historical log entry, binary document or scientific input file,
nor a secret scan of Git history. GitHub authentication, current remote refs, Render and Neon
were not contacted. No commits, pushes, deployments or configuration changes were made.

The repository choice is resolved. Any publication should review the existing local changes
and save the intended handoff files on `dev`, preserving the production promotion process.
