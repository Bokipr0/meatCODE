#!/bin/bash
# ============================================================================
# setup-dev-branch.command — ONE-TIME. Creates your private 'dev' branch.
# ----------------------------------------------------------------------------
# Double-click once. It creates a 'dev' branch (a safe place to work that never
# touches the live site), pushes it to GitHub, and switches you onto it.
# After this, point the Render "meatcode-dev" service at the 'dev' branch.
# ============================================================================
set -o pipefail
cd "$(dirname "$0")" || exit 1            # = meatCODE/ repo root
[ -f .git/index.lock ] && { echo "Clearing a stale git lock…"; rm -f .git/index.lock; }

DEV="dev"; PROD="main"

echo "Setting up your '$DEV' branch…"
git fetch origin --quiet 2>/dev/null

if git show-ref --verify --quiet "refs/heads/$DEV"; then
  echo "You already have a local '$DEV' branch."
else
  git branch "$DEV" "$PROD" 2>/dev/null || git branch "$DEV"
  echo "Created '$DEV' from '$PROD'."
fi

git checkout "$DEV" || { echo "❌ Could not switch to '$DEV'."; read -p "Press Enter to close."; exit 1; }

echo "Pushing '$DEV' to GitHub…"
OUT="$(git push -u origin "$DEV" 2>&1)"; CODE=$?
echo "$OUT"
if [ "$CODE" -ne 0 ]; then
  echo ""
  echo "❌  Push failed. If a GitHub sign-in appeared, finish it and run this again."
  read -p "Press Enter to close."; exit 1
fi

echo ""
echo "==================================================================="
echo "  ✅  Done. GitHub now has a '$DEV' branch."
echo "      NEXT: in Render, create the meatcode-dev service pointed at '$DEV'."
echo "      You are now ON '$DEV' — do all your work here, then promote."
echo "==================================================================="
read -p "Press Enter to close."
