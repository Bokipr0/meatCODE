<!-- Last updated: 2026-10-31 · Codex · Name-only Oracle introduction and session binding. -->
# Oracle tester names

In production demo mode, entering Oracle opens Soft's welcome dialog with one required name field and Continue. Testing still starts after login. The name is self-reported, not an authenticated account identity.

`POST /api/research/name` attaches the trimmed name (1–80 characters) to the current `(environment, session_id)` row in `user_research.sessions.tester_label`. It uses existing production-only intake, site login, origin, exclusion and rate-limit checks. The session lock makes retries idempotent and prevents relabelling an already named session. The name uses an existing column; no additional data store is needed. The release also includes repair migration 0025 for missing legacy research tables discovered during verification.

The dialog closes only after a successful database acknowledgement. A failure leaves the field available for retry. Subsequent events, Oracle turns and feedback use the same session ID. Existing rows from earlier in that session acquire the name through the session join. Names never enter Clarity or PostHog payloads.

The dashboard shows the name and the same stable `session_label` alongside journey inputs, activity and feedback. This is a hash-derived display reference; the underlying session UUID is also a deletion capability and is not exposed in admin responses. Two sessions with the same name remain separate. A browser pseudonym is never treated as a person's identity.

A Web Lock prevents simultaneously open tabs from sharing an inherited sessionStorage identity. Duplicated tabs start a fresh session and ask for a name. Reloading a named tab preserves its session. Browsers without Web Locks conservatively start a new session on each load. To hand the device to a different tester, close the previous tester's tab and open a fresh tab.

Soft's existing art is a temporary welcome asset. The designer's final motion kit and hover-to-note interface remain separate follow-up work. Existing feedback is session-linked; explicit feedback-to-turn/event anchors still need the note integration. Do not infer an exact referenced Oracle turn solely from timing.

Verification: server validation/immutability tests, dashboard session separation, isolated Chromium tests for acknowledgement, retry, refresh, duplicated tabs, identical names, Oracle linkage and mobile layout. No synthetic production research rows are created by these tests.

## Live dependency repair

Preflight on 2026-10-31 found `feedback`, `withdrawals` and `clarity_exports` absent from `research-logs / research_prod`. The app calls withdrawals on every session write; the dashboard joins feedback. Migration `0025_restore_research_dependencies.sql` restores those established contracts and their scoped writer/reader grants. A transactional dry run was explicitly rolled back and absence rechecked before applying. Existing 3 sessions, 147 events and 4 Oracle turns were preserved; no synthetic production records were added. Missing historical feedback or withdrawal tombstones cannot be reconstructed by this schema repair.

Applied only to the dedicated production research database. The previously documented inactive `research_dev` database no longer exists, as confirmed by Neon; development/local intake stays disabled. No scientific branch or data was modified. Writer name-column privileges and reader joins were checked using their actual roles.

For a future repair, use the numbered migration in Neon's SQL Editor on the dedicated research database: inspect the missing objects, run the transaction, then check table presence and role grants. Do not rerun older restrictive migrations over newer session policies.
