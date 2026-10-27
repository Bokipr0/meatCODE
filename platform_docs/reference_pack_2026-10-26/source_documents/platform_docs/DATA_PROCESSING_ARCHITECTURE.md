<!-- Last updated: 2026-10-17 20:42 UTC · Codex / Advisory · proposed v1 data-processing architecture; based on the 2026-10-11 system snapshot and existing extraction strategy. -->

# MeatCODE data processing procedure and architecture

## Decision

Use a **governed batch pipeline with Neon Postgres as the only production system of record**.
Process eligible scientific full text locally with GROBID, extract qualitative claims and numeric
observations in parallel, resolve entities deterministically, and require independent checking plus
mechanical validation before admitting derived records to Neon. Keep publisher full text and raw
passages out of Neon, GitHub, Render, public APIs, vector stores, and graph stores. The Oracle reads
only admitted records through a retrieval adapter; its current Postgres full-text search remains the
production baseline until an evaluated alternative beats it.

This decision defines the stable architecture regardless of the later choice between LightRAG,
Neo4j, pgvector, or another retrieval component. Those tools may consume approved representations;
none becomes the scientific system of record.

**Status:** architecture recommendation complete and ready for Lior plus Daniel/Yochai sign-off.
No schema, database, deployment, or production data was changed by this decision record.

## Why this fits the system that exists

As of the verified 11 October snapshot, MeatCODE already has 818 sources, 798 non-junk molecules,
3,650 provenanced molecule-property observations, 45 claims, and a live grounded Oracle. The weak
point is not document storage or graph technology: only 23 paper-to-molecule links exist;
`experiments` and `processes` are empty; and no molecule-property observation cites a paper. The
pipeline must therefore increase **condition-bound evidence density** without creating a second
uncontrolled source of truth.

## Architecture

```text
Source registry and rights gate (Neon sources)
        |
        v
Controlled local source vault (PDFs; never committed or publicly served)
        |
        v
GROBID local parser -> TEI XML -> evidence-ready passages
        |                              |
        |                              +-> parse/rights failures -> quarantine report
        v
Parallel extraction
  A. claims, relations, conditions     B. numeric values, units, methods, uncertainty
        |                              |
        +---------------+--------------+
                        v
Entity resolution and normalization
  DOI/source_id; PubChem/InChIKey; controlled predicates; explicit units only
                        |
                        v
Independent checker -> deterministic validator -> batch admission gate
                        |
                        v
Neon dev: approved derived records + provenance
  sources / claims / source_molecules / experiments / processes /
  molecule_properties and their join tables
                        |
                        v
Evaluation and human acceptance -> production promotion
                        |
                        v
Retrieval adapter -> FTS baseline; optional vector/graph candidate -> Oracle/API
```

## Processing procedure

### 1 Source registration and eligibility

1. Every paper must first resolve to one `sources.id`, preferably by DOI. Duplicate DOI, ambiguous
   identity, or missing rights classification blocks full-text processing.
2. Record access class as one of: open, licensed/approved for mining, internal-only pending rights,
   or excluded. The formal publisher-rights decision is still open, so the default for paid content
   is internal-only.
3. Apply the existing relevance and audit controls before extraction. A quarantined source cannot
   enter a new extraction batch until a human resolves the verdict.
4. Freeze a batch manifest containing source IDs, file hashes, access class, parser version, schema
   version, prompt/model versions, and timestamps.

### 2 Controlled acquisition and parsing

1. PDFs live in a controlled local vault that is excluded from Git. Open or licensed files may be
   retained according to their rights; paid files pending a decision must not leave that boundary.
2. Run GROBID locally to produce TEI XML. Do not send rights-limited full text to a hosted parser.
3. Segment TEI into stable passages carrying `source_id`, section, page/table/figure locator,
   passage ordinal, and input hash.
4. A scanned or structurally failed PDF is not treated as successfully parsed. Route it to a parse
   exception queue for OCR or manual handling.

### 3 Parallel evidence extraction

Run two separate outputs over the same evidence-ready passages:

- **Claim extraction:** subject, controlled predicate, object, polarity, epistemic status,
  comparator, matrix, process conditions, and evidence locator.
