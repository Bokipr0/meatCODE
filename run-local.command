#!/bin/bash
# ============================================================================
# run-local.command — preview your work on YOUR Mac, instantly, for free.
# ----------------------------------------------------------------------------
# Runs the MeatCODE server locally at http://localhost:8000 using your DEV
# settings (dev database + dev key), so nothing you do here can affect the
# public site or real data. This is your fastest edit → see-it loop.
# Stop it with Ctrl+C in the Terminal window.
# ============================================================================
set -o pipefail
cd "$(dirname "$0")" || exit 1            # = meatCODE/ repo root

# First run: make a .env.dev for you to fill in (it is gitignored — never committed).
if [ ! -f .env.dev ]; then
  cat > .env.dev <<'EOF'
# LOCAL DEV ONLY — never commit this (it is gitignored).
# run-local.command loads this so local runs use your DEV database + DEV key.
APP_ENV=dev
ANTHROPIC_API_KEY=
DATABASE_URL=
EOF
  echo "Created .env.dev — paste your DEV Anthropic key and DEV Neon URL into it, then run this again."
  echo "(Opening it for you…)"
  open -e .env.dev 2>/dev/null
  read -p "Press Enter to close."; exit 0
fi

echo "Starting MeatCODE DEV on http://localhost:8000  —  Ctrl+C to stop."
echo "(Using .env.dev → your dev database. Nothing here touches the live site.)"
# open the browser a moment after the server boots
( sleep 2; open "http://localhost:8000/app/meatcode_mockup.html" 2>/dev/null ) &
APP_ENV=dev python3 server/meatcode_server.py
