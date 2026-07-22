_Last updated: 2026-07-22 · Advisory · dev + production split for MeatCODE_

# Two environments: a place to build, a place users live

You now have **two separate servers** and **two separate databases**:

| | Where you experiment | What users see |
|---|---|---|
| **Name** | `meatcode-dev` (staging) | `meatcode-oracle` (production) |
| **Git branch** | `dev` | `main` |
| **Database** | Neon `dev` branch | Neon main (production) |
| **Who can reach it** | just you (password) | the world |
| **Cost** | free tier (sleeps when idle) | Starter, always-on |

The rule: **you only ever work on `dev`.** Nothing reaches the public site until you run one command that copies your approved `dev` onto `main`. Production can never be edited by accident.

```
   edit files
      │
      ▼
  run-local        →  see it instantly on your Mac (localhost, dev DB)
      │
      ▼
  deploy-dev       →  try it on the hosted PRIVATE staging site
      │
      ▼
  promote-to-prod  →  "bring it to the air": dev → main, public site updates
      │
      ▼
  rollback-prod    →  (only if needed) put the public site back
```

---

## One-time setup (your part — about 15 minutes)

Do these **once**, in order. Steps 1–4 are in your dashboards; step 5 is a double-click.

**1. Neon — make the dev database.** ✅ (You've done this.)
Neon console → your project → Branches → create a branch named `dev`. Copy its **connection string** — that's your dev `DATABASE_URL`. While you're there, **rotate the production password** (Roles → reset) and update it in Render prod + your local `.env` — it's still the old one.

**2. Anthropic — make a dev key.** console.anthropic.com → API Keys → create one named "MeatCODE dev". This keeps dev testing off your production budget.

**3. GitHub — make the `dev` branch.** Either double-click **`setup-dev-branch.command`**, or on GitHub: open the repo → branch dropdown (`main`) → type `dev` → "Create branch: dev from main." This is what makes `dev` show up in Render.

**4. Render — create the dev service.** New + → Web Service → same `Bokipr0/meatCODE` repo →
   - **Branch:** `dev`
   - **Instance type:** Free
   - **Build:** `pip install -r requirements.txt`  ·  **Start:** `python3 server/meatcode_server.py`
   - **Environment variables:**
     - `APP_ENV` = `dev`
     - `DATABASE_URL` = your **dev** Neon string (step 1)
     - `ANTHROPIC_API_KEY` = your **dev** key (step 2)
     - `SITE_PASSWORD` = a password (keeps staging private)
     - `SITE_USER` = `meatcode`
   - Name it `meatcode-dev`. Note its URL — that's your private staging link.

   **On your existing production service**, add `APP_ENV` = `prod` (and confirm its `DATABASE_URL` is the production one, not the dev branch). `/api/version` will then show `env: dev` or `prod` so you can always tell which site you're on.

**5. Local dev file.** The first time you double-click **`run-local.command`**, it creates `.env.dev` and opens it. Paste your **dev** key and **dev** Neon URL there. It's gitignored — it never leaves your Mac.

> ⚠️ **The one rule that protects real data:** the dev database URL goes in the dev service and in `.env.dev`. The production URL goes **only** in the production service. Never paste the production URL into `.env.dev`.

---

## Everyday workflow

1. **Edit** your files (mockup, server, whatever). You're on the `dev` branch — you never leave it.
2. **`run-local.command`** → previews at `http://localhost:8000` instantly, using the dev DB. Fastest way to catch mistakes. Ctrl+C to stop.
3. **`deploy-dev.command`** → pushes to the hosted staging site. Open your `meatcode-dev` URL and check it for real (same environment as production, just private).
4. Happy? **`promote-to-prod.command`** → shows you the exact diff about to go live, you type `yes`, and the public site updates in ~1–2 minutes. Each promotion is tagged (`prod-YYYYMMDD-HHMM`).
5. Something broke? **`rollback-prod.command`** → pick a previous snapshot; the public site reverts. Then fix on `dev` and promote again.

That's the whole loop. `run-local` for speed, `deploy-dev` for a real check, `promote-to-prod` to go live.

---

## Your two questions, answered

**Do both databases run at the same time?** Yes. A Neon branch is a full, independent live database with its own connection string. Production keeps using the main one; dev uses the branch. They run simultaneously and are isolated — anything you do in dev (queries, migrations, pipeline runs, wiping a table) can't touch production. It's a point-in-time *fork*, not a live mirror: new production data won't appear in dev automatically. If you ever want dev to have fresh production data, make a new branch (or reset the dev branch) in Neon.

**Does promote actually update my live server?** Yes. It pushes your approved build onto `main`; Render's production service auto-deploys on every push to `main`, so it rebuilds and the public site updates (~1–2 min). The URL never changes. Confirm it's live by refreshing, or check `/api/version` (it shows the commit and `env: prod`).

---

## How promotion works under the hood (for peace of mind)

- You always sit on `dev`. `promote-to-prod` does `git push origin dev:main` — it fast-forwards production to the exact commit you validated. No files are hand-copied, so the two can't silently drift.
- Because it's a fast-forward, if anyone ever committed straight to `main`, the push is **rejected** and your live site is left untouched — a deliberate safety catch.
- Every promotion tags the release, so rollback is just "point `main` back at an earlier tag."

---

## Troubleshooting

- **macOS won't open a `.command` file** ("unidentified developer"): right-click it → Open → Open. Only needed the first time for each script.
- **"dev branch not found" in Render:** run `setup-dev-branch.command` (or create it on GitHub), then refresh Render's branch list.
- **A push asks you to sign in to GitHub:** finish the sign-in, then double-click the script again.
- **Staging looks stale:** the free dev service sleeps when idle and takes ~30–60s to wake on the first visit. Give it a moment.
- **"Which site am I looking at?"** open `/api/version` — `env` is `dev` or `prod`.
- **Promotion says "already identical":** there's nothing on `dev` that isn't already live. Nothing to do.

---

## Files in this setup

- `setup-dev-branch.command` — one-time: create the `dev` branch.
- `run-local.command` — run dev on your Mac (localhost).
- `deploy-dev.command` — push to the private staging site.
- `promote-to-prod.command` — put dev live (dev → main).
- `rollback-prod.command` — revert the public site to an earlier release.
- `deploy.command` — the old single-environment publish button; superseded by the above. Keep it or delete it; it still pushes the current branch.
