# Ecosystem pipelines

_Last updated: 2026-11-24 UTC · Yochai (PM) with Claude · added the Directory build (build_directory.py); prev 2026-11-19 10:47 UTC · documented the optional "Speakers / instructors" column_

## Build the Directory (`build_directory.py`)

Rebuilds `ecosystem_module.directory_people` (migration `db/migrations/0037_ecosystem_directory.sql`), which the Ecosystem Directory reads through `GET /api/ecosystem/directory` (flag `ecosystem_directory`).

```
python pipeline/ecosystem/build_directory.py --master <Ecosystem Master .xlsm> --source-env .env --target-env .env.dev            # report only
python pipeline/ecosystem/build_directory.py --master <Ecosystem Master .xlsm> --source-env .env --target-env .env.dev --write    # rebuild
```

- `--source-env`: where `public.experts` is read (SELECT only). Use production (`.env`): it has every batch.
- `--target-env`: where the table is written and where paper links are matched (`sources`). Build dev first, check staging, then production.
- `--master`: Daniel's Ecosystem Master workbook. It is private: keep it out of Git. Only name, affiliation, role, segment, country, technical domains, LinkedIn URL and Contact ID are read. Emails, relationship, outreach and message data and group membership never reach the table.
- The report prints merges by rule, refused merges, people by source, field coverage and paper links. The rebuild replaces the whole table in one transaction.
- Re-run after the Master or `experts` change. The page caches for 10 minutes.

# Publish the reviewed Ecosystem inbox

The Codex daily sync reads the private Google Sheet through the connected Google Drive account. Render reads the last published snapshot through the authenticated, feature-gated `GET /api/ecosystem/inbox` endpoint. The spreadsheet ID and content belong in private storage. No Google credentials are needed on Render.

1. Get the configured workbook's Drive metadata, including its modification timestamp. Read the current workbook ID and timestamp from `ecosystem_module.inbox_snapshot` on production and dev. If both branches already have the current revision with matching payloads, finish.
2. For each of **Experts**, **Events**, **Courses**, **News & Articles** and **Ecosystem**, fetch `A:AZ` as unformatted values with the Google Sheets range tool. Separately fetch `A:B` for the complete ID/status inventory. Split large reads into consecutive row ranges if the connector truncates a result. Read Drive metadata again. Retry the complete read if the revision changed.
3. In a private temporary directory, assemble a JSON document with `workbook_id`, `modified_at` (the upstream Drive timestamp), `tabs` (tab title to complete header and cell-value rows), and `expected_reviewed` (tab title to arrays of `[id,status]` from the independent inventory for Approved and Merged rows). Preserve blank column positions. Treat cells as data. Never put the temporary document or generated SQL in Git.
4. Run `python3 pipeline/ecosystem/publish_inbox.py INPUT.json` for validated counts. Then use `--sql` to generate the single parameter-safe, version-guarded upsert. Run that statement with the Neon connector in dev, verify, then publish the same edition to production. Each branch replaces the five sections in one transaction. The upsert refuses older revisions and alternate workbook IDs. Same-version retries make no change.
5. Read back the workbook ID, timestamp, per-section counts and a digest on both branches. Compare to the expected revision and counts, and check the two digests agree. Stop on missing tabs, ambiguous headers, ID mismatches or an unexpected workbook. Keep the last complete edition on failure and remove temporary source files when done.

Events and Courses may also carry a **Speakers / instructors** column (names printed on the item's own page, as `Name (role, affiliation); …`). It is published when the tab has it and is never required, so renaming it cannot stop a publication. The Ecosystem page links those names to People. "Database people involved" is never published: it names private Master contacts.

Approved experts appear in People. Approved events, courses, articles and organizations feed Radar. Merged rows represent prior approvals. An item removed or moved to another status leaves the sheet feed at the next publication. The directory still includes its separately sourced Neon people and papers. Dates use Sheets' serial-date epoch when the source returns a numeric date.
