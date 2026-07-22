#!/bin/bash
# ============================================================================
# promote-to-prod.command — "BRING IT TO THE AIR": put dev live for everyone.
# ----------------------------------------------------------------------------
# Double-click ONLY after you've checked your changes on staging and you're
# happy. It shows you exactly what will change on the public site, asks you to
# type "yes", then makes production identical to your validated dev build
# (dev → main). Render redeploys the public site (~1-2 min). Every promotion is
# tagged so rollback-prod.command can undo it in one click.
# You stay on the 'dev' branch the whole time.
# ============================================================================
set -o pipefail
cd "$(dirname "$0")" || exit 1            # = meatCODE/ repo root
[ -f .git/index.lock ] && { echo "Clearing a stale git lock…"; rm -f .git/index.lock; }

DEV="dev"; PROD="main"

# 1. make sure dev is fully saved and pushed
git add -A
if ! git diff --cached --quiet; then
  git commit -q -m "dev $(date '+%Y-%m-%d %H:%M') (saved before promoting)"
  echo "Saved your latest dev changes first."
fi
echo "Making sure staging is up to date…"
if ! git push origin "$DEV" --quiet 2>/dev/null; then
  echo "❌ Couldn't push '$DEV' to GitHub. Finish any sign-in and retry."
  read -p "Press Enter to close."; exit 1
fi
git fetch origin "$PROD" --quiet 2>/dev/null

# 2. show what will go live
COUNT="$(git rev-list --count "origin/$PROD..$DEV" 2>/dev/null || echo '?')"
if [ "$COUNT" = "0" ]; then
  echo ""
  echo "ℹ️  The public site is already identical to dev — nothing to promote."
  read -p "Press Enter to close."; exit 0
fi
echo ""
echo "=== Commits about to go LIVE ($COUNT): ==============================="
git log --oneline "origin/$PROD..$DEV" 2>/dev/null
echo ""
echo "=== Files that will change on the public site: ======================"
git diff --stat "origin/$PROD..$DEV" 2>/dev/null
echo "====================================================================="
echo ""

# 3. confirm
read -p "Type  yes  to put this LIVE for everyone (anything else cancels): " OK
if [ "$OK" != "yes" ]; then
  echo "Cancelled — the public site was NOT changed."
  read -p "Press Enter to close."; exit 0
fi

# 4. promote: fast-forward origin/main to the dev commit (no local main checkout needed)
echo "Promoting to production…"
OUT="$(git push origin "$DEV:$PROD" 2>&1)"; CODE=$?
echo "$OUT"
if [ "$CODE" -ne 0 ]; then
  echo ""
  echo "❌  Promotion was REJECTED and your live site was NOT changed."
  echo "    This usually means someone committed directly to '$PROD'."
  echo "    Don't force it — ask before overriding. (rollback-prod is unaffected.)"
  read -p "Press Enter to close."; exit 1
fi

# 5. tag this release for one-click rollback
TAG="prod-$(date '+%Y%m%d-%H%M')"
git tag "$TAG" "$DEV" 2>/dev/null && git push origin "$TAG" --quiet 2>/dev/null

echo ""
echo "==================================================================="
echo "  ✅  LIVE. Render is rebuilding the public site (~1-2 min)."
echo "      Snapshot tagged:  $TAG"
echo "      To undo: double-click rollback-prod.command."
echo "==================================================================="
read -p "Press Enter to close."
