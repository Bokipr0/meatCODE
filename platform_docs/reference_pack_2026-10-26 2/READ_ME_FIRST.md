# MeatCODE - system reference pack

_Last updated: 2026-10-26 · Codex / Advisory · local curated pack, read-only live checks._

## Start here

1. **MeatCODE-One-Pager.pdf** - one-page current overview; editable Markdown alongside it.
2. **MeatCODE-System-Visuals.pdf** - current architecture, actual LightRAG screenshot, and simplified schema map.
3. **schema/SCHEMA_REFERENCE.md** - all inspected table/view columns and constraints, production and dev.
4. **source_documents/** - the selected original docs and SQL files, preserved as source material.

GitHub: https://github.com/Bokipr0/meatCODE (private). Platform: https://meatcode-oracle.onrender.com (password gate). Local repository branch verified as dev.

## Current checks versus older documents

- Production public version endpoint: commit 6394c039749a, main, claude-sonnet-4-6; password gate on.
- Production and dev metadata/counts queried in read-only transactions. Production: 49 base tables / 16 views; dev: 56 / 16.
- Local GraphML: 5,101 nodes / 6,240 undirected edges; 5 local document records and 284 chunks observed during startup. The screenshot is the app's 1,000-node / 1,718-edge subset.
- Neon dev frozen demo: 3 documents, 194 chunks, 3,418 entities, 4,164 relations, 7,582 embeddings and 8,932 provenance links. It is not a mirror of today's complete local graph.
- Historical source docs retain their dates. October 11 production/release facts are superseded by this pack's version evidence. Optional/hidden screens are not reclassified as shipped features here.
- Local Oracle score cutoff was removed on October 18; old threshold descriptions remain in historical docs. Deployed retrieval code was not re-audited today.
- The polished earlier target architecture labels M3 GPT and proposes independent M2 admission. Current Oracle reports Claude; the new current-architecture page explains this distinction.
- Original collaborator two-pager claims more than 1,000 collected sources; the current database contains 818 source rows. Collected-source inventory and admitted rows are different quantities; the larger collection was not audited.
- Existing API key problem was last seen October 18. No paid LLM query was sent in this gathering task; answer quality/credential repair and benchmark scores are not reverified.
- GROBID and its Docker MCP adapter were verified October 20. Docker was subsequently stopped at Lior's request; it was not restarted for this pack. Only the existing local LightRAG UI was started for the screenshot.
- The migrations README references historical baseline files absent from this checkout. SQL history is useful context, but is not a confirmed complete rebuild path. Use the fresh schema inventory to understand what exists.

## Key folders

| Folder | What it explains |
|---|---|
| app/ | Platform HTML, assets and UI |
| server/ | Python API, Oracle SSE and retrieval adapter |
| db/ | SQL migrations, taxonomies and seeds |
| pipeline/ | Literature ingestion, GROBID and LightRAG importer |
| analysis/ | RAG evaluation, benchmark and internal analysis |
| platform_docs/ | Architecture, decisions, schemas and operating docs |
| docs/ | Product journeys, strategy, meeting history |
| orchestration/ | Agent onboarding, skills and snapshot tooling |
| Release Center/ | Local start, staging/release and rollback scripts |
| /Users/lior/LightRAG/rag_storage/ | Local extracted graph, vectors, chunks and statuses |
| /Users/lior/LightRAG/inputs/ | Local PDF/extraction inputs; not included in pack |

## Selected reading order and original documents

| Document | Why read it |
|---|---|
| [START_HERE.md](source_documents/START_HERE.md) | Entry point; dated October 11 status needs the current supplement. |
| [PROJECT_STATE.md](source_documents/PROJECT_STATE.md) | Technical status and dated changes; older live-production section is historical. |
| [platform_docs/SYSTEMS_MAP.md](source_documents/platform_docs/SYSTEMS_MAP.md) | GitHub, Neon, Render, Asana, ownership and release connections. |
| [platform_docs/SYSTEM_SNAPSHOT.md](source_documents/platform_docs/SYSTEM_SNAPSHOT.md) | Historical October 11 inventory; fresh schema inventory is included separately. |
| [docs/MeatCODE_MVP_Definition_and_User_Journeys.md](source_documents/docs/MeatCODE_MVP_Definition_and_User_Journeys.md) | Product purpose, intended user journeys and success criteria; July plan. |
| [platform_docs/ENGINEERED_RAG_ARCHITECTURE.md](source_documents/platform_docs/ENGINEERED_RAG_ARCHITECTURE.md) | Selected target architecture, model responsibilities and admission rules. |
| [platform_docs/DATA_PROCESSING_ARCHITECTURE.md](source_documents/platform_docs/DATA_PROCESSING_ARCHITECTURE.md) | Ingestion, evidence, normalization, validation and governance design. |
| [platform_docs/LOCAL_CLOUD_HOSTING_DECISION.md](source_documents/platform_docs/LOCAL_CLOUD_HOSTING_DECISION.md) | Hosting tradeoffs; proposal, with later vault-placement clarification in engineered architecture. |
| [platform_docs/LIGHTRAG_DEMO_IMPLEMENTATION.md](source_documents/platform_docs/LIGHTRAG_DEMO_IMPLEMENTATION.md) | Implemented graph/vector demo, source mapping, data model and dated checks. |
| [platform_docs/LIGHTRAG_CURATION_AND_SCALING.md](source_documents/platform_docs/LIGHTRAG_CURATION_AND_SCALING.md) | Graph quality audit, bibliography leakage and curation plan. |
| [platform_docs/KG_CLAIM_MODEL.md](source_documents/platform_docs/KG_CLAIM_MODEL.md) | Why scientific assertions need conditions, provenance and review. |
| [platform_docs/KG_DECISION.md](source_documents/platform_docs/KG_DECISION.md) | Historical graph direction; read with newer implementation notes. |
| [platform_docs/tagging_relational_guide.md](source_documents/platform_docs/tagging_relational_guide.md) | Taxonomy and source tagging relationships. |
| [platform_docs/DECISIONS.md](source_documents/platform_docs/DECISIONS.md) | Dated decisions; later user direction and implemented code can supersede old entries. |
| [platform_docs/PEOPLE.md](source_documents/platform_docs/PEOPLE.md) | Owners, collaborators and responsibilities. |
| [platform_docs/TWO_ENVIRONMENT_WORKFLOW.md](source_documents/platform_docs/TWO_ENVIRONMENT_WORKFLOW.md) | Development, staging, production and release boundary. |
| [platform_docs/GITHUB_READINESS.md](source_documents/platform_docs/GITHUB_READINESS.md) | Repository review and publication considerations. |
| [pipeline/grobid/README.md](source_documents/pipeline/grobid/README.md) | Local PDF-to-TEI service and verification. |
| [pipeline/grobid/mcp/README.md](source_documents/pipeline/grobid/mcp/README.md) | Local GROBID MCP tools and scoped file access. |
| [analysis/rag_eval/PROTOCOL.md](source_documents/analysis/rag_eval/PROTOCOL.md) | Benchmark design; no comparative result is implied. |
| [db/migrations/README.md](source_documents/db/migrations/README.md) | Migration convention; some named baseline files are absent from this checkout. |

Additional originals: `source_documents/MeatCODE-external-collaborator-2-pager-original.docx`, WUR deck, and earlier target architecture images/SVGs.

## Schema evidence

- `schema/live_schema_inventory.json`: complete columns, constraints, indexes, views, table counts and extension versions.
- `schema/production_version.json`: current public production version response.
- `schema/local_graph_inventory.json`: file-backed graph count and modification timestamp.
- The schema diagram intentionally simplifies the 49-table production model. The inventory includes all observed relationships, including the 7 dev-only graph tables.

## Scope

This is a local internal reference pack, not a public release or a production backup. No raw publisher PDFs, full-text chunks, API keys, environment files, connection strings or credentials were copied. The screenshot includes extracted entity labels and the source docs include internal context. Gathering this pack did not grant anyone access or modify data/schema. No Git, deployment, graph ingestion or model call was performed.

The supplied originals and new notes are dated snapshots. This pack does not update every historical document. Publish the new repository documentation through the normal dev release process when ready.