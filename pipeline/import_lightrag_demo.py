#!/usr/bin/env python3
# Last updated: 2026-10-18 10:00 UTC · Codex / Data-RAG · validated, atomic LightRAG→Neon projection import.
"""Preview by default. --apply writes the graph and its existing vectors atomically.

python3 pipeline/import_lightrag_demo.py --workspace /Users/lior/LightRAG
python3 pipeline/import_lightrag_demo.py --workspace /Users/lior/LightRAG --env-file .env.dev --apply
No raw chunk text, PDFs or TEI are uploaded. Existing scientific records are unchanged.
"""
import argparse
import base64
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import sys
import xml.etree.ElementTree as ET
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'analysis/rag_eval'))
from benchmark import digest


def load(path):
    return json.loads(path.read_text())


def vector_values(value, dim=1024):
    if isinstance(value, str):
        raw = zlib.decompress(base64.b64decode(value, validate=True))
        if len(raw) != dim * 2:
            raise ValueError('Expected compressed little-endian Float16 vector of dimension 1024')
        values = list(struct.unpack('<' + str(dim) + 'e', raw))
    else:
        values = list(value)
    if len(values) != dim or not all(math.isfinite(v) for v in values):
        raise ValueError('Invalid vector dimension or nonfinite coordinate')
    norm = math.sqrt(sum(v * v for v in values))
    if norm < 1e-8:
        raise ValueError('Zero embedding')
    return values


def vector_literal(value):
    return '[' + ','.join(format(v, '.9g') for v in value) + ']'


def dotenv(path):
    result = {}
    for line in path.read_text().splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            k, v = line.split('=', 1)
            result[k.strip()] = v.strip().strip('"').strip("'")
    return result


def refs(value):
    return sorted(set(filter(None, (value or '').split('<SEP>'))))


def normal_doi(value):
    return re.sub(r'^https?://(?:dx\.)?doi.org/', '', (value or '').strip().lower())


