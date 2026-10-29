# Last updated: 2026-10-29 · Full-Stack · private read-only production monitoring commands.
"""A bounded command vocabulary, never an operating-system shell or SQL console.

The HTTP caller must apply the existing site authentication gate first. The
separate research-admin credential and same-origin checks remain mandatory.
"""
import datetime
import json
import re
from urllib.request import Request,build_opener,HTTPRedirectHandler

try:
    from . import research_dashboard as dashboard,research_http,user_research
except ImportError:
    import research_dashboard as dashboard
    import research_http,user_research

COMMANDS=frozenset(('status','errors','activity'))
PUBLIC_SITES={'prod':'https://meatcode-oracle.onrender.com','dev':'https://meatcode.onrender.com'}


def parameters(payload,app_env):
    user_research._object(payload,('command','environment','minutes'),('command',),max_bytes=4096)
    command=payload['command'];environment=payload.get('environment',app_env);minutes=payload.get('minutes',60)
    if not isinstance(command,str) or command not in COMMANDS:raise user_research.InputError('Unknown monitoring command.')
    if not isinstance(environment,str) or environment not in PUBLIC_SITES or type(minutes) is not int or minutes not in dashboard.WINDOWS:
        raise user_research.InputError('Invalid monitoring selection.')
    return command,environment,minutes


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):return None


def _public_json(environment,path):
    # No caller-controlled hostname/path, redirect following, or forwarded credentials.
    if environment not in PUBLIC_SITES or path not in ('/api/version','/api/health'):
        raise user_research.InputError('Invalid status destination.')
    request=Request(PUBLIC_SITES[environment]+path,headers={'Accept':'application/json'})
    with build_opener(NoRedirect()).open(request,timeout=4) as response:
        raw=response.read(65537)
    if len(raw)>65536:raise ValueError('Status response exceeds the limit.')
    result=json.loads(raw)
    if not isinstance(result,dict):raise ValueError('Invalid status response.')
    return result


def status(environment):
    version=_public_json(environment,'/api/version');health=_public_json(environment,'/api/health')
    if version.get('env')!=environment:raise ValueError('Unexpected status environment.')
    revision=version.get('commit_full','')
    if not isinstance(revision,str) or not re.fullmatch(r'[a-f0-9]{40}|',revision):revision=''
    started=version.get('server_started_utc')
    if not isinstance(started,str) or not re.fullmatch(r'[0-9T:+.Z-]{10,40}',started):started=None
    # Model name is public configuration, never a credential or live-model probe.
    model=version.get('model')
    if not isinstance(model,str) or not re.fullmatch(r'[A-Za-z0-9_.:/-]{1,100}',model) or model.lower().startswith(('sk-','phx_','postgres')):model=None
    return {'mode':'read_only','service_url':PUBLIC_SITES[environment],'environment':environment,
            'revision':revision or None,'server_started_at':started,'configured_model':model,
            'checks':{'database_configured':health.get('db_ok') is True,
                      'model_key_configured':health.get('has_anthropic_key') is True,
                      'scope':'configuration_only'},
            'notice':'Configuration presence does not verify database connectivity or a successful model answer.',
            'allowed_commands':sorted(COMMANDS)}


def activity(cursor,environment,minutes=60,errors_only=False,now=None):
    checked=now or datetime.datetime.now(datetime.timezone.utc);since=checked-datetime.timedelta(minutes=minutes)
    predicate=" AND name='oracle.failed'" if errors_only else ''
    cursor.execute('''SELECT event_id,name,scene,created_at,duration_ms,error_code,source_count,session_id,elapsed_ms
        FROM user_research.events WHERE environment=%s AND created_at >= %s AND created_at <= %s'''+predicate+'''
        ORDER BY created_at DESC,event_id DESC LIMIT 50''',(environment,since,checked))
    entries=[{'id':str(identifier),'event':name,'scene':scene,'created_at':dashboard._iso(created),
        'duration_ms':duration,'error_code':error,'source_count':sources,'elapsed_ms':elapsed,
        'session_label':dashboard._session_label(session,environment)}
        for identifier,name,scene,created,duration,error,sources,session,elapsed in cursor.fetchall()]
    return {'mode':'read_only','entries':entries,'limit':50,'window_minutes':minutes,
            'log_scope':'consented_product_events','notice':'These are recorded lifecycle events, not raw Render logs, stack traces or unsaved browser errors.'}


def handle(handler,database_url,app_env,environ,local_admin=False):
    hosted=str(environ.get('RENDER','')).strip().lower()=='true';local=bool(local_admin and not hosted)
    if not dashboard._browser_origin_ok(handler.headers) or (not local and not dashboard._admin_token_ok(handler.headers,environ)):
        return research_http._error(handler,403,'research_admin_required','Research administrator access is required.',close=True)
    payload,error=research_http._read_payload(handler,max_bytes=4096)
    if error:return research_http._error(handler,*error,close=True)
    try:
        command,environment,minutes=parameters(payload,app_env)
        target,_=dashboard._database_settings(environment,app_env,environ,database_url,local)
        if command=='status':result=status(environment)
        else:
            with dashboard.readonly(target) as cursor:result=activity(cursor,environment,minutes,command=='errors')
        return research_http._reply(handler,{'ok':True,'command':command,'environment':environment,
            'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'result':result})
    except user_research.InputError:
        return research_http._error(handler,400,'invalid_monitoring_command','Choose status, errors or activity and an available environment.')
    except Exception:
        return research_http._error(handler,503,'monitoring_unavailable','Monitoring could not complete. No production action was performed.')
