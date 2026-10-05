<!-- Last updated: 2026-10-05 14:49 UTC · Advisory · new decision record + brainstorm for the dev-only Papers browser (flag `papers_browser`) -->

# Papers browser — decision record & brainstorm

**Status:** Recommendation. Owner: Advisory. Audience: Lior (PM), Daniel (for the decisions in §6).
**Data basis:** live Neon `sources` queried (SELECT only) on 2026-10-05; numbers below are not from docs.

## TL;DR

Build it, but as a **narrow dev tool**, not a fourth table. v1 = a fast, filterable, sortable, paginated *selection-and-export* surface over `sources` whose defaults are the **audit lenses** (not "all 818 by year"), with row-level open-link + best-effort Unpaywall link, tick → CSV/XLSX, full-table CSV. **No write-back in v1.** The genuinely new thing is *selection + lens + export manifest*, not browsing. Everything else (flag-for-Daniel, collections, duplicate review, heatmap) is later and each is gated on a trigger below.

## 1. Who uses it, for what — and what the data says

| Job | User | What they need from the table |
|---|---|---|
| Curate the corpus before Daniel's review | Lior / dev team | Slice by relevance band + tag state, tick a batch, export to xlsx for Daniel |
| Hunt quarantine / audit candidates (B2) | Lior, Data Eng | "Low relevance but high priority", "untagged", "borderline 40-59", "audited = review" |
| Build eval / gold sets (A4 benchmark, `audit_gold.csv`) | Algorithm Expert | Stratified pick across relevance bands/study types; stable IDs in the export |
| Hand a slice to Daniel / Yochai | Lior | A clean file with titles, DOI links, abstract, relevance, tags; nothing internal-only |
| WUR-style sharing | Lior | Same as above, minus internal scoring columns |

**Data reality that should drive defaults (818 sources):**

- **Relevance is the axis that matters.** `relevance_llm`: 139 at 80+, 180 at 60-79, 170 at 40-59, **329 below 40**. Only **319 (39%) pass the Oracle's >=60 gate** (312 of them with an abstract). Note the <40 pile has grown past the "202" quoted in older docs; the stale number is in PROJECT_STATE/audit docs.
- **Linkability is strong.** 818/818 have a URL (797 are `doi.org` links), 769 have a DOI, 790 have an abstract, 0 rows have neither DOI nor URL. So "open link" is near-universal; the Unpaywall step only applies to the 769 with a DOI, and it is best-effort.
- **Enrichment is mostly empty or unfilled — do not present it as signal.** `review_status` = `pending` for all 818; `trust_tier` is NULL for all 818; `composite_score` = 0 for all; `tailored_abstract` 30/818; `top_keywords` 309; `pathway`/`method`/`matrix` are empty arrays on ~300-330 rows each. `study_type` is the one well-filled facet (experimental 580, review 194, method 17, modeling 12, other 15).
- **Tags:** 252 sources have no `source_topics` row (31%).
- **Year is heavily skewed:** 798/818 are 2020+, 599 are 2025-26, only 7 predate 2010. A year slider is nearly useless; use year *buckets* (2025-26 / 2020-24 / older).
- **Citations:** 441 have `citation_count > 0` (max 1,295), 8 NULL. Usable as a sort, weak as a quality filter on a 2025-heavy corpus (recent papers have not accrued citations).
- **Duplicates are not a real problem:** 0 DOI duplicates, 4 title-normalised duplicate groups. Dedupe already ran (818 after removing 10).
- **Audit trail is tiny:** `source_audits` has 40 rows (18 keep / 18 review / 4 quarantine), so "audited" is a lens, but a small one today.

Implication: the default view should be **relevance-desc, with a visible band selector**, and the filters worth building are relevance band, in-Oracle indicator, tag state (tagged/untagged), study type, review flag, has-DOI/has-abstract, year bucket, topic, free-text. Pathway/method/matrix facets and `trust_tier` should be hidden or marked "unfilled" until populated.

## 2. Recommended scope

### v1 (build now, dev-only)
- Server-side paginated list (50/page), sort, filter, text search over title/abstract/venue (reuse the existing `search_vec`).
- **Audit-lens quick filters** as one-click presets, each a plain filter combo:
  1. Oracle-eligible (>=60) · 2. Borderline 40-59 (the flip zone) · 3. Likely off-topic (<40) · 4. Untagged (252) · 5. High priority but low relevance (disagreement between `priority_score` and `relevance_llm`) · 6. Missing abstract (28) · 7. Audited-as-review/quarantine (from `source_audits`).
