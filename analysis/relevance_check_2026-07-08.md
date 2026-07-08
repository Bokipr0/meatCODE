_Last updated: 2026-07-08 10:11 UTC · Data Engineer · taxonomy-bible relevance check vs relevance_llm, full corpus_

# MeatCODE — corpus relevance check (2026-07-08)

Evidence-based relevance verification of the `sources` corpus against the taxonomy bible (`db/taxonomy/keywords_topics.json`, 91 keywords / 5 branches) and the ingest-time LLM relevance gate (`relevance_llm`). **Read-only** — no rows were changed, quarantined, or deleted in Neon. This is evidence for Daniel to decide on; nothing here auto-applies.

## 1. Corpus health (trust-critical numbers)

- **Total sources:** 818
- **Citable corpus** (non-null `abstract` AND non-null `search_vec`): **790 (96.6%)** — the number that matters for the Oracle, since it can only ground answers in sources that actually have retrievable text.
- **Tagged** (present in `source_topics`): 329 (40.2%) · **Untagged:** 489 (59.8%)

| relevance_llm bucket | sources | % |
|---|--:|--:|
| >=80 | 139 | 17.0% |
| 60-79 | 180 | 22.0% |
| 40-59 | 170 | 20.8% |
| <40 | 329 | 40.2% |

| priority_score bucket | sources | % |
|---|--:|--:|
| >=80 | 45 | 5.5% |
| 60-79 | 289 | 35.3% |
| 40-59 | 282 | 34.5% |
| <40 | 202 | 24.7% |

`priority_score` (60% `relevance_llm` + 40% deterministic venue/citation/recency signal) visibly compresses the tails vs raw `relevance_llm` — e.g. only 45 score >=80 on `priority_score` vs 139 on raw `relevance_llm`, because a well-cited core-journal paper claws back points even when off-topic. For a pure relevance read, `relevance_llm` is the cleaner signal; `priority_score` is the right one for ranking what to surface first.

## 2. Taxonomy-bible relevance signal

Per source, `name + abstract + top_keywords` is matched against the 91-keyword bible (`db.taxonomy.classify()`, reused) and unioned with whatever topics are already attached via `source_topics`. Classified purely on hit count:

| Taxonomy signal | Definition | Sources | % |
|---|---|--:|--:|
| On-topic | 2+ distinct canonical topics matched | 393 | 48.0% |
| Weak | exactly 1 matched | 246 | 30.1% |
| Off-topic | 0 matched, untagged | 179 | 21.9% |

**Known limitation (measured, not assumed):** several level-2 topic names in the bible are common English words used generically elsewhere in food science — *Cooking, Grill, Thermal, Genomics, Vitamins, Peptide, Amino acids, FTIR, Collagen, Metallic*. A lone hit on one of these is usually noise, not real topical overlap (examples below). Because of this, **taxonomy overlap is treated as a secondary/diagnostic signal here, not a verdict** — `relevance_llm` (which reads the actual abstract) stays authoritative for the recommended action. This matches how `score_relevance.py` itself describes the LLM gate: *"it separates keyword-matched from substantive."*

**Branch coverage** (hit-count across the corpus, a source can hit more than one branch):

| Branch | Hits |
|---|--:|
| analytics | 309 |
| flavor_chemistry | 235 |
| flavor_ingredients | 218 |
| meat_analogs | 60 |
| meat_science | 200 |

`meat_analogs` is by far the thinnest branch here too — consistent with the 2026-07-05 white-space analysis (`analysis/white_space_data.md`) that already flagged it as the least-covered branch at ~14% high-relevance.

## 3. Reconciliation vs `relevance_llm` (where the two signals disagree)

| Reconciliation | Meaning | Sources |
|---|---|--:|
| agree | Both signals point the same way | 508 |
| borderline | `relevance_llm` 40-59 (tangential, per its own rubric) | 170 |
| **disagreement** | Taxonomy matched 2+ topics but `relevance_llm` < 40 — the flagged case | **103** |
| coverage_gap | `relevance_llm` >= 60 but zero taxonomy hits and untagged | 37 |

