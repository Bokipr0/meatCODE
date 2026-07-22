# Data-Audit Loop — recurring source authentication with dynamic prioritization

_Last updated: 2026-07-07 10:35 UTC · Advisory (audit loop) · new design + operating doc (script-first architecture, dynamic-priority selection, every-2-days schedule)_

**Status:** Design of record for the recurring corpus-authentication loop. Ties together two scripts being
built in parallel — the Data Engineer's `pipeline/audit_sources.py` (+ a new `source_audits` table) and the
Algorithm Expert's `pipeline/audit_judge.py` (LLM judge + dynamic prioritization). This doc is the contract
those two must meet so they interoperate, plus the schedule and human-review process around them. Where it
describes those scripts it is specifying intended behaviour, not documenting shipped code.

---

## 1. Purpose & fit

The corpus is the foundation everything downstream stands on — the Oracle only cites what's in `sources`, the
molecular and expert surfaces hang off the same rows, and the white-space map is only as trustworthy as the
tags underneath it. PROJECT_STATE names corpus quality as a live risk in three concrete ways: only ~40% of the
818 sources are tagged in `source_topics` (489 legacy sources were never back-tagged), the LLM relevance gate
flagged **202 sources scoring <40** as keyword-matched-but-off-topic (nutrition/contaminants/health) that no
one has yet confirmed or removed, and the structured evidence layer is thin (45 claims; 784 of 799 molecules
uncategorized). Those aren't one-time cleanups — a corpus that keeps ingesting from Europe PMC / OpenAlex will
keep accreting the same kinds of error. This is exactly the Asana line *"validate source quality / chatbot
quality."*

The loop answers that with a standing discipline rather than a heroic one-off: **every two days, authenticate 20
sources chosen by dynamic priority** — surface each one's stored info, tags and connected claims/queries, judge
its quality and on-topic relevance, and record a verdict. Over a validation year this converts "we scored the
corpus once in July" into "the corpus is continuously re-checked, oldest-and-riskiest first, and every verdict
is logged." The point is not to touch every row constantly; it is to *keep spending the checking budget where
the data is most likely wrong or most valuable*, and to leave an audit trail that is itself a credibility asset
when Daniel or WUR ask "how do you know your sources are good?"

What the loop authenticates, concretely, per source:
- **On-topic relevance** — does this actually concern meaty *process* flavor, or is it a keyword false-positive
  (the 202-source failure mode)? This directly gates whether the Oracle may cite it (`relevance_llm >= 60`).
- **Quality / trust tier** — venue, review-vs-primary, citation signal, whether the abstract supports what the
  row claims. Feeds `priority_score` and the currently-unused `trust_tier` column.
- **Tag correctness & coverage** — are its `source_topics` right, and if it's one of the 489 untagged legacy
  rows, tag it so it stops being invisible to the white-space read.
- **Connectedness integrity** — do its linked claims/molecules actually follow from it (thin layer, high stakes).

---

## 2. Architecture — script-first, LLM-narrow

The senior recommendation is deliberately unglamorous: **a deterministic Python script owns everything except
judgement, and the LLM judges only the 20 rows the script hands it.** Selection, all database reads and writes,
the report, and the audit-trail row are plain, reproducible Python. The model is a narrow subroutine.

```
                    ┌─────────────────────────────────────────────────────────┐
   every 2 days     │  pipeline/audit_sources.py   (deterministic — owns DB IO) │
   scheduled  ─────▶│                                                           │
   session          │  1. SELECT candidate sources + their tags/claims/queries  │
                    │     from Neon (priority_score, relevance_llm, is_review,   │
                    │     source_topics, claims, last audit date)               │
                    │  2. score each by DYNAMIC PRIORITY and take the top 20     │
                    │         │                                                  │
                    │         ▼                                                  │
                    │  ┌──────────────────────────────┐                         │
                    │  │ audit_judge.py               │  ← LLM (Haiku) touches   │
                    │  │  • DEFAULT_WEIGHTS / selection │    ONLY these 20 rows   │
                    │  │  • judge(source) → verdict     │                         │
                    │  │  • update_weights(history)     │                         │
                    │  └──────────────────────────────┘                         │
                    │         │  verdicts (relevance, quality, tags, flag)       │
                    │         ▼                                                  │
                    │  3. WRITE verdicts → source_audits  (append-only trail)    │
                    │     apply SAFE, reversible changes (re-score, add tags)    │
                    │     stage risky ones (quarantine) for human confirm        │
                    │  4. WRITE data/audits/audit_YYYY-MM-DD.md  (dated report)   │
                    └─────────────────────────────────────────────────────────┘
                              │                          │
                              ▼                          ▼
                     source_audits (Neon)        dated markdown report
                     + optional relevance_llm     ── read by the scheduled
                       / priority_score / tag        session → AGENT_UPDATE_LOG
                       / trust_tier updates          + quarantine surfaced to Lior
```

