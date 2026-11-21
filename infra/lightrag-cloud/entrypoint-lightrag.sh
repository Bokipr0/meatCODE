#!/bin/sh
# Last updated: 2026-11-21 21:34 UTC · Claude (Sonnet 5.5) · auth-required entrypoint with verified seeding
# Refuses to start unauthenticated. Seeds an EMPTY disk from a verified baseline archive.
set -eu
[ -n "${LIGHTRAG_API_KEY:-}" ] || { echo "FATAL: LIGHTRAG_API_KEY is required" >&2; exit 1; }
[ "${#LIGHTRAG_API_KEY}" -ge 32 ] || { echo "FATAL: LIGHTRAG_API_KEY must be >=32 chars" >&2; exit 1; }
mkdir -p "$WORKING_DIR" "$INPUT_DIR"
if [ -z "$(ls -A "$WORKING_DIR" 2>/dev/null)" ]; then
  if [ -n "${SEED_ARCHIVE_URL:-}" ]; then
    [ -n "${SEED_ARCHIVE_SHA256:-}" ] || { echo "FATAL: SEED_ARCHIVE_SHA256 required with SEED_ARCHIVE_URL" >&2; exit 1; }
    echo "Seeding empty workspace from baseline archive..."
    curl -fsSL "$SEED_ARCHIVE_URL" -o /tmp/seed.tgz
    echo "$SEED_ARCHIVE_SHA256  /tmp/seed.tgz" | sha256sum -c -
    tar -xzf /tmp/seed.tgz -C "$WORKING_DIR"
    rm -f /tmp/seed.tgz
    touch "$WORKING_DIR/.seeded-from-baseline"
  else
    echo "Workspace empty and no SEED_ARCHIVE_URL: starting a fresh, empty graph."
  fi
else
  echo "Workspace already populated: not seeding (disk is authoritative)."
fi
exec lightrag-server
