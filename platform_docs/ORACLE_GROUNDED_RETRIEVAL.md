# Oracle grounded retrieval — implementation notes

_Last updated: 2026-07-08 10:20 UTC · Algorithm Expert · initial version, shipped this session_

Technical companion to `docs/DECISION_Oracle_Answer_Engine.docx` (the plain-English design
decision for Daniel/Lior). That doc picked the shape: one retrieval step, one Claude call,
answer-only-from-retrieved-sources. This doc records how the "this month" / keyword-FTS phase
of that plan was actually implemented in `server/meatcode_server.py`, why two things were added
on top of the original spec, and what's still weak.

## Before → after

**Before:** `POST /api/ask` sent `event: sources` with a hardcoded `"[]"`, then let Claude answer
the raw question from training knowledge with no citations. The mockup's "Sources retrieved" row
always showed "No matches in the database."

**After:** `/api/ask` runs a live retrieval query against `sources.search_vec` before opening the
SSE stream, sends the REAL top-6 rows as `event: sources`, and injects those same rows into
Claude's system prompt with hard citation rules (answer ONLY from these sources, cite `[id]`,
say "the corpus doesn't cover this" otherwise). Falls back to the old behaviour — not a crash —
if `DATABASE_URL` is unset or the query fails for any reason.

## RETRIEVE — the SQL

```sql
SELECT * FROM (
    SELECT id, name AS title, year, COALESCE(journal, venue) AS journal, venue,
           doi, url, abstract,
           ts_rank_cd(search_vec, websearch_to_tsquery('english', %s)) AS rank
    FROM sources
    WHERE search_vec IS NOT NULL
      AND (relevance_llm IS NULL OR relevance_llm >= 60)
) ranked
WHERE rank > 0
ORDER BY rank DESC
LIMIT 6
```

This is the spec'd filter (citable + on-topic, `ts_rank_cd` over `search_vec`, top 6) plus two
things discovered necessary via live testing against Neon while building this feature — both
documented in code comments in `server/meatcode_server.py` right above `_RETRIEVAL_SQL` /
`_retrieve_sources()`, and reproduced here with the evidence:

**1. `WHERE rank > 0` (outer query).** `websearch_to_tsquery('english', question)` ANDs bare
words together. `ts_rank_cd` is provably `0` for a document missing even one AND-term — confirmed
live, e.g. `websearch_to_tsquery('english', 'why does pea protein taste beany off-notes')` →
`'pea' & 'protein' & 'tast' & 'beani' & 'off-not' <2> 'note'`, and a paper titled *"Flavour
Chemistry of Chicken Meat: A Review"* scored a literal `0.0` against it (no shared lexemes) yet
would have been returned as one of the "top 6" without this filter, since without it Postgres
pads `LIMIT 6` with whatever rows tie at `rank = 0` in arbitrary (physical scan) order. A
`SELECT`-list alias can't be referenced in the same query's `WHERE`, hence the subquery wrapper.

