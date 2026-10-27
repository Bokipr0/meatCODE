---
name: "meatcode-agent-team"
description: "Orchestrate a parallel MeatCODE specialist-agent team on one shared objective, then consolidate as Project Coordinator. Use whenever Lior asks to orchestrate/run his MeatCODE \"agent team\", pastes a prompt that names specialist agents (UI/UX Designer, Advisory, Data Engineer, Algorithm Expert, Full-Stack, etc.) to \"work IN PARALLEL\" on a shared objective with coordination rules, asks for a \"parallel team run\", to \"spawn specialists\", to split one objective across agents, or to have a Project Coordinator consolidate their work and notify the team. Handles roster→disjoint-file split, parallel spawning, parallel-write-safe logging, and consolidation into AGENT_UPDATE_LOG.md + PROJECT_STATE.md + TEAM_BROADCAST.md."
---

# MeatCODE Agent-Team Orchestration

Run several specialist sub-agents **in parallel** on one shared objective inside the canonical
`meatCODE/` repo, then act as **Project Coordinator** to verify, consolidate, and notify the team.
This is Lior's standard "parallel team run." Follow it whenever he pastes an orchestration prompt that
names specialist agents to work simultaneously, or asks to run/orchestrate his agent team.

The repo evolves fast between sessions. **Treat the repo's own files as the source of truth for current
conventions** (deploy/branch workflow, feature flags, roster, corpus reality) — trust them over any
specific fact written here.

---

