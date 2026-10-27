# Last updated: 2026-10-18 10:00 UTC · Codex / RAG · Neon graph/vector demo retrieval.
"""Read-only retrieval of the dedicated extracted-demo projection.

No raw passages are served. The DB accessor is supplied by the application.
Local Ollama embeds only the user query and a compatibility reference text.
An unavailable embedding service is explicitly reported as lexical_graph fallback.
"""
import json
import math
import os
import re
import threading
import time
import urllib.request

_verified = set()
_verification_lock = threading.Lock()


def enabled(app_env):
    return app_env == 'dev' and os.environ.get('ORACLE_GRAPH_DEMO', '1') == '1'


def embedding(text, model):
    host = os.environ.get('OLLAMA_EMBED_URL', 'http://127.0.0.1:11434').rstrip('/')
    request = urllib.request.Request(host + '/api/embed',
        data=json.dumps({'model': model, 'input': text, 'truncate': False}).encode(),
        headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=20) as response:
        data = json.load(response)
    values = data['embeddings'][0]
    if len(values) != 1024 or not all(isinstance(x, (int, float)) and math.isfinite(x) for x in values):
        raise ValueError('Invalid query embedding')
    if sum(x * x for x in values) < 1e-8:
        raise ValueError('Zero query vector')
    return values


def vector_literal(values):
    return '[' + ','.join(format(x, '.9g') for x in values) + ']'


