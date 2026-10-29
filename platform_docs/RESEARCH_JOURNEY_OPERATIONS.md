# Development research dashboard and isolated journey storage

29 October 2026 · Implementation verified locally; hosted release verification pending.

## Open it

Development Dev Area (`https://meatcode.onrender.com/app/dev/`) links to **Live testing dashboard** at `/research-dashboard?environment=prod`. Use the development site's normal login and its separate RESEARCH_ADMIN_TOKEN. Production data is read through a restricted SELECT-only database connection, never the production site/admin credential. Credentials remain in page memory. Choose Last 24 hours or a longer window for older activity. Hosted production remains limited to its own environment.

The dashboard refreshes every three seconds, with pause/manual refresh. It shows module clicks separately from scene views, a live input ledger, private transcripts and recorded lifecycle/error events. The ledger has server date/time, a random tester reference (optional explicitly supplied tester code), shared input, elapsed milliseconds since testing opt-in, and an opaque Clarity reference. The identity is per consented tab, not a named account or a cross-device user. Unsent text, passwords, uploads and arbitrary form fields are not scraped. Supported inputs are submitted Oracle questions/answers and explicitly submitted feedback.

## Actual Neon destination

Project `holy-mode-78356834` (GFI database), child branch **research-logs** (`br-lingering-morning-alh02jz5`), parent production `br-wandering-frost-al93o2yk`.

Two new initially empty databases hold only research tables: **research_prod** and **research_dev**. Their ordinary application roles are research_prod_writer and research_dev_writer. **research_prod_reader** can only read production research, even with transaction read-only mode disabled. Scientific DATABASE_URL values are unchanged. The child is a normal copy-on-write branch: its inherited neondb snapshot still exists but is unused by research ingestion; restricted research writers cannot SELECT scientific sources there. This is branch/database isolation within the same project, not a separate account/project. No inherited neondb or parent permissions were changed. The setup API also created three unused branch management roles; they were not deployed as application credentials or shared.

Runtime RESEARCH_DATABASE_URL selects only the appropriate research database. RESEARCH_DATABASE_REQUIRED=true prohibits silent fallback to scientific storage. Development also has RESEARCH_PRODUCTION_DATABASE_URL containing only the reader credential. Production does not get the cross-environment credential. Private local settings match hosted routing; all values remain ignored and outside source control.

Existing research records were copied in bounded, idempotent transactions, with read-only source snapshots. Withdrawal tombstones are preserved and take priority over copied sessions; original records are retained pending a separately approved cleanup. No scientific rows were copied into either research database. The historical snapshot in unused inherited neondb is normal branch behavior. Copy reconciliation after deployment handles late legacy writes. New session data is written only to research storage after cutover.

## Consent and Clarity

Lior’s later instruction in the MeatCODE chat supersedes optional activation during demos. Default demo policy **2026-10-29-demo-v1** starts tracking and new-chat capture on the first trusted interaction, with a visible notice and stop/delete controls. This is recorded as first-use activation, not checkbox consent. RESEARCH_DEMO_MODE=false restores the separate optional **2026-10-29-journey-v1** flow. Optional tester code is entered deliberately, not read from an account/profile. The timer and references survive reload within the same consented tab; historical missing values remain NULL. Stop testing deletes that session's private research records and blocks late retries. The existing 90-day purge/export tools include transcripts and new columns; retention remains manually operated.

Only the independent opaque clarity_ref is sent to Microsoft as custom tag **research_reference**, after the applicable versioned testing policy activates. The session deletion capability, tester code, pseudonym and question/answer text never reach Clarity or PostHog. Clarity stays masked. Match the reference in the ledger with Clarity Filters → Custom tags → research_reference, then compare the server timestamp and elapsed timer with the recording timeline. Microsoft documents custom tags and their processing delay at https://learn.microsoft.com/en-us/clarity/filters/custom-tags . Recording delivery must be observed in the actual account; browser fixture emission does not prove receipt.

Supported navigation produces **module.clicked** in Neon/PostHog and both module.clicked and module.<scene>.clicked events in Clarity (Oracle, Science, Ecosystem, Simulate, Analytics and other allowlisted controls when available). These are actual click handlers, not inferred route views. Existing legacy scene.viewed records cannot reconstruct past clicks. In the Clarity screenshot, the specific URL pattern, New users: Yes and device selection can exclude recordings: clear/narrow filters intentionally and select the correct environment/date. Heatmaps and first-party named events measure different things.

## Administrator command panel

Commands are **status**, **errors**, **activity** only. They inspect fixed public service health/version and bounded consented research events. Origin, custom header and distinct admin authorization are mandatory. The production reader has no writes, so these checks cannot change production. This is not a shell, SQL console, redeploy control or a complete export of Render stack traces/diagnostic logs. Public health indicators say configuration presence, not a successful live model call.

## Verification

Migrations0020 and0021 applied to both research databases with zero PUBLIC grants. 81 Python checks passed per destination with rollback-only fixtures. Four browser suites passed privacy, module clicks, Clarity reference, timer/reload persistence, transcript safety, dashboard controls and responsive layout. Actual local HTTP save/read/click/withdraw tests passed; production read-only activity/status/error commands worked and shell/cross-origin requests were rejected. Actual research reader writes and research-writer scientific SELECT were denied. Deployment verification is appended after rollout.
