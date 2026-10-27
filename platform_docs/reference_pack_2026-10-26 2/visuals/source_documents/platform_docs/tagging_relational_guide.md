_Last updated: 2026-07-08 09:47 UTC · Algorithm Expert (parallel team run) · relational-tag usage + retrieval guide (written to the incoming `tags`/`source_tags` schema)_

# Relational tagging — connect sources, power retrieval

A practical guide to the `tags` / `source_tags` junction the Data Engineer is building in parallel:
how to read it, query it, and use it to make the Oracle smarter than plain full-text search. Written
for Lior — everything below is meant to be run, not just read.

**Contents:** [1. The model, plainly](#1-the-model-plainly) · [2. SQL recipes](#2-copy-pasteable-sql-recipes) · [3. Powering the Oracle / RAG](#3-how-this-powers-the-oracle--rag)

---

## Status & assumptions (read this first)

- **As of this writing, `tags` and `source_tags` do not exist yet** — there's no migration file for
  them in `db/migrations/`, and grepping the repo confirms zero references. This doc is written
  *ahead of* the schema landing, to the fixed shape below, so retrieval work and tag-population work
  can proceed in parallel without blocking on each other.
- **Assumed DDL** (confirm the real column types/constraints once the Data Engineer's migration
  lands — the shapes below are the standard/reasonable choice, not a guess at anything unusual):

  ```sql
  CREATE TABLE tags (
      id       BIGSERIAL PRIMARY KEY,
      category TEXT NOT NULL,   -- 'pathway' | 'method' | 'sensory_descriptor' | 'matrix' | 'compound_class'
      name     TEXT NOT NULL,   -- display form, e.g. 'Maillard'
      slug     TEXT NOT NULL,   -- lookup key, e.g. 'maillard'
      UNIQUE (category, slug)
  );

  CREATE TABLE source_tags (
      source_id BIGINT NOT NULL REFERENCES sources(id),
      tag_id    BIGINT NOT NULL REFERENCES tags(id),
      PRIMARY KEY (source_id, tag_id)
  );
  CREATE INDEX ON source_tags (tag_id);   -- reverse lookup (tag → sources); the PK alone only
                                           -- optimizes source → tags, and most recipes below
                                           -- need the other direction too.
  ```

- **Corpus today:** 818 `sources`. `source_topics` (taxonomy) has 329 rows. `source_tags` has **0**
  rows (table doesn't exist yet). Don't confuse this with the "~72 tagged" figure floating around —
  that's `pipeline/tag_sources.py` filling the five **flat** `TEXT[]` columns migration `0005` added
  directly on `sources` (`pathway`, `method`, `sensory_descriptor`, `matrix`, `compound_class`) as an
  interim measure. Those flat columns are almost certainly the seed data for `tags`/`source_tags` —
  see the box below.
- **You do not need this populated to use this guide.** Every recipe below works on an empty table;
  swap in real ids/slugs once rows exist.

---

## 1. The model, plainly

Three separate many-to-many junctions hang off `sources`, each answering a different question:

```
sources (818 rows: id, name, abstract, search_vec, priority_score, relevance_llm,
         study_type, main_claim  ← these two are plain TEXT columns, NOT junctioned)
  │
  ├─ source_topics (source_id, topic_id) ──── topics (91 keywords / 5 branches; 329 sources tagged)
  │     "which taxonomy branch/keyword is this paper filed under?"
  │     The governing bible (`db/taxonomy/keywords_topics.json`) — mostly assigned at ingest time,
  │     one paper usually sits under a handful of topics. Strategic/organizational.
  │
  ├─ source_tags (source_id, tag_id) ──────── tags (id, category, name, slug)
  │     "what's actually IN this paper, scientifically?" — five cross-cutting FACETS:
  │       pathway · method · sensory_descriptor · matrix · compound_class
  │     Assigned by reading the abstract (LLM extraction / curation), many-to-many both ways —
  │     one source can carry several tags per category, one tag applies to many sources.
  │     This is the fine-grained, connective layer — the subject of this guide.
  │
  └─ source_molecules (source_id, molecule_id) ─ molecules (799 rows)
        Specific NAMED compounds the paper discusses (e.g. "2,5-dimethylpyrazine").
        Contrast with the `compound_class` TAG, which is a coarse bucket (e.g. "Pyrazines") —
        a source can be tagged `compound_class = {Pyrazines}` *and* separately linked via
        `source_molecules` to the exact molecule. Tag = category the paper is about;
        molecule link = the specific thing the paper names.
```

**Mental model:** `topics` is the library shelf — which section this paper is filed under.
`tags` are index-card facets — cross-cutting attributes you use to pull related papers *regardless*
of which shelf they're on. Two sources in totally different taxonomy branches (say, one filed under
`meat_science`, one under `meat_analogs`) can still be tightly connected because they share
`pathway = Maillard` and `method = GC-MS`. That cross-branch connective power is what `source_tags`
gives you that `source_topics` structurally can't.

The five categories, with realistic example values (matching migration `0005`'s own comments, since
that's almost certainly where the vocabulary comes from):

| category             | example tag values                          |
|----------------------|----------------------------------------------|
| `pathway`             | Maillard, lipid oxidation, Strecker degradation |
| `method`              | GC-MS, GC-O, SPME, sensory panel              |
| `sensory_descriptor`  | roasted, meaty, sulfurous                     |
| `matrix`              | beef, plant-protein, model system             |
| `compound_class`      | pyrazines, aldehydes, thiols                  |

`study_type` (review / experimental / patent / modeling) and `main_claim` (one-line finding) stay as
plain columns on `sources` — single-valued, not worth a junction, but useful to `SELECT` alongside
tag results so a list of "connected sources" is legible, not just a wall of ids (see §2.3, §2.7).

### Where the rows will come from

`sources` already carries the five flat `TEXT[]` columns above (migration `0005`), and
`pipeline/tag_sources.py` is filling them via an LLM pass (~72/818 done as of 2026-07-08, resumable).
The natural path into `tags`/`source_tags` is to **promote** those arrays: one distinct `tags` row
per unique value per category, one `source_tags` row per (source, value) pair. Illustrative only —
this is the Data Engineer's call and not something to run from this doc:

```sql
-- Promote one category's flat array into the junction (repeat per category).
INSERT INTO tags (category, name, slug)
SELECT DISTINCT 'pathway', v, lower(regexp_replace(v, '[^a-zA-Z0-9]+', '-', 'g'))
FROM sources, unnest(pathway) AS v
ON CONFLICT (category, slug) DO NOTHING;

INSERT INTO source_tags (source_id, tag_id)
SELECT s.id, t.id
FROM sources s, unnest(s.pathway) AS v
JOIN tags t ON t.category = 'pathway'
           AND t.slug = lower(regexp_replace(v, '[^a-zA-Z0-9]+', '-', 'g'))
ON CONFLICT DO NOTHING;
```

---

## 2. Copy-pasteable SQL recipes

All of these run as-is in the Neon SQL console / `psql` / DBeaver — just swap the literal example
id (`123`) or slug (`'maillard'`) for a real one. (§3's recipes use `%s` psycopg2 placeholders
instead, since those are meant to be pasted into `pg_rows()` calls in `meatcode_server.py` — flagged
there.)

### 2.1 All tags on a given source

```sql
SELECT t.category, t.name, t.slug
FROM source_tags st
JOIN tags t ON t.id = st.tag_id
WHERE st.source_id = 123
ORDER BY t.category, t.name;
```

Grouped-by-category form (handy for a detail-page render — one JSON blob):

```sql
SELECT jsonb_object_agg(category, names) AS tags_by_category
FROM (
    SELECT t.category, array_agg(t.name ORDER BY t.name) AS names
    FROM source_tags st
    JOIN tags t ON t.id = st.tag_id
    WHERE st.source_id = 123
    GROUP BY t.category
) c;
```

### 2.2 All sources carrying a given tag (by category)

```sql
-- All sources tagged pathway = Maillard
SELECT s.id, s.name, s.year, s.priority_score
FROM source_tags st
JOIN tags t    ON t.id = st.tag_id
JOIN sources s ON s.id = st.source_id
WHERE t.category = 'pathway' AND t.slug = 'maillard'
ORDER BY s.priority_score DESC NULLS LAST;
```

If you already have the `tag_id` (e.g. from a UI filter chip), skip the `tags` join:

```sql
SELECT s.id, s.name, s.year
FROM source_tags st
JOIN sources s ON s.id = st.source_id
WHERE st.tag_id = 17
ORDER BY s.priority_score DESC NULLS LAST;
```

### 2.3 ★ "Connect sources" — sources that SHARE tags with source X, ranked by shared-tag count

This is the key query — the one behind a "related sources" panel on any paper's detail page.

```sql
WITH seed_tags AS (
    SELECT tag_id FROM source_tags WHERE source_id = 123
)
SELECT
    s.id,
    s.name,
    s.year,
    s.priority_score,
    s.main_claim,
    COUNT(*)                          AS shared_tags,
    array_agg(t.name ORDER BY t.name) AS shared_tag_names
FROM source_tags st
JOIN seed_tags ON seed_tags.tag_id = st.tag_id
JOIN tags t    ON t.id = st.tag_id
JOIN sources s ON s.id = st.source_id
WHERE st.source_id <> 123
GROUP BY s.id, s.name, s.year, s.priority_score, s.main_claim
ORDER BY shared_tags DESC, s.priority_score DESC NULLS LAST
LIMIT 10;
```

Category-scoped variant — e.g. "only sources that share a *mechanism* with X" (ignore that they might
also share, say, a method tag), useful when you want mechanism-similar neighbours specifically rather
than similar-on-anything:

```sql
WITH seed_tags AS (
    SELECT st.tag_id
    FROM source_tags st
    JOIN tags t ON t.id = st.tag_id
    WHERE st.source_id = 123 AND t.category = 'pathway'
)
SELECT s.id, s.name, s.year, COUNT(*) AS shared_pathway_tags
FROM source_tags st
JOIN seed_tags ON seed_tags.tag_id = st.tag_id
JOIN sources s ON s.id = st.source_id
WHERE st.source_id <> 123
GROUP BY s.id, s.name, s.year
ORDER BY shared_pathway_tags DESC
LIMIT 10;
```

### 2.4 Tag co-occurrence

Which `method` tags co-occur with the `Maillard` pathway tag (and how often)?

```sql
SELECT
    method_tag.name AS method,
    COUNT(DISTINCT st_method.source_id) AS n_sources
FROM tags pathway_tag
JOIN source_tags st_pathway ON st_pathway.tag_id = pathway_tag.id
JOIN source_tags st_method  ON st_method.source_id = st_pathway.source_id
JOIN tags method_tag ON method_tag.id = st_method.tag_id AND method_tag.category = 'method'
WHERE pathway_tag.category = 'pathway' AND pathway_tag.slug = 'maillard'
GROUP BY method_tag.name
ORDER BY n_sources DESC;
```

General form — every `(pathway tag, sensory tag)` pair and how many sources carry both. Swap the two
`category` filters for any pair of categories; this is exactly what feeds a co-occurrence heatmap:

```sql
SELECT
    ta.name AS pathway_tag,
    tb.name AS sensory_tag,
    COUNT(DISTINCT sa.source_id) AS n_sources
FROM source_tags sa
JOIN tags ta ON ta.id = sa.tag_id AND ta.category = 'pathway'
JOIN source_tags sb ON sb.source_id = sa.source_id
JOIN tags tb ON tb.id = sb.tag_id AND tb.category = 'sensory_descriptor'
GROUP BY ta.name, tb.name
ORDER BY n_sources DESC
LIMIT 30;
```

### 2.5 Per-category faceting / counts

```sql
-- Tag counts within one category (e.g. build the "Method" filter chips + counts)
SELECT t.name, t.slug, COUNT(st.source_id) AS n_sources
FROM tags t
LEFT JOIN source_tags st ON st.tag_id = t.id
WHERE t.category = 'method'
GROUP BY t.id, t.name, t.slug
ORDER BY n_sources DESC, t.name;
```

```sql
-- Tag counts across ALL categories at once (drives a full facet panel)
SELECT t.category, t.name, COUNT(st.source_id) AS n_sources
FROM tags t
LEFT JOIN source_tags st ON st.tag_id = t.id
GROUP BY t.category, t.id, t.name
ORDER BY t.category, n_sources DESC;
```

```sql
-- Coverage per category: how many of the 818 sources have >=1 tag in each?
SELECT t.category, COUNT(DISTINCT st.source_id) AS sources_tagged
FROM tags t
JOIN source_tags st ON st.tag_id = t.id
GROUP BY t.category
ORDER BY t.category;
```

```sql
-- Overall: tagged vs untagged (any category) — the same shape as the
-- source_topics coverage check already used in analysis/white_space_analysis.py
SELECT
    COUNT(*) FILTER (WHERE has_tag)     AS tagged,
    COUNT(*) FILTER (WHERE NOT has_tag) AS untagged
FROM (
    SELECT s.id, EXISTS (SELECT 1 FROM source_tags st WHERE st.source_id = s.id) AS has_tag
    FROM sources s
) x;
```

### 2.6 Source similarity over `source_tags` (shared-count + Jaccard)

Similarity between two *specific* sources — shared-tag count plus Jaccard
(`|shared| / |union|`, which corrects for one source just having way more tags than the other):

```sql
WITH a_tags AS (SELECT tag_id FROM source_tags WHERE source_id = 123),
     b_tags AS (SELECT tag_id FROM source_tags WHERE source_id = 456)
SELECT
    (SELECT COUNT(*) FROM a_tags) AS tags_a,
    (SELECT COUNT(*) FROM b_tags) AS tags_b,
    (SELECT COUNT(*) FROM a_tags JOIN b_tags USING (tag_id)) AS shared,
    ROUND(
      (SELECT COUNT(*) FROM a_tags JOIN b_tags USING (tag_id))::numeric
      / NULLIF((SELECT COUNT(*) FROM (
            SELECT tag_id FROM a_tags UNION SELECT tag_id FROM b_tags
        ) u), 0)
    , 3) AS jaccard;
```

Full pairwise graph — top 50 most-similar pairs across the *whole* corpus. This table is exactly the
edge list for a "related sources" graph (nodes = sources, edges = shared tags, weight = Jaccard):

```sql
WITH tag_counts AS (
    SELECT source_id, COUNT(*) AS n_tags
    FROM source_tags
    GROUP BY source_id
),
pairs AS (
    SELECT a.source_id AS source_a, b.source_id AS source_b, COUNT(*) AS shared
    FROM source_tags a
    JOIN source_tags b ON b.tag_id = a.tag_id AND b.source_id > a.source_id   -- unordered, no self-pairs
    GROUP BY a.source_id, b.source_id
)
SELECT
    p.source_a, p.source_b, p.shared,
    ca.n_tags AS tags_a, cb.n_tags AS tags_b,
    ROUND(p.shared::numeric / (ca.n_tags + cb.n_tags - p.shared), 3) AS jaccard
FROM pairs p
JOIN tag_counts ca ON ca.source_id = p.source_a
JOIN tag_counts cb ON cb.source_id = p.source_b
ORDER BY jaccard DESC, p.shared DESC
LIMIT 50;
```

At current/near-term scale (hundreds of sources, a handful of tags each) this is cheap. If the corpus
or tag density grows a lot, don't materialize all pairs — wrap the per-source version (§2.3) in a
`LATERAL` join to precompute just the top-N neighbours per source instead of the full N² table.

### 2.7 Bonus: full profile of a source (topics + tags + molecules together)

Ties all three junctions from §1 into one row — useful for a paper detail view, or just to sanity-check
how the systems compose:

```sql
SELECT
    (SELECT array_agg(DISTINCT tp.name) FROM source_topics st2
       JOIN topics tp ON tp.id = st2.topic_id WHERE st2.source_id = s.id)    AS topics,
    (SELECT jsonb_object_agg(category, names) FROM (
        SELECT tg.category, array_agg(tg.name ORDER BY tg.name) AS names
        FROM source_tags stg JOIN tags tg ON tg.id = stg.tag_id
        WHERE stg.source_id = s.id GROUP BY tg.category
     ) x)                                                                    AS tags_by_category,
    (SELECT array_agg(DISTINCT m.name) FROM source_molecules sm
       JOIN molecules m ON m.id = sm.molecule_id WHERE sm.source_id = s.id)  AS molecules
FROM sources s
WHERE s.id = 123;
```

### Recommended constraints & indexes

Not applied by this doc — confirm with the Data Engineer — but worth flagging since every recipe
above depends on them for correctness/speed: `UNIQUE (category, slug)` on `tags` (idempotent
population passes, and makes `ON CONFLICT` promotion inserts work — see §1); `PRIMARY KEY
(source_id, tag_id)` on `source_tags` with FKs to `sources(id)` / `tags(id)`; an index on
`source_tags(tag_id)` (the PK alone only optimizes *source → tags*, but §2.2/§2.3/§2.4/§2.6 all need
*tag → sources* too); and an index on `tags(category)` for faceting.

---

## 3. How this powers the Oracle / RAG

**Reality check first.** Today, `POST /api/ask` in `server/meatcode_server.py` sends
`send_event("sources", "[]")` (line 554) and then streams a raw Claude answer with no retrieval at
all — the Oracle is currently **ungrounded**. Separately, `sources.search_vec` (a `tsvector` column
+ GIN index + auto-refresh trigger, migration `0001`, applied live) is real and populated — every
source ingested via `pipeline/openalex_ingest.py` gets it auto-filled by the trigger — but nothing in
the live server queries it yet. So "existing FTS retrieval" means *live, populated infrastructure
that isn't wired into `/api/ask` yet*, not a working pipeline to improve. The recipes below are the
concrete next step: wire FTS in, then use tags to sharpen it from day one rather than bolting them on
later. (One more repo-hygiene note: the `0001` migration file itself isn't in `db/migrations/` today —
similar to the `db/connect.py` source loss the audit-loop session flagged — worth a `git log`
check/restore when someone picks this up.)

These recipes use `%s` (psycopg2 placeholders, matching `pg_rows()`'s existing convention in
`meatcode_server.py`) since they're meant to be pasted straight into a new `if path == "/api/ask"`
retrieval step, not run standalone in a SQL console.

### 3.1 Tag-aware filtering / boosting

**Simplest form — hard filter.** Mirrors the pattern `/api/sources` already uses for `topic`
filtering (an `EXISTS` subquery against `source_topics`/`topics`, lines 368–373) — same shape, aimed
at tags instead. Use this when the UI already knows the category (e.g. a "search within Maillard
sources only" toggle):

```sql
WITH q AS (SELECT websearch_to_tsquery('english', %s) AS tsq)   -- param 1: the question
SELECT s.id, s.name, s.abstract, s.year,
       ts_rank(s.search_vec, q.tsq) AS fts_rank
FROM sources s, q
WHERE s.search_vec @@ q.tsq
  AND s.relevance_llm >= 60                                     -- keep the existing off-topic gate
  AND EXISTS (
        SELECT 1 FROM source_tags st JOIN tags t ON t.id = st.tag_id
        WHERE st.source_id = s.id AND t.category = 'pathway' AND t.slug = %s   -- param 2
      )
ORDER BY ts_rank(s.search_vec, q.tsq) DESC
LIMIT 8;
```

**Free-text form — soft boost.** For a plain Oracle question with no explicit category selected:
rank by FTS first, then add a boost for sources whose tags match a short list of slugs (`%s` takes a
Python list, bound via `= ANY(%s)`). Don't solve "which tags does this question imply" in SQL — fetch
the ~few-hundred-row `tags` table once (cheap, cacheable) and match candidate slugs in application
code (simple substring/keyword match against `tags.name`), then pass the resulting slug list in here:

```sql
WITH q AS (
    SELECT websearch_to_tsquery('english', %s) AS tsq          -- param 1: the question
),
ranked AS (
    SELECT s.id, s.name, s.abstract, s.year, s.priority_score,
           ts_rank(s.search_vec, q.tsq) AS fts_rank
    FROM sources s, q
    WHERE s.search_vec @@ q.tsq
      AND s.relevance_llm >= 60
),
boost AS (
    SELECT st.source_id, COUNT(*) AS matching_tags
    FROM source_tags st
    JOIN tags t ON t.id = st.tag_id
    WHERE t.slug = ANY(%s)                                     -- param 2: e.g. ['maillard','strecker']
    GROUP BY st.source_id
)
SELECT r.*, COALESCE(b.matching_tags, 0) AS matching_tags,
       r.fts_rank + 0.2 * COALESCE(b.matching_tags, 0) AS combined_score
FROM ranked r
LEFT JOIN boost b ON b.source_id = r.id
ORDER BY combined_score DESC
LIMIT 8;
```

**Zero-result fallback.** `PROJECT_STATE.md`'s Open Items flags the known failure mode:
`websearch_to_tsquery` ANDs every term, so a full natural-language question often matches **0 rows**
and the Oracle silently has nothing to cite. Tags give you a fallback path that doesn't depend on FTS
at all — if the FTS query above returns nothing, fall back to tag-only retrieval ranked by
`priority_score`:

```sql
SELECT s.id, s.name, s.year, s.priority_score
FROM sources s
JOIN source_tags st ON st.source_id = s.id
JOIN tags t ON t.id = st.tag_id
WHERE t.category = 'pathway' AND t.slug = %s                  -- from the same keyword→tag match
  AND s.relevance_llm >= 60
ORDER BY s.priority_score DESC NULLS LAST
LIMIT 8;
```

### 3.2 Related-source expansion (after an FTS hit, pull neighbours via shared tags)

Two-step: run the FTS query, take its top hit's id, then reuse §2.3's "connect sources" shape to pull
that source's tag-neighbours. This surfaces mechanism/method-similar sources that don't happen to
share the FTS keywords verbatim — useful when the literal query is narrow but the corpus has related
material phrased differently:

```sql
-- Step 2: given the top FTS hit's id, pull its tag-neighbours.
WITH seed_tags AS (
    SELECT tag_id FROM source_tags WHERE source_id = %s        -- param: top FTS hit's id
)
SELECT s.id, s.name, s.year, COUNT(*) AS shared_tags
FROM source_tags st
JOIN seed_tags ON seed_tags.tag_id = st.tag_id
JOIN sources s ON s.id = st.source_id
WHERE st.source_id <> %s AND s.relevance_llm >= 60              -- param: same id again
GROUP BY s.id, s.name, s.year
ORDER BY shared_tags DESC
LIMIT 3;
```

Merge FTS hits (top ~5) with their tag-neighbours (top ~2–3 each, deduped by id), cap the combined
list at ~8, and pass that as the `sources` payload of the existing SSE contract
(`event: sources` → `event: chunk` → `event: done`, already implemented in `do_POST`/`send_event`) —
no change to the mockup needed, since it already renders whatever the `sources` event contains and
currently just gets `[]`.

### 3.3 Eval angle — does tag-filtering actually lift retrieval quality?

Same shape as the audit judge's own validation (`analysis/audit_eval.md`) — don't trust a retrieval
change just because it looks reasonable; measure it against a small human-labeled set before making
it the default.

1. **Gold set.** Hand-pick ~15–25 realistic Oracle questions, spanning easy (one clear pathway/method,
   e.g. "How does GC-O detect meaty aroma compounds?") through hard/multi-concept (the kind likely to
   trip the AND-query 0-result problem, e.g. "How does Maillard chemistry differ between beef and
   plant-protein matrices?"). For each, record which source ids *should* come back (5–10 judged
   relevant). Store as `analysis/retrieval_gold.csv`: `question, source_id, relevant (0/1), notes` —
   same shape as the existing `analysis/audit_gold.csv` convention. To bootstrap faster than labeling
   cold: pre-filter candidates to `relevance_llm >= 60` and skim top-`priority_score` results per
   question, then just confirm/reject that shortlist rather than reading all 818.
2. **Two arms per question.** Arm A = FTS-only (the `ranked` CTE alone, no boost/filter). Arm B =
   FTS + tags (§3.1's filter or boost form). Capture each arm's top-8 ids.
3. **Metrics**, per question then averaged: **Precision@8** = `|retrieved ∩ relevant| / 8`;
   **Recall@8** = `|retrieved ∩ relevant| / |relevant|`; and **0-result rate** = fraction of gold
   questions where the arm returns nothing — track this one specifically, since it's the *documented*
   current failure mode, and a fallback that cuts it is a win even before precision moves.
4. **Decide, don't eyeball a single run.** With ~20 questions, a 1-question swing is noise. Look for a
   consistent improvement across most questions (not an average dragged by one outlier) before
   promoting tag-filtering from "available" to "default." Re-run this eval whenever the tag vocabulary
   or the FTS query changes, same discipline as `audit_eval.md` recommends for the judge.

---

## Related docs

- `docs/white_space_map.md` — the current gap analysis runs on `source_topics` only (40% coverage);
  it gets a second, complementary lens once tags are populated (a topic can look "covered" while every
  source in it shares one narrow `method`/`matrix` — tags would surface that).
- `docs/data_audit_loop.md` + `analysis/audit_eval.md` — the audit loop already flags "no tags stored
  despite clear relevance" on most untagged sources; this junction is what that finding is pointing at.
- `db/migrations/0005_source_tag_columns.sql` — the flat-column predecessor `tags`/`source_tags`
  most likely promotes from (see §1).
- `PROJECT_STATE.md` — corpus counts, the `/api/ask` ungrounded-Oracle status, and the
  `websearch_to_tsquery` 0-result risk referenced in §3.
