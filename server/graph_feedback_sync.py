# Last updated: 2026-11-18 · Codex · durable native LightRAG feedback synchronization.
"""Materialize user contributions through the running LightRAG writer and indexes.

The outbox remains in graph_oracle's private state. Contributions have their own
entity names and source pages, so published-paper evidence is not reassigned.
"""
import json
import os
from pathlib import Path
import tempfile
import threading
import time
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

WORKER_LOCK = threading.Lock()
WORKER = None


class PendingSync(RuntimeError):
    pass


class LightRAGWriter:
    def __init__(self, base_url, storage):
        parsed = urlsplit(base_url)
        if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost', '::1') or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise PendingSync('Configure a loopback LightRAG service URL.')
        self.url = base_url.rstrip('/')
        self.storage = Path(storage).resolve()

    def request(self, path, payload=None):
        headers = {'Accept': 'application/json'}
        key = os.environ.get('KG_ORACLE_LIGHTRAG_API_KEY')
        if key:
            headers['X-API-Key'] = key
        data = None
        if payload is not None:
            headers['Content-Type'] = 'application/json'
            data = json.dumps(payload).encode()
        request = Request(self.url + path, data=data, headers=headers)
        try:
            with urlopen(request, timeout=60) as response:
                return json.load(response)
        except HTTPError as exc:
            if exc.code in (401, 403):
                raise PendingSync('LightRAG needs an authorized local API key.') from None
            if exc.code in (409, 423):
                raise PendingSync('LightRAG is processing another job. Retrying shortly.') from None
            raise PendingSync('LightRAG has not accepted this update. Retrying shortly.') from None
        except (OSError, ValueError):
            raise PendingSync('Waiting for the local LightRAG service.') from None

    def ready(self):
        status = self.request('/health')
        if status.get('status') != 'healthy':
            raise PendingSync('Waiting for a healthy LightRAG service.')
        if Path(status.get('working_directory', '')).resolve() != self.storage:
            raise PendingSync('LightRAG is serving a different graph directory.')
        if status.get('configuration', {}).get('workspace'):
            raise PendingSync('Configure a LightRAG workspace matching this graph export.')
        pipeline = self.request('/documents/pipeline_status')
        if pipeline.get('busy') or pipeline.get('scanning'):
            raise PendingSync('LightRAG is processing another job. Retrying shortly.')

    def upsert_node(self, name, values):
        # Editing only our unique annotation IDs also repairs a partial graph/vector write.
        found = self.request('/graph/entity/exists?' + urlencode({'name': name}))
        if found.get('exists'):
            return self.request('/graph/entity/edit', {'entity_name': name, 'updated_data': values})
        return self.request('/graph/entity/create', {'entity_name': name, 'entity_data': values})

    def upsert_edge(self, source, target, values):
        # The graph API has no edge-exists read. Create first, then repair/verify
        # a duplicate using the exact endpoint names and our unique feedback node.
        try:
            return self.request('/graph/relation/create', {'source_entity': source, 'target_entity': target, 'relation_data': values})
        except PendingSync:
            return self.request('/graph/relation/edit', {'source_id': source, 'target_id': target, 'updated_data': values})

    def verify(self, name, targets):
        result = self.request('/graphs?' + urlencode({'label': name, 'max_depth': 1, 'max_nodes': len(targets) + 2}))
        nodes = {n['id']: n for n in result.get('nodes', [])}
        if name not in nodes:
            raise PendingSync('Waiting for LightRAG to expose the indexed contribution.')
        pairs = {frozenset((e['source'], e['target'])) for e in result.get('edges', [])}
        if any(frozenset((name, target)) not in pairs for target in targets):
            raise PendingSync('Some feedback connections are still waiting to synchronize.')


