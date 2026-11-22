#!/bin/bash
# Last updated: 2026-11-21 22:10 UTC · Claude (Opus 5.5) · privacy gate before any commit/push (repo is PUBLIC)
# Usage (from repo root, before committing):  bash infra/lightrag-cloud/check_private.sh
# Checks the files git would commit (staged + untracked-not-ignored) for secrets and private data.
# Exit 1 = do NOT commit. Prints file names only, never the secret values.
set -uo pipefail
cd "$(git rev-parse --show-toplevel)"
files=$( { git diff --cached --name-only --diff-filter=ACM; git ls-files --others --exclude-standard; } | sort -u)
bad=0
# 1) forbidden paths
echo "$files" | grep -E '(^|/)\.env($|\.)|^data/|\.tar\.gz$|\.tgz$|rag_storage|render-paste|seed_.*url|kg_audit|\.pem$|\.key$' \
  | grep -vE '\.example$|^data/\.gitkeep$' && { echo "^ forbidden path(s)"; bad=1; }
# 2) secret values inside files: generic patterns (regex) + the live values from local .env files (fixed strings)
re='X-Amz-Signature=|nak_live_|sk-ant-[A-Za-z0-9_-]{20,}|rnd_[A-Za-z0-9]{20,}|napi_[A-Za-z0-9]{20,}'
live=$(mktemp); trap 'rm -f "$live"' EXIT
ER="${CHECK_PRIVATE_ENV_ROOT:-.}"   # where the real .env files live (a temp worktree has none)
for f in "$ER/infra/lightrag-cloud/.env.kg" "$ER/infra/lightrag-cloud/.env.intake" "$ER/infra/lightrag-cloud/.env.embed" "$ER/infra/lightrag-cloud/.env.cloud" "$ER/.env" "$ER/.env.dev"; do
  [ -f "$f" ] && grep -E '^[A-Z_]*(KEY|SECRET|PASSWORD|TOKEN|DATABASE_URL[A-Z_]*)=' "$f" | cut -d= -f2- | awk 'length($0)>=20' >> "$live"
done
while IFS= read -r f; do [ -f "$f" ] || continue
  [ "$f" = infra/lightrag-cloud/check_private.sh ] && continue   # contains the patterns themselves
  if grep -qIE "$re" "$f" 2>/dev/null || { [ -s "$live" ] && grep -qIFf "$live" "$f" 2>/dev/null; }; then
    echo "secret-like value in: $f"; bad=1; fi
done <<< "$files"
[ $bad -eq 0 ] && echo "OK: nothing private in the files git would commit." || { echo "BLOCKED: fix the above before committing."; exit 1; }
