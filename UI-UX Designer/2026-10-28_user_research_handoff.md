# Optional user testing and Clarity integration

_Last updated: 2026-10-28 · Codex UI/UX · implemented locally and verified with isolated browser fixtures; unpublished._

## Files and publication order

- `app/assets/user-research.js`: optional consent, metadata-only events, explicit feedback, withdrawal and masked Microsoft Clarity project `z4upnrbddu`.
- `app/meatcode_mockup.html`: static `data-clarity-mask="true"` on the whole body, one external script at the end, and small Oracle lifecycle hooks. The Oct27 sidebar/Analytics work is preserved.
- `tests/test_user_research_client.cjs`: isolated headless-browser network fixtures; no real Microsoft or production requests.
- `UI-UX Designer/2026-10-28_user_research_main.patch`: **telemetry-only** HTML patch based on `/private/tmp/meatcode-ui-main-after.html`, the Oct27 reviewed remote-main candidate. Apply Oct27 UI patch first, then this Oct28 patch. Do not apply it directly to the original main file or overwrite main with stale local HTML.

Inspected main remained blob `850b4a208c83ebfe9c1754e463baa48540b403d5`. Combined candidate `/private/tmp/meatcode-research-main-after.html` preserves remote Science, Ecosystem, guided Oracle and the prior requested UI fixes. The new asset is a separate file to include in the release. No Git operation, deployment, backend edit, environment mutation or shared-log edit was performed by this lane.

## Behavior and privacy boundary

`GET /api/research/config` must return enabled and the matching consent version before the consent UI appears. No SDK or event collection starts until opt-in. The small **Testing privacy** button reopens consent/feedback settings. The feedback rating requires a deliberate choice. Comment text, limited to 2,000 characters, goes only to MeatCODE's explicit feedback endpoint; event properties contain only bounded durations, source counts and enum error codes.

The SDK loads only on the main app URL with an empty query and an allowlisted scene hash. An unsafe query/hash skips Clarity without changing the route; first-party events can still work and use `referrerPolicy:'no-referrer'`. The entire body is masked before SDK execution. Any unmask descendant makes SDK loading fail closed. No prompt, answer, attachment, user email, account identifier or source metadata is passed to this module. Clarity receives allowlisted event names and scene/environment tags only. The first-party session UUID is a deletion capability, stored in sessionStorage, and **never** sent to Microsoft. Clarity recordings are not linked to first-party session IDs or stored replay URLs.

Microsoft's official [ConsentV2 documentation](https://learn.microsoft.com/en-us/clarity/setup-and-installation/clarity-consent-api-v2) specifies `window.clarity('consentv2', {ad_Storage:'denied', analytics_Storage:'granted'})`. Advertising storage remains denied. The [masking API documentation](https://learn.microsoft.com/en-us/clarity/setup-and-installation/clarity-api) documents `data-clarity-mask="true"`. The consent documentation says denied consent can continue cookieless tracking, so withdrawal also calls `clarity('stop')` (confirmed by Microsoft repository maintainers in [issue 75](https://github.com/microsoft/clarity/issues/75)) and reloads after first-party deletion succeeds, ensuring the SDK is absent on the new page.

Withdrawal stops future collection immediately, clears the queue and active session, aborts pending first-party requests, requests deletion from the server and keeps only a pending deletion UUID if retry is needed. Deletion controls remain reachable even when the server disables collection. A withdrawal tombstone on the backend must reject later writes for the same UUID to close in-flight server races. The UI distinguishes deletion of MeatCODE session data from management of earlier Microsoft recordings. The 90-day first-party retention policy does not claim automatic expiration; coordinator/storage must configure and operate cleanup. Microsoft retention and masking settings require separate Clarity dashboard review.

## Oracle event boundary

The Oracle request contract is unchanged. The UI calls `startOracle()` without question text. Sources provide only an array length. The SSE `done` event records completion, an SSE `error` records model-unavailable failure, and EOF without a terminal event records unknown failure. A finished turn cannot emit a second terminal outcome, so HTTP 200 with error followed by done cannot count as success. Fetch rejection and HTTP 401 use enum-only network/session-expired outcomes. No research code clones or stores the response body.

## Verification

Both local HTML and the patched remote candidate passed all inline-script parse checks (14 local, 17 remote) and isolated Chromium interaction tests with zero page errors. Browser fixtures verified no collection before consent, masking before SDK execution, minimized event and Clarity payloads, explicit ratings, successful and failed Oracle outcomes, feedback isolation, withdrawal retries/no later collection, disabled configuration, unsafe query handling, and pending deletion while disabled. The main patch applied exactly to the Oct27 candidate. These tests use a stubbed SDK/API; they do not assert a real Clarity dashboard recording or Neon persistence. Coordinator/backend checks cover those connections before release.

Run browser tests with Node and Playwright available, optionally setting `PLAYWRIGHT_MODULE` to the package location and `PLAYWRIGHT_EXECUTABLE` to an existing Chromium binary. Set `RESEARCH_HTML=/private/tmp/meatcode-research-main-after.html` to verify the remote candidate.

## Ready-to-paste log entry

2026-10-28 · Codex UI/UX — Added opt-in, whole-body-masked Microsoft Clarity project z4upnrbddu and first-party metadata/feedback client in `app/assets/user-research.js`; integrated one external script and content-free Oracle lifecycle hooks into the mockup, preserving Oct27 UI fixes. Added explicit rating/category/comment feedback, same-origin JSON/custom-header requests, sessionStorage UUIDs, bounded metadata, no account identity, consent withdrawal/deletion retry and complete SDK unload after successful withdrawal. Official ConsentV2/masking docs checked. Isolated Chromium tests against local and current-main candidate plus syntax and patch-chain checks pass, zero page errors. Main-safe Oct28 patch and handoff saved under `UI-UX Designer/`; no deployment or real SDK capture performed. Backend tombstones and retention cleanup/dashboard settings remain coordinator verification responsibilities.