**2. A two-tier OR-fallback in `_retrieve_sources()`.** Tier 1 is the query above, run with
`question` as typed (precise). If tier 1 returns zero rows, tier 2 retries the *same* SQL with
one change: the question's words joined by `" OR "` instead of left as-is, e.g. `"key Maillard
reaction products in grilled beef"` → `"key OR Maillard OR reaction OR products OR in OR grilled
OR beef"`, still passed through `websearch_to_tsquery` (which treats a literal `OR` as its OR
operator — this is "websearch" syntax by design, not a hack). Same ranking function, same
citable/on-topic filter, same `LIMIT`, same `rank > 0` guard — the only thing that changes is
AND vs. OR combination of the same terms. This is still plain keyword/FTS search (the "this
month" phase per the decision doc) — no semantic/embedding search, no reranking model, no extra
LLM call. It is exactly `PROJECT_STATE.md`'s own already-flagged "Next" item ("Oracle recall —
tune next... switch to keyword extraction or OR/`|` query semantics to lift recall before any
expert demo"), executed here rather than left for a separate session, because building the
`analysis/oracle_eval/` harness (below) surfaced hard numbers on how badly tier-1-only performs:

| | tier-1 only (AND) | with tier-2 OR-fallback |
|---|---|---|
| 14 sample R&D questions, 0 sources retrieved | **10/14 (71%)** | **0/14** |

That first run (before the fallback existed) is what motivated adding it — the exact same 14
questions, unchanged, went from "the Oracle would say 'corpus doesn't cover this' 71% of the
time even though the corpus does contain relevant material" to full coverage. See
`analysis/oracle_eval/results.md` for the live run with both tiers and a qualitative relevance
read per question (net: 9/14 strong direct hits, 3/14 moderate/mixed, 2/14 weak — the 2 weak ones,
cultivated-meat metallic taste and kokumi, look like genuine corpus gaps consistent with
`analysis/white_space_data.md`, not retrieval bugs).

Because tier 2 only engages when tier 1 finds literally nothing, and because looser OR-matching
is lower-confidence by construction, `_retrieve_sources()` returns `(rows, used_fallback)` and
the grounding prompt adds one extra hedge sentence when `used_fallback=True`, asking Claude to
read abstracts critically rather than assume term-overlap implies relevance.

## GROUND — citation numbering is the real `sources.id`, not 1..6

The system prompt lists retrieved sources as `[id] Title (year, journal)\nabstract snippet…`
using each source's **real Postgres `id`** as the bracket number — not a positional 1..6 index —
and instructs Claude to cite using that same number. This matters mechanically, not just
stylistically: `app/meatcode_mockup.html`'s `streamSSE()` renders the `sources` event's `s.id` as
both the citation-chip label (`[` + s.id + `]`) and the `data-paper-id` used when a chip is
clicked to fetch `GET /api/papers/{id}` for the detail modal — and it parses `[\d+]` markers
inside Claude's own prose the same way (`renderAnswerHTML`). If Claude cited a positional `[1]`
instead of the source's real id, clicking that inline citation would fetch whatever random paper
happens to have `id=1`, silently showing the wrong paper. Using the real id as the citation label
end-to-end means every chip — in the "Sources retrieved" row and inline in the answer — resolves
to the actual cited paper. No mockup changes were needed or made; this was purely a matter of
choosing the right label scheme server-side.

The `sources` SSE payload itself is trimmed to what the mockup actually reads
(`id`/`title`/`year`/`journal`, plus `doi`/`url` for potential future use) — see
`_public_source_fields()`. The fuller `abstract` text stays server-side only, used to build the
grounding prompt via `_format_sources_block()` (truncated to ~500 characters per source).

## Fallback behaviour (never crash, never mislead)

Two distinct failure modes are handled differently on purpose:

- **`DATABASE_URL` unset, or the retrieval query raises** (bad connection, Neon asleep and
  unreachable, `psycopg2` missing, etc.) → `grounded = False`. Behaves exactly like the original
  code: `sources: []`, Claude answers the raw question with the unmodified `SYSTEM_PROMPT`, no
  grounding rules applied. This is deliberate — telling the user "the corpus doesn't cover this"
  would be **false** if the real reason is a transient DB hiccup, not lack of coverage.
- **Retrieval runs cleanly but returns zero rows** (both tiers exhausted) → `grounded = True`
  with an empty source list. Claude gets the full grounding rules plus an explicit "SOURCES:
  (none retrieved…)" block and is instructed to say the MeatCODE corpus doesn't cover this. This
  is the honest case — the DB was queried successfully and genuinely has nothing on-topic for the
  question. After the OR-fallback, this should now be rare (0/14 in the eval set); it's expected
  to still happen for well-formed questions that fall outside the ~319-source on-topic pool
  (see below).

## The on-topic pool is smaller than it looks

Verified live against Neon (2026-07-08): 818 total sources, all 818 have `search_vec` populated
(fully citable), but only **319/818 (39%)** pass `relevance_llm IS NULL OR relevance_llm >= 60` —
the retrieval-quality gate this feature uses. That's a stricter bar than the "202 flagged <40"
quarantine threshold mentioned in `PROJECT_STATE.md` (a different, more lenient cut used for
audit/removal candidates) — 499 sources sit in the 0–59 band that's fine for the corpus generally
but excluded from what the Oracle will retrieve/cite. Worth knowing before reading eval results as
"the Oracle only really has ~319 candidate sources to draw from," not 818.

## Eval harness

`analysis/oracle_eval/eval_questions.md` — 14 natural R&D questions spanning all 5 taxonomy
branches (analytics, flavor_chemistry, flavor_ingredients, meat_analogs, meat_science), phrased
the way a researcher would actually type them (not keyword-stuffed to guarantee hits).

`analysis/oracle_eval/run_eval.py` — runs ONLY the retrieval SQL (both tiers) against live Neon
and prints/saves the top-6 per question. Deliberately does **not** import
`server/meatcode_server.py` (that module hard-`sys.exit`s at import time if `ANTHROPIC_API_KEY`
is missing, and constructs an Anthropic client) and does **not** call the Anthropic API — it is a
standalone duplicate of the retrieval SQL, with a comment in both files pointing at the other so
they get updated together if the query changes. Run it with:

```bash
python3 analysis/oracle_eval/run_eval.py --save analysis/oracle_eval/results.md
```

`analysis/oracle_eval/results.md` — the saved output of the command above (live run, 2026-07-08)
plus a short human relevance read at the top.

## Known limitations / next steps

1. **Per-source precision within a 6-result set.** The OR-fallback trades some precision for
   recall by design — a couple of eval questions pulled in one clearly off-target paper alongside
   5 good ones (e.g. a Baijiu-aroma paper for a myoglobin/heme question, matched on generic
   flavor-chemistry vocabulary). The grounding prompt's "read each abstract, only rely on what
   actually addresses the question" instruction is the current mitigation. A real reranking step
   (decision doc's step 3: "take the ~30 most promising passages and do a quick quality check to
   keep only the best ~6") is the structural fix, and is explicitly "later" per that doc.
2. **Semantic/embedding search is still not built.** Everything here is lexical (Postgres FTS).
   The decision doc's step 2 ("search three complementary ways at once — by meaning, by keywords,
   and narrowed by tags") is the target end-state; this session ships the keyword leg only, which
   is the agreed "this month" scope.
3. **Corpus coverage, not retrieval, is the ceiling for some topics.** Cultivated-meat-specific
   and kokumi-specific questions retrieved only tangentially related sources — consistent with
   `analysis/white_space_data.md` flagging meat_analogs as the thinnest-covered branch. No amount
   of retrieval tuning fixes a genuine content gap; that's Phase 1's literature-collection crux
   (`PROJECT_STATE.md` "Next" #1).
4. **Not yet browser-click-tested end-to-end** (question → real citations → click a chip → modal
   shows the right paper). Verified up through the SSE payload shape and the retrieval SQL live;
   the mockup-side click path was verified by code-reading (`app/meatcode_mockup.html`'s
   `streamSSE`/`attachCiteHandlers`/`openPaperModal`), not by driving a browser.
