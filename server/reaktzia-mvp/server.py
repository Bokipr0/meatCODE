"""Reaktzia MVP — FastAPI proxy that wires the mockup to Claude + Neon.

Run locally:
    uvicorn server:app --reload --host 127.0.0.1 --port 8000

Endpoints:
    GET  /api/health              — sanity check (DB + key presence)
    POST /api/ask                 — streams an Oracle answer (SSE)
    GET  /api/papers/{id}         — single paper (for the detail modal)
    GET  /api/papers/recent       — recent papers (for the dashboard)

Reads ANTHROPIC_API_KEY and DATABASE_URL from .env in this folder, or
falls back to the Claude Database/.env one level up.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import AsyncIterator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import anthropic

# ── env loading: try ./.env then ../.env ─────────────────────────────────────
HERE = Path(__file__).resolve().parent
for candidate in (HERE / ".env", HERE.parent / ".env"):
    if candidate.is_file():
        load_dotenv(candidate, override=False)
        print(f"[reaktzia] loaded env from {candidate}", file=sys.stderr)
        break

if not os.environ.get("ANTHROPIC_API_KEY"):
    print("[reaktzia] WARNING: ANTHROPIC_API_KEY not set — /api/ask will 500",
          file=sys.stderr)
if not os.environ.get("DATABASE_URL"):
    print("[reaktzia] WARNING: DATABASE_URL not set — DB calls will fail",
          file=sys.stderr)

# ── local imports (after env load so they can read env at import time) ───────
from retrieval import retrieve, fetch_paper, recent_papers, db_health
from prompts import ORACLE_SYSTEM, build_user_message

# ── app + CORS ───────────────────────────────────────────────────────────────
app = FastAPI(title="Reaktzia MVP", version="0.1.0")

# CORS: allow file:// and any localhost port, plus null origin (file:// in some browsers)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # demo-only; we're on localhost
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── default Claude model (overrideable via env or per-request) ───────────────
DEFAULT_MODEL = os.environ.get("REAKTZIA_MODEL", "claude-sonnet-4-6")
DEFAULT_MAX_TOKENS = int(os.environ.get("REAKTZIA_MAX_TOKENS", "600"))


# ───────── /api/health ─────────
@app.get("/api/health")
def health():
    out = {"ok": True, "model": DEFAULT_MODEL}
    out["has_anthropic_key"] = bool(os.environ.get("ANTHROPIC_API_KEY"))
    try:
        out.update(db_health())
        out["db_ok"] = True
    except Exception as e:
        out["db_ok"] = False
        out["db_error"] = str(e)[:200]
    return out


# ───────── /api/papers/{id} ─────────
@app.get("/api/papers/{paper_id}")
def get_paper(paper_id: int):
    try:
        row = fetch_paper(paper_id)
    except Exception as e:
        raise HTTPException(503, f"database unavailable: {e}")
    if not row:
        raise HTTPException(404, "paper not found")
    return row


# ───────── /api/papers/recent ─────────
@app.get("/api/papers/recent")
def get_recent(limit: int = 6):
    try:
        return recent_papers(limit=max(1, min(20, limit)))
    except Exception as e:
        raise HTTPException(503, f"database unavailable: {e}")


# ───────── /api/ask ─────────
class AskBody(BaseModel):
    question: str
    k: int = 5
    model: str | None = None


@app.post("/api/ask")
def ask(body: AskBody):
    """Streams an Oracle answer.

    The wire format is Server-Sent Events. Three event types:
      - event: chunk     data: <text>          (a piece of the answer)
      - event: sources   data: <json array>    (the chunks we retrieved)
      - event: done      data: {}              (terminator)
      - event: error     data: <message>       (on failure)
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise HTTPException(500, "ANTHROPIC_API_KEY is not configured on the server")

    # 1) retrieval (synchronous, fast)
    try:
        chunks = retrieve(body.question, k=body.k)
    except Exception as e:
        raise HTTPException(503, f"retrieval failed: {e}")

    # 2) build the prompt
    user_message = build_user_message(body.question, chunks)
    model = body.model or DEFAULT_MODEL

    # 3) stream from Claude
    client = anthropic.Anthropic()

    def event_stream() -> AsyncIterator[bytes]:
        try:
            # Emit the sources up front so the UI can show citation chips
            # progressively as the answer streams.
            yield _sse("sources", json.dumps([
                {
                    "id":      c["id"],
                    "title":   c["title"],
                    "year":    c.get("year"),
                    "journal": c.get("journal"),
                    "score":   c.get("score"),
                }
                for c in chunks
            ]))

            with client.messages.stream(
                model=model,
                max_tokens=DEFAULT_MAX_TOKENS,
                system=ORACLE_SYSTEM,
                messages=[{"role": "user", "content": user_message}],
            ) as stream:
                for text in stream.text_stream:
                    yield _sse("chunk", text)

            yield _sse("done", "{}")
        except Exception as e:
            yield _sse("error", str(e)[:400])

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # nginx-friendly; harmless elsewhere
        },
    )


# ── SSE helpers ──────────────────────────────────────────────────────────────
def _sse(event: str, data: str) -> bytes:
    """Format one SSE message. Splits multi-line data into multiple data: lines."""
    lines = data.split("\n")
    body = "\n".join(f"data: {ln}" for ln in lines)
    return f"event: {event}\n{body}\n\n".encode("utf-8")


# ── A friendly root ──────────────────────────────────────────────────────────
@app.get("/")
def root():
    return JSONResponse({
        "name": "Reaktzia MVP",
        "endpoints": [
            "GET  /api/health",
            "POST /api/ask",
            "GET  /api/papers/{id}",
            "GET  /api/papers/recent",
        ],
        "docs": "/docs",
    })
