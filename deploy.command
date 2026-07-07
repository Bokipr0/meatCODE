#!/bin/bash
# ============================================================================
# deploy.command — publish MeatCODE to the live public site.
# ----------------------------------------------------------------------------
# Double-click on your Mac when you want your latest work to go live.
# It commits your changes and pushes to GitHub; Render rebuilds and updates
# the public site automatically (~1-2 min). The public URL never changes.
# ============================================================================
set -o pipefail
cd "$(dirname "$0")" || exit 1     # = meatCODE/ repo root

# Clear a stale git lock left behind by an interrupted process (safe when no
# other git command is running — which is the case for a double-click).
if [ -f .git/index.lock ]; then
  echo "Clearing a stale git lock…"
  rm -f .git/index.lock
fi

MSG="${1:-deploy $(date '+%Y-%m-%d %H:%M')}"

echo "Publishing MeatCODE…"
if ! git add -A; then
  echo "git add failed."; read -p "Press Enter to close."; exit 1
fi

COMMITTED="no"
if git diff --cached --quiet; then
  echo "No local changes to commit."
else
  if git commit -q -m "$MSG"; then COMMITTED="yes"; echo "Committed: $MSG"; fi
fi

echo "Pushing to GitHub…"
PUSH_OUT="$(git push origin HEAD 2>&1)"; PUSH_CODE=$?
echo "$PUSH_OUT"

if [ "$PUSH_CODE" -ne 0 ]; then
  echo ""
  echo "❌  Push failed. If a GitHub sign-in prompt appeared, complete it and run this again."
  read -p "Press Enter to close."
  exit 1
fi

if [ "$COMMITTED" = "no" ] && echo "$PUSH_OUT" | grep -qi "up-to-date"; then
  echo ""
  echo "ℹ️  Nothing new since the last deploy — the live site is already current."
else
  echo ""
  echo "==================================================================="
  echo "  ✅  Published. Render is rebuilding the live site (~1-2 min)."
  echo "      The public URL stays the same; refresh it once it finishes."
  echo "==================================================================="
fi
read -p "Press Enter to close."
