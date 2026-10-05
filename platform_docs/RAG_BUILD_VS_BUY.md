# Build or buy the RAG? — decision memo

_2026-10-05 · Lior Teper · prepared for the 7 Oct knowledge-machine plan · verified live against Neon_

**Verdict in one line: the question "custom or off-the-shelf" has no single answer, because the stack
has four layers and the right choice differs per layer. Buy the pipeline. Build the ontology.**

---

## 1. Where we actually are (live numbers, 5 Oct 2026)

Any build-vs-buy argument that starts from zero is wrong — a grounded RAG is already live.

| Already built | Status |
|---|---|
| Grounded retrieval | Postgres FTS (`ts_rank_cd` + `websearch_to_tsquery`) over `sources.search_vec`, gated `relevance_llm ≥ 60`, SSE streaming, citing real source IDs |
| **Measured RAG baseline** | groundedness **3.4** · citation accuracy **4.8** · coverage **4.1** (/10) · **zero invented citations** over 8 closed-corpus questions |
| Corpus | **818** sources, 769 with DOI, 790 abstracts, 319 above the relevance gate |
| Molecule identity | **798** molecules · **590** InChIKey-canonical via PubChem · 568 CAS · ambiguity flagged, never guessed |
| Sensory layer | **2,263** molecule↔odour links over 785 molecules |
| Measurement-event table | `molecule_properties` — **3,650** rows, with `derivation`, `uncertainty`, `conditions` jsonb, `source_location`, `confidence` |
| Access analysis | **384 open access (46.9%)** · 387 paid · 349 on ScienceDirect |

**And the hole, stated honestly:**

| Gap | Rows |
|---|---|
| `source_molecules` — paper ↔ molecule | **23** (against 818 papers) |
| `experiments` · `processes` · `matrix_profiles` | **0 · 0 · 0** |
| `molecule_properties` rows citing a paper | **0** (all 3,650 cite PubChem/RDKit or the Meaty Volatile Library) |

That is precisely what an extraction pipeline fills. Nothing else in the stack is missing.

---

## 2. The four layers

| # | Layer | Decision | Why |
|---|---|---|---|
| 1 | PDF → structured text | **BUY — GROBID** | Solved, open source, best-in-class. No reason to touch this. |
| 2 | Chunking · embedding · vector store | **BUY — SPECTER2 / BGE-M3 + pgvector** | Commodity. pgvector keeps it inside the Postgres we already run. |
| 3 | **Extraction schema · entity resolution · validation** | **BUILD** | This is the entire scientific value. See §3. |
| 4 | Retrieval + answering | **BUY the framework, keep our grounding rules** | Already working and measured. |

So: roughly 75% bought, 25% built — and the 25% is the part nobody can sell us.

---

## 3. Why layer 3 cannot be bought

Prof. Ram's suggested relation set is `STUDIES · USES_METHOD · REPORTS_EFFECT · SUPPORTS · CONTRADICTS · CITES`.

These are **bibliometric** relations: they describe what a *paper* does. They cannot express the unit
our science runs on:

> hexanal · 6.4 ± 0.7 µg/g · pea-protein formulation B · 160 °C · 10 min · HS-SPME-GC-MS ·
> Table 3, row Hexanal, column Treatment B · DOI 10.xxxx

`REPORTS_EFFECT` discards the temperature, the unit, the uncertainty and the matrix. But the central
MeatCODE thesis is that **apparent contradictions between papers are condition-dependent, not
errors** — cysteine helps at one pH and does nothing at another. Strip the conditions and that thesis
is unrepresentable.

Concretely, generic graph-RAG answers *"which papers study Maillard chemistry in pea protein?"* —
a question Google Scholar already answers. It does not answer *"at what temperature does hexanal
formation plateau, and who measured it?"* — the question that justifies the project.

**Second reason: chemical identity.** No general framework resolves "(E,Z)-3,6-nonadien-1-ol" and
"3-methylindole (skatole)" to the same canonical entity. We do, via PubChem → InChIKey, with
ambiguity flagged rather than guessed. An LLM asked to do this invents CIDs.

