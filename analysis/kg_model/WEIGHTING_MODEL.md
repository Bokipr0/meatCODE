# MeatCODE claim weighting model — v0.1 specification

_2026-08-16 · Algorithm Expert · reference implementation: `analysis/kg_model/score_claims.py` (stdlib only, runnable)._
_Consumes the reified-claim schema proposed in `analysis/rag_eval/CLAIM_LAYER_NOTES.md`._

**Status: designed and implemented, not yet fitted.** Every constant below is an expert prior, not a
learned parameter. The value of the model right now is that it makes the priors explicit, auditable and
tunable — not that it is calibrated. Read §6 before believing any number.

---

## 1. The formula

For a single reified claim *k* on edge `(subject, axis, object)`:

```
b_k = tier(k) · method(k) · directness(k)                # base credibility, (0,1]
c_E = (1 + ln n_eff(E)) / (1 + ln N_sat)                 # corroboration of its consensus cluster E, capped at 1
p_k = λ · W_opp(k) / (W_opp(k) + b_k)                    # contradiction penalty, [0, λ]
w_k = clamp( b_k · c_E − p_k , 0, 1 )
```

where `W_opp(k)` is the summed **base** credibility of claims that genuinely contradict *k* (§5), and
`n_eff` is the independence-discounted source count of *k*'s cluster (§4).

### Why multiplicative on the first three factors
`tier`, `method`, `directness` are **conjunctive necessary conditions**. A claim needs all three to be
credible: a T1 experimental paper that only did peak identification in the wrong matrix is not
"two-thirds credible", it is weak. Multiplication encodes *any one factor near zero kills the claim*,
which is the behaviour we want; addition would let a strong tier compensate for an irrelevant matrix.

### Where multiplicative is wrong — say this out loud
1. **It double-counts correlated factors.** `tier=T1_experimental` and `method=gco_aeda_quant` are not
   independent — experimental papers are the ones that run GC-O. Multiplying them squares the same
   underlying "this was really measured" signal, which over-separates the top of the ranking.
   A logistic/log-linear form `w = σ(Σ βᵢ xᵢ)` with fitted βᵢ would absorb that correlation. We can't fit
   it yet (no labels), so we accept the bias and record it.
2. **It has no floor for irreducible evidence.** Three mediocre factors give `0.45·0.5·0.55 = 0.12` —
   arguably too harsh for a claim that is nonetheless the only thing known about a compound.
3. **The 0–1 scale is ordinal, not probabilistic.** `w=0.8` is *not* "80% likely true". It is a ranking
   score. Any UI copy that implies probability is a lie; label it "evidence strength", never "confidence".

### Normalisation to 0–1
Each factor table is defined with max = 1.00, so `b ∈ (0,1]` by construction. `c` is divided by its value
at saturation `N_sat` and capped, so `c ∈ (0,1]`. The penalty is bounded by λ. The final clamp is a
safety net, not the main mechanism — the components are already bounded.

---

## 2. Corroboration: why `1 + ln n`, not `n`

Linear `n` makes evidence volume the dominant term: 20 mediocre abstracts beat 2 excellent GC-O studies.
That is exactly the failure the flat `ts_rank_cd` baseline already has.

Log has the right marginal shape:

| n independent sources | 1 + ln n | c (N_sat = 10) |
|---|---|---|
| 1 | 1.00 | 0.303 |
| 2 | 1.69 | 0.512 |
| 3 | 2.10 | 0.635 |
| 5 | 2.61 | 0.790 |
| 10 | 3.30 | 1.000 (cap) |
| 30 | 4.40 | 1.000 (cap) |

The 2nd independent replication roughly doubles the corroboration term; the 12th adds nothing. The cap at
`N_sat` is deliberate: past ~10 independent confirmations the bottleneck is no longer "is it true", it is
"under what conditions" — so extra papers should go to condition resolution, not weight.

### The assumption that breaks: independence

`ln n` is only defensible if the *n* sources are independent evidence. **They usually are not.** Three
papers from the same lab, or three reviews all citing the same 1998 primary study, are one observation
wearing three hats. Counting them as n=3 inflates `c` by ~2× over the true n=1.

**What is implemented now (a stub, honestly labelled).** Each triplet carries `source_group`. Effective
count is

