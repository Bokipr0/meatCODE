_Last updated: 2026-10-05 · UI/UX Designer · NEW — design rationale, layout alternatives and expansion backlog for the dev Papers browser (`app/dev/papers_browser.html`, flag `papers_browser`)._

# Papers browser — design notes

**What it is:** a dev-team module to browse ALL papers (Neon `sources`, 818 today), 50 per page, filter/sort, tick rows → CSV/XLSX, export the whole table, open each paper and (best effort) its open-access PDF. Top-nav module, flag-gated (`papers_browser`, dev ON / prod OFF), embedded in the platform shell exactly like Analytics (`#papers` scene → iframe `?embed=1`).

## Principles (why it looks the way it does)
1. **Audit tool, not a showcase.** The users are the dev team checking corpus quality. Density, honesty and speed beat decoration. Nulls render as a faint "—" (many enrichment columns are genuinely empty; we never hide that). The relevance bar turns coral below the corpus gate (>= 60) so "does this paper pass?" is readable at a glance.
2. **Minimal landing, everything else on demand** (Lior's decision): checkbox · Title · Authors · Year · Journal · DOI · Citations · Open/PDF. All other list-payload fields live in the **Columns** picker (persisted, `mc_papers_cols_v1`).
3. **Same design system, no new colors.** GFI seaweed-teal tokens, Varela Round, mono for numbers/DOIs, `.db-table`-style header (uppercase 11px, surface-2), `.fchip` chips, `.db-bar` bars, `.db-page-btn` pager, `.db-xlsx-btn` ghost buttons. Only existing literals reused (the `#6F2A26` error ink and the brass-soft/`#8a4a2c` preview-banner pair).
4. **4-region shell, no page scroll.** The page is `100vh`; only the table region scrolls (sticky header, sticky checkbox + title columns for wide column sets), the filter panel scrolls inside its own capped box. Verified: `scrollHeight == innerHeight` at 1440x800 and 1100x700.
5. **Honest exports.** Two always-visible footer buttons with counts: "Export filtered (CSV) · N rows" and "Download entire papers table (CSV) · 818 rows". The selection bar exports only ticked rows. Nothing is labelled "all" unless it is.
6. **Honest PDFs.** We never store/proxy PDFs. "PDF" does a lazy open-access lookup; on a miss the toast says exactly "No open-access PDF found — opened the publisher page."

## Layout alternatives considered
| | Layout | Pros | Cons | Verdict |
|---|---|---|---|---|
| **A** | **Left filter rail (260px, always open) + table** | Classic faceted-search; filters always visible | At the 1100px floor the table loses ~25% width — the 8 minimal columns + actions no longer fit; permanent rail steals the no-scroll height budget | Rejected |
| **B** | **Top toolbar (search · Filters · Columns · density) + lens chips + collapsible filter panel above a full-width table** | Table gets the full canvas width at every size; filters are one click away and collapse when done; lens chips give one-click audit passes without opening anything | Opening the panel squeezes table height (capped at 42vh to keep ~4 rows visible) | **Chosen** |
| **C** | **Table only + per-column header filters (spreadsheet style)** | Most compact; very "data tool" | Poor for multi-select facets with counts (topic/tag lists are long), no space for range controls, hard to show active filters, weak on keyboard/a11y | Rejected (header sort stays) |

Why B: Lior's brief is "minimal landing" + "everything else on demand". B makes the landing exactly the table; power features are summoned (Filters / Columns / drawer) and leave no footprint when closed. It also embeds cleanly in the shell (no left rail competing with the platform's own).

