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
set -eo pipefail
pause() { if [ "${RELEASE_CENTER_NONINTERACTIVE:-0}" != "1" ]; then read -r -p "Press Enter to close."; fi; }
# Always work on the real repo, wherever this file is double-clicked from.
# If you ever MOVE the meatCODE folder, update this one path.
REPO="/Users/lior/Documents/Claude/Projects/Claude Database/meatCODE"
[ -d "$REPO/.git" ] || REPO="$(dirname "$0")"
cd "$REPO" || exit 1            # = meatCODE/ repo root
if [ -f .git/index.lock ]; then
  echo "❌ Another Git operation may be active (.git/index.lock exists). Close it or inspect the lock before retrying."
  exit 1
fi

DEV="dev"; PROD="main"

# Check history before staging or committing anything. A rejected fast-forward
# is a sync problem, not automatically a GitHub sign-in problem.
if [ "$(git branch --show-current)" != "$DEV" ]; then
  echo "❌ Open deploy-dev.command first: promotion must run from the dev branch."
  pause; exit 1
fi
if ! git fetch origin "$DEV" "$PROD"; then
  echo "❌ Could not refresh GitHub history. See the connection error above."
  pause; exit 1
fi
if ! git merge-base --is-ancestor "origin/$DEV" "$DEV"; then
  echo "❌ Local dev is behind or diverged from GitHub. Reconcile the newer commits before publishing."
  echo "Your files have not been staged or committed by this attempt. Do not force-push."
  pause; exit 1
fi

# 1. make sure dev is fully saved and pushed
git add -A
if ! git diff --cached --quiet; then
  git commit -q -m "dev $(date '+%Y-%m-%d %H:%M') (saved before promoting)"
  echo "Saved your latest dev changes first."
fi
# An explicit deployment must not silently reuse a commit marked to skip Render.
if git log -1 --format=%B | grep -Eiq '\[(skip (render|deploy|cd)|((render|deploy|cd) skip))\]'; then
  git commit --allow-empty -q -m "Release current dev build $(date '+%Y-%m-%d %H:%M')"
  echo "Created a release marker so Render will build the requested version."
fi

echo "Making sure staging is up to date…"
if ! git push origin "$DEV"; then
  echo "❌ Could not push dev. The actual GitHub error is shown above; production was not changed."
  pause; exit 1
fi
git fetch origin "$PROD" --quiet 2>/dev/null

# 2. show what will go live
COUNT="$(git rev-list --count "origin/$PROD..$DEV" 2>/dev/null || echo '?')"
if [ "$COUNT" = "0" ]; then
  echo ""
  echo "ℹ️  The public site is already identical to dev — nothing to promote."
  pause; exit 0
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
if [ "${RELEASE_CENTER_NONINTERACTIVE:-0}" = "1" ]; then
  OK=yes # local HTTP handler already checked origin + explicit confirmation
else
  read -r -p "Type  yes  to put this LIVE for everyone (anything else cancels): " OK
fi
if [ "$OK" != "yes" ]; then
  echo "Cancelled — the public site was NOT changed."
  pause; exit 0
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
  pause; exit 1
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
pause
