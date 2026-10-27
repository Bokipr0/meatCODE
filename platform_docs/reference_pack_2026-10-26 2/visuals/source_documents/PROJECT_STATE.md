# PROJECT_STATE — MeatCODE

_Last updated: 2026-10-20 21:33 UTC · Codex / Data · scanned PDF OCR and GROBID annotation recovery verified; other system figures retain their stated dates._

> Living technical status: **what's built, what's live, what's broken.** Short on purpose.
> Tasks and priorities → Asana (mirrored in `platform_docs/ASANA_SNAPSHOT.md`). History → `AGENT_UPDATE_LOG.md`.
> Decisions and why → `platform_docs/DECISIONS.md`. People → `platform_docs/PEOPLE.md`.

## How this file stays true

| Claim type | Verified against | Re-verified by |
|---|---|---|
| What's live on production | `https://meatcode-oracle.onrender.com/api/version` (commit) vs git tags | `SYSTEM_SNAPSHOT.md` → "What is live right now" |
| What's on dev only | `origin/main..dev` commit list | same |
| Data numbers | live Neon, both branches | `SYSTEM_SNAPSHOT.md` |
| Task status | Asana project 1215201551726181 | `ASANA_SNAPSHOT.md` (daily sync) |

Status key: ✅ **live on prod** · 🟡 **on dev only** (committed, not promoted) · 🚩 **on prod but flag OFF** · 📄 **in repo, not committed** · ❌ **open/broken**

---

## 1. Production — what reviewers can actually use (verified 2026-10-11)

Production runs **`prod-20260921-1717`** (commit `c563d16`), started **2026-09-21**, model `claude-sonnet-4-6`, password gate on. `/api/health` → db ok, key present.

| Capability | Status | Note |
|---|---|---|
| Grounded Oracle chat (multi-turn, SSE, real citations, consensus event, attach + dictation) | ✅ | Retrieval: Postgres FTS, `relevance_llm ≥ 60` gate. Prompt answers uncited gaps from general knowledge (decision 2026-07-20). |
| Research, Database (molecules · experts · companies), Map, molecule/protocol detail pages | ✅ | |
| Analytics scene, Oracle v11 design | ✅ | the only two flags ON in prod |
| `/api/corpus`, `/api/compare`, `/api/molecules/{id}`, `/api/reaction-network` | ✅ | code on prod |
| `/api/backup` (repo zip), `/api/data-backup` (full Neon data) | ✅ | behind the site password; **no button on prod** (flag `backup_center` OFF) |
| Maillard simulator (`/api/simulate`) | 🚩 | mock mode, flag `maillard_sim` OFF → 404 on prod. Real simulator needs a `runtime: docker` Render service (not created). |
| Research reaction-network wizard · Analytics bring-your-own-data workspace · Compare · KG explorer · Fingerprint · Dev Area · Versions | 🚩 | built and on prod, hidden behind flags (dev ON / prod OFF) |
| Migrations 0011–0014 (molecule properties, drops) | ✅ | applied to both Neon branches; code on prod |

**Correction to every older doc:** "B1 — deploy the backlog" (the critical path through August) is **done**. Promotions on 2026-08-31 and 2026-09-21 shipped it. Entries in the archive marked "awaiting deploy-dev" up to 2026-09-21 are live.

## 2. On dev only — waiting for `promote-to-prod.command` 🟡

| Commit | Date | What |
|---|---|---|
| `4635fa9` | 2026-09-21 | **Backups** topbar button (flag `backup_center`) |
| `881f3a1` | 2026-10-05 | **Papers browser** — browse/filter/export all 818 papers, Unpaywall open-access links (flag `papers_browser`) · `platform_docs/RAG_BUILD_VS_BUY.md` |

Both are flag-gated, so promoting changes nothing visible on prod until a flag's `prod` is flipped.

## 3. In the repo, not yet committed 📄

_2026-10-20 21:33 UTC · Codex / Data: GROBID annotation failure for `Meat Flavour - NAMQ2.pdf`
was caused by an image-only scan (41 pages, no text), not MCP health. Local OCR derivative
`Meat Flavour - NAMQ2 - searchable.pdf` saved in Downloads and ignored `data/grobid/ocr/`.
Full-text extraction and reference annotation both now return HTTP 200; TEI: 91 body paragraphs,
132 references. Original preserved; OCR accuracy not adjudicated; no LightRAG/Neon writes._

