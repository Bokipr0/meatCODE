# DISPATCH ORDER — Agent Command Center

_Last updated: 2026-07-05 15:20 UTC · scheduled dispatch (meatcode-dispatch-expertmap) · preset: IMPROVE EXPERT MAP_

**Dispatched: 2026-07-05 15:20 UTC**

## Preset: IMPROVE EXPERT MAP

**Objective:** Improve the expert map so it has several new clickable buttons that interact live
with the database through the server. Data Engineer owns the API + DB side; UI Designer owns the
buttons, states, and layout. Deliver a working, interactive expert map.

Note: the filter bar (`q`/`country`/`sort`/`min_relevance` + `/api/expert-facets`) already shipped
in the earlier 2026-07-05 team run — this dispatch goes BEYOND filters: per-expert actions and
map-level action buttons.

## Ownership split (parallel-safe — disjoint files)

| Agent | Owns | Files |
|---|---|---|
| Data Engineer | Neon queries + API endpoints | `server/meatcode_server.py` only |
| UI Designer | Buttons, wiring, loading/empty/error states, on-brand styling | `app/meatcode_mockup.html` only |

## Agreed API contract (both agents build to THIS)

- `GET /api/experts/{id}/papers?limit=10` → `{expert_id, papers:[{id,title,year,journal,doi,relevance_llm}]}` — that expert's papers, best-relevance first. 404 unknown id, 503 no DB.
- `GET /api/experts/{id}/similar?limit=6` → `{expert_id, experts:[same shape as /api/experts rows]}` — similar curated experts (shared topics/country/affiliation heuristic). 404/503 as above.
- `GET /api/experts/export.csv` — same filter params as `/api/experts` (`q`,`country`,`sort`,`min_relevance`,`limit`); returns `text/csv` attachment.
- `GET /api/experts/stats` → `{total_curated, countries, avg_relevance, top_country, with_papers}` — headline network numbers.

## UI deliverables (buttons — all live against the contract above)

1. Expert detail panel: **View papers** button → fetches `/api/experts/{id}/papers`, renders list w/ loading/empty/error.
2. Expert detail panel: **Similar experts** button → fetches `/api/experts/{id}/similar`, clickable results jump to that expert.
3. Map toolbar: **Export CSV** button → downloads `/api/experts/export.csv` honoring current filters.
4. Map toolbar: **Network stats** button → fetches `/api/experts/stats`, shows popover of headline numbers.

All states styled on-brand (GFI seaweed-teal tokens already in the mockup); demo-data fallback when server offline.
