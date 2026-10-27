# MeatCODE — the simple architecture

_26 October 2026 · Design for review, not yet implemented._

**Two connected flows:** turn papers into reliable evidence, then use that evidence and relevant user context to answer questions.

## Build the knowledge

- **1. Scientific papers:** The source material, with each finding linked back to its paper.
- **2. GROBID:** Converts PDFs into structured text for extraction.
- **3. M1 / Qwen:** Runs locally on the PC and proposes entities, relationships and claims.
- **4. Validation / M2 + human:** Checks the extracted claims against their evidence. Humans approve initially; reviewed examples can support later model training and evaluation.
- **5. Knowledge / Neon:** Stores approved evidence and its source links. Active evidence is searched normally; valid but lower-priority evidence stays in reserve. Unresolved claims remain in review.

## Answer and adapt

- **6. Oracle + API:** Receives the question, brings in relevant user context and coordinates the answer. The API is grouped with Oracle to simplify the map.
- **7. Hybrid retrieval:** Selects useful evidence through keywords, vector similarity and graph connections. Sends a limited evidence package to GPT. Reserve-search rules remain to be decided.
- **8. M3 / GPT:** Reasons over the selected evidence and user context, then returns a cited answer through the API. It identifies uncertainty when evidence is insufficient.
- **9. User memory / Neon:** Saves useful goals, preferences, constraints and corrections. Updates this memory after interactions and uses relevant parts in later questions. Users can review, change or delete their memory.

## The repeating loop

**Ask → retrieve → answer → feedback → update memory → ask again.**

- Memory helps choose more relevant evidence and suggestions; it does not automatically retrain GPT or execute suggested actions.
- User statements remain separate from verified scientific evidence. Preferences must not hide contradictory findings.
- Logs, memory processing, artifact storage and ranking still exist behind the scenes. They are grouped within the nine objects rather than shown as separate steps.