**Why this beats a "constant swarm of agents."** The tempting alternative — keep a fleet of autonomous agents
perpetually crawling the corpus — is the wrong tool for a validation-year budget, for four reasons:

- **Cheaper.** The only paid step is ~20 short Haiku judgements per run (§4). A swarm burns tokens on planning,
  navigation, re-reading state, and re-deciding what to look at every cycle — most of the spend is overhead, not
  judgement.
- **Deterministic & reproducible.** `audit_sources.py --n 20` selects the same 20 given the same DB state, and
  the selection logic is readable Python you can diff, unit-test, and reason about. An agent swarm's behaviour is
  emergent and non-reproducible — you cannot re-run last Tuesday's audit and get last Tuesday's audit.
- **Auditable.** Every verdict lands in `source_audits` with the source id, the scores, the model/prompt version,
  and the timestamp. The trail *is* the product here; a swarm's chain-of-thought is not a durable record.
- **Bounded blast radius.** The script auto-applies only safe, reversible changes and stages the rest for a human.
  A swarm with write access to the corpus is a standing risk of silent, correlated damage (see over-quarantining,
  §6).

This mirrors the pattern already working in the repo: `score_relevance.py` uses Haiku as a narrow batched gate
and `score_priority.py` is fully deterministic. The audit loop is the *recurring, self-focusing* version of that
same shape — not a new paradigm, a scheduled continuation of the one that already earned its place.

The division of labour between the two sibling scripts: `audit_sources.py` is the deterministic harness (DB IO,
selection execution, writes, report, the audit row); `audit_judge.py` is the brain (the `DEFAULT_WEIGHTS` and
selection scoring that rank candidates, the per-source `judge()` call, and `update_weights()` that closes the
feedback loop). Keeping judgement and prioritization in one importable module means the harness stays boring and
the intelligence stays testable in isolation.

---

## 3. Dynamic prioritization — the audit focuses itself

The loop is only worth running if it spends its 20-source budget where it matters. Selection scores every
candidate on three multiplied factors — **importance × staleness × uncertainty** — so a source rises to the top
when it is simultaneously load-bearing, overdue, and doubtful. The framing to hold onto: *the audit concentrates
itself on where the data is most likely wrong, or most costly to have wrong.*

**Importance — how much the platform leans on this row.** Built from signals already in the schema: `priority_score`
(itself 60% LLM relevance + 40% deterministic), `is_review` (reviews are high-leverage entry points), Oracle-
eligibility (`relevance_llm >= 60` means it can actually be cited, so an error is user-visible), taxonomy weight
via `db.taxonomy` (a source tagged to a HIGH-priority branch/topic — using the canonical `BRANCH_ORDER` /
`PRIORITY_ORDER` — matters more than one on a MED topic), and connectedness (a source linked to `claims` /
`molecules`, or one many Oracle queries retrieve, is higher-stakes because its error propagates).

**Staleness — how overdue a re-check is.** Deliberately defined by *audit history, not ingest date* — `sources`
has no `created_at`/`updated_at` column, and the clean definition is anyway "time since we last authenticated
this row" = the newest `audited_at` for that source in `source_audits`, with **never-audited = maximum
staleness**. This is what makes the loop sweep the whole corpus instead of re-poking the same 20: once a source
is audited its staleness resets, so the frontier of unaudited/overdue rows keeps advancing.

