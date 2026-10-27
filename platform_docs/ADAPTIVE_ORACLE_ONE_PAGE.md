# MeatCODE — Adaptive Oracle memory loop

_26 October 2026 · Proposed design for review; not deployed._

**Purpose:** Make Oracle progressively more useful to each user by remembering relevant goals, constraints and feedback, while keeping personal context separate from validated scientific evidence.

## 1. Capture the interaction
- Oracle sends the question, current context and explicit feedback to the Render API.
- The API records selected events in Neon SQL with user, project, time and source-message identifiers. Current-turn context can be used immediately.

## 2. Digest useful information
- A background process extracts durable preferences, project goals, constraints and decisions; it avoids retaining every sentence as permanent memory.
- Reconcile updates with existing memory. Distinguish explicit user statements from inferred preferences; uncertain or conflicting updates can request confirmation. This process is a proposed service, not a fourth fixed LLM.

## 3. Store private, structured memory
- A separate logical vault in Neon Postgres holds versioned memory records and links back to their source interactions. SQL is authoritative; optional pgvector embeddings support semantic lookup.
- Scope access to the correct user/project. Provide review, correction, deletion and retention controls, including removal from derived indexes. User statements remain user context, not verified scientific facts.

## 4. Adapt retrieval and reasoning
- At each question, the API selects a small relevant memory set. Current explicit instructions take precedence over older preferences.
- User context guides filters and ranking across keyword, vector and bounded graph retrieval. M3 receives both context and cited scientific evidence, clearly distinguished. Preferences must not suppress relevant contradictory findings.

## 5. Close the feedback loop
- Oracle returns an answer or proposed next action. The next user response supplies new constraints, corrections or usefulness feedback, which repeat the cycle.
- Evaluate whether evidence selection and recommendations improve using explicit feedback, citation quality and task outcomes. Do not assume repeated interaction finds an optimal route; action execution requires its own authorization.

## Relationship to the existing architecture
- M1/Qwen extracts; M2 combines rules, model assessment and human review. Approved scientific claims live in Neon as active or reserve evidence. Unresolved claims remain in review.
- The artifact vault, reserve evidence and user-memory vault serve different purposes. Reserve retrieval policy remains open. Personalization changes retrieved context and ranking; it does not automatically retrain M1, M2 or M3.

**Review choices:** What should be remembered? How long? Which updates require confirmation? The new purple loop on the editable diagram shows the proposed flow; existing scientific ingestion remains separate.
