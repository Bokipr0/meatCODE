#!/bin/bash
# ============================================================================
# rollback-prod.command — undo: put the PUBLIC site back to an earlier release.
# ----------------------------------------------------------------------------
# Double-click if a promotion caused a problem. It lists your recent live
# snapshots (each promotion is tagged prod-YYYYMMDD-HHMM), lets you pick one,
# and makes the public site that version again. Render redeploys (~1-2 min).
# Your 'dev' branch is untouched — fix things there, then promote again.
# ============================================================================
set -o pipefail
# Always work on the real repo, wherever this file is double-clicked from.
# If you ever MOVE the meatCODE folder, update this one path.
REPO="/Users/lior/Documents/Claude/Projects/Claude Database/meatCODE"
[ -d "$REPO/.git" ] || REPO="$(dirname "$0")"
cd "$REPO" || exit 1            # = meatCODE/ repo root
[ -f .git/index.lock ] && { echo "Clearing a stale git lock…"; rm -f .git/index.lock; }

PROD="main"
git fetch origin --tags --quiet 2>/dev/null

# collect prod-* snapshots, newest first
TAGS=()
while IFS= read -r t; do [ -n "$t" ] && TAGS+=("$t"); done < <(git tag --list 'prod-*' --sort=-creatordate)

if [ "${#TAGS[@]}" -eq 0 ]; then
  echo "No live snapshots found yet (they're created each time you promote)."
  read -p "Press Enter to close."; exit 0
fi

echo "Recent live snapshots (newest first):"
i=1; for t in "${TAGS[@]:0:8}"; do echo "   $i) $t"; i=$((i+1)); done
DEFAULT="${TAGS[1]:-${TAGS[0]}}"          # the one BEFORE the latest = the usual "undo"
echo ""
read -p "Roll back to which number?  (Enter = the previous one, $DEFAULT): " N

if [ -z "$N" ]; then
  TARGET="$DEFAULT"
else
  TARGET="${TAGS[$((N-1))]}"
fi
if [ -z "$TARGET" ]; then echo "That wasn't a valid choice."; read -p "Press Enter to close."; exit 1; fi

echo ""
echo "About to make the LIVE public site =  $TARGET"
read -p "Type  yes  to roll back: " OK
if [ "$OK" != "yes" ]; then echo "Cancelled — nothing changed."; read -p "Press Enter to close."; exit 0; fi

OUT="$(git push origin "${TARGET}^{commit}:$PROD" --force-with-lease 2>&1)"; CODE=$?
echo "$OUT"
if [ "$CODE" -ne 0 ]; then
  echo "❌  Rollback failed — the live site was NOT changed. (Someone may have just pushed to '$PROD'.)"
  read -p "Press Enter to close."; exit 1
fi

echo ""
echo "==================================================================="
echo "  ✅  Rolled back. Render is redeploying $TARGET (~1-2 min)."
echo "      Fix things on 'dev', then promote-to-prod when ready."
echo "==================================================================="
read -p "Press Enter to close."
