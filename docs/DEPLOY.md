# Deploying MeatCODE — your "edit offline, publish when ready" setup

_Last updated: 2026-07-07 · advisory session · Render always-on deploy + quick tunnel_

You have two ways to let other people use the Oracle. They serve different needs.

| | **Always-on link (Render)** | **Quick tunnel (`share_oracle.command`)** |
|---|---|---|
| Public URL | Permanent, never changes | Temporary, changes each run |
| Works when your Mac is off? | **Yes** | No — needs your Mac on + window open |
| How you publish updates | Run `deploy.command` (push) | Just restart the script |
| Cost when nobody's using it | Free tier sleeps (no waste) | Your Mac + credits stay engaged |
| Best for | The real shared link for collaborators | A quick live preview in a meeting |

**Your intended workflow — "work offline, then publish" — is the Render path.** You edit locally with everything off, and only when you run `deploy.command` does the live site change.

---

## The loop, once it's set up

1. **Edit** anything in `meatCODE/` on your Mac — frontend (`app/…`), backend (`server/meatcode_server.py`), etc. Nothing is public yet; nothing is running; no cost.
2. **Test locally** if you want: double-click `run_oracle.command`.
3. **Publish:** double-click **`deploy.command`**. It commits your changes and pushes; Render rebuilds and updates the **same public URL** in ~1–2 minutes.
4. Collaborators refresh the link and see your latest — even if your Mac is now closed.

---

## One-time setup (about 15 minutes)

**Prep (already done in the repo):** `render.yaml` (the blueprint), `requirements.txt` (dependencies), and the server now reads the host's port automatically.

1. Go to **render.com** and sign up (you can sign in with GitHub).
2. Click **New +  →  Blueprint**.
3. **Connect the `Bokipr0/meatCODE` GitHub repo.** Render reads `render.yaml` and proposes a web service called `meatcode-oracle`.
4. When prompted for the two secret values, paste them (they are stored in Render, never in the repo):
   - `ANTHROPIC_API_KEY` — your Anthropic key.
   - `DATABASE_URL` — your Neon connection string (the `postgresql://…` one).
5. Click **Apply / Create**. Render builds and starts it (first build ~3–5 min).
6. You get a permanent URL like `https://meatcode-oracle.onrender.com`.
   **Share this + the mockup path:** `https://meatcode-oracle.onrender.com/app/meatcode_mockup.html`

That's it. From now on, `deploy.command` is your publish button.

---

## Good to know

- **Always-on:** `render.yaml` is now set to the **Starter plan (~$7/mo per service)**, which is always awake — no idle spin-down, no cold-start delay. Enable it in the Render dashboard: **your service → Settings → Instance Type → Starter** (you'll add a payment method there). The free plan sleeps after ~15 min idle (30–60s to wake) and caps at 750 instance-hours/month — fine for casual demos, not for an always-available link.
- **Secrets live in Render's dashboard**, never in the repo. `.env` stays on your Mac and is gitignored. If you rotate a key, update it in Render → Environment.
- **Private access (password gate):** the server now supports a shared username + password. Set **`SITE_PASSWORD`** in Render → Environment to a strong password and the whole site (mockup, Oracle, API) requires it — a browser login prompt appears, and only people you give the password to get in. Username defaults to `meatcode` (override with `SITE_USER`). Leave `SITE_PASSWORD` unset and the site is open to anyone with the link. `/api/health` stays open so uptime checks still work. This is enough to keep the public out and protect your Anthropic credits; for a bigger/rotating audience, step up to Cloudflare Access (email-based) later.
- **Database:** Neon is already in the cloud, so the deployed site reaches it directly. (Neon also auto-sleeps and wakes on first query.)
- **Custom domain** (e.g. `oracle.meatcode.org`) can be added in Render later if you want a branded address.

---

## Troubleshooting

- **Build fails on a missing package** → add it to `requirements.txt` and run `deploy.command` again.
- **Site loads but Oracle/expert map errors** → check the env vars in Render → Environment (`ANTHROPIC_API_KEY`, `DATABASE_URL`) are set correctly.
- **"Application failed to respond"** → the server must bind `0.0.0.0` and the host's `$PORT` (both already handled in `server/meatcode_server.py`).
