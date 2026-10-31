# Last updated: 2026-10-28 15:51 UTC · Data/Backend · manual, quota-limited sanitized Clarity dashboard aggregate import.
"""Import dashboard aggregates, not raw replays. No automatic job is scheduled.

Official contract: https://learn.microsoft.com/en-us/clarity/setup-and-installation/clarity-data-export-api
Only Browser/Device/OS dimensions; URL/title/referrer metrics and arbitrary text are discarded.
"""
import argparse
import datetime
import json
import math
import re
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, HTTPRedirectHandler, build_opener

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'server'))
from user_research import transaction, config, StorageError
from settings import settings, research_database_url

ENDPOINT='https://www.clarity.ms/export-data/api/v1/project-live-insights'
DIMENSIONS=('Browser','Device','OS')
METRICS={'Traffic','ScrollDepth','EngagementTime','Browser','Device','OS','DeadClickCount',
         'ExcessiveScroll','RageClickCount','QuickbackClick','ScriptErrorCount','ErrorClickCount'}
NUMERIC_FIELDS={'totalSessionCount','totalBotSessionCount','distantUserCount','distinctUserCount',
                'PagesPerSessionPercentage','sessionsWithMetricPercentage','sessionsWithoutMetricPercentage',
                'sessionsWithMetricCount','sessionsWithoutMetricCount','totalSessions','engagementTime',
                'activeTime','totalTime','scrollDepth','averageScrollDepth','averageEngagementTime',
                'count','percentage','value','metricCount','affectedSessionCount'}


def sanitize_aggregates(payload):
    if not isinstance(payload,list) or len(payload)>100:
        raise ValueError('Unexpected aggregate response.')
    result=[]
    for metric in payload:
        if not isinstance(metric,dict):
            raise ValueError('Unexpected aggregate response.')
        name=metric.get('metricName')
        if not isinstance(name,str) or name.replace(' ','') not in METRICS:
            continue
        rows=metric.get('information')
        if not isinstance(rows,list) or len(rows)>1000:
            raise ValueError('Unexpected aggregate response.')
        clean=[]
        for row in rows:
            if not isinstance(row,dict):
                raise ValueError('Unexpected aggregate response.')
            item={}
            for key,value in row.items():
                if key in DIMENSIONS and isinstance(value,str) and re.fullmatch(r'[A-Za-z0-9 ._()\-]{1,80}',value):
                    item[key]=value
                elif key in NUMERIC_FIELDS:
                    if isinstance(value,str) and re.fullmatch(r'-?\d{1,15}(\.\d{1,10})?',value):
                        value=float(value) if '.' in value else int(value)
                    if type(value) in (int,float) and math.isfinite(value) and 0<=value<=10**15:
                        item[key]=value
            # No dimension-only rows or arbitrary strings survive storage.
            if any(key in NUMERIC_FIELDS for key in item):
                clean.append(item)
        result.append({'metricName':name.replace(' ',''),'information':clean})
    return result


class NoRedirect(HTTPRedirectHandler):
    # Never forward the server-only bearer token to a redirected endpoint.
    def redirect_request(self,*args,**kwargs):
        return None


def _reserve(cur,environment,project,date,days,retry_failed=False):
    cur.execute("SELECT to_regclass('user_research.clarity_exports')")
    if cur.fetchone()[0] is None:return None,'archive_not_configured'
    cur.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',
                ('user_research:clarity:'+project+':'+date.isoformat(),))
    cur.execute('''SELECT export_id,status,attempts FROM user_research.clarity_exports
                   WHERE environment=%s AND project_id=%s AND export_date=%s AND num_of_days=%s''',
                (environment,project,date,days))
    existing=cur.fetchone()
    if existing and (existing[1]!='failed' or not retry_failed):
        return None,existing[1]
    cur.execute('SELECT coalesce(sum(attempts),0) FROM user_research.clarity_exports WHERE project_id=%s AND export_date=%s',
                (project,date))
    if cur.fetchone()[0]>=10:
        return None,'daily_limit'
    if existing:
        cur.execute("UPDATE user_research.clarity_exports SET status='pending',attempts=attempts+1 WHERE export_id=%s",(existing[0],))
        return existing[0],'reserved'
    cur.execute('''INSERT INTO user_research.clarity_exports
                   (environment,project_id,export_date,num_of_days,status,attempts)
                   VALUES(%s,%s,%s,%s,'pending',1) RETURNING export_id''',(environment,project,date,days))
    return cur.fetchone()[0],'reserved'


def run(environment,days=1,apply=False,retry_failed=False):
    if type(days) is not int or days not in (1,2,3):
        raise ValueError('numOfDays must be 1, 2 or 3.')
    conf=settings(environment)
    project=config(conf,environment)['clarity_project_id']
    if not project:
        raise ValueError('Configure a valid project ID.')
    if not apply:
        return {'mode':'preview','environment':environment,'scope':'project','project_id':project,'num_of_days':days,
                'dimensions':DIMENSIONS,'token_configured':bool(conf.get('CLARITY_EXPORT_TOKEN'))}
    if environment != 'prod':
        raise ValueError('Run the shared-project importer against production only; development supports preview.')
    token=conf.get('CLARITY_EXPORT_TOKEN')
    if not token:
        raise ValueError('CLARITY_EXPORT_TOKEN must be set server-side before importing.')
    if not re.fullmatch(r'[A-Za-z0-9._\-]+',token):
        raise ValueError('Invalid export token format.')
    date=datetime.datetime.now(datetime.timezone.utc).date()
    with transaction(research_database_url(conf)) as cur:
        export_id,state=_reserve(cur,environment,project,date,days,retry_failed)
    if export_id is None:
        return {'mode':'skipped','reason':state,'environment':environment,'scope':'project'}
    try:
        query=urlencode({'numOfDays':days,**{'dimension'+str(i+1):value for i,value in enumerate(DIMENSIONS)}})
        request=Request(ENDPOINT+'?'+query,headers={'Accept':'application/json','Authorization':'Bearer '+token})
        with build_opener(NoRedirect).open(request,timeout=15) as response:
            raw=response.read(2*1024*1024+1)
        if len(raw)>2*1024*1024:
            raise ValueError('Aggregate response too large.')
        aggregates=sanitize_aggregates(json.loads(raw))
        with transaction(research_database_url(conf)) as cur:
            cur.execute("UPDATE user_research.clarity_exports SET status='complete',aggregates=%s::jsonb,imported_at=now() WHERE export_id=%s",
                        (json.dumps(aggregates),export_id))
        return {'mode':'imported','environment':environment,'scope':'project','export_id':export_id,'metrics':len(aggregates)}
    except Exception as exc:
        with transaction(research_database_url(conf)) as cur:
            cur.execute("UPDATE user_research.clarity_exports SET status='failed' WHERE export_id=%s",(export_id,))
        return {'mode':'failed','environment':environment,'scope':'project','error_code':'clarity_http_'+str(exc.code) if isinstance(exc,HTTPError) else 'clarity_import_failed'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--environment',required=True,choices=('dev','prod'))
    parser.add_argument('--days',type=int,choices=(1,2,3),default=1)
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--retry-failed',action='store_true')
    args=parser.parse_args()
    try:
        result=run(args.environment,args.days,args.apply,args.retry_failed)
        print(json.dumps(result));sys.exit(1 if result['mode']=='failed' else 0)
    except Exception as exc:
        print(json.dumps({'ok':False,'error_type':type(exc).__name__,'error_code':'clarity_import_stopped'}));sys.exit(1)
