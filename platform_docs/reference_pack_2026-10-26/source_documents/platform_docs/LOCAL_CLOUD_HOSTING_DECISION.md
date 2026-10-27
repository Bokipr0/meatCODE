<!-- Last updated: 2026-10-18 08:56 UTC · Codex / Advisory · proposed hybrid local-cloud hosting boundary; not implemented. -->

# Proposed decision: MeatCODE local-cloud hosting boundary

## Meeting decision

**Approve a hybrid v1.** Neon remains the only authoritative scientific system of record. Render
remains the stateless, always-on application and query server. Rights-sensitive PDFs, GROBID, TEI,
exact evidence passages, and restricted-text extraction stay in an encrypted controlled local
workspace. A hosted interactive LLM may receive only admitted derived records or source material
whose rights and provider-processing terms explicitly permit hosted processing. pgvector, LightRAG,
Neo4j, graph JSON, embeddings, and other retrieval structures are rebuildable projections; none is
an independent authority for scientific facts.

**Status:** proposed on 18 October 2026; awaiting Lior and Daniel/Yochai approval. This record does
not implement the architecture and does not authorize cloud processing of publisher-controlled
full text. The research and rationale are in the
[full local-cloud architecture report](../reports/MeatCODE%20local%20cloud%20architecture.md); the
admission procedure is in the
[data-processing architecture](DATA_PROCESSING_ARCHITECTURE.md).

## Why this boundary

MeatCODE already runs a shared production service on Render with production and dev data in Neon;
the current Render Python service cannot run Docker ([systems map](SYSTEMS_MAP.md)). The present
scientific bottleneck is evidence density—23 paper-to-molecule links and empty experiment/process
tables—not a missing graph database ([project state](../PROJECT_STATE.md);
[knowledge-graph decision](KG_DECISION.md)). All-local would turn a personal or self-managed machine
into a production availability, patching, security, and recovery dependency. All-cloud would place
rights-limited text in third-party storage or processing before the team has approved publisher and
provider terms.