```
n_eff = Σ_g [ 1 + β · (k_g − 1) ]        β = 0.35 by default
```

so the first source in a group counts fully and each additional one counts 0.35. In the sample corpus,
`grp_B` contributes two sources → `n_eff = 1 + 1.35 = 2.35` for that pair, not 3.

**How I would discount correlated sources properly** (in priority order, all deferrable past MVP):
1. **Citation-graph clique discount.** Build the citation DAG over the 818 sources (Dimensions gives
   references). If A cites B, A's claim is partly derivative of B's. Discount by
   `1 − ρ · (shared-ancestor overlap)` using a Jaccard on reference sets.
2. **Author/affiliation blocking.** Sources sharing ≥1 author or the same lab collapse into one group —
   this is `source_group` populated automatically instead of by hand.
3. **Review demotion.** A T2 review whose claim traces to primary sources already in the cluster
   contributes ~0 new corroboration; it should raise *coverage* not *weight*.
4. **Proper form:** replace the count with the effective sample size of a correlated-observation model,
   `n_eff = n / (1 + (n−1)·ρ̄)` where `ρ̄` is mean pairwise correlation estimated from the citation graph.
   This is the principled version; the β-stub is its crude special case.

---

## 3. Value tables (expert priors — v0.1, unfitted)

**Evidence tier** — from `CLAIM_LAYER_NOTES.md` §3a, extended with T4.

| tier | value | meaning |
|---|---|---|
| `T1_experimental` | 1.00 | the linked source measured it directly |
| `T2_review` | 0.75 | asserted in a review; primary data one hop away |
| `T3_inferred` | 0.45 | model-extracted from abstract, unreviewed (all 45 legacy rows) |
| `T4_conjecture` | 0.25 | discussion-section hypothesis |
| *missing* | 0.45 | defaults to T3 — matches the current corpus |

**Method strength** — what the measurement can actually establish.

| method | value | rationale |
|---|---|---|
| `gco_aeda_quant` | 1.00 | olfactometry + quantification + OAV: links chemistry to perception |
| `gcms_quantified` | 0.90 | calibrated concentration, but no perceptual link |
| `sensory_trained` | 0.85 | trained panel, n≥8, replicated |
| `gcms_identification` | 0.70 | peak identified only; presence ≠ contribution |
| `model_system` | 0.65 | buffer/model reaction, not a food matrix |
| `consumer_panel` | 0.60 | hedonic, high variance, no mechanism |
| `in_silico` | 0.40 | QSAR / prediction, no measurement |
| `unspecified` | 0.50 | not stated in abstract — the common case today |

**Directness** — distance between what was measured and what the claim asserts.

| directness | value | meaning |
|---|---|---|
| `target_matrix` | 1.00 | measured in the matrix the claim is about |
| `analogous_matrix` | 0.75 | beef claim measured in pork; pea claim in soy |
| `model_system` | 0.60 | measured in a model reaction system |
| `extrapolated` | 0.45 | cross-species / cross-domain inference |
| `unknown` | **0.55** | **a guess** — conditionless claims land here (§6.5) |

---

## 4. Consensus clustering

Claims aggregate into an edge weight in three steps.

1. **Cluster key = `(subject, axis, object, polarity, condition_bucket)`.** Condition bucket is the
   matrix today (`cooked_beef`, `pea_protein_isolate`, …), `any_matrix` when absent. Crucially, claims
   about the *same* relation under *different* conditions form **separate clusters** — the graph carries
   conditioned parallel edges, not one averaged edge. This is what stops "hexanal in pea" and
   "hexanal in soy" being mashed into a meaningless mean.
2. **Corroboration is computed per cluster**, from the independence-discounted source count, and applied
   to every member claim.
3. **Edge weight = noisy-OR** over the member weights, minus the noisy-OR of the opposing cluster:

   ```
   S = 1 − Π(1 − w_k)   over supporting claims
   O = 1 − Π(1 − w_k)   over opposing claims
   edge_weight = max(0, S − O)
   ```

   Noisy-OR, not mean: three independent weak-ish claims *should* aggregate to something stronger than
   any one of them, while a single strong claim is not diluted by weak company (a mean would punish it).
   Noisy-OR assumes conditional independence given the edge — the same assumption already discounted in
   `n_eff`, applied twice, which is a known conservatism/inconsistency to clean up in v0.2.

