# Daniel's Audit Review Workflow — MeatCODE

_Last updated: 2026-07-08 10:05 UTC · Advisory · new short operating doc for Daniel's xlsx sign-off loop_

**Status:** Operating procedure, kept short on purpose. **Audience:** Daniel. **What this covers:** exactly
what to check in the audit xlsx, what your three possible calls mean, how they feed back, and the cadence.
See `docs/DECISION_grounded_answers_and_relevance.md` for *why* this loop exists — this doc is just the *how*.

---

## What lands in front of you

Every audit run (currently every 2 days, 20 sources per run, oldest-and-riskiest-first) produces one
spreadsheet: `docs/audits/audit_<date>_<run-id>_sources.xlsx` (e.g. `audit_2026-07-07_86e6ae7e_sources.xlsx`).
Two sheets:
- **Overview** — run date, how many audited, verdict totals (keep / review / quarantine), a column legend.
- **Audited Sources** — one row per source, colour-coded by verdict (green = keep, yellow = review,
  red = quarantine), sorted by how urgent the row is.

## What to check, per row

Work top to bottom (already sorted most-urgent-first). For each row:

1. **Read the Verdict column.**
   - **Quarantine (red)** — the automated judge thinks this source is off-topic or too low quality to be
     citable by the Oracle. Read the "Judge notes" column + the title. Either confirm ("yes, off-topic,
     quarantine it") or reject ("no, keep it — the judge misread this because...").
   - **Review (yellow)** — borderline; the judge isn't confident either way. Same read; your call decides
     it.
   - **Keep (green)** — no action needed by default; spot-check only if something looks obviously wrong.
2. **Check the "Attached tags (source_topics)" column.** If it reads "— none (untagged) —", this is one of
   the legacy sources that predates the taxonomy-tagging pass (roughly 60% of the corpus is currently in
   this state).
3. **Read "Suggested tags / issues (judge)."** This is the judge's proposed fix for #2 — a ready-made list
   of taxonomy tags. If they look right, that's your back-tag decision. If they look wrong or too vague,
   say so instead of rubber-stamping — a bad tag is worse than no tag, since it actively misleads
   tag-aware retrieval later.
4. **Watch for repeat patterns across a run.** If several rows share a cause — e.g. one particular ingest
   search query keeps surfacing off-topic papers — flag that separately. It's a signal to fix the ingest
   query, not just the individual rows it happened to catch this time.

## Your three calls, and what happens to each

| Your call | What it means | What happens next |
|---|---|---|
| **Keep** | Source is on-topic and fine as-is — including overriding a judge "review" or "quarantine" you disagree with | No corpus change. If you're overriding the judge, say why — that disagreement is useful signal for tightening the judge's rubric later. |
| **Quarantine** | Source should stop being citable by the Oracle | Staged, never auto-deleted. **Today this is not yet fully wired end-to-end** — a confirmed quarantine is recorded, but by itself doesn't yet stop the Oracle from retrieving that source (see the write-back gap in `docs/DECISION_grounded_answers_and_relevance.md` §3). Tell Lior explicitly per confirmed quarantine until that's closed. |
| **Back-tag** | An untagged (or wrongly-tagged) source should get the suggested taxonomy tags applied | Independent of keep/quarantine — a kept, on-topic source can still need back-tagging. This is what feeds `source_topics`, which both tag-aware retrieval and the white-space gap map depend on. |

Quarantine and back-tag are **independent axes**, not a single choice — a source can be "keep + back-tag"
(good source, just needs tags) just as easily as "quarantine, no tagging needed."

## Cadence

- Runs automatically every 2 days — 20 sources per run. At that rate the whole corpus gets a first full
  pass roughly every 3 months, then keeps re-checking, oldest-and-riskiest first.
- You don't need same-day turnaround. Batching a review weekly, across 2–3 accumulated xlsx files, is
  fine — nothing gets auto-deleted or auto-suppressed while it waits for you.
- **How to send verdicts back:** by row (source id + your call: keep / quarantine / back-tag + suggested
  tags if applicable), to Lior, who applies them or relays them into the next working session. There is
  no self-serve "click to confirm" UI yet — the dashboard's Review Queue tab is planned for this but not
  wired up yet, so the xlsx plus your reply is the real mechanism today.

## Where this fits in the bigger picture

This is the human checkpoint in the relevance gate: the Oracle only cites sources that are both citable
and score `relevance_llm >= 60`. Your sign-off is what keeps that gate calibrated over time instead of
drifting on an unsupervised LLM's say-so — it's the difference between "an AI scored our sources" and "an
AI scored our sources, and a domain expert checks its work."

---

_Owner: Advisory. See also: `docs/data_audit_loop.md` (mechanics of how sources get selected + judged each
run), `docs/DECISION_grounded_answers_and_relevance.md` (why this loop exists, and how it connects to what
the Oracle is allowed to cite)._