def prepare(workspace):
    storage = workspace / 'rag_storage'
    names = ['graph_chunk_entity_relation.graphml', 'kv_store_doc_status.json',
             'kv_store_text_chunks.json', 'vdb_entities.json', 'vdb_relationships.json']
    hashes = {n: digest(storage / n) for n in names}
    batch = 'lightrag-' + hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()[:24]
    config = dotenv(workspace / '.env')
    if config.get('EMBEDDING_MODEL') != 'bge-m3:latest' or int(config.get('EMBEDDING_DIM', '0')) != 1024:
        raise ValueError('This importer expects the inspected BGE-M3 1024-dimensional workspace')
    if config.get('EMBEDDING_QUERY_PREFIX', '').strip() or config.get('EMBEDDING_DOCUMENT_PREFIX', '').strip():
        raise ValueError('Nonempty embedding prefixes require an explicit query adapter')
    statuses = load(storage / 'kv_store_doc_status.json')
    chunks = load(storage / 'kv_store_text_chunks.json')
    docs = {}
    ns = {'t': 'http://www.tei-c.org/ns/1.0'}
    for key, row in statuses.items():
        if row.get('status') != 'processed':
            continue
        path = workspace / 'inputs/__parsed__' / Path(row['file_path']).name
        header = ET.parse(path).getroot().find('t:teiHeader', ns)
        dois = set(normal_doi(x.text) for x in header.findall('.//t:idno', ns)
                   if x.get('type', '').lower() == 'doi' and x.text) if header is not None else set()
        if len(dois) != 1:
            raise ValueError('Processed document must have one unambiguous DOI in its TEI header')
        docs[key] = {'doi': dois.pop(), 'tei_sha256': digest(path)}
    if not docs:
        raise ValueError('No processed documents')
    for key, row in chunks.items():
        if row.get('full_doc_id') not in docs:
            raise ValueError('Chunk references a failed or unmapped document')
    ns = {'g': 'http://graphml.graphdrawing.org/xmlns'}
    graph = ET.parse(storage / 'graph_chunk_entity_relation.graphml').getroot()
    keys = {x.get('id'): x.get('attr.name') for x in graph.findall('g:key', ns)}
    def attrs(row):
        return {keys[x.get('key')]: x.text or '' for x in row.findall('g:data', ns)}
    entities = {x.get('id'): attrs(x) for x in graph.findall('.//g:node', ns)}
    edges = {}
    for row in graph.findall('.//g:edge', ns):
        pair = tuple(sorted((row.get('source'), row.get('target'))))
        if pair in edges:
            raise ValueError('Parallel edges require a multigraph-aware import')
        edges[pair] = attrs(row)
    records, seen, evidence = [], set(), []
    entity_matches, edge_matches = set(), set()
    for kind, name in [('entity', 'vdb_entities.json'), ('relation', 'vdb_relationships.json')]:
        data = load(storage / name)
        if data.get('embedding_dim') != 1024:
            raise ValueError('Embedding dimension mismatch')
        for row in data['data']:
            item_id = row['__id__']
            if item_id in seen:
                raise ValueError('Duplicate vector item ID')
            seen.add(item_id)
            source_refs = refs(row.get('source_id'))
            if not source_refs or set(source_refs) - chunks.keys():
                raise ValueError('Vector item has missing/dangling evidence chunk IDs')
            entity_id, relation_id = None, None
            if kind == 'entity':
                entity_id = row['entity_name']
                if entity_id not in entities:
                    raise ValueError('Vector entity missing from graph')
                entity_matches.add(entity_id)
                graph_refs = refs(entities[entity_id].get('source_id'))
            else:
                pair = tuple(sorted((row['src_id'], row['tgt_id'])))
                if pair not in edges or set(pair) - entities.keys():
                    raise ValueError('Vector relation missing graph edge/endpoints')
                relation_id = item_id
                edge_matches.add(pair)
                graph_refs = refs(edges[pair].get('source_id'))
                row = dict(row, graph=edges[pair])
            if source_refs != graph_refs:
                raise ValueError('Graph and embedding evidence differ; freeze/rebuild workspace first')
            content = row['content']
            if not isinstance(content, str) or not content.strip():
                raise ValueError('Empty embedding input content')
            records.append(dict(item_id=item_id, kind=kind, entity_id=entity_id, relation_id=relation_id,
                content=content, content_sha256=hashlib.sha256(content.encode()).hexdigest(),
                embedding=vector_literal(vector_values(row['vector'])), row=row))
            evidence.extend((batch, item_id, chunk_id) for chunk_id in source_refs)
    if entity_matches != set(entities) or edge_matches != set(edges):
        raise ValueError('Graph/vector count reconciliation failed')
    if any(digest(storage / n) != h for n, h in hashes.items()):
        raise ValueError('Workspace changed during import preparation; stop ingestion and retry')
    manifest = {'input_hashes': hashes, 'documents': docs, 'embedding_revision': 'historical_digest_unknown',
        'vector_encoding': 'base64+zlib+little-endian-float16; copied without regeneration',
        'source_status_counts': dict(Counter(r.get('status') for r in statuses.values())),
        'expected_counts': {'documents': len(docs), 'chunks': len(chunks), 'entities': len(entities),
            'relations': len(edges), 'embeddings': len(records), 'evidence': len(evidence)},
        'embedding_model': config['EMBEDDING_MODEL'], 'document_prefix': '', 'query_prefix': '',
        'review_state': 'extracted_demo', 'raw_chunk_text_uploaded': False}
    return dict(batch=batch, docs=docs, chunks=chunks, entities=entities, records=records,
                evidence=evidence, manifest=manifest)


def migration_body():
    text = (ROOT / 'db/migrations/0015_lightrag_demo_pgvector.sql').read_text()
    return '\n'.join(line for line in text.splitlines() if line.strip() not in ('BEGIN;', 'COMMIT;'))


