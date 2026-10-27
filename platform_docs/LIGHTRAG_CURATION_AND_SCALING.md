# LightRAG curation and scaling — working proposal

_Last updated: 2026-10-20 20:54 UTC · Codex / Advisory · read-only local graph audit and evidence-based pilot proposal._

**Status:** proposed design, not an approved implementation or measured scaling guarantee. Extends the selected M1 extraction / M2 curation / M3 reasoning architecture. Preserves Lior's removal of the provisional relevance-score cutoff. This session did not change the graph, database, application, deployment or Asana.

## Finding: start with graph meaning and input structure

Read-only inspection of `/Users/lior/LightRAG/rag_storage` on 20 October found:

| Metric | Observed |
|---|---:|
| Document status records | 4 processed, 1 failed |
| Chunk records | 206 |
| Graph nodes / edges | 3,759 / 4,531 |
| Graph direction | Undirected |
| Nodes typed `person` | 1,687 (44.9%) |
| Nodes typed `content` | 600 |
| Nodes typed `naturalobject` / `molecule` | 527 / 2 |
| Nodes with evidence chunks belonging to multiple documents | 94 (2.5%) |
| Edges with evidence chunks belonging to multiple documents | 2 |
| Connected components / largest component | 353 / 2,401 nodes |
| Isolated nodes / median degree / maximum degree | 157 / 1 / 68 |
| Chunks containing bibliography XML markers (`biblStruct` or `listBibl`, case-insensitive) | 124 |
| Person-linked chunks containing those markers | 122 of 141 |

Graph, chunk and status files were hash-stable during the follow-up bibliography audit. These are local file observations, not refreshed Neon counts. The 18 October imported batch remains a distinct snapshot; do not assume it contains subsequent local additions. Exact installed LightRAG package/model revisions were not established.

Interpretation: bibliography-rich XML is entering extraction, and a substantial share of graph nodes represent people. That is useful for expert/citation discovery but can distract from chemistry and experiment discovery. It does not prove every such node is irrelevant or wrong. The two `molecule` labels do not mean only two chemicals exist: many could be classified as `naturalobject`. Low multi-document evidence counts do not measure all useful cross-paper paths; they are a diagnostic for identity reuse and repeated support.

## Proposed architecture

GROBID TEI → section-aware text and citation records → M1 candidates → identity resolution and M2 checks → canonical evidence records in Neon → versioned graph/vector projections → bounded retrieval → M3 explanation.

The central design choice is to make scientific assertions durable outside LightRAG's merged descriptions. LightRAG remains an extraction/retrieval component; canonical data carries the scientific semantics and review history.

### 1. Separate scientific findings from the bibliography network

- Parse TEI as XML. Extract body sections, headings, table structures/captions and source locators. Do not send raw XML tags, headers or a bibliography dump as ordinary scientific body text.
- Store authors, references and paper-to-paper citations separately. Build `CITES` edges from resolved reference records, recording unresolved matches instead of guessing.
- Retain introductions and discussions with section labels: a prior finding cited in a review is not a new experiment conducted by that review.
- Preserve table headers, units and footnotes; route failed numeric/table extraction to review. Chunk size is a tunable parameter, not a substitute for section integrity.

### 2. Resolve identity before building cross-paper links

Start with a small scientific vocabulary: paper, experiment, molecule, ingredient/matrix, process, analytical method, sensory attribute and claim. Author/organization nodes remain available through a separate view.

Give entities stable internal IDs and typed aliases. Use DOI for papers and structure-aware chemical identifiers when established. Chemical-name similarity, CAS or a partial identifier alone must not force merges across salts, isomers, mixtures or ambiguous names. Resolve units explicitly. Keep unresolved candidates distinct until checked. Reuse the existing canonical taxonomy and molecule records rather than creating a second identity system inside prompts.

### 3. Preserve individual claims and experimental context

Represent each assertion with subject, predicate, object, paper, experiment, exact evidence locator, section, relevant conditions, original wording, extraction run, validation outcomes and review state. Conditions may include matrix, temperature, pH, duration, concentration, analytical method and measured outcome; unknowns remain NULL.

