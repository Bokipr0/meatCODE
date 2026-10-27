# MeatCODE engineered RAG architecture

**Status:** Lior-selected pilot architecture, 2026-10-18. The three model roles and Neon-hosted protected-artifact placement are selected for the pilot; exact model variants, prompts, hardware, storage controls, and promotion thresholds remain to be measured. Nothing in this record is implemented by the diagram itself.

**Visual:** [`diagrams/meatcode-engineered-rag-architecture.svg`](diagrams/meatcode-engineered-rag-architecture.svg) (editable vector) · [`PNG preview`](diagrams/meatcode-engineered-rag-architecture.png)

## Core decision

MeatCODE separates ingestion from serving and gives each model one responsibility:

1. **M1 — local Qwen extraction:** proposes entities, relationships, claims, and source references from GROBID output.
2. **M2 — local validation and curation:** independently checks grounding, schema compliance, relevance, conflicts, confidence, and provenance. It does not treat M1 output as true merely because it is well-formed.
3. **M3 — cloud GPT reasoning:** answers questions, produces decision support and identifies knowledge gaps using only approved evidence retrieved from the governed knowledge layer.

Neon Postgres remains the authoritative scientific record and the overview places the protected artifact vault in controlled Neon storage. Full-text search, embeddings/pgvector, and the graph view are rebuildable retrieval projections. A graph or vector index is never a second scientific authority.

## What every arrow means

| From → to | Payload or action | Admission rule |
|---|---|---|
| Scientific PDFs → GROBID | Document bytes are parsed into structured TEI/XML, sections, metadata, and citations | Process only sources with a recorded access/rights class |
| GROBID → protected artifact vault | TEI/XML, exact passages, parse artifacts, and extraction intermediates | Encrypted, access-controlled Neon storage with explicit rights and retention policy |
| GROBID → M1 Qwen | Structured text and metadata, not an untraceable plain-text dump | Every input carries paper, section/page, and parser-run identity |
| M1 Qwen → M2 validation | Candidate entities, relationships, claims, confidence, and exact source references | Candidates are untrusted until M2 and mechanical checks pass |
| Artifact vault → M2 validation | Exact passages needed to verify each candidate | Local M2 may read controlled Neon evidence; the hosted reasoning model does not receive the raw vault by default |
| M2 → M1 feedback loop | Rejected, ambiguous, conflicting, or low-confidence candidates | Human review is required for unresolved scientific or rights-sensitive cases |
| M2 → Neon | Approved normalized records plus provenance, confidence, rights state, review state, and run lineage | No evidence reference, no admission; unknown values remain `NULL` |
| Neon → retrieval projections | Build/refresh FTS, versioned embeddings in pgvector, and graph views | Every projection must be reproducible from canonical records |
| Oracle → Render | Authenticated user question and permitted user context | Server applies access control and records the run |
| Render → evidence retrieval | Normalized query, filters, and retrieval policy | Rights and audience filters run before evidence leaves retrieval |
| Retrieval projections → evidence retrieval | Ranked records, passages, graph context, and citations | Only approved, audience-permitted material is returned |
| Evidence retrieval → M3 GPT | Bounded evidence pack with source identifiers and requested task | Hosted model receives approved evidence only, not the protected vault |
| M3 GPT → grounded output | Answer, prediction, decision support, or explicit knowledge gap with citations | Unsupported conclusions must be marked as uncertainty or refusal |
| Grounded output → Oracle | User-visible response and citations | UI must preserve provenance and distinguish evidence from inference |

## Benchmark plan — intentionally omitted from the overview infographic

The engineered pipeline and the baseline RAG must receive the same held-out corpus, questions, rights policy, and gold evidence. Compare at least:

- evidence grounding and citation accuracy;
- entity/relation/claim precision and recall;
- severe unsupported-claim rate;
- knowledge-gap/refusal quality;
- human reviewer minutes per accepted record;
- ingestion throughput, interactive latency, and cost.

Cloud scaling is allowed only if the engineered system meets a pre-agreed improvement threshold **and** the rights, retention, security, recovery, and operations review passes. Failure means iterating the model, schema, prompts, or pipeline—not automatically adding more infrastructure.

## Implementation clarifications

- GROBID, M1, M2, embedding generation, and projection rebuilds are asynchronous jobs. They must not run inside a live Oracle request.
- Before exact passages or publisher-controlled text are placed in Neon, the rights owner must approve cloud storage, retention, access, backup, and deletion rules. “Protected” describes intended controls; it is not evidence that these permissions are already resolved.
- The embedding model is a versioned retrieval utility, not a fourth reasoning authority.
- M2 should use independent prompts/checks and, where practical, an independently evaluated model configuration so it does not reproduce M1's errors.
- Low-confidence and conflict cases need a named human scientific-review queue before production admission.
- Moving local components to cloud is a later deployment decision. Passing the quality benchmark alone does not override publisher or provider-processing restrictions.

