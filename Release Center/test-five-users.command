#!/bin/bash
# Updated 2026-10-29: run five simultaneous Oracle requests without deploying.
cd "$(dirname "$0")/.." || exit 1
python3 pipeline/oracle_five_user_check.py "$@"
result=$?
read -r -p "Press Enter to close." ignored
exit "$result"