_2026-10-20 21:19 UTC · Codex / Data + Full-Stack: connected GROBID to the existing
Codex `MCP_DOCKER` gateway/profile `meatcode`, preserving Playwright. Local adapter:
`pipeline/grobid/mcp/`; three tools: status, PDF listing, PDF parsing. Exact read-only input bind:
`/Users/lior/LightRAG/inputs`; writable output: ignored `data/grobid/mcp/`. Config backed up;
startup timeout and scoped bind allowlists set. Actual gateway tool calls passed: healthy 0.8.2,
PDF listing and parsing to valid TEI (26 paragraphs, 62 refs) plus 22,096-character cleaned body.
Five unit tests passed. No Neon/LightRAG/production writes. Reload MCP or restart Codex to load
these tools into the current chat; setup instructions in `pipeline/grobid/mcp/README.md`._

_2026-10-20 21:03 UTC · Codex / Full-Stack: configured existing GROBID 0.8.2 Docker image as
`meatcode-grobid` at **http://localhost:8070** with loopback port binding and health check.
Two duplicate unexposed processes stopped; their containers preserved. Compose file:
`pipeline/grobid/compose.yaml`; launcher: `Release Center/start-grobid.command`; usage:
`pipeline/grobid/README.md`. Health/version passed; one local PDF parsed to valid 96,780-byte
TEI XML in 27.64s. Smoke files under ignored `data/grobid/`. No Neon/LightRAG/production changes.
Docker MCP Toolkit v0.43.3 confirmed installed; no MCP connection/configuration was changed._

_2026-10-20 20:54 UTC · Codex / Advisory: added `platform_docs/LIGHTRAG_CURATION_AND_SCALING.md`.
Current local files show 4 processed / 1 failed document status records, 206 chunks, 3,759 nodes
and 4,531 undirected edges (not a Neon refresh). Of the nodes, 1,687 are typed person; 122 of
141 person-linked chunks contain bibliography XML markers. Only 94 nodes and 2 edges have
evidence from multiple documents; this is a reuse diagnostic, not a complete connection-quality
metric. Recommend clean TEI section extraction, a separate bibliography network, canonical IDs,
individual condition-specific claims, measured M2 review, and bounded graph retrieval. Proposal
only; no graph, code, schema, deployment, score-cutoff policy or external system changed._

_2026-10-18 11:57 UTC · Codex / Design: cleaned the attached architecture picture’s connectors and handwritten annotations; saved `platform_docs/diagrams/MeatCODE-Architecture-Clean-Arrows.png` and a Downloads copy. Visual-only edit; system status unchanged._

_2026-10-18 11:48 UTC · Codex / Design: exported the current architecture overview as `platform_docs/diagrams/MeatCODE-Architecture-8K.png` (7680×4320); copy saved to Lior’s Downloads. Diagram content and system status unchanged._

_2026-10-18 10:14 UTC · Codex / Data-RAG-Design: at Lior’s explicit request, removed the
provisional relevance-score gate from local Oracle FTS, both eval runners, and Papers browser’s
Oracle-eligibility labels/filters. Applied additive migration **0015** to **Neon dev only** and
imported the existing LightRAG graph into `lightrag_demo`: **3 documents, 194 chunk metadata rows,
3,418 entities, 4,164 relations, 7,582 vector(1024) embeddings, 8,932 evidence links**. Original
BGE-M3 embeddings reused; raw chunk text and scientific source/property tables unchanged. Exact
DOI→source IDs 275/833/857; immutable batch `lightrag-0fea952f5db82becdc87501f`. Second import
returned `verified_existing`, with no duplicates. Local Oracle on `localhost:8000` now uses dev
vector/graph retrieval; authenticated dev `/api/kg-demo/status` and `/search` added. A semantic
query returned 15 evidence items from source 275 in `vector_graph` mode; `/api/ask` retrieved the
same evidence but Claude returned **401 invalid x-api-key**. Lior chose to keep Claude configured
and repair credentials; no Qwen/provider switch. Thirteen tests, compilation and JS syntax checks
pass. Live evidence saved under ignored `data/benchmarks/2026-10-18-pilot/`. Added minimal icon-led
overview SVG/PNG, detailed flow and interactive viewer under `platform_docs/diagrams/meatcode-rag-demo-*`.
Implementation, arrow contract and self-service instructions: `platform_docs/LIGHTRAG_DEMO_IMPLEMENTATION.md`;
import/start script: `Release Center/demo-lightrag.command`. Production, credentials, Asana and
Git/release state unchanged. Local code still needs publication through the normal dev workflow._

