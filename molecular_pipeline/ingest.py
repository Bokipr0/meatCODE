#!/usr/bin/env python3
"""Thin CLI entrypoint so you can run `python ingest.py molecules.csv`.

All logic lives in the `moldedup` package. Usage:
    python ingest.py init
    python ingest.py ingest molecules.csv --source "flavor list"
    python ingest.py resolve "vanillin"
    python ingest.py review
    python ingest.py stats
"""
import sys

from moldedup.cli import main

if __name__ == "__main__":
    sys.exit(main())
