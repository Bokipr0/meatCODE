# Live Insights dashboard access

_Last updated: 2026-10-29 17:45 UTC · Codex · owner-requested navigation/access changes_

Dashboard replaces the18 right-side topbar Inventory buttons. Dev Area and Backups remain.
The link opens /research-dashboard. Production Operations is immediately below the brand header.
The Dev Area production-testing card continues to request environment=prod.

The dev site reuses its verified shared-password Basic login for dashboard, journey, transcript
and read-only operations APIs. No extra token is required. This explicitly authorizes all holders
of the dev-site password; the Dev Area flag is visibility, not a developer/admin role check.
Empty/wrong/duplicate credentials and cross-origin browser requests are denied. The production
site still requires its distinct research-admin token (or the existing local cockpit boundary).
Dev-to-prod monitoring still requires the explicit RESEARCH_PRODUCTION_DATABASE_URL, whose
existing read-only scope is preserved. No scientific database fallback is introduced.

RESEARCH_DEV_LOGIN_ACCESS=false restores the extra-token requirement on dev. No credentials,
Render settings, data or deployments were changed. Publish the dashboard/server modules and
frontend together through the established release workflow. Browser fixtures use synthetic APIs;
they are not hosted access or live database verification.