- **"In Oracle corpus?" column** = `relevance_llm >= 60 AND citable` (same predicate the Oracle uses; one shared SQL expression, not a re-implementation, so the browser can never disagree with retrieval). This is the single most useful new column.
- Row-select (persists across pages) → CSV/XLSX of selected; "export all matching current filters" and "whole table" CSV.
- Per-row: open (DOI/URL) and Unpaywall OA link, **links only, fetched lazily on click, cached server-side briefly.**
- Export columns: a **curated, labelled set** (id, title, authors, year, venue, DOI, URL, relevance_llm, priority_score, in-Oracle, study_type, is_review, citation_count, topics, abstract optional). Default **excludes** the empty enrichment columns.
- Every export carries a header block / sheet: timestamp, filter description, row count, schema version. This is the cheap 80% of "saved-export manifests".
- Shareable URLs: encode filters/sort/page in the query string. Free, no storage, and it makes "look at this slice" a link. **Do this in v1.**

### Later, with triggers
| Item | Verdict | Trigger / reason |
|---|---|---|
| Flag for Daniel / mark quarantine candidate (write-back) | **Not v1** | See below. |
| Saved views (named, stored) | v2 | Only after URL-encoded views prove people reuse the same few. Requires identity to be meaningful. |
| Collections | v2/v3 | Needs a table + owner. Substitute now: export manifest + a pasted ID list. |
| Duplicate detection | **Skip as a feature** | 0 DOI dupes, 4 title groups. Show a 4-row report in the audit, not a UI. Revisit if ingestion resumes (blocked today). |
| Coverage heatmap year x topic | v2, **but build it in the existing white-space/Analytics surface**, not here | Year is 95% 2020+, so the year axis is nearly degenerate. Topic x relevance-band is the informative heatmap. |
| Citation-quality columns | v1.5 | Add `citation_count`, `is_review`, venue now (already filled). Anything computed (citations/year, venue tier) waits; recency bias makes raw citations misleading. |
| Saved-export manifests (persisted) | v2 | v1 embeds the manifest in the file; persist only if someone needs to reproduce a handed-over slice. |

### Why write-back is deliberately NOT in v1
1. **There is no identity.** The site is behind one shared password; any write ("flagged by") is anonymous and unattributable. Daniel's verdicts are a signed judgement; an anonymous button cannot carry that.
2. **B2 is unresolved.** Confirmed quarantines write only to `source_audits`, not to `relevance_llm`, so the system already has one half-wired verdict path. A second write path (from a UI) before the first is closed creates two sources of truth about what is quarantined.
3. **Blast radius.** A tick-and-click bulk "quarantine" on a shared password is exactly the silent, correlated damage the audit-loop design was built to avoid (human-gated, reversible, append-only).
4. **Validation-year guardrail.** It turns a read tool into a workflow product.

**Safe path:** (a) v1 exports a *"Review sheet"* template (id, title, current relevance, blank `Daniel call` column: keep/quarantine/back-tag, blank note) in the same format Daniel already uses (`daniel_review_workflow.md`); verdicts come back by row and are applied through the existing audit path. (b) When B2 lands, add an **append-only `source_flags` table** (source_id, flag, note, free-text "who" self-declared, timestamp), written by the endpoint, **never touching `sources` columns**; the Data Engineer reads flags into the existing review queue. Flags are *suggestions*; a human-gated script applies them. (c) Only add real attribution if/when auth moves beyond a shared password.

## 3. Risks & guardrails (for the humans to check)

