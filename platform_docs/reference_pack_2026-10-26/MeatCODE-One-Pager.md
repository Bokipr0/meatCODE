# MeatCODE - one-page overview

_Last updated: 2026-10-26 · Codex / Advisory · current system briefing._

MeatCODE (Meat Collaborative Open Development Ecosystem) is a GFI Israel initiative for accelerating meaty flavor and aroma research in alternative proteins. It brings scattered scientific literature, molecules, sensory knowledge and expert information into a searchable platform with a source-backed AI Oracle. Lior Teper builds the platform; Daniel Dikovsky leads the GFI IL SciTech work. This is a prototype under validation.

The platform provides Oracle scientific Q&A, literature exploration, molecule and expert discovery, and research-oriented views. GC-MS interpretation, process-flavor simulation and experimental planning are intended journeys; their presence in a design is not evidence of validated capability.

As checked on 26 October: production serves commit 6394c039749a on main using claude-sonnet-4-6, with a password gate. Neon production contains 49 base tables and 16 views; dev contains 56 base tables and 16 views. Both have 818 source rows, 799 molecule rows, 3,129 experts, 45 claims and 3,650 molecule-property records. There are 23 source-molecule links; experiments and processes remain empty.

The local LightRAG extraction holds 5,101 nodes and 6,240 undirected edges. The separate frozen Neon dev import contains 3 documents, 194 chunk metadata records, 3,418 entities, 4,164 relations and 7,582 vector(1024) embeddings. These are different snapshots. Extracted graph descriptions are demo data, not independently validated scientific claims.

Processing flow: PDF -> OCR when needed -> GROBID TEI -> LightRAG extraction -> versioned import into Neon dev/pgvector. Query flow: Oracle -> Python server -> retrieval -> Claude -> streamed answer with citations. Graph retrieval is a dev-only local-code adapter; deployed retrieval behavior was not re-audited. The selected target adds independent M2 curation; Qwen/GPT model roles in the target diagram are not the same as the currently configured Claude-based services.

Next validation work: curate graph entities and evidence, strengthen paper-to-molecule/condition links, and complete a controlled RAG-versus-direct-LLM benchmark. The October 18 Oracle credential failure has not been retested in this pack.

Repository: https://github.com/Bokipr0/meatCODE (private). Local checkout: dev. Platform: https://meatcode-oracle.onrender.com (password protected).

Read next: READ_ME_FIRST.md, schema/SCHEMA_REFERENCE.md and MeatCODE-System-Visuals.pdf. Key code folders: app/, server/, db/, pipeline/, analysis/, platform_docs/, orchestration/ and Release Center/.
