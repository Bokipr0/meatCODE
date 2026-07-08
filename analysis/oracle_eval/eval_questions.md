# Oracle retrieval eval — question set

<!-- Last updated: 2026-07-08 10:20 UTC · Algorithm Expert · initial 14-question set for the
     grounded-RAG retrieval sanity check (analysis/oracle_eval/run_eval.py) -->

Real-world R&D questions a GFI/MeatCODE researcher might actually type into the Oracle,
spanning all 5 taxonomy branches (`db/taxonomy/keywords_topics.json`: analytics,
flavor_chemistry, flavor_ingredients, meat_analogs, meat_science) so the retrieval sanity
check isn't cherry-picked toward easy hits. `run_eval.py` parses one question per numbered
line below and runs ONLY the retrieval SQL against Neon — it never calls the Anthropic API.

1. Why does pea protein taste beany?
2. What are the key Maillard reaction products formed in grilled beef?
3. What makes cultivated beef taste metallic?
4. Which sulfur volatile compounds contribute most to cooked meat aroma?
5. How does lipid oxidation affect meat flavor development during storage?
6. What role does GC-Olfactometry (GC-O) play in identifying character-impact meat aroma compounds?
7. How can off-notes in plant-based meat analogs be masked without adding artificial flavors?
8. What is the role of myoglobin and heme compounds in meat flavor and color development?
9. How does the Maillard reaction interact with lipid oxidation to generate meaty aroma notes?
10. What precursor compounds drive process (reaction) flavor development during cooking?
11. How is precision fermentation being used to produce heme or flavor precursors for meat analogs?
12. What causes cardboard-like off-flavors in fermented pea protein products?
13. How is HS-SPME used to sample volatile compounds in meat products before GC-MS analysis?
14. What is the sensory and chemical basis of kokumi taste enhancement in meat products?
