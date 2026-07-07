_Last updated: 2026-07-07 10:56 UTC · Algorithm Expert (audit loop) · how to validate the judge + the dynamic-prioritization math_

# Audit judge — evaluation & prioritization notes

Companion to `pipeline/audit_judge.py` (the LLM judge + dynamic selection) and
`pipeline/audit_sources.py` (the orchestrator). This file explains how we know the
judge is trustworthy, and the reasoning behind the selection math.

## 1. Why the judge needs its own eval

The whole point of the audit loop is to *authenticate* the corpus — so the auditor
itself has to be trusted, or we are just adding a second layer of unverified opinion.
An LLM judge that silently mislabels good sources as `quarantine` (or waves through
off-topic ones as `keep`) is worse than no audit at all, because it manufactures false
confidence. So before the judge's verdicts are allowed to auto-apply anything, we
measure it against a small human-labeled gold set.

## 2. The gold set

Hand-label **30–50 sources** spanning the range: clearly on-topic + rigorous, clearly
off-topic (the nutrition/health/contaminants false-positives already visible in the
corpus), and genuinely borderline. For each, a human records the "true" verdict
(`keep` / `review` / `quarantine`) and, where relevant, the correct tags. Store it as
`analysis/audit_gold.csv` (id, human_verdict, notes). This is a one-time few-hour task
and it is the single highest-leverage thing for trusting the loop.

## 3. Metrics that matter

Run `judge_source` over the gold set and compute, treating **quarantine** as the
positive class (the consequential call):

- **Quarantine precision** — of everything the judge wants to quarantine, how much the
  human agreed. This must be high; a false quarantine removes a good source. Precision
  is why the loop *stages* quarantines for human confirmation rather than deleting.
- **Quarantine recall** — of everything the human quarantined, how much the judge caught.
  Lower recall is tolerable (missed junk just gets re-examined on a later sweep).
- **Verdict agreement (κ)** — Cohen's kappa over the 3-way verdict vs the human, to
  confirm agreement isn't just chance.
- **Tag-issue usefulness** — spot-check that flagged `tag_issues` are real and grounded
  in the abstract, not invented.

Target for go-live: quarantine precision ≥ ~0.9 with sensible κ. If precision is low,
tighten the rubric prompt and raise the score thresholds in `_verdict_from_scores`
before trusting auto-apply. Re-run this eval whenever the judge model or prompt changes
(guards against silent drift).

## 4. Robustness already built in

`judge_source` parses model output defensively and, on any error (bad JSON, missing
key, API failure), returns a safe `review` verdict with a note instead of crashing the
batch — verified in the module self-test. Low temperature keeps verdicts near-stable
across runs. Nothing destructive is ever auto-applied from a single judgement.

## 5. The dynamic-prioritization math (why these 20)

`rank_for_audit` scores each candidate by a weighted blend of three intuitions —
**"check what is most likely wrong, most valuable, or most overdue"**:

- **Importance** — `priority_score`, citation weight, and a boost for thin/high-value
  taxonomy branches (e.g. `meat_analogs`). Getting the platform's load-bearing sources
  right matters most.
- **Staleness** — never-audited or long-since-audited sources rank up (half-life decay
  on time-since-last-audit). This makes the loop *sweep the whole corpus* instead of
  re-poking the same rows; at 20/run every 2 days, ~818 sources are covered in ~3 months,
  then it re-sweeps oldest-first.
- **Uncertainty** — mid-range `relevance_llm` (~40–70) and untagged sources score up,
  because they are where a check is most *informative* (confident-high and confident-low
  rows teach us little).

Weights live in `DEFAULT_WEIGHTS` and are fully tunable.

## 6. The feedback loop (`update_weights`)

After each batch, `update_weights` nudges the weights toward wherever the errors
clustered: if a branch or class produced many quarantines, its weight rises so the next
run probes it harder; a clean branch **decays back toward the default** so no bias sticks
permanently. Two guards keep it healthy: a **staleness floor** (nothing starves, even
low-priority rows eventually get audited) and an **exploration fraction** (a slice of each
batch is sampled outside the current high-priority focus, so the loop can discover new
problem areas instead of tunnel-visioning). Net effect: the audit *learns the shape of
its corpus's errors and chases them*, while staying honest about coverage.
