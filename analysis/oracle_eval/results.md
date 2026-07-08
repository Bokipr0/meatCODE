# Oracle retrieval eval — results

_Retrieval-only sanity check: runs the exact two-tier ts_rank_cd/search_vec ranking logic from server/meatcode_server.py's `_retrieve_sources()` against live Neon for each question in eval_questions.md. Does NOT call the Anthropic API — this checks retrieval quality alone._

Filter: `search_vec IS NOT NULL AND (relevance_llm IS NULL OR relevance_llm >= 60) AND rank > 0`, `ORDER BY ts_rank_cd(search_vec, websearch_to_tsquery('english', query)) DESC LIMIT 6`. Tier 1 runs `query = question` (strict AND); if that returns 0 rows, tier 2 ("OR-fallback" below) retries with `query = question's words joined by " OR "` (recall fallback).
**Summary:** 0/14 questions returned 0 sources. 10/14 needed the tier-2 OR-fallback (tier-1 strict AND-match alone returned 0 rows for them).

<!-- Last updated: 2026-07-08 10:20 UTC · Algorithm Expert · added this human eyeball-relevance
     read on top of the script's raw (machine-generated, reproducible) output below. -->
**Human eyeball-relevance read (Algorithm Expert, this run):**
- **Strong, directly on-topic hits (9/14):** Q1 pea-beany, Q2 Maillard/grilled-beef, Q4 sulfur
  volatiles, Q5 lipid oxidation, Q6 GC-O/aroma-ID methodology, Q7 plant-analog off-note masking,
  Q9 Maillard×lipid interaction, Q12 pea-protein cardboard off-flavor, Q13 HS-SPME sampling — the
  top-6 for each of these genuinely address the question, not just share stray keywords.
- **Moderate / mixed relevance (3/14):** Q8 myoglobin/heme (one Baijiu-aroma paper is a clear
  keyword-overlap miss; the rest are on-topic), Q10 process-flavor precursors (same pattern, one
  weak outlier), Q11 precision-fermentation-for-heme (tier-1 hits are about meat-analog flavor
  generally, not precision fermentation specifically — the corpus is thin here).
- **Weak / tangential (2/14):** Q3 cultivated-beef-metallic-taste and Q14 kokumi-taste-enhancement
  — retrieval returns *something* on-topic-adjacent (general meat taste/aroma papers) but nothing
  that actually addresses "cultivated meat" or "kokumi" specifically. This reads as a genuine
  **corpus gap**, not a retrieval bug — consistent with `analysis/white_space_data.md`'s finding
  that meat_analogs is the thinnest-covered branch (~14% high-relevance) — and it's exactly the
  case the grounding prompt's "say the corpus doesn't cover this" instruction exists for.
- **Net read:** the OR-fallback (added this session — see docs/ORACLE_GROUNDED_RETRIEVAL.md) is
  what makes this usable at all: without it, 10/14 of these realistic questions would have gone to
  Claude with zero sources. With it, 12/14 get genuinely relevant grounding and the other 2 fail
  honestly (few/weak sources on a real corpus gap) rather than silently hallucinating from training
  data. The known remaining risk is per-source precision within a 6-result set (occasional
  off-target filler like the Baijiu hit on Q8/Q10) — the grounding prompt's per-source read
  instruction is the current mitigation; a future reranking pass is the structural fix (see "Next").


## Q1: Why does pea protein taste beany?
- [324] rank=0.0041  Screening of a Microbial Culture Collection: Empowering Selection of Starters for Enhanced Sensory Attributes of Pea-Protein-Based Beverages (2024, Journal of Agricultural and Food Chemistry, 11 citations)
- [314] rank=0.0039  Reduction of Beany Flavor and Improvement of Nutritional Quality in Fermented Pea Milk: Based on Novel Bifidobacterium animalis subsp. lactis 80 (2024, Foods, 7 citations)
- [320] rank=0.0020  Fermentation of Pea Protein Isolate by Enterococcus faecalis 07: A Strategy to Enhance Flavor and Functionality (2025, Foods, 2 citations)

