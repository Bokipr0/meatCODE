# MeatCODE hybrid local-cloud architecture

## Which component should be local, managed cloud, or portable across both?

### Takeaway

MeatCODE should adopt a **hybrid boundary, not a hybrid source of truth**: keep the governed scientific record and always-on serving in managed cloud services, while keeping rights-sensitive document parsing and extraction inside a controlled local execution boundary. Every model, graph and retrieval component should sit behind a replaceable adapter; none should become an independent authority for scientific facts.

### Cited Findings

- MeatCODE already defines Neon Postgres as the only production system of record, Render as the production/staging server platform, local GROBID as the parser for eligible scientific full text, and a rule that publisher full text and raw passages do not enter Neon, GitHub, Render, public APIs, vector stores or graph stores. — [MeatCODE data-processing architecture](https://github.com/Bokipr0/meatCODE/blob/dev/platform_docs/DATA_PROCESSING_ARCHITECTURE.md)
- The current system already has independent Neon production and dev branches, a stateless Python server on Render, and an explicit limitation that the existing Render Python service cannot run Docker. — [MeatCODE systems map](https://github.com/Bokipr0/meatCODE/blob/dev/platform_docs/SYSTEMS_MAP.md)
- GROBID recommends its Dockerized web-service mode on a multi-core machine for production/benchmarking rather than its single-threaded batch CLI; its clients can submit parallel PDF-to-TEI jobs and the service concurrency should be sized to available CPU threads. — [GROBID service documentation](https://grobid.readthedocs.io/en/latest/Grobid-service/)
- Render separates web services from background workers, cron jobs and workflows; it describes workflows as appropriate for ETL and on-demand background tasks. — [Render service types](https://render.com/docs/service-types)
- Render filesystems are ephemeral unless a persistent disk is attached. A persistent disk is available to only one service instance, prevents horizontal scaling and zero-downtime deploys, and cannot be reached from cron or one-off jobs, so it is a poor shared artifact store. — [Render persistent disks](https://render.com/docs/disks)
- Both local and hosted model execution can be hidden behind one compatible interface: Ollama documents local endpoints on `localhost` and hosted endpoints, including OpenAI-compatible and Anthropic-compatible interfaces. — [Ollama API documentation](https://docs.ollama.com/api/introduction)
- A hosted API is not equivalent to “data never leaves or is never retained.” Anthropic says standard API inputs/outputs are deleted within 30 days, with exceptions, and Zero Data Retention is a separate approved arrangement; OpenAI similarly says API data is not used for training by default but abuse-monitoring logs may retain customer content for up to 30 days unless eligible controls apply. — [Anthropic retention policy](https://privacy.claude.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data); [OpenAI API data controls](https://developers.openai.com/api/docs/guides/your-data)
- LightRAG is deployable locally or in cloud infrastructure. Its default file-persisted in-memory stores are explicitly for small-scale testing, not production; its current official guidance recommends PostgreSQL as a production backend capable of serving its KV, vector, graph and document-status storage roles. — [LightRAG official repository](https://github.com/HKUDS/LightRAG)
- Neo4j likewise supports both local/self-managed Docker deployment and a fully managed Aura cloud service. Neo4j's GraphRAG package includes vector, full-text, hybrid and Cypher-augmented retrievers, but its knowledge-graph builder is currently marked experimental. — [Neo4j Docker operations manual](https://neo4j.com/docs/operations-manual/current/docker/); [Neo4j Aura documentation](https://neo4j.com/docs/aura/); [Neo4j GraphRAG KG builder](https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_kg_builder.html)

### Inferences

#### Recommended component map

| Component | MVP location | Persistence / authority | Why now | Trigger to move or add infrastructure |
|---|---|---|---|---|
| Canonical database | **Managed cloud: existing Neon production + dev** | **Authoritative** for admitted sources, molecules, claims, observations, conditions, audit state and provenance | It already serves production, supports isolated copy-on-write branches, and keeps one governed scientific record. [Neon branching](https://neon.com/docs/introduction/branching) | Reconsider provider only after a measured availability, compliance, cost or performance failure that cannot be solved within Neon; do not move merely because a new RAG tool includes storage. |
| Full-text extraction / “deducing” LLM | **Portable router; local by default for rights-limited text, hosted allowed only for open/licensed/approved inputs** | Pre-admission outputs are **candidates**, never facts | A local endpoint prevents rights-limited passages from being sent to a third party; a hosted frontier model can still be used where policy permits and where the benchmark shows a material quality advantage. Ollama-compatible local/cloud endpoints make the execution layer replaceable. [Ollama API](https://docs.ollama.com/api/introduction) | Permit hosted full-text extraction only after written rights/provider approval and retention review. Move sustained local work from Lior's laptop to a secured workstation or institutional worker when runs must be unattended, the backlog repeatedly exceeds the team's review capacity, or hardware limits the agreed ingestion cadence. |
| Oracle/query LLM | **Hosted API from Render, with a provider-neutral adapter** | No model is authoritative; it receives only admitted derived records and returns cited synthesis | The production server is already cloud-hosted and the query model benefits from high answer quality and elastic inference. Restricting context to admitted facts sharply reduces the publisher-content issue, but does not remove normal API retention/security review. [Anthropic retention](https://privacy.claude.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data) | Add a local or second-provider fallback only after the same fixed evaluation set proves acceptable groundedness, citation accuracy, latency and cost. |
| Knowledge-graph entities and edges | **Canonical rows in Neon; rebuildable projection locally or in an isolated dev service** | Neon rows are **authoritative**; graph nodes/edges in LightRAG or Neo4j are **derived** | MeatCODE's existing graph is already rebuilt from Neon and the present bottleneck is the paper-to-molecule evidence bridge, not graph traversal technology. [MeatCODE KG decision](https://github.com/Bokipr0/meatCODE/blob/dev/platform_docs/KG_DECISION.md) | Add Neo4j only when fixed product queries routinely require multi-hop traversal or Cypher-based curation that PostgreSQL projections cannot meet at the agreed p95/quality SLO, and only after a one-way rebuild plus consistency test is operational. |
| Application/API server | **Managed cloud: existing stateless Render web service**; local only for development | No durable scientific data on its filesystem | Always-on shared access belongs in the cloud; parsing, indexing and ingestion should not consume request-serving CPU/RAM or make the Oracle wait. Render explicitly separates web services from background workers/workflows. [Render service types](https://render.com/docs/service-types) | Split additional query services only when measured traffic, latency or isolation requirements justify it. Never attach the scientific corpus to the web server's disk. |
| GROBID parser | **Local Docker service for MVP** | TEI is a **versioned, rebuildable intermediate** in the controlled batch workspace | It can process locally, emits structured TEI, and is naturally asynchronous. Official guidance favors its multi-threaded service API over the batch CLI. [GROBID service](https://grobid.readthedocs.io/en/latest/Grobid-service/) | Cloud-host GROBID only for open/licensed inputs after rights approval, or move it to a dedicated local/institutional machine when laptop availability or throughput blocks the agreed ingestion cadence. |
| Dynamic ingestion and orchestration | **Local versioned batch runner now; separate worker/workflow later** | Job/batch state, hashes and admission state in Neon; large temporary artifacts stay outside the API server | The 10-paper pilot does not justify a continuously running cloud queue. The process must be restartable and idempotent, while the serving path reads only admitted records. | Introduce a durable queue plus one or more workers when there are concurrent submitters, multiple workers, automatic retries, continuous discovery, or an operational need to ingest while no approved local machine is online. Render workflows/background workers are candidates for inputs cleared for cloud processing. [Render service types](https://render.com/docs/service-types) |
| Embeddings and vector index | **Managed cloud: pgvector in Neon, behind a retrieval adapter** | **Derived/rebuildable** from approved text representations; store model/version/hash | Neon supports pgvector on every plan, including exact and approximate search, and keeps vector joins and provenance in the existing database. [Neon pgvector](https://neon.com/docs/extensions/pgvector) | Add a separate vector database only after a benchmark shows pgvector cannot meet defined recall and latency under actual load after indexing/query tuning. Changing embedding models requires a governed re-embedding job, not silent in-place mixing. |
| High-relevance versus future-use storage | **Logical status in Neon; physical artifact tier based on rights and lifecycle, not relevance alone** | Relevance, rights, admission and quarantine metadata stay authoritative in Neon | A low-relevance paper can later become important; moving its identity/provenance out of the catalogue would make rediscovery and audit harder. Raw file placement should be governed by rights, retention and access frequency instead. | Add managed object storage only after owner, access, retention and deletion policies are approved. Do not equate “cold” with “untracked.” |
| Audit and evaluation data | **Split: versioned evaluation definitions/config in Git; operational run metadata and scores in Neon; copyrighted evidence spans in the controlled local vault** | Human gold labels and signed-off verdicts are authoritative evaluation assets; model outputs are versioned observations | This keeps reproducibility without putting full passages into the repository or public-serving database. The current architecture already requires parser/model/prompt/schema versions, checker verdicts and validation reports. [MeatCODE data-processing architecture](https://github.com/Bokipr0/meatCODE/blob/dev/platform_docs/DATA_PROCESSING_ARCHITECTURE.md) | Add an experiment-tracking service only when run volume makes Git + Neon run tables inadequate; it must store references/hashes rather than prohibited full text. |
| Backups | **Neon PITR plus independent logical backup; encrypted local/offline backup for the controlled source vault** | Backups are recovery copies, not a second live authority | Neon offers instant restore within a plan-dependent history window and recommends `pg_dump` to remote storage for business continuity/compliance. An independent versioned object store can protect logical dumps from accidental overwrite/deletion. [Neon backup strategies](https://neon.com/docs/postgres/backup-restore/backups); [S3 Versioning](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html) | Select retention/RPO/RTO and test restoration before calling this complete. Use a separate provider/account or at least separate credentials from the production database to reduce a single-account failure domain. |

#### Model-role split

- Do not choose one LLM deployment for the whole system. Use at least three logical roles: **extraction** (local for restricted text), **query synthesis** (hosted over admitted records), and **checking/judging** (independent model or human plus deterministic validation). LightRAG itself now recommends different model roles because extraction and long-context query answering have different capability/latency requirements. — [LightRAG model-role guidance](https://github.com/HKUDS/LightRAG)
- “No training” is necessary but not sufficient for publisher-text approval: ordinary API retention, subprocessor location, feedback paths, file APIs and persistent application state must also be reviewed. — [Anthropic retention policy](https://privacy.claude.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data); [OpenAI API data controls](https://developers.openai.com/api/docs/guides/your-data)
- The model adapter should record `provider`, exact `model`, model revision if exposed, prompt/schema version, temperature/reasoning controls, input hash, output hash, latency and token/cost data for every extraction or evaluation run. This is an architectural inference required to compare local and hosted models reproducibly from the existing versioned-batch rule. — [MeatCODE data-processing architecture](https://github.com/Bokipr0/meatCODE/blob/dev/platform_docs/DATA_PROCESSING_ARCHITECTURE.md)

### Gaps

- The Mac's RAM/GPU, sustained tokens-per-second and thermal behavior are unknown; therefore no rigorous claim can yet be made that a local extraction model will meet the batch deadline or be cheaper than an API.
- Publisher licences and Daniel/legal's position on local retention, cloud processing, quotations and backups remain unresolved; this blocks any definitive cloud placement for paid full text.
- The target query latency, ingestion cadence, monthly budget and acceptable human-review workload are not yet quantified, so scaling triggers must be expressed as measured service-level failures rather than guessed corpus-size thresholds.
- A local model has not yet passed MeatCODE's chemistry-specific extraction benchmark. Locality alone does not establish scientific quality.

## How do all-local, all-cloud and hybrid patterns compare?

### Takeaway

All-local maximizes boundary control but conflicts with MeatCODE's existing shared, always-on product and makes Lior's machine an operational dependency. All-cloud simplifies shared operations but prematurely sends rights-sensitive full text into third-party infrastructure. Hybrid is the only option that preserves the current product, respects the unresolved publisher boundary and allows each component to move later on measured evidence.

### Cited Findings

- MeatCODE's production data and server already live in Neon and Render, while local execution is the documented development and controlled-extraction environment. An all-local choice would therefore be a migration away from a working architecture, not a neutral starting point. — [MeatCODE systems map](https://github.com/Bokipr0/meatCODE/blob/dev/platform_docs/SYSTEMS_MAP.md)
- Local model serving is technically feasible through a localhost API without API authentication, while cloud requests use a hosted endpoint and credential. — [Ollama API](https://docs.ollama.com/api/introduction)
- Hosted commercial APIs offer meaningful protections but still have standard retention and feature-specific exceptions, which matters for publisher full text. — [Anthropic retention](https://privacy.claude.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data); [OpenAI API data controls](https://developers.openai.com/api/docs/guides/your-data)
- Managed cloud components remove some infrastructure work: Neo4j Aura is fully managed, Neon manages Postgres branching/recovery, and Render provides purpose-built web, worker and workflow services. — [Neo4j Aura](https://neo4j.com/docs/aura/); [Neon branching](https://neon.com/docs/introduction/branching); [Render service types](https://render.com/docs/service-types)
- Self-managed components require explicit persistence and recovery: Neo4j's Docker documentation warns that container data is lost without mounted storage, and Render's disk documentation shows that persistent storage constrains scaling and deployment behavior. — [Neo4j Docker storage](https://neo4j.com/docs/operations-manual/current/docker/mounting-volumes/); [Render persistent disks](https://render.com/docs/disks)

### Inferences

| Pattern | Advantages | Disadvantages for MeatCODE | Verdict |
|---|---|---|---|
| **All local** | Maximum control over raw documents; can run offline; no per-token API charge after hardware/model acquisition; easy local experimentation | Loses or complicates always-on team access; Lior's machine, power and internet become production dependencies; team must operate database, model serving, storage, security, patching, monitoring and backups; frontier-quality inference may require hardware not yet measured; conflicts with existing Neon/Render deployment | **Reject as target architecture.** Keep local as the restricted ingestion lane, not the whole product. |
| **All cloud** | Always available to collaborators; managed recovery/monitoring options; elastic compute; easier separation of web and worker services; no local GPU purchase | Rights-limited PDFs/TEI/passages leave the controlled boundary; normal API retention and object-store copies require legal approval; recurring compute/token/storage cost; more cloud credentials and vendors; a cloud pipeline can accidentally make unpublished full text reachable; premature redesign of a 10-paper pilot | **Reject for the MVP.** It may become valid for open/licensed data after policy approval and measurement. |
| **Hybrid** | Preserves Neon + Render; isolates publisher-sensitive work; cloud query path stays always-on; local and hosted models can be benchmarked behind one interface; components can move independently; avoids buying hardware before quality/throughput evidence | Requires explicit rights-based routing, versioned manifests and recovery across two execution zones; local ingestion pauses when the approved machine is unavailable; greater configuration/testing burden; poor design could create split-brain data | **Recommend.** One authoritative cloud data plane plus a controlled local evidence-processing plane, with no dual authority. |

- Local inference should not be described as “free”: its relevant cost is amortized hardware, power, engineering/operations and lower utilization, while cloud cost is usage-based. The decision should use measured total cost per accepted record, not token price alone.
- Cloud should not be described as inherently more accurate: quality belongs to the exact model and task. The same gold set must compare local and hosted configurations, including extraction precision, severe error rate, throughput, human-review minutes and cost per accepted record.
- The hybrid design's main control is a **rights router** before parsing/model execution: `open/licensed-approved` may use an approved cloud lane; `internal-pending` is local only; `excluded` is not processed. This operationalizes the existing access-class rule. — [MeatCODE data-processing architecture](https://github.com/Bokipr0/meatCODE/blob/dev/platform_docs/DATA_PROCESSING_ARCHITECTURE.md)

### Gaps

- There is no benchmark yet for accepted records per hour, human review minutes, severe scientific errors or total cost on the actual 10-paper sample.
- The team has not decided whether “local” means Lior's laptop, a GFI-managed workstation, an on-premise server or a private institutional VM; these have materially different reliability and governance profiles.
- Provider-specific enterprise terms, regional processing and negotiated zero-retention eligibility have not been obtained for GFI.

## What should be the single source of truth versus a derived or rebuildable index?

### Takeaway

There must be one authoritative scientific data plane: Neon. PDFs are controlled evidence, Git is the authority for code/config/decision records, and every TEI file, chunk, embedding, vector index, graph database, LightRAG store, cache and model-generated relation is derived until it passes MeatCODE's admission gate.

### Cited Findings

- The existing MeatCODE decision explicitly requires local GROBID parsing, separate extraction/checking/validation, dev-first transactional admission, and Neon as the only production record. — [MeatCODE data-processing architecture](https://github.com/Bokipr0/meatCODE/blob/dev/platform_docs/DATA_PROCESSING_ARCHITECTURE.md)
- The current knowledge graph is already a projection from Neon and can be rebuilt quickly; the internal decision record warns that an additional graph database would create another data home to synchronize. — [MeatCODE KG decision](https://github.com/Bokipr0/meatCODE/blob/dev/platform_docs/KG_DECISION.md)
- pgvector keeps vectors inside Postgres, with ACID transactions, joins and point-in-time recovery available alongside conventional data. — [Neon pgvector](https://neon.com/docs/extensions/pgvector)
- Neo4j's GraphRAG pipeline writes extracted entities/relations to a graph and can ground extraction with a provided schema, but the pipeline is experimental and still depends on an LLM, resolver and graph writer; using it does not remove the need for MeatCODE's domain validation. — [Neo4j KG builder](https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_kg_builder.html)
- LightRAG's production deployment itself has four storage categories and recommends PostgreSQL as an all-in-one backend, confirming that LightRAG is an application framework with storage choices rather than a magically authoritative scientific database. — [LightRAG storage guidance](https://github.com/HKUDS/LightRAG)

### Inferences

- **Authoritative in Neon:** paper identity/DOI, access class, canonical molecule identity, claims, measurements, experiment/process conditions, source locators, rights/quarantine state, human verdicts, batch identity and promotion/admission status.
- **Authoritative in Git:** migrations, schemas, controlled predicates, prompts, deterministic normalization rules, evaluation questions that contain no restricted passages, release code and decision records.
- **Controlled evidence, not an app database:** original PDFs, TEI and exact checking passages. They need a hash and source ID in Neon but must stay in the approved local vault until rights policy permits another location.
- **Derived and disposable/rebuildable:** chunks, embeddings, vector indexes, FTS indexes, LightRAG KV/graph/vector/doc-status stores, Neo4j projections, KG JSON, caches, summaries and unapproved extractions. “Disposable” means reconstructable from permitted evidence plus pinned versions; it does not mean unlogged.
- **No dual writes from extraction code:** the ingestion pipeline should write authoritative rows to Neon; projection jobs then rebuild pgvector/LightRAG/Neo4j. If a graph tool accepts human curation, the approved change must be written back through a governed Neon command before rebuilding, not remain only in the graph.

### Gaps

- The current schema may lack batch-level lineage and rollback fields; the architecture document already flags that a numbered migration may be required.
- The team has not decided whether any exact evidence snippets may be retained after review, and if so for how long and under which access controls.
- Ownership of the controlled local vault and continuity access for Daniel/Yochai are not defined; this is a material single-person risk.

## How should hot, warm and cold data be separated without losing provenance?

### Takeaway

Use two independent classifications: **scientific/admission state** in Neon and **artifact storage tier** based on access frequency, rights and retention. Every tier must retain `source_id`, content hash, access class, batch ID and version metadata so that moving an artifact never severs its provenance.

### Cited Findings

- AWS S3 Versioning preserves multiple object versions and allows recovery from accidental overwrite/deletion; S3 Lifecycle can transition objects to lower-cost storage classes or expire them according to rules. — [S3 Versioning](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html); [S3 Lifecycle](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html)
- S3 encrypts all new objects at rest by default and supports KMS-based encryption options; transport can be protected with TLS. — [Amazon S3 encryption](https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingEncryption.html)
- Neon now offers branch-aware, S3-style object storage with copy-on-write inheritance and branch-scoped credentials, which could be convenient for non-sensitive working artifacts. — [Neon Object Storage overview](https://neon.com/docs/storage/overview); [Neon Object Storage authentication](https://neon.com/docs/storage/authentication)
- Neon Object Storage is not currently a suitable archival/backup substitute for MeatCODE: its S3 compatibility page says versioning is not enforced, lifecycle rules are not enforced, cross-region replication is unsupported and object-lock enforcement is limited. — [Neon S3 compatibility limitations](https://neon.com/docs/storage/s3-compatibility)
- Render persistent disks are single-service storage and have significant deployment/scaling/access limitations, so they should not hold a shared document lake or the only copy of ingestion artifacts. — [Render persistent disks](https://render.com/docs/disks)

### Inferences

#### Proposed tiers

| Tier | Contents | Location now | Retention and access rule |
|---|---|---|---|
| **Hot — query path** | Admitted bibliographic records, claims, measurements, conditions, rights flags, source locators, active audit state, embeddings of permitted representations | Neon production; dev equivalents in Neon dev | Low-latency queryable. Never include prohibited full passages. Each row carries or resolves to batch/model/schema provenance. |
| **Warm — active curation** | Candidate records, reviewer verdicts, validation reports, active batch manifests; active PDFs/TEI/evidence spans for the 10-paper pilot | Structured state in Neon dev; binary/text artifacts in the encrypted controlled local workspace | Accessible only to the ingestion/review group. Admission changes state; it does not overwrite raw/rejected history. Purge or archive exact text according to the rights policy. |
| **Cold — reproducibility/archive** | Completed manifests, allowed derived outputs, open/licensed raw artifacts where retention is permitted, logical database dumps, historical evaluation reports | Independent encrypted, private, versioned S3-compatible archive after approval; rights-limited full text remains in approved local/offline encrypted custody or is deleted per policy | Use lifecycle rules and restore tests. Cold objects keep immutable keys based on `source_id` + content hash + artifact type + version; Neon stores the locator/hash and rights/retention class. |

- “High relevance” should be a query/curation field, not a separate physical database. A currently low-priority source stays discoverable in the source registry even if its file is cold or absent.
- Use separate prefixes or buckets for `open`, `licensed-approved`, `internal-pending`, `quarantine`, and `backups`, with least-privilege credentials. Never move `internal-pending` into cloud object storage through a generic lifecycle rule.
- Neon Object Storage can be evaluated for branch-aligned, non-sensitive **working** artifacts, but its lack of enforced versioning/lifecycle/replication makes independent S3-compatible storage the stronger archive and backup target. This is an inference from the documented limitations, not a claim that Neon Object Storage is unsafe. — [Neon S3 compatibility limitations](https://neon.com/docs/storage/s3-compatibility)
- A database backup must be kept outside the same operational failure domain as the live database. Neon PITR handles recent operational mistakes; independent logical dumps address longer-term business continuity and account/provider failure. — [Neon backup strategies](https://neon.com/docs/postgres/backup-restore/backups)

### Gaps

- RPO, RTO, history window, backup frequency, restore owner and retention duration have not been approved.
- No object-storage provider/account/region has been selected. AWS S3 is used here as the reference capability, not as a procurement decision.
- The legality of backing up publisher PDFs or TEI outside the primary local workstation is unresolved. An offline encrypted second copy may still constitute retention and must be included in the legal decision.
- The team has not defined a deletion certificate/audit procedure for source files whose licence expires or whose access class changes.

## How should asynchronous ingestion coexist with an always-on query server?

### Takeaway

The Oracle must never parse a PDF or wait for extraction. Use an independent, idempotent batch state machine that writes only reviewed, complete batches to Neon dev and then promotes admitted rows; the Render query server reads only admitted records and remains stateless.

### Cited Findings

- GROBID exposes a web service designed for parallel PDF processing, so parsing can naturally run as a worker separate from the serving path. — [GROBID service documentation](https://grobid.readthedocs.io/en/latest/Grobid-service/)
- Render provides separate service types for request-serving web services, continuous background workers, scheduled cron jobs and ETL-oriented workflows. — [Render service types](https://render.com/docs/service-types)
- Render cron jobs cannot access persistent disks, guarantee at most one active run per cron service and stop runs after 12 hours; long or continuous work should use workflows or background workers. — [Render cron jobs](https://render.com/docs/cronjobs)
- Neon branches are isolated copy-on-write clones; branch writes do not affect production, making dev a suitable first admission target. — [Neon branching](https://neon.com/docs/introduction/branching)
- MeatCODE's current architecture requires one complete approved batch to be written to the dev branch inside transactions, with failed batches leaving no partial state. — [MeatCODE data-processing architecture](https://github.com/Bokipr0/meatCODE/blob/dev/platform_docs/DATA_PROCESSING_ARCHITECTURE.md)

### Inferences

#### MVP state machine

`registered -> rights_checked -> queued -> parsing -> parsed -> extracting -> validating -> human_review -> admitted_dev -> evaluated -> promoted_prod`

Terminal alternatives are `quarantined`, `failed_retryable`, `failed_permanent`, and `excluded_rights`. The query server selects only admitted/promoted records; it never reads in-progress candidates.

#### Idempotency and lineage

- Define the work identity as at least `(source_id, input_sha256, parser_version, extraction_model, prompt_version, schema_version)`.
- A retry with the same identity resumes or reuses completed stages; a changed component creates a new run rather than overwriting the old one.
- Store small status, hashes, timestamps, error classes and validation summaries in an `ingestion_batches`/`ingestion_jobs` contract in Neon dev; keep prohibited raw passages in the controlled workspace.
- Admission is a transaction. Embedding and graph projection happen **after** authoritative rows are admitted and can be retried independently.
- The MVP can be manually triggered on the Mac because only 10 papers are planned. It still needs a manifest and checkpoint files; “manual” must not mean untraceable.

#### Scale path

1. **Pilot:** local GROBID + local restricted-text extraction; manual batch trigger; Neon dev admission; existing Render server unchanged.
2. **Operational local:** dedicated secured workstation or institutional machine with an agent/worker that can run unattended; local queue runner; encrypted local storage; remote status metadata only.
3. **Mixed workers:** approved open/licensed jobs can run in a Render workflow/background worker against object storage; rights-limited jobs remain local. Both implement the same job contract.
4. **Cloud-first ingestion only after approval:** stateless workers pull permitted artifacts from object storage and scale horizontally; local worker remains a fallback/regulated lane.

### Gaps

- The exact job schema, lease/heartbeat behavior, retry limits and dead-letter review procedure have not been designed or migrated.
- Render Workflows' pricing and availability for the current workspace were not evaluated in this research.
- There is no measured per-paper GROBID/extraction duration on the selected pilot hardware, so worker sizing and completion estimates would be speculative.
- The team's preferred alerting/observability service is not defined.

## What decision should Lior present at the noon meeting?

### Takeaway

Present a narrow, reversible decision: **approve a hybrid MVP architecture for the 10-paper pilot, preserving Neon + Render and keeping rights-sensitive ingestion local.** Do not ask the meeting to choose a permanent model vendor, Neo4j, LightRAG, cloud object provider or GPU before the pilot evidence and publisher-rights decision exist.

### Cited Findings

- MeatCODE's current data problem is evidence density—especially paper-to-molecule links and empty experiment/process tables—not the absence of a graph database. — [MeatCODE build-vs-buy memo](https://github.com/Bokipr0/meatCODE/blob/dev/platform_docs/RAG_BUILD_VS_BUY.md); [MeatCODE KG decision](https://github.com/Bokipr0/meatCODE/blob/dev/platform_docs/KG_DECISION.md)
- The approved architecture direction already states that LightRAG or Neo4j may be tested as retrievers/projections but may not become the scientific system of record. — [MeatCODE data-processing architecture](https://github.com/Bokipr0/meatCODE/blob/dev/platform_docs/DATA_PROCESSING_ARCHITECTURE.md)
- LightRAG can use PostgreSQL for all of its production storage roles, while Neo4j is available either self-managed or hosted. Thus neither tool choice forces an all-local or all-cloud architecture. — [LightRAG storage guidance](https://github.com/HKUDS/LightRAG); [Neo4j deployment options](https://neo4j.com/docs/operations-manual/current/docker/); [Neo4j Aura](https://neo4j.com/docs/aura/)

### Inferences

#### Proposed meeting decision — approve now

1. **Architecture:** Hybrid. Neon remains the only production scientific system of record; Render remains the stateless always-on API/query server.
2. **Sensitive ingestion:** PDFs, GROBID TEI and exact evidence from rights-limited papers stay in the approved local vault. Run GROBID locally. Use a local extraction model for restricted text unless legal/provider review explicitly permits hosted processing.
3. **LLM routing:** Hosted query LLMs may receive only admitted, rights-permitted derived records. All model calls go through a provider-neutral adapter and are versioned/evaluated.
4. **Graph/retrieval:** Keep canonical graph entities/edges in Neon. Build pgvector and graph projections as derived indexes. LightRAG and Neo4j remain benchmark candidates, not production authorities.
5. **Asynchrony:** The ingestion worker is separate from the Render web server. The web server reads only admitted data and is not blocked by parsing/extraction.
6. **Storage:** For the pilot, use an encrypted local source vault plus Neon for structured facts and provenance. Do not place publisher full text into cloud object storage. Select an independent versioned S3-compatible archive later for allowed artifacts and logical backups.
7. **Next proof:** Run the 10-paper pilot, measure parsing/extraction quality, review effort, latency, cost and retrieval improvement, and then decide what to move.

#### Explicit non-decisions

- No permanent choice of local extraction model, hosted model vendor or embedding model.
- No production Neo4j or LightRAG deployment.
- No purchase of GPU hardware.
- No cloud storage of paid/publisher full text.
- No final object-storage vendor, region or retention duration.
- No full automation/queue platform until the manual pilot exposes real operational needs.
- No assumption that local is cheaper or that cloud is more accurate; both must be measured on the same gold set.

#### Decision triggers

| Future change | Evidence required before changing |
|---|---|
| Move rights-limited extraction to hosted LLM | Written publisher/legal permission; provider retention, location and feature-specific storage reviewed; chemistry extraction benchmark passes; audit logging enabled. |
| Move GROBID/ingestion to cloud | Inputs cleared for cloud processing; need for unattended/parallel throughput; local backlog or availability misses the agreed cadence; object storage and worker isolation approved. |
| Buy a dedicated local GPU/workstation | Local model passes quality gates; stable workload shows materially lower measured 3-year TCO or a mandatory data-boundary need; named owner for patching, uptime and backup. |
| Add Neo4j | Real product questions require routine multi-hop/Cypher workflows; Postgres projection fails defined p95/maintainability targets; one-way rebuild and consistency checks from Neon are demonstrated. |
| Adopt LightRAG in production | Its configuration beats the existing retrieval baseline on the fixed evaluation set without storing prohibited chunks or bypassing MeatCODE's chemistry schema/provenance. |
| Add a separate vector database | pgvector fails defined recall/latency/throughput SLO after tuning at actual corpus/load; migration/rebuild cost and operational ownership are accepted. |
| Add cloud object storage for source artifacts | Rights classification, access policy, encryption/key ownership, region, lifecycle, deletion, audit and restore test are approved. |
| Add durable queue/multiple workers | More than one producer/worker, continuous ingestion, automated retries or unattended operation becomes a real requirement; job/lease/idempotency contract is ready. |

#### Primary risks and mitigations

- **Hybrid split-brain risk:** Prevent it by allowing authoritative writes only through Neon admission; graph/vector stores rebuild one-way.
- **Local-machine single point of failure:** Keep manifests/hashes remote, maintain an approved encrypted backup, document restore, and move from laptop to a secured worker when ingestion becomes operational rather than experimental.
- **Hosted-provider data leakage/retention:** Apply rights-based routing, redact/minimize context, avoid file APIs for restricted content, negotiate/verify retention controls where necessary, and log the route used.
- **Model drift and irreproducibility:** Pin exact model/prompt/parser/schema versions and rerun a fixed gold set before promotion.
- **Cold archive loses scientific context:** Keep source ID, rights class, object hash, locator and batch linkage in Neon regardless of physical tier.
- **Premature infrastructure expansion:** Require benchmark evidence and an owner before adding Neo4j, a vector database, a queue, a cloud parser or a GPU fleet.

### Gaps

- Lior still needs Daniel/Yochai to accept the hybrid boundary and name an owner for the publisher-rights decision, scientific adjudication and backup policy.
- The 10 pilot papers and their access classes are not selected.
- Meeting participants need to agree on measurable pilot success criteria and who signs off on scientific errors; infrastructure can be approved today, but production ingestion cannot be declared complete without those inputs.
