<!-- Last updated: 2026-10-31 · Codex · Name-only Oracle introduction and session binding. -->
# Oracle tester names

In production demo mode, entering Oracle opens Soft's welcome dialog with one required name field and Continue. Testing still starts after login. The name is self-reported, not an authenticated account identity.

`POST /api/research/name` attaches the trimmed name (1–80 characters) to the current `(environment, session_id)` row in `user_research.sessions.tester_label`. It uses existing production-only intake, site login, origin, exclusion and rate-limit checks. The session lock makes retries idempotent and prevents relabelling an already named session. No schema migration or additional data store is needed.

The dialog closes only after a successful database acknowledgement. A failure leaves the field available for retry. Subsequent events, Oracle turns and feedback use the same session ID. Existing rows from earlier in that session acquire the name through the session join. Names never enter Clarity or PostHog payloads.

The dashboard shows the name and the same stable `session_label` alongside journey inputs, activity and feedback. This is a hash-derived display reference; the underlying session UUID is also a deletion capability and is not exposed in admin responses. Two sessions with the same name remain separate. A browser pseudonym is never treated as a person's identity.

A Web Lock prevents simultaneously open tabs from sharing an inherited sessionStorage identity. Duplicated tabs start a fresh session and ask for a name. Reloading a named tab preserves its session. Browsers without Web Locks conservatively start a new session on each load. To hand the device to a different tester, close the previous tester's tab and open a fresh tab.

Soft's existing art is a temporary welcome asset. The designer's final motion kit and hover-to-note interface remain separate follow-up work. Existing feedback is session-linked; explicit feedback-to-turn/event anchors still need the note integration. Do not infer an exact referenced Oracle turn solely from timing.

Verification: server validation/immutability tests, dashboard session separation, isolated Chromium tests for acknowledgement, retry, refresh, duplicated tabs, identical names, Oracle linkage and mobile layout. No synthetic production research rows are created by these tests.
