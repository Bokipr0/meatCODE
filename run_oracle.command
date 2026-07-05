#!/bin/bash
# ============================================================================
# MeatCODE Oracle — run the live Claude-powered demo (run on YOUR Mac)
# Double-click this. It starts the local server and opens the mockup so the
# Oracle answers real questions via the Claude API.
#   Stop the server later with Ctrl+C in the Terminal window it opens.
# ============================================================================
cd "$(dirname "$0")" || exit 1   # = meatCODE/ repo root

# 1) Need the API key in meatCODE/.env
if [ ! -f .env ] || ! grep -qE '^ANTHROPIC_API_KEY=[[:space:]]*sk-' .env 2>/dev/null; then
  echo "⚠  No Anthropic key found."
  echo "   Create a file  meatCODE/.env  containing one line:"
  echo "       ANTHROPIC_API_KEY=sk-ant-...your key..."
  echo "   (copy .env.example to .env and paste your key), then run this again."
  read -p "Press Enter to close."
  exit 1
fi

# 2) Make sure the anthropic SDK is installed
python3 -c "import anthropic, psycopg2" 2>/dev/null || {
  echo "Installing dependencies (one-time): anthropic + psycopg2…"
  python3 -m pip install --user anthropic psycopg2-binary || pip3 install anthropic psycopg2-binary
}

# 3) Open the mockup once the server is up
( sleep 2; open "http://localhost:8000/app/meatcode_mockup.html" ) &

# 4) Start the server (Ctrl+C to stop)
echo "Starting MeatCODE Oracle server…  (Ctrl+C to stop)"
python3 server/meatcode_server.py