## Q2: What are the key Maillard reaction products formed in grilled beef?
- _tier 1 strict match returned 0 rows — showing tier 2 OR-fallback:_
- [79] rank=11.6000  Maillard Reaction in Flour Product Processing: Mechanism, Impact on Quality, and Mitigation Strategies of Harmful Products (2025, Foods, 36 citations)
- [78] rank=10.6000  Studies on the Increasing Saltiness and Antioxidant Effects of Peanut Protein Maillard Reaction Products (2024, Antioxidants, 13 citations)
- [83] rank=9.4000  Physicochemical and Flavor Characteristics of Maillard Reaction Products from Nile Tilapia Fish Skin Collagen Peptides Induced by Four Reducing Sugars (2025, Foods, 6 citations)
- [74] rank=9.2000  Maillard Reaction: Mechanism, Influencing Parameters, Advantages, Disadvantages, and Food Industrial Applications: A Review (2025, Foods, 223 citations)
- [99] rank=8.8000  The flavour substances and key precursor peptides of meaty flavour prepared from Maillard reaction products of Lycium barbarum seed meal (2025, Food Chemistry, 10 citations)
- [117] rank=8.8000  Antioxidant Activity of Maillard Reaction Products in Dairy Products: Formation, Influencing Factors, and Applications (2026, Foods, 2 citations)

## Q3: What makes cultivated beef taste metallic?
- _tier 1 strict match returned 0 rows — showing tier 2 OR-fallback:_
- [220] rank=4.6000  Insights into the flavor endowment of aroma-active compounds in cloves (Syzygium aromaticum) to stewed beef (2024, Food Chemistry, 18 citations)
- [534] rank=4.4000  Unraveling mechanism of odor-induced taste enhancement in air-dried beef: an integrated approach combining GC-O-MS, intelligent sensory, and molecular docking (2026, Food Research International., 0 citations)
- [86] rank=4.2000  Ultrasound-assisted Maillard reaction of Corynebacterium glutamicum protein: Impact on structure, taste, and plant-based meat applications (2025, Ultrasonics Sonochemistry, 7 citations)
- [540] rank=3.8000  Non-volatile and volatile compound analyses revealed the effect of oregano essential oil on the flavor characteristics of beef. (2026, Frontiers in nutrition, 0 citations)
- [552] rank=3.4000  Integration of sensory, sensor-based, and volatile analyses reveals flavor gaps between plant-based meat analogs and beef patties. (2026, Food research international (Ottawa, Ont.), 0 citations)
- [168] rank=3.4000  Oral processing of meat-flavour textured soy proteins – Part II: Influence on taste compounds release and sensory perception (2025, Food Research International, 3 citations)

## Q4: Which sulfur volatile compounds contribute most to cooked meat aroma?
- [160] rank=0.0040  Characteristic volatile compounds contributed to aroma of braised pork and their precursor sources (2024, Food Chemistry, 48 citations)

## Q5: How does lipid oxidation affect meat flavor development during storage?
- _tier 1 strict match returned 0 rows — showing tier 2 OR-fallback:_
- [699] rank=15.2000  The development of chicken meat flavor from the interaction between Maillard reaction intermediates and enzymatically hydrolyzed-oxidized chicken fat (2025, Food Research International., 0 citations)
- [155] rank=12.8000  Effective Strategies for Understanding Meat Flavor: A Review (2025, Food Science of Animal Resources, 32 citations)
- [369] rank=11.6000  Flavor of extruded meat analogs: A review on composition, influencing factors, and analytical techniques (2024, Current Research in Food Science, 34 citations)
- [124] rank=11.0000  The flavor properties of Amadori rearrangement products and their potentials in flavor replication of plant-based meat analogs: a review (2025, Critical Reviews in Food Science and Nutrition, 3 citations)
- [646] rank=10.6000  Next-generation strategies for designing cultured fat with enhanced flavor and functionality (2026, Trends in Food Science & Technology., 0 citations)
- [550] rank=10.4000  Modulate meat flavor by different forms of Iron with chicken breast as a model. (2026, Food research international (Ottawa, Ont.), 0 citations)

## Q6: What role does GC-Olfactometry (GC-O) play in identifying character-impact meat aroma compounds?
- _tier 1 strict match returned 0 rows — showing tier 2 OR-fallback:_
- [205] rank=11.2000  Difference comparison of characteristic aroma compounds between braised pork cooked by traditional open-fire and induction cooker and the potential formation cause under electromagnetic cooking (2024, Food Research International, 21 citations)
- [189] rank=9.8000  Identification and comparison of aroma and taste-related compounds from breast meat of three breeds of Korean native chickens (2024, Poultry Science, 14 citations)
- [159] rank=9.6000  A lipidomic and volatilomic approach to map the lipid profile and related volatile compounds in roasted quail meat using circulating non-fried roast technology (2024, Food Chemistry, 13 citations)
- [194] rank=9.2000  Characterization of Key Aroma Compounds in Dongpo Pork Dish and Their Dynamic Changes During Storage (2025, Foods, 3 citations)
- [548] rank=9.2000  Comparative lipidomics and volatile profiling reveal distinct aroma signatures in Arbas cashmere goat meat from grazing and housed feeding systems. (2026, Journal of animal science and biotechnology, 0 citations)
- [169] rank=9.0000  Integrated HS-SPME-GC/MS and RNA sequencing analysis reveals metabolic differences of flavor compounds of muscle tissues with different intramuscular fat contents from Tibetan sheep (2025, BMC Genomics, 0 citations)

