# Agent skills — source of truth

These are the MeatCODE agent skills, versioned with the repo so the team's engineering travels with
the code instead of living inside one Claude account.

- **Edit here**, not in a Claude account's skill cache.
- **Install** into any account: run `Release Center/refresh-handoff.command`, then upload the files it
  writes to `data/migration_kit/1_skills/*.skill` (Settings → Skills).
- To update a skill in an account, re-upload its `.skill` file (or use the skill-creator with overwrite).

| Skill | Role it serves |
|---|---|
| `meatcode-agent-team` | Project Coordinator — parallel specialist runs |
| `meatcode-curate-state` | Coordinator — keeps CLAUDE.md / PROJECT_STATE.md clean |
| `meatcode-schema-change`, `data-engineer` | Data Engineer — safe Neon migrations |
| `project-board-sync` | PM / Coordinator — MVP board + team briefing |
| `reaktzia-mockup` | UI/UX Designer — mockup tokens and conventions (legacy name; covers `app/meatcode_mockup.html`) |
| `integrate-dimensions-ai` | Data Engineer — literature ingestion |
| `weekly-progress-brief` | PM — weekly update |
| `meatcode-daily-sync` | Keeps the context files true daily from Gmail, Asana, meetings, prod, Neon — see `orchestration/DAILY_SYNC_SETUP.md` |

Personal skills (TAU lab reports, PM practice, morning brief) are intentionally not here.
