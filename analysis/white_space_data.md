# White-Space Data — Empirical Corpus Coverage vs. Taxonomy

# Last updated: 2026-07-05 16:06 UTC · Data Engineer (parallel white-space run) · live query against Neon via analysis/white_space_analysis.py

Factual data only — no strategic interpretation. Companion to the Advisory agent's strategic white-space narrative (docs/). Re-run the script anytime for fresh numbers: `python3 analysis/white_space_analysis.py`.

## 0. Corpus totals

- Sources total: **818**
- Sources with `relevance_llm` scored: **818**
- Sources with `relevance_llm >= 60` (high-relevance, Oracle-eligible): **319**
- Sources with `relevance_llm >= 80` (very-high): **139**
- `claims` rows: **45**
- `molecules` rows: **799**

## 1. CRITICAL CAVEAT — tagged vs. untagged sources

- Sources with **at least one** `source_topics` tag: **329** (40.2% of 818 total)
- Sources with **zero** taxonomy tags (untagged): **489**
- Total `source_topics` rows (sources can carry >1 topic): **329**

**Read this before trusting any topic/branch coverage number below.** Per PROJECT_STATE.md, only the ~332 sources ingested via `openalex_ingest.py` (the post-taxonomy-sync ingest pass) were tagged into `source_topics`. The original ~496 legacy sources were never back-tagged. The measured tagged count above (329) confirms this: it is far below the 818-source total. Every coverage/white-space number in this report describes **the tagged subset only** — a topic showing '0 sources' may still have relevant papers sitting untagged in the other 489 sources. Back-tagging the legacy 496 is a prerequisite for a fully trustworthy gap read.

## 2. Branch coverage (tagged subset)

| Branch | Tagged sources | High-relevance (≥60) | High-relevance share | Topics in taxonomy bible |
|---|---:|---:|---:|---:|
| analytics | 134 | 73 | 54.5% | 25 |
| flavor_ingredients | 66 | 23 | 34.8% | 15 |
| meat_science | 52 | 14 | 26.9% | 15 |
| meat_analogs | 43 | 6 | 14.0% | 11 |
| flavor_chemistry | 34 | 15 | 44.1% | 25 |

(Branch totals sum to 329 source-topic pairs, not 329 distinct sources, because a source can be tagged to topics in more than one branch.)

## 3. Top ~15 empirical white-space topics (HIGH priority, low/zero coverage)

| Topic | Branch | Priority | Tagged sources | High-relevance (≥60) |
|---|---|---|---:|---:|
| PINN (Physics-Informed NN) | flavor_chemistry | HIGH | 0 | 0 |
| LMMA (low-moisture meat analogs / TVP) | meat_analogs | HIGH | 0 | 0 |
| Precision fermentation | meat_analogs | HIGH | 0 | 0 |
| Pre-rigor biochemistry | meat_science | HIGH | 0 | 0 |
| Cooking | meat_science | HIGH | 0 | 0 |
| Enzymatic processing | flavor_ingredients | HIGH | 1 | 0 |
| Curing | meat_science | HIGH | 1 | 0 |
| GC-Olfactometry (GC-O) | analytics | HIGH | 1 | 1 |
| Plant-based proteins | meat_analogs | HIGH | 1 | 1 |
| Meat aroma | meat_science | HIGH | 1 | 1 |
| Structured fats | flavor_ingredients | HIGH | 2 | 0 |
| Yeast extract | flavor_ingredients | HIGH | 2 | 1 |
| Off-note masking | meat_analogs | HIGH | 2 | 1 |
| Fermentation | flavor_ingredients | HIGH | 2 | 2 |
| Thermal | meat_science | HIGH | 2 | 2 |

- **5 of 75 HIGH-priority topics have ZERO tagged sources.**

## 4. Full topic coverage table (all branches, all priorities)

