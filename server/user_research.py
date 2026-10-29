# Last updated: 2026-10-29 10:49 UTC · Data/Backend · renewed provider consent and validated public PostHog configuration; typed private storage preserved.
"""Private server-side storage; callers own HTTP auth, Origin checks and feature gating.

No prompts, answers, URLs, emails, IP addresses, user agents or arbitrary properties
are accepted. UUIDv4 session IDs are bearer capabilities: do not expose/list them.
"""
from contextlib import contextmanager
import json
import re
import uuid

CONSENT_VERSION = '2026-10-29-chat-v1'
RETENTION_DAYS = 90
EVENT_NAMES = frozenset(('session.started','scene.viewed','oracle.submitted','oracle.completed',
                         'oracle.failed','feedback.submitted'))
SCENES = frozenset(('oracle','research','science','ecosystem','simulate','analytics',
                    'database','map','papers','dev','other'))
ERROR_CODES = frozenset(('network','model_unavailable','session_expired','unknown'))


class InputError(ValueError):
    code = 'invalid_research_input'
    status = 400


class StorageError(Exception):
    code = 'research_storage_unavailable'
    status = 503

    def __init__(self):
        super().__init__('Research storage is temporarily unavailable.')


class WithdrawnError(Exception):
    code = 'research_session_withdrawn'
    status = 410

    def __init__(self):
        super().__init__('This research session was withdrawn.')


def _environment(value):
    if value not in ('dev', 'prod'):
        raise InputError('environment must be dev or prod')
    return value


def config(environ, app_env):
    project = str(environ.get('CLARITY_PROJECT_ID', 'z4upnrbddu')).strip()
    if not re.fullmatch(r'[a-zA-Z0-9]{1,32}', project):
        project = ''
    enabled = str(environ.get('USER_RESEARCH_ENABLED', '')).strip().lower() in ('1','true','yes','on')
    token = str(environ.get('POSTHOG_PROJECT_TOKEN', '')).strip()
    host = str(environ.get('POSTHOG_API_HOST', '')).strip().rstrip('/')
    if not re.fullmatch(r'phc_[A-Za-z0-9]{16,200}', token):
        token = ''
    if host not in ('https://us.i.posthog.com', 'https://eu.i.posthog.com'):
        host = ''
    return {'enabled': enabled,
            'environment': _environment(app_env), 'clarity_project_id': project,
            'consent_version': CONSENT_VERSION, 'retention_days': RETENTION_DAYS,
            'posthog': {'enabled': bool(enabled and token and host),
                        'project_token': token, 'api_host': host}}


def _object(value, allowed, required, max_bytes=32768):
    if not isinstance(value, dict) or set(value) - set(allowed) or set(required) - set(value):
        raise InputError('Missing or unexpected research fields.')
    try:
        if len(json.dumps(value, ensure_ascii=False).encode('utf-8')) > max_bytes:
            raise InputError('Research payload is too large.')
    except (TypeError, ValueError, RecursionError) as exc:
        if isinstance(exc, InputError):
            raise
        raise InputError('Research input must be plain JSON.') from None
    return value


def _uuid(value):
    if not isinstance(value, str):
        raise InputError('Research identifiers must be UUIDv4 strings.')
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError):
        raise InputError('Research identifiers must be UUIDv4 strings.') from None
    if parsed.version != 4 or str(parsed) != value.lower():
        raise InputError('Research identifiers must be UUIDv4 strings.')
    return str(parsed)


def _consent(payload):
    if payload.get('consent') is not True or payload.get('consent_version') != CONSENT_VERSION:
        raise InputError('Current explicit research consent is required.')
    return _uuid(payload.get('session_id'))


def _choice(value, values):
    if not isinstance(value, str) or value not in values:
        raise InputError('Research selection is not supported.')
    return value


def validate_events(payload):
    _object(payload, ('session_id','consent','consent_version','events'),
            ('session_id','consent','consent_version','events'))
    session_id = _consent(payload)
    events = payload['events']
    if not isinstance(events, list) or not 1 <= len(events) <= 20:
        raise InputError('Send between one and twenty research events.')
    result = []
    for event in events:
        _object(event, ('event_id','name','scene','properties'), ('event_id','name','scene'))
        properties = _object(event.get('properties', {}), ('duration_ms','error_code','source_count'), ())
        for key, maximum in (('duration_ms',3600000),('source_count',1000)):
            if key in properties and (type(properties[key]) is not int or not 0 <= properties[key] <= maximum):
                raise InputError('Research numeric property is outside the supported range.')
        if 'error_code' in properties:
            _choice(properties['error_code'], ERROR_CODES)
        result.append({'event_id': _uuid(event['event_id']), 'name': _choice(event['name'], EVENT_NAMES),
                       'scene': _choice(event['scene'], SCENES), **properties})
    return session_id, result