- **PDF / copyright / Unpaywall.** We return links only and store nothing. Unpaywall's API terms require a real contact email on each request (`email=` parameter) and ask for modest rate (~100k calls/day cap, and they ask to be reasonable). **Action: set `UNPAYWALL_EMAIL` to a real, monitored address** (not a placeholder, not Lior's personal one by accident). Do not proxy, cache or rehost PDFs; surface the publisher's `best_oa_location` URL with its licence label if present, and treat "no OA found" as a normal state. Whether showing OA links to a WUR/Daniel audience raises any licensing question is for legal/GFI to confirm; we are not issuing that verdict.
- **Export size & data exposure.** A full-table CSV is a one-click copy of our curated corpus plus internal scores, behind one shared password that already reaches Daniel, Yochai and anyone they gave it to. Recommendations: (i) the new endpoints must be **flag-gated server-side, not just hidden in the UI** (the `backup_center` precedent was UI-only; the team has now made these endpoints flag-gated too, so verify prod returns 404, not 403 or 200); (ii) full-table export is **dev flag only** and not enabled for external shares; (iii) a `--public` column preset (no priority/relevance/audit fields) for anything leaving GFI; (iv) log export events (count, filter, timestamp) server-side with no identity, consistent with the anonymous question-log option on the board. Bibliographic metadata is largely factual; abstracts are publisher-copyrighted text, so the "with abstracts" export option is the one to flag for a human check before any external hand-off.
- **Untrustworthy or empty enrichment in bulk export.** `trust_tier`, `composite_score`, `review_status` and `tailored_abstract` are empty/constant. Exporting them reads as "scored and reviewed" to an outsider. Hide by default, and where included, label the header `(unfilled)`; never export `review_status=pending` as if it were a status. `relevance_llm` is an LLM score, not a human verdict: label it `relevance_llm (automated)`.
- **Excel hazards.** DOIs and IDs mangled to dates/scientific notation, formula injection from titles beginning `=`/`+`/`-`/`@` (prefix with `'`), UTF-8 BOM for CSV so Hebrew/accents survive in Excel.
- **Scope creep.** This is a corpus-curation convenience, not a MVP deliverable on `MVP_BOARD.md` and not a validation-year proof point. Time-box v1 (the two agents are already building it); anything in the "Later" table needs a named user and a trigger before it is started.
- **Neon cold-start** on first load of the page; show a loading state, don't treat it as an error.

## 4. Relation to existing surfaces — what is genuinely new

| Surface | What it does today | Overlap |
|---|---|---|
| Database -> Sources tab (product) | Read-only exploration of sources for product users | Same rows. Product-facing, curated UX, no export, no audit lenses. |
| Streamlit dashboard (`analysis/`) | Internal analytics, Review Queue tab planned | Aggregates and charts; not a row-selection/export tool. |
| `export_snapshot.xlsx` (`pipeline/export_snapshot.py`) | Curated sample for audit, 50/20/20/20/20 rows | A static sample; not filterable, not live. |
| `/api/data-backup` | Whole-DB dump | Disaster recovery, not curation. |

**New in the browser:** (1) *live*, filterable **selection** across all 818 with persistence across pages; (2) **audit lenses** as presets; (3) the shared-predicate **in-Oracle indicator**; (4) **export of an arbitrary selection with a manifest**; (5) **shareable filter URLs**; (6) per-row OA link. **Not new, so don't build it:** another general "browse" of the corpus, charts, or a duplicate of the Streamlit aggregates. If the Sources tab grows a filter/export, merge, do not fork; the cleanest long-run outcome is the Sources tab consuming the same `/api/papers-browser/*` query layer with the dev-only affordances (full export, lenses) behind the flag. Retire `export_snapshot.xlsx` for audit use once the "Review sheet" export exists.

## 5. Phased roadmap

- **v1 (this build):** list/filter/sort/paginate, audit-lens presets, in-Oracle column, selection + CSV/XLSX + full CSV, open + Unpaywall links, shareable URLs, export manifest, curated column sets, server-side flag gate, Excel-safe exports.
- **v1.5 (days, optional):** "Review sheet" export for Daniel; citation/venue columns; topic filter polish; server export log.
- **v2 (after B2 closes):** append-only `source_flags` write-back; read flags into the Review Queue; named saved views if reuse is observed; topic x relevance heatmap in the white-space surface.
- **v3 (only on demand):** collections, persisted manifests, real attribution if auth changes, merging the query layer into the product Sources tab.

## 6. Open decisions

**Lior**
1. Confirm write-back is out of v1 and the Review-sheet export is the interim path (recommended: yes).
2. Provide the real `UNPAYWALL_EMAIL` and confirm that is acceptable as the contact on outbound requests.
3. Is full-table CSV allowed on **staging** only, or also prod once the flag is flipped? (Recommended: dev/staging only until a `--public` preset exists.)
4. Include abstracts in exports by default? (Recommended: off by default, opt-in checkbox.)
5. Should the Sources tab eventually share this query layer, or stay separate? (Recommended: share.)

**Daniel**
1. Which relevance bands and lenses does he actually want in his review sheet (is 40-59 the right "review" zone)?
2. For slices handed to Yochai/WUR: which columns are acceptable to share (internal scores yes/no)?
3. What counts as a quarantine candidate for him: purely `<40`, or also "high priority but disagreement"? This defines lens #5.
