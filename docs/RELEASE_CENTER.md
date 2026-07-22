_Last updated: 2026-07-23 · Advisory · feature flags + the Release Center_

# The Release Center — control what's live, per feature

Your private cockpit for deciding, feature by feature, what's visible in **dev** vs **production** — without touching code. Deploy your code once; turn features on where and when you want.

## The idea in one line

Every experimental feature is wrapped in a **switch** that's ON in dev and OFF in prod. The code ships to both environments, but a feature only *appears* where its switch is on. Flip it on for prod when you're ready.

## Open it

Double-click **`release-center.command`**. It starts a local server (admin powers on) and opens the dashboard at `http://localhost:8000/app/release-center.html`. It runs only on your Mac — it is never public.

You can also press **H** anywhere inside the dev app to slide the Release Center open as an overlay (H or Esc to close). On your local cockpit it's fully interactive; on the hosted dev site it opens **read-only** (viewing only — changing and deploying happen on your Mac). It never appears on production.

## Use it

1. Each feature has two switches: **Dev** and **Prod**. Flipping one saves to `features.json` instantly.
2. Flip a feature ON for **Dev**, then hit **Deploy to staging** — check it on your `meatcode-dev` URL.
3. Happy? Flip it ON for **Prod**, then hit **Promote to production**. A Terminal window opens where you type `yes` to confirm. It goes live.
4. The Deploy / Promote buttons just launch your existing `deploy-dev.command` / `promote-to-prod.command`, so every safety prompt stays.

Nothing reaches users until you Promote.

## How it works (so you can trust it)

- **`features.json`** (committed, at the repo root) holds every flag with a `dev` and a `prod` boolean. One file, both environments — each server reads only its own column based on `APP_ENV`.
- The mockup fetches `GET /api/flags` on load and turns on any feature that's on for its environment (each becomes a `ff-<name>` body class).
- The write/deploy endpoints and the dashboard page exist **only** on the local cockpit: they require `RELEASE_CENTER=1` (set solely by `release-center.command`, never on Render) **and** a loopback caller. On any hosted server they return 404 — verified.

## Adding a feature flag

1. Add an entry to `features.json`:
   ```json
   "my_feature": { "label": "My feature", "description": "What it does.", "dev": true, "prod": false }
   ```
2. Gate the feature on `body.ff-my_feature` in CSS, or check it in JS (`document.body.classList.contains('ff-my_feature')`).
3. It now appears in the Release Center automatically.

## Flag #1: the new logo

`new_logo` is wired as the first example (currently a placeholder restyle of the wordmark until the real asset is dropped in). It's ON in dev, OFF in prod — so staging shows it and the public site doesn't. Drop the real logo file in and it swaps in behind the same switch.
