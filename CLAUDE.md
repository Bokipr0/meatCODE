# MeatCODE — repository guide for agents

_Last updated: 2026-06-30 12:23 UTC · advisory session · added File-update conventions (stamps + AGENT_UPDATE_LOG.md)_

**Read this first, then `PROJECT_STATE.md`.** This repo is the single source of truth for everything
file-based on MeatCODE. If anything here conflicts with a scattered copy elsewhere on disk
(the parent *Claude Database* folder, the iCloud *GFI Database* folder, old uploads) — *this repo wins.*
Those old copies are being retired.

> **Canonical working location — all agents operate HERE:**
> `/Users/lior/Documents/Claude/Projects/Claude Database/meatCODE`
> This folder is mounted into every cowork session, so every agent reaches it directly.
> Do all reads, edits, commits, and pushes inside this folder. Remote: `Bokipr0/meatCODE`.
> Never edit MeatCODE files in the parent *Claude Database* folder or in iCloud — only here.

---

## The three homes (do not mix them up)

MeatCODE state lives in three places, each authoritative for one kind of thing:

| Kind of thing | Authoritative home | How an agent uses it |
|---|---|---|
| Code, docs, mockup, SQL, **technical status** | **This git repo** (`Bokipr0/meatCODE`) | Pull at start, commit + push at end. Edit files here, nowhere else. |
| Structured data (literature, molecules, experts, protocols) | **Neon Postgres** | Query live via `DATABASE_URL`. Never cache copies into the repo. |
| Tasks, milestones, phases, priorities | **Asana** ("MeatCODE – Open Flavor & Aroma Initiative", owned by Daniel) | Read live. Don't track task status in docs. |

Why agents used to fall out of sync: code/knowledge were smeared across a local folder, an iCloud
folder, GitHub, and ephemeral uploads. **One home per kind of thing fixes that.** Never use a local
folder or iCloud as shared memory between agents again.

---

## Repo map

```
meatCODE/
  CLAUDE.md            ← this file (conventions + protocol)
  PROJECT_STATE.md     ← living technical status: done / in-flight / decisions / next
  README.md
  .env.example         ← copy to .env and fill keys (.env is gitignored)
  app/                 ← the product surface
    meatcode_mockup.html      ← CANONICAL mockup (Map / Oracle / Research + Protocol library + Prediction)
    expert_network_map.html   ← standalone expert/co-authorship network view
    assets/                   ← logo, chord-diagram SVG, media
  server/              ← backends
    meatcode_server.py        ← thin single-file demo server (Anthropic SDK only, no DB) — fast demos / fallback
    MeatCODE_API_Quickstart.md
    reaktzia-mvp/             ← full FastAPI + Neon + RAG (real cited papers)
  db/                  ← schema, migrations, seeds (source-controlled SQL)
    taxonomy/                 ← topics hierarchy CSVs
  pipeline/            ← literature pipeline (Dimensions ingester, Layer C/E, migration scripts)
  analysis/            ← streamlit_dashboard.py and other internal-only analysis tools
  docs/                ← strategy: roadmap, use scenarios, decks, 2-pager, reports
    decks/  reports/
  data/                ← exports/snapshots ONLY (gitignored). Neon is the real source.
```

---

## Agent operating protocol (this is what keeps every session current)

**At the start of every session:**
1. `git pull`
2. Read `CLAUDE.md` (this file), then `PROJECT_STATE.md`.
3. Check Asana for the current task if the work is task-driven.

**While working:**
- Edit files in this repo only. Query Neon and Asana live — don't snapshot them into files.
- **Parallel safety (Lior runs a mix of sequential + parallel cowork agents):**
  - Single agent at a time → just work on `main`.
  - Spawning parallel agents → give each its own `git worktree` (or branch), then merge back.
    Never have two agents writing `main` in the same clone at once.

**At the end of every session:**
1. **Stamp** every file you created or materially changed with a last-updated note (see *File-update conventions* below).
2. **Append a detailed entry to `AGENT_UPDATE_LOG.md`** (newest first) — what changed, which files, why, what's next.
3. Update `PROJECT_STATE.md` — move finished items to Done, add what's now in-flight, log any decision with the date.
4. Pushing to GitHub is done by **Lior on his Mac** via `sync_meatcode.command` — the cowork sandbox can't run git on the mounted folder, so agents never run `git` here.

That's the whole discipline: **read STATE first; stamp + log + update STATE last.**
Any session opened afterwards is automatically current.

---

