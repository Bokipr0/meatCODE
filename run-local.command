#!/bin/bash
# ============================================================================
# run-local.command — preview your work on YOUR Mac at http://localhost:8000.
# Uses your dev settings; nothing here can affect the public site. Ctrl+C to stop.
# ============================================================================
set -o pipefail
# Always work on the real repo, wherever this file is double-clicked from.
REPO="/Users/lior/Documents/Claude/Projects/Claude Database/meatCODE"
[ -d "$REPO/.git" ] || REPO="$(dirname "$0")"
cd "$REPO" || exit 1

# Optional local overrides (dev DB, etc.). Your .env already provides the API key,
# so .env.dev is created COMMENTED — a blank key line here would wipe the real one.
if [ ! -f .env.dev ]; then
  printf '# LOCAL DEV ONLY — never commit.\n# Uncomment + fill to point local dev at your DEV database:\n# DATABASE_URL=postgresql://...your-dev-branch...\n' > .env.dev
fi

echo "Starting MeatCODE DEV on http://localhost:8000  —  Ctrl+C to stop."
( sleep 2; open "http://localhost:8000/app/meatcode_mockup.html" 2>/dev/null ) &
APP_ENV=dev python3 server/meatcode_server.py
