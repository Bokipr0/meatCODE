# MeatCODE RAG benchmark protocol v0.1

_Last updated: 2026-10-18 10:12 UTC · Codex / Algorithm-RAG · live graph/vector import status and user-directed relevance-gate removal; comparative protocol retained._

Status: **protocol and capture foundation implemented; comparative experiment not run**.
Acceptance thresholds below are proposals for Lior and the scientific reviewer to adopt before
opening the held-out test. No measured superiority is claimed.

**Update, 18 October 2026 10:12 UTC:** Lior explicitly removed the provisional Oracle relevance cutoff.
The earlier eligibility observations below describe the code at initial inspection, not the new
local policy. The score field remains stored; it no longer gates local Oracle retrieval. A validated
LightRAG→Neon importer, additive pgvector migration and dev retrieval adapter are implemented.
The migration/import were applied to Neon dev; 7,582 embeddings and the graph/evidence rows were
verified, idempotency passed, and a live semantic graph query succeeded. Claude answer generation
returned 401 for the configured API key; Lior chose to retain Claude and repair the credential. See
[`LIGHTRAG_DEMO_IMPLEMENTATION.md`](../../platform_docs/LIGHTRAG_DEMO_IMPLEMENTATION.md) for current
implementation status, process diagram and exact import command. No comparative benchmark has run.

## What this experiment must answer

1. Does retrieval improve useful, correct answers over the **same answer model** without retrieval?
2. Does adding the extracted graph improve answers over **vector retrieval alone**?
3. Which answer model works best when retrieval and evidence are fixed?
4. Does the full Oracle experience beat a direct GPT/Claude configuration on user tasks?

LightRAG is a retrieval system; GPT and Claude are model families. Compare configurations,
not those names in isolation. The API experiment is the reproducible primary benchmark.
Any later comparison to consumer chat products is a separate, dated user-experience experiment
with actual model label, search mode, memory, tools, attachments and settings recorded.

## Verified starting point, 18 October 2026

| Component | Observed state |
|---|---|
| `/Users/lior/LightRAG/rag_storage` | 3 processed and 3 failed document records |
| Local graph | 3,418 nodes; 4,164 edges |
| Chunks | 194; all resolve to processed documents |
| Graph provenance checks | No missing chunk references or references to nonprocessed documents detected |
| Vector files | Entities 3,418; relationships 4,164; chunks 194; declared dimension 1,024 |
| Local configuration | Answer model `claude-sonnet-4-6`; embedding model `bge-m3:latest` through Ollama |
| Local LightRAG HTTP probe | No reachable OpenAPI response at `127.0.0.1:9621` from this session |
| Neon dev, read-only inspection | 818 sources; 319 pass the relevance filter; installed extensions `plpgsql`, `pg_session_jwt`; **pgvector not installed** |
| Oracle code | `/api/ask` uses FTS and streams sources, answer chunks, optional consensus, done |
| Existing evaluations | Eight diagnostic questions; no reviewed reference answers in their question file |

These checks establish structural links, not scientific correctness. The graph has many extracted
concepts, not necessarily 3,418 unique chemical identities. No database or extraction workspace
was modified. DOI matching subsequently verified the following mappings against Neon dev:

| LightRAG file | Neon source | DOI | Relevance score |
|---|---|---|---|
| `275.tei.xml` | 275 | `10.1111/1541-4337.70318` | 55 |
| `833.tei.xml` | 833 | `10.3389/fnut.2026.1791530` | 32 |
| `857.tei.xml` | 857 | `10.1371/journal.pone.0325622` | 38 |

**All three fall below the Oracle's current relevance threshold of 60.** Existing graph extraction
is real, but it does not currently represent the Oracle-eligible corpus. Keep these as a diagnostic
extraction corpus. Select shared, on-topic papers for the primary Oracle benchmark, or obtain a
scientific reassessment of their relevance. Do not silently lower the threshold or equate an
isolated LightRAG evaluation with the production retrieval policy. Source 275's parsed `titleStmt`
contains a journal title; its matching DOI, rather than that title, established identity.

The latest completed “Architecture” chat selects **local Qwen extraction, independent local
validation, and hosted GPT reasoning for the pilot** (`platform_docs/ENGINEERED_RAG_ARCHITECTURE.md`).
That is the target configuration. The inspected LightRAG workspace is configured with Claude
for generation; configuration alone does not prove which model generated each historical record.
Record extraction history before comparing the existing workspace to a new Qwen/validation pipeline.

