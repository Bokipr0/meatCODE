# Private Oracle chat research

29 October 2026 · Implementation and database verification complete; deployment verification pending.

## Scope and opt-in

Testing privacy has a separate unchecked checkbox for sharing submitted Oracle questions, displayed answers, clarification exchanges and citation IDs. Consent version `2026-10-29-chat-v1` renews the existing testing choice. Ordinary testing opt-in alone does not capture chat text. Capture starts with newly submitted turns after this choice; earlier chats, drafts, attachments and account profiles are not imported.

Text goes only to the authenticated same-origin `/api/research/chat` endpoint and the private `user_research.oracle_turns` table in each environment's existing Neon database. This is private schema separation, **not a newly created independent Neon branch**. Clarity remains masked and PostHog receives only its existing allowlisted lifecycle metadata. No transcript text enters either provider, server diagnostic logs, scientific evidence or model training.

## Viewing

Open `/research-dashboard` on the intended hosted service. Use its normal site login followed by its separate research-administrator credential, held only in page memory. Under **Oracle conversations · private**, select a conversation. Use the window selector (up to 90 days) to find older activity. The picker lists the latest 20 conversations in that window; each transcript loads in ordered pages of 20 turns. The local Release Center dashboard can select development or production. Hosted dashboards read only their own environment.

The viewer displays questions, responses, clarification options, source IDs and outcome. Text is rendered literally without HTML execution. It is not included in the dashboard summary or accessible through public/static exports. Necmettin's scientific read-only role cannot access the research schema or transcripts.

## Capture and limits

These are browser-observed transcripts, not a tamper-proof server audit. A turn is saved at submission, checkpointed during streaming, and finalized at completion, clarification, failure or interrupted stream. Delayed checkpoints cannot overwrite terminal answers. Network failures, blockers or closing a tab can lose unsaved text; a submitted/partial record may remain. Each question is capped at 12,000 characters and response at 64,000, with a visible truncation indicator. Conversations are tab/session scoped, not linked to named accounts or Clarity identities.

**Stop testing & delete session data** removes this tab's research session and all associated transcripts; a tombstone rejects late retries. This does not delete the user's own local Oracle history or third-party recordings. The existing 90-day maintenance command now includes transcripts; retention remains an operator-run task, not a newly scheduled automatic expiry.

## Database and maintenance

Migration `db/migrations/0019_oracle_chat_research.sql` was applied transactionally to development and production. Scientific table inventories were unchanged. The research migration runner, verification and private JSONL export/purge commands include `oracle_turns`. Old branch-copy material under `research_storage_2026-10-29` predates this table and must be refreshed and reviewed before use.

Verification: 61 Python tests passed against each database using rollback-only synthetic fixtures. Dedicated browser checks cover separate consent, question/answer capture, conversation ordering, clarification/failure, provider text exclusion, private viewing, pagination and literal text rendering. Deployment state will be appended after hosted verification.
