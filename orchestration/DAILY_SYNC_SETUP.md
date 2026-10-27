<!-- Last updated: 2026-10-11 · Advisory · how the daily context loop is wired. -->

# Daily context sync — setup (2 minutes)

The loop is the **`meatcode-daily-sync`** skill (source: `orchestration/skills/meatcode-daily-sync/`).
It's already installed on Lior's personal account. It reads Gmail, Asana, meetings, production
and Neon, and rewrites the context files. It never writes to Gmail, Asana or the calendar.

## Run it on demand (any time)
In a Cowork session with the `Claude Database` folder connected, type: **"run the daily sync"**.

## Make it run every morning
Claude can no longer create scheduled tasks from inside a chat; create it once in the app:

1. Sidebar → **Scheduled** → **New task**
2. **Name:** `MeatCODE daily context sync`
3. **Schedule:** daily, 07:30
4. **Folder:** `Claude Database` (required — the task writes into `meatCODE/`)
5. **Prompt:** `Run the meatcode-daily-sync skill.`

**Caveats (from Anthropic's help pages, Oct 2026):** scheduled tasks run in the cloud. They can use
your remote connectors (Gmail, Asana) at any time, but they can **only reach the local folder while
the Claude desktop app is open on the Mac**. If the app is closed, the skill stops and says so instead
of writing elsewhere. Team/Enterprise cloud execution is in beta.

## What a run changes
`platform_docs/SYSTEM_SNAPSHOT.md` and `ASANA_SNAPSHOT.md` (regenerated) · `PROJECT_STATE.md` ·
`platform_docs/DECISIONS.md` · `platform_docs/PEOPLE.md` · `docs/meetings/<month>_record-from-email.md` ·
`START_HERE.md` §3 (only if a headline fact changed) · a "Daily context sync" entry in `AGENT_UPDATE_LOG.md`.

Files change on disk only. For GitHub to carry them, run `Release Center/deploy-dev.command` (the sync reminds you).

## In a new Claude account
Upload `meatcode-daily-sync.skill` with the other skills (`refresh-handoff.command` packs it), then repeat the steps above.