---

## 5. Contradiction detection rules

Run pairwise inside each `(subject, axis, object)` group. Two claims conflict if **either**:

- **R1 — polarity opposition.** Same subject + object + axis, opposite `polarity` (`+` vs `−`).
  "Hexanal increases green off-note" vs "hexanal decreases green off-note".
- **R2 — non-overlapping measurement intervals.** Same `quantity` and `unit`, and the reported
  `[low, high]` ranges are disjoint after a ±10 % slack (`interval_slack`, absorbs rounding and
  units-of-last-place). Sample: OAV `[120,180]` vs `[5,12]` — same direction, incompatible magnitude.

**R3 — the condition-mismatch guard (the one that matters most).** Before a conflict is recorded as a
contradiction, the two claims must be *comparable*. They are **not** comparable — and the conflict is
reclassified as a `condition_divergence` — if any of:

| test | default tolerance | reason |
|---|---|---|
| `matrix` differs and both are stated | exact match required | pea ≠ soy ≠ beef; different chemistry, not disagreement |
| \|ΔT\| between stated temperatures | > 20 °C | Maillard product distribution is strongly temperature-dependent |
| \|ΔpH\| | > 1.0 | pH switches furanthiol/pyrazine pathways |

A `condition_divergence` carries **zero penalty**. It is treated as information: it *splits the edge*
into two conditioned edges, which is the correct KG representation and, in the UI, the most interesting
thing on the page ("these disagree because they are not the same experiment").

This asymmetry is deliberate: false contradictions are more damaging than missed ones. A false
contradiction suppresses true evidence and makes the Oracle hedge; a missed one merely leaves an
over-confident edge that further papers will correct.

**Penalty.** Only comparable conflicts penalise:
`p_k = λ · W_opp / (W_opp + b_k)` with λ = 0.35. Because the mass is credibility-weighted, a T3/in-silico
contradictor barely dents a T1/GC-O claim (sample: S4 knocks S1 from 0.635 to 0.470), while a symmetric
T1-vs-T1 conflict halves both. Both sides are penalised — the model refuses to pick a winner, which is
correct: an unresolved contradiction means we don't know.

---

## 6. Retrieval impact

**Baseline (today, measured 2026-08-15, `analysis/rag_eval/results_2026-08-15.md`):** flat
`ts_rank_cd` over `sources.search_vec`, gated `relevance_llm >= 60`, top-6, OR fallback fired on 8/8
questions. Scores: **groundedness 3.4 · citation accuracy 4.8 · coverage 4.1** (of 10).

The eval criticisms are unambiguous about *why*: the retrieved documents are topically adjacent but do
not contain the specific assertions the answer makes (Q1: source [205] is braised **pork**, cited for a
beef claim; Q3/Q4: near-total ungroundedness). This is a **granularity** failure, not a lexical-matching
failure — the unit of retrieval (whole abstract) is coarser than the unit of the answer (one assertion).
Weighted claims attack exactly that.

Three concrete changes:

1. **Claim-level scoring (unit change).** Retrieve over claims, not sources:
   `score = ts_rank_cd(claim.search_vec, q) · (0.5 + 0.5·w_k)`, then resolve each claim to its
   `claim_sources` for citation. The citation now points at the sentence that supports the assertion,
   which is precisely what citation-accuracy measures.
2. **Entity-anchored expansion.** Link the question to KG entities (`molecules.name` /
   `normalized_axis`), walk 1 hop along edges ordered by `edge_weight`, and pull the top-m claims per
   edge. Q1's failure was that MFT chemistry exists in the corpus but was not retrieved by keyword —
   graph expansion from the entity "cooked beef aroma" reaches it; bag-of-words did not.
3. **Weight as a re-ranking multiplier (cheapest, ship first).** Keep the current source retrieval, take
   top-30 instead of top-6, and re-rank by `ts_rank_cd · (1 + γ·max_claim_weight(source))`, γ ≈ 0.5.
   No schema change, no new index; just a re-sort. Also lets the answer prompt receive an explicit
   "evidence strength" annotation per source so the model can hedge proportionately.

**Expected movement, stated as a falsifiable prediction on the same 8 questions.** These are estimates
with a defended mechanism, not measurements:

