#!/bin/bash
# ============================================================================
# MeatCODE — sync to GitHub (run from YOUR Mac, not from inside a Claude session)
# Double-click this whenever you want to push the latest state of this folder
# to github.com/Bokipr0/meatCODE. Safe to run as often as you like.
#
# First run also repairs the half-initialized .git that a Claude sandbox left
# behind (it can't manage git on the mounted folder — only your Mac can).
# ============================================================================
set -uo pipefail
cd "$HOME/Documents/Claude/Projects/Claude Database/meatCODE" || { echo "folder not found"; exit 1; }

REMOTE="https://github.com/Bokipr0/meatCODE.git"

# One-time repair: if a stale/locked .git from the sandbox is present, reset it clean.
if [ -f .git/HEAD.lock ] || [ ! -d .git ]; then
  echo "==> Repairing / initializing git in a clean state"
  rm -rf .git
  git init -q
  git branch -M main
  git remote add origin "$REMOTE" 2>/dev/null || git remote set-url origin "$REMOTE"
fi

# Make sure remote is set (in case .git already existed but had no origin)
git remote get-url origin >/dev/null 2>&1 || git remote add origin "$REMOTE"

MSG="${1:-sync $(date '+%Y-%m-%d %H:%M')}"
git add -A
if git diff --cached --quiet; then
  echo "==> Nothing new to commit."
else
  git commit -q -m "$MSG" && echo "==> Committed: $MSG"
fi

echo "==> Pushing to $REMOTE (you may be asked to sign in to GitHub the first time)"
git push -u origin main && echo "==> Done. GitHub is up to date." || {
  echo ""
  echo "Push failed. Most likely you just need to authenticate once:"
  echo "  - If a browser/credential prompt appears, complete it and re-run."
  echo "  - Or set up a Personal Access Token / 'gh auth login' once, then re-run."
}