| Topic | Branch | Priority | Tagged sources | High-relevance (≥60) |
|---|---|---|---:|---:|
| Sensory analysis | analytics | (not in bible) | 0 | 0 |
| Omics | analytics | (not in bible) | 0 | 0 |
| Chromatography | analytics | (not in bible) | 0 | 0 |
| Spectroscopy | analytics | (not in bible) | 0 | 0 |
| Analytics | analytics | (not in bible) | 0 | 0 |
| GC-Olfactometry (GC-O) | analytics | HIGH | 1 | 1 |
| Time-intensity analysis | analytics | HIGH | 3 | 2 |
| Mass spectrometry | analytics | HIGH | 3 | 3 |
| Electronic tongue | analytics | HIGH | 3 | 3 |
| Tasting | analytics | HIGH | 4 | 2 |
| Proteomics | analytics | HIGH | 4 | 3 |
| Threshold testing / odor activity values | analytics | HIGH | 5 | 0 |
| SAFE (Solvent-Assisted Flavor Evaporation) | analytics | HIGH | 5 | 0 |
| HPLC | analytics | HIGH | 5 | 3 |
| QDA (Quantitative Descriptive Analysis) | analytics | HIGH | 5 | 1 |
| HS-SPME | analytics | HIGH | 5 | 4 |
| Volatilomics | analytics | HIGH | 5 | 4 |
| Metabolomics | analytics | HIGH | 5 | 5 |
| FTIR | analytics | HIGH | 6 | 4 |
| Sniffing | analytics | HIGH | 6 | 4 |
| NMR spectroscopy | analytics | HIGH | 6 | 2 |
| Consumer panel | analytics | HIGH | 7 | 2 |
| Transcriptomics | analytics | HIGH | 7 | 4 |
| Genomics | analytics | HIGH | 7 | 4 |
| GCMS | analytics | HIGH | 7 | 3 |
| LCMS | analytics | HIGH | 7 | 3 |
| Peptidomics | analytics | HIGH | 7 | 6 |
| Lipidomics | analytics | HIGH | 7 | 1 |
| Electronic nose | analytics | HIGH | 7 | 6 |
| Aroma Extract Dilution Analysis (AEDA) | analytics | HIGH | 7 | 3 |
| Maillard | flavor_chemistry | (not in bible) | 0 | 0 |
| PINN (Physics-Informed NN) | flavor_chemistry | HIGH | 0 | 0 |
| Flavor Chemistry | flavor_chemistry | (not in bible) | 0 | 0 |
| Process flavor | flavor_chemistry | (not in bible) | 0 | 0 |
| Polysulfides | flavor_chemistry | MED | 0 | 0 |
| Thiophenes | flavor_chemistry | MED | 0 | 0 |
| Peptide | flavor_chemistry | MED | 0 | 0 |
| Amino acids | flavor_chemistry | MED | 0 | 0 |
| Primary sugars | flavor_chemistry | MED | 0 | 0 |
| Vitamins | flavor_chemistry | MED | 0 | 0 |
| Sulfur chemistry | flavor_chemistry | (not in bible) | 0 | 0 |
| Lipid oxidation | flavor_chemistry | MED | 0 | 0 |
| Heme | flavor_chemistry | (not in bible) | 0 | 0 |
| Modeling | flavor_chemistry | (not in bible) | 0 | 0 |
| β-oxidation | flavor_chemistry | MED | 0 | 0 |
| Lipoxygenase pathway (LOX) | flavor_chemistry | MED | 0 | 0 |
| Strecker degradation | flavor_chemistry | MED | 0 | 0 |
| Pyrazine chemistry | flavor_chemistry | MED | 0 | 0 |
| Furan chemistry | flavor_chemistry | MED | 0 | 0 |
| Amadori rearrangement | flavor_chemistry | MED | 0 | 0 |
| Oil chemistry | flavor_chemistry | (not in bible) | 0 | 0 |
| Disulfides | flavor_chemistry | MED | 0 | 0 |
| Heyns rearrangement | flavor_chemistry | MED | 0 | 0 |
| Thiols | flavor_chemistry | MED | 0 | 0 |
| Matrix interactions | flavor_chemistry | HIGH | 3 | 0 |
| Metallic | flavor_chemistry | HIGH | 3 | 0 |
| Myoglobin | flavor_chemistry | HIGH | 3 | 0 |
| Caramelization | flavor_chemistry | HIGH | 4 | 2 |
| Maillard-Lipid interaction | flavor_chemistry | HIGH | 4 | 3 |
| Leghemoglobin | flavor_chemistry | HIGH | 5 | 3 |
| Hemoglobin | flavor_chemistry | HIGH | 6 | 4 |
| AI / ML | flavor_chemistry | HIGH | 6 | 3 |
| Plant-fat alternatives | flavor_ingredients | (not in bible) | 0 | 0 |
| Flavor modulators | flavor_ingredients | (not in bible) | 0 | 0 |
| Flavor Ingredients | flavor_ingredients | (not in bible) | 0 | 0 |
| Enzymatic processing | flavor_ingredients | HIGH | 1 | 0 |
| Structured fats | flavor_ingredients | HIGH | 2 | 0 |
| Fermentation | flavor_ingredients | HIGH | 2 | 2 |
| Yeast extract | flavor_ingredients | HIGH | 2 | 1 |
| Salt enhancers | flavor_ingredients | HIGH | 3 | 0 |
| Maillard intermediates as ingredients | flavor_ingredients | HIGH | 3 | 0 |
| Encapsulated flavors | flavor_ingredients | HIGH | 5 | 0 |
| Kokumi enhancers | flavor_ingredients | HIGH | 5 | 3 |
| Flavor house | flavor_ingredients | HIGH | 5 | 1 |
| Liquid smoke | flavor_ingredients | HIGH | 5 | 4 |
| Reaction flavors / process flavors | flavor_ingredients | HIGH | 6 | 3 |
| Hydrolyzed Vegetable Protein (HVP) | flavor_ingredients | HIGH | 6 | 4 |
| Bitter blockers | flavor_ingredients | HIGH | 7 | 2 |
| Umami enhancers | flavor_ingredients | HIGH | 7 | 2 |
| Oleogels | flavor_ingredients | HIGH | 7 | 1 |
| LMMA (low-moisture meat analogs / TVP) | meat_analogs | HIGH | 0 | 0 |
| Meat analogs | meat_analogs | (not in bible) | 0 | 0 |
| Precision fermentation | meat_analogs | HIGH | 0 | 0 |
| Plant-based proteins | meat_analogs | HIGH | 1 | 1 |
| Off-note masking | meat_analogs | HIGH | 2 | 1 |
| Mycoprotein | meat_analogs | HIGH | 4 | 0 |
| Hybrid products (animal + plant) | meat_analogs | HIGH | 4 | 0 |
| Beany note reduction | meat_analogs | HIGH | 5 | 3 |
| HMMA (high-moisture meat analogs) | meat_analogs | HIGH | 6 | 0 |
| Cultivated / cell-based meat | meat_analogs | HIGH | 7 | 1 |
| Heme analogues (synthetic biology) | meat_analogs | HIGH | 7 | 0 |
| 3D-printed meat | meat_analogs | HIGH | 7 | 0 |
| Processing | meat_science | (not in bible) | 0 | 0 |
| Meat flavor | meat_science | (not in bible) | 0 | 0 |
| Pre-rigor biochemistry | meat_science | HIGH | 0 | 0 |
| Meat Science | meat_science | (not in bible) | 0 | 0 |
| Cooking | meat_science | HIGH | 0 | 0 |
| Connective tissue chemistry | meat_science | (not in bible) | 0 | 0 |
| Culinary aspects | meat_science | (not in bible) | 0 | 0 |
| Curing | meat_science | HIGH | 1 | 0 |
| Meat aroma | meat_science | HIGH | 1 | 1 |
| Thermal | meat_science | HIGH | 2 | 2 |
| Collagen | meat_science | HIGH | 3 | 1 |
| Fermentation (meat) | meat_science | HIGH | 3 | 0 |
| Grill | meat_science | HIGH | 3 | 1 |
| Smoking | meat_science | HIGH | 3 | 2 |
| Myoglobin (meat) | meat_science | HIGH | 5 | 0 |
| Post-rigor biochemistry | meat_science | HIGH | 5 | 0 |
| Ageing | meat_science | HIGH | 6 | 1 |
| Elastin | meat_science | HIGH | 6 | 2 |
| Brining / salting | meat_science | HIGH | 7 | 2 |
| Marbling / intramuscular fat | meat_science | HIGH | 7 | 2 |

## 5. Thin evidence layers

- `claims` total: **45** (claims linked to ≥1 source: 45; claims linked to ≥1 molecule: 41)
- `molecules` total: **799**, by category:

| Category | Molecules |
|---|---:|
| (uncategorized) | 784 |
| Fats | 10 |
| Unclassified | 4 |
| Proteins | 1 |

These are the thinnest layers in the schema — 45 claims and the molecule table's category spread are far below what a credible molecular/claims surface needs; treat both as structurally thin regardless of the topic-coverage read above.