Commercial API data not being used for training is not the same as zero retention or legal
permission to upload. OpenAI documents endpoint-specific retention and says Files, Batch, and hosted
Vector Stores are not Zero Data Retention eligible
([OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data)); Anthropic likewise
documents separate retention behavior and says Message Batches are not ZDR eligible
([Anthropic retention controls](https://platform.claude.com/docs/en/manage-claude/api-and-data-retention)).
Local execution reduces third-party disclosure but does not create text-and-data-mining rights or
override a licence ([Directive (EU) 2019/790](https://eur-lex.europa.eu/legal-content/EN/ALL/?uri=CELEX:32019L0790)).

| Pattern | Decisive advantage | Decisive disadvantage | Position |
|---|---|---|---|
| **All local** | Maximum direct control over raw evidence; can run offline | Makes self-managed hardware an uptime and recovery dependency; local processing does not create legal rights | Reject as the target; retain as the restricted ingestion lane |
| **All cloud** | Shared availability, elastic inference, managed operations | Crosses the unresolved publisher/provider-processing boundary | Reject for the MVP; allow only for open or explicitly approved content |
| **Hybrid** | Preserves Neon/Render while isolating sensitive evidence and keeping components movable | Requires explicit rights routing, manifests, and recovery across two execution zones | **Recommend** with Neon as the only authority |

## Component placement

| Component | v1 placement | Authority rule |
|---|---|---|
| Canonical database | **Managed cloud: existing Neon production + dev** | Authoritative for admitted sources, identities, claims, observations, conditions, rights/audit state, and batch lineage ([Neon branching](https://neon.com/docs/introduction/branching)) |
| Restricted-text extraction LLM | **Local by default, behind a provider-neutral adapter** | Output is a candidate until independent checking, deterministic validation, and human admission |
| Interactive answer LLM | **Hosted from Render** for admitted or explicitly approved context | Never authoritative; must preserve source-linked answer and citation contracts |
| Knowledge-graph entities and edges | **Canonical rows in Neon; optional local/dev projection** | LightRAG, Neo4j, and graph files are rebuilt one-way from admitted Neon rows |
| Application/API server | **Existing stateless Render service** | No durable scientific corpus on server disk; ingestion never blocks a request ([Render service types](https://render.com/docs/service-types)) |
| GROBID | **Local Docker service for the 10-paper pilot** | TEI is a versioned controlled intermediate; size concurrency from measured CPU/RAM and parse quality ([GROBID Docker guidance](https://github.com/grobidOrg/grobid/blob/master/doc/Grobid-docker.md)) |
| Ongoing ingestion | **Local resumable batch runner now; managed worker later for approved content** | Immutable manifests and status in Neon; transactional dev admission; no partial scientific writes |
| Relevance-tier storage | **Relevance/rights/catalogue state in Neon; restricted artifacts in encrypted local storage; approved cloud objects later** | Relevance is metadata, not a second database; Render persistent disks are not the shared corpus vault ([Render disks](https://render.com/docs/disks)) |
| Embeddings/vector index | **pgvector in Neon for approved representations; restricted vectors remain local or are not retained** | Derived, versioned, and rebuildable; a model change requires governed re-embedding ([Neon pgvector](https://neon.com/docs/extensions/pgvector)) |
| Audit/evaluation | **Git for non-sensitive definitions; Neon for run metadata/verdicts; local vault for protected gold passages** | Human labels and accepted verdicts are evaluation authorities; model outputs are observations |
| Backups | **Neon restore history plus independent logical dumps; encrypted vault backup only where rights permit** | Recovery copies are not a second live authority; define and test RPO/RTO ([Neon backups](https://neon.com/docs/postgres/backup-restore/backups)) |

## Staged plan

| Stage | Action | Exit evidence |
|---|---|---|
| **1 — approve the boundary** | Accept this hybrid rule; name publisher-rights, scientific-review, and backup owners; select 10 papers and classify their rights | Written team approval, named owners, and unambiguous processing class for every pilot paper |
| **2 — local 10-paper pilot** | Run rights gate → GROBID → extraction → checking/validation → transactional Neon dev admission → retrieval evaluation | Parse/OCR quality, wall time, peak memory, model tokens/throughput, field-level precision/recall, severe errors, reviewer minutes, and cost per accepted record |
| **3 — harden the local lane** | Move recurrent work from a laptop to a managed workstation/institutional worker; add service identities, private access, minimal logs, second operator, and tested restoration | The model passes quality gates and local availability or throughput misses the agreed ingestion cadence |
| **4 — scale approved cloud workloads** | Add versioned EU object storage and ephemeral workers only for open/licensed-and-approved inputs; isolate ingestion credentials, budgets, queues, and pools | Written processing rights, approved region/retention/key/lifecycle controls, and measured need for unattended parallel work |

## Explicit non-decisions

This proposal does **not** select a permanent extraction model, answer model, embedding model, LLM
provider, object-storage provider, queue, or GPU. It does not approve production LightRAG or Neo4j,
cloud storage or hosted inference for paid/publisher full text, a separate vector database, or a
hardware purchase. It does not claim that local is cheaper, cloud is more accurate, or the 10-paper
manual process is the final ingestion platform. Each depends on benchmark or rights evidence that
does not yet exist.

## Move triggers

| Future move | Required evidence first |
|---|---|
| Send restricted text to a hosted LLM | Written publisher/legal permission; exact endpoint retention, residency, subprocessors, and organization configuration approved; fixed gold benchmark passes |
| Move GROBID/ingestion to cloud | Inputs cleared for cloud processing; local availability/backlog misses the agreed cadence; worker isolation and object lifecycle approved |
| Buy a dedicated local GPU | A local model passes scientific gates and shows a measured boundary or three-year total-cost advantage; named owner for patching, uptime, and recovery |
| Add Neo4j | Recurring multi-hop/Cypher workflows that Postgres cannot meet at an agreed p95/maintainability target; one-way rebuild and consistency tests demonstrated |
| Adopt LightRAG in production | Beats the existing retrieval baseline on the fixed evaluation set without persisting prohibited passages or bypassing MeatCODE chemistry/provenance rules |
| Add a separate vector database | pgvector misses agreed recall, latency, or throughput after tuning under actual load |
| Add cloud source storage | Rights class, owner, region, encryption/key policy, lifecycle, deletion, audit, and restore test approved |
| Add a durable queue/multiple workers | Multiple producers/workers, continuous ingestion, unattended retries, or queue-age SLO becomes a measured requirement |

## Evidence still missing

- Daniel/legal decision on publisher mining, local retention, quotation, hosted processing, and backups.
- Exact 10-paper corpus, source IDs, and access classes.
- Gold annotations and a named scientific reviewer for identity, conditions, values, and claims.
- Measured GROBID parse/OCR/table quality and local model throughput on the pilot hardware.
- Verified `experiments`, `processes`, and batch-lineage contracts; a numbered migration may be needed.
- RTO, RPO, retention, encryption/deletion policy, key owner, secondary operator, and restore cadence.
- Interactive latency, ingestion cadence, concurrency, monthly budget, and human-review capacity.
- Actual GFI provider configuration for data residency, DPA/ZDR, retention, subprocessors, and regional availability.

## Implementation boundary

The decision is complete only when Lior and the team approve or revise it. Implementation is complete
only after the 10-paper pilot passes the acceptance gates in
[`DATA_PROCESSING_ARCHITECTURE.md`](DATA_PROCESSING_ARCHITECTURE.md), any required migrations are
applied to both Neon branches, and the results are documented. This document changed no Asana task,
Neon data, schema, deployment, or external system.
