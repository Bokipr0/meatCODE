# Clarity installation check — 29 October 2026

_Last updated: 2026-10-29 10:45 UTC · Codex · verified live deployments against their actual GitHub source._

**The intended Clarity integration is still local. It is absent from both hosted builds.**
Production was manually redeployed on 28 October, but the deployment uses the same
older commit; it does not contain the newly prepared research integration.

| Check | Production | Staging |
|---|---|---|
| Service | [MeatCODE](https://dashboard.render.com/web/srv-d96ftplaeets73da7vng) | [dev-meatCODE](https://dashboard.render.com/web/srv-d9ghriu1a83c73dr8lj0) |
| Site | `meatcode-oracle.onrender.com` | `meatcode.onrender.com` |
| Live commit | `6394c039749a` | `6394c039749a` |
| Latest live deployment completed | 28 Oct, 16:36:18 UTC | 26 Oct, 07:23:45 UTC |
| Unauthenticated research-config request | HTTP 401, site gate active | HTTP 401, site gate active |

GitHub's current `main` also resolves to the same full commit,
`6394c039749ad0e6d7279dabd00a380dfb95ee87`. Inspection of that exact source establishes:

- [The deployed HTML](https://github.com/Bokipr0/meatCODE/blob/6394c039749ad0e6d7279dabd00a380dfb95ee87/app/meatcode_mockup.html)
  has no `user-research.js` inclusion, Clarity tag/project identifier or body masking marker.
- [The deployed server](https://github.com/Bokipr0/meatCODE/blob/6394c039749ad0e6d7279dabd00a380dfb95ee87/server/meatcode_server.py)
  has no `/api/research/` routes.
- [The deployed feature registry](https://github.com/Bokipr0/meatCODE/blob/6394c039749ad0e6d7279dabd00a380dfb95ee87/Release%20Center/features.json)
  has no `user_testing` flag. Fetching `app/assets/user-research.js` at that commit returns GitHub 404.

Filtered Render application logs from 29 October contained no research-script or
research-route requests. That supports the source finding; it does not establish
what Clarity itself received. The protected site/script/config requests returned
401, so no claim is made to have inspected an authenticated production browser.

The supplied public tag URL, `https://www.clarity.ms/tag/z4upnrbddu`, returned HTTP
200 JavaScript. It was **not executed**, and no collection request or real session
was generated. A downloadable tag does not prove that a website has installed it.
No Microsoft project settings or recordings were inspected or changed.

## What should happen after publication

The local integration requires enabled research configuration and explicit consent
before loading the tag. It also rejects unsafe page URLs and unmask overrides.
Those conditions are intentional. The local configuration endpoint was not
reachable during this check; local source is under active revision for PostHog.

Publish the reconciled integration through the existing dev-to-production Release
Center workflow; preserve the newer Science/Ecosystem/guided Oracle code. Then,
in an authorized signed-in browser, verify research config is enabled, accept the
optional-testing consent, check the tag and `collect` POST, and check the matching
Clarity live recording. Keep the existing site-password gate.

Microsoft documents live recordings and collection requests as installation
checks, while its FAQ separately allows a few hours for dashboard data. Waiting
cannot resolve an integration missing from the deployed code. References:
[verify installation](https://learn.microsoft.com/en-us/clarity/setup-and-installation/clarity-setup#verify-your-installation)
and [dashboard timing FAQ](https://learn.microsoft.com/en-us/clarity/faq#when-can-i-start-seeing-data-on-the-clarity-dashboard).

Evidence with timestamps and source hashes:
`data/verification/clarity-installation-2026-10-29.json` (ignored local verification output).
