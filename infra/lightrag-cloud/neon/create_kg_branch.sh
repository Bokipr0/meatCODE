#!/bin/sh
# Last updated: 2026-11-21 21:34 UTC · Claude (Sonnet 5.5) · Neon KG branch script
# Creates the isolated Neon KG branch + least-privilege role for Phase 4 (Neon-backed LightRAG).
# Prereq: NEON_API_KEY in the environment (neonctl reads it) or `neon login`. None exists on this machine yet.
# Usage: NEON_PROJECT_ID=<id> PARENT_BRANCH=<dev branch name> ./create_kg_branch.sh
# Branches copy data from the parent: the parent MUST be the development scientific branch
# (never production). The KG tables are additive in their own schema and never touch scientific tables.
set -eu
: "${NEON_PROJECT_ID:?set NEON_PROJECT_ID}" "${PARENT_BRANCH:?set PARENT_BRANCH (development, not production)}"
case "$PARENT_BRANCH" in *prod*|main) echo "refusing: parent looks like production" >&2; exit 1;; esac
npx --yes neonctl@latest branches create --project-id "$NEON_PROJECT_ID" --name kg-lightrag --parent "$PARENT_BRANCH"
echo "Next: psql \"\$(npx neonctl connection-string kg-lightrag --project-id $NEON_PROJECT_ID)\" -v kg_pw=\"<generated>\" -f init_kg.sql"
