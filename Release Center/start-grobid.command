#!/bin/bash
# Last updated: 2026-10-20 · Codex / Full-Stack · start the local Docker GROBID API.
set -euo pipefail
TASK_REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$TASK_REPO"
docker compose -f pipeline/grobid/compose.yaml up -d --wait --wait-timeout 240
printf '%s\n' 'GROBID is ready at http://localhost:8070'
open http://localhost:8070
