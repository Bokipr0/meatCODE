# Last updated: 2026-10-29 10:49 UTC · Data/Backend · bounded read-only dashboard with distinct admin authorization and hashed session labels.
"""Called only after the site's existing authentication gate. No provider API calls."""
from contextlib import contextmanager
import datetime
import hashlib
import hmac
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

try:
    from . import user_research, research_http
except ImportError:
    import user_research
    import research_http

ROOT = Path(__file__).resolve().parents[1]
WINDOWS = frozenset((15,60,1440,10080,129600))


def _admin_token_ok(headers, environ):
    token = str(environ.get('RESEARCH_ADMIN_TOKEN', ''))
    if not 32 <= len(token) <= 256 or any(not 33 <= ord(c) <= 126 for c in token):
        return False
    if token == str(environ.get('SITE_PASSWORD', '')):
        return False
    provided = research_http._single_header(headers, 'X-MeatCODE-Research-Admin')
    if not isinstance(provided,str) or len(provided)>256:
        return False
    return hmac.compare_digest(token.encode('utf-8'),provided.encode('utf-8'))


def _browser_origin_ok(headers):
    # The local cockpit must not become readable by an unrelated web page when
    # the shared site-password gate is disabled on a developer machine.
    site=research_http._single_header(headers,'Sec-Fetch-Site')
    if site is not None and site not in ('same-origin','none'):
        return False
    for name in ('Origin','Sec-Fetch-Site'):
        if hasattr(headers,'get_all') and len(headers.get_all(name,[]))>1:
            return False
    origin=research_http._single_header(headers,'Origin')
    return research_http._same_origin(headers) if origin is not None else True


def parameters(path, app_env):
    query = parse_qs(urlsplit(path).query, keep_blank_values=True)
    if set(query)-{'environment','minutes','limit'} or any(len(value)!=1 for value in query.values()):
        raise user_research.InputError('Dashboard parameters are invalid.')
    environment = query.get('environment',[app_env])[0]
    if environment not in ('dev','prod'):
        raise user_research.InputError('Choose dev or prod.')
    window = query.get('minutes',['15'])[0]
    limit = query.get('limit',['50'])[0]
    if window not in ('15','60','1440','10080','129600') or not 1<=len(limit)<=2 or not limit.isascii() or not limit.isdigit() or not 1<=int(limit)<=50:
        raise user_research.InputError('Choose a supported window and limit.')
    return environment,int(window),int(limit)


def _local_settings(environment, environ):
    settings=dict(environ)
    for path in [ROOT/'.env']+([ROOT/'.env.dev'] if environment=='dev' else []):
        if not path.is_file():
            continue
        for raw in path.read_text().splitlines():
            line=raw.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key,value=line.split('=',1);value=value.strip().strip('\"\'')
            if value:settings[key.strip()]=value
    return settings


def _database_settings(environment, app_env, environ, database_url, local_admin):
    hosted=str(environ.get('RENDER','')).strip().lower()=='true'
    if not local_admin or hosted:
        if environment!=app_env:
            raise user_research.InputError('Hosted dashboard can read only this application environment.')
        return database_url,dict(environ)
    selected=_local_settings(environment,environ)
    # Do not label inherited production data as development if its overlay is absent.
    if environment=='dev':
        production=_local_settings('prod',environ)
        if selected.get('DATABASE_URL')==production.get('DATABASE_URL'):
            raise user_research.StorageError()
    chosen=selected.get('DATABASE_URL')
    if not chosen:
        raise user_research.StorageError()
    return chosen,selected


def _provider_url(value):
    if not isinstance(value,str) or len(value)>512:
        return ''
    try:
        parsed=urlsplit(value)
        if (parsed.scheme=='https' and parsed.hostname in ('us.posthog.com','eu.posthog.com')
                and parsed.netloc==parsed.hostname and parsed.port is None
                and parsed.path.startswith('/project/') and not parsed.query and not parsed.fragment):
            return value
    except ValueError:
        pass
    return ''


