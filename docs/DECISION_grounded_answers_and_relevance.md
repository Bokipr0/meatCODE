# How Grounding + Relevance Fit Together — MeatCODE Oracle

_Last updated: 2026-07-08 10:05 UTC · Advisory · new decision doc tying the grounded-answer contract to the relevance/audit gate_

**Status:** Decision / design of record. **Audience:** Daniel + Lior — no technical background needed.
**Ties together:** `docs/DECISION_Oracle_Answer_Engine.docx` (the Oracle's retrieval design, 2026-06-30),
`docs/data_audit_loop.md` (the recurring relevance-QA loop), `docs/tagging_relational_guide.md` (the
concrete retrieval SQL being wired right now). This doc doesn't replace any of those — it's the piece
that says how they must fit together, and states the one rule that makes the whole thing trustworthy.

---

## In one sentence

The Oracle is only allowed to speak from what's in our own verified library — and the audit loop plus
Daniel's sign-off is what keeps that library trustworthy enough to speak from. Grounding without a
relevance gate is just confident citation of garbage; a relevance gate without grounding never reaches
the user. Neither half works alone.

## Why this doc exists

Two things are being built in parallel right now. The Algorithm Expert is wiring `/api/ask` to actually
retrieve from the corpus (`sources.search_vec`) instead of answering from Claude's general training —
today it does not retrieve anything at all (see §1). The Data Engineer is checking whether the corpus
itself deserves to be retrieved from — verifying sources against the taxonomy bible and refreshing the
xlsx Daniel reviews. Neither is complete without the other. This is the contract that ties them together
in plain language, so Daniel can see the whole shape of "how do we know the Oracle isn't making things up."

---

## 1. The grounding contract — what the Oracle is and isn't allowed to do

Plain statement:
- The Oracle answers **ONLY** using passages it retrieved from our own closed corpus (the `sources`
  table) for that specific question.
- Every answer **must show which sources it used** (citations back to real papers).
- If nothing in the corpus is relevant enough, the Oracle **says so** — "the corpus doesn't cover this"
  — rather than quietly filling the gap from Claude's general/open-web training knowledge.
- This is a structural rule, not a style preference: the retrieval step + system prompt must make it
  true by construction (only the retrieved passages are ever put in front of the model), not just ask
  the model nicely to behave.

**Why this matters, in the deck's language:** this is the project's front-line mitigation for the
"AI reliability / hallucination" risk that comes up in every stakeholder conversation about an AI
research tool. A flavor scientist's or WUR reviewer's first question about any AI tool is "how do I know
it's not making this up?" The defensible answer is **provenance**: every claim traces to a specific paper
we chose to trust, and you can click through and read it yourself. That converts "trust the AI" into
"trust our library, then click the citation" — a much easier ask for expert audiences who will actively
try to break a system that leans on model output alone.

**Where this comes from:** this restates — does not replace — the architecture already agreed in
`docs/DECISION_Oracle_Answer_Engine.docx` (2026-06-30): "one smart librarian," four steps — understand
the question → find the best passages (keyword + meaning + tag search combined) → pick the top few via a
quality check → write the answer from only those passages, with references, saying "the evidence doesn't
cover this" when it doesn't. **This doc adds the piece that one didn't fully spell out: which passages are
even eligible to be found in step 2 — that's the relevance gate, §2.**

**Which phase we're actually in today:** the Oracle roadmap is phased — keyword RAG → pgvector (semantic)
hybrid → streaming UI → auth/feedback (per `CLAUDE.md`). What's being wired right now is **phase 1,
keyword-only**: full-text search over `sources.search_vec` (a `tsvector` column, live since migration
`0001`), not yet the "meaning-based" semantic search the Answer Engine decision describes as the fuller
picture. That's a deliberate, correctly-sequenced narrowing, not a missed step — but it means today's
grounded answers are only as good as literal keyword overlap, which is itself a documented weak spot (see
Open risks).

**Current status — be honest about this, Daniel will ask:** as of this writing, `POST /api/ask` in
`server/meatcode_server.py` sends an **empty** sources list and streams a raw Claude answer with **zero
corpus grounding**. The Algorithm Expert is wiring the retrieval step right now, following the recipes in
`docs/tagging_relational_guide.md`. Until that lands and is verified, the live Oracle demo should not be
represented externally as citing our corpus.

---

## 2. The relevance gate — what's even allowed to be retrieved

Plain statement: not every row in the database is fair game for the Oracle to cite. A source has to clear
**two independent bars** before it's eligible:

1. **Citable** — we can actually search inside it: it has an abstract and a populated `search_vec`
   (the searchable-text index, auto-filled by a database trigger at ingest). ~818 sources today.
2. **Relevant** — an LLM (Haiku) scored it 0–100 at ingest time for "does this genuinely concern meaty
   *process* flavor," and it scored **`relevance_llm >= 60`**. Below that, it's treated as a keyword false
   positive — usually a paper that matched on a word like "meat" or "protein" but is actually about
   nutrition, contaminants, health claims, or some other unrelated angle. **202 of the 818 sources
   currently score below 40** — large enough to be a named risk, not a rounding error.

**The rule the Oracle enforces, concretely: retrieve only sources that are citable AND
`relevance_llm >= 60`.** That's literally the `WHERE` clause in the retrieval query being wired
(`s.search_vec @@ query AND s.relevance_llm >= 60`, per `docs/tagging_relational_guide.md` §3.1). Anything
scoring lower is invisible to the Oracle — not deleted, just never offered as a citation candidate.

Where does that gate value come from, and why should anyone trust it? Not a one-time guess — a whole loop
keeps it honest:

- **The taxonomy bible** (`db/taxonomy/keywords_topics.json` — 91 keywords across 5 branches: analytics,
  flavor_chemistry, flavor_ingredients, meat_analogs, meat_science) is the single source of truth for what
  "on-topic" even means. It drives what gets ingested and what a source gets tagged as.
- **`relevance_llm` scoring** (`pipeline/score_relevance.py`) reads each source's title/abstract and scores
  it against that taxonomy's *intent*, not just keyword overlap — this is what catches the false positives
  a pure keyword match would let through.
- **The recurring audit loop** (every 2 days, `docs/data_audit_loop.md`) re-checks a rotating sample of 20
  sources, oldest-and-riskiest-first, with a second independent LLM judgement — and it has already caught
  real disagreement with the stored gate (e.g., source #308 scored 72 `relevance_llm` at ingest but only 28
  on re-audit). That's the loop doing its job: catching drift and gate errors after the fact, not just once
  at ingest.
- **Daniel's human sign-off** on the audit xlsx is the last check before anything is trusted long-term —
  see `docs/daniel_review_workflow.md`.

---

## 3. How they connect — garbage-in, garbage-cited

The sentence to hold onto: **grounding is only as trustworthy as the gate that decides what's groundable.**
A perfect retrieval pipeline pointed at an unverified corpus doesn't produce a trustworthy Oracle — it
produces a very confident, well-cited *wrong* answer. So the two workstreams are not parallel-and-independent;
they are one pipe:

```
taxonomy bible (keywords_topics.json)
        |  defines "on-topic"
        v
ingest + relevance_llm scoring        (score_relevance.py, Haiku, 0-100)
        |  sets the initial gate value
        v
recurring audit loop                  (every 2 days, 20 sources, dynamic priority)
        |  independent re-judgement: tag / relevance / quality -> keep | review | quarantine
        v
Daniel's xlsx sign-off                (pipeline/export_audit_xlsx.py)
        |  human confirms: keep / quarantine / back-tag
        v
corpus gets corrected                 (tags added, bad rows flagged)
        |
        v
Oracle retrieval gate                 (search_vec populated AND relevance_llm >= 60)
        |  only citable+relevant rows are ever offered as citation candidates
        v
grounded, cited answer — or an honest "the corpus doesn't cover this"
```

**The gap this surfaces — worth Daniel and Lior both knowing about explicitly:** today, a confirmed
quarantine is written **only** to `source_audits`. It does **not** yet change `sources.relevance_llm` or
otherwise suppress that source from the Oracle's retrieval query, because the retrieval `WHERE` clause
checks `sources.relevance_llm` directly and never looks at `source_audits`. So right now, a source Daniel
has explicitly rejected could still be retrieved and cited — until someone also lowers its `relevance_llm`
(or the retrieval query is changed to also exclude confirmed quarantines). This reads like a one-line fix,
but it is the actual joint between the two workstreams, and it should close before the grounded Oracle goes
in front of anyone external. See Open risks.

---

## 4. Open risks + what's needed for WUR-grade credibility

Framed as: what would a skeptical outside reviewer (WUR, a flavor-house R&D lead, a GFI funder) actually
check if they wanted to poke holes in this?

- **Citable-corpus size is unpublished.** ~818 sources total, but the Oracle's real citable set is only
  those that clear *both* bars (search_vec populated AND `relevance_llm >= 60`) — that count hasn't been
  run since the corpus grew to 818 (PROJECT_STATE's "retrievability check" is still an open item). Until
  it is, we don't actually know how big the Oracle's real library is. **Needed:** run the count, publish
  the number here and in PROJECT_STATE.
- **Tagged % is low.** Only ~40% of sources carry taxonomy tags (`source_topics`); the other ~489 legacy
  rows are invisible to tag-aware retrieval and to the white-space gap analysis. Back-tagging is the
  single highest-leverage cleanup — it also reduces audit churn, since "untagged" is itself an uncertainty
  signal that keeps re-selecting the same rows every audit cycle.
- **The 202-source off-topic shortlist is still just a shortlist.** These already sit below the 60 cutoff
  (so the Oracle can't cite them today), but none have been individually confirmed removed or reinstated.
  Until triaged, they inflate "corpus size" without adding real coverage.
- **The quarantine → `relevance_llm` write-back gap** (§3) — should close before any external demo asserts
  "we quarantine bad sources," since today that quarantine doesn't yet block retrieval on its own.
- **No end-to-end retrieval eval exists yet.** `docs/tagging_relational_guide.md` §3.3 proposes a gold set
  (~15–25 hand-labeled real questions with known-correct sources) to measure precision/recall of the new
  retrieval step before it's trusted as the default path. This hasn't been built. Recommend it exists
  before the grounded Oracle is shown to WUR or any external reviewer.
- **The audit judge itself is unvalidated against humans.** `analysis/audit_gold.csv` (30–50 hand-labeled
  sources, to measure the judge's own quarantine precision) is still an open item. Until it exists, we
  don't have a number for "how often is the automated judge right" — exactly the question a rigorous
  outside reviewer will ask, and exactly the kind of number that makes "we have a review process" a
  credible claim instead of a hopeful one.
- **Keyword-only retrieval today (§1).** Literal keyword overlap misses paraphrased or synonym-only
  matches (e.g., a question about "beany off-notes" won't find a paper that only says "hexanal in pea
  protein" if the words never overlap). This is a known, already-scheduled next phase (pgvector semantic
  search), not a surprise — but worth naming so early demo limitations are framed as "phase 1 of a known
  plan," not an unadvertised gap.

---

_Owner: Advisory (strategy/architecture/docs). Depends on / ties to: `docs/DECISION_Oracle_Answer_Engine.docx`
(retrieval design, Lior/Daniel), `docs/data_audit_loop.md` (audit loop design, Advisory), `docs/tagging_relational_guide.md`
(retrieval SQL, Algorithm Expert), `docs/daniel_review_workflow.md` (the human sign-off loop). Feeds:
the Asana "validate source quality / chatbot quality" task and the corpus-quality risk in `PROJECT_STATE.md`._
