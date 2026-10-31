# Last updated: 2026-10-29 · Codex · read-only production verification; never run synthetic fixtures on live intake.
"""Inspect production research schema/counts only. Positive fixtures belong on isolated QA storage."""
import argparse,json
from settings import settings,research_database_url
from migrate import verify as verify_schema


def run(environment):
    if environment!='prod':raise RuntimeError('Only production research storage is active.')
    target=research_database_url(settings(environment))
    if not target:raise RuntimeError('Production research storage is not configured.')
    import psycopg2
    conn=psycopg2.connect(target,connect_timeout=5)
    try:
        conn.set_session(readonly=True,isolation_level='REPEATABLE READ')
        with conn.cursor() as cur:
            cur.execute("SET LOCAL statement_timeout='5s'")
            schema=verify_schema(cur)
            cur.execute("SELECT count(DISTINCT conrelid) FROM pg_constraint WHERE connamespace='user_research'::regnamespace AND contype='c' AND pg_get_constraintdef(oid)='CHECK ((environment = ''prod''::text))'")
            if cur.fetchone()[0]!=6:raise RuntimeError('Production-only constraints are missing.')
            counts={}
            for table in ('sessions','events','feedback','withdrawals','clarity_exports','oracle_turns'):
                cur.execute('SELECT count(*) FROM user_research.'+table+' WHERE environment=%s',('prod',))
                counts[table]=cur.fetchone()[0]
        return {'ok':True,'environment':'prod','mode':'read_only','synthetic_writes':0,'retained_rows':counts,**schema}
    finally:conn.rollback();conn.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--environment',required=True,choices=('prod',))
    args=parser.parse_args()
    try:report=run(args.environment);print(json.dumps(report))
    except Exception as exc:
        print(json.dumps({'ok':False,'error_type':type(exc).__name__,'error_code':'read_only_verification_stopped'}));raise SystemExit(1)