## File-update conventions (last-updated stamps + the update log)

Two requirements on every working session — this is how Lior tracks who changed what:

**1. Stamp every text file you create or materially edit** with a last-updated note near the top, in the file's own comment syntax. Use UTC; run `date -u` if unsure of the time. Update the existing stamp in place — don't stack new ones.
- Markdown / docs → `_Last updated: YYYY-MM-DD HH:MM UTC · <agent or session label> · <one-line what changed>_`
- Python / SQL / shell → `# Last updated: YYYY-MM-DD HH:MM UTC · <label> · <what>`
- HTML / XML → `<!-- Last updated: YYYY-MM-DD HH:MM UTC · <label> · <what> -->`
- Binary / data files (xlsx, png, gif, docx) can't carry a stamp → record them in the log only.

**2. Append a detailed entry to `AGENT_UPDATE_LOG.md`** (newest at top) for the session: what changed, files touched, why, result, next. The stamp is the quick in-file marker; the log is the full audit trail. Copy the template at the top of that file.

---

## Taxonomy — the governing "bible"
`db/taxonomy/keywords_topics.json` is the single source of truth for topics/keywords/priorities
(91 keywords across 5 branches: analytics, flavor_chemistry, flavor_ingredients, meat_analogs, meat_science).
**Edit topics ONLY there.** This is how the whole DB stays governed by one taxonomy:
- **Every script reads it via `db/taxonomy.py` — never hardcode topic/keyword lists.** `search_queries()` drives literature ingest, `classify(text)` tags arbitrary text, `sort_key()` gives canonical ordering (branch order → priority HIGH→MED → level).
- **The DB mirrors it:** after editing the bible run `python3 pipeline/sync_taxonomy.py` to upsert into the `topics` table (by slug, never deletes). New sources are tagged to canonical topics via `source_topics` at ingest time (`openalex_ingest.py` does this automatically).
- Filter and sort everywhere by canonical branch order then priority. A JSON file can't force compliance on its own — compliance = this loader + the synced `topics` table + this rule.

## Connecting to Neon (data)
One `.env` at the repo root (`meatCODE/.env`, git-ignored) holds `DATABASE_URL` + `ANTHROPIC_API_KEY`. Copy from `.env.example`.
- **Agents / scripts:** `from db.connect import get_conn`, or run `python3 db/connect.py` for a live row-count + citable-corpus snapshot. Never hard-code credentials.
- **The mockup never talks to Neon directly.** It calls the local FastAPI server (`server/reaktzia-mvp/`, port 8000), which reads the same root `.env`. Start it with `server/reaktzia-mvp/run_server.command`; verify at `http://127.0.0.1:8000/api/health` (expects `db_ok: true`, `has_anthropic_key: true`).
- Neon auto-sleeps; the first query after idle wakes it (a few seconds).

## Conventions
- Secrets (`.env`, API keys) never get committed. Use `.env.example` as the template.
- Large binaries (demo GIFs, big PDFs) — keep out of git history; link or store in `data/` (gitignored)
  or use Git LFS if they must be versioned.
- Brand: wine / pomegranate palette, distinct from Claude's cream+orange. (Design tokens live in the mockup.)
- Owner/supervisor: **Daniel Dikovsky** (GFI IL Head of SciTech). Author/core execution: **Lior Teper**.

## Key facts an agent should know
- **2026 is the validation year, not launch.** The #1 risk is building the full vision too early —
  prefer a narrow, validated MVP. Push back on scope creep.
- The strategic hypothesis: meaty flavor should be engineered as **process flavor** (cooking-generated
  precursor + lipid + matrix + heat chemistry), not only added as a final flavor mix.
- Phase 1 (Jun–Aug 2026) crux: **collect first 1,000–2,000 high-value literature sources** (currently
  ~34 migrated). Closing this gap is the foundation everything else stands on.
- Ecosystem interest already in: Wageningen (WUR — joint GC-MS / volatile-atlas idea), Masha Niv, FSI.
- Stack: Neon Postgres · Dimensions.ai-fed pipeline (Layer C typed extraction + Layer E store, 3-tier
  relevance) · Streamlit (internal) · Metabase planned (stakeholder self-serve) · mockup → Next.js planned.
  Oracle chatbot phased: keyword RAG → pgvector hybrid → Next.js SSE streaming → auth + feedback.
- Neon auto-sleeps; for multi-agent access either keep it warm or go through `meatcode_server.py`
  as the always-on API so agents never handle raw DB credentials.