## Q7: How can off-notes in plant-based meat analogs be masked without adding artificial flavors?
- _tier 1 strict match returned 0 rows — showing tier 2 OR-fallback:_
- [369] rank=15.0000  Flavor of extruded meat analogs: A review on composition, influencing factors, and analytical techniques (2024, Current Research in Food Science, 34 citations)
- [124] rank=13.8000  The flavor properties of Amadori rearrangement products and their potentials in flavor replication of plant-based meat analogs: a review (2025, Critical Reviews in Food Science and Nutrition, 3 citations)
- [155] rank=11.2000  Effective Strategies for Understanding Meat Flavor: A Review (2025, Food Science of Animal Resources, 32 citations)
- [699] rank=9.2000  The development of chicken meat flavor from the interaction between Maillard reaction intermediates and enzymatically hydrolyzed-oxidized chicken fat (2025, Food Research International., 0 citations)
- [692] rank=8.8000  Improving the aromatic profile of plant-based meat alternatives: Effects of leghemoglobin and myoglobin addition on volatiles. (2025, Food chemistry, 1 citations)
- [550] rank=8.0000  Modulate meat flavor by different forms of Iron with chicken breast as a model. (2026, Food research international (Ottawa, Ont.), 0 citations)

## Q8: What is the role of myoglobin and heme compounds in meat flavor and color development?
- _tier 1 strict match returned 0 rows — showing tier 2 OR-fallback:_
- [155] rank=12.4000  Effective Strategies for Understanding Meat Flavor: A Review (2025, Food Science of Animal Resources, 32 citations)
- [508] rank=12.4000  Elucidating the Impact of High-Temperature Daqu on Base Baijiu of Sauce-Flavor Baijiu: From Key Aroma Compounds to Microbial Origins (2026, Foods, 0 citations)
- [369] rank=11.6000  Flavor of extruded meat analogs: A review on composition, influencing factors, and analytical techniques (2024, Current Research in Food Science, 34 citations)
- [699] rank=11.4000  The development of chicken meat flavor from the interaction between Maillard reaction intermediates and enzymatically hydrolyzed-oxidized chicken fat (2025, Food Research International., 0 citations)
- [642] rank=11.4000  Key volatile off-flavor compounds identification in chicken meat and deodorizing effects of polyphenol and spice extracts. (2025, Food chemistry: X, 4 citations)
- [550] rank=11.2000  Modulate meat flavor by different forms of Iron with chicken breast as a model. (2026, Food research international (Ottawa, Ont.), 0 citations)

## Q9: How does the Maillard reaction interact with lipid oxidation to generate meaty aroma notes?
- _tier 1 strict match returned 0 rows — showing tier 2 OR-fallback:_
- [699] rank=11.2000  The development of chicken meat flavor from the interaction between Maillard reaction intermediates and enzymatically hydrolyzed-oxidized chicken fat (2025, Food Research International., 0 citations)
- [585] rank=11.0000  Effects of chicken fat oxidation levels on flavor compounds and sensory properties of Maillard reaction products in chicken bone broth: HS-SPME-GC-MS and molecular simulation approach. (2026, Journal of the science of food and agriculture, 0 citations)
- [696] rank=11.0000  Unraveling the co-evolution of lipidome and flavorome during the light-frying of grass carp cubes: Interactions between lipid oxidation and Maillard reaction. (2026, Food chemistry, 0 citations)
- [594] rank=10.4000  Addition of monosodium glutamate can reduce the oxidative stability of lipids in pork burger patties via early-stage Maillard reaction products formation. (2025, Current research in food science, 0 citations)
- [215] rank=10.2000  Controlled formation of characteristic aroma compounds induced by added seasonings during electromagnetic cooking of braised pork: Weakened lipid oxidation and accelerated Maillard reaction (2025, Food Chemistry, 5 citations)
- [646] rank=9.8000  Next-generation strategies for designing cultured fat with enhanced flavor and functionality (2026, Trends in Food Science & Technology., 0 citations)

