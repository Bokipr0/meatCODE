# Release Center repair — 29 October2026

GitHub authentication and Render branch wiring were verified working. The local dev branch had earlier diverged; it was backed up and reconciled without force. Publishing had not followed that local repair. Toggling a switch writes only the local registry; Git push and a successful Render deployment remain necessary.

The old action handler returned success after spawning macOS open/Terminal. It did not observe a script failure, so the browser could not distinguish a failed push from a deployed release. Some recent documentation commits also intentionally skipped Render; pushing an existing skipped commit does not imply a new hosted build.

The repaired local handler runs a tracked publishing job, reads the real exit status and sanitized Git output, rejects concurrent jobs and exposes job status only on the local administrator cockpit. Job launch additionally requires a same-origin request, a custom release header and explicit confirmation. Hosted services cannot run these actions. Production confirmation is performed in the cockpit; direct command-file use retains its Terminal yes prompt. The browser waits for /api/version to match the pushed target before declaring it live; timeout remains explicitly unverified.

Both launchers check branch ancestry before committing, show real errors, stop on failures and refuse to delete an existing Git lock. The resolver prefers canonical Release Center files over archival copies. No GitHub credential or repository key was rotated.

Analytics and simulation switches are saved OFF in dev and production. Simulate navigation/starter/deep links now follow maillard_sim, alongside its existing API gate. Analytics navigation/deep links and direct workspace routes follow analytics. Neither scientific tables nor research-log collection is disabled by these module switches.

Verification:55 offline tests pass (5 previously verified live-only tests skipped), shell and inline JavaScript syntax pass. Isolated browser confirms hidden Analytics/Simulate, hidden simulator starter, disabled deep links returning to Oracle and zero page errors. Release-job tests verify actual script failure reporting, origin protection, concurrency and remote-ref success verification. Hosted deployment checks are recorded after publication in data/verification.

Flag updates now serialize the entire read-modify-write operation and atomically replace the JSON file; a concurrent30-toggle probe preserved every change and registry metadata. Explicit deployments create a normal release marker after skipped-render documentation commits, preventing silent no-deploy outcomes.

## Verified deployment

Both sites now run41872cbe0bb7cfea01ed76409a515ec361f2bc27, with Analytics and Simulate switches off and healthy startup. Productiondep-dbhlth4s728c73da8n40; stagingdep-dbhlsp29lscs739ttusg. Rollback tagprod-20261029-1557. Research collection remains enabled. Refresh the local Release Center to load the new job-progress interface. The launcher reuses an existing healthy local cockpit.
