#!/bin/bash
# ============================================================================
# share_oracle.command — put the MeatCODE Oracle on a PUBLIC link (temporary)
# ----------------------------------------------------------------------------
# Double-click this. It will:
#   1. make sure a tunnel tool (cloudflared) is installed,
#   2. start your local MeatCODE server on port 8000 if it isn't already,
#   3. open a free Cloudflare tunnel and print a public https link to share.
#
# The link works from ANY computer/phone — nobody needs to download anything.
# Keep this window OPEN while people use it. Press Ctrl+C to take it offline.
#
# NOTE: this needs your Mac ON and this window OPEN. For an always-on link that
# works even when your Mac is closed, use the Render deploy (see docs/DEPLOY.md).
#
# The free link is temporary and CHANGES each run. While live, anyone with the
# link can use the Oracle and spend your Anthropic credits — share it only with
# the people you want, and Ctrl+C to shut it down when the demo is over.
# ============================================================================
set -o pipefail                    # (intentionally no 'set -u')
cd "$(dirname "$0")" || exit 1     # = meatCODE/ repo root
PORT=8000
SERVER_PID=""
CF_PID=""

cleanup() {
  echo ""
  echo "Taking the public link down…"
  [ -n "$CF_PID" ] && kill "$CF_PID" 2>/dev/null
  [ -n "$SERVER_PID" ] && kill "$SERVER_PID" 2>/dev/null
  exit 0
}
trap cleanup INT TERM

# ── 1) find or install cloudflared ──────────────────────────────────────────
CF=""
if command -v cloudflared >/dev/null 2>&1; then
  CF="cloudflared"
elif [ -x "./cloudflared" ]; then
  CF="./cloudflared"
else
  echo "Installing the tunnel tool (one-time)…"
  if command -v brew >/dev/null 2>&1; then
    brew install cloudflared >/dev/null 2>&1 && CF="cloudflared"
  fi
  if [ -z "$CF" ]; then
    echo "Downloading cloudflared…"
    ARCH="amd64"
    [ "$(uname -m)" = "arm64" ] && ARCH="arm64"
    BASE="https://github.com/cloudflare/cloudflared/releases/latest/download"
    if curl -fL "$BASE/cloudflared-darwin-$ARCH.tgz" -o cf.tgz 2>/dev/null \
       || curl -fL "$BASE/cloudflared-darwin-amd64.tgz" -o cf.tgz 2>/dev/null; then
      tar -xzf cf.tgz 2>/dev/null && rm -f cf.tgz && chmod +x cloudflared && CF="./cloudflared"
    fi
  fi
fi

if [ -z "$CF" ]; then
  echo "Couldn't install cloudflared automatically."
  echo "Install Homebrew (https://brew.sh), then run:  brew install cloudflared"
  read -p "Press Enter to close."
  exit 1
fi

# ── 2) make sure the MeatCODE server is up on :$PORT ────────────────────────
if ! curl -s "http://localhost:$PORT/api/health" >/dev/null 2>&1; then
  echo "Starting the MeatCODE server on port $PORT…"
  python3 server/meatcode_server.py > /tmp/meatcode_server.log 2>&1 &
  SERVER_PID="$!"
  i=0
  while [ "$i" -lt 15 ]; do
    curl -s "http://localhost:$PORT/api/health" >/dev/null 2>&1 && break
    sleep 1
    i=$((i + 1))
  done
fi

# ── 3) open the public tunnel and print the shareable link ──────────────────
echo "Opening the public link…"
"$CF" tunnel --url "http://localhost:$PORT" > /tmp/cf_tunnel.log 2>&1 &
CF_PID="$!"

URL=""
i=0
while [ "$i" -lt 25 ]; do
  URL="$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' /tmp/cf_tunnel.log 2>/dev/null | head -1)"
  [ -n "$URL" ] && break
  sleep 1
  i=$((i + 1))
done

echo ""
if [ -n "$URL" ]; then
  echo "==================================================================="
  echo "  Your public MeatCODE Oracle is live. Share this link:"
  echo ""
  echo "      $URL/app/meatcode_mockup.html"
  echo ""
  echo "  - Works from any computer or phone — nothing to install."
  echo "  - Keep this window OPEN. Press Ctrl+C to take it offline."
  echo "==================================================================="
else
  echo "Tunnel is starting but no URL yet. Watch it with:"
  echo "    tail -f /tmp/cf_tunnel.log"
fi
echo ""
wait "$CF_PID"
