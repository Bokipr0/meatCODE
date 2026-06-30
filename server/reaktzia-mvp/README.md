# Reaktzia MVP — working Phase 0 RAG

A tiny FastAPI proxy that wires the Reaktzia HTML mockup to **Claude + Neon Postgres**, with proper SSE streaming and full-text retrieval. Built 2026-05-25, the day before the hackathon with Daniel.

The Oracle is now *actually alive*: type a question in `reaktzia_mockup_gfi.html`, get a Claude-streamed answer with citation chips that link to real paper detail modals.

---

## How to run (10 seconds)

**Easy mode (macOS — double-click the launcher):**

1. Open Finder, navigate to this folder.
2. Double-click **`run_server.command`**.
3. Wait for "uvicorn running on http://127.0.0.1:8000" — first run installs deps.
4. Open **`../reaktzia_mockup_gfi.html`** in your browser (or the wine variant).
5. Click the Oracle tab in the top-right. Ask anything.

**Manual mode:**

```bash
cd "/Users/lior/Documents/Claude/Projects/Claude Database/reaktzia-mvp"
pip install -r requirements.txt
uvicorn server:app --host 127.0.0.1 --port 8000 --reload
```

Then open `../reaktzia_mockup_gfi.html` in a browser.

---

## What's wired

| Endpoint | Purpose |
|----------|---------|
| `GET  /api/health`         | Sanity check: env keys, DB connectivity, model in use |
| `POST /api/ask`            | Streams an Oracle answer via SSE. Body: `{question, k?, model?}` |
| `GET  /api/papers/{id}`    | Single paper row (powers the modal that opens when you click a citation chip) |
| `GET  /api/papers/recent`  | Last 6 papers by year — for the dashboard "For you" row |
| `GET  /docs`               | FastAPI interactive API explorer |

Inside `/api/ask`:

1. Postgres full-text search against `sources.search_vec` (tsvector with title weighted A and abstract weighted B).
2. ILIKE fallback if FTS returns nothing — the demo never shows an empty result.
3. The top 5 chunks are formatted into a "Sources" block in the user message.
4. Claude (sonnet-4.6 by default) streams the answer back with citation markers like `[12]`.
5. The mockup parses citation markers inline and renders them as clickable chips.

---

## Before you run — one-time setup

### 1. Apply the FTS migration to Neon (~30 seconds)

```bash
cd "/Users/lior/Documents/Claude/Projects/Claude Database"
python3 apply_sql.py reaktzia-mvp/add_fts_columns.sql
```

This adds `search_vec` to the `sources` table, populates it for all existing rows, creates a GIN index, and installs a trigger so future inserts stay indexed. Idempotent — safe to run more than once.

### 2. Confirm env vars

The server reads `ANTHROPIC_API_KEY` and `DATABASE_URL` from `.env`. It looks first in **this folder**, then in **`../`** (Claude Database). Your existing `.env` in `Claude Database/` already has both — nothing to do.

### 3. Verify health

After starting the server:

```bash
curl http://127.0.0.1:8000/api/health
```

Should return something like:

```json
{
  "ok": true,
  "model": "claude-sonnet-4-6",
  "has_anthropic_key": true,
  "sources_total": 627,
  "sources_indexed": 627,
  "db_ok": true
}
```

If `sources_indexed` is 0, run the migration (step 1 above) again.

---

## Two mockup variants

| File | Identity | When to use |
|------|----------|-------------|
| `../reaktzia_mockup.html`     | Wine palette · Reaktzia primary | Internal work, alternative-branded version |
| `../reaktzia_mockup_gfi.html` | Teal / GFI Israel primary       | **GFI team presentation** — Daniel's choice |

Both share the same JS, modal, FastAPI calls. Swapping is a matter of opening the other file — no server restart.

---

## Demo flow (rehearse this)

1. Start the server. Confirm `/api/health` shows `db_ok: true`.
2. Open `reaktzia_mockup_gfi.html` in a browser.
3. Navigate to the Oracle scene (top-right tab).
4. Click a starter chip — start with "Mask beany off-notes."
5. As the answer streams in, point out:
   - The "Sources retrieved" row at the top (the RAG retrieval is visible).
   - The citation chips like `[12]` appearing inline as Claude writes.
6. Click any citation chip — paper detail modal opens with the real paper.
7. Ask a follow-up question by clicking one of the suggestion chips at the bottom.
8. Walk through the rest: Community Map (live globe), Research bubbles, Database table.

Total demo time: ~6 minutes for the Oracle alone, ~12 minutes for the full tour.

---

## What to do during tomorrow's hackathon (Saturday)

Time blocks for you + Daniel:

**Morning (09:00–12:00) — Prompt tuning**
- Edit `prompts.py` (`ORACLE_SYSTEM`). Try 3–4 variants and ask the same question to each, see which voice lands best for GFI.
- Specifically test: tone (warm vs. clinical), citation strictness, follow-up quality.
- The system prompt is the single highest-leverage thing to iterate on this week.

