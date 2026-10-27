<!-- Last updated: 2026-10-11 · Advisory · how to give a brand-new Claude account (or a new collaborator) the full MeatCODE context in ~30 minutes. -->

# Give a new Claude account the full MeatCODE context

**The principle:** nothing important lives *inside* a Claude account. Code, docs, agent rules, skills
and project state are in this folder (and GitHub); data is in Neon; tasks are in Asana. A new account
only needs four things pointed at them: **the folder, the skills, one Project, and the connectors.**

Before starting, double-click `Release Center/refresh-handoff.command` once. It regenerates the live
snapshot and packs the skills into `data/migration_kit/1_skills/`.

> `data/` is gitignored, so the packed `.skill` files exist only on the Mac that ran the script. On any
> other machine, pull the repo and run `refresh-handoff.command` there — it rebuilds them from
> `orchestration/skills/`, which *is* in git.

---

## Step 1 — Connect the folder (2 min)
Claude desktop → switch to the new account → Cowork → connect
`~/Documents/Claude/Projects/Claude Database`.
That alone gives every agent `CLAUDE.md` (auto-loaded), `START_HERE.md`, the whole repo, and the
`.env` files it needs to reach Neon.

## Step 2 — Upload the skills (5 min)
Settings → Skills → upload every file in `data/migration_kit/1_skills/`. Source of truth:
`orchestration/skills/` — if a skill changes, edit it there and re-run `refresh-handoff.command`.

| Skill | What it does for the team |
|---|---|
| `meatcode-agent-team` | Runs a parallel specialist team with disjoint file ownership and consolidates as Coordinator |
| `meatcode-curate-state` | Refreshes CLAUDE.md / PROJECT_STATE.md from agent outputs |
| `meatcode-schema-change` · `data-engineer` | Safe Neon schema changes with migrations + verification |
| `project-board-sync` | Turns task lists into the MVP board and briefs the team |
| `reaktzia-mockup` | Design tokens and conventions for the mockup |
| `integrate-dimensions-ai` | Adds Dimensions.ai to the literature pipeline |
| `weekly-progress-brief` | Weekly update docx |
| `meatcode-daily-sync` | Daily refresh of the context files from Gmail/Asana/prod/Neon — then set up the schedule: `orchestration/DAILY_SYNC_SETUP.md` |

## Step 3 — Create the Project (3 min)
Name: **meatCODE – GFI**. Paste this as the instructions — it's deliberately short, because the
folder carries the rest:

> You are working on MeatCODE (GFI Israel). Before anything else, read `meatCODE/START_HERE.md` and
> follow its reading order. All edits happen inside `meatCODE/`. Never print or paste secrets. Never
> fabricate chemistry or citations. Lior pushes to git from his Mac; you never run git. Log every change
> in `AGENT_UPDATE_LOG.md`.

Optional uploads to Project knowledge (only helps chat outside Cowork): `START_HERE.md`,
`platform_docs/SYSTEMS_MAP.md`, `platform_docs/SYSTEM_SNAPSHOT.md`, `PROJECT_STATE.md`.

## Step 4 — Memory seed (2 min)
Settings → Memory → Import → paste [`ACCOUNT_MEMORY_SEED.md`](ACCOUNT_MEMORY_SEED.md) (below its line).
If the org has memory switched off, skip it — the Project instructions and the folder already cover it.

## Step 5 — Connectors (10 min)
Reconnect: **Asana** (required — tasks), **Gmail**, **Google Drive**, **Google Calendar**, and as needed
Figma, Miro, Granola, Airtable. Then recreate the `weekly-progress-brief` scheduled task if you use it
(prompt in `data/migration_kit/4_scheduled_tasks/`).

## Step 6 — Smoke test (2 min)
New Cowork session, inside the Project:
> "Follow START_HERE.md, then tell me: which release production is running, the top open problem, the RAG
> eval baseline, how many paper↔molecule links exist, and the Asana phase we're in."

Expected: the `prod-…` tag shown in `SYSTEM_SNAPSHOT.md` · **B2 quarantine write-back** · **3.4 / 4.8 / 4.1** ·
the `source_molecules` count from the snapshot · **Phase 2 – MVP knowledge hub**. Five right answers =
the context transferred.

---

## What does NOT need moving
GitHub, Neon (both branches), Render, Asana, the `.env` files, the release scripts — none of them
belong to a Claude account. Desktop Cowork sessions and artifacts stay on the Mac.

## What can't be one click
Anthropic gives no API to create a Project, upload skills or connect apps on someone's behalf, so
Steps 2–5 are manual. Everything else is done by `refresh-handoff.command`.
