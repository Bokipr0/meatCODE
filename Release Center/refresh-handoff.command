#!/bin/bash
# ============================================================================
# refresh-handoff.command — ONE CLICK: bring the whole MeatCODE context up to date
# for a new Claude account, a new agent, or a new collaborator.
# ----------------------------------------------------------------------------
# 1. Regenerates platform_docs/SYSTEM_SNAPSHOT.md from LIVE Neon (prod + dev),
#    git, render.yaml, features.json and the server route table.
# 2. Re-packs every agent skill in orchestration/skills/ into an uploadable
#    .skill file in data/migration_kit/1_skills/ (gitignored).
# 3. Opens START_HERE.md so you can see the entry point.
# Writes NO secrets anywhere. Safe to run as often as you like.
# ============================================================================
REPO="/Users/lior/Documents/Claude/Projects/Claude Database/meatCODE"
[ -d "$REPO/.git" ] || REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO" || exit 1

echo "→ 1/3  Live system snapshot…"
python3 -c "import psycopg2" 2>/dev/null || pip3 install --quiet --user psycopg2-binary
python3 orchestration/build_system_snapshot.py || { echo "Snapshot failed."; read -n1 -p "Press any key…"; exit 1; }

echo "→ 2/3  Packing agent skills…"
mkdir -p data/migration_kit/1_skills
cd orchestration/skills || exit 1
for s in */; do
  s="${s%/}"
  rm -f "../../data/migration_kit/1_skills/$s.skill"
  zip -qr "../../data/migration_kit/1_skills/$s.skill" "$s" -x "*.DS_Store"
  echo "   packed $s.skill"
done
cd "$REPO"

echo "→ 3/3  Done. Opening START_HERE.md"
open START_HERE.md 2>/dev/null
open data/migration_kit/1_skills 2>/dev/null
echo
echo "Next: commit + push with deploy-dev.command so GitHub carries the fresh snapshot."
read -n1 -p "Press any key to close…"