## Freeze the corpus and reference answers

Start with the **three successfully processed documents**, subject to source identity and processing
eligibility review. Exclude failed document records. Record each selected document ID, content/file
hash, DOI and canonical Neon `sources.id`. A reviewer must resolve duplicates and ambiguous matches;
never infer an association solely from a similar title. Save the workspace inventory hashes.
Pause ingestion while freezing; rerun the inventory if any input changes.

Build 40 questions: 10 development and 30 sealed test questions. On the test split, use five each of:
single-source facts; graph-dependent multi-step reasoning; numeric conditions/units/matrix;
conflicting evidence; applied formulation/analytical decisions; insufficient-evidence questions.
Write the questions independently of model outputs. If three papers cannot support that variety,
expand the selected corpus before freezing the test. Do not manufacture gold answers.

Each gold record contains: exact user input, expected atomic claims, required conditions/units,
acceptable alternatives, supporting and contradicting evidence locators, relevant chunk IDs,
answerability, unacceptable assertions, reviewer identity and approval. Store restricted passages
only in the approved local evidence vault; the benchmark packet keeps permitted facts and locators.
Gold material is available to reviewers, **never** to answering models or retrieval indexes.
Group paraphrases and questions from the same underlying evidence into one split to limit leakage.

The eight existing questions are a separate smoke test. They are not eight reviewed gold answers
and cannot substantiate a graph-benefit or statistical superiority claim.

## Experimental configurations

| Arm | Retrieval | Answer model | Purpose |
|---|---|---|---|
| A | None | Fixed Claude model M1 | Isolate retrieval benefit |
| B | Vector-only over frozen chunks | M1 | Conventional RAG control |
| C | Graph plus vector over the same corpus | M1 | Isolate graph contribution |
| D | None | Fixed GPT model M2 | Direct-model comparison |
| E | Same saved evidence packets as B | M2 | Model comparison under vector retrieval |
| F | Same saved evidence packets as C | M2 | Model comparison under graph retrieval |
| P | Existing Oracle FTS endpoint | Its reported model | Current product reference |

Run A/B/C first; then D/E/F. Save B/C evidence packets before generation and reuse them for
E/F. Use retrieval-only mode, followed by one shared answer-generation wrapper, so LightRAG's
own generation prompt does not confound the graph comparison. Verify retrieval-only API behavior
against the installed version before implementing that adapter. P searches the larger production
corpus and uses the current product prompt; label it **product reference**, not controlled A/B/C.
An FTS arm restricted to the frozen corpus can later be added as another controlled retrieval arm.

For A–F freeze the exact same user input, common system/answer instructions, output format,
maximum output tokens (initially 1,600), and generation settings supported by both providers.
Freeze and hash the common prompt. Ask all arms to distinguish measured findings from inference,
give conditions when available, and acknowledge unsupported specifics. Only RAG arms receive
retrieved evidence and its citation identifiers. Direct arms may abstain; invented references fail.

Use a fixed common evidence cap (proposed 6,000 tokens, measured with one frozen tokenizer)
and deterministic truncation. Graph summaries consume the same budget as chunks. Log actual
tokens and source IDs. Do not impose a shared number of graph edges and vector chunks as though
they conveyed the same quantity of information. Freeze top-k, fusion, reranking, graph depth and
all retrieval parameters after tuning only on development questions.

Pin exact model IDs, provider endpoint, tokenizer/model revision (resolve `latest` to a digest),
embedding dimension and query/document prefixes, LightRAG package version, prompt hashes, code
hashes, Neon dataset snapshot identifier, index settings and source mappings. Use fresh sessions
without previous answers. Run each question three times per arm, interleaved in seeded random order;
repeat questions, not individual claims, are the statistical unit. Record cold/warm server state.

## Scoring and evidence

Blind answer labels and randomized presentation order hide arm/model names. Two scientific
reviewers score independently; resolve disagreements and retain both initial scores. An optional
LLM judge is diagnostic until calibrated against those reviewers; it is never the sole gold authority.

