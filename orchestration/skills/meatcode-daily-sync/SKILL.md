---
name: meatcode-daily-sync
description: Refresh the MeatCODE context files from live Gmail, Asana, meetings, production and Neon so START_HERE / PROJECT_STATE / DECISIONS / PEOPLE / ASANA_SNAPSHOT are true as of today. Read-only on every external system; every new fact dated and sourced. Use when Lior says "run the daily sync", "update the context", "refresh MeatCODE status from Gmail and Asana", "what changed since yesterday on MeatCODE", or when the daily scheduled task fires.
---

# MeatCODE daily context sync

You keep the MeatCODE record true. You do not do project work. By the end of a run, the context files
reflect everything that happened up to today, and every new fact is dated and traceable to a source.

## Where things are
- Repo folder (Mac): `/Users/lior/Documents/Claude/Projects/Claude Database/meatCODE`. In a bash sandbox it is under `/sessions/*/mnt/Claude Database/meatCODE` (`ls -d /sessions/*/mnt/"Claude Database"/meatCODE`). If the folder isn't reachable (desktop app closed), stop and say so — don't write anywhere else.
- Read first, in order: `START_HERE.md`, `PROJECT_STATE.md`, `platform_docs/DECISIONS.md`, `platform_docs/PEOPLE.md`, `platform_docs/ASANA_SNAPSHOT.md`, the newest file in `docs/meetings/`. The last sync date = the newest "Daily context sync" entry at the top of `AGENT_UPDATE_LOG.md` (else 2026-10-11).

## Hard rules
1. **Read-only on every external system.** Never send, draft, reply, label or archive email. Never create, complete, comment on, reassign or edit Asana tasks. Never change calendar events. Never run git or any `.command` script.
2. **Never invent.** Every added line carries a date (YYYY-MM-DD) and a source: `Gmail: <thread subject>`, `Asana: <task/status title>`, `Calendar: <event>`, `Meeting: <title>`, `Prod /api/version`, `Neon snapshot`. Unclear → write "unclear".
3. **No secrets:** never print or write `.env` contents, connection strings, keys or tokens. No phone numbers or private email addresses.
4. **MeatCODE/GFI work only.** Ignore university, exchange, job-search, personal, newsletter, promotional and automated-digest mail (including Lior's own research digests).
5. **Preserve history.** Never delete a decision or a person; mark reversals "SUPERSEDED by <date>". Only generated files (`SYSTEM_SNAPSHOT.md`, `ASANA_SNAPSHOT.md`) are rewritten in full.
6. **Ownership:** edit only `PROJECT_STATE.md`, `START_HERE.md` §3, `platform_docs/{DECISIONS,PEOPLE,ASANA_SNAPSHOT}.md`, `docs/meetings/*`, and append to `AGENT_UPDATE_LOG.md`.

## Steps
1. **Live snapshot.** From the repo folder: `python3 orchestration/build_system_snapshot.py` (if psycopg2 is missing: `pip install psycopg2-binary --break-system-packages`). It rewrites `platform_docs/SYSTEM_SNAPSHOT.md` from live Neon, git refs and production `/api/version`. If Neon or prod is unreachable, the file says so — carry that into your report.
2. **Asana.** Project `1215201551726181`. Get the project (`include_sections: true`) for `current_status` and `task_counts`; get every task (page through all pages) with `opt_fields=name,completed,completed_at,assignee.name,due_on,memberships.section.name,modified_at`. `get_tasks` returns top-level tasks only, so also run `search_tasks` with `projects_any=1215201551726181`, `is_subtask=true`, `completed=false` (opt_fields `name,assignee.name,due_on,parent.name`) to catch open/overdue subtasks; label every count "top-level" or "incl. subtasks". Rewrite `platform_docs/ASANA_SNAPSHOT.md` in its existing structure: header (date, totals, phase, latest status + colour) · §1 overdue · §2 completed since the previous sync (keep ~3 weeks) · §3 Lior's open tasks, re-checking each row's evidence against the repo, `SYSTEM_SNAPSHOT.md` and `PROJECT_STATE.md`, with a *suggested* status (state clearly it is not applied to Asana) · §4 due in the next 14 days.
3. **Gmail.** Search `(meatcode OR "meat code" OR GFI OR Daniel OR Yochai OR "Yoav Ram" OR Yizhou OR WUR OR Atlas OR Pablo OR publisher OR GROBID) newer_than:3d`, pageSize 25 (overlap is deliberate — skip threads already recorded). Open relevant threads with `get_thread`, `PLAIN_TEXT`. Extract only decisions, commitments/asks (who owes what to whom, by when), new people, scheduled meetings, and system facts (Render, Neon, GitHub, credentials, budget).
4. **Meetings + calendar.** Wispr Flow meetings since the last sync (open MeatCODE ones with the transcript); if a calendar connector exists, MeatCODE events in the next 7 days.
5. **Write.**
   - `docs/meetings/<YYYY-MM>_record-from-email.md` (create the month's file in the existing style): dated entries under topic headings.
   - `platform_docs/PEOPLE.md`: last contact + open thread; add new people in the right section.
   - `platform_docs/DECISIONS.md`: explicit decisions at the top of "Decided" (who, why, source); proposals under "Positions stated"; refresh "Waiting for a decision" from Asana.
   - `PROJECT_STATE.md`: §1–2 if prod/dev changed (from the snapshot) · §5 only verified changes (e.g. the B2 count) · §6 if Asana changed · §7 upcoming · update its stamp line.
   - `START_HERE.md` §3: only if a headline fact changed.
6. **Validate.** Re-open the source for at least three facts written today and confirm each exactly. Confirm every number in `PROJECT_STATE.md` / `START_HERE.md` equals `SYSTEM_SNAPSHOT.md` or Asana. Fix mismatches.
7. **Log.** Insert above the first `## ` entry of `AGENT_UPDATE_LOG.md`: `## <today> · Daily context sync` — sources read (with counts), files changed, new decisions, new asks, any connector that failed.

## Report to Lior (short)
- What changed since the last sync (3–6 bullets).
- What needs him: asks addressed to him · Asana tasks whose evidence says done/overdue (he updates Asana himself) · whether production is behind dev.
- If files changed: "Run `deploy-dev.command` so GitHub carries today's context."
- Any connector that failed or returned nothing — say so plainly. Never cover a gap.
