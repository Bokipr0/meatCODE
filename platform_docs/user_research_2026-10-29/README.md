# MeatCODE live testing release package — 29 October2026

## Published update

User authorized publication. Both hosted services now run release20acea3e648e (29 October2026), with user_testing and analytics enabled. Production deploymentdep-dbhkn5vb9u1s73a0nsv0 is live; rollback tagprod-20261029-analytics-live-testing. Documentation follow-up2858a2e was pushed to main/dev with skip-render. The patch below is now historical: do not reapply it to the published branches. Private dashboard credentials were separately approved and configured securely. Actual hosted recordings require a signed-in tester’s opt-in and remain unverified.


_Last updated: 2026-10-29 · Project Coordinator._

Open [MeatCODE Live Testing](https://eu.posthog.com/project/325792/dashboard/1066277) for six private native PostHog charts. The official SDK1.442.0 and consent-gated integration are installed locally. Public PostHog settings are saved on original production MeatCODE and dev-meatCODE Render services; no private account token was copied. Application source publication is still required.

The local /research-dashboard view polls first-party Neon every three seconds. Its API needs separate hosted administrator authorization, or the local Release Center administrator. Shared site credentials alone cannot expose tester comments. No hosted administrator token was generated. See [operations/access guide](../POSTHOG_LIVE_TESTING.md).

## Publish this package

`meatcode-research-combined-main.patch` is the complete combined patch against inspected deployed/main commit6394c039749ad0e6d7279dabd00a380dfb95ee87. Apply it **instead of** the Oct27/Oct28 or Oct29 incremental patches. It contains earlier sidebar/Analytics/Release Center fixes, research integration and privacy guards, new PostHog SDK, forward consent migration0017, private live dashboard, tests and operations docs.

It preserves the newer remote Science/Ecosystem/guided Oracle code missing from the stale local checkout. Do not overwrite those newer files with stale local copies. Reconcile against any newer dev/main changes before applying. Lior publishes through the documented dev→staging→production workflow; no Git/publish/deploy operation was performed by agents.

`verification.json` records37 changed file hashes,1.19MB patch, clean dry-run and byte-exact reapplication to inspected originals, Python/JSON checks and remote-module preservation guards. `posthog-dashboard.json` records project/dashboard/insight IDs and native query definitions. SDK provenance and hashes are in app/vendor/posthog/manifest.json.

## Verification and limits

- Backend production45-test suite passed, including rollback-only database checks. Consent migration0017 applied dev then prod; historical data preserved.
- Browser fixtures cover consent renewal, payload minimization, delayed/blocked SDK, feedback isolation, dashboard memory-only auth, live/empty/error states, safe escaping/links and mobile layout. The screenshot in UI-UX Designer/2026-10-29_live_testing_dashboard.png contains **fixture data**, not actual tester totals.
- Independent real local HTTP→dev Neon: an event appeared in private feed, session UUID stayed hidden, cross-origin read403, withdrawal removed it and late retry410. All owned test data cleaned. Evidence: data/verification/research-dashboard-http-2026-10-29.json.
- The real vendored SDK serialized only approved fields in an intercepted-network browser check. For QA only, automation detection was overridden inside the isolated SDK copy; the production bundle and bot behavior were untouched.
- One consented local development session then sent session.started and scene.viewed through the actual SDK to EU ingestion, both HTTP200, with zero page errors. Clarity was blocked and no Oracle call or prompt/answer/comment was sent. First-party routes were intercepted in this provider-only check, so no Neon fixture was retained. Evidence: data/verification/posthog-live-sdk-2026-10-29.json. These are setup QA events, not production usage. A subsequent forced dashboard refresh confirms one session.started event in the saved session chart. Local delivery and query visibility are verified; this is not hosted production traffic.
- Clarity tag is reachable but both hosted apps lack the integration at their deployed commit. See [dated diagnosis](../CLARITY_INSTALLATION_CHECK_2026-10-29.md). No real Clarity recording was generated or verified.

After staging publication, verify declined consent produces no provider requests. Opt in with an ordinary signed-in browser, navigate, inspect PostHog Activity and Clarity collect requests, check the private first-party view, then stop/delete. Verify production separately after promotion. Environment settings only take effect in a subsequent deploy. Oracle authentication after the latest production redeploy remains separately unverified.