**Uncertainty — where our confidence is lowest.** The signals that flag "we might be wrong here": untagged legacy
rows (the 489 with no `source_topics` — we don't even know their topics), borderline relevance near the 60
Oracle cutoff (a wrong call flips whether the Oracle cites it), the 202-source <40 quarantine shortlist (probably
wrong-*in*, needs confirmation before removal), missing `abstract`, un-scored `relevance_llm`, and sources tagged
to the five HIGH-priority topics that currently have zero tagged coverage.

**The feedback loop — findings reweight future selection.** This is the part that makes it *dynamic* rather than
a fixed sort. The Algorithm Expert's `DEFAULT_WEIGHTS` set the starting mix of the three factors; `update_weights()`
nudges that mix from the accumulated `source_audits` verdicts each run. If a slice keeps *passing* (e.g. core
food-chemistry reviews are reliably fine), its selection weight decays so the audit stops wasting budget there.
If a slice keeps *failing* (e.g. a particular provider, `search_query`, or branch keeps surfacing off-topic
rows), its weight rises so the next run concentrates there. The audit thus learns the shape of its own corpus's
error and chases it — with two guards so it doesn't over-focus: a **staleness floor** guarantees every source is
eventually audited regardless of weights, and a small **exploration fraction** (a few randomly-chosen sources per
run) keeps the loop from going blind to a slice it has learned to ignore. (Guards detailed in §6.)

---

## 4. The every-2-days schedule

The loop runs as a **registered scheduled task** (the Cowork scheduling mechanism), which spins up a fresh agent
session on the cadence with a fixed prompt — the exact prompt is in §7, ready for the Coordinator to register.
Two days is the right interval: frequent enough that the whole 818-source corpus gets a first full sweep in
roughly three months (≈20 sources × ~15 runs/month ≈ 300/month) and is then continuously re-swept oldest-first,
but infrequent enough that each run has a meaningful, human-reviewable batch rather than a trickle.

Each scheduled session is short and mechanical: work in `meatCODE/`, run `python3 pipeline/audit_sources.py --n 20`,
read the dated report the script just wrote, append a short `AGENT_UPDATE_LOG.md` entry summarizing the run
(counts + anything quarantined), and surface any quarantine items to Lior. The heavy lifting is in the script;
the session is a thin runner-plus-narrator. It does not edit the corpus by hand and does not make judgement calls
the script didn't — that keeps every run identical in shape and safe to leave unattended.

**Cost profile: trivial.** The only paid work is ~20 Haiku judgements per run, batched the same way
`score_relevance.py` already batches (BATCH=12 → 2 calls of short title+abstract inputs). At Haiku pricing that is
a fraction of a cent per run and on the order of a few cents per month across ~15 runs — genuinely negligible
against the value of a continuously-authenticated corpus. Neon auto-sleep is a non-issue: the first `get_conn()`
query wakes it in a few seconds. If the corpus grows toward the 1,000–2,000 target, the loop scales by bumping
`--n` or tightening the cadence — the cost stays linear and tiny.

---

## 5. Human-in-the-loop

The loop is designed so a human confirms *judgement* and the script handles *bookkeeping* — never the reverse.
Three surfaces carry a run to a person:

**The quarantine queue.** When the judge flags a source as off-topic or low-quality, the script does **not**
delete it. It records the verdict in `source_audits` and stages the source (a quarantine status / flag) awaiting
human confirmation. Deleting a row or de-listing it from the Oracle corpus is always human-gated — this is the
single most important safety property of the design, because a false quarantine silently removes real evidence.

**The dashboard Review Queue tab.** The Streamlit dashboard's existing Review Queue tab is the working surface:
it lists the staged verdicts — quarantine candidates, borderline relevance calls near the 60 cutoff, proposed
re-tags — so Lior can confirm or reject in one place rather than reading SQL. (The dashboard is the intended
review surface per PROJECT_STATE; wiring the audit verdicts into that tab is the Data Engineer's follow-up.)

**The dated reports.** Each run writes `data/audits/audit_YYYY-MM-DD.md` — a skimmable summary (how many audited,
verdict distribution, what got auto-applied, what's waiting) that also feeds the `AGENT_UPDATE_LOG` entry. The
reports accumulate into the human-readable half of the audit trail; `source_audits` is the queryable half.

**What auto-applies vs. what waits.** Auto-applied (safe, reversible, and re-derivable by re-running the scorers):
re-scoring `relevance_llm` / `priority_score`, writing the `source_audits` row, adding high-confidence tags to
untagged rows, and recording/refreshing `trust_tier`. **Human-decided:** confirming or rejecting a quarantine
(keep vs. remove), accepting re-tagging on genuinely ambiguous sources, and acting on *systemic* findings — e.g.
"provider X or query Y keeps surfacing junk, fix the ingest string" is a decision for a person, not an auto-edit.

---

## 6. Roadmap & risks

**How it compounds.** In the validation year this loop turns corpus quality from a snapshot into a trend line.
The 40%-tagged fraction climbs as legacy rows get audited-and-tagged; the 202-source quarantine shortlist gets
worked down from "flagged" to "confirmed removed or confirmed fine"; the Oracle-eligible set (`relevance_llm >= 60`)
becomes something we've *checked*, not just *scored once*; and `source_audits` becomes a provenance record that
directly answers the trust question Daniel and WUR will ask. Because selection is oldest-and-riskiest-first, the
loop also naturally catches *drift* — sources whose relevance we'd judge differently now than at ingest — which a
one-time scoring pass structurally cannot. As the corpus grows toward 1,000–2,000, the same loop scales without
redesign.

**Risks and mitigations.**
- **Judge drift** (Haiku's calls shift over time or across model updates, so verdicts aren't comparable
  run-to-run). Mitigate: version the rubric inside `audit_judge.py` and store the model id + prompt version in
  every `source_audits` row; periodically re-audit a small fixed "gold" set and watch for verdict movement; keep
  human spot-checks in the Review Queue so drift is visible, not silent.
- **Over-quarantining** (an over-harsh judge removes good sources). Mitigate: quarantine is reversible and
  human-gated — the script never auto-deletes; track quarantine precision from human confirm/reject decisions and
  loosen the threshold if false-positives climb; start conservative.
- **Cost creep.** Mitigate: Haiku only, a hard `--n` cap, and batched calls — the script's paid surface is fixed
  per run by construction; monitor via the report's per-run counts.
- **Selection starvation / feedback overfit** (the weights collapse onto one slice and never revisit the rest).
  Mitigate: the staleness floor guarantees eventual coverage of every source; cap how far `update_weights()` can
  move the weights in one step; keep the exploration fraction so no slice goes permanently unseen.
- **Stale local tree / Neon sleep.** Always go through `db.connect.get_conn()` (never hardcode); the first query
  wakes Neon. (Note for the Coordinator: this local repo copy is currently missing `db/connect.py` source and the
  baseline schema SQL — only compiled artifacts remain — so a `git pull` on Lior's Mac before the first scheduled
  run is worth confirming.)

---

## 7. The scheduled-task prompt (ready to register)

Register this as the every-2-days task. It is intentionally prescriptive and self-contained so each unattended
run behaves identically.

```
You are the recurring MeatCODE data-audit session. Work ONLY in the meatCODE repo at
/Users/lior/Documents/Claude/Projects/Claude Database/meatCODE (bash mount under
/sessions/.../mnt/Claude Database/meatCODE).

1. Read CLAUDE.md and PROJECT_STATE.md (top) so you're current, then read
   docs/data_audit_loop.md for what this loop is.
2. Run the audit:
       cd meatCODE
       python3 pipeline/audit_sources.py --n 20
   This selects 20 sources by dynamic priority (importance × staleness × uncertainty),
   has the Haiku judge in pipeline/audit_judge.py authenticate each, writes verdicts to
   the source_audits table, auto-applies only safe reversible changes, and writes a dated
   report to data/audits/audit_<today>.md.
3. Read that dated report. Summarize in 3-5 lines: how many audited, the verdict spread
   (pass / borderline / quarantine), what was auto-applied, and what is staged for review.
4. Append ONE entry to AGENT_UPDATE_LOG.md (newest at top, use the template there,
   timestamp from `date -u`) recording the run and the summary.
5. Surface to Lior anything that needs a human decision — especially quarantine candidates
   (sources the judge flagged as off-topic/low-quality that are staged, NOT deleted). List
   them by id + title + one-line reason, and point him to the Review Queue tab / the dated
   report to confirm or reject. Do not delete or de-list any source yourself.
6. If audit_sources.py fails (e.g. missing table, Neon asleep, no API key), do NOT improvise
   fixes to the corpus — report the error and stop. Neon's first query may need a few seconds
   to wake; a single retry is fine.

Keep it short: run the script, narrate the report, log it, flag what needs a human. The
script does the work; you are the runner and the messenger.
```

---

_Owner: Advisory (strategy/architecture/docs). Depends on: `pipeline/audit_sources.py` + `source_audits`
(Data Engineer) and `pipeline/audit_judge.py` — `DEFAULT_WEIGHTS` / `judge()` / `update_weights()` (Algorithm
Expert). Feeds: the Asana "validate source quality / chatbot quality" task and the corpus-quality risk in
PROJECT_STATE._
