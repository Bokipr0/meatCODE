<!-- Last updated: 2026-10-11 16:10 UTC · Advisory · §3 re-verified against prod/Asana/Gmail; DECISIONS/PEOPLE/ASANA_SNAPSHOT added to reading order · the single entry point for a new Claude account, a new agent, or a new collaborator. Keep it short; it points, it doesn't duplicate. -->

# START HERE — MeatCODE

**MeatCODE** (Meat Collaborative Open Development Ecosystem) is a GFI Israel open, pre-competitive
platform that turns scattered meaty-flavour science into a searchable knowledge hub — literature,
molecules, experts, tools, and a grounded AI "Oracle". Owners: **Lior Teper** (builder) and
**Daniel Dikovsky** (GFI IL Head of SciTech). 2026 is the **validation year**, not launch.

If you are a new account, a new agent, or a new person: read the files below **in this order**.
That's the whole onboarding — nothing else is needed.

## 1. Reading order

| # | File | What you get | ~time |
|---|---|---|---|
| 1 | [`ROLES.md`](ROLES.md) | The agent constitution: who owns which files, the one law | 3 min |
| 2 | [`CLAUDE.md`](CLAUDE.md) | How to work: the session protocol | 3 min |
| 3 | [`platform_docs/SYSTEMS_MAP.md`](platform_docs/SYSTEMS_MAP.md) | Every external system — Neon, Render, GitHub, Asana, the folder — and how to reach it | 4 min |
| 4 | [`platform_docs/SYSTEM_SNAPSHOT.md`](platform_docs/SYSTEM_SNAPSHOT.md) | **Live** numbers: row counts, flags, release tags, routes. Generated, not hand-written | 2 min |
| 5 | [`PROJECT_STATE.md`](PROJECT_STATE.md) | Verified status: what's live, on dev, broken, next | 4 min |
| 5b | [`platform_docs/DECISIONS.md`](platform_docs/DECISIONS.md) · [`platform_docs/PEOPLE.md`](platform_docs/PEOPLE.md) | What was decided and why · who's who | 4 min |
| 6 | [`MVP_BOARD.md`](MVP_BOARD.md) · [`TEAM_BROADCAST.md`](TEAM_BROADCAST.md) | Open deliverables by lane · each agent's next move | 4 min |
| 7 | [`platform_docs/ASANA_SNAPSHOT.md`](platform_docs/ASANA_SNAPSHOT.md), then Asana live | Priorities, owners, overdue items | 3 min |

`AGENT_UPDATE_LOG.md` is append-only history — search it, don't read it top to bottom.

## 2. Where things live

| Kind of thing | Home |
|---|---|
| Code, docs, mockup, SQL, agent rules, skills, status | this repo — `github.com/Bokipr0/meatCODE` |
| Structured data | Neon Postgres (production + `dev` branch) — connection in `.env` / `.env.dev`, never printed |
| Running platform | Render — `meatcode-oracle` (prod, `main`) · `meatcode-dev` (staging, `dev`) |
| Tasks and milestones | Asana — *MeatCODE - Open Flavor & Aroma Initiative* |
| Agent skills | [`orchestration/skills/`](orchestration/skills/) |

## 3. Where the project is (verified 2026-10-11)

- **Asana phase:** Phase 2 — MVP knowledge hub (Sep–Nov 2026). Latest monthly status *Oct 1*: **At risk**;
  12 tasks overdue. Mirror: [`platform_docs/ASANA_SNAPSHOT.md`](platform_docs/ASANA_SNAPSHOT.md).
- **Production** runs the **2026-09-21 release** (`prod-20260921-1717`), verified against `/api/version`.
  The old "B1 — deploy the backlog" is **done**. Dev holds two unpromoted, flag-gated additions (Papers
  browser, Backups button).
- **Oracle** = grounded RAG over the corpus (818 sources; only those with `relevance_llm ≥ 60` — 319 —
  are retrievable), citing real IDs. Baseline **groundedness 3.4 · citation accuracy 4.8 · coverage
  4.1 /10**, zero invented citations.
- **Top open problems:** **B2** — 4 quarantined sources still pass the gate and the audit loop hasn't run
  since 2026-07-08 · the **paper↔molecule bridge** (23 links; `experiments`/`processes` empty) · publisher
  rights unresolved (Daniel, overdue). Next step for the bridge: 10-paper **GROBID** extraction pilot —
  [`platform_docs/RAG_BUILD_VS_BUY.md`](platform_docs/RAG_BUILD_VS_BUY.md).
- **This week:** Yochai × Prof. Yoav Ram, Mon 2026-10-12 13:00 · Daniel scheduling WUR simulator
  validation + AKA Foods Atlas pilot · Lior owes Rebecca a 10–15 min architecture overview.
- **Do not** publish or open external access to anything built on publisher content until rights are clarified.

Full detail: [`PROJECT_STATE.md`](PROJECT_STATE.md) · decisions [`platform_docs/DECISIONS.md`](platform_docs/DECISIONS.md) ·
people [`platform_docs/PEOPLE.md`](platform_docs/PEOPLE.md) · email-derived history
[`docs/meetings/2026-09-to-10_record-from-email.md`](docs/meetings/2026-09-to-10_record-from-email.md).

> `MVP_BOARD.md` and `TEAM_BROADCAST.md` were last refreshed on 1 Sep — for priorities, Asana and
> `PROJECT_STATE.md` win.

## 4. Hard rules (any agent, any account)

1. Edit only inside `meatCODE/`, and only files your role owns (`ROLES.md`).
2. Never print or paste secrets. Never put the production DB URL in `.env.dev`.
3. Never fabricate chemistry or citations — unknown stays NULL. Label placeholders and mock output.
4. Schema changes = a numbered file in `db/migrations/`, applied to **both** Neon branches.
5. You can't run git from Cowork. Lior pushes with the `Release Center/*.command` scripts.
6. End every session by appending to `AGENT_UPDATE_LOG.md` and updating `PROJECT_STATE.md`.

## 5. Keeping this true

The `meatcode-daily-sync` skill refreshes §3, `PROJECT_STATE.md`, `DECISIONS.md`, `PEOPLE.md` and the
snapshots from Gmail, Asana, meetings, production and Neon. Setup: [`orchestration/DAILY_SYNC_SETUP.md`](orchestration/DAILY_SYNC_SETUP.md).

## 6. Setting up a new Claude account

Follow [`orchestration/NEW_ACCOUNT_SETUP.md`](orchestration/NEW_ACCOUNT_SETUP.md) — six steps, ~30 min.
Before you start, double-click **`Release Center/refresh-handoff.command`**: it refreshes the live
snapshot and packs the skills for upload.
