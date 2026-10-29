# PostHog browser SDK

_Last updated: 2026-10-29 UTC · Codex · install official npm browser bundle with provenance._

`posthog.js` is the unchanged official `posthog-js` **1.442.0** browser bundle,
`dist/array.no-external.js`. Its companion source map retains the upstream name.
The download resolved the latest npm release on this date; no version was guessed.
Upstream licensing is retained in `LICENSE`; exact hashes, npm integrity and source
paths are recorded in `manifest.json`. `package-lock.json` records dependency resolution.

The bundle exposes `window.posthog.init`, `.capture`, `.opt_in_capturing` and
`.opt_out_capturing`. Merely storing or serving this file does not initialize it.
The application loads `/app/vendor/posthog/posthog.js` only after explicit research
consent and initializes it with project configuration supplied by the server.
MeatCODE's project token and ingestion host are supplied only at runtime by that
configuration. No account credentials are included here; upstream SDK defaults
remain part of the unchanged vendor bundle.

The application disables automatic capture, pageviews, recordings, feature-flag
requests, surveys, performance/exception/dead-click collection and external
dependency loading. Clarity remains the separate opt-in replay integration.
The no-external bundle also avoids a runtime dependency on CDN script downloads.

To update, resolve a new release in a temporary folder with `npm install posthog-js
--ignore-scripts --no-audit --no-fund`, copy the same upstream artifacts, refresh
the manifest/lock, and rerun the client privacy tests before publication. Do not
replace the SDK with a hand-written analytics stub.

Official references: [JavaScript SDK](https://posthog.com/docs/libraries/js),
[configuration](https://posthog.com/docs/libraries/js/config), and
[collection controls](https://posthog.com/docs/privacy/data-collection).
