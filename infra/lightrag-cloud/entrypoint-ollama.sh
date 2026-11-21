#!/bin/sh
# Last updated: 2026-11-21 21:34 UTC · Claude (Sonnet 5.5) · bge-m3 entrypoint
set -eu
mkdir -p "$OLLAMA_MODELS"
ollama serve &
PID=$!
for i in $(seq 1 60); do ollama list >/dev/null 2>&1 && break; sleep 1; done
ollama list | grep -q '^bge-m3' || ollama pull bge-m3:latest
echo "bge-m3 ready"
wait $PID
