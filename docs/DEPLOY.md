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

- **Free tier sleeps** after ~15 min with no visitors; the next visit takes ~30–50s to wake it. That's ideal for "don't waste resources." To keep it instant/always-awake, switch the plan to **Starter (~$7/mo)** in the Render dashboard (or in `render.yaml`).
- **Secrets live in Render's dashboard**, never in the repo. `.env` stays on your Mac and is gitignored. If you rotate a key, update it in Render → Environment.
- **Anyone with the URL can use the Oracle** (and spend your Anthropic credits). If you want it gated, add a simple shared password later — ask and I'll wire it in.
- **Database:** Neon is already in the cloud, so the deployed site reaches it directly. (Neon also auto-sleeps and wakes on first query.)
- **Custom domain** (e.g. `oracle.meatcode.org`) can be added in Render later if you want a branded address.

---

## Troubleshooting

- **Build fails on a missing package** → add it to `requirements.txt` and run `deploy.command` again.
- **Site loads but Oracle/expert map errors** → check the env vars in Render → Environment (`ANTHROPIC_API_KEY`, `DATABASE_URL`) are set correctly.
- **"Application failed to respond"** → the server must bind `0.0.0.0` and the host's `$PORT` (both already handled in `server/meatcode_server.py`).
