<!-- Last updated: 2026-10-11 · Advisory · every external system MeatCODE depends on, how to reach it, and who owns it. Static facts only — live numbers are in SYSTEM_SNAPSHOT.md. -->

# MeatCODE — Systems map

One page per system: what it is, where it lives, how an agent or a new account reaches it, and what
must never happen. **Live numbers (row counts, flags, tags, routes) are in
[`SYSTEM_SNAPSHOT.md`](SYSTEM_SNAPSHOT.md)** — regenerate it with `Release Center/refresh-handoff.command`.

```
                 ┌──────────── Lior's Mac ─────────────┐
                 │  ~/Documents/Claude/Projects/        │
 Claude account ─┤    Claude Database/meatCODE/  (repo) │── push ──▶ GitHub  Bokipr0/meatCODE
 (Cowork/Code)   │    .env  .env.dev   (secrets, local) │              │ dev  ──▶ Render meatcode-dev    ─▶ Neon dev branch
                 │    Release Center/*.command          │              │ main ──▶ Render meatcode-oracle ─▶ Neon production
                 └──────────────────────────────────────┘
 Tasks & milestones: Asana "MeatCODE - Open Flavor & Aroma Initiative" (GFI workspace)
```

---

## 1. The local folder — the thing you connect

| | |
|---|---|
| Path | `~/Documents/Claude/Projects/Claude Database` (the repo is the `meatCODE/` subfolder) |
| Connect in | Claude desktop → Cowork → add folder. Any account on this Mac can connect the same folder; the bytes don't move. |
| Rule | Every edit happens inside `meatCODE/`. The parent folder and the iCloud `GFI Database` folder are legacy. |
| Can't do from Claude | **git**. The Cowork sandbox can't lock files on the mounted folder. Lior commits/pushes via the `.command` scripts. |

## 2. GitHub

| | |
|---|---|
| Repo | `https://github.com/Bokipr0/meatCODE` (private, owner `Bokipr0`) |
| Branches | `dev` = where all work happens · `main` = production. Never commit to `main` directly. |
| Release tags | `prod-YYYYMMDD-HHMM`, one per promotion — these are the rollback points |
| Auth | Lior's GitHub sign-in on the Mac. No token is stored in the repo. |
| Gitignored | `.env*` (except `.env.example`), `data/*`, `__pycache__`, `.vscode/` |

## 3. Neon Postgres — the data

| | |
|---|---|
| What | The single source of truth for sources, molecules, experts, claims, properties |
| Branches | **production** (used by `meatcode-oracle`) and **`dev`** (used by `meatcode-dev` and local runs) — independent live databases |
| How to connect | `DATABASE_URL` in `meatCODE/.env` (production) and `meatCODE/.env.dev` (dev). Agents read it from the file; it is never printed or pasted. |
| Schema history | Forward-only numbered SQL in `db/migrations/` (`NNNN_description.sql`). Apply to **both** branches. |
| Schema changes | Use the `meatcode-schema-change` skill. Three checks before any drop: `count(col)=0`, no dependent views, and a repo grep shows no code reads it. |
| Console | console.neon.tech → project → SQL Editor (Lior's login) |
| Open advisory | Rotate the production password; give dev its own Anthropic key. |

## 4. Render — the servers

| | Production | Staging |
|---|---|---|
| Service | `meatcode-oracle` (declared in `render.yaml`) | `meatcode-dev` (created in the dashboard) |
| URL | https://meatcode-oracle.onrender.com | private URL in the Render dashboard |
| Branch | `main` (auto-deploys on push) | `dev` (auto-deploys on push) |
| Plan | Starter, always on | Free, sleeps when idle |
| Runtime | `python` · start `python3 server/meatcode_server.py` · health `/api/health` · `/api/version` shows `env` + commit | same |
| Env vars | `ANTHROPIC_API_KEY`, `DATABASE_URL`, `SITE_PASSWORD` (secret, set in dashboard) · `SITE_USER=meatcode` · `APP_ENV=prod` · `MAILLARD_MODE=mock` · `UNPAYWALL_EMAIL` (optional) | same, with `APP_ENV=dev` and the dev Neon URL |
| Hard limit | A `runtime: python` service **cannot run Docker** — the Maillard simulator needs its own `runtime: docker` service (commented out in `render.yaml`). | |

## 5. The release loop (all on the Mac, in `Release Center/`)

| Script | Does |
|---|---|
| `run-local.command` | Runs the server at `localhost:8000` against the **dev** DB |
| `deploy-dev.command` | Commits + pushes `dev` → staging rebuilds |
| `promote-to-prod.command` | Shows the diff, asks `yes`, fast-forwards `dev → main`, tags `prod-…` → production rebuilds |
| `rollback-prod.command` | Points `main` back at an earlier `prod-…` tag |
| `release-center.command` | Local admin cockpit: flag toggles, version history, rollback (works only on loopback with `RELEASE_CENTER=1`) |
| `refresh-handoff.command` | Regenerates `SYSTEM_SNAPSHOT.md` and re-packs the agent skills |

Full guide: [`TWO_ENVIRONMENT_WORKFLOW.md`](TWO_ENVIRONMENT_WORKFLOW.md) · flags: [`RELEASE_CENTER.md`](RELEASE_CENTER.md).

## 6. Asana — tasks and milestones

| | |
|---|---|
| Project | **MeatCODE - Open Flavor & Aroma Initiative** · id `1215201551726181` · workspace *Good Food Institute* |
| Link | https://app.asana.com/1/167772284987522/project/1215201551726181 |
| Owner | Daniel Dikovsky · members include Lior, Yochai Maytal, Nir Goldstein, Noga Sela Shalev, Anton Slavkin, Hadas Rajchenberg |
| Sections | Phase 0 setup (May–Jun) · Phase 1 foundation (Jun–Aug) · **Phase 2 MVP knowledge hub (Sep–Nov 2026)** · Phase 3 validation (Nov–Jan) · Phase 4 scale-up proposal (Jan–Mar 2027) |
| Custom fields | Workstream · Priority · Output Type · Audience · Confidence · Value/Effort score · MVP Inclusion · status |
| Status updates | Monthly, posted by Yochai (latest: *Oct 1*) |
| Rule | Asana owns tasks and priorities; the repo owns technical reality. Read Asana live through the connector — don't copy task status into docs. |

## 7. Anthropic / Claude

| | |
|---|---|
| API keys | Production key in Render prod + `.env`; dev should have its own key (open advisory item) |
| Model | Production reports **`claude-sonnet-4-6`** (`/api/version`, 2026-10-11); set via the `MODEL` env var — `.env.example` still shows the older default |
| Agent tooling | Claude Cowork (desktop) and Claude Code, both pointed at the same `meatCODE/` folder |
| Skills | Source of truth in `orchestration/skills/` (committed). Upload the packed `.skill` files to any new account. |
| Connectors used | Gmail, Google Drive, Google Calendar, Asana, Figma, Miro, Granola, Airtable (legacy source of the original data) — reconnect per account; the org's policy decides which are allowed |

## 8. Never

- Paste or print `ANTHROPIC_API_KEY`, `DATABASE_URL` or `SITE_PASSWORD` into chat, docs, Asana or a Claude Project.
- Put the production `DATABASE_URL` in `.env.dev`.
- Commit to `main` directly, or run git from the Cowork sandbox.
- Present mock simulator output or placeholder screens as real. Invent chemistry or citations — unknown stays NULL.
- Expose publisher full text externally. Store derived facts + span locators only.