def providers(environ,environment):
    public=user_research.config(environ,environment)
    posthog=public['posthog']
    return {'clarity':{'configured':bool(public['clarity_project_id']),
                       'project_id':public['clarity_project_id'],'delivery':'unverified'},
            'posthog':{'configured':bool(posthog['project_token'] and posthog['api_host']),
                        'api_host':posthog['api_host'],
                        'project_url':_provider_url(environ.get('POSTHOG_PROJECT_URL','')),
                        'dashboard_url':_provider_url(environ.get('POSTHOG_DASHBOARD_URL','')),
                        'delivery':'unverified'}}


@contextmanager
def readonly(db_url):
    connection=None
    try:
        if not db_url:
            raise user_research.StorageError()
        import psycopg2
        connection=psycopg2.connect(db_url,connect_timeout=5)
        connection.set_session(readonly=True,isolation_level='REPEATABLE READ')
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL statement_timeout='5s'")
            cursor.execute("SET LOCAL lock_timeout='2s'")
            yield cursor
        connection.rollback()
    except Exception:
        if connection is not None:
            try:connection.rollback()
            except Exception:pass
        raise user_research.StorageError() from None
    finally:
        if connection is not None:
            connection.close()


def _session_label(session_id,environment):
    return 's_'+hashlib.sha256(('research:'+environment+':'+str(session_id)).encode()).hexdigest()[:12]


def _iso(value):
    return value.isoformat() if hasattr(value,'isoformat') else str(value)


def snapshot(cursor,environment,minutes=15,limit=50,now=None):
    if environment not in ('dev','prod') or minutes not in WINDOWS or type(limit) is not int or not 1<=limit<=50:
        raise user_research.InputError('Dashboard parameters are invalid.')
    checked=now or datetime.datetime.now(datetime.timezone.utc)
    since=checked-datetime.timedelta(minutes=minutes)
    args=(environment,since,checked)
    cursor.execute('''WITH recent_events AS (
        SELECT session_id,name,duration_ms FROM user_research.events
        WHERE environment=%s AND created_at >= %s AND created_at <= %s
    ), recent_feedback AS (
        SELECT session_id FROM user_research.feedback
        WHERE environment=%s AND created_at >= %s AND created_at <= %s
    ) SELECT
        (SELECT count(*) FROM (SELECT session_id FROM recent_events UNION SELECT session_id FROM recent_feedback) AS active_sessions),
        count(*) FILTER (WHERE name='oracle.submitted'),
        count(*) FILTER (WHERE name='oracle.completed'),
        count(*) FILTER (WHERE name='oracle.failed'),
        (SELECT count(*) FROM recent_feedback),
        percentile_cont(0.5) WITHIN GROUP (ORDER BY duration_ms)
            FILTER (WHERE name='oracle.completed' AND duration_ms IS NOT NULL)
        FROM recent_events''',args+args)
    row=cursor.fetchone()
    totals=dict(zip(('sessions','oracle_submitted','oracle_completed','oracle_failed','feedback'),map(int,row[:5])))
    totals['median_response_ms']=float(row[5]) if row[5] is not None else None
    cursor.execute('''SELECT scene,count(*) FROM user_research.events
        WHERE environment=%s AND created_at >= %s AND created_at <= %s
        GROUP BY scene ORDER BY count(*) DESC,scene''',args)
    scenes=[{'scene':scene,'count':int(count)} for scene,count in cursor.fetchall()]
    cursor.execute('''SELECT event_id,name,scene,created_at,duration_ms,error_code,source_count,session_id
        FROM user_research.events WHERE environment=%s AND created_at >= %s AND created_at <= %s
        ORDER BY created_at DESC,event_id DESC LIMIT %s''',args+(limit,))
    activity=[{'id':str(event_id),'event':name,'scene':scene,'created_at':_iso(created),
               'duration_ms':duration,'error_code':error,'source_count':sources,
               'session_label':_session_label(session,environment)}
              for event_id,name,scene,created,duration,error,sources,session in cursor.fetchall()]
    cursor.execute('''SELECT created_at,rating,category,comment,session_id FROM user_research.feedback
        WHERE environment=%s AND created_at >= %s AND created_at <= %s
        ORDER BY created_at DESC,event_id DESC LIMIT 20''',args)
    feedback=[{'created_at':_iso(created),'rating':rating,'category':category,
               'comment':str(comment or '')[:2000].replace(str(session),'[session]'),
               'session_label':_session_label(session,environment)}
              for created,rating,category,comment,session in cursor.fetchall()]
    cursor.execute('SELECT conversation_id,count(*),max(updated_at),min(created_at)\n        FROM user_research.oracle_turns WHERE environment=%s\n        GROUP BY conversation_id HAVING max(updated_at)>=%s AND max(updated_at)<=%s\n        ORDER BY max(updated_at) DESC,conversation_id LIMIT 20',args)
    conversations=[{'id':str(cid),'turns':int(count),'last_updated':_iso(updated),'started_at':_iso(started)}
                   for cid,count,updated,started in cursor.fetchall()]
    return {'ok':True,'environment':environment,'checked_at':checked.isoformat(),'window_minutes':minutes,
            'source':'neon_first_party','totals':totals,'scenes':scenes,'activity':activity,
            'feedback':feedback,'conversations':conversations,'limits':{'activity_limit':limit,'conversation_limit':20}}


