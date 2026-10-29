# Last updated: 2026-10-29 · Codex · bounded idempotent research-only database copy; source remains read-only.
"""Preview first; repeat --apply after cutover to reconcile late source writes/withdrawals.

Never exports feedback, identifiers or database URLs into a file or console.
The destination must be a dedicated database containing only user_research tables.
"""
import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit,unquote
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'server'))
import user_research
from settings import settings
from migrate import verify

TABLES=('sessions','events','feedback','oracle_turns','withdrawals','clarity_exports')
MAX_ROWS_PER_TABLE=10000


def identity(url):
    parsed=urlsplit(url)
    if parsed.scheme not in ('postgres','postgresql') or not parsed.hostname or not parsed.path.strip('/'):
        raise ValueError('A PostgreSQL database connection is required.')
    return parsed.hostname.replace('-pooler.','.'),parsed.port or 5432,unquote(parsed.path)


def targets(conf):
    source=conf.get('DATABASE_URL');target=conf.get('RESEARCH_DATABASE_URL')
    if not source or not target or identity(source)==identity(target):
        raise ValueError('Distinct scientific source and dedicated research target are required.')
    return source,target


def copy(environment,apply=False,conf=None):
    import psycopg2
    from psycopg2 import sql
    from psycopg2.extras import Json
    if environment not in ('dev','prod'):raise ValueError('Unsupported environment.')
    source_url,target_url=targets(settings(environment) if conf is None else conf)
    source=psycopg2.connect(source_url,connect_timeout=5);target=None
    try:
        source.set_session(readonly=True,isolation_level='REPEATABLE READ')
        rows={};columns={}
        with source.cursor() as cur:
            cur.execute("SET LOCAL statement_timeout='10s'")
            for table in TABLES:
                cur.execute(sql.SQL('SELECT * FROM user_research.{} WHERE environment=%s').format(sql.Identifier(table)),(environment,))
                columns[table]=[c[0] for c in cur.description];rows[table]=cur.fetchmany(MAX_ROWS_PER_TABLE+1)
                if len(rows[table])>MAX_ROWS_PER_TABLE:raise ValueError('Copy exceeds reviewed bounded batch size.')
        target=psycopg2.connect(target_url,connect_timeout=5)
        with target.cursor() as cur:
            cur.execute("SET LOCAL statement_timeout='10s'; SET LOCAL lock_timeout='3s'")
            verify(cur)
            cur.execute("SELECT count(*) FROM information_schema.tables WHERE table_type='BASE TABLE' AND table_schema NOT IN ('pg_catalog','information_schema','user_research')")
            if cur.fetchone()[0]:raise ValueError('Destination contains unrelated tables; refusing research cutover.')
            counts={t:len(r) for t,r in rows.items()}
            if not apply:return {'environment':environment,'mode':'preview','source_rows':counts,'source_readonly':True,'target_research_only':True}
            # Serialize with live writes/deletions. Lock ordering is stable, and
            # each subsequent READ COMMITTED statement sees committed tombstones.
            session_ids=sorted({str(row[columns[t].index('session_id')]) for t in ('sessions','events','feedback','oracle_turns','withdrawals') for row in rows[t]})
            for sid in session_ids:user_research._lock_session(cur,environment,sid)
            for row in rows['withdrawals']:
                sid=str(row[columns['withdrawals'].index('session_id')]);user_research._withdraw(cur,environment,sid)
                cur.execute('UPDATE user_research.withdrawals SET withdrawn_at=LEAST(withdrawn_at,%s) WHERE environment=%s AND session_id=%s',(row[columns['withdrawals'].index('withdrawn_at')],environment,sid))
            for table in ('sessions','events','feedback','oracle_turns','clarity_exports'):
                names=columns[table]
                source_rows=rows[table]
                if table=='clarity_exports':
                    index=names.index('export_id');names=[n for n in names if n!='export_id'];source_rows=[tuple(v for i,v in enumerate(row) if i!=index) for row in source_rows]
                template='INSERT INTO user_research.{} AS existing ({}) VALUES ({}) ON CONFLICT DO NOTHING'
                if table=='sessions':template='INSERT INTO user_research.{} AS existing ({}) VALUES ({}) ON CONFLICT(session_id,environment) DO UPDATE SET last_seen_at=GREATEST(existing.last_seen_at,EXCLUDED.last_seen_at)'
                if table=='oracle_turns':template='INSERT INTO user_research.{} AS existing ({}) VALUES ({}) ON CONFLICT(turn_id,environment) DO UPDATE SET answer=EXCLUDED.answer,status=EXCLUDED.status,revision=EXCLUDED.revision,source_ids=EXCLUDED.source_ids,error_code=EXCLUDED.error_code,truncated=EXCLUDED.truncated,updated_at=EXCLUDED.updated_at WHERE existing.status=\'submitted\' AND EXCLUDED.revision>existing.revision'
                query=sql.SQL(template).format(sql.Identifier(table),sql.SQL(',').join(map(sql.Identifier,names)),sql.SQL(',').join(sql.Placeholder() for _ in names))
                for row in source_rows:
                    if 'session_id' in names:
                        sid=str(row[names.index('session_id')]);cur.execute('SELECT 1 FROM user_research.withdrawals WHERE environment=%s AND session_id=%s',(environment,sid))
                        if cur.fetchone():continue
                    values=[Json(v) if names[i]=='aggregates' and v is not None else v for i,v in enumerate(row)]
                    cur.execute(query,values)
                    # Confirm immutable records are present with all original
                    # fields, not merely matching counts after a conflict.
                    if table in ('events','feedback'):
                        cur.execute(sql.SQL('SELECT {} FROM user_research.{} WHERE environment=%s AND event_id=%s').format(sql.SQL(',').join(map(sql.Identifier,names)),sql.Identifier(table)),(environment,row[names.index('event_id')]))
                        if tuple(cur.fetchone() or ())!=tuple(row):raise ValueError('Destination record conflict; copy rolled back.')
            target.commit()
            return {'environment':environment,'mode':'copied','source_rows':counts,'source_readonly':True,'withdrawals_preserved':True,'originals_deleted':False}
    finally:
        source.rollback();source.close()
        if target is not None:target.rollback();target.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--environment',required=True,choices=('dev','prod'));parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    try:print(json.dumps(copy(args.environment,args.apply)))
    except Exception as exc:
        print(json.dumps({'ok':False,'error_type':type(exc).__name__,'error_code':'research_copy_stopped'}));sys.exit(1)