| metric | baseline | expected | mechanism | confidence |
|---|---|---|---|---|
| citation accuracy | 4.8 | **7.0–8.0** | citation resolves to the claim's own source, so the wrong-matrix mis-citation class (Q1 [205], Q1 [99]) is structurally eliminated | high — mechanical, not model-dependent |
| groundedness | 3.4 | **5.0–6.0** | claim text in-context is assertion-shaped, so the model has something to copy instead of recall; but if the corpus genuinely lacks the chemistry (Q3/Q4), retrieval cannot invent it | medium |
| coverage | 4.1 | **5.0–6.5** | graph expansion surfaces the ignored-but-relevant sources the eval flagged ([79],[78],[74],[699]) | medium |

**Honest ceiling:** with 45 claims over 818 sources, claim coverage is ~5 %. Until extraction runs at
scale, change (3) is the only one that can move the numbers, and it will move them modestly. The eval
harness (`analysis/rag_eval/run_eval.py`) already exists, so this is measurable in one run — that is the
proof, and it should be run before any of these numbers are quoted to a stakeholder.

---

## 7. Failure modes (candid)

1. **Rich-get-richer.** `c` is monotone increasing in `n`, so well-studied compounds (MFT, hexanal)
   dominate ranking permanently and novel chemistry — exactly what a *white-space discovery* product
   exists to surface — is buried. The weight model and the discovery mission are in direct tension.
   *Mitigation, not implemented:* a separate `novelty` score (inverse corpus frequency × recency) shown
   as a second axis, and a "low-evidence frontier" view. Never fold novelty into `w` — that would make
   `w` mean two things at once.
2. **Corroboration counts papers, not findings.** Extraction currently emits ~1 claim per paper, so a
   paper reporting 12 compounds contributes one claim; and one finding restated across a paper's abstract
   and its review contributes two. `n` is a proxy for independent findings and a biased one.
3. **Tier/method/directness values are expert priors, not learned.** No labelled set exists. They were
   chosen to be ordinally defensible; their *spacing* (is T2 really 0.75 and not 0.6?) is arbitrary, and
   spacing is what determines ranking near ties. Fitting requires ~200 human-judged claim pairs.
4. **No independence model.** §2's β-stub is a placeholder; `source_group` is not populated by any
   pipeline today. Until the citation graph is wired in, corroboration is systematically over-stated for
   any topic with a dominant lab.
5. **Conditionless edges get a guessed directness (0.55).** Most legacy claims have no conditions, so
   most of the graph runs on a made-up constant. Worse, 0.55 sits *above* `extrapolated` (0.45), so a
   claim that hides its conditions currently scores better than one that honestly declares a weak match —
   a perverse incentive. This should probably be lowered to ~0.45 pending data.
6. **Contradiction penalty is symmetric and unresolved.** Both sides get penalised, so a settled dispute
   where the field has moved on still depresses the winner's weight. No recency term, no retraction
   handling.
7. **Edge weight is clamped at 0.** An edge with only *opposing* evidence (sample: hexanal/soy) prints
   `edge_weight 0.000` and is indistinguishable from "no evidence". Edge weight should be **signed**;
   this is a v0.2 fix, visible in the run output below.
8. **Extraction error is unmodelled.** `w` conditions on the triplet being a faithful reading of the
   paper. LLM extraction from abstracts is maybe 80–90 % faithful; that error is not in the formula, and
   it is probably larger than the difference between adjacent tier values.

---

## 8. Tunable parameters

