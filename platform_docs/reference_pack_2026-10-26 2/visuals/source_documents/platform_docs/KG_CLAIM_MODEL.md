# MeatCODE Knowledge Graph — The Claim Model

**2026-08-16 · Advisory · Prepared for the working session with Yizhou (AI algorithm expert).**
Purpose: get a critique of the claim model and a recommendation on extraction strategy. Not an approval request.

---

## 1. Thesis

**We are moving the unit of knowledge from the *paper* to the *claim* — because every problem we actually have is invisible at paper resolution.**

A paper is a container. Agreement, disagreement, conditions and confidence live *inside* it. As long as the paper is our atom, we can't compute any of them.

---

## 2. Why reified claims beat flat triplets

**Flat triplet:**
`2-methyl-3-furanthiol —contributes_to→ meaty`

That edge has no author, no conditions, no strength. Worse: a paper that *supports* it and a paper that *refutes* it produce **the same edge**. Disagreement silently disappears into the graph.

**Reified claim** — the claim itself becomes a node, carrying:

| Layer | Contents |
|---|---|
| Assertion | subject · predicate · object |
| Conditions | matrix, pH, temperature, time |
| Measurement | method, value, units |
| Evidence | source, study type, relevance tier |
| Weight | computed confidence |

Now the graph can answer: *who says this, under what conditions, how strongly, and who disagrees.* Agreement, contradiction and confidence become **computable** rather than editorial. Same chemistry, two matrices, opposite results — that's two claims, not one broken edge.

---

## 3. How data is extracted today — honestly

| What | Status |
|---|---|
| LLM facet extraction per paper — pathway, method, matrix, compound_class, sensory_descriptor, study_type, main_claim (~100% filled across 818 sources) | **Automated** |
| Molecule↔paper mining by name matching | **Automated, shallow** (string match, no semantics) |
| MVL chemistry (molecule properties, odour descriptors) | **Curated / hand-assembled** |
| 45 structured claims | **Hand-made** |

So: the *facets* are machine-produced at scale; the *claims* are not. We have 45 hand-made claims and 818 papers. That gap is the whole conversation.

---

## 4. The weight formula, in plain language

```
w = evidence_tier × method_strength × directness × corroboration − contradiction_penalty
```

- **evidence_tier** — how relevant/reliable the source is (our 3-tier literature grade).
- **method_strength** — GC-O/sensory panel outranks a passing mention in a review.
- **directness** — measured in the claim's own system vs. inferred or extrapolated.
- **corroboration** — how many independent sources say the same thing.
- **contradiction_penalty** — subtracted when credible sources disagree.

**This encodes expert priors, not learned parameters.** Deliberate v1 choice: we have no labelled ground truth, so a learned model would be fitting noise. Hand-set priors are inspectable, arguable and correctable by a domain expert — and they give us the scaffolding to collect the labels that would later justify learning.

---

## 5. Where we honestly struggle (verified numbers)

1. **Bridge sparsity.** Only **13% of molecules** and **34% of papers** are connected (712 mined + 23 curated edges). Chemistry and literature are two islands with a thin rope between them.
2. **Odour edges have no context.** The **2,263 molecule→odour edges carry no conditions, no provenance, no weight** — "2-MFT smells meaty" is asserted as if universally true.
3. **One claim per paper.** We store a single `main_claim` where a paper contains 5–20 claims. Consequence: **corroboration currently counts papers, not findings** — which is the wrong denominator.
4. **Identity debt.** **210 molecules** need identity review; **34 duplicate InChIKey groups (70 rows)** not yet merged. Duplicates inflate corroboration and split evidence.
5. **No per-claim conditions.** Matrix/temperature/pH exist at *paper* level, not claim level — so we can't yet say "true in a plant-protein matrix, not in beef."
6. **Live consequence:** the roasted/nutty query returns perfect chemistry and **zero papers**. The demo shows the gap better than any slide.

---

## 6. Three questions for Yizhou

**Q1 — Independence.** Corroboration assumes sources are independent, but our papers cite each other and reuse each other's data. **How should we discount corroboration for citation dependence** — citation-graph damping, author/lab clustering, or something simpler that survives a sparse corpus?

**Q2 — Extraction strategy.** For 818 papers, is it better to run **one LLM pass per paper extracting N claims**, or **targeted extraction per candidate entity pair** (ask only about pairs we care about)? The first is cheaper per unit but noisy and unbounded; the second is precise but scales with pairs, not papers. **Which fails less badly at our size, and what's the recall cost of the targeted route?**

**Q3 — Validation without ground truth.** We have no lab data yet. **What is the cheapest defensible way to evaluate a weight model** — expert pairwise ranking on a held-out sample, retrieval-based proxy metrics, synthetic contradiction injection? We need something a reviewer would accept, not something that merely feels rigorous.

---

## 7. What we're asking for

Not approval — a **critique of the claim model** and a **recommendation on extraction strategy** we can build against next sprint.