def verify_model(batch, model, run):
    """Pin compatibility with historical embeddings whose exact model digest is unknown."""
    cache_key = (batch, model, os.environ.get('OLLAMA_EMBED_URL', ''), int(time.monotonic() // 300))
    with _verification_lock:
        if cache_key in _verified:
            return
        rows = run('SELECT content, embedding::text AS vector FROM lightrag_demo.embeddings '
                   'WHERE batch_id=%s ORDER BY length(content), item_id LIMIT 1', (batch,))
        if not rows:
            raise ValueError('No reference embedding')
        old = json.loads(rows[0]['vector'])
        new = embedding(rows[0]['content'], model)
        cosine = sum(a * b for a, b in zip(old, new)) / math.sqrt(sum(a*a for a in old) * sum(b*b for b in new))
        if cosine < .99:
            raise ValueError('Query embedding model differs from stored vector space')
        _verified.clear()
        _verified.add(cache_key)


def status(run):
    found = run("SELECT to_regclass('lightrag_demo.batches') IS NOT NULL AS installed")
    if not found[0]['installed']:
        return {'status': 'not_imported', 'relevance_gate': None}
    rows = run('SELECT batch_id,created_at,embedding_model,embedding_dimension,manifest,review_state '
               'FROM lightrag_demo.batches ORDER BY created_at DESC LIMIT 1')
    if not rows:
        return {'status': 'not_imported', 'relevance_gate': None}
    batch = rows[0]
    return {'status': 'imported', 'batch_id': batch['batch_id'],
            'embedding_model': batch['embedding_model'], 'dimension': batch['embedding_dimension'],
            'counts': batch['manifest']['expected_counts'], 'review_state': batch['review_state'],
            'created_at': batch['created_at'], 'relevance_gate': None}


def search(question, run, limit=8):
    start = time.monotonic()
    state = status(run)
    if state['status'] != 'imported':
        return {**state, 'items': [], 'sources': [], 'mode': 'unavailable'}
    batch = state['batch_id']
    mode, vectors, embedding_issue = 'vector_graph', None, None
    try:
        verify_model(batch, state['embedding_model'], run)
        vectors = embedding(question, state['embedding_model'])
    except Exception as exc:
        mode, embedding_issue = 'lexical_graph', type(exc).__name__
    limit = max(1, min(int(limit), 20))
    if vectors is not None:
        seeds = run('SELECT item_id,kind,entity_id,relation_id,content,1-(embedding <=> %s::vector) AS score '
                    'FROM lightrag_demo.embeddings WHERE batch_id=%s '
                    'ORDER BY embedding <=> %s::vector, item_id LIMIT %s',
                    (vector_literal(vectors), batch, vector_literal(vectors), limit))
    else:
        # Use significant OR terms rather than requiring every word of a question.
        stop = {'what','which','where','when','does','with','from','that','this','have','their','about','into','would','could','should','there','these','those'}
        terms = [x for x in re.findall(r"[\w-]+", question.lower()) if len(x) >= 3 and x not in stop]
        if not terms:
            return {**state, 'items': [], 'sources': [], 'mode': mode, 'embedding_issue': embedding_issue}
        query = ' OR '.join(terms[:24])
        seeds = run("SELECT item_id,kind,entity_id,relation_id,content,ts_rank_cd(search_vec,websearch_to_tsquery('english',%s)) AS score "
                    "FROM lightrag_demo.embeddings WHERE batch_id=%s AND search_vec @@ websearch_to_tsquery('english',%s) "
                    'ORDER BY score DESC,item_id LIMIT %s', (query, batch, query, limit))
    entity_ids = [s['entity_id'] for s in seeds if s.get('entity_id')]
    relation_ids = [s['relation_id'] for s in seeds if s.get('relation_id')]
    if relation_ids:
        endpoints = run('SELECT source_entity,target_entity FROM lightrag_demo.relations WHERE batch_id=%s AND relation_id=ANY(%s)',
                        (batch, relation_ids))
        entity_ids.extend(v for row in endpoints for v in (row['source_entity'], row['target_entity']))
    expanded = []
    if entity_ids:
        expanded = run('SELECT e.item_id,e.kind,e.entity_id,e.relation_id,e.content,0.0 AS score '
            'FROM lightrag_demo.relations r JOIN lightrag_demo.embeddings e '
            "ON e.batch_id=r.batch_id AND e.relation_id=r.relation_id AND e.kind='relation' "
            'WHERE r.batch_id=%s AND (r.source_entity=ANY(%s) OR r.target_entity=ANY(%s)) '
            'ORDER BY r.weight DESC,r.relation_id LIMIT %s', (batch, sorted(set(entity_ids)), sorted(set(entity_ids)), limit))
    items, seen = [], set()
    for row in seeds + expanded:
        if row['item_id'] not in seen:
            seen.add(row['item_id'])
            items.append(dict(row, origin='seed' if row in seeds else 'graph_neighbor'))
    if not items:
        return {**state, 'items': [], 'sources': [], 'mode': mode, 'embedding_issue': embedding_issue}
    evidence = run('SELECT ev.item_id,ev.chunk_id,d.source_id,s.name AS title,s.doi,s.url,s.year, '
        'COALESCE(s.journal,s.venue) AS journal '
        'FROM lightrag_demo.evidence ev JOIN lightrag_demo.chunks c ON c.batch_id=ev.batch_id AND c.chunk_id=ev.chunk_id '
        'JOIN lightrag_demo.documents d ON d.batch_id=c.batch_id AND d.document_id=c.document_id '
        'JOIN sources s ON s.id=d.source_id WHERE ev.batch_id=%s AND ev.item_id=ANY(%s) '
        'ORDER BY ev.item_id,d.source_id,ev.chunk_id', (batch, list(seen)))
    source_map = {}
    for item in items:
        refs = [r for r in evidence if r['item_id'] == item['item_id']]
        item['source_ids'] = sorted(set(r['source_id'] for r in refs))
        item['chunk_ids'] = sorted(set(r['chunk_id'] for r in refs))
        for ref in refs:
            source_map[ref['source_id']] = {k: ref[k] for k in ('source_id','title','doi','url','year','journal')}
    return {**state, 'mode': mode, 'embedding_issue': embedding_issue, 'items': items,
            'sources': [dict(r, id=r['source_id']) for r in source_map.values()],
            'retrieval_ms': round((time.monotonic()-start)*1000)}


def oracle_rows(result):
    """Bound descriptions to 8k characters; retain at least one evidence item per selected source."""
    snippets = {r['id']: [] for r in result['sources']}
    budget = 8000
    for item in result['items']:
        content = item['content'][:1200]
        if len(content) > budget:
            break
        for sid in item['source_ids']:
            if sid in snippets and len(content) <= budget:
                snippets[sid].append(content)
                budget -= len(content)
    return [dict(source, abstract='', main_claim='', graph_evidence='\n\n'.join(snippets[source['id']]),
                 evidence_state='extracted_demo') for source in result['sources'] if snippets[source['id']]]
