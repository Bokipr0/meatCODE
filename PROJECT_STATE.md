# PROJECT_STATE — MeatCODE

## 2026-10-29 · LIVE release — Clarity/PostHog and private testing dashboard

User explicitly authorized redeploy/update and separately approved enabling the private administrator dashboard. Published the reviewed changes from a clean checkout, preserving newer Science/Ecosystem/guided Oracle and original local work. Both dev and production now run20acea3e648e0e3feba40845cae3936951867b07; verified /api/version, user_testing+analytics flags, healthy startup and protected research routes401 without site login. Staging deploydep-dbhkm9h9q7ns73d280qg and productiondep-dbhkn5vb9u1s73a0nsv0 are live. Rollback tagprod-20261029-analytics-live-testing. No new production ERROR/Traceback logs found after deployment.

Public PostHog settings, USER_RESEARCH_ENABLED=true and distinct RESEARCH_ADMIN_TOKEN values are configured on both Render services; admin values remain only in secure Render settings and ignored local .env/.env.dev, never chat/Git. Dashboard /research-dashboard requires normal site login plus the corresponding administrator value retrieved privately from Render Environment. Local Release Center administrators retain token-free local access. No site password or Anthropic key was changed.

Fifty offline checks passed (five database-only skips); actual staging HTML browser privacy suite passed. Prior real local SDK delivery is queryable in PostHog; first-party HTTP→Neon capture/deletion checks passed and probes removed. Protected hosted-page checks require the user's signed-in browser: user initially did not see the privacy control before final production deployment; fresh production opt-in confirmation requested. Actual hosted Microsoft recordings and successful live Oracle model call remain unverified. Health labels key/database checks configuration-only. Do not claim a valid model credential from key presence.

Correction: Render environment-update API operations themselves triggered redeploys of then-current source; prior notes saying no deploy was triggered were inaccurate. Missing Clarity source was resolved by publishing the new Git commit, not by those earlier old-source redeploys. Local original checkout remains intentionally untouched/stale; do not blanket-push it over the clean published release. Credential-free verification is under data/verification/research-deployment-2026-10-29.json and research-hosted-public-checks-2026-10-29.json.


_Last updated: 2026-10-29 · Codex / Project Coordinator · PostHog setup, native dashboard and private live view._

## 2026-10-29 · PostHog and live research dashboard — local code, configured accounts

- **Native dashboard exists:** https://eu.posthog.com/project/325792/dashboard/1066277 (private MeatCODE Live Testing), six validated saved insights. EU project325792, latest official vendored posthog-js1.442.0, public runtime settings saved to original prod and dev Render services with merge-only updates. No app deployment was triggered.
- **Local dashboard/API ready:** /research-dashboard, three-second refresh over real Neon; admin-only data beyond shared site password, local loopback cockpit exception, no analytics SDK on admin page, no-store/read-only/bounded SQL and hash session labels. Hosted RESEARCH_ADMIN_TOKEN has not been generated/configured; hosted private reads remain closed.
- **Data migration live:** forward0017 applied DEV then PROD for fresh explicit2026-10-29 consent; historical consents remain unchanged. Five private research tables/scientific schema preserved. Backend45-test production suite passed; client privacy/dashboard fixtures passed. Independent actual local HTTP→dev Neon capture/feed/deletion/late-write410/cross-origin403/cleanup passed. Provider fixture tests are not delivery evidence.
- **Clarity exact cause:** both hosted services still run6394c039749a; that source lacks wrapper, routes and research flag. October28 manual redeploy reused older source. Public tag200 is reachable only, not installed/recording. Publish reconciled source; waiting does not install code.
- **Oracle status caution:** invalid-key logs were Oct28 at12:39 UTC; production manual deploy at16:36 UTC happened later. Latest model success remains unverified; do not present old401 as a fresh failure.
- **Real SDK delivery QA:** one consented local dev session sent session.started + scene.viewed to EU ingestion; two HTTP200 responses, zero page errors, Clarity blocked, no model/private content or Neon fixture. QA-only automation-detection override; production SDK unchanged. Forced dashboard refresh now confirms one session.started event; hostedcapture remains unverified.
- **Publication:** combined Oct29 package under platform_docs/user_research_2026-10-29 preserves newer remote Science/Ecosystem/guided Oracle and all previous research/UI guards; clean patch reapplication matches bytes. Local checkout is stale; avoid wholesale publish. ROLES/CLAUDE/team skill reserve Git and publication for Lior. Current guide: platform_docs/POSTHOG_LIVE_TESTING.md. No model call, private-key copy or code publication by agents.


