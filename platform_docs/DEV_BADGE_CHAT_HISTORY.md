# DEV badge and Oracle chat deletion

_Last updated: 2026-10-29 17:47 UTC · Codex · clearer development context and history actions_

The new app/assets/environment-badge.js reads the authenticated same-origin /api/version.
Only env=dev adds a small DEV badge beside the MeatCODE brand across application scenes and
Live Insights. No badge appears for prod, failed requests or unknown environment. The Dev Area
header separately labels its developer-settings context beside the MeatCODE link.

The existing hidden-on-hover delete control is now an always-visible trash button with a28px
hit area, accessible label, tooltip and keyboard focus. It works for pinned and unpinned chats.
Deleting the active chat clears its visible conversation and active reference; localStorage is
updated and deletion survives reload. Other chats and saved Inventory items are preserved.
This deletes browser history only: demo-research copies have separate session-deletion controls.
No backend schema, retention rules, cloud configuration or deployments were changed.

Publish the new asset together with app/meatcode_mockup.html, app/dev/index.html and
app/internal/research-dashboard.html. Browser fixtures use synthetic APIs, not live model calls.
