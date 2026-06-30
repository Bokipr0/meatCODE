# MeatCODE — Agent Update Log

_Last updated: 2026-06-30 12:23 UTC · advisory session · created this log + update conventions_

> **Every agent appends an entry here at the end of any working session — newest at the top.**
> This is the detailed audit trail of who changed what, when, and why. The short in-file
> "Last updated" stamp is the quick marker; this log is the full story. Use UTC (`date -u`).
> `PROJECT_STATE.md` = current state; this file = the running history. Don't delete past entries.

## Entry template (copy this)
```
## YYYY-MM-DD HH:MM UTC · <agent / session label> · <short area>
- What:    <what changed, concretely>
- Files:   <paths touched>
- Why:     <reason / which task or request>
- Result:  <outcome, what works now>
- Next:    <follow-ups left open, if any>
```

---

## 2026-06-30 12:45 UTC · advisory session · Repo cleanup
- What:    Deleted junk + one exact duplicate from `meatCODE/`.
- Files:   Removed 6 `.DS_Store`, `server/__pycache__/` + `server/reaktzia-mvp/__pycache__/` (.pyc), and the duplicate `docs/MeatCODE for WUR.pdf` (kept the canonical `docs/decks/` copy).
- Why:     Lior asked to clean irrelevant files.
- Result:  Folder decluttered; no source/content/schema touched. (Note: sandbox can't delete on the mount — used the Cowork delete-permission flow.)
- Next:    Optional cleanup pending Lior's call — `pipeline/migrate_airtable.py` (one-time, already run) and `app/assets/MeatCODE_Atlas_ChordDiagram_v7_GFI.svg` (verify the mockup still uses it).

## 2026-06-30 12:23 UTC · advisory session · Update tracking (stamps + log)
- What:    Added the file-update conventions; created this log; created `meatCODE/.env` (empty key fields ready to fill).
- Files:   `CLAUDE.md` (new "File-update conventions" section + end-of-session steps), `AGENT_UPDATE_LOG.md` (new), `.env` (new, gitignored).
- Why:     Lior's request — every agent should stamp files it edits with a last-updated note, and keep a detailed shared update log.
- Result:  Convention is documented for all agents; `.env` is in place awaiting Lior's `ANTHROPIC_API_KEY`.
- Next:    Lior pastes his Anthropic key into `.env`, then runs `run_oracle.command`.

## 2026-06-30 ~12:00 UTC · advisory session · Oracle wiring + MVP design docs
- What:    Made the thin Oracle server demo-ready and drafted the two Phase-0 "define" docs.
- Files:   `server/meatcode_server.py` (serve repo root so `app/meatcode_mockup.html` loads; model → `claude-sonnet-4-6`; load `.env` from repo root), `run_oracle.command` (new double-click launcher), `docs/TAGGING_TAXONOMY_v0.1.md` (new), `docs/HUB_ARCHITECTURE_v0.1.md` (new), `PROJECT_STATE.md` (Oracle + docs status).
- Why:     Lior's "Oracle answering by tomorrow" + define tagging taxonomy v0.1 + hub architecture.
- Result:  Server compiles + SSE contract matches the mockup; taxonomy (7 faceted axes on existing schema) and tight-MVP architecture (Oracle/Literature/Expert/Molecular) drafted.
- Next:    Lior's key → live test; his topics `.md` to lock the Topic axis; Daniel sign-off on both docs.

## 2026-06-30 (approx, earlier) · setup + art-director sessions · Repo established
- What:    Built the single-source-of-truth repo and core conventions (summary of prior sessions).
- Files:   `CLAUDE.md`, `PROJECT_STATE.md`, `README.md`, `.gitignore`, `.env.example`; migrated code/docs/mockup/SQL/pipeline into the tree; added `db/connect.py`, `docs/DATA_DICTIONARY.md`, `db/migrations/`; `UI-UX Designer/` v8 mockup candidate; `sync_meatcode.command`.
- Why:     Consolidate scattered copies into one mounted repo all agents share; back it with GitHub `Bokipr0/meatCODE`.
- Result:  `meatCODE/` is the canonical working location; three-homes model (Git / Neon / Asana) adopted.
- Next:    First GitHub push from Lior's Mac; copy two iCloud-only files in; verify citable-corpus size in Neon.