| parameter | default | range | what moving it does |
|---|---|---|---|
| `n_saturation` (N_sat) | 10 | 3–50 | Corroboration cap. Lower ⇒ few sources already max out, quality (`b`) dominates ranking. Higher ⇒ volume keeps mattering, favours well-studied compounds. |
| `beta_dependence` (β) | 0.35 | 0–1 | Credit for extra sources within one group/lab. 0 = fully dependent (one lab counts once); 1 = disables the independence discount entirely. |
| `lambda_contra` (λ) | 0.35 | 0–1 | Maximum weight subtractable by contradiction. 0 = ignore disagreement; ≥0.6 ⇒ any disputed claim drops out of top-k, i.e. the Oracle only ever cites uncontested findings. |
| `temp_tol_c` | 20 °C | 5–50 | Above this ΔT, a conflict is a condition divergence, not a contradiction. Lower ⇒ more edge splits, more "it depends" answers. Higher ⇒ more false contradictions. |
| `ph_tol` | 1.0 | 0.3–2.0 | Same, for pH. |
| `interval_slack` | 0.10 | 0–0.5 | Fractional slack before two measurement ranges count as disjoint. Higher ⇒ fewer numeric contradictions (tolerant of unit/rounding noise). |
| `EVIDENCE_TIER[*]` | see §3 | 0–1 | Ordinal spacing between tiers. The single highest-leverage table: it sets how much a reviewed claim beats a machine-extracted one. |
| `METHOD_STRENGTH[*]` | see §3 | 0–1 | How much analytical rigour buys. Raising `unspecified` (0.50) is the fastest way to stop penalising the 90 % of abstracts that never state a method. |
| `DIRECTNESS['unknown']` | 0.55 | 0.2–0.8 | The guess for conditionless claims. Governs how much of the legacy graph is trusted. See failure mode 5. |
| `gamma` (retrieval re-rank) | 0.5 | 0–2 | Strength of the weight multiplier in re-ranking. 0 = current flat behaviour (the A/B control). |

All of `n_saturation`, `beta_dependence`, `lambda_contra`, `temp_tol_c`, `ph_tol`, `interval_slack` are
settable at the CLI: `python3 score_claims.py --params lambda_contra=0.6 n_saturation=5`.

---

## 9. Run output

### 9a. LIVE — `pipeline/out/claim_triplets_v1.json`, 5041 triplets (2026-08-16)

The Data Engineer's Layer-C export landed mid-session; the script normalises it (`normalise()`) and
scores the full corpus in **0.09 s**, stdlib only.

```
$ python3 analysis/kg_model/score_claims.py --top 12
source: LIVE  pipeline/out/claim_triplets_v1.json  (5041 triplets)

[0] CORPUS SUMMARY
  claims scored      : 5041   distinct edges: 4857
  weight  min/med/max: 0.017 / 0.052 / 0.669    p90 0.204
  contradictions     : 0      condition divergences: 0
  tier mix           : T1_experimental=2173  T2_review=335  T3_inferred=2519  T4_conjecture=14
  vs stored `weight` (first 400): mean |diff| 0.011  (stored mean 0.027, recomputed mean 0.037)

[1] RANKED CLAIMS (top 12 of 5041)
claim                             edge                                    pol  tier  meth   dir   base  n_eff   corr    pen      W
C-src-203-181-lipid oxidation     hexanal -[formed_by]-> Lipid oxidation   +   1.00  1.00  0.75  0.750   7.00  0.892  0.000  0.669
C-src-174-362-lipid oxidation     nonanal -[formed_by]-> Lipid oxidation   +   1.00  1.00  0.75  0.750   7.00  0.892  0.000  0.669
C-src-203-750-lipid oxidation     1-octen-3-ol -[formed_by]-> Lipid oxid.  +   1.00  1.00  0.75  0.750   6.00  0.845  0.000  0.634
C-src-160-181-lipid oxidation     hexanal -[formed_by]-> Lipid oxidation   +   1.00  1.00  0.75  0.750   6.00  0.845  0.000  0.634
C-src-864-181-lipid oxidation     hexanal -[formed_by]-> Lipid oxidation   +   1.00  0.90  0.75  0.675   7.00  0.892  0.000  0.602
C-src-864-437-lipid oxidation     octanal -[formed_by]-> Lipid oxidation   +   1.00  0.90  0.75  0.675   7.00  0.892  0.000  0.602
C-src-864-750-lipid oxidation     1-octen-3-ol -[formed_by]-> Lipid oxid.  +   1.00  0.90  0.75  0.675   6.00  0.845  0.000  0.571
C-src-160-750-lipid oxidation     1-octen-3-ol -[formed_by]-> Lipid oxid.  +   1.00  1.00  0.75  0.750   4.00  0.723  0.000  0.542
C-src-200-181-maillard reaction   hexanal -[formed_by]-> Maillard reaction +   1.00  1.00  0.75  0.750   4.00  0.723  0.000  0.542
C-src-219-181-thermal degradation hexanal -[formed_by]-> Thermal degrad.   +   1.00  1.00  0.75  0.750   4.00  0.723  0.000  0.542
C-src-219-362-thermal degradation nonanal -[formed_by]-> Thermal degrad.   +   1.00  1.00  0.75  0.750   4.00  0.723  0.000  0.542
C-src-264-181-lipid oxidation     hexanal -[formed_by]-> Lipid oxidation   +   1.00  0.85  0.75  0.637   6.00  0.845  0.000  0.539

[2] CONTRADICTIONS — 0
[3] CONDITION DIVERGENCES — 0

[4] CONSENSUS EDGES (noisy-OR, per condition bucket) — top 12 of 4857
edge                                           matrix                     n+   n-    supp     opp   EDGE_W
hexanal -[formed_by]-> Lipid oxidation         Steak / whole cut           7    0   0.993   0.000    0.993
nonanal -[formed_by]-> Lipid oxidation         Steak / whole cut           7    0   0.991   0.000    0.991
octanal -[formed_by]-> Lipid oxidation         Steak / whole cut           7    0   0.989   0.000    0.989
1-octen-3-ol -[formed_by]-> Lipid oxidation    Steak / whole cut           6    0   0.985   0.000    0.985
hexanal -[formed_by]-> Lipid oxidation         Pork analogue               6    0   0.980   0.000    0.980
linalool -[formed_by]-> Fermentation           any_matrix                  7    0   0.968   0.000    0.968
Acetate -[formed_by]-> Fermentation            any_matrix                  8    0   0.955   0.000    0.955
Lactic Acid -[formed_by]-> Fermentation        any_matrix                  9    0   0.951   0.000    0.951
hexanal -[formed_by]-> Lipid oxidation         Ground beef / burger        5    0   0.897   0.000    0.897
1-octen-3-ol -[formed_by]-> Lipid oxidation    Pork analogue               4    0   0.890   0.000    0.890
2-pentylfuran -[formed_by]-> Lipid oxidation   Steak / whole cut           4    0   0.878   0.000    0.878
hexanal -[formed_by]-> Thermal degradation     Steak / whole cut           4    0   0.871   0.000    0.871
```

