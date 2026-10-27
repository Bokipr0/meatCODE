#!/usr/bin/env python3
# Last updated: 2026-10-18 09:46 UTC · Codex / RAG · reproducible benchmark preparation and Oracle capture.
"""No server imports, database writes, or model calls during prepare/inventory.

prepare creates a frozen packet from the existing eight smoke-test questions.
capture records the REAL Oracle SSE endpoint; it does not duplicate retrieval.
Reviewed gold answers and scoring are separate from answer generation.
"""
import argparse
import ast
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import random
import time
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def load(path):
    return json.loads(path.read_text())


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents accidental replacement of a frozen run.
    with path.open('x') as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


def inventory(workspace):
    storage = workspace / 'rag_storage'
    statuses = load(storage / 'kv_store_doc_status.json')
    chunks = load(storage / 'kv_store_text_chunks.json')
    processed = {k for k, v in statuses.items() if v.get('status') == 'processed'}
    chunk_ids = set(chunks)
    ns = {'g': 'http://graphml.graphdrawing.org/xmlns'}
    graph = ET.parse(storage / 'graph_chunk_entity_relation.graphml').getroot()
    keys = {x.get('id'): x.get('attr.name') for x in graph.findall('g:key', ns)}
    nodes = graph.findall('.//g:node', ns)
    edges = graph.findall('.//g:edge', ns)
    counts = Counter()
    for row in nodes + edges:
        data = {keys.get(x.get('key')): x.text or '' for x in row.findall('g:data', ns)}
        refs = set(filter(None, data.get('source_id', '').split('<SEP>')))
        if not refs:
            counts['graph_records_without_chunk_refs'] += 1
        if refs - chunk_ids:
            counts['graph_records_with_unresolved_chunk_refs'] += 1
        if any(chunks.get(k, {}).get('full_doc_id') not in processed for k in refs):
            counts['graph_records_with_nonprocessed_document_refs'] += 1
    vectors = {}
    for name in ('entities', 'relationships', 'chunks'):
        raw = load(storage / ('vdb_' + name + '.json'))
        vectors[name] = {'dimension': raw.get('embedding_dim'), 'rows': len(raw.get('data', []))}
    files = sorted(storage.glob('*.json')) + sorted(storage.glob('*.graphml'))
    return {
        'captured_at': dt.datetime.now(dt.timezone.utc).isoformat(),
        'document_statuses': dict(Counter(v.get('status', 'unknown') for v in statuses.values())),
        'processed_document_ids': sorted(processed),
        'chunks': len(chunks), 'nodes': len(nodes), 'edges': len(edges),
        'chunks_outside_processed_documents': sum(v.get('full_doc_id') not in processed for v in chunks.values()),
        'provenance_checks': dict(counts), 'vectors': vectors,
        'file_sha256': {f.name: digest(f) for f in files},
        'notes': ['No passages, entity descriptions, filenames or secrets exported.',
                  'Local chunk provenance does not establish a mapping to Neon sources.id.',
                  'Inventory requires a quiescent workspace; stop ingestion before freezing.'],
    }


def server_constants():
    result = {}
    for node in ast.parse((ROOT / 'server/meatcode_server.py').read_text()).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ('SYSTEM_PROMPT', 'MODEL', 'MAX_TOKENS'):
                    result[target.id] = ast.literal_eval(node.value)
    return result


def prepare(out, workspace):
    out.mkdir(parents=True, exist_ok=False)
    config = server_constants()
    source = ROOT / 'analysis/rag_eval/questions.json'
    questions = load(source)['questions']
    save(out / 'questions.json', {'status': 'smoke_only_not_reviewed_gold', 'questions': questions})
    save(out / 'inventory.json', inventory(workspace))
    save(out / 'manifest.json', {
        'created_at': dt.datetime.now(dt.timezone.utc).isoformat(),
        'question_sha256': digest(out / 'questions.json'),
        'inventory_sha256': digest(out / 'inventory.json'),
        'server_sha256': digest(ROOT / 'server/meatcode_server.py'),
        'control_system_prompt': config['SYSTEM_PROMPT'],
        'oracle_source_model': config['MODEL'], 'max_output_tokens': config['MAX_TOKENS'],
        'arms_planned': ['direct_same_model', 'oracle_fts', 'vector_only', 'graph_hybrid', 'direct_other_model'],
        'repeats': 3, 'seed': 42, 'gold_status': 'pending_scientific_review',
    })
    save(out / 'gold.template.json', {'questions': [dict(
        id=q['id'], expected_claims=[], evidence=[], relevant_chunk_ids=[],
        answerable=None, reviewer=None, approved=False) for q in questions]})
    save(out / 'scores.template.json', {'rubric': 'See PROTOCOL.md; null means unscored.', 'rows': [dict(
        question_id=q['id'], blind_answer_id=None, correctness=None, completeness=None,
        supported_claims=None, checked_claims=None, correct_citations=None,
        checked_citations=None, appropriate_abstention=None, critical_errors=[], reviewer=None)
        for q in questions]})


