# MeatCODE — connect Claude to the mockup in 3 steps

The simplest possible wiring. One Python file, no Postgres, no FastAPI,
no `reaktzia-mvp/` folder needed. Works with the v6 or v7 mockup as-is.

---

## What you need

- macOS / Linux with Python 3.9+ (you already have this — `python3 --version` to check)
- An Anthropic API key (you already have one in `.env`)

## 3 steps

### 1. Install the only dependency

```bash
pip install anthropic
```

Run this once, ever. It's the official Anthropic SDK (~2 MB).

### 2. Make sure the API key is available

You have two options — pick one:

**Option A — `.env` file (recommended, matches your existing setup)**
You already have `/Users/lior/Documents/Claude/Projects/Claude Database/.env`
with `ANTHROPIC_API_KEY=sk-ant-...` in it (per the install guide). The script
reads it automatically. No action needed.

**Option B — environment variable**

```bash
export ANTHROPIC_API_KEY=sk-ant-api03-...
```

### 3. Run the server

```bash
cd "/Users/lior/Documents/Claude/Projects/Claude Database"
python3 meatcode_server.py
```

You'll see:

```
  MeatCODE server running on http://localhost:8000
  Open:  http://localhost:8000/MeatCODE_Mockup_GFI_v7.html
  Model: claude-sonnet-4-5
  Press Ctrl+C to stop.
```

Open that URL in your browser → click **Oracle** → type a question → hit **Ask**.
You should see the answer stream in word by word.

To stop the server: `Ctrl+C` in the terminal.

---

## What this gives you vs. the old `reaktzia-mvp/` setup

| Feature                     | Old (`reaktzia-mvp/`)             | This (`meatcode_server.py`) |
|-----------------------------|-----------------------------------|-----------------------------|
| Backend lines of code       | ~600 across multiple files        | ~140, one file              |
| Dependencies                | FastAPI, uvicorn, psycopg2, dotenv, anthropic | anthropic only |
| Postgres (Neon)             | Required                          | Not used                    |
| Migration step              | Required (`apply_sql.py`)         | None                        |
| RAG / paper citations       | Yes — real papers from your DB    | No — Claude answers from training only |
| `Sources retrieved` chips   | Real chips with paper IDs         | Empty (UI handles gracefully and shows "Claude is responding based on the question alone.") |
| Streaming                   | SSE                               | SSE (same format)           |
| Setup time first run        | ~15 min (per install guide)       | ~30 seconds                 |
| Every-time-you-demo         | ~30 seconds                       | ~30 seconds                 |

**Use this when:** you want a clean demo, you don't need paper citations,
you don't want to depend on the Neon database being up.

**Use the old `reaktzia-mvp/` setup when:** you need real RAG with cited papers
from the GFI literature database.

You can keep both. They don't conflict — different folders, different ports
(this one is also on 8000 by default; change `PORT` in the script if you want
to run them side-by-side).

---

## Customising

Everything tweakable is at the top of `meatcode_server.py`:

```python
PORT       = 8000              # change if 8000 is taken
MODEL      = "claude-sonnet-4-5"   # any Claude model you have access to
MAX_TOKENS = 1600
SYSTEM_PROMPT = "..."          # how the Oracle behaves
```

To swap the system prompt (e.g. make it speak more like a flavor chemist or
include specific in-scope topics), edit `SYSTEM_PROMPT` and restart the
server. No other code needs to change.

---

## Troubleshooting

**`ANTHROPIC_API_KEY is not set`**
The script can't find your key. Either:
- Add `ANTHROPIC_API_KEY=sk-ant-...` to `.env` in this folder, OR
- Run `export ANTHROPIC_API_KEY=sk-ant-...` before starting the script.

**`anthropic package not installed`**
Run `pip install anthropic` (or `pip3 install anthropic`).

**`Address already in use`**
Port 8000 is taken — either stop whatever's using it, or change `PORT` at the
top of the script to something else (8001, 8765, etc.) and update the URL you
open in the browser to match.

**Oracle shows "Failed to fetch"**
The mockup is opening from `file://` and the browser blocks the call to
`localhost:8000`. Open the mockup via the server URL instead:
`http://localhost:8000/MeatCODE_Mockup_GFI_v7.html` (not by double-clicking
the file in Finder).

**Answer streams in but no "Sources retrieved" chips appear**
Expected. This minimal server doesn't do paper retrieval. The mockup shows
"No matches in the database — Claude is responding based on the question
alone." If you want real citations, use the `reaktzia-mvp/` FastAPI server.

**Answer cuts off mid-sentence**
Bump `MAX_TOKENS` at the top of the script. Default is 1600 — usually plenty
for the Oracle's answer style, but if you've asked for something long, raise it.

---

*MeatCODE · simple API server · June 2026*