def validate_feedback(payload):
    _object(payload, ('session_id','event_id','consent','consent_version','rating','category','comment'),
            ('session_id','event_id','consent','consent_version','rating','category'))
    session_id = _consent(payload)
    comment = payload.get('comment', '')
    if not isinstance(comment, str) or len(comment) > 2000 or any(ord(c) < 32 and c not in '\n\r\t' for c in comment):
        raise InputError('Feedback comment must be text of at most 2000 characters.')
    return session_id, {'event_id':_uuid(payload['event_id']),
                        'rating':_choice(payload['rating'], ('helpful','neutral','unhelpful')),
                        'category':_choice(payload['category'], ('answer','usability','bug','other')),
                        'comment':comment}


@contextmanager
def transaction(db_url):
    conn = None
    try:
        if not db_url:
            raise StorageError()
        import psycopg2
        conn = psycopg2.connect(db_url, connect_timeout=5)
        with conn.cursor() as cur:
            cur.execute("SET LOCAL statement_timeout = '6s'")
            cur.execute("SET LOCAL lock_timeout = '3s'")
            yield cur
        conn.commit()
    except (InputError, WithdrawnError):
        if conn is not None:
            conn.rollback()
        raise
    except Exception:
        if conn is not None:
            conn.rollback()
        raise StorageError() from None
    finally:
        if conn is not None:
            conn.close()


def _lock_session(cur, environment, session_id):
    # Same transaction-scoped lock for every write AND withdrawal prevents late
    # queued events from resurrecting deleted sessions. No process-local lock.
    cur.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',
                ('user_research:'+environment+':'+session_id,))


def _session(cur, environment, session_id):
    _lock_session(cur, environment, session_id)
    cur.execute('SELECT 1 FROM user_research.withdrawals WHERE session_id=%s AND environment=%s',
                (session_id, environment))
    if cur.fetchone():
        raise WithdrawnError()
    cur.execute('''INSERT INTO user_research.sessions AS existing(session_id,environment,consent_version)
                   VALUES(%s,%s,%s) ON CONFLICT(session_id,environment)
                   DO UPDATE SET last_seen_at=now(),consent_version=EXCLUDED.consent_version,
                   consent_at=CASE WHEN existing.consent_version IS DISTINCT FROM EXCLUDED.consent_version
                       THEN now() ELSE existing.consent_at END''', (session_id,environment,CONSENT_VERSION))


def _write_events(cur, environment, session_id, events):
    _session(cur, environment, session_id)
    accepted = 0
    for event in events:
        cur.execute('''INSERT INTO user_research.events
                       (event_id,environment,session_id,name,scene,duration_ms,error_code,source_count)
                       VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
                       ON CONFLICT(event_id,environment) DO NOTHING''',
                    (event['event_id'], environment, session_id, event['name'], event['scene'],
                     event.get('duration_ms'),event.get('error_code'),event.get('source_count')))
        accepted += cur.rowcount
    return {'ok':True,'session_id':session_id,'accepted':accepted,'duplicate':len(events)-accepted}


def write_events(db_url, app_env, payload):
    environment = _environment(app_env)
    session_id, events = validate_events(payload)
    with transaction(db_url) as cur:
        return _write_events(cur, environment, session_id, events)


def _write_feedback(cur, environment, session_id, feedback):
    _session(cur, environment, session_id)
    cur.execute('''INSERT INTO user_research.feedback(event_id,environment,session_id,rating,category,comment)
                   VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(event_id,environment) DO NOTHING''',
                (feedback['event_id'],environment,session_id,feedback['rating'],feedback['category'],feedback['comment']))
    accepted = cur.rowcount
    return {'ok':True,'session_id':session_id,'accepted':accepted,'duplicate':1-accepted}


def write_feedback(db_url, app_env, payload):
    environment = _environment(app_env)
    session_id, feedback = validate_feedback(payload)
    with transaction(db_url) as cur:
        return _write_feedback(cur, environment, session_id, feedback)