## 0. Orient — always first
Read, in order:
1. `meatCODE/CLAUDE.md` (conventions, canonical path, three-homes model, file-stamp rules)
2. `meatCODE/PROJECT_STATE.md` (current technical reality — what's built/broken/in-flight)
3. Skim the top ~30 lines of `meatCODE/AGENT_UPDATE_LOG.md` and `meatCODE/TEAM_BROADCAST.md` (what just changed; the current deploy/branch + feature-flag workflow is often flagged here).

Confirm the canonical working path from CLAUDE.md (all work happens there; never edit MeatCODE files in a parent/iCloud copy).

## 1. Parse the request
Extract **(a)** the roster of specialist agents and **(b)** the one shared objective. Common roles:
- **UI/UX Designer** — mockup, screens, screen-flows, design system (`app/…`, `UI-UX Designer/…`)
- **Advisory** — strategy, architecture, infra, docs (`docs/…`)
- **Data Engineer** — Neon schema/migrations, API endpoints, pipeline (`db/…`, `pipeline/…`, `server/…`)
- **Algorithm Expert** — retrieval, scoring, judge, eval (`pipeline/…`, `analysis/…`)
- **Full-Stack** — server wiring + endpoints (`server/…`)

You are the **Project Coordinator** (not a spawned agent).

## 2. Split by DISJOINT FILE OWNERSHIP — the hard rule
The Cowork sandbox **cannot drive git** on the mounted repo, so there are no worktrees/branches to isolate
parallel agents. If two agents write the same file simultaneously, they clobber each other. Therefore:
- Give **each agent its own file(s)** — no overlap.
- If the objective converges on one file (e.g. the mockup `app/meatcode_mockup.html`), either split it by
  **scene/section**, or have **one** agent own that file while the others own specs / backend / docs.
- **No agent edits `AGENT_UPDATE_LOG.md`, `PROJECT_STATE.md`, or `TEAM_BROADCAST.md`** — the Coordinator owns those.
- State the ownership split explicitly to Lior before spawning, and inside each agent's prompt.

## 3. Spawn ALL specialists in ONE message (true parallel)
Issue every `Agent` call (subagent_type `general-purpose`) **in a single message** so they run concurrently.
Each agent prompt MUST contain:
- **Read `meatCODE/CLAUDE.md` then `meatCODE/PROJECT_STATE.md` first.** Work only inside `meatCODE/`.
- **You own ONLY `<these exact files>`.** Do not touch any other file — a teammate or the Coordinator owns the rest.
- **Follow the file-stamp convention** — put/refresh a last-updated stamp near the top of every file you materially edit (format is in CLAUDE.md).
- **Do NOT edit `AGENT_UPDATE_LOG.md`, `PROJECT_STATE.md`, or `TEAM_BROADCAST.md`.** Instead **return a ready-to-paste AGENT_UPDATE_LOG entry** (template below). *(Parallel-write safety — this is the #1 lesson.)*
- **Be honest to reality:** match the current backend (phased RAG, the real corpus size from PROJECT_STATE, no fabricated data or capabilities). Anything half-built or "preview" must respect the repo's current feature-flag convention if one exists (check CLAUDE.md / `platform_docs/`).
- **Verify before finishing:** `node --check` on any inline `<script>`, tag/markup balance, live endpoint or DB checks as applicable.
- **Return:** a concise report (what you built, where, key decisions, open flags) **plus** the log entry.

Agent-prompt skeleton:
```
You are the <ROLE> specialist on the MeatCODE agent team. Work inside
/…/meatCODE/. Read CLAUDE.md then PROJECT_STATE.md first.

SHARED OBJECTIVE (team): <objective>
YOUR PART (own ONLY these files): <files>

Rules: edit only your files; stamp them; DO NOT edit AGENT_UPDATE_LOG.md /
PROJECT_STATE.md / TEAM_BROADCAST.md — return a ready-to-paste log entry instead;
stay honest to the current backend + design system; verify before finishing.

Return: concise report + a log entry (What/Files/Why/Result/Next).
```

## 4. Coordinator consolidation — after all agents return
1. **Verify** each deliverable independently (files exist, markup/JS sound, consistent with each other and the design system / API contract).
2. **AGENT_UPDATE_LOG.md** — re-read its top first (other sessions may have appended), then insert **one grouped block** at the very top: a coordinator header (`## <date> · Project Coordinator · PARALLEL team run — <objective> (consolidated)`) followed by a `### <role> · …` sub-entry per specialist, from their returned entries. Update the "Last updated" stamp. Newest-first; never delete past entries.
3. **PROJECT_STATE.md** — if technical reality changed, update Done / In-flight / Decisions (re-read first). Refresh its stamp.
4. **Notify the team (coordination rule 4):** refresh the head of `TEAM_BROADCAST.md` with a short "what just landed / what's now current / each lane's next move" note, so the next agents that spawn read reality. (The updated PROJECT_STATE + log are themselves the durable notification.)
5. **Never run `git`** from the sandbox. Pushing/deploying is Lior's action via the **current** documented workflow — read CLAUDE.md / `platform_docs/` for the live command names (the deploy flow changes; do not assume `deploy.command`).

## 5. Report to Lior
Concise: who owned what · what's ready for review · any open flags or decisions the specialists surfaced.
Offer the obvious next step.

---

## Guardrails
- **2026 is the validation year, not launch.** Push back on scope creep; prefer a narrow, validated slice over the full vision.
- **UI stays on-brand:** GFI seaweed-teal design system + the 4-region app-shell (topbar / left context / canvas / dock). Tokens live in the mockup — never invent colors.
- **Deploy-safety:** before any change to a deployed file, confirm the frontend↔API contract is intact (diff the `<script>` blocks and every `fetch()` / `API_BASE` / `/api/…` line against the working version; they should be identical unless the change is intentional).
- **Ask-before-build** only when the objective is genuinely ambiguous; otherwise state your assumptions and proceed. (Lior's standing pattern: 3–4 quick multiple-choice questions before a creative build, then iterate per-piece on surgical notes.)

## AGENT_UPDATE_LOG entry template (each agent returns this; Coordinator writes it)
```
## YYYY-MM-DD HH:MM UTC · <agent / role> · <short area>
- What:    <what changed, concretely>
- Files:   <paths touched>
- Why:     <reason / which objective>
- Result:  <outcome, what works now, how verified>
- Next:    <follow-ups left open>
```

