# Independent research-log storage — prepared 29 October2026

Status: application change prepared and54 offline tests pass (5 live-only skips). No Neon branch/database has been created and no storage connection has switched. Existing production logging continues to its current research schema.

## Intended destination

Create a dedicated Neon branch `research-logs` in the existing project, using schema-only initialization so scientific rows are not copied. Disable automatic branch expiry for persistent logs. Neon schema-only branches start an independent root line within the project. Create two empty databases on that branch: `research_prod` and `research_dev`, each with its own research application role. The actual research databases contain only the user_research schema; the inherited empty scientific structure, if present in a default database, is not used.

This separates log data and application connections from scientific storage. Project administration/billing remain shared; this is not a separate Neon account or a complete organizational access boundary. New roles should have access only to their research database: revoke PUBLIC CONNECT on those databases and grant the intended roles, keeping administrative recovery access. Do not copy scientific credentials into the research connection.

Official reference: https://neon.com/docs/manage/branches and https://neon.com/docs/guides/branching-schema-only . Account creation/permissions must be completed through Neon; a SQL connection alone cannot create a Neon branch.

## Application preparation

The patch routes HTTP ingestion, private dashboard, export, purge, Clarity aggregate import and migration/verification tooling through RESEARCH_DATABASE_URL. Scientific DATABASE_URL remains unchanged. RESEARCH_DATABASE_REQUIRED=true disables legacy fallback after cutover: a research connection failure cannot redirect logs into scientific storage. Before cutover, absent research settings preserve the existing working logger.

Each environment needs a distinct research connection. These values are private and belong only in Render and ignored .env/.env.dev, never Git or chat. The existing dashboard administrator credential and site gate remain in effect.

## Safe cutover

1. Finish Neon connection. Provision the dedicated branch, two databases and scoped roles. Check plan limits before creating resources; do not enable auto-expiry for a persistent log branch.
2. Apply existing research migrations0016 and0017 to the empty research databases, dev first. Verify the five tables, indexes and private grants, plus no unrelated destination tables.
3. Privately set RESEARCH_DATABASE_URL locally for each environment. Run copy_storage.py without --apply to preview. It requires distinct source/target endpoints or databases, a research-only target, and bounded rows.
4. Run the reviewed copy with --apply. It reads source in a read-only repeatable snapshot, writes only the target in a transaction, preserves first-party identifiers/timestamps and honors deletion tombstones. It does not print comments, identifiers or connection strings. Originals are preserved.
5. Deploy routing code to staging while legacy fallback remains available; test strict routing and target failure isolation. Switch staging runtime research connection, set RESEARCH_DATABASE_REQUIRED=true, wait for deployment, then run the copy again to reconcile late source writes/withdrawals. Repeat production only after staging verification.
6. Verify actual new capture goes exclusively to each research database and the private dashboard reads that same destination. Recheck migration copies and source/target counts using privacy-safe verification. Scientific Oracle queries must continue against unchanged DATABASE_URL. Keep the legacy copy until reconciliation and an explicit later retention decision; do not delete it automatically.

The copy script is a bounded migration tool, not a permanent dual writer. Ingestion/withdrawal cutover needs deployment completion and final reconciliation before calling storage independent. A source/target disagreement stops the transaction for review.

## Current access blocker

Neon is available for installation but is not connected in this chat. There is no Neon management CLI or API key in the existing configuration. The app explicitly rejected automated access to its own installation UI; the user must click Install and approve the Neon connection. No private key should be pasted into chat.