_Last updated: 2026-10-28 15:58 UTC · Codex / Coordinator · isolated user research schema live; Clarity code local; production credential rejected._

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

## Current verification — 2026-10-28

- **Original production Oracle still rejects its configured key.** Fresh28 October12:39 UTC guided-decision/answer logs return 401 invalid x-api-key. Production/dev use the same 6394c039749a and model, with separate environment credentials. User confirmed changing dev only. A valid key must be saved/deployed on original MeatCODE srv-d96ftplaeets73da7vng and tested with a real signed-in answer. Presence in health is not model access. Source now makes Render environment authoritative over dotenv and labels health configuration-only; unpublished, no credential changed.
- **Research storage is live:** additive migration0016 created isolated user_research schema on both Neon branches (five tables, 12 indexes, no PUBLIC grants), preserving scientific tables. Rollback tests and independent schema verification passed; all research/test rows are zero after cleanup.
- **Clarity integration is local, not hosted:** supplied project z4upnrbddu; explicit opt-in, whole-body masking, advertising denied, metadata-only events, submitted first-party feedback and deletion controls. No prompts/answers/attachments/account identities in events. Existing scientific download excludes research data; static private exports blocked. Actual local HTTP→dev Neon persistence, deduplication, deletion and late-write rejection verified. Local server restarted.
- **Operations and limits:** private JSONL export, manual90-day cleanup and server-token dashboard aggregate import provided. No scheduler or real Microsoft export/recording test; no token configured. Shared Clarity project aggregates cover both domains; they are not production-filtered records or raw replay copies. Feedback is separate from scientific evidence/model training.
- **Publication package:** platform_docs/user_research_2026-10-28/README.md and USER_RESEARCH_CLARITY.md. Combined current-main patch preserves newer Science/Ecosystem/guided Oracle and prior Oct27 fixes. Reconcile stale checkout; Lior publishes through Release Center. No Git/commit/deploy or key mutation by agents.

## Current verification — 2026-10-27

**2026-10-28 clarification:** Lior confirmed the service updated was **dev-meatCODE** at meatcode.onrender.com. This resolves the service-identity question; it does not establish that original production received the key change. Render still returns original production's latest deploy as dep-dbg8rgd9fdbs73d4bnj0 (2026-10-27 11:41:48UTC), with no newer deploy as of this check. Direct repair to original **MeatCODE**, srv-d96ftplaeets73da7vng, at meatcode-oracle.onrender.com: set a valid ANTHROPIC_API_KEY through Render, save/deploy, then verify an authenticated Oracle answer. No key read/copied/changed or deployment triggered by agent.

**Dev follow-up:** user-observed staging answer is supported by11:53UTC request/generated-answer follow-up logs; same commit/model as production. Credential/config difference is the current lead. User says already deployed; no newer original-production deployment returned after12:41Zurich, so service identity is being clarified.

- **Production build is live; Oracle answers are broken.** Original MeatCODE `srv-d96ftplaeets73da7vng` at meatcode-oracle.onrender.com runs main/`6394c039749a`, model `claude-sonnet-4-6`. User's updated-key manual deployment `dep-dbg8rgd9fdbs73d4bnj0` went live11:41:48UTC. Signed-in test then failed; matching guided-decision/answer logs at11:43:09/13UTC show **401 authentication_error invalid x-api-key** on the new instance. Fresh valid key + deployed environment + successful actual request still needed. Health only checks configured strings, not model authentication or DB connectivity.
- **Local changes ready, not published:** Simulate's three requested sidebar sections removed; Analytics nav follows the canonical Analytics zone switch (explicit OFF overrides legacy ON); Release Center distinguishes saved settings from observed production build/switch state. Local server restarted with the changes at localhost:8000. Analytics remains a labelled demo/illustrative workspace.
- **Publication requires reconciliation:** remote main has newer Science/Ecosystem/guided Oracle code absent from this checkout. Main-safe narrow patches, visual proof and verification: `platform_docs/release_fixes_2026-10-27/README.md`. Both patches applied together and syntax checks passed against inspected remote snapshots. Do not publish the stale local checkout wholesale. Lior owns normal dev→staging→production publication.
- **Separate Yochai resource:** `meatcode-oracle-0o99.onrender.com` remains a distinct missing-ANTHROPIC_API_KEY startup failure; do not confuse it with original production's rejected key. Local Oracle key also returned401; local retrieval itself returned sources.