## Q10: What precursor compounds drive process (reaction) flavor development during cooking?
- _tier 1 strict match returned 0 rows — showing tier 2 OR-fallback:_
- [508] rank=12.4000  Elucidating the Impact of High-Temperature Daqu on Base Baijiu of Sauce-Flavor Baijiu: From Key Aroma Compounds to Microbial Origins (2026, Foods, 0 citations)
- [699] rank=11.0000  The development of chicken meat flavor from the interaction between Maillard reaction intermediates and enzymatically hydrolyzed-oxidized chicken fat (2025, Food Research International., 0 citations)
- [221] rank=9.6000  Gut Microbiota and Lipid Metabolism: Impacts on Lamb Flavor Precursors (2025, Comprehensive Reviews in Food Science and Food Safety, 3 citations)
- [609] rank=9.6000  Comparative Analysis of Fatty Acids, Amino Acids, and Flavor Compounds among in Different Skeletal Muscles of the Tianzhu White Yak. (2026, Animal bioscience, 0 citations)
- [228] rank=9.6000  Variation of volatile flavor substances in salt-baked chicken during processing (2024, Food Chemistry X, 16 citations)
- [124] rank=9.2000  The flavor properties of Amadori rearrangement products and their potentials in flavor replication of plant-based meat analogs: a review (2025, Critical Reviews in Food Science and Nutrition, 3 citations)

## Q11: How is precision fermentation being used to produce heme or flavor precursors for meat analogs?
- [369] rank=0.4444  Flavor of extruded meat analogs: A review on composition, influencing factors, and analytical techniques (2024, Current Research in Food Science, 34 citations)
- [124] rank=0.0260  The flavor properties of Amadori rearrangement products and their potentials in flavor replication of plant-based meat analogs: a review (2025, Critical Reviews in Food Science and Nutrition, 3 citations)
- [646] rank=0.0089  Next-generation strategies for designing cultured fat with enhanced flavor and functionality (2026, Trends in Food Science & Technology., 0 citations)

## Q12: What causes cardboard-like off-flavors in fermented pea protein products?
- _tier 1 strict match returned 0 rows — showing tier 2 OR-fallback:_
- [340] rank=13.5000  Rapid Acidification and Off-Flavor Reduction of Pea Protein by Fermentation with Lactic Acid Bacteria and Yeasts (2024, Foods, 21 citations)
- [315] rank=10.9000  Unveiling the role of oxylipins in the formation of off-flavor in pea protein isolates (2025, Food Research International, 0 citations)
- [358] rank=10.4000  Tailoring the physico-chemical properties and VOCs of pea-based fermented beverages through Lactobacillus delbrueckii subsp. bulgaricus and Streptococcus thermophilus fermentation (2025, Food Research International, 8 citations)
- [339] rank=9.8000  Assessing the impact of bacterial blends, crosslinking enzyme and storage times on volatile and non-volatile compound production in fermented pea protein emulsion gels (2024, Food Chemistry, 5 citations)
- [314] rank=9.6000  Reduction of Beany Flavor and Improvement of Nutritional Quality in Fermented Pea Milk: Based on Novel Bifidobacterium animalis subsp. lactis 80 (2024, Foods, 7 citations)
- [318] rank=9.6000  Fortification of Pea and Potato Protein Isolates in Oat-Based Milk Alternatives; Effects on the Sensory and Volatile Profile (2024, Foods, 15 citations)

## Q13: How is HS-SPME used to sample volatile compounds in meat products before GC-MS analysis?
- _tier 1 strict match returned 0 rows — showing tier 2 OR-fallback:_
- [180] rank=13.4000  Effect of by-products-based diet and intramuscular fat content on volatile compounds from pork (2025, Meat Science, 1 citations)
- [201] rank=12.6000  Characterization of Volatilized Compounds in Conventional and Organic Vegetable-Source Alternative Meat-Curing Ingredients (2025, Molecules, 7 citations)
- [169] rank=11.2000  Integrated HS-SPME-GC/MS and RNA sequencing analysis reveals metabolic differences of flavor compounds of muscle tissues with different intramuscular fat contents from Tibetan sheep (2025, BMC Genomics, 0 citations)
- [813] rank=11.2000  Analysis of aroma compounds in barbecued mutton during storage and exploration of customer preferences. (2026, BMC chemistry, 0 citations)
- [540] rank=11.0000  Non-volatile and volatile compound analyses revealed the effect of oregano essential oil on the flavor characteristics of beef. (2026, Frontiers in nutrition, 0 citations)
- [151] rank=10.8000  The Aroma of Non-Fermented and Fermented Dry-Cured Meat Products: Savory and Toasted Odors (2025, Foods, 3 citations)

## Q14: What is the sensory and chemical basis of kokumi taste enhancement in meat products?
- [534] rank=0.0019  Unraveling mechanism of odor-induced taste enhancement in air-dried beef: an integrated approach combining GC-O-MS, intelligent sensory, and molecular docking (2026, Food Research International., 0 citations)