| Metric | Definition |
|---|---|
| Correctness / completeness | Each 0–4: 0 absent/wrong, 1 major gaps, 2 partial, 3 mostly correct/complete, 4 fully meets the gold rubric |
| Evidence support | Supported substantive claims / checked substantive claims, against the same gold evidence for every arm |
| RAG faithfulness | Claims supported by that arm's actual retrieved context / checked claims; separate diagnostic, N/A for direct arms |
| Citation correctness | Citations whose target supports the attached assertion / checked citations; ID validity alone is insufficient |
| Citation coverage | Evidence-requiring claims with a correct citation / evidence-requiring claims; direct answers without citations do not receive perfect scores |
| Retrieval recall@k / precision@k | Gold relevant chunks retrieved / all gold relevant chunks; relevant retrieved chunks / all retrieved chunks; N/A for direct arms |
| Abstention | Correctly withheld unsupported answers / unanswerable questions, alongside unnecessary abstention rate on answerable questions |
| Graph usefulness | C minus B paired correctness/completeness; successful supported multi-step cases; inspected evidence paths and failure examples |
| Runtime | First-token and complete-response latency p50/p95; retrieval latency separately where instrumented; failures/timeouts included |
| Cost | Actual ingestion and query token usage by model, embedding work, pricing date/rate, infrastructure and reviewer effort separately |
| Reproducibility | Frozen hashes/versions, same inputs, repeat variability, complete failure records |

Evaluate ingestion separately from retrieval/generation. A reviewer annotates entities, relations
and claims in selected evidence passages before seeing extracted outputs. Measure exact/normalized
entity identity precision/recall, typed relation precision/recall (including direction, polarity,
conditions and source), provenance correctness, rejected/accepted records, reviewer minutes per
accepted record, extraction throughput and ingestion cost. Score both raw LightRAG candidates and
post-validation records against that same annotation set. Proposed admission targets: entity and
relation precision each at least 0.95, recall each at least 0.80, provenance correctness 1.00.
Report denominators and intervals; benchmark success cannot be inferred from node/edge counts.

Use null for missing metrics and zero denominators. Report sample sizes and failures per arm;
do not silently drop failures. Report paired mean differences and 95% bootstrap intervals by
question, plus per-category results. Three repeats characterize variability, not triple the sample size.
Current Oracle sources events do not include the exact grounding context, usage, retrieval success
or graph paths: those metrics remain **unobservable**, not guessed. Its consensus event indicates
stance classification, not independently verified factual correctness.

## Proposed acceptance gates, frozen before test execution

- Admission: every imported entity/relation resolves to approved source/chunk evidence; zero dangling
  references, quarantined-source leakage, or unexplained document mappings. Reconcile import counts.
- Retrieval: recall@10 at least 0.80 on answerable gold cases, with category breakdowns.
- Answer evidence: at least 0.90 supported-claim fraction, at least 0.95 citation correctness,
  and zero fabricated references or critical chemistry/unit/condition errors in the held-out run.
- Answer quality: mean correctness at least 3/4; C beats B by at least 0.3/4 on the multi-step subset,
  with no aggregate correctness regression greater than 0.1/4. If intervals include no improvement,
  label the finding inconclusive and expand the test before claiming a graph win.
- Abstention: at least 0.80 correct abstention on unanswerable questions; unnecessary abstention
  no more than 0.10 on answerable questions. A five-question category is a pilot, not precise inference.
- Serving: proposed warm first-token p95 at most 5 seconds and complete-response p95 at most
  30 seconds. Report whether optional consensus time is included. Record cold starts separately.
- Cost: agree the numeric ingestion and per-query budget before paid runs. A missing budget or
  usage measurement cannot receive a cost pass. Report cost per scientifically acceptable answer.

These are independent gates. Do not average away fabricated references or critical errors with
fluent prose. Production adoption requires a reviewed report and the existing release process.

## LightRAG → Neon → pgvector → Oracle implementation sequence

1. Preserve the existing workspace and reuse completed extraction. Inventory and resolve its three
   successful documents to canonical source IDs. Audit failed-document causes separately.
2. Define a versioned candidate import contract: extraction batch, external entity/edge ID,
   canonical IDs where resolved, typed predicate, polarity, matrix/conditions, provenance chunk IDs,
   source ID, locator, extraction model/version, review status. Free-form LightRAG descriptions
   are candidate assertions; do not silently turn them into curated molecule properties.
3. Prepare a numbered dev migration after inspecting actual table contracts. Separate candidate
   assertions from admitted science; upsert by stable external IDs and batch, with idempotency,
   reconciliation, explicit rejects and batch rollback. Preserve conflicting observations.
