#!/bin/bash
# Reaktzia MVP — one-click launcher. Double-click in Finder to start the server.
set -u
cd "$(dirname "$0")"

echo "================================================================"
echo " Reaktzia MVP server"
echo " Working dir: $(pwd)"
echo "================================================================"
echo

# 0) make sure pip deps are installed
if ! python3 -c "import fastapi, uvicorn, anthropic, psycopg2" 2>/dev/null; then
    echo "── installing Python dependencies (one-time) ───────────────────"
    python3 -m pip install --break-system-packages -r requirements.txt
    echo
fi

echo "── starting uvicorn on http://127.0.0.1:8000 ───────────────────"
echo "   /api/health   — sanity check"
echo "   /docs         — interactive API explorer"
echo
echo "   Press Ctrl+C to stop."
echo

python3 -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload

echo
read -p "Server stopped. Press Enter to close this window..."
