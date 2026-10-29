# One production-only research cache

29 October 2026 · Implementation and verification underway.

**Active intake:** research-logs branch / research_prod database only. Development/local/staging capture is disabled in code and development Render settings, with the development writer NOLOGIN. Its empty research_dev database is inactive; it was not deleted. No development records are selected or offered in the dashboard.

Production ingestion requires all three: APP_ENV=prod, the hosted Render runtime, and the actual production Host meatcode-oracle.onrender.com. A local process that defaults to APP_ENV=prod is still rejected. Database migration0022 adds production-only CHECK constraints on all six research tables. Flags or a wrong connection cannot turn a development request into production intake. Admin reads from the development site remain read-only against production.

## Internal testing

On the production platform, open Demo testing → Details & feedback, then enable **Internal testing: exclude this browser**. A secure host-only cookie blocks writes server-side, including stale pages. Local storage stops current browser collection across open production tabs; each tab withdraws its own active first-party session and reloads excluded. The setting persists across normal reloads. Ordinary Oracle use and administrator dashboard access still work. Explicitly turning it off clears the exclusion and resumes the configured demo policy. Deletion failures retain a retry marker. Earlier unrelated sessions and provider recordings are not erased by this switch.

Recognized crawler/bot, HeadlessChrome/Playwright and command-line automation user agents are blocked before any database/body processing; navigator.webdriver skips browser initialization. X-MeatCODE-Internal:1 is an additional opt-out header for internal tools, never an access grant. This is heuristic bot exclusion, not proof that every accepted visitor is human. Invited users/individual accounts would be needed for stricter participation control.

The fixed dashboard source is **Production data only**. Snapshot, transcript, journey, activity and status commands reject environment=dev, even for local administrators. The existing development-site login access is preserved; production still uses its separate research-admin gate. No research writer is exposed to the development dashboard.

Positive database fixtures run against the inactive QA database and roll back. Production is checked with a rejected development insert only; no synthetic event is successfully stored. Browser flows intercept all traffic and provider scripts. Existing production records are retained; unknown historical records are not retroactively classified as bots or staff.