- **Numeric extraction:** raw expression, raw unit, basis/denominator, normalized value only when
  deterministic, uncertainty, replicate count, method, experiment/sample/treatment, and locator.

Use deterministic parsers first for explicit quantities, units, identifiers, and exact string
checks. Use an LLM for semantic binding and interpretation, never for inventing a missing number,
chemical identifier, condition, or citation. Claims and numeric observations remain separate until
both have passed checking.

For rights-limited full text, use a local extraction model unless Daniel/legal explicitly approves
processing by a hosted provider. Hosted models may process abstracts, open content, or content whose
licence and provider terms permit it.

### 4 Identity resolution and normalization

1. Resolve the paper to `sources.id` and molecules to canonical MeatCODE rows using InChIKey as the
   preferred chemical identity. Names, abbreviations, and CAS numbers are candidate signals, not
   authority on their own.
2. Unresolved or ambiguous entities remain flagged and cannot silently create a canonical edge.
3. Preserve source wording beside normalized forms. Convert units only through a deterministic,
   versioned rule with an unambiguous basis.
4. Never collapse apparently conflicting measurements. Store each observation with its own matrix,
   method, treatment, conditions, uncertainty, and source.

### 5 Checking and deterministic validation

An independent checker assigns the existing verdict set (`KEEP`, `KEEP_WITH_CONTEXT`,
`MERGE_WITH_EXISTING`, `GENERALIZE_AND_KEEP`, `REVISE`, `DROP`, `NEEDS_SOURCE_CHECK`). Admission
requires a positive checker verdict and all applicable mechanical checks:

- cited paper and locator exist;
- quoted evidence in the controlled batch actually entails the claim;
- every numeric raw value and raw unit occur in the cited span or table cell;
- direction, negation, comparator, treatment, and conditions agree with the source;
- foreign keys resolve; molecule identity is unambiguous;
- normalized values reproduce from the documented rule;
- JSON/schema constraints pass; duplicates are handled idempotently.

Raw, corrected, rejected, and admitted records remain distinguishable. A rerun never overwrites the
history of an earlier model, prompt, parser, or schema version.

### 6 Admission to Neon

Write one complete approved batch to the **dev Neon branch first**, inside transactions. A failed
batch leaves no partial production state. The intended mappings are:

| Evidence | Governed destination |
|---|---|
| Paper identity and bibliographic metadata | `sources` |
| Paper-to-molecule evidence | `source_molecules` with explicit provenance |
| Qualitative scientific statement | `claims` plus `claim_sources`, `claim_molecules`, and other join tables |
| Experiment/sample/treatment context | `experiments` and experiment join tables |
| Temperature, time, pH, water activity, oxygen, fat phase | `processes` |
| Per-source numeric molecular observation | `molecule_properties` |
| Audit decision and quarantine history | `source_audits` |

Only derived facts, normalized values, confidence, derivation type, and source locators enter Neon.
Exact passages may remain in the controlled batch workspace for internal checking but do not enter
the public-serving database. Any missing destination field requires a numbered migration applied to
both Neon branches; do not hide overflow in an opaque JSON blob merely to avoid schema review.

### 7 Indexing and retrieval

1. Keep the current Postgres FTS path (`sources.search_vec`, relevance gate, ranked retrieval) as the
   measured baseline.
2. Add claim-level search and, if justified, pgvector behind a retrieval interface so the Oracle API
   and citation contract do not depend on a particular index.
3. Build the knowledge graph as a projection from approved Neon rows. LightRAG or Neo4j may be tested
   as retrievers or projections; they must not become an independent authority for scientific facts.
4. Store only representations allowed by the rights policy. A system that requires persistent
   publisher passages is not eligible for production until rights are resolved.

### 8 Serving, citation, and knowledge gaps

The API may return an admitted claim or value only with its source identity and locator. Retrieval
failure and missing conditions must be represented explicitly; an LLM may not fill a scientific gap
and present it as corpus evidence. General model knowledge, if product policy allows it, must remain
uncited and clearly separate from source-backed output. The existing rule against fabricated
citations remains absolute.

### 9 Reprocessing and audit

