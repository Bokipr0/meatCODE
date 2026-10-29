# MeatCODE — Release Center, Analytics and Simulate fixes

_Last updated: 2026-10-27 11:53 UTC · Codex / Project Coordinator · reviewed local changes and production authentication evidence._

## What is ready

The local platform removes **Recent simulations**, **SLR family** and **Saved presets** from the Simulate sidebar. The profile card, simulator inputs, Predict action, results and synthetic-result labels remain.

The **Analytics zone** switch now controls the Analytics navigation button and opens the existing `#analytics` workspace. An explicit OFF wins over the older Analytics module setting. The older setting is only a fallback when Analytics zone is absent. Analytics workspace remains a separate Dev Area listing. No switch values were changed.

Release Center now describes switches as **saved settings for the next release**, shows feature locations, and compares saved production settings with the observed deployed build. An old deployment that does not report its switches is labelled **unverified**. A local release tag alone is no longer evidence that Render has deployed it. The new local-only status endpoint reads the fixed public production version endpoint without sending credentials.

The local server was restarted with these changes and remains available at [localhost:8000](http://localhost:8000). [Analytics](http://localhost:8000/app/meatcode_mockup.html#analytics) and [Simulate](http://localhost:8000/app/meatcode_mockup.html#simulate) were visually checked. The Analytics workspace remains a labelled preview with illustrative/demo data; this work did not implement real uploaded-data analysis.

## Service clarification — 2026-10-28

Lior confirmed the service updated was **dev-meatCODE** at meatcode.onrender.com. This resolves the service-identity question; it does not establish that original production received the key change. Render still returns original production's latest deploy as dep-dbg8rgd9fdbs73d4bnj0 (2026-10-27 11:41:48UTC), with no newer deploy as of this check. Direct repair to original **MeatCODE**, srv-d96ftplaeets73da7vng, at meatcode-oracle.onrender.com: set a valid ANTHROPIC_API_KEY through Render, save/deploy, then verify an authenticated Oracle answer. No key read/copied/changed or deployment triggered by agent.

## Production Oracle — still blocked by its credential

The original production service is **MeatCODE**, `srv-d96ftplaeets73da7vng`, at [meatcode-oracle.onrender.com](https://meatcode-oracle.onrender.com). It is distinct from Yochai's service with the `-0o99` hostname.

Lior updated its key and manually deployed. Deployment `dep-dbg8rgd9fdbs73d4bnj0` became live at **2026-10-27 11:41:48 UTC / 12:41:48 Zurich**, still on commit `6394c039749ad0e6d7279dabd00a380dfb95ee87`. The signed-in user request then reached Claude, but both guided-decision and answer calls returned **401 authentication_error: invalid x-api-key** at **11:43:09 / 11:43:13 UTC**. The model is configured as `claude-sonnet-4-6`. This is an authentication failure, not evidence that the Oracle endpoint is disconnected. A healthy web server or a key-present boolean does not verify model access.

Create a fresh key in [Claude Console](https://platform.claude.com/settings/keys), save its full value as `ANTHROPIC_API_KEY` in the [original service's Render Environment settings](https://dashboard.render.com/web/srv-d96ftplaeets73da7vng), then deploy the saved environment change. Keep the key out of chat and repository files. After it is live, one signed-in Oracle request must produce answer chunks, citations and a completed stream; check the matching logs. The local configured key also returned 401 and needs separate repair if using the local Oracle. [Anthropic error reference](https://platform.claude.com/docs/en/api/errors).

## Dev comparison — 12:53 Zurich

Lior reports that the dev-domain Oracle works. Staging logs show the request at11:53:14UTC followed by a frontend request containing its generated answer at11:53:50UTC, with no Oracle authentication error in that window. Both environments run the same commit/model. This supports a production environment/credential difference rather than a missing Claude integration; actual credential values were not read or compared. User reports having updated/deployed already, but Render still returns no original-production deployment newer than12:41Zurich (before the failed12:43test). Service identity is being clarified.

## Safe publication package

**These UI/backend changes are local and have not been published.** Current remote main contains newer Science, Ecosystem and guided Oracle work missing from the local checkout. Publishing the whole stale local checkout could regress those additions. Reconcile the checkout first; do not use a blanket publish of the present folder.

The two narrow patches here apply to the inspected production/main commit `6394c039749ad0e6d7279dabd00a380dfb95ee87`:

- `release-controls-current-main.patch` updates `app/release-center.html`, `Release Center/features.json` descriptions and `server/meatcode_server.py` status/version handlers.
- `simulate-analytics-current-main.patch` updates `app/meatcode_mockup.html`, preserving Science, Ecosystem, guided Oracle and hidden-Research navigation.

Both were applied sequentially using the system patch utility to temporary copies of the inspected remote files; every result matched its reviewed candidate exactly. If main advances, inspect and reconcile these patches against the new version first. Lior then uses the repository's normal dev → staging → production Release Center workflow. No Git, commit, promotion, deployment, feature-toggle write, database or credential mutation was performed by the agents.

## Validation and review

Python syntax and feature-registry JSON passed. All 17 nonempty inline scripts in the patched current-main mockup and the Release Center script passed JavaScript syntax checks. Browser fixtures checked canonical Analytics ON, canonical OFF with legacy ON, legacy-only fallback, direct-link selection, removed sidebar sections, retained simulator controls and preservation of newer navigation. The new status handler was checked for local-admin restriction, fixed destination, bounded response, safe fields and sanitized failures. Actual local endpoints responded successfully after restart. Production's old version correctly reports per-feature live state as unverified.

`verification.json` records patch checks and reviewed output hashes. `simulate-sidebar-clean-local.png` and `analytics-navigation-local.png` show the running local changes. These screenshots show the older local shell; they are not screenshots of a newly deployed production build. Runtime Oracle evidence is retained in the ignored `data/verification/oracle-connection-2026-10-27.json`.