def _withdraw(cur, environment, session_id):
    _lock_session(cur, environment, session_id)
    cur.execute('''INSERT INTO user_research.withdrawals(session_id,environment) VALUES(%s,%s)
                   ON CONFLICT(session_id,environment) DO NOTHING''',(session_id,environment))
    cur.execute('DELETE FROM user_research.sessions WHERE session_id=%s AND environment=%s',(session_id,environment))
    return {'ok':True,'withdrawn':True,'session_id':session_id}


def withdraw(db_url, app_env, payload):
    _object(payload, ('session_id',), ('session_id',))
    session_id, environment = _uuid(payload['session_id']), _environment(app_env)
    with transaction(db_url) as cur:
        return _withdraw(cur, environment, session_id)


def validate_chat(payload):
    fields=('session_id','consent','consent_version','full_chat_consent','turn_id','conversation_id','turn_index','question','answer','status','revision','source_ids','error_code','truncated')
    _object(payload,fields,tuple(x for x in fields if x!='error_code'),max_bytes=393216)
    sid=_consent(payload)
    if payload['full_chat_consent'] is not True:raise InputError('Explicit full-chat consent is required.')
    turn={k:payload[k] for k in fields if k not in ('session_id','consent','consent_version','full_chat_consent') and k in payload}
    turn['turn_id']=_uuid(turn['turn_id']);turn['conversation_id']=_uuid(turn['conversation_id'])
    for key,minimum in (('turn_index',1),('revision',0)):
        if type(turn[key]) is not int or not minimum<=turn[key]<=1000000:raise InputError('Invalid turn order.')
    for key,minimum,maximum in (('question',1,12000),('answer',0,64000)):
        value=turn[key]
        if not isinstance(value,str) or not minimum<=len(value)<=maximum or any(ord(c)<32 and c not in '\n\r\t' for c in value):raise InputError('Invalid transcript text.')
    _choice(turn['status'],('submitted','complete','failed','clarification','interrupted'))
    if 'error_code' in turn:_choice(turn['error_code'],ERROR_CODES)
    if type(turn['truncated']) is not bool:raise InputError('Invalid truncation flag.')
    if not isinstance(turn['source_ids'],list) or len(turn['source_ids'])>100 or any(type(x) is not int or not 1<=x<=9223372036854775807 for x in turn['source_ids']):raise InputError('Invalid citations.')
    turn['source_ids']=list(dict.fromkeys(turn['source_ids']))
    return sid,turn


def _write_chat(cur,environment,sid,turn):
    _session(cur,environment,sid) # same lock/tombstone boundary as capture and deletion
    cur.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',('research-chat:'+environment+':'+turn['conversation_id'],))
    cur.execute('SELECT session_id FROM user_research.oracle_turns WHERE conversation_id=%s AND environment=%s LIMIT 1',(turn['conversation_id'],environment))
    previous=cur.fetchone()
    if previous and str(previous[0])!=sid:raise InputError('Conversation ownership differs.')
    cur.execute('SELECT session_id,conversation_id,turn_index,question FROM user_research.oracle_turns WHERE turn_id=%s AND environment=%s',(turn['turn_id'],environment))
    previous=cur.fetchone()
    if previous and (str(previous[0]),str(previous[1]),previous[2],previous[3])!=(sid,turn['conversation_id'],turn['turn_index'],turn['question']):raise InputError('Turn identity differs.')
    cur.execute("""INSERT INTO user_research.oracle_turns AS existing
      (turn_id,environment,session_id,conversation_id,turn_index,question,answer,status,revision,source_ids,error_code,truncated,consent_version)
      VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
      ON CONFLICT(turn_id,environment) DO UPDATE SET answer=EXCLUDED.answer,status=EXCLUDED.status,
      revision=EXCLUDED.revision,source_ids=EXCLUDED.source_ids,error_code=EXCLUDED.error_code,
      truncated=EXCLUDED.truncated,updated_at=now()
      WHERE existing.status='submitted' AND EXCLUDED.revision>existing.revision""",
      (turn['turn_id'],environment,sid,turn['conversation_id'],turn['turn_index'],turn['question'],turn['answer'],turn['status'],turn['revision'],turn['source_ids'],turn.get('error_code'),turn['truncated'],CONSENT_VERSION))
    return {'ok':True,'accepted':cur.rowcount}


def write_chat(db_url,app_env,payload):
    sid,turn=validate_chat(payload)
    with transaction(db_url) as cur:return _write_chat(cur,_environment(app_env),sid,turn)
