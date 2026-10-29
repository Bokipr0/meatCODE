> Current 29 October policy: only research_prod is active for input capture. Development/local capture is blocked. Use `verify.py --environment prod` for strictly read-only checks; never point positive synthetic fixtures at live production. See [production-only operations](../../platform_docs/PRODUCTION_RESEARCH_ONLY.md). Older dev migration/consent examples below are historical.

_Last updated: 2026-10-28 15:51 UTC · Data/Backend · isolated research storage, private export and manual retention/import operations._

# Product research storage

`user_research` is a separate PostgreSQL schema. Scientific evidence tables and Oracle retrieval never read it. The five tables are `sessions`, `events`, `feedback`, `withdrawals` and `clarity_exports`; scientific tables have no foreign keys into this schema. PUBLIC has no schema/table/sequence grants. The server uses its existing private database role; this does not create a new database account.

Explicit consent is required for typed first-party events and feedback. Events accept only the fixed names/scenes and `duration_ms`, `source_count`, `error_code`. Raw prompts, answers, URLs, user agents, IPs, emails and arbitrary JSON properties are rejected. The optional comment is deliberately submitted first-party feedback, never a Clarity property. No public listing/read endpoint exists.

Sessions and event IDs are UUIDv4. Possession of the session ID authorizes withdrawal under the existing site auth and Origin checks; do not expose or enumerate it. Withdrawal atomically deletes a session and cascades events/feedback, then preserves only a UUID/environment/timestamp tombstone for 90 days. Database transaction advisory locks serialize withdrawal and ingestion; queued requests cannot recreate a withdrawn session during that window. This deletes our first-party rows only; it does not delete recordings held by Microsoft.

## Configuration and HTTP contract

`server/user_research.py` exports `config(environ, app_env)`, `write_events(db_url, app_env, payload)`, `write_feedback(...)`, `withdraw(...)`. The HTTP glue supplies auth, same-Origin checks, payload-byte limit and effective enablement; module default `USER_RESEARCH_ENABLED` is false. `InputError`, `WithdrawnError`, `StorageError` expose safe `.code` and `.status` values of 400, 410, 503.

Environment is `dev` or `prod`. CLI settings start with the process environment. Locally, `.env` then non-empty `.env.dev` values overlay it for development. On Render (`RENDER=true`), private runtime variables are authoritative and no dotenv files are loaded. Credentials are never printed. The live migration script refuses a development target that equals production.

```sh
python3 pipeline/user_research/migrate.py --environment dev
python3 pipeline/user_research/migrate.py --environment dev --apply
python3 pipeline/user_research/verify.py --environment dev
```

Run production only after development passes. Migration `0016` contains no drops or scientific changes. The script strips its transaction wrapper, executes and verifies all tables/indexes/privileges in one transaction, then commits. Verification tests use rolled-back transactions, including withdrawal contention, environment separation, idempotency and quotas. They retain no test feedback/events.

## Review retained research privately

```sh
python3 pipeline/user_research/manage.py --environment prod export --from-date 2026-10-01 --to-date 2026-10-28
```

This explicit command exports JSONL to a newly created private-mode file under ignored `data/user_research/`; `--output /absolute/path/research.jsonl` selects another path. Existing files are never overwritten. Dates are UTC and inclusive, at most 90 days; default is the last 90 calendar dates. Each table is filtered by environment and its retention timestamp. No CSV is produced. Files contain explicit feedback and session capabilities: restrict access and delete exported copies when no longer needed. Research export retention is the operator's responsibility; database purge does not erase files already downloaded.

## Retention: manual, not scheduled

```sh
python3 pipeline/user_research/manage.py --environment prod purge
python3 pipeline/user_research/manage.py --environment prod purge --apply
```

The first command previews counts. Only `--apply` deletes rows older than 90 days from this schema. Active sessions use last-seen time; event/feedback rows use creation time; tombstones retain the full 90-day withdrawal window. **No automated purge or Clarity import job is installed or scheduled.** Until an operator runs it or schedules it, 90 days is a configured retention policy, not an enforced daily cleanup guarantee.

## Clarity dashboard aggregates

[Microsoft's Data Export API documentation](https://learn.microsoft.com/en-us/clarity/setup-and-installation/clarity-data-export-api) describes dashboard aggregates, not a raw-replay download API. It supports the preceding 1–3 days, up to three dimensions, ten requests per project per day, and at most 1,000 rows without pagination. Results use UTC.

The CLI fixes dimensions to Browser/Device/OS, removes page/URL/title/referrer metrics, and retains only allowlisted numeric metrics and bounded dimension labels. Unknown fields are discarded; never use this table as evidence or assume it contains full replay histories. Requests disable redirects to protect the bearer token. The token's project must match `CLARITY_PROJECT_ID`; the endpoint determines project access from that token.

```sh
python3 pipeline/user_research/clarity_import.py --environment prod
python3 pipeline/user_research/clarity_import.py --environment prod --days 1 --apply
```

Preview makes no database write or Microsoft request. `--apply` needs **server-only `CLARITY_EXPORT_TOKEN`**, generated by a Clarity project admin, and optional `CLARITY_PROJECT_ID` (default `z4upnrbddu`). Never send that token to browser configuration. Completed/pending imports deduplicate by UTC date/import environment/project/window. `--retry-failed` explicitly permits retrying failed requests. Reserved attempts count toward a transactional maximum of ten per project/day in one database. **Apply is restricted to the production importer** because separate databases cannot coordinate local counters; development supports preview only. Microsoft's project-wide quota still applies to other clients. A crashed pending reservation intentionally blocks duplicate same-day requests; review it administratively rather than blindly retrying. No real third-party request was made during setup because no export token was configured.

**Aggregate scope is the complete Clarity project.** API results have no environment/custom-tag filter here. If staging and production share a project, the snapshot includes both domains. The `environment` database column labels the import destination/context, not visitor traffic attribution; responses therefore report `scope: project`. First-party events and feedback remain separately tagged by their actual application environment. Do not interpret the aggregate snapshot as a production-only cohort or join it to individual sessions.