def transcript_parameters(path,app_env):
    query=parse_qs(urlsplit(path).query,keep_blank_values=True)
    if set(query)-{'environment','conversation','after','limit'} or any(len(v)!=1 for v in query.values()):raise user_research.InputError('Invalid transcript parameters.')
    environment=query.get('environment',[app_env])[0]
    if environment not in ('dev','prod'):raise user_research.InputError('Invalid environment.')
    conversation=user_research._uuid(query.get('conversation',[''])[0])
    after=query.get('after',['0'])[0];limit=query.get('limit',['20'])[0]
    if not after.isascii() or not after.isdigit() or len(after)>7 or not 0<=int(after)<=1000000:raise user_research.InputError('Invalid cursor.')
    if not limit.isascii() or not limit.isdigit() or len(limit)>3 or not 1<=int(limit)<=20:raise user_research.InputError('Invalid page size.')
    return environment,conversation,int(after),int(limit)


def transcript(cursor,environment,conversation,after=0,limit=20):
    cursor.execute("""SELECT turn_index,question,answer,status,source_ids,error_code,truncated,created_at,updated_at
        FROM user_research.oracle_turns WHERE environment=%s AND conversation_id=%s AND turn_index>%s
        ORDER BY turn_index LIMIT %s""",(environment,conversation,after,limit+1))
    rows=cursor.fetchall();more=len(rows)>limit;rows=rows[:limit]
    turns=[{'index':index,'question':question,'answer':answer,'status':status,'source_ids':sources,
            'error_code':error,'truncated':truncated,'created_at':_iso(created),'updated_at':_iso(updated)}
           for index,question,answer,status,sources,error,truncated,created,updated in rows]
    return {'ok':True,'environment':environment,'conversation':conversation,'turns':turns,
            'has_more':more,'next_after':turns[-1]['index'] if turns else after,'provenance':'browser_observed_after_explicit_consent'}


def handle(handler,database_url,app_env,environ,local_admin=False):
    """Private data route, after BasicAuth. Shared site credentials alone are insufficient."""
    hosted=str(environ.get('RENDER','')).strip().lower()=='true'
    local=bool(local_admin and not hosted)
    if not _browser_origin_ok(handler.headers):
        return research_http._error(handler,403,'research_admin_required','Research administrator access is required.')
    if not local and not _admin_token_ok(handler.headers,environ):
        return research_http._error(handler,403,'research_admin_required','Research administrator access is required.')
    try:
        is_transcript=urlsplit(handler.path).path=='/api/research/transcript'
        if is_transcript:environment,conversation,after,limit=transcript_parameters(handler.path,app_env)
        else:environment,minutes,limit=parameters(handler.path,app_env)
        target,settings=_database_settings(environment,app_env,environ,database_url,local)
        with readonly(target) as cursor:
            result=transcript(cursor,environment,conversation,after,limit) if is_transcript else snapshot(cursor,environment,minutes,limit)
        if not is_transcript:result['providers']=providers(settings,environment)
        return research_http._reply(handler,result)
    except user_research.InputError:
        return research_http._error(handler,400,'invalid_dashboard_parameters','Dashboard parameters are invalid for this server.')
    except Exception:
        return research_http._error(handler,503,'research_dashboard_unavailable','Research dashboard is temporarily unavailable.')
