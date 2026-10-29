"""2026-10-29: read-only, consistent per-database backups before isolation work.
Secrets stay in subprocess environment. Files are private and gitignored.
"""
from pathlib import Path
import os, sys, json, subprocess, hashlib
from datetime import datetime, timezone
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import parse_dsn
sys.path.insert(0,str(Path(__file__).resolve().parent/'user_research'))
from settings import settings

ROOT=Path(__file__).resolve().parents[1]
BIN=Path('/Library/PostgreSQL/18/bin')

def run():
    os.umask(0o077)
    out=ROOT/'data/backups'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out.mkdir(parents=True,exist_ok=False)
    report={'created_utc':datetime.now(timezone.utc).isoformat(),'restore_tested':False,'databases':{}}
    for name in ('prod','dev'):
        conf=settings(name); params=parse_dsn(conf['DATABASE_URL'])
        params['host']=params['host'].replace('-pooler.','.')
        conn=psycopg2.connect(**params,connect_timeout=15)
        conn.set_session(isolation_level='REPEATABLE READ',readonly=True)
        env=dict(os.environ)
        for k in list(env):
            if k.startswith('PG'): del env[k]
        for key,target in [('host','PGHOST'),('port','PGPORT'),('dbname','PGDATABASE'),('user','PGUSER'),('password','PGPASSWORD'),('sslmode','PGSSLMODE')]:
            if key in params: env[target]=params[key]
        env['PGCONNECT_TIMEOUT']='15';env['PGSSLMODE']='require'
        try:
            with conn.cursor() as cur:
                cur.execute("SET LOCAL statement_timeout='120s'")
                cur.execute('SELECT pg_export_snapshot()');snap=cur.fetchone()[0]
                cur.execute("SELECT n.nspname,c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.relkind IN ('r','p') AND n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_toast%' ORDER BY 1,2")
                tables=cur.fetchall();counts={}
                for schema,table in tables:
                    cur.execute(sql.SQL('SELECT count(*) FROM {}.{}').format(sql.Identifier(schema),sql.Identifier(table)))
                    counts[schema+'.'+table]=cur.fetchone()[0]
                cur.execute("SELECT rolname,rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,rolinherit,rolreplication,rolbypassrls,rolconfig FROM pg_roles WHERE rolname NOT LIKE 'pg_%'")
                roles=cur.fetchall()
            dump=out/(name+'.dump')
            args=[str(BIN/'pg_dump'),'--format=custom','--no-password','--snapshot='+snap,'--file='+str(dump)]
            r=subprocess.run(args,env=env,capture_output=True,timeout=900)
            if r.returncode: raise RuntimeError('Backup failed for '+name+' (diagnostic withheld to avoid credential exposure)')
            toc=subprocess.run([str(BIN/'pg_restore'),'--list',str(dump)],capture_output=True,check=True)
            (out/(name+'-contents.txt')).write_bytes(toc.stdout)
            report['databases'][name]={'bytes':dump.stat().st_size,'sha256':hashlib.sha256(dump.read_bytes()).hexdigest(),'table_counts':counts,'role_metadata':roles,'archive_list_verified':True}
            print(name+': '+str(len(counts))+' tables; '+str(dump.stat().st_size)+' bytes; archive readable',flush=True)
        finally: conn.rollback();conn.close()
    (out/'manifest.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
    print('Backup directory: '+str(out),flush=True)
    print('No restore drill performed. Roles/passwords and platform settings require separate provisioning.')

if __name__=='__main__': run()
