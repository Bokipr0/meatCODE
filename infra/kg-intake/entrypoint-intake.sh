#!/bin/sh
# Last updated: 2026-11-21 23:55 UTC · Claude (Opus 5.5) · fail-closed start + one-time overlap inventory seed (kv_store_full_docs.json only)
set -eu
for v in INTAKE_API_KEY LIGHTRAG_API_KEY; do
  eval "val=\${$v:-}"; [ "${#val}" -ge 32 ] || { echo "FATAL: $v missing or shorter than 32 chars" >&2; exit 1; }
done
[ -n "${ANTHROPIC_API_KEY:-}" ] || { echo "FATAL: ANTHROPIC_API_KEY required (claim extraction)" >&2; exit 1; }
INV=/data/graph/kv_store_full_docs.json
mkdir -p /data/graph
if [ ! -s "$INV" ]; then
  if [ -n "${SEED_ARCHIVE_URL:-}" ]; then
    URL=$(printf '%s' "$SEED_ARCHIVE_URL" | tr -d '[:space:]"'"'"'')
    CODE=$(curl -sSL -o /tmp/seed.tgz -w '%{http_code}' "$URL" || echo 000)
    if [ "$CODE" != "200" ]; then
      echo "WARN: inventory seed HTTP $CODE from ${URL%%\?*} (len ${#URL}); worker stays paused (fail closed)" >&2
      head -c 600 /tmp/seed.tgz 2>/dev/null | grep -oE '<(Code|Message)>[^<]*' >&2 || true
    else
      echo "${SEED_ARCHIVE_SHA256:?}  /tmp/seed.tgz" | sha256sum -c - && tar -xzf /tmp/seed.tgz -C /data/graph kv_store_full_docs.json
    fi
    rm -f /tmp/seed.tgz
  else
    echo "WARN: no overlap inventory and no SEED_ARCHIVE_URL; worker stays paused (fail closed)" >&2
  fi
fi
exec python3 /app/intake/intake_server.py