**Midday (12:00–14:00) — Content polish**
- Pick the 4 best "starter" questions for the Oracle. Edit them in `reaktzia_mockup_gfi.html` (search for `oracle-starter`).
- Curate a list of 10 papers that should always rank highly — add them to a "pinned" boost in `retrieval.py` if needed.

**Afternoon (14:00–18:00) — UI polish**
- The wine variant's hardcoded avatar SVG colors look out of place on the GFI palette. If you want a fully GFI-tuned avatar, edit each `<svg class="avatar-svg">` block in `reaktzia_mockup_gfi.html`.
- The Three.js globe colors are wine-themed. Find `0x7E2E2E`, `0xA14848`, `0xEAD2CF`, `0xC89A95`, `0xC84F4F` in the JS block and swap for teal equivalents if you want the globe to match.
- Add 5–10 demo screenshots to a `presentation_assets/` folder for the slide deck.

**Late afternoon — rehearsal**
- Run the demo twice end-to-end. Time it. Identify the slowest moment (usually the first Claude call — it warms up).

---

## Configuration knobs

All optional. Set in `.env` or as shell env vars before starting the server:

| Variable | Default | What it does |
|----------|---------|--------------|
| `REAKTZIA_MODEL`        | `claude-sonnet-4-6` | Which Claude model to use. Try `claude-haiku-4-5-20251001` for speed, `claude-opus-4-6` for depth. |
| `REAKTZIA_MAX_TOKENS`   | `600`               | Max tokens per Oracle answer. Higher = longer answers but slower. |
| `ANTHROPIC_API_KEY`     | (from .env)         | Required. |
| `DATABASE_URL`          | (from .env)         | Required. Neon connection string. |

To switch model per-request from JS: send `{question: "...", model: "claude-haiku-4-5-20251001"}` to `/api/ask`.

---

## Troubleshooting

**"Failed to fetch" in the browser when asking the Oracle.**
→ The FastAPI server isn't running. Look for the terminal window with uvicorn.

**Answers come back but no citation chips appear.**
→ The retrieval probably returned 0 rows. Check `/api/health` — if `sources_indexed` is 0, re-run the FTS migration.

**ANTHROPIC_API_KEY warning at startup.**
→ Make sure `.env` exists in either `reaktzia-mvp/` or its parent (`Claude Database/`). Spaces around `=` are tolerated; the loader strips them.

**Postgres timeout / connection refused.**
→ Neon free-tier wakes from sleep on first query (~3s). Try once, wait, try again. Or hit `/api/health` to wake it before the demo.

**CORS errors when opening the mockup via `file://`.**
→ Try opening via a tiny local server instead:
```bash
cd "/Users/lior/Documents/Claude/Projects/Claude Database"
python3 -m http.server 8080
# then visit http://localhost:8080/reaktzia_mockup_gfi.html
```

**Streaming feels janky on Lior's laptop.**
→ The fallback path: edit `streamSSE` in the mockup to accumulate text and only update the DOM every 5–10 chunks instead of every chunk.

---

## File map

```
reaktzia-mvp/
├── README.md                  ← this file
├── server.py                  ← FastAPI app (endpoints, CORS, env loading)
├── retrieval.py               ← Neon Postgres FTS + paper lookup
├── prompts.py                 ← Oracle system prompt + user-message builder
├── add_fts_columns.sql        ← one-time DB migration
├── requirements.txt           ← Python deps
├── run_server.command         ← double-click launcher for macOS
└── assets/                    ← scratch folder for any GFI brand files
```

Together with the existing `Claude Database/`:

```
Claude Database/
├── .env                       ← ANTHROPIC_API_KEY + DATABASE_URL (already set)
├── apply_sql.py               ← used by the FTS migration step
├── reaktzia_mockup.html       ← wine variant — Oracle scene now wired
├── reaktzia_mockup_gfi.html   ← NEW — GFI palette, lead variant for the demo
└── reaktzia-mvp/              ← this folder
```

---

## Next steps after the GFI presentation

These are deferred from this MVP — pick up after Daniel's feedback:

- **Phase 1 hybrid retrieval** — add pgvector + embeddings, blend full-text and vector rankings via RRF. See the theory primer's page 4-5 for the recipe.
- **Researcher profile drawer** — clicking a researcher name (in citations or on the globe) opens a side drawer with their org, h-index, recent papers, "request intro" CTA.
- **Globe wiring to real Dimensions data** — pull the 476 researchers from Neon and plot them with real lat/lng + filters.
- **Conversation history** — multi-turn Oracle, with the previous question + answer included in context.
- **Deployment** — Render or Railway for the FastAPI; Vercel for static mockup; pgvector on Neon stays as-is.

---

*Built for GFI Israel · Tel Aviv · 2026-05-25*