_2026-10-18 09:53 UTC · Codex / Advisory: revised the architecture visual into an icon-led,
low-text overview with no component-card borders and no benchmark panel. Connector routes were
moved away from icons and labels. Per Lior's correction, the protected artifact vault is labelled
as Neon storage; the earlier advisory local-vault recommendation is superseded in that respect.
Cloud storage of exact or publisher-controlled passages still requires explicit rights, retention,
access, backup, and deletion approval. No implementation or external system changed._

_2026-10-18 09:47 UTC · Codex / RAG: added `analysis/rag_eval/PROTOCOL.md`,
`benchmark.py` and `test_benchmark.py`: controlled direct/vector/graph and cross-model protocol,
ingestion/retrieval/answer metrics, proposed thresholds, results template, local inventory, frozen
smoke packet preparation and real Oracle SSE capture. Five tests pass; comparative runs, model
adapters, reviewed gold, import/schema and serving integration are not implemented. Local ignored
packet: `data/benchmarks/2026-10-18-pilot/`. LightRAG inspected read-only: 3 processed / 3 failed
documents, 194 chunks, 3,418 nodes, 4,164 edges, 1,024-dimensional vectors, no dangling graph chunk
references detected. Exact DOI matches to Neon dev sources **275/833/857** verified; relevance
**55/32/38**, so all three fail the existing Oracle ≥60 gate. A shared approved corpus is needed
before a fair controlled comparison. Neon dev inspected read-only: pgvector absent; 818 sources,
319 pass relevance. Latest Architecture chat and live benchmark task inspected. No schema, data,
deployment, extraction workspace or Asana changes; no paid model run._

_2026-10-18 09:43 UTC · Codex / Advisory: Lior selected the pilot model split: local Qwen
extraction (M1), local custom validation/curation plus deterministic checks (M2), and cloud-hosted
GPT reasoning over approved evidence (M3), with Neon authoritative and graph/vector layers derived.
Added `platform_docs/ENGINEERED_RAG_ARCHITECTURE.md` plus editable SVG and PNG under
`platform_docs/diagrams/`. The diagram separates controlled ingestion, governed knowledge,
interactive serving, and the apples-to-apples benchmark/scale gate. This is an architecture artifact,
not an implementation. No Asana, Neon, schema, deployment, production data, or external system changed._

_2026-10-18 08:56 UTC · Codex / Advisory: added
`platform_docs/LOCAL_CLOUD_HOSTING_DECISION.md` and the supporting
`reports/MeatCODE local cloud architecture.md`. The proposed hybrid v1 keeps Neon authoritative and
Render stateless, while rights-sensitive PDFs, GROBID, exact passages, and restricted extraction
remain local; retrieval and graph systems stay rebuildable projections. This is awaiting Lior and
Daniel/Yochai approval and is not implemented. No Asana task, Neon data, schema, deployment, or
external system changed._

_2026-10-17 20:42 UTC · Codex / Advisory: added
`platform_docs/DATA_PROCESSING_ARCHITECTURE.md`, a concrete governed batch design for local parsing,
parallel evidence extraction, identity resolution, checking, deterministic validation, dev-first
Neon admission, retrieval, audit and failure handling. The architecture recommendation is complete;
implementation still requires the 10-paper pilot and the evidence listed in that record. No schema,
database, deployment, production data, Asana task, or external system was changed._

