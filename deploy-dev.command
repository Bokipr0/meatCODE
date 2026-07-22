#!/bin/bash
# ============================================================================
# deploy-dev.command — publish your work to the PRIVATE staging site.
# ----------------------------------------------------------------------------
# Double-click when you want to try your changes on the real hosted dev server
# (meatcode-dev on Render, password-protected). It commits your work and pushes
# the 'dev' branch; Render rebuilds the staging site (~1-2 min).
# This does NOT touch the public site. That's what promote-to-prod is for.
# ============================================================================
set -o pipefail
cd "$(dirname "$0")" || exit 1            # = meatCODE/ repo root
[ -f .git/index.lock ] && { echo "Clearing a stale git lock…"; rm -f .git/index.lock; }

DEV="dev"
CUR="$(git rev-parse --abbrev-ref HEAD 2>/dev/null)"
if [ "$CUR" != "$DEV" ]; then
  echo "You're on '$CUR', not '$DEV'. Switching to '$DEV' (your files stay as they are)…"
  if ! git checkout "$DEV" 2>/dev/null; then
    echo "❌ Couldn't switch to '$DEV'. Run setup-dev-branch.command first, then retry."
    read -p "Press Enter to close."; exit 1
  fi
fi

MSG="${1:-dev $(date '+%Y-%m-%d %H:%M')}"
git add -A
if git diff --cached --quiet; then
  echo "No new changes since your last staging deploy."
else
  git commit -q -m "$MSG" && echo "Saved: $MSG"
fi

echo "Pushing to staging ('$DEV')…"
OUT="$(git push origin "$DEV" 2>&1)"; CODE=$?
echo "$OUT"
if [ "$CODE" -ne 0 ]; then
  echo ""
  echo "❌  Push failed. If a GitHub sign-in appeared, finish it and run this again."
  read -p "Press Enter to close."; exit 1
fi

echo ""
echo "==================================================================="
echo "  ✅  Staging is updating (~1-2 min). Open your meatcode-dev URL"
echo "      (the password-protected one) and check it before promoting."
echo "==================================================================="
read -p "Press Enter to close."
