#!/bin/bash
# Last updated: 2026-10-18 10:05 UTC · Codex / RAG · import existing graph into Neon dev, then run Oracle locally.
set -euo pipefail
TASK_REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$TASK_REPO"
printf '%s\n' 'Importing the extracted LightRAG graph and its existing embeddings into Neon DEV.'
printf '%s\n' 'This adds dedicated demo tables; existing scientific records are preserved.'
python3 pipeline/import_lightrag_demo.py --workspace /Users/lior/LightRAG --env-file .env.dev --apply
printf '%s\n' 'Import verified. Starting the local Oracle with graph retrieval enabled.'
printf '%s\n' 'Open http://localhost:8000/app/meatcode_mockup.html and use the Oracle.'
printf '%s\n' 'Graph status: http://localhost:8000/api/kg-demo/status'
APP_ENV=dev ORACLE_GRAPH_DEMO=1 RELEASE_CENTER=1 python3 server/meatcode_server.py
