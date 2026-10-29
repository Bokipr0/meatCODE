# Last updated: 2026-10-28 15:51 UTC · Data/Backend · transactional additive migration with in-transaction verification.
"""Apply only the isolated user_research schema. Run DEV, then production."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from settings import ROOT, settings, research_database_url

EXPECTED = {
    'oracle_turns':{'elapsed_ms','turn_id','environment','session_id','conversation_id','turn_index','question','answer','status','revision','source_ids','error_code','truncated','consent_version','consent_at','created_at','updated_at'},
    'sessions': {'user_ref','clarity_ref','tester_label','session_id','environment','consent_version','consent_at','created_at','last_seen_at'},
    'events': {'elapsed_ms','event_id','environment','session_id','name','scene','duration_ms','error_code','source_count','created_at'},
    'feedback': {'elapsed_ms','event_id','environment','session_id','rating','category','comment','created_at'},
    'withdrawals': {'session_id','environment','withdrawn_at'},
    'clarity_exports': {'export_id','environment','project_id','export_date','num_of_days','dimensions',
                        'attempts','status','aggregates','imported_at'},
}
INDEXES = {'ur_sessions_clarity_ref','sessions_pkey','events_pkey','feedback_pkey','withdrawals_pkey','clarity_exports_pkey',
           'clarity_export_daily_unique','oracle_turns_pkey','ur_oracle_session','ur_oracle_updated','ur_sessions_last_seen','ur_events_session_time',
           'ur_events_created','ur_feedback_created','ur_withdrawals_created','ur_exports_created'}


def verify(cur):
    cur.execute("SELECT table_name,column_name FROM information_schema.columns WHERE table_schema='user_research'")
    actual = {}
    for table, column in cur.fetchall():
        actual.setdefault(table,set()).add(column)
    if actual != EXPECTED:
        raise RuntimeError('Unexpected user_research schema; migration rolled back.')
    cur.execute("SELECT indexname FROM pg_indexes WHERE schemaname='user_research'")
    indexes = {row[0] for row in cur.fetchall()}
    if not INDEXES <= indexes:
        raise RuntimeError('Missing expected user_research indexes.')
    cur.execute("""SELECT count(*) FROM pg_namespace n,
                   LATERAL aclexplode(coalesce(n.nspacl,acldefault('n',n.nspowner))) a
                   WHERE n.nspname='user_research' AND a.grantee=0""")
    if cur.fetchone()[0] != 0:
        raise RuntimeError('PUBLIC unexpectedly has research schema privileges.')
    cur.execute("""SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace,
                   LATERAL aclexplode(coalesce(c.relacl,acldefault('r',c.relowner))) a
                   WHERE n.nspname='user_research' AND c.relkind='r' AND a.grantee=0""")
    if cur.fetchone()[0] != 0:
        raise RuntimeError('PUBLIC unexpectedly has research table privileges.')
    cur.execute("""SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace,
                   LATERAL aclexplode(coalesce(c.relacl,acldefault('s',c.relowner))) a
                   WHERE n.nspname='user_research' AND c.relkind='S' AND a.grantee=0""")
    if cur.fetchone()[0] != 0:
        raise RuntimeError('PUBLIC unexpectedly has research sequence privileges.')
    return {'tables': sorted(actual), 'indexes': len(indexes), 'public_grants':0}


def run(environment, apply=False):
    import psycopg2
    if environment!='prod':raise RuntimeError('Only production research storage is active.')
    conf=settings(environment);prod=settings('prod')
    if not research_database_url(conf) or (environment=='dev' and research_database_url(conf)==research_database_url(prod)):
        raise RuntimeError('Independent dev database configuration is required.')
    conn=psycopg2.connect(research_database_url(conf),connect_timeout=5)
    try:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL lock_timeout='3s'; SET LOCAL statement_timeout='15s'")
            cur.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")
            before=cur.fetchone()[0]
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='user_research'")
            existing={row[0] for row in cur.fetchall()}
            if existing and not existing <= set(EXPECTED):
                raise RuntimeError('Existing research schema differs; stop for review.')
            if not apply:
                conn.rollback()
                return {'environment':environment,'mode':'preflight','existing_tables':sorted(existing),'public_tables':before}
            cur.execute("SELECT pg_advisory_xact_lock(hashtextextended('meatcode:migration:0016',0))")
            # Never reinstall older restrictive consent checks over newer rows.
            migrations=['0016_user_research.sql']
            if 'oracle_turns' not in existing:migrations.append('0019_oracle_chat_research.sql')
            cur.execute("SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_schema='user_research' AND table_name='sessions' AND column_name='user_ref')")
            if not cur.fetchone()[0]:migrations.append('0020_research_journey.sql')
            migrations.append('0021_research_demo_policy.sql')
            migrations.append('0022_production_research_only.sql')
            for migration in migrations:
                sql=(ROOT/'db/migrations'/migration).read_text()
                body='\n'.join(line for line in sql.splitlines() if line.strip() not in ('BEGIN;','COMMIT;'))
                cur.execute(body)
            result=verify(cur)
            cur.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")
            if cur.fetchone()[0]!=before:
                raise RuntimeError('Scientific/public table inventory changed; rolled back.')
        conn.commit()
        return {'environment':environment,'mode':'applied',**result,'public_tables_unchanged':True}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--environment',choices=('dev','prod'),required=True)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    try:
        print(json.dumps(run(args.environment,args.apply)))
    except Exception as exc:
        # No connection string, SQL payload, row content or raw DB error in CLI output.
        print(json.dumps({'ok':False,'error_type':type(exc).__name__,'action':'Migration stopped; no unverified transaction committed.'}))
        sys.exit(1)