---

## 4. Option comparison

| Option | Strength | Cost / risk for us | Verdict |
|---|---|---|---|
| **LightRAG** (Ram's primary) | Lightweight, fast to stand up, own backend, graph-aware retrieval | Generic relations (§3); **stores full-text chunks by default** → creates the publisher problem we don't currently have; schema not chemistry-aware | **Adopt the pattern, not the storage.** Good reference design for the offline/token-time split. |
| **Microsoft GraphRAG** | Most established; strong on corpus-wide "what themes exist" questions | Expensive indexing; community-summary output is the opposite of per-measurement traceability | No. Optimised for a question type we don't have. |
| **Neo4j GraphRAG** | Inspectable graph, custom schema, built for human curation | A second source of truth beside Neon + a sync surface; our KG MVP already projects a graph from Postgres joins | Not yet. Revisit if routine ≥3-hop traversal appears. |
| **LlamaIndex Property Graph** | Custom Python pipeline, flexible | Flexibility we'd have to fill in ourselves anyway | Equivalent to building, with a dependency. |
| **GROBID + our schema + pgvector** | Chemistry-aware; conditions mandatory; provenance per value; nothing new to sync | We own the extraction prompt and validation | **Recommended.** |

---

## 5. Two corrections to the proposal as summarised

**5.1 — The publisher gate is already designed out, not pending.**
Our architecture stores a *derived value + a span locator + `source_id`* and never the source text
(`molecule_properties.value_num` / `source_location` / `source_id`). The Elsevier TDM 200-character
limit and the ~150-character Israeli provision are satisfied **by construction**. LightRAG's default
behaviour — storing full-text chunks — would introduce that exposure. So the gate is a reason to keep
our storage model, not a reason to delay ingestion.

**5.2 — Cost is an order of magnitude lower than the headline.**
The 9–18M-token figure assumes full-text embedding of 1,000 papers. Our staged plan — title+abstract
across the corpus, full text on **30–50** manually tagged papers — lands at roughly **250–500k tokens**
for the embedding pass. Prof. Ram's own staged suggestion agrees. Budget is not the constraint;
**human review capacity is** (current agreed batch: 10 papers).

---

## 6. Recommended plan

1. **GROBID in Docker**, locally — PDFs → TEI XML. Offline, zero per-token cost.
2. **Deterministic pass first** — quantity parser (value ± uncertainty + unit) and chemical NER.
3. **LLM for semantic interpretation only** — bind value↔molecule↔condition. NULL when unsupported.
4. **PubChem → InChIKey** resolution. New molecules land `id_needs_review = true`.
5. **Mechanical validation** before insert — does the number appear in the span? the unit? is it
   nearer this molecule than another?
6. **Write into the existing tables** — `molecule_properties`, `processes`, `experiments`, keyed on
   the real `source_id` via DOI. Everything already reading Neon (Oracle, KG builder, Compare) sees
   it with no integration work.
7. **10-paper human check** with a review sheet showing each record beside its source sentence.
8. **Re-run the RAG eval** against the 3.4 / 4.8 / 4.1 baseline. That is the proof.

**The measurable claim this plan makes:** extracting 10–50 papers should move groundedness and
coverage measurably, because the Oracle will for the first time be able to cite a *number under a
condition* rather than a sentence from an abstract.

---

## 7. What we want from Prof. Ram

Not "is this a good architecture" — he already answered that, and the answer was sound. The open
questions are narrower and worth paying for:

1. Can LightRAG be made to emit a **domain-specific schema with mandatory condition fields**, or is
   that fighting the framework?
2. Has he seen generic graph-RAG **preserve numeric values with units and uncertainty**, or does it
   degrade to entity co-occurrence?
3. How does `CONTRADICTS` get decided in practice? Our own derived triplet layer produced
   **5,035 of 5,041 positive-polarity** claims — contradiction detection was structurally impossible
   without an explicit polarity field. Generic extractors may have the same blind spot.
4. At what corpus size does projecting a graph from Postgres stop being adequate versus a real
   graph database?