**What the live run actually tells us — the uncomfortable part.**

- **Zero contradictions and zero condition divergences across 5041 claims.** This is not the model
  working; it is the *corpus* being unable to express disagreement. 5035/5041 triplets have
  `polarity = positive`, and almost none carry a numeric `measurement`. Both contradiction rules (R1
  polarity, R2 disjoint intervals) are structurally unfirable. **Extraction, not scoring, is the
  bottleneck** — until Layer C emits negative/quantitative claims, the contradiction machinery is
  untested on real data and only the SAMPLE run in §9b demonstrates it.
- **The graph is nearly one claim per edge**: 4857 distinct edges for 5041 claims. Corroboration
  therefore does almost nothing for the median claim (median `w` = 0.052; p90 = 0.204). The top of the
  ranking is dominated by the handful of edges with 4–9 sources — all of them well-known lipid-oxidation
  aldehydes. **This is failure mode 1 (rich-get-richer) visible in the first real run**, not a
  hypothetical.
- **No claim exceeds w = 0.669.** Nothing hits `directness = target_matrix`, because the live schema
  states a matrix but does not let us verify the matrix *matches the claim's target* — the normaliser
  honestly downgrades every matrix-bearing claim to `analogous_matrix` (0.75) and every matrix-less one to
  `unknown` (0.55). Roughly 58 % of the corpus is running on the guessed constant (failure mode 5).
- **Recomputed vs the file's own `weight` field: mean |diff| 0.011** (stored mean 0.027 vs recomputed
  0.037). The two implementations broadly agree in ordering; this model is systematically slightly more
  generous, mainly because it applies corroboration per condition-bucketed cluster rather than
  per claim. Worth one reconciliation pass with the Data Engineer so one number ships, not two.

### 9b. SAMPLE — contradiction / divergence demonstration

Run with `--json /nonexistent` to force the inline **SAMPLE** corpus — illustrative structure only,
**not verified chemistry, not citable**. It exists because the live corpus (§9a) cannot yet exercise
rules R1–R3.

