# Last updated: 2026-11-16 · Codex · Restricted scientific connection provisioning.
"""Create new column-scoped MCP readers; write credentials only to a private file."""
import argparse
import json
import os
from pathlib import Path
import secrets
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg2
from psycopg2 import sql
from dotenv import dotenv_values

ROLE = 'meatcode_mcp_science_ro'
COLUMNS = ['id', 'name', 'year', 'doi', 'url', 'review_status', 'search_vec', 'main_claim',
           'tailored_abstract', 'top_keywords', 'journal', 'venue']
GRAPH_TABLES = ['batches', 'documents', 'chunks', 'embeddings', 'relations', 'evidence']


def provision(env_file, graph):
    url = dotenv_values(env_file)['DATABASE_URL']
    password = secrets.token_urlsafe(40)
    conn = psycopg2.connect(url, connect_timeout=10)
    try:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL statement_timeout = '10s'")
            cur.execute('SELECT 1 FROM pg_roles WHERE rolname=%s', (ROLE,))
            if cur.fetchone():
                raise RuntimeError('MCP reader already exists; reuse its private configuration instead of rotating it')
            cur.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD %s NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS').format(sql.Identifier(ROLE)), (password,))
            cur.execute(sql.SQL('GRANT USAGE ON SCHEMA public TO {}').format(sql.Identifier(ROLE)))
            cur.execute(sql.SQL('GRANT SELECT ({}) ON public.sources TO {}').format(
                sql.SQL(',').join(map(sql.Identifier, COLUMNS)), sql.Identifier(ROLE)))
            if graph:
                cur.execute(sql.SQL('GRANT USAGE ON SCHEMA lightrag_demo TO {}').format(sql.Identifier(ROLE)))
                for table in GRAPH_TABLES:
                    cur.execute(sql.SQL('GRANT SELECT ON lightrag_demo.{} TO {}').format(sql.Identifier(table), sql.Identifier(ROLE)))
            cur.execute(sql.SQL('ALTER ROLE {} SET statement_timeout = %s').format(sql.Identifier(ROLE)), ('5s',))
            cur.execute(sql.SQL('ALTER ROLE {} SET default_transaction_read_only = on').format(sql.Identifier(ROLE)))
            # Check no broad table grants or privileged memberships were inherited through PUBLIC.
            cur.execute("SELECT has_table_privilege(%s,'public.sources','UPDATE'),has_column_privilege(%s,'public.sources','abstract','SELECT')", (ROLE, ROLE))
            if any(cur.fetchone()):
                raise RuntimeError('Existing PUBLIC privileges would exceed the scoped MCP policy; rolled back')
        conn.commit()
    finally:
        conn.close()
    parts = urlsplit(url)
    authority = quote(ROLE, safe='') + ':' + quote(password, safe='') + '@' + parts.hostname
    if parts.port:
        authority += ':' + str(parts.port)
    return urlunsplit((parts.scheme, authority, parts.path, parts.query, parts.fragment))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus-env', required=True)
    parser.add_argument('--graph-env', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise SystemExit('Private hosted configuration already exists; refusing to overwrite')
    output.parent.mkdir(parents=True, exist_ok=True)
    # Persist immediately after each successful provisioning so a partial run is recoverable.
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        values = {'MCP_DATABASE_URL': provision(args.corpus_env, False)}
        json.dump(values, stream); stream.flush(); os.fsync(stream.fileno())
        values['MCP_GRAPH_DATABASE_URL'] = provision(args.graph_env, True)
        stream.seek(0); json.dump(values, stream); stream.truncate(); stream.flush(); os.fsync(stream.fileno())
    print('Created restricted scientific reader on production and development; credentials saved privately.')


if __name__ == '__main__':
    main()