4. Enable pgvector in dev and build versioned projections from admitted data: eligible chunks,
   entity descriptions and relation descriptions. Retain stable document/chunk/entity mappings.
   Existing vectors are reusable only when their **exact input text**, model revision, dimension,
   prefixes and normalization match. Re-embed changed/canonicalized text; this does not require
   repeating entity/relation extraction. Record and check each embedding input hash.
5. Put FTS, vector-only and graph-hybrid behind a server retrieval interface. The browser keeps
   calling `/api/ask`; it does not connect to Neon. Add benchmark-visible retrieval health, version,
   exact permitted evidence, IDs/paths, timings and usage in an authenticated dev-only trace.
6. Execute A/B/C on the frozen pilot; investigate misses; then execute the cross-model arms and
   produce the blinded report. Promote only after review through the established dev→prod process.

Native LightRAG PostgreSQL tables are an optional projection, not automatically MeatCODE's
domain schema. Its current docs distinguish `PGVectorStorage` and `PGTableGraphStorage`, and
describe limited storage-migration support; **changing storage settings is not a verified import
of this existing local workspace**. Pin the installed version and inspect its migration/export
contracts first. Do not assume Apache AGE is available on Neon.

Primary references checked 18 October 2026:
[LightRAG server/storage documentation](https://github.com/HKUDS/LightRAG/blob/main/docs/LightRAG-API-Server.md),
[graph storage migration](https://github.com/HKUDS/LightRAG/blob/main/lightrag/tools/README_MIGRATE_GRAPH_STORAGE.md),
[Neon pgvector documentation](https://neon.com/docs/extensions/pgvector).

## Available tools and first run

`benchmark.py` uses Python's standard library. `inventory` reads local metadata and hashes without
exporting passages. `prepare` freezes the eight existing smoke questions, current Oracle control
prompt, workspace inventory and review templates. Outputs live under ignored `data/benchmarks/`.

```sh
python3 analysis/rag_eval/benchmark.py inventory --workspace /Users/lior/LightRAG
python3 analysis/rag_eval/benchmark.py prepare --workspace /Users/lior/LightRAG --out data/benchmarks/new-pilot
python3 analysis/rag_eval/benchmark.py capture-oracle --packet data/benchmarks/new-pilot --url http://localhost:8000
python3 -m unittest discover -s analysis/rag_eval -p 'test_benchmark.py'
```

A prepared packet already exists at `data/benchmarks/2026-10-18-pilot/`. Preparation never calls
an LLM. `capture-oracle` makes 24 real Oracle requests (8 × 3), each potentially including the product's
consensus call. It supports the server's Authorization header through `BENCHMARK_AUTHORIZATION`
in the process environment; credentials are never written into results. It checks the frozen question
hash, reads `/api/version`, saves every outcome, and stops reading at `done` on keep-alive streams.
Latency includes product consensus. Errors are retained; no hidden retries.

Implemented since the initial protocol: Neon graph/vector import, dev graph retrieval and a
retrieval SSE trace. Still needed for the controlled experiment: direct-model adapters, separately
controlled vector-only/graph arms, reviewed gold questions, blinded scoring/statistics, and complete
usage/exact-context instrumentation. No comparative benchmark run has been executed. The prepared
packet remains a smoke-test starting point; one live answer attempt stopped at Claude authentication.

## Results template

Run ID / date / corpus hash / approved source IDs / code and model versions / prompt hashes /
retrieval parameters / evidence budget / hardware / warm-up policy / pricing date / reviewer IDs:

| Arm | Questions / repeats | Success / failure | Correctness /4 | Completeness /4 | Claim support | Citation correctness / coverage | Recall@10 / precision@10 | Abstention | TTFT / total p95 | Ingestion / query cost |
|---|---|---|---|---|---|---|---|---|---|---|
| A–F, P separately | pending | pending | pending | pending | pending | pending | pending | pending | pending | pending |

Paired C−B and C−A differences with 95% intervals; category results; critical errors; reviewer
agreement; examples where graph paths helped or harmed; cost per acceptable answer; gate-by-gate
pass/fail/unknown; recommendation and limitations. Keep raw answers, retrieved evidence IDs,
timings and reviewer annotations in the local run directory.

Alignment: live Asana task
[Define the benchmark for LightRAG, GPT, and Claude configurations](https://app.asana.com/1/167772284987522/project/1215201551726181/task/1219613997167139),
due 18 October; first-run task is separate. Asana was read, not modified. The active “Architecture”
chat and the repository's data-processing/local-cloud proposals were inspected; those proposals
remain distinct from implemented production behavior.