def events(stream):
    kind, lines = 'message', []
    for raw in stream:
        line = raw.decode('utf-8').rstrip('\r\n')
        if not line:
            if lines:
                yield kind, '\n'.join(lines)
            kind, lines = 'message', []
        elif line.startswith('event:'):
            kind = line[6:].lstrip(' ')
        elif line.startswith('data:'):
            lines.append(line[5:].removeprefix(' '))
    if lines:
        yield kind, '\n'.join(lines)


def capture_one(url, question, headers):
    request = urllib.request.Request(url.rstrip('/') + '/api/ask',
        data=json.dumps({'question': question}).encode(),
        headers={'Content-Type': 'application/json', **headers})
    start = time.monotonic()
    record = {'status': 'incomplete', 'answer': '', 'sources': [], 'first_token_ms': None,
              'retrieval_health': 'unobservable_in_current_sse', 'usage': None, 'cost': None}
    with urllib.request.urlopen(request, timeout=180) as response:
        if 'text/event-stream' not in response.headers.get('Content-Type', ''):
            raise ValueError('Expected SSE; authentication or endpoint may be wrong')
        for kind, value in events(response):
            if kind == 'sources':
                record['sources'] = json.loads(value)
            elif kind == 'retrieval':
                record['retrieval'] = json.loads(value)
                record['retrieval_health'] = record['retrieval'].get('retrieval_ok')
            elif kind == 'chunk':
                if record['first_token_ms'] is None:
                    record['first_token_ms'] = round((time.monotonic() - start) * 1000)
                record['answer'] += value
            elif kind == 'error':
                record['status'] = 'error'
                break
            elif kind == 'done':
                record['status'] = 'ok' if record['answer'].strip() else 'empty_answer'
                break  # keep-alive socket need not close after the final SSE event
    record['total_ms'] = round((time.monotonic() - start) * 1000)
    return record


def capture(packet, url):
    manifest = load(packet / 'manifest.json')
    if digest(packet / 'questions.json') != manifest['question_sha256']:
        raise ValueError('Frozen question packet changed')
    headers = {}
    if os.environ.get('BENCHMARK_AUTHORIZATION'):
        headers['Authorization'] = os.environ['BENCHMARK_AUTHORIZATION']
    req = urllib.request.Request(url.rstrip('/') + '/api/version', headers=headers)
    with urllib.request.urlopen(req, timeout=15) as response:
        version = json.load(response)
    jobs = [(q, i) for q in load(packet / 'questions.json')['questions']
            for i in range(manifest['repeats'])]
    random.Random(manifest['seed']).shuffle(jobs)
    # A fresh journal per invocation. Failed rows remain failures; no hidden retries.
    path = packet / ('oracle_' + dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%f') + '.jsonl')
    with path.open('x') as stream:
        for q, repeat in jobs:
            try:
                record = capture_one(url, q['question'], headers)
            except Exception as exc:
                record = {'status': 'error', 'error_type': type(exc).__name__}
            mode = record.get('retrieval', {}).get('mode', 'fts')
            record.update(question_id=q['id'], repeat=repeat, arm='oracle_' + mode, version=version,
                          question_sha256=manifest['question_sha256'])
            stream.write(json.dumps(record, ensure_ascii=False) + '\n')
            stream.flush()
    print(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    audit = sub.add_parser('inventory')
    audit.add_argument('--workspace', type=Path, required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('--workspace', type=Path, required=True)
    prep.add_argument('--out', type=Path, required=True)
    cap = sub.add_parser('capture-oracle')
    cap.add_argument('--packet', type=Path, required=True)
    cap.add_argument('--url', required=True)
    args = parser.parse_args()
    if args.command == 'inventory':
        print(json.dumps(inventory(args.workspace), indent=2))
    elif args.command == 'prepare':
        prepare(args.out, args.workspace)
        print(args.out)
    else:
        capture(args.packet, args.url)


if __name__ == '__main__':
    main()
