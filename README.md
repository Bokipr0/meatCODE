# MeatCODE

**Open Meaty Flavor & Aroma Initiative — GFI Israel.**

MeatCODE is a pre-competitive knowledge and collaboration platform that helps the alternative-meat
sector solve one of its hardest sensory barriers: *meaty flavor and aroma.* The core hypothesis is
that compelling meaty flavor should be engineered primarily as **process flavor** — the
cooking-generated chemistry that emerges from the right interaction of precursors, lipids, matrix,
and heat — and translated into plant-based, cultivated, and hybrid systems.

The product surface spans **Map** (worldwide expert & organization network), **Oracle** (RAG chatbot
grounded in a curated literature corpus), **Research** (molecular & mechanistic database), a
**Protocol Library**, and an aroma **Prediction** surface.

## For agents and contributors
Start with **[`CLAUDE.md`](./CLAUDE.md)** (operating protocol + the three-homes model), then
**[`PROJECT_STATE.md`](./PROJECT_STATE.md)** (current technical status). The short version:

- **Code, docs, mockup, SQL** live in this git repo — the single source of truth.
- **Structured data** (literature, molecules, experts, protocols) lives in **Neon Postgres**.
- 
Pull and read `PROJECT_STATE.md` first; update it and commit/push last. That discipline keeps every
session — human or agent — automatically current.

## Quick start
```bash
cp .env.example .env        # fill in ANTHROPIC_API_KEY, DATABASE_URL, etc.

# Thin demo server (no DB required):
python server/meatcode_server.py

# Full RAG backend (FastAPI + Neon):
cd server/reaktzia-mvp && pip install -r requirements.txt && ./run_server.command

# Open the product mockup:
open app/meatcode_mockup.html
```

## Status
2026 is the **validation year**, not launch. Current focus (Phase 1): building the minimum credible
version of the knowledge hub — the foundational lift is collecting the first 1,000–2,000 high-value
literature sources.

---
_Owner/supervisor: Daniel Dikovsky (GFI IL). Author/core execution: Lior Teper._
