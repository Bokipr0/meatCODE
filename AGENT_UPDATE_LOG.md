# MeatCODE — Agent Update Log

_Last updated: 2026-07-01 11:18 UTC · art-director session · UI/UX v8 polish + dashboard upgrade_

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

## 2026-07-05 ~13:30 UTC · Claude Design session · New screen handoff (Home / Map / Oracle / Research)
- What:    Produced 4 high-fidelity screen designs against the MeatCODE Design System (Claude
           Design, outside the mounted sandbox) — Home (workspace dashboard), Community Map,
           Food Oracle (ask/empty state only), Research phase picker. Packaged as a dev handoff
           with screenshots, annotated source, and exact design-token values.
- Files:   `UI-UX Designer/design_handoffs/2026-07-05_home-map-oracle-research/` (new — README.md,
           screenshots/, source/). Filed into the repo + logged by the deploy-templates session
           (2026-07-05) — the handoff was prepared outside git write access.
- Why:     Lior's request to hand deployed/designed screens to the agent team for implementation.
           These four screens are the "templates I created in Claude Design" that the deploy-templates
           session built the serving infrastructure for (`app/templates/` + `meatcode-api.js`).
- Result:  Bundle ready to build from — README is self-sufficient (layout, colors, type, tokens,
           per-screen component notes, explicitly flagged gaps).
- Next:    (1) Decide the build target — deploy as server-served HTML wired to the live Claude+Neon
           backend via `meatcode-api.js` (matches Lior's stated goal), or recreate as React in the
           planned Next.js frontend (handoff author's assumption). (2) Oracle's answered/loading
           states are designed in the source file (typing dots, streamed answer + CiteChips, paper
           modal) but only the empty/ask state was screenshotted. (3) Map's ranked list showed two
           variants (plain "MATCH" vs. numeric score) — the numeric-score version is in the source.

## 2026-07-05 13:30 UTC · deploy-templates session · Claude Design templates → live server
- What:    Made Claude Design templates deployable so their elements talk to Claude + Neon through the same FastAPI server the canonical mockup uses. Added a static mount + listing endpoint to the server, a shared drop-in connector script, a self-populating gallery, a README, and two reference templates.
- Files:   `server/reaktzia-mvp/server.py` (added `StaticFiles` import, `/api/templates` listing endpoint, `/templates` static mount of `app/templates/`, updated root + docstring), `app/templates/meatcode-api.js` (new — SSE `ask()` mirroring the mockup's proven parser, plus `health`/`paper`/`recentPapers` and zero-JS `data-mc-*` auto-wiring), `app/templates/index.html` (new — gallery that self-populates from `/api/templates`), `app/templates/README.md` (new — 3-step deploy + wiring docs), `app/templates/example-oracle.html` + `oracle-demo.html` (reference templates).
- Why:     Lior asked to deploy all templates built in Claude Design so their elements interact with his Claude/MCP the same way the HTML mockup does.
- Result:  Any exported Claude Design `.html` dropped into `app/templates/` is served at `http://127.0.0.1:8000/templates/`, appears in the gallery automatically, and gains live Claude+DB access by including `<script src="meatcode-api.js"></script>` and either `data-mc-*` attributes or the `MeatCODE.*` JS API. Verified: server.py parses; template path-resolution + listing logic confirmed against the real folder (index.html correctly excluded). Full uvicorn boot not run in-sandbox (fastapi/psycopg2/anthropic not installed here) — runs via `run_server.command` on the Mac as usual.
- Next:    Getting the actual Claude Design projects into the repo needs a manual export (DesignSync needs an interactive claude.ai login not available in cowork) — export each template's HTML and drop it in `app/templates/`, or use Design's "Send to Claude Code Web". Templates that need endpoints beyond ask/papers will need new `/api/*` routes.

---

## 2026-07-01 11:18 UTC · art-director session · UI/UX v8 polish + dashboard upgrade + repo consolidation
- What:    Art-direction pass on the product mockup, in two rounds, plus consolidating design work into the repo and fixing the parent-folder routing that causes agent drift.
- Files:   `UI-UX Designer/MeatCODE_mockup_v8_UIUX-polish.html` (new candidate, moved in from a loose out-of-repo folder), `UI-UX Designer/DESIGN_NOTES_v8.md` (new), parent `Claude Database/CLAUDE.md` (added redirect banner → `meatCODE/`), `PROJECT_STATE.md` (v8 entry + decision), this log.
- Why:     Lior asked Claude to act as standing art director — improve visuals + screen flow; then "keep working it" (round 1 read as too subtle); then centralize everything under meatCODE.
- Result:  Round 1 — avatar wine→teal (all scenes), research bubbles + globe recolored to teal/coral/olive, emoji bell→SVG icon, onboarding personas realigned to the 4 real audiences, dashboard now fronts all 5 domains, Simulate marked "Preview", molecular names monospaced. Round 2 (dashboard) — per-domain color accents (left border + tinted icon chip), hover-lift cards, hero eyebrow + 4-metric stat strip, accented "For you" cards. Markup verified balanced (11/11 sections, 1065/1065 divs). v8 base was byte-identical to canonical `app/meatcode_mockup.html`, so it's a clean superset.
- Next:    Lior reopen/refresh the file; then choose: (a) promote v8 → `app/meatcode_mockup.html`, (b) carry the richer treatment into Oracle/Map/Research/Toolbench, or (c) the deferred structural round (nav dedup, cross-domain links, second typeface). Reconnect Claude-in-Chrome so future passes are screenshot-verified. Push via `sync_meatcode.command`.

## 2026-06-30 13:05 UTC · advisory session · Decision doc → Word (.docx)
- What:    Generated a polished Word version of the Oracle answer-engine decision doc (wine-accent headings, footer, US-Letter). Validated OK (50 paragraphs).
- Files:   `docs/DECISION_Oracle_Answer_Engine.docx` (new; mirrors the .md).
- Why:     Lior asked for a docx for sharing/review (Daniel-friendly).
- Result:  Shareable Word doc alongside the markdown source.
- Next:    Same as decision doc — review, then build the pipeline + golden eval set.

## 2026-06-30 12:55 UTC · advisory session · Oracle answer-engine decision doc
- What:    Reviewed Lior's proposed "tag-summoned expert agents + consensus vote" retrieval design; consulted the Algorithm Expert sub-agent (independent, same conclusion). Wrote a plain-English decision doc.
- Files:   `docs/DECISION_Oracle_Answer_Engine.md` (new).
- Why:     Lior asked for a subjective expert view + a non-expert-friendly write-up.
- Result:  Recommendation: keep the goal, drop the agent-swarm. Build single-pass tag-aware hybrid RAG (understand→retrieve[pgvector+full-text+soft tags]→rerank→grounded answer with persona + citations). Reserve multi-agent for rare multi-field questions, done as sequential decomposition, later.
- Next:    Lior/Daniel review; if agreed → embed citable sources into pgvector + build the 4-step pipeline + a 30–50 Q golden eval set this month.

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