```
============================================================================================================
MeatCODE claim weighting — w = tier x method x directness x corroboration - contradiction
source: *** SAMPLE DATA *** (pipeline/out/claim_triplets_v1.json not found) — illustrative structure only,
        NOT verified chemistry, do not cite
============================================================================================================

[1] RANKED CLAIMS
claim  edge                                           pol   tier  meth   dir   base  n_eff   corr    pen      W
------------------------------------------------------------------------------------------------------------
S1     2-methyl-3-furanthiol -[aroma_intensity]-> mea +     1.00  1.00  1.00  1.000   3.00  0.635  0.166  0.470
S2     2-methyl-3-furanthiol -[aroma_intensity]-> mea +     1.00  0.90  1.00  0.900   3.00  0.635  0.175  0.397
S4     2-methyl-3-furanthiol -[aroma_intensity]-> mea +     1.00  0.90  1.00  0.900   3.00  0.635  0.237  0.334
S6     hexanal -[off_note_intensity]-> green_offnote_ -     1.00  0.85  1.00  0.850   1.00  0.303  0.000  0.257
S5     hexanal -[off_note_intensity]-> green_offnote_ +     1.00  0.85  1.00  0.850   1.00  0.303  0.044  0.213
S3     2-methyl-3-furanthiol -[aroma_intensity]-> mea +     0.75  0.50  0.75  0.281   1.00  0.303  0.000  0.085
S8     thiamine -[formation_rate]-> 2-methyl-3-furant +     0.45  0.40  0.45  0.081   1.00  0.303  0.000  0.025
S7     hexanal -[off_note_intensity]-> green_offnote_ -     0.45  0.50  0.55  0.124   1.00  0.303  0.306  0.000

[2] CONTRADICTIONS (comparable conditions — genuine disagreement)
  S1 <-> S4  [interval]  [120,180] vs [5,12] OAV   (conditions overlap)
  S2 <-> S4  [interval]  [90,200] vs [5,12] OAV   (conditions overlap)
  S5 <-> S7  [polarity]  + vs -   (conditions overlap)

[3] CONDITION DIVERGENCES (look opposed, are NOT — different context)
  S5 <-> S6  [polarity]  [6,7.5] vs [1,2] pt   -> split by matrix pea_protein_isolate vs soy_protein_concentrate

[4] CONSENSUS EDGES (noisy-OR over agreeing claims, per condition bucket)
edge                                           matrix                       n+   n-    supp     opp   EDGE_W
------------------------------------------------------------------------------------------------------------
2-methyl-3-furanthiol -[aroma_intensity]-> mea cooked_beef                   3    0   0.787   0.000    0.787
hexanal -[off_note_intensity]-> green_offnote_ pea_protein_isolate           1    1   0.213   0.000    0.213
2-methyl-3-furanthiol -[aroma_intensity]-> mea cooked_pork                   1    0   0.085   0.000    0.085
thiamine -[formation_rate]-> 2-methyl-3-furant any_matrix                    1    0   0.025   0.000    0.025
hexanal -[off_note_intensity]-> green_offnote_ soy_protein_concentrate       0    1   0.000   0.257    0.000
```

**Reading the run.** Three behaviours worth checking, and one bug it exposes:
- `n_eff = 3.00` for the beef cluster (S1/S2/S4) — three distinct source groups, so the independence
  discount happens not to bite here. S3 sits in a *separate* pork cluster despite sharing `grp_B` with S2,
  because clustering is by condition bucket first. Set two sample rows to the same `source_group` inside
  one bucket and `n_eff` drops to 2.35; that is the discount firing.
- S4 contradicts S1 and S2 on magnitude under matching conditions, so all three lose weight, S4 most
  (it is outnumbered by credibility mass). No winner is declared.
- S5 vs S6 is the important negative result: opposite polarity, but pea vs soy — routed to
  §3 divergence, penalty 0, and the edge splits into two conditioned edges. S5 vs S7 *is* penalised
  because both are pea at 25 °C. This is the rule that keeps the graph from manufacturing disagreement.
- **Bug surfaced:** the soy edge shows `EDGE_W 0.000` despite carrying a weight-0.257 opposing claim,
  because edge weight is clamped at zero (failure mode 7). It should read −0.257. Not fixed here so the
  output stays honest.
