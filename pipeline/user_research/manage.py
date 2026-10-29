# Last updated: 2026-10-28 15:51 UTC · Data/Backend · private JSONL export and explicit 90-day retention command.
"""Manual maintenance only. No automatic retention/import job is scheduled."""
import argparse
import datetime
import json
import os
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'server'))
from user_research import transaction, RETENTION_DAYS
from settings import ROOT, settings

TABLES=('sessions','events','feedback','withdrawals','clarity_exports')
TIMESTAMPS={'sessions':'last_seen_at','events':'created_at','feedback':'created_at',
            'withdrawals':'withdrawn_at','clarity_exports':'imported_at'}


def purge(environment,apply=False):
    from psycopg2 import sql
    counts={}
    with transaction(settings(environment).get('DATABASE_URL')) as cur:
        # First-party consent/feedback/events and export copies all have a 90-day boundary.
        # Tombstones persist for the complete 90-day window, preventing late re-ingestion.
        for table in ('events','feedback','sessions','withdrawals','clarity_exports'):
            query=sql.SQL('{} FROM user_research.{} WHERE environment=%s AND {} < now() - (%s * interval \'1 day\')').format(
                sql.SQL('DELETE' if apply else 'SELECT count(*)'),sql.Identifier(table),sql.Identifier(TIMESTAMPS[table]))
            cur.execute(query,(environment,RETENTION_DAYS))
            counts[table]=cur.rowcount if apply else cur.fetchone()[0]
    return {'mode':'purged' if apply else 'preview','environment':environment,'retention_days':RETENTION_DAYS,'rows':counts}


def export_jsonl(environment,output=None,start=None,end=None):
    from psycopg2 import sql
    today=datetime.datetime.now(datetime.timezone.utc).date()
    start=datetime.date.fromisoformat(start) if start else today-datetime.timedelta(days=89)
    end=datetime.date.fromisoformat(end) if end else today
    if end<start or (end-start).days>=90 or end>today:
        raise ValueError('Export needs a past UTC date range of at most 90 days.')
    if output:
        path=Path(output).expanduser()
    else:
        directory=ROOT/'data/user_research';directory.mkdir(parents=True,exist_ok=True)
        path=directory/('research-'+environment+'-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%f')+'.jsonl')
    # Exclusive creation + private mode; never overwrite a previous research export.
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    rows=0
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as stream, transaction(settings(environment).get('DATABASE_URL')) as cur:
            cur.execute('SET TRANSACTION READ ONLY')
            for table in TABLES:
                cur.execute(sql.SQL('SELECT * FROM user_research.{} WHERE environment=%s AND {} >= %s::date AND {} < (%s::date + 1)').format(
                    sql.Identifier(table),sql.Identifier(TIMESTAMPS[table]),sql.Identifier(TIMESTAMPS[table])),(environment,start,end))
                columns=[column[0] for column in cur.description]
                while True:
                    batch=cur.fetchmany(500)
                    if not batch:break
                    for row in batch:
                        stream.write(json.dumps({'table':table,'row':dict(zip(columns,row))},default=str,ensure_ascii=False)+'\n');rows+=1
        return {'mode':'exported','environment':environment,'rows':rows,'format':'JSONL','output':str(path),
                'from_utc_date':start.isoformat(),'to_utc_date':end.isoformat()}
    except Exception:
        path.unlink(missing_ok=True)
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--environment',required=True,choices=('dev','prod'))
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('purge');p.add_argument('--apply',action='store_true')
    e=sub.add_parser('export');e.add_argument('--output');e.add_argument('--from-date');e.add_argument('--to-date')
    args=parser.parse_args()
    try:
        print(json.dumps(purge(args.environment,args.apply) if args.command=='purge' else export_jsonl(args.environment,args.output,args.from_date,args.to_date)))
    except Exception as exc:
        print(json.dumps({'ok':False,'error_type':type(exc).__name__,'error_code':'research_maintenance_stopped'}));sys.exit(1)
