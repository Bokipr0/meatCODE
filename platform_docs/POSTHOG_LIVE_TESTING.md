# MeatCODE live testing — PostHog and private Neon dashboard

_Last updated: 2026-10-29 · Project Coordinator._

## Ready now

[MeatCODE Live Testing](https://eu.posthog.com/project/325792/dashboard/1066277) is a private, pinned dashboard in Lior's connected EU project325792 (currently named Default project). Six saved native insights measure testing starts, Oracle submitted/completed/failed outcomes, median successful-turn duration, scene usage, sanitized failure reasons and feedback ratings. All six queries execute. The initial query results contain no product events; dashboard creation does not prove ingestion. The existing generic onboarding dashboard was preserved.

The official posthog-js1.442.0 browser bundle is vendored under app/vendor/posthog with its license, lock, source map and SHA256 manifest. The application loads it only after current explicit testing consent. Public project settings are saved in ignored local configuration and, through merge updates, on the original production MeatCODE and dev-meatCODE Render services. Existing server credentials were preserved. No application deployment was triggered by this work.

Required public settings: POSTHOG_PROJECT_TOKEN, POSTHOG_API_HOST=https://eu.i.posthog.com, POSTHOG_PROJECT_URL=https://eu.posthog.com/project/325792, POSTHOG_DASHBOARD_URL=https://eu.posthog.com/project/325792/dashboard/1066277. These must remain in runtime configuration; no private PostHog API key belongs in the browser. Render changes take effect with a subsequent deployment.

## Private live view

Open http://localhost:8000/research-dashboard while the local Release Center server is running. It polls Neon every three seconds with environment and time-window controls, real totals, recent activity and deliberately submitted feedback. It works independently of Clarity/PostHog dashboard aggregation. Polling is best effort, not a zero-latency guarantee.

Hosted /research-dashboard serves the shell behind the existing site gate. Its data API additionally requires a distinct RESEARCH_ADMIN_TOKEN of32–256 printable characters in X-MeatCODE-Research-Admin; the shared site password is insufficient and cannot be reused. No new administrator token was generated in this change, so hosted private reads remain closed until one is securely configured. The dashboard keeps a supplied token in page memory only. Local loopback Release Center administrators need no separate token and may select dev/prod; hosted administrators can read only that service's environment.

The API is bounded/read-only/no-store, uses short statement/connect timeouts, and exposes hash labels instead of first-party session UUIDs. Cross-origin browser reads are denied. The administrator page loads no analytics SDK. Feedback comments are shown as text, never HTML. Session totals are active anonymous tab sessions in the selected window, not people.

## Consent and data boundaries

Consent version2026-10-29 adds PostHog. Prior opt-in requires renewal. Forward migration0017 was applied dev then production, allowing historical consent rows without rewriting them. Both scientific schemas were preserved.

Only approved event names plus environment, scene, numeric duration/source count and categorical error/rating/category reach PostHog. Autocapture, automatic pageviews/pageleave, surveys, feature flags, person profiles and PostHog replay are disabled. A strict before_send removes SDK URL/referrer/automatic properties while retaining ingestion-required public token and a separate ephemeral anonymous distinct_id. No prompt, answer, attachment, feedback comment or first-party deletion-capability UUID is included. Clarity remains the optional masked replay provider.

Stop/delete clears application queues, requests provider opt-out and deletes first-party records with a tombstone preventing late recreation. Already-started provider requests may finish; this does not claim to erase provider copies. Microsoft recordings and PostHog copies need their own provider administration. Ninety-day retention tooling remains manual; no automatic purge schedule was created.

## Clarity diagnosis and publication

Both hosted services still run commit6394c039749a. That exact GitHub source lacks the research script/routes/flag, and the intended SDK wrapper path is absent there. The October28 manual redeploy reused that old source. The public Clarity tag is reachable, but waiting for analytics cannot install missing application code. See [dated installation evidence](CLARITY_INSTALLATION_CHECK_2026-10-29.md).

Publish the reconciled current-main package through the documented dev→staging→production process. Avoid wholesale replacement from the stale local checkout: newer remote Science, Ecosystem and guided Oracle code must be preserved. The repository's ROLES.md/CLAUDE.md and team skill reserve Git/publishing for Lior. After staging publication, verify declined consent produces no collection, then opt in and check a real event in PostHog Activity and Clarity collect requests. Verify production separately after promotion. A healthy server or configured key does not prove Oracle model authentication.

## Verification evidence

- Native six-chart query execution and IDs: user_research_2026-10-29/posthog-dashboard.json.
- Backend45-test production suite, rollback-only SQL, consent migration and dev checks: Data lane handoff; no retained probe rows.
- Independent local HTTP→dev Neon test: accepted event visible immediately in private feed, session UUID hidden, cross-origin403, withdrawal deletes it and late write410. Owned event/session/tombstone cleaned; data/verification/research-dashboard-http-2026-10-29.json.
- Client fixtures cover renewed consent, blocked SDK, safe payloads, delayed-load withdrawal, escaping, memory-only dashboard auth, empty/error/live states and mobile layout. Fixture screenshots are illustrative and do not show actual tester traffic.

Real SDK check: one isolated consented local dev session sent session.started and scene.viewed to EU ingestion; both returned HTTP200 with zero page errors, Clarity blocked and no Oracle/model/private-text call. Automation detection was overridden only inside the isolated QA SDK copy; production SDK unchanged. First-party routes were intercepted for this provider-only check, retaining no Neon rows. A subsequent forced dashboard refresh confirms one session.started event in the saved testing-session chart: local SDK delivery and chart visibility are verified. Hosted capture remains unverified. See data/verification/posthog-live-sdk-2026-10-29.json and the release README. No fixture result is described as provider ingestion.