Recommended action breakdown (this is what's colour-coded in the xlsx):

| Recommended action | Sources | % |
|---|--:|--:|
| Keep — relevance_llm >= 60 | 319 | 39.0% |
| Review — relevance_llm 40-59 | 170 | 20.8% |
| Off-topic, check first — LLM<40 but taxonomy matched 2+ topics | 103 | 12.6% |
| Off-topic, high confidence — LLM<40, taxonomy agrees (0-1 hits) | 226 | 27.6% |

Of the 329 sources `relevance_llm` scores below 40, **226 (68.7%)** have zero or at most one (often generic-word) taxonomy hit too — a doubly-confirmed, high-confidence off-topic shortlist. The remaining **103** share vocabulary with 2+ canonical topics despite the LLM rejection; spot-checking a sample of these shows most are still coincidental generic-word overlap (e.g. "ftir"+"thermal" hitting a dairy-protein glycation paper), not the LLM being wrong — but they are the honest disagreement set and worth a human glance before any bulk action.

On the other side, **37 sources** score `relevance_llm` >= 60 (the LLM read them as on-topic) yet match nothing in the 91-keyword bible and were never tagged — these are back-tagging / taxonomy-completeness candidates, not a relevance risk.

## 4. Off-topic shortlist (high confidence — both signals agree)

226 sources total; the 30 lowest-`relevance_llm` are listed here (full list in the xlsx). None have been removed — this is a shortlist for Daniel's review.

| id | Title | Yr | rel_llm | Ingest query |
|--:|---|--:|--:|---|
| 7 | Nutrition, Physical Activity, and Other Lifestyle Factors in the Prevention of C | 2021 | 0 | Flavor and Metabolite Profiles of Meat |
| 393 | Is there a relationship between olfactory dysfunction and duration of menopause? | 2025 | 2 | sensory |
| 448 | Improved Moth-Inspired Algorithm Based on Fuzzy Controller | 2025 | 2 | sensory |
| 452 | Olfactory Function in Patients Undergoing Maxillary Advancement | 2025 | 2 | sensory |
| 394 | Effect of physical activity on olfaction acuity: A systematic review | 2024 | 3 | sensory |
| 413 | Multi-channel portable odor delivery device for self-administered and rapid smel | 2024 | 3 | sensory |
| 456 | Odour source distance is predictable from a time history of odour statistics for | 2024 | 3 | sensory |
| 395 | Olfactory processing in gifted and non-gifted children: assessing the sniffin’ s | 2025 | 4 | sensory |
| 411 | Olfactory outcomes in skull base surgery | 2024 | 4 | sensory |
| 23 | Bisphenol A, nonylphenols, benzophenones, and benzotriazoles in soils, groundwat | 2014 | 5 | Flavor and Metabolite Profiles of Meat |
| 288 | Three-Dimensional Printing in Paediatrics: Innovative Technology for Manufacturi | 2025 | 5 | off-note |
| 391 | Research on pollution identification and safety thresholds based on the olfactor | 2024 | 5 | sensory |
| 403 | Cross‐Sectional and Longitudinal Associations Between Olfaction and White‐Matter | 2025 | 5 | sensory |
| 447 | Children and adolescents with primary headaches exhibit altered sensory profiles | 2024 | 5 | sensory |
| 453 | Can immersive olfactory training serve as an alternative treatment for patients  | 2024 | 5 | sensory |
| 649 | Single-Neuron Responses to Odor-Related Words in the Human Amygdala. | 2025 | 5 | Threshold testing / odor activity values |
| 735 | The Interplay of Salivary Leptin, Taste Perception, and Dental Caries in Adolesc | 2026 | 5 | Reaction flavors / process flavors |
| 760 | Dietary management of pediatric patients with kidney disease: recommendations by | 2026 | 5 | Salt enhancers meat flavor |
| 819 | Exploring the Comparative Impact of Red and White Meat on Cardiovascular Disease | 2025 | 5 | Ageing meat flavor |
| 294 | Strategies to Mitigate Allergenicity of Edible Insect Proteins: Mechanisms, Syne | 2026 | 6 | off-note |
| 396 | Potential application of electronic odor diffuser in olfaction testing | 2024 | 6 | sensory |
| 400 | A canine model to evaluate the effect of exercise intensity and duration on olfa | 2024 | 6 | sensory |
| 406 | Characterization of Self‐Administered Olfactory Assessments Novel Olfactory Sort | 2025 | 6 | sensory |
| 414 | Patients with parosmia respond faster to unpleasant odors than patients with hyp | 2024 | 6 | sensory |
| 398 | Environmental effects on explosive detection threshold of domestic dogs | 2024 | 7 | sensory |
| 408 | Expanding the scope of olfactory evaluation in Alzheimer's disease and related d | 2025 | 7 | sensory |
| 10 | Flax and flaxseed oil: an ancient medicine &amp; modern functional food | 2014 | 8 | Flavor and Metabolite Profiles of Meat |
| 22 | Omega-3 Polyunsaturated Fatty Acids and Their Health Benefits | 2018 | 8 | Flavor and Metabolite Profiles of Meat |
| 284 | From empirical exploration to data-driven innovation: The role of artificial int | 2025 | 8 | off-note |
| 300 | Choosing the “Ideal” Oral Dosage Form for Pediatric Patients: Parents’ Perspecti | 2025 | 8 | off-note |

## 5. Ingest-query quality — where the off-topic material comes from

Off-topic rate (either recommended-action off-topic bucket) by ingest query, top offenders (min 5 sources):

| Ingest query | Total | Off-topic (either bucket) | Off-topic % |
|---|--:|--:|--:|
| sensory | 73 | 68 | 93.2% |
| off-note | 80 | 39 | 48.8% |
| maillard | 80 | 27 | 33.8% |
| fermentation | 76 | 23 | 30.3% |
| plant-protein | 72 | 20 | 27.8% |
| Flavor and Metabolite Profiles of Meat | 20 | 17 | 85.0% |
| 3D-printed meat | 7 | 7 | 100.0% |
| Lipidomics | 7 | 6 | 85.7% |
| Cultivated / cell-based meat | 7 | 6 | 85.7% |
| SAFE (Solvent-Assisted Flavor Evaporation) | 5 | 5 | 100.0% |
| Bitter blockers meat flavor | 7 | 5 | 71.4% |
| Heme analogues (synthetic biology) meat flavor | 7 | 5 | 71.4% |
| Ageing meat flavor | 6 | 5 | 83.3% |
| Marbling / intramuscular fat meat flavor | 7 | 5 | 71.4% |
| Post-rigor biochemistry meat flavor | 5 | 5 | 100.0% |

`sensory` and `off-note` stand out as the dirtiest ingest queries (pulling human-olfaction / clinical-neuroscience literature — Alzheimer's, Parkinson's, anosmia/parosmia, canine explosive detection — that matches bare "odor/sensory" wording but has nothing to do with meaty process flavor). `meat-aroma` and the specific taxonomy-keyword queries are markedly cleaner. These predate the taxonomy-driven query set (`db.taxonomy.search_queries()`) that `openalex_ingest.py` now defaults to — candidates to retire or narrow on the next ingest pass.

## 6. Prior audits cross-check

40 sources have a prior `source_audits` verdict (from the recurring `audit_sources.py` loop, whose Haiku judge reads full tagging + connected-query context, not just name+abstract). Cross-tab against this check's `relevance_llm`-driven recommended action:

| Prior audit verdict | Recommended action here | Sources |
|---|---|--:|
| review | keep | 18 |
| keep | keep | 18 |
| quarantine | keep | 4 |

**Load-bearing disagreement:** all **4** sources the audit loop has staged for quarantine still show `relevance_llm` >= 60 ("Keep" here), because `relevance_llm` only ever saw name + first ~500 chars of abstract at ingest time, while the audit judge additionally reasoned over tags and connected taxonomy queries and scored them much lower. The ingest-time gate is measurably looser than the audit loop on these:

| id | Title | relevance_llm (ingest) | audit relevance (judge) | Audit notes |
|--:|---|--:|--:|---|
| 252 | Study on Interaction of Aromatic Substances and Correlation  | 70 | 35 | Off-topic: focuses on odor perception (EEG, brain activity, sensory thresholds) not meaty process-flavor gener |
| 308 | Hemp-Based Meat Analogs: An Updated Review on Extraction Tec | 72 | 28 | Review on hemp meat analogs, but focuses on nutrition/extraction/sustainability, NOT meaty flavor generation m |
| 341 | Biopurification using non-growing microorganisms to improve  | 75 | 35 | Off-topic: focuses on *removal* of off-flavors via microbial bioconversion, not *generation* of meaty/savory f |
| 380 | Exploring the Role and Functionality of Ingredients in Plant | 62 | 35 | Review in peer-reviewed venue (Foods, 2024) with decent citation count, but abstract centers on ingredient fun |

These 4 are **not** re-flagged by this pass's own action column (relevance_llm alone says keep) — treat the audit loop's quarantine verdict as the more trustworthy read for these specific IDs, and note this as a concrete argument for re-scoring `relevance_llm` with more context (or fully replacing the ingest gate with the audit judge) rather than trusting the ingest-time score in isolation.

## Recommendation

- **Confirm the 4 sources already staged for quarantine by the audit loop** (§6: #252, #308, #341, #380) — they read as "keep" under `relevance_llm` alone, which is exactly why they were nearly missed; the deeper audit judge is the more trustworthy signal here.
- Treat the **226-source high-confidence off-topic shortlist** (section 4, full list in the xlsx) as the primary quarantine-review queue — both an LLM read of the abstract and independent taxonomy-keyword overlap agree.
- The **103-source "check first"** group is lower confidence (mostly generic-word coincidence per the spot-check in §3) — worth a lighter pass, not urgent.
- **489 untagged sources** (59.8%) remain the single biggest structural gap — most are legacy pre-taxonomy ingests, not necessarily off-topic (the ongoing audit loop's "Tag issues" notes already double as a back-tagging worksheet).
- Consider retiring or narrowing the `sensory` and `off-note` ingest queries (§5) before the next ingest pass — they are disproportionately responsible for the off-topic shortlist.
