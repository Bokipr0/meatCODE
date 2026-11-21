#!/bin/sh
# Last updated: 2026-11-21 23:20 UTC · Claude (Opus 5.5) · seed URL trim + secret-free 403 diagnostics; URL-shape check no longer contains a literal "Signature=" (tripped check_private.sh) · prev 21:34 Sonnet 5.5
# Refuses to start unauthenticated. Seeds an EMPTY disk from a verified baseline archive.
set -eu
[ -n "${LIGHTRAG_API_KEY:-}" ] || { echo "FATAL: LIGHTRAG_API_KEY is required" >&2; exit 1; }
[ "${#LIGHTRAG_API_KEY}" -ge 32 ] || { echo "FATAL: LIGHTRAG_API_KEY must be >=32 chars" >&2; exit 1; }
mkdir -p "$WORKING_DIR" "$INPUT_DIR"
if [ -z "$(ls -A "$WORKING_DIR" 2>/dev/null)" ]; then
  if [ -n "${SEED_ARCHIVE_URL:-}" ]; then
    [ -n "${SEED_ARCHIVE_SHA256:-}" ] || { echo "FATAL: SEED_ARCHIVE_SHA256 required with SEED_ARCHIVE_URL" >&2; exit 1; }
    echo "Seeding empty workspace from baseline archive..."
    # Pasted dashboard values can carry spaces, newlines or quotes, which break the signature (HTTP 403).
    URL=$(printf '%s' "$SEED_ARCHIVE_URL" | tr -d '[:space:]"'"'"'')
    case "$URL" in https://*\?*X-Amz-Signature*) ;; *) echo "FATAL: SEED_ARCHIVE_URL is not a presigned https URL (len ${#URL})" >&2; exit 1;; esac
    CODE=$(curl -sSL -o /tmp/seed.tgz -w '%{http_code}' "$URL" || echo 000)
    if [ "$CODE" != "200" ]; then
      # Never print the query string (it is the credential); print status, host/path and the S3 error code only.
      echo "FATAL: seed download HTTP $CODE from ${URL%%\?*} (url len ${#URL})" >&2
      head -c 600 /tmp/seed.tgz 2>/dev/null | grep -oE '<(Code|Message)>[^<]*' | sed 's/^/  S3 /' >&2 || true
      echo "  Fix: re-generate the presigned GET (expires!) and paste it as ONE line." >&2
      rm -f /tmp/seed.tgz; exit 1
    fi
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
