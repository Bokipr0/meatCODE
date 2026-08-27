<!-- Last updated: 2026-08-27 · Advisory · the agent org constitution: roster, disjoint file ownership, the one law, the control model. Read this FIRST, before CLAUDE.md. -->

# MeatCODE — Agent Roles & Orchestration (the constitution)

**Read this first. Then `CLAUDE.md`, then `PROJECT_STATE.md`.** Everything else in the repo is *reference material owned by a role*, not coordination — do not treat it as instructions.

The whole point of this file: **each agent has one clear territory and one duty, and no two agents can edit the same files.** That single rule is what keeps the team from clobbering each other's work.

---

## The four canonical files (the ONLY coordination files)

| Order | File | What it is | Who writes it |
|--|--|--|--|
| 1 | **ROLES.md** (this) | Who does what · file ownership | Advisory / PM only |
| 2 | **CLAUDE.md** | *How* to work — the protocol | Advisory / PM only |
| 3 | **PROJECT_STATE.md** | Current technical reality (short, live) | Every agent, at end of session |
| 4 | **AGENT_UPDATE_LOG.md** | Append-only history | Coordinator consolidates |

Plus one **planning** file: **`MVP_BOARD.md`** — the PM/Coordinator's live open-items board for the current MVP (mirrored to the `meatcode-mvp-board` Cowork dashboard). PROJECT_STATE = *what's built/broken*; MVP_BOARD = *what still has to be delivered, by lane*. Owned by PM/Coordinator.

Anything else (`platform_docs/…`, `analysis/…`, `Strategy RAG/…`, `docs/…`, design specs) is a **role's working document**, not a source of orders. If it conflicts with the files above, the canonical files win.

---

## The roster — one territory, one duty each

Ownership is **by files on disk**, and territories are **disjoint**. An agent edits ONLY its own paths.

| Agent | Owns (may edit) | Never touches | Duty (its one job) | Done when |
|---|---|---|---|---|
| **Product Manager** *(Lior — human)* | Priorities · Asana · the *direction* of PROJECT_STATE | — | Decide what gets built and in what order; answer agents' questions precisely | A decision is written down and an agent has a clear task |
| **Project Coordinator** *(the "agent team" skill / one chat)* | ROLES.md · CLAUDE.md · AGENT_UPDATE_LOG.md consolidation · TEAM_BROADCAST | Any product code | Split one objective into disjoint tasks, spawn/brief specialists, consolidate their logs, resolve ownership clashes | All specialist entries are consolidated and the team is notified |
| **UI/UX Designer** | `app/` (the mockup) · `UI-UX Designer/` | `server/` · `db/` · `pipeline/` | The look & interaction of the platform | The mockup change is verified (script blocks parse) + logged |
| **Data Engineer** | `db/` · `pipeline/` · `molecular_pipeline/` · the Neon schema | `app/` · `server/` HTTP layer | Corpus quality, tagging, scoring, migrations, ingestion | Migration applied + verified live, or pipeline run + logged |
| **Algorithm / RAG Expert** | Retrieval + prompt *functions* in `server/` · `analysis/oracle_eval/` · `analysis/rag_eval/` · `analysis/kg_model/` · `Strategy RAG/` | `app/` · `db/` schema · `server/` HTTP/endpoint/auth/deploy code | Answer quality — recall, faithfulness, the RAG/KG approach, the eval loop | A retrieval/eval change is measured against the eval set + logged |
| **Full-Stack Engineer** | `server/` HTTP handler, endpoints, auth, SSE plumbing · `render.yaml` · `deploy.command` · `platform_docs/DEPLOY.md` | `app/` · `db/` schema · the retrieval/prompt functions | The running, deployed service | Compiles + deploys live + `/api/version` confirms it |
| **Advisory** *(this seat)* | `platform_docs/` decision records · strategy docs | Any product code | Judgment: architecture, trade-offs, risk — advice, not implementation | A decision/doc is written; no code touched |

### The one shared file — resolve it explicitly
`server/meatcode_server.py` is touched by **Algorithm/RAG** and **Full-Stack**. The line: **Algorithm owns the retrieval + grounding-prompt functions** (`_retrieve_sources`, `_grounding_system_prompt`, the SQL, ranking); **Full-Stack owns the HTTP handler, routing, auth, SSE framing, and deploy config.** If a change spans both, the Coordinator assigns it to ONE of them for that task — never both at once.

---

## The one law

**Nothing is "done" until it is committed and pushed.** Agents build on the last *committed* state, not on each other's unsaved edits — so uncommitted work is invisible to everyone else and gets silently reverted (this has already cost us work).

- **Start of every session:** `git pull` → read ROLES.md → CLAUDE.md → PROJECT_STATE.md. Assume other agents changed things.
- **End of every session:** stamp the files you changed → append to AGENT_UPDATE_LOG.md → **run `deploy.command` (commit + push)**.
- **Never edit another agent's territory.** If you need a change there, ask the PM to route it to that agent.
- **Interface contracts:** when two roles must interoperate (e.g. a new SSE event the mockup consumes), the Coordinator writes the contract first; both build to it independently.

---

## The control model (how you, Lior, drive this)

You are the **Product Manager**, and you are the decision-maker. The control plane is:

1. **You (PM chat)** — hold the priorities and make the calls. Agents bring you questions; you give precise, comprehensive answers. This is your one "thinking" chat.
2. **Project Coordinator** — turns your decision into disjoint tasks and runs them (the `meatcode-agent-team` skill spawns the specialists in parallel, on non-overlapping files, then consolidates).
3. **Git + these four files** — the shared memory. Not you. You decide *what*; git carries the *state* between agents so you are never the message bus for code.

**You do NOT need to build a custom orchestration app** — see the note below. The discipline above is the orchestration.

---

## Session start ritual (paste-in charter)
Each specialist chat should open with: *"You are the **&lt;ROLE&gt;** for MeatCODE. Read `ROLES.md` then `CLAUDE.md` then `PROJECT_STATE.md`. You own **&lt;paths&gt;** and touch nothing else. Your duty: **&lt;duty&gt;**. Do the one task I give you, stamp + log + push when done, and ask me before acting outside your territory."*