- Every record carries or can be reconstructed from batch ID, source ID, file hash, parser version,
  extraction model/prompt version, schema version, checker, and validation report.
- New parser/model/schema versions create new batch outputs and a comparison report before replacing
  an admitted representation.
- The recurring source-audit loop continues independently. A later quarantine must suppress affected
  records from retrieval without deleting the underlying audit history.
- Backups cover Neon data and batch manifests. The retention and encryption policy for the controlled
  source vault still requires an owner decision.

## Initial 10-paper pilot

1. Select 10 high-relevance papers with known access class and useful tables/conditions.
2. Freeze the gold questions and manually annotate a small gold set of claims and numeric records.
3. Run GROBID, extraction, checking, validation, and dev admission as one versioned batch.
4. Review every admitted row for the pilot; do not extrapolate the acceptance rate from unchecked
   model output.
5. Re-run the existing RAG evaluation against groundedness 3.4, citation accuracy 4.8, coverage 4.1,
   and zero invented citations.
6. Scale to 30-50 papers only if the gates below pass and the human review workload is acceptable.

## Acceptance gates

| Gate | Required result for the pilot |
|---|---|
| Identity | 100% of processed files map to the intended `sources.id`; no ambiguous molecule is auto-canonicalized |
| Rights | 100% have an access class; no rights-limited full text leaves the approved boundary |
| Provenance | 100% of admitted records have source ID, precise locator, batch ID, derivation, and checker verdict |
| Numeric fidelity | 100% of admitted raw values/units reproduce from the cited controlled span; normalization is deterministic |
| Scientific review | At least 90% precision on the manually checked gold set; all high-severity direction, negation, identity, and unit errors corrected before admission |
| Retrieval safety | Zero invented citations; citation accuracy does not regress below 4.8/10 |
| Retrieval value | Groundedness or coverage improves materially on the fixed questions; report both even if the result is negative |
| Operations | A failed/repeated batch is idempotent, leaves no partial write, and can be traced or rolled back by batch |

The 90% precision threshold is an initial product gate, not a scientific claim about model quality.
The team should tighten it after the first adjudicated batch reveals error severity and review cost.

## Failure policy

| Failure | Required behavior |
|---|---|
| Missing or ambiguous rights | Exclude from hosted processing and production indexing |
| Parse/OCR failure | Quarantine the paper; never treat missing sections/tables as negative evidence |
| Invalid model output | Retain the failure report; rerun only under recorded configuration; no partial admission |
| Unresolved chemical identity | Keep as a review candidate; do not invent a PubChem CID or InChIKey |
| Conflicting studies | Preserve separate condition-bound observations; do not average or choose a winner automatically |
| Database write failure | Roll back the transaction and mark the batch failed |
| Later source quarantine | Remove from retrieval through governance flags while preserving provenance and audit history |

## Evidence still missing

The architecture can be implemented, but these inputs are required before the pilot is execution-ready:

1. Daniel/legal's decision on publisher mining, local retention, permitted quotation length, and
   whether rights-limited text may be sent to Anthropic/OpenAI or another hosted processor.
2. The exact 10 PDFs, their `sources.id` values, and their access classes.
3. A live schema export or verified column contract for `experiments`, `processes`, and the relevant
   join tables; the repository contains current row counts but not the complete original DDL.
4. The gold annotations and named scientific reviewer for claim, identity, condition, and numeric
   adjudication.
5. Measured GROBID quality on tables, captions, equations, and scanned pages in this exact sample.
6. Selection of the extraction model and evidence that its local/hosted deployment meets rights,
   latency, cost, and structured-output requirements.
7. Retention, encryption, backup, and deletion rules for the controlled local source vault and
   batch-local evidence passages.
8. A batch identifier/write-back mechanism in Neon if existing tables cannot trace admission and
   rollback at batch granularity; this may require a numbered migration.

## Definition of done

The **architecture decision is complete** when Lior accepts this record as the v1 design. The
**pipeline implementation is complete** only after the 10-paper pilot passes the acceptance gates,
its results are documented, and any schema migration is applied to both Neon branches. These are
separate milestones and must not be reported as the same thing.

