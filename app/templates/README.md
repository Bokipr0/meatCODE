# Claude Design templates → live MeatCODE app

_Last updated: 2026-07-05 13:30 UTC · deploy-templates session · initial version_

This folder deploys the templates you build in **Claude Design** so their elements
talk to Claude + the Neon database through the **same** FastAPI server the canonical
mockup uses (`server/reaktzia-mvp/`, port 8000). No per-template server code — you
drop an exported HTML file in here and wire its elements with data attributes.

## How it fits together

```
Claude Design template (.html)  ──include──▶  meatcode-api.js
                                                     │  (SSE / fetch)
                                                     ▼
                            server/reaktzia-mvp  (FastAPI, :8000)
                                 /api/ask   → Claude (streams answer + citations)
                                 /api/papers → Neon Postgres
```

The server already reads `ANTHROPIC_API_KEY` and `DATABASE_URL` from the repo `.env`,
so every template inherits the live Claude/DB connection automatically.

## Deploy a template — 3 steps

1. **Export from Claude Design.** In the Design project, use *Send to Claude Code* /
   export the template as a standalone `.html`. (This session can't reach your Design
   project over the network — `DesignSync` needs an interactive login — so export the
   files and place them here, or use Design's "Send to Claude Code Web".)

2. **Drop the `.html` into this folder** (`app/templates/`). It appears in the gallery
   at `http://127.0.0.1:8000/templates/` automatically — no registry to edit.

3. **Wire its elements** — either zero-JS with `data-` attributes, or from the
   template's own script. Add `<script src="meatcode-api.js"></script>` before `</body>`.

## Wiring options

### A. Zero-JS auto-wiring (works on untouched exports)

```html
<textarea data-mc-input placeholder="Ask the Oracle…"></textarea>
<button data-mc-ask data-mc-output="#answer" data-mc-sources="#sources">Ask</button>
<div id="sources"></div>
<div id="answer"></div>

<!-- starter chip with a fixed question -->
<button data-mc-ask data-mc-question="Why does heme drive meaty aroma?"
        data-mc-output="#answer" data-mc-sources="#sources">Try an example</button>

<!-- recent papers, auto-filled -->
<div data-mc-recent="6"></div>

<!-- live server/DB status -->
<span data-mc-health></span>

<script src="meatcode-api.js"></script>
```

### B. Programmatic (from the template's own script)

```js
MeatCODE.ask("why does heme drive meaty aroma?", {
  onSources: list => { /* citation chips */ },
  onChunk:   (piece, fullSoFar) => { /* stream into the UI */ },
  onDone:    fullText => {},
  onError:   msg => {}
});

MeatCODE.health().then(h => {});      // {ok, db_ok, has_anthropic_key, model}
MeatCODE.paper(42).then(p => {});     // single paper for a detail view
MeatCODE.recentPapers(6).then(ps => {});
```

## Run it

```
server/reaktzia-mvp/run_server.command      # starts uvicorn on :8000
open http://127.0.0.1:8000/templates/       # the gallery
```

Templates opened directly via `file://` also work — `meatcode-api.js` detects that
and points at `http://127.0.0.1:8000`. Serving them through the server (the gallery
URL above) avoids any CORS edge cases and is the recommended path for demos.

## Files here

- `meatcode-api.js` — the shared connector. Include it in every template.
- `index.html` — self-populating gallery (lists whatever `.html` is in this folder).
- `example-oracle.html` — reference template showing both wiring styles (starter chips + programmatic).
- `oracle-demo.html` — minimal reference template using **data attributes only** (no custom JS).
