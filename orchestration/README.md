<!-- Last updated: 2026-08-27 · Advisory · orchestration folder = the front door to the agent system. Groups + points to the canonical coordination spine (which stays at repo root for functional reasons). -->

# MeatCODE — Orchestration

This folder is the **front door to how the agent team runs**. It groups the orchestration tooling and points to the coordination spine.

## The coordination spine — READ IN THIS ORDER
These four files are the ONLY sources of orders. **They live at the repo root by necessity, not by accident** (see "why they stay at root" below) — treat this folder as the index, not a second copy.

1. [`../ROLES.md`](../ROLES.md) — **who does what** + file ownership (the constitution). Read first.
2. [`../CLAUDE.md`](../CLAUDE.md) — **how** to work (the protocol).
3. [`../PROJECT_STATE.md`](../PROJECT_STATE.md) — **current technical reality** (short, live).
4. [`../AGENT_UPDATE_LOG.md`](../AGENT_UPDATE_LOG.md) — **append-only history**.

Plus the PM board: [`../MVP_BOARD.md`](../MVP_BOARD.md) — what's still to deliver, by lane.

## Why those 4 stay at the repo root (do NOT move them)
- **`CLAUDE.md`** is auto-loaded by the agent tooling *from the root* — moving it stops it loading, so every agent loses the protocol.
- **`PROJECT_STATE.md`** and **`AGENT_UPDATE_LOG.md`** are written by every session at the root path, and every charter references them there. Moving them mid-flight fragments the writes.
- **`ROLES.md`** could live here, but it's kept beside CLAUDE.md so the whole spine is one glance away at the root.

Grouping is achieved by *this index*, not by relocating live files. That keeps the system working AND findable.

## What this folder holds (orchestration tooling, safe to keep here)
- `charters/` — the paste-in system prompt for each agent chat (one file per role). *(generate on request)*
- Any orchestration scripts or templates that are *about running the team*, not product code.

## The control model (one line)
**Lior (PM chat) decides → the Coordinator / `meatcode-agent-team` skill splits & runs disjoint tasks → git + the spine carry the state.** No custom orchestration app needed. Full rationale in `ROLES.md`.