## What was built (v1)
- Toolbar: debounced search (320ms, Enter = immediate, `/` focuses), Filters button with active-count badge, Columns picker (Minimal / All columns resets), Comfortable/Compact density (persisted `mc_papers_density_v1`), `?` shortcuts popover.
- **Quick lens chips** (one-click audit passes): Passes relevance gate (>= 60) · Below gate (< 60) · Has DOI · Reviews only · Cited >= 10. They set the same state as the filter panel, so pills/URL stay consistent.
- Filter panel: year range, relevance range (+ gate hint), min citations, has DOI / has URL, reviews any/only/exclude, and searchable multi-select lists with facet counts for review status, study type, trust tier, topic, tag (tags grouped by category).
- **Active-filter pills** with per-pill ✕ and "Clear all".
- Table: sortable headers (click toggles asc/desc, `aria-sort`, default direction asc for text columns / desc for numeric), sticky header, sticky checkbox+title, loading skeleton (first load) / dimmed-in-place reload, empty / error (retry) / 503 / 404-"not enabled" / 401-403 states.
- Pager: first / prev / numbered window / next / last, "Showing 1–50 of 818", jump-to-page; `[` `]` keys.
- **Selection persists across pages and filters** (Set of ids), shift-click range select, header select-page (tri-state), sticky selection bar: "N selected · Export CSV · Export XLSX · Select all N matching · Clear". "Select all matching" pages through the current view client-side (cap 2,000).
- Exports: server CSV for filtered / entire table (plain anchor navigation), `POST /export.csv` for ticked ids (blob download, filename from Content-Disposition), **XLSX built client-side** with SheetJS 0.18.5 (same CDN URL as the mockup) from `POST /rows` (all columns, tags flattened, chunked at 2,000).
- Row actions: **Open** (doi_url, else url, else doi.org/<doi>) and **PDF** (lazy lookup, spinner, blank tab opened synchronously so popup blockers don't eat it).
- **Detail drawer** (row click / Enter): title, authors, journal·year, DOI, badges, Open/PDF/Select, **main claim**, **abstract**, **tags** (by category), an "All fields" key/value list; Prev/Next within the page (also ←/→), Esc closes, focus returns to the row.
- **Keyboard:** `/` search · `f` filters · `[` `]` pages · `j` `k` row focus · `x` select row · `Enter` drawer · `Esc` close.
- **Shareable views:** filters/sort/page live in the URL hash (`#q=heme&min_relevance=60&sort=citations&dir=desc&page=2`) via `replaceState`; opening such a link restores the view.
- `?mock=1`: ~120 clearly-labelled synthetic rows, fully client-side (list, facets, rows, pdf, exports), loud "MOCK DATA — layout check only" banner, `.invalid` URLs; never activates without the param.

## Expansion backlog (Lior asked to brainstorm) — built vs deferred
Legend: **BUILT** in v1 · **NEXT** small, needs no new API · **API** needs a contract extension (ask Full-Stack) · **LATER** bigger idea.

| # | Idea | Status | Notes |
|---|---|---|---|
| 1 | Quick-filter chips for audit lenses | **BUILT** (10 lenses) | Gate / below gate / has DOI / No DOI / No abstract / Untagged / In Oracle corpus / Not in Oracle corpus / reviews / cited>=10. |
| 2 | Active-filter pills + Clear all | **BUILT** | |
| 3 | Density toggle | **BUILT** | Persisted. |
| 4 | Column picker, persisted | **BUILT** | Versioned key. |
| 5 | Keyboard shortcuts | **BUILT** | See above. |
| 6 | Detail drawer (abstract, main_claim, tags) | **BUILT** | One `POST /rows` per open, cached. |
| 7 | Shareable URL state | **BUILT** | |
| 8 | Select-all-matching across pages | **BUILT** | Client paging, cap 2,000. |
| 9 | **Audit lenses: No DOI / No abstract / Untagged / In Oracle corpus / Not in Oracle corpus** | **BUILT** (2026-10-05) | Uses tri-state `has_doi`, `has_abstract`, `has_tags`, `in_oracle` (1/0). Each has a lens chip, a Yes/No/Any select in the filter panel, an active pill, URL-hash persistence, Clear-all. Opposite lenses share one state value so they are mutually exclusive by construction. `has_main_claim` omitted (0 papers lack it). Still open: a canonical "unreviewed" `review_status` value. |
| 10 | **Saved views** (named filter+sort+columns presets, e.g. "Below gate, reviews excluded") | NEXT | localStorage `mc_papers_views_v1` (same pattern as Inventory); later sync via a tiny server table so the team shares them. |
| 11 | **Coverage strip: year x topic heat-strip** above the table (click a cell = filter) | API | Needs `GET /facets?matrix=year,topic` (counts). Shows where the corpus is thin at a glance — turns the browser into a coverage tool. |
| 12 | Histogram brush on year / relevance in the filter panel | API | Same facets endpoint with buckets; replaces number boxes with a draggable range. |
| 13 | Tag/topic bulk actions on the selection ("mark reviewed", "add tag") | LATER | Needs write endpoints + audit trail; changes the module from reader to curator — decide with Data Engineer. |
| 14 | Compare two papers side-by-side from 2 ticked rows | LATER | Reuse the drawer layout x2; pairs with `/api/compare`. |
| 15 | Duplicate / near-duplicate finder (same DOI, fuzzy title) | API | Server-side group query; a "duplicates" lens + group badge in the row. |
| 16 | Cell-level "quality flags" (missing DOI, year out of range, empty authors) as a small row indicator | NEXT | Pure client from list payload; sorted by flag count = instant triage queue. |
| 17 | Copy-citation / copy-DOI buttons in row + drawer | NEXT | One-click clipboard; BibTeX export of the selection is a natural follow-on. |
| 18 | "Open in Oracle" — seed an Oracle question from a paper | LATER | Link into `#oracle` with the title as context. |
| 19 | Virtualised/infinite mode toggle | LATER | Not needed at 818 rows / 50 per page; revisit if the corpus is 10x. |
| 20 | Per-column filters in headers (alt layout C) | LATER | Only if the panel proves heavy in real use. |

## Contract notes / questions for Full-Stack
- **Audit lenses (resolved 2026-10-05):** `has_doi`/`has_abstract`/`has_tags`/`in_oracle` accept 1 or 0 and every list item carries boolean `in_oracle` (= citable AND relevance_llm>=60). Backlog #9. Counts on 818 papers: no DOI 49, no abstract 28, untagged 70, in Oracle 319, not in Oracle 499.
- **Gate lens vs In Oracle lens:** kept both. "Passes relevance gate" is relevance_llm>=60 only (score view); "In Oracle corpus" is the true Oracle predicate (also requires citable), so it is stricter. Gate AND Not-in-Oracle isolates papers that score well but aren't citable, the most actionable audit set. Opposite lens pairs are mutually exclusive.
- **"In Oracle?" column** (check / dash, default OFF) in the column picker and an "In Oracle corpus" badge in the drawer. Mock mode derives mock `in_oracle` as (doi or url) and relevance>=60 and supports all new lenses client-side.
- Open-link fallback: if a row has `doi` but neither `doi_url` nor `url`, the UI builds `https://doi.org/<doi>`; say if you'd rather the API guarantee `doi_url`.
- `topic` / `tag` values are sent as slugs (comma-separated), as in the contract; slugs must not contain commas.
- 400 responses are shown with `error.message` (or `error`) when present.
- `authors` may be a string or an array; the UI accepts both (joined with "; ").
- Export CSV via GET relies on `Content-Disposition`; the UI does not read the response (plain anchor navigation, `download` attribute).

## Verification (what could and could not be tested)
Executed in a headless Chromium (screenshots at 1440x800 and 1100x700, mock mode): layout, no page scroll, sticky header, selection bar, drawer, column picker. Executed in jsdom with stubbed `fetch`: contract-shaped responses (hash parsing → exact query string, pager, escaping), 404 → "not enabled", 503 → error+retry, mock never active without `?mock=1`, mock paging/sort/filter/select/exports/drawer/PDF toast. **Not tested:** the real `/api/papers-browser*` endpoints (not live when built), real SheetJS file output (stubbed in jsdom; the CDN script is the same one the mockup already loads), real Unpaywall PDF flows, and the in-app iframe inside the live shell (chip/scene wiring verified in jsdom only).