Different papers can make different assertions about the same pair of entities. Keep those records separate. Model claims/experiments as their own objects if projected into a simple graph; do not rely on one summarized pairwise edge to retain direction, numeric conditions or disagreement. Current upstream LightRAG merges by unordered endpoint pairs; the local importer also sorts endpoints. [Upstream merge implementation](https://github.com/HKUDS/LightRAG/blob/main/lightrag/operate.py) · local `pipeline/import_lightrag_demo.py`.

Source support and inference need separate states. Similarity suggests a candidate connection; it cannot establish a mechanism. A potential disagreement requires comparable conditions before it becomes `CONTRADICTS`. Count independent primary studies separately from chunks, reviews and papers reusing the same dataset. A LightRAG edge weight is not a calibrated probability of truth.

### 4. Use M2 as a measured quality gate

Mechanical checks: source/locator resolves, quoted span matches the stored parse, IDs/types are valid, units are consistent and no records dangle. Semantic checks: evidence entails the assertion, direction and negation are preserved, conditions match, and a review's citation is not misattributed as its own result.

Suggested states: candidate, automatically checked, human reviewed, disputed, rejected and superseded. Disagreement does not by itself imply an invalid extraction: retain valid conflicting findings and qualify them for retrieval. M2 self-confidence is not a pass criterion. Calibrate automatic checks against expert annotations; audit a random sample as well as difficult cases. Prioritize false entity merges, contradictions, numeric claims and high-impact new connections for human review.

For a pre-merge validator, prompt customization alone is insufficient. Implement an explicit candidate staging boundary or controlled export/import adapter. LightRAG exposes graph editing/custom insertion APIs, but current upstream documents weaker crash-recovery guarantees for direct custom-KG insertion; verify the pinned release and reconcile documents, graph, vectors and evidence during promotion. [Custom KG API implementation](https://github.com/HKUDS/LightRAG/blob/main/lightrag/lightrag.py).

## Keep growth useful and operationally bounded

| Concern | Proposed policy |
|---|---|
| Too many paper pairs | Store reusable entities, individual evidence and citations; compute related-paper candidates using sparse inverted/vector indexes instead of materializing every possible pair. Retain only justified or requested derived links. |
| Broad hubs dominate search | Rank by query fit, predicate, conditions, entity specificity and evidence quality. Reduce generic-hub influence; evaluate rare but useful discoveries rather than deleting them by frequency. |
| Context floods M3 | Begin with one-hop expansion, a per-seed neighbor limit, a total token budget and source diversity. Expand selectively when evidence requires it. Proposed limits must be tuned against recall. |
| Duplicate ingestion | Hash document/version and parser/extractor/prompt/model revisions. Checkpoint jobs, deduplicate overlap, retry failed stages and reprocess only affected material. |
| Stale conclusions | Keep append-only assertion history with active/superseded status. On correction/retraction, invalidate affected summaries, vectors and caches; test complete evidence removal. |
| Workspaces fragment connections | Keep global canonical IDs and source mappings. Use separate workspaces only for measured operational/access needs, with an explicit cross-workspace retrieval strategy. |
| Storage growth | Keep full evidence history in canonical storage and derive compact query projections. Projection source-list caps must not erase the canonical evidence ledger. |

Keep extraction and reindexing asynchronous with bounded worker concurrency and separate resource budgets from interactive retrieval. Track queue age, retry rate, extraction time/paper, validator time/paper and reviewer minutes/accepted assertion. More ingestion workers do not automatically help a GPU or database already at capacity.

Default NetworkX storage keeps the whole graph in memory and rewrites a GraphML file; it is useful for local experiments, not the default choice for a shared growing service. [NetworkX implementation](https://github.com/HKUDS/LightRAG/blob/main/lightrag/kg/networkx_impl.py).

Continue evaluating MeatCODE's existing Neon relational graph plus pgvector adapter first. This differs from LightRAG's native `PGGraphStorage`, which uses Apache AGE; pgvector availability does not establish native graph-backend compatibility. Test the exact server/extensions and pinned LightRAG release before selecting that backend. Neo4j is a possible derived store if measured graph workloads justify another service, not a mandatory replacement for Neon. [Postgres backend implementation](https://github.com/HKUDS/LightRAG/blob/main/lightrag/kg/postgres_impl.py).

For filtered approximate vector search, measure recall against exact search: pgvector applies filtering after approximate-index scans, so batch or metadata filters can return too few matches. Tune scans/index layout only after observing query plans and recall. [pgvector filtering documentation](https://github.com/pgvector/pgvector#filtering).

## First experiment: demonstrate useful connections before increasing volume

1. Freeze the four processed local documents and their evidence. Keep failed-document handling explicit. Preserve the existing graph as the baseline.
2. Audit a stratified sample of 100–200 candidate nodes/claims: identities, evidence, reference leakage, numeric statements, rare concepts and proposed cross-paper connections. Record denominators and uncertainty; this small sample is diagnostic, not certification.
3. Re-extract the same documents into a separate experimental projection using clean TEI sections, domain types and canonical identity resolution. Do not reinstate the removed paper relevance-score cutoff; measure query relevance directly.
4. Grow to about ten deliberately overlapping and contrasting papers. A corpus with no expected overlap is not a fair test of cross-paper discovery. Then test 100 and 1,000 papers if prior stages succeed; these are evaluation sizes, not promised capacity limits.
5. Compare vector-only, current graph retrieval and curated graph retrieval on the same corpus and answer model with equal evidence budgets. Reuse `analysis/rag_eval/PROTOCOL.md`; prepare both answerable and unanswerable questions plus reviewed positive/negative paper pairs.
6. Report entity-merge precision/recall, assertion support precision, useful-connection precision@k/recall@k, source diversity, condition errors, p50/p95 retrieval latency, index size, ingestion throughput and reviewer effort. Avoid using node count, largest component or bridge count alone as quality scores.

The key scientific deliverable is an inspectable explanation of *why* two papers connect, with the precise evidence on each side, the conditions that make them comparable, and any inference labelled. An absent edge means no connection was extracted under this corpus and pipeline; it is not evidence that the scientific question has never been studied.

**First product choice for Lior:** prioritize one discovery task: shared chemistry/mechanisms, contrasting experimental outcomes, or transfer of findings across ingredient matrices. This determines which context fields, gold examples and curation rules matter most. Suggested initial engineering step: a clean-TEI versus existing-input extraction experiment, followed by canonical entity resolution.

## Evidence scope

Local sources: `platform_docs/ENGINEERED_RAG_ARCHITECTURE.md`, `LIGHTRAG_DEMO_IMPLEMENTATION.md`, `analysis/rag_eval/PROTOCOL.md`, `pipeline/import_lightrag_demo.py`, `server/lightrag_retrieval.py`, migration 0015, and the current local GraphML/chunk/status files. Online sources above are upstream `main` inspected on 20 October 2026, not proof of the installed local release. No paid LLM runs, extraction, database queries/writes or performance experiments were performed in this session.