def apply(payload, env_file):
    import psycopg2
    from psycopg2.extras import execute_values, Json
    url = dotenv(env_file)['DATABASE_URL']
    connection = psycopg2.connect(url, connect_timeout=15)
    b = payload['batch']
    try:
        with connection:
            with connection.cursor() as cur:
                cur.execute("SET LOCAL statement_timeout = '180s'")
                cur.execute("SELECT pg_advisory_xact_lock(hashtext('meatcode_lightrag_demo_import'))")
                cur.execute('SELECT count(*) FROM sources')
                original_sources = cur.fetchone()[0]
                cur.execute("SELECT count(*) FROM pg_available_extensions WHERE name='vector'")
                if cur.fetchone()[0] != 1:
                    raise ValueError('vector extension unavailable on target Neon branch')
                cur.execute(migration_body())
                mapping = {}
                for doc, metadata in payload['docs'].items():
                    cur.execute("SELECT id FROM sources WHERE lower(regexp_replace(btrim(doi), '^https?://(dx\\.)?doi.org/', '')) = %s", (metadata['doi'],))
                    ids = cur.fetchall()
                    if len(ids) != 1:
                        raise ValueError('DOI does not resolve to exactly one Neon source')
                    mapping[doc] = ids[0][0]
                cur.execute('SELECT manifest FROM lightrag_demo.batches WHERE batch_id=%s', (b,))
                previous = cur.fetchone()
                if previous:
                    if previous[0] != payload['manifest']:
                        raise ValueError('Immutable batch ID has a different manifest')
                else:
                    cur.execute('INSERT INTO lightrag_demo.batches(batch_id,embedding_model,embedding_dimension,manifest) VALUES(%s,%s,1024,%s)',
                                (b, payload['manifest']['embedding_model'], Json(payload['manifest'])))
                    execute_values(cur, 'INSERT INTO lightrag_demo.documents VALUES %s',
                        [(b, k, mapping[k], v['doi']) for k, v in payload['docs'].items()])
                    execute_values(cur, 'INSERT INTO lightrag_demo.chunks VALUES %s',
                        [(b, k, v['full_doc_id'], v.get('chunk_order_index')) for k, v in payload['chunks'].items()])
                    execute_values(cur, 'INSERT INTO lightrag_demo.entities VALUES %s',
                        [(b, k, v.get('entity_type'), v.get('description', '')) for k, v in payload['entities'].items()])
                    relation_rows = []
                    for record in payload['records']:
                        if record['kind'] == 'relation':
                            row = record['row']; g = row['graph']
                            relation_rows.append((b, record['relation_id'], row['src_id'], row['tgt_id'],
                                g.get('description', ''), g.get('keywords'), float(g.get('weight') or 0)))
                    execute_values(cur, 'INSERT INTO lightrag_demo.relations VALUES %s', relation_rows)
                    execute_values(cur, 'INSERT INTO lightrag_demo.embeddings(batch_id,item_id,kind,entity_id,relation_id,content,content_sha256,embedding) VALUES %s',
                        [(b, r['item_id'], r['kind'], r['entity_id'], r['relation_id'], r['content'],
                          r['content_sha256'], r['embedding']) for r in payload['records']], page_size=100)
                    execute_values(cur, 'INSERT INTO lightrag_demo.evidence VALUES %s', payload['evidence'], page_size=500)
                # Counts and DOI mappings are verified on reruns too; no updates/deletes.
                for table, expected in payload['manifest']['expected_counts'].items():
                    cur.execute('SELECT count(*) FROM lightrag_demo.' + table + ' WHERE batch_id=%s', (b,))
                    if cur.fetchone()[0] != expected:
                        raise ValueError('Import reconciliation failed for ' + table)
                cur.execute('SELECT document_id,source_id FROM lightrag_demo.documents WHERE batch_id=%s', (b,))
                if dict(cur.fetchall()) != mapping:
                    raise ValueError('Stored source mapping changed')
                cur.execute('SELECT count(*) FROM sources')
                if cur.fetchone()[0] != original_sources:
                    raise ValueError('Scientific source count changed unexpectedly')
                cur.execute("SELECT count(*) FROM lightrag_demo.embeddings WHERE batch_id=%s AND vector_dims(embedding)<>1024", (b,))
                if cur.fetchone()[0]:
                    raise ValueError('Unexpected stored vector dimension')
        return {'status': 'verified_existing' if previous else 'imported', 'batch_id': b,
                'counts': payload['manifest']['expected_counts'], 'source_ids': sorted(mapping.values())}
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--env-file', type=Path, default=ROOT / '.env.dev')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        payload = prepare(args.workspace)
        result = apply(payload, args.env_file) if args.apply else {
            'status': 'validated_preview_no_network_no_writes', 'batch_id': payload['batch'],
            'manifest': payload['manifest'], 'dois': [d['doi'] for d in payload['docs'].values()]}
        print(json.dumps(result, indent=2))
    except Exception as exc:
        # Connection errors may contain credentials; never echo exception messages.
        print('Import failed: ' + type(exc).__name__ + '. No partial import is committed.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