The following older deployment/feature tables are historical snapshots; they do not establish today's live commit, key validity or feature visibility. Asana remains authoritative for task priorities.

## 1. Historical production baseline — verified 2026-10-11

At that historical check, production ran **`prod-20260921-1717`** (commit `c563d16`), started **2026-09-21**, model `claude-sonnet-4-6`, password gate on. `/api/health` → db ok, key present.

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

## 2. Historical dev-only snapshot — recheck before promotion 🟡

| Commit | Date | What |
|---|---|---|
| `4635fa9` | 2026-09-21 | **Backups** topbar button (flag `backup_center`) |
| `881f3a1` | 2026-10-05 | **Papers browser** — browse/filter/export all 818 papers, Unpaywall open-access links (flag `papers_browser`) · `platform_docs/RAG_BUILD_VS_BUY.md` |

Both are flag-gated, so promoting changes nothing visible on prod until a flag's `prod` is flipped.

## 3. In the repo, not yet committed 📄

_2026-10-26 · Advisory: simplified adaptive architecture to nine objects/two flows in
`platform_docs/diagrams/meatcode-adaptive-simple.svg` (PNG preview), with matching one-page
`platform_docs/ADAPTIVE_ORACLE_SIMPLE.pdf` and editable Markdown. Supersedes the expanded visual
for review; earlier files preserved. Design only._

_2026-10-26 · Codex / Advisory: added editable adaptive-memory architecture SVG/PNG under
`platform_docs/diagrams/meatcode-adaptive-architecture.*` and verified one-page
`platform_docs/ADAPTIVE_ORACLE_ONE_PAGE.pdf` with editable Markdown source. Proposed user-scoped
SQL memory/optional vector lookup remains separate from scientific evidence. Documentation only._

_2026-10-26 12:57 UTC · Codex / Advisory: Render now connected. Failed resource is separate
`meatcode-oracle` / srv-dbf5eb5g1s2s73ei0td0 at meatcode-oracle-0o99.onrender.com (main,
Starter, Oregon). Original production is MeatCODE at meatcode-oracle.onrender.com and is live
on 6394c039749a. New resource build passes; startup exits1 because ANTHROPIC_API_KEY is not set.
Reuse this resource for Yochai after key/database/site-gate provisioning; no new server needed.
It still follows main, so an independent branch/env track remains to configure consistently with
its Blueprint. Diagnosis doc updated; no deployment/settings/secret changes made._

_2026-10-26 12:45 UTC · Codex / Advisory: added `platform_docs/ARCHITECTURE_EXPANDED_VALIDATION.md`,
working design v0.1 expanding Lior’s clean-arrows map. Records user-described local-PC Qwen M1,
separates M2 model from human review and deterministic checks, and specifies proposed candidate
contracts, supervised-learning loop, selective automation and publication/retrieval boundaries.
Includes three Mermaid diagrams. Design only; exact M2 variant, thresholds and training schedule
remain open pending Lior’s further requirements. No runtime, data, schema or deployment change._

_2026-10-26 12:42 UTC · Codex / Advisory: investigated screenshot of failed main-linked Render Blueprint.
Public production still responds on main/6394c039749a. Remote main includes newer Yochai
Science/Ecosystem changes absent from this local checkout; no Git sync performed. Screenshot
service identity and exact error remain unconfirmed: Render connection/sign-in needed for logs.
Prepared `platform_docs/YOCHAI_DEPLOYMENT_DIAGNOSIS.md` and inactive sandbox YAML under
`platform_docs/deployment_templates/`, recommending independent service/branch/database credentials.
No deployment, production settings, permissions, credentials or code changed._

_2026-10-26 12:33 UTC · Codex / Advisory: current internal reference pack at
`platform_docs/reference_pack_2026-10-26/` (entry: READ_ME_FIRST.md), plus ZIP in platform_docs.
Live production now reports main/6394c039749a, Claude Sonnet 4.6, password gate on; older release
statements below remain historical. Read-only Neon: production 49 base tables/16 views, dev 56/16;
818 sources, 799 molecule rows, 3,129 experts, 45 claims, 3,650 properties. Dev demo remains the
3-document frozen import (3,418 entities/4,164 relations/7,582 vectors), while local LightRAG now
has 5,101 nodes/6,240 edges. Added one-pager, actual UI screenshot, current architecture/schema
visuals and full inspected schema metadata with curated source docs. No model/benchmark run,
production retrieval audit, Git/deployment or data changes. Docker not restarted._

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
