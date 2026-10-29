# Clarity and user-testing delivery — 28 October2026

_Last updated: 2026-10-28 15:57 UTC · Project Coordinator · completed local and Neon verification; hosted activation pending._

## Ready

- Microsoft Clarity public project z4upnrbddu, explicit opt-in, advertising consent denied, whole-body masking, approved event names and environment/scene tags.
- First-party navigation/Oracle outcome events and submitted ratings/comments. No raw question/answer/attachment/account identity in the event stream or Clarity tags.
- Isolated live `user_research` schema on both existing Neon branches, with five tables, twelve indexes and no PUBLIC grants. Scientific/public inventory preserved. All test rows removed.
- Authenticated same-origin bounded APIs, duplicate handling, withdrawal locking/tombstones, private export protection and exclusion from shared scientific backups.
- Manual private JSONL export,90-day cleanup and safe aggregate importer. Real aggregate import awaits a server-only token and data; no scheduler or external export request was created.
- Render source configuration now preserves dashboard environment values instead of loading dotenv files on Render. This is a defensive source fix, not a repaired production credential.

[Operations and access guide](../USER_RESEARCH_CLARITY.md) explains where to see the Neon tables, the Clarity export limits and manual maintenance.

## What is still not live

The application changes are local, not committed/deployed. The local server was restarted and its research API tested end-to-end against dev Neon, including erasure and rejection of a late write. A real Clarity dashboard recording is not verified by the mocked browser tests. Hosted activation needs normal publication and a tester's opt-in.

Production Claude still rejects its active key: today's28 October12:39 UTC logs report 401 invalid x-api-key. The key exists, but key presence is not credential validity. The user confirmed updating dev-meatCODE; the separate original MeatCODE service still requires a valid key saved/deployed and an authenticated answer test. Exact service: https://dashboard.render.com/web/srv-d96ftplaeets73da7vng/env . No key was copied or changed by agents.

## Publication package

`meatcode-research-combined-main.patch` is one combined patch against the inspected main source at 6394c039749ad0e6d7279dabd00a380dfb95ee87. It includes the prior Oct27 sidebar/Analytics/Release Center fixes plus Oct28 research integration, new data modules/migration/tooling/tests and new documentation. It preserves the newer Science, Ecosystem, hidden-Research and guided Oracle code missing from the local checkout.

Apply this combined patch **instead of** the earlier incremental patches; applying both would duplicate the changes. Reconcile against the latest dev/main through Lior's normal Release Center workflow before publication. Do not blanket-publish the stale local application/server files, and do not assume this inspected main is still current if others have changed it.

The patch was applied independently to fresh inspected originals and matched all 24 reviewed output files exactly. Python/JSON/JavaScript syntax checks passed;31 offline Python tests passed with 3 live-only checks skipped in that run. The data specialist separately ran all 9 storage tests against each Neon branch with rollback-only fixtures. Browser fixtures checked consent, masking, minimized payloads, feedback isolation, SSE failure handling, withdrawal retry and no collection after withdrawal. Actual local HTTP → dev Neon persistence/deletion passed; independent read-only schema verification found zero retained rows on either branch.

## Review evidence

- `verification.json`: patch chain, reapplication, syntax and combined-candidate checks/hashes.
- `neon-schema-verification.json`: independently checked tables/indexes/private grants/empty rows on both branches.
- `http-neon-verification.json`: real local write, duplicate, feedback, invalid-content rejection, withdrawal, late-write rejection and cleanup.
- `testing-privacy-preview.png`: consent-dialog fixture; no actual Microsoft collection. Background is the local shell, not a deployed production screenshot.

No Git operation, app publication, deployment, real Clarity data collection, model call or credential mutation was performed. The Neon schema was applied; verification wrote only labelled temporary first-party test data and removed it.