def wiki_page(folder, feedback):
    directory = folder / 'wiki' / 'feedback'
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = directory / (feedback['id'] + '.md')
    content = '\n'.join([
        '# MeatCODE user contribution', '',
        'Evidence status: unverified user feedback. This page records a contribution, not a published scientific finding.',
        '', 'Feedback ID: ' + feedback['id'], 'Map ID: ' + feedback['map_id'],
        'Source graph version: ' + feedback['source_graph_version'],
        'Revision: ' + str(feedback['revision']), '', '## Referenced graph entities',
        *['- ' + json.dumps(entity, ensure_ascii=False) for entity in feedback['entity_ids']],
        '', '## Contribution text',
        *['> ' + line for line in feedback['comment'].splitlines()], ''
    ])
    fd, temporary = tempfile.mkstemp(dir=directory, prefix='.feedback-')
    try:
        with os.fdopen(fd, 'w') as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return path


def sync_contribution(feedback, graph_path, state_folder, writer):
    writer.ready()
    name = 'MEATCODE_FEEDBACK_' + feedback['id']
    page = wiki_page(state_folder, feedback)
    description = ('UNVERIFIED USER FEEDBACK. Map ' + feedback['map_id'] +
                   '; source graph ' + feedback['source_graph_version'] +
                   '; contribution: ' + feedback['comment'])
    writer.upsert_node(name, {'entity_type': 'MEATCODE_FEEDBACK', 'description': description,
                             'source_id': '', 'file_path': str(page)})
    for target in sorted(set(feedback['entity_ids'])):
        writer.upsert_edge(name, target, {
            'description': 'UNVERIFIED USER FEEDBACK annotates ' + target + '. ' + feedback['comment'],
            'keywords': 'user_feedback, annotates, unverified',
            'source_id': '', 'file_path': str(page), 'weight': 0.1
        })
    writer.verify(name, feedback['entity_ids'])
    return {'status': 'synced', 'entity_id': name, 'wiki_page': str(page),
            'synced_at': time.time(), 'message': 'Contribution synchronized to LightRAG and its search indexes.'}


def sync_pending_once(graph_module, writer=None):
    graph_path, folder = graph_module.configuration()
    with graph_module.LOCK:
        state = graph_module.state_read()
        pending = next((dict(f) for f in state['feedback']
                        if f.get('native_sync', {}).get('status') != 'synced'
                        and f.get('native_sync', {}).get('retry_at', 0) <= time.time()), None)
    if pending is None:
        return False
    try:
        writer = writer or LightRAGWriter(os.environ['KG_ORACLE_LIGHTRAG_URL'], graph_path.parent)
        result = sync_contribution(pending, graph_path, folder, writer)
    except PendingSync as exc:
        result = {'status': 'pending', 'message': str(exc), 'retry_at': time.time() + 30}
    except Exception:
        result = {'status': 'pending', 'message': 'Graph synchronization is waiting to retry.', 'retry_at': time.time() + 30}
    with graph_module.LOCK:
        state = graph_module.state_read()
        for feedback in state['feedback']:
            if feedback['id'] == pending['id']:
                feedback['native_sync'] = result
                break
        graph_module.state_write(state)
    return True


def start_worker(graph_module):
    global WORKER
    if not os.environ.get('KG_ORACLE_LIGHTRAG_URL'):
        return
    with WORKER_LOCK:
        if WORKER is not None and WORKER.is_alive():
            return
        def run():
            while True:
                try:
                    sync_pending_once(graph_module)
                except Exception:
                    pass  # Outbox survives an unavailable graph or a service restart.
                time.sleep(2)
        WORKER = threading.Thread(target=run, name='meatcode-feedback-sync', daemon=True)
        WORKER.start()


def status(feedback):
    enabled = bool(os.environ.get('KG_ORACLE_LIGHTRAG_URL'))
    synced = sum(f.get('native_sync', {}).get('status') == 'synced' for f in feedback)
    pending = len(feedback) - synced
    return {'enabled': enabled, 'synced': synced, 'pending': pending,
            'message': ('LightRAG feedback connection is not configured.' if not enabled else
                        'Graph updates are synchronizing.' if pending else
                        'Graph feedback is synchronized.')}