_2026-10-17 12:29 UTC · Codex / Advisory: Lior confirmed continued use of `Bokipr0/meatCODE`.
Local checkout already points to that remote on `dev`. Folder/connection review recorded in
`platform_docs/GITHUB_READINESS.md`; no remote configuration, publication, or live-system changes.
The external-system status elsewhere in this file remains verified as of 2026-10-11._

The 2026-10-11 handoff + context-sync work: `START_HERE.md`, `platform_docs/{SYSTEMS_MAP,SYSTEM_SNAPSHOT,DECISIONS,PEOPLE,ASANA_SNAPSHOT}.md`, `orchestration/` (snapshot script, skills, setup guide, memory seed), meeting notes, this file. → Lior: `deploy-dev.command`.

## 4. Data layer (numbers: `SYSTEM_SNAPSHOT.md`)

- **Literature:** 818 sources, all tagged (pathway/method/matrix/compound class/sensory/study type), one `main_claim` each; **319** pass the Oracle gate. Tailored abstracts: 30.
- **Molecules:** 798 non-junk · 590 with InChIKey (PubChem) · 568 CAS · 3,650 provenanced property values (RDKit-derived + 110 literature odour thresholds) · 2,263 molecule↔odour links. **Precursor view (`v_precursors`) is empty.**
- **Experts:** 3,129 records; enrichment thin (`research_field` ~17).
- **The gap:** **23** paper↔molecule links; `experiments`, `processes`, `reaction_participants` = 0; no property value cites a paper yet.

## 5. Open problems ❌ (verified 2026-10-11)

1. **B2 — quarantine write-back.** 4 sources quarantined on 2026-07-07/08 (ids 252, 308, 341, 380) still have `relevance_llm` 62–75, so the Oracle can still cite them. And the data-quality audit loop **hasn't run since 2026-07-08** (40 sources audited of 818).
2. **Paper↔molecule bridge** (23 links) — blocks the knowledge graph, white-space map and condition-aware answers. Plan: 10-paper GROBID extraction pilot into the existing tables (`RAG_BUILD_VS_BUY.md`).
3. **RAG quality** — baseline groundedness **3.4** · citation accuracy **4.8** · coverage **4.1** /10 (8 questions, zero invented citations). No comparison vs generic AI tools yet (Asana task due 2026-11-06).
4. **Publisher rights unresolved** (Asana, Daniel, overdue 2026-10-08). Written position (Daniel, 2026-09-07): extract facts with provenance, never store/reproduce/share full text. Don't open external access to publisher-derived content until resolved.
5. **Single point of failure** — Neon, Render, GitHub and the Anthropic key all sit on Lior's logins (Yochai flagged 2026-09-20; Asana continuity task closed 2026-09-21 — confirm what access Daniel/Yochai actually have).
6. **Stale docs** — `MVP_BOARD.md` and `TEAM_BROADCAST.md` (1 Sep) still frame the end-of-August demo; superseded by this file + Asana.

## 6. What's next (from Asana + this audit)

Lior's 19 open Asana tasks and the evidence for each are in `ASANA_SNAPSHOT.md` §3. The highest-leverage items now:

1. **Close B2** — write quarantine verdicts to `relevance_llm` and re-run the audit loop (Data Engineer).
2. **Promote dev** (Papers browser + Backups button) once reviewed on staging.
3. **Choose tool stack** (overdue 2026-09-30) — the recommendation exists (`RAG_BUILD_VS_BUY.md`); needs Daniel/Yochai sign-off.
4. **10-paper extraction pilot** → re-run the RAG eval against 3.4 / 4.8 / 4.1.
5. **Prepare the 10–15 min architecture overview for Rebecca** (asked by Daniel, 2026-10-11).

## 7. Upcoming (from Gmail/Calendar, 2026-10-11)

- **2026-10-12 13:00** — Yochai meets Prof. Yoav Ram (TAU, Sherman 328); Lior invited. Ram hasn't replied to Lior's 2026-10-05 email.
- **Next 2 weeks** — Daniel scheduling: WUR simulator-validation meeting (Pablo, Prof. Fogliano, Bei Wang) and an AKA Foods Atlas pilot call.
- **Weekly Core Sync** — Sundays 12:30 (Yochai, Daniel; Lior optional).
