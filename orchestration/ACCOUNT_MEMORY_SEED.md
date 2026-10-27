HOW TO USE: in the ORG account → Settings → Memory → Import → paste everything below the line → submit.
Curated from the personal account on 2026-10-11: MeatCODE/GFI work only. Personal items (TAU courses,
Zurich exchange, job applications, diet, hobbies) are deliberately left out. Stale entries (Airtable-rag repo,
April sprint, the pre-July "no retrieval" Oracle) were dropped or corrected. No secrets.

---

ABOUT ME (work context)
- I'm Lior Teper. I build MeatCODE at GFI Israel; my supervisor and MeatCODE co-owner is Daniel Dikovsky (GFI IL Head of SciTech, danield@gfi.org). Yochai Maytal is a collaborator.
- I prefer concise, practical answers; rigorous reasoning over recipes; methodological weaknesses named, not passed through.
- Act as my standing technology/innovation advisory board for MeatCODE (technology only — not legal, marketing or finance), and as Art Director / UI-UX designer for the product. Push back on scope creep.
- Before non-trivial creative builds, ask me 3–4 multiple-choice questions to align, then iterate piece by piece on my notes.
- Daniel prefers DOCX, professional-but-warm tone, 1-page weekly summaries (completed / in progress-needs input), light colour theme.

WHAT MEATCODE IS
- MeatCODE = Meat Collaborative Open Development Ecosystem: an open, pre-competitive GFI IL SciTech platform turning fragmented meaty-flavour science into shared knowledge, tools and R&D directions for alternative meat.
- Thesis: meaty flavour is an integrated process-flavour system (Maillard + lipid oxidation), not one missing molecule.
- 2026 is the VALIDATION year, not launch. Top risk: building the full vision too early.
- Scope is beef-only for now. Public project launch moved to end of Oct 2026; MVP to a closed group of ~50 testers by end of 2026.
- Go-to-market: data holders first (academia, flavour houses such as Givaudan/IFF). Audience ceiling ~1,000 users → minimal DevOps spend.
- Ecosystem interest: Wageningen (WUR — proposed GC-MS "Volatile Atlas" module), Masha Niv, FSI.

WHERE THINGS LIVE (three homes)
- Code, docs, mockup, SQL, project status → git repo github.com/Bokipr0/meatCODE, local working tree ~/Documents/Claude/Projects/Claude Database/meatCODE. Start every session by reading meatCODE/CLAUDE.md, then PROJECT_STATE.md, MVP_BOARD.md and TEAM_BROADCAST.md.
- Structured data → Neon Postgres (production + dev branches). Query live; never cache data into the repo.
- Tasks → Asana project "MeatCODE – Open Flavor & Aroma Initiative".
- The Cowork sandbox cannot run git on the mounted folder; I push from my Mac with the .command scripts.
- After every change, log it in meatCODE/AGENT_UPDATE_LOG.md and update PROJECT_STATE.md.

PLATFORM STATE (as of Oct 2026)
- Live on its own domain behind credentials, with separate dev and production servers (git dev → main; deploy-dev.command / promote-to-prod.command / rollback-prod.command). Feature flags in "Release Center/features.json"; a Dev Area holds work-in-progress screens.
- Oracle = grounded RAG: Postgres full-text over sources.search_vec, gated relevance_llm ≥ 60, citing real source IDs, streamed over SSE. Measured baseline: groundedness 3.4, citation accuracy 4.8, coverage 4.1 (/10), zero invented citations.
- Data: 818 sources (all tagged, one main_claim each), 798 molecules (590 with InChIKey via PubChem, 568 CAS), 3,129 experts, 2,263 molecule–odour links. molecule_properties holds per-value provenance (derivation, uncertainty, conditions, source).
- Biggest gap: only 23 paper↔molecule links; experiments/processes tables are empty. Next step is offline extraction: GROBID → measurement events written into the existing tables, keyed on DOI and InChIKey, starting with a 10-paper open-access pilot.
- Prof. Yoav Ram (TAU) proposed GROBID → LightRAG. My position: buy the pipeline (GROBID, embeddings, pgvector), build the chemistry-specific schema; store derived facts + span locators, never publisher full text.
- Production runs the 2026-09-21 release (prod-20260921-1717); the old 'B1 deploy the backlog' item is done. Still open: B2 — 4 quarantined sources still pass the relevance gate, and the audit loop hasn't run since 2026-07-08. Live status is always in meatCODE/PROJECT_STATE.md and platform_docs/SYSTEM_SNAPSHOT.md.
- A Maillard chemistry simulator exists as a Docker prototype; it runs in mock mode in the platform (always labelled synthetic) because Render's python runtime can't run Docker.

DESIGN
- Product UI uses the GFI seaweed-teal palette (#00736E family; coral #C77E5F, olive #7A8C5F), Varela Round, pill buttons. Canonical mockup: meatCODE/app/meatcode_mockup.html. Placeholders must say they are placeholders.

RULES I CARE ABOUT
- Never fabricate chemistry or bibliographic data; unknowns stay NULL.
- Never print or paste secrets (ANTHROPIC_API_KEY, DATABASE_URL); .env files stay gitignored.
- Before dropping a DB column: count(col)=0, no dependent views, AND a repo grep shows no code reads it.
