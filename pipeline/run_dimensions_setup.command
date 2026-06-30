#!/bin/bash
# One-click setup + dry-run for the Dimensions ingester.
# Double-click this file in Finder to run.

set -u
cd "$(dirname "$0")"
echo "================================================================"
echo " Reaktzia · Dimensions → Neon · setup + dry-run"
echo " Working dir: $(pwd)"
echo "================================================================"
echo

# Sanity check files
for f in .env apply_sql.py dimensions_ingest.py add_dimensions_columns.sql; do
    if [ -f "$f" ]; then
        echo "  ✓ $f"
    else
        echo "  ✗ MISSING: $f"
        echo
        read -p "Press Enter to close..."
        exit 1
    fi
done
echo

echo "── Step 1: applying schema additions to Neon ───────────────────"
python3 apply_sql.py add_dimensions_columns.sql
rc=$?
if [ $rc -ne 0 ]; then
    echo
    echo "Schema apply failed (exit $rc). Stopping."
    read -p "Press Enter to close..."
    exit $rc
fi
echo

echo "── Step 2: Full Dimensions pull — all 6 topics, writes to Neon ─"
python3 dimensions_ingest.py
rc=$?
echo

if [ $rc -eq 0 ]; then
    echo "================================================================"
    echo " ✓ Ingest complete — your Neon DB has been populated."
    echo "   Check the totals printed above for what landed."
    echo "================================================================"
else
    echo "Ingest failed (exit $rc). Check the error above."
fi

echo
read -p "Press Enter to close this window..."
