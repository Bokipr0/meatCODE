#!/bin/bash
# ============================================================================
# release-center.command — opens your private Release Center (feature flags +
# deploy controls) at http://localhost:8000/app/release-center.html.
# Local-only admin cockpit. You can also press H inside the app. Ctrl+C to stop.
# ============================================================================
set -o pipefail
# Always work on the real repo, wherever this file is double-clicked from.
REPO="/Users/lior/Documents/Claude/Projects/Claude Database/meatCODE"
[ -d "$REPO/.git" ] || REPO="$(dirname "$0")"
cd "$REPO" || exit 1

# Optional local overrides (dev DB, etc.). Created COMMENTED so a blank key line
# can never wipe the real ANTHROPIC_API_KEY your .env already provides.
if [ ! -f .env.dev ]; then
  printf '# LOCAL DEV ONLY — never commit.\n# Uncomment + fill to point local dev at your DEV database:\n# DATABASE_URL=postgresql://...your-dev-branch...\n' > .env.dev
fi

# Reuse a healthy existing local cockpit instead of starting a second server.
if python3 - <<'CHECK_COCKPIT'
import json,urllib.request
try:
    with urllib.request.urlopen('http://127.0.0.1:8000/api/flags/all',timeout=2) as response:
        assert json.load(response).get('admin') is True
except Exception:
    raise SystemExit(1)
CHECK_COCKPIT
then
  echo "The local Release Center is already running. Opening its controls…"
  open "http://localhost:8000/app/release-center.html"
  exit 0
fi

echo "Opening the MeatCODE Release Center…"
echo "  http://localhost:8000/app/release-center.html"
echo "  (Admin cockpit — local only. You can also press H inside the app. Ctrl+C to stop.)"
( sleep 2; open "http://localhost:8000/app/release-center.html" 2>/dev/null ) &
APP_ENV=dev RELEASE_CENTER=1 python3 server/meatcode_server.py
