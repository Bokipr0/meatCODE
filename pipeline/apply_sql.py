#!/usr/bin/env python3
"""
Run a .sql file against the database in $DATABASE_URL.
Replacement for `psql -f file.sql` when psql isn't installed.

Usage:
    export DATABASE_URL="postgresql://neondb_owner:...@...neon.tech/neondb?sslmode=require"
    python3 apply_sql.py add_dimensions_columns.sql
"""
import os, sys
from pathlib import Path
import psycopg2

def _load_dotenv():
    for path in (Path(__file__).resolve().parent / ".env", Path.cwd() / ".env"):
        if not path.is_file():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.lower().startswith("export "):
                line = line[7:].lstrip()
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v
        return path
    return None

_loaded = _load_dotenv()
if _loaded:
    print(f"Loaded env from {_loaded}")

if len(sys.argv) < 2:
    sys.exit("Usage: python3 apply_sql.py <file.sql>")
sql_path = sys.argv[1]
url = os.environ.get("DATABASE_URL")
if not url:
    sys.exit("Set DATABASE_URL env var first")

with open(sql_path, "r", encoding="utf-8") as fh:
    sql = fh.read()

print(f"Applying {sql_path} → Neon …")
conn = psycopg2.connect(url)
conn.autocommit = False
try:
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    print("✓ done")
except Exception as e:
    conn.rollback()
    print(f"✗ failed: {e}")
    sys.exit(1)
finally:
    conn.close()
