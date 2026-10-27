# Last updated: 2026-10-18 10:00 UTC · Codex / RAG · graph import, evidence and score-policy regression checks.
import ast
import base64
import importlib.util
import json
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch
import zlib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'server'))
import lightrag_retrieval as retrieval
spec = importlib.util.spec_from_file_location('import_demo', ROOT / 'pipeline/import_lightrag_demo.py')
importer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(importer)


class GraphDemoTests(unittest.TestCase):
    def test_decode_original_float16_encoding(self):
        vector = [1.0] + [0.0] * 1023
        compressed = base64.b64encode(zlib.compress(struct.pack('<1024e', *vector))).decode()
        self.assertEqual(importer.vector_values(compressed), vector)
        self.assertEqual(len(json.loads(importer.vector_literal(vector))), 1024)

    def test_reject_invalid_vector_and_zero_vector(self):
        for vector in ([0.0] * 1024, [1.0] * 1023, [float('nan')] * 1024):
            with self.assertRaises(ValueError):
                importer.vector_values(vector)

    def test_query_embedding_compatibility_is_checked(self):
        def run(sql, params):
            return [{'content': 'reference', 'vector': json.dumps([1.0] + [0.0] * 1023)}]
        retrieval._verified.clear()
        with patch.object(retrieval, 'embedding', return_value=[0.0, 1.0] + [0.0] * 1022):
            with self.assertRaisesRegex(ValueError, 'differs'):
                retrieval.verify_model('test', 'bge', run)

    def test_no_score_cutoff_in_all_three_retrieval_queries(self):
        for name, variable in [('server/meatcode_server.py', '_RETRIEVAL_SQL'),
                               ('analysis/oracle_eval/run_eval.py', 'RETRIEVAL_SQL'),
                               ('analysis/rag_eval/run_eval.py', 'RETRIEVAL_SQL')]:
            tree = ast.parse((ROOT / name).read_text())
            value = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                         and any(isinstance(t, ast.Name) and t.id == variable for t in n.targets))
            self.assertNotIn('relevance_llm', value)
            self.assertEqual(value.count('%s'), 2)

    def test_graph_evidence_is_bounded_and_source_ids_preserved(self):
        result = {'sources': [{'id': 275}, {'id': 833}], 'items': [
            {'content': 'A' * 1200, 'source_ids': [275, 833]} for _ in range(20)]}
        rows = retrieval.oracle_rows(result)
        self.assertTrue(rows)
        # Separators are the only extra characters beyond the content budget.
        self.assertLessEqual(sum(len(r['graph_evidence']) for r in rows), 8050)
        self.assertTrue(all(r['evidence_state'] == 'extracted_demo' for r in rows))
        self.assertTrue(all(r['id'] in [275, 833] for r in rows))

    def test_missing_graph_does_not_call_embedding_service(self):
        def run(sql, params=()): return [{'installed': False}]
        with patch.object(retrieval, 'embedding') as model:
            result = retrieval.search('protein flavor', run)
        self.assertEqual(result['status'], 'not_imported')
        model.assert_not_called()

    def test_embedding_failure_reports_lexical_mode_and_expands_graph(self):
        def run(sql, params=()):
            if 'to_regclass' in sql: return [{'installed': True}]
            if 'FROM lightrag_demo.batches' in sql:
                return [{'batch_id': 'b', 'embedding_model': 'bge', 'embedding_dimension': 1024,
                         'created_at': 'now', 'review_state': 'extracted_demo',
                         'manifest': {'expected_counts': {'entities': 2}}}]
            if 'ts_rank_cd' in sql:
                return [{'item_id': 'e', 'kind': 'entity', 'entity_id': 'protein',
                         'relation_id': None, 'content': 'protein binds aroma', 'score': .2}]
            if 'r.weight DESC' in sql:
                return [{'item_id': 'r', 'kind': 'relation', 'entity_id': None,
                         'relation_id': 'r', 'content': 'binding changes release', 'score': 0.0}]
            if 'FROM lightrag_demo.evidence' in sql:
                return [dict(item_id=k, chunk_id='c1', source_id=275, title='paper', doi='doi',
                             url=None, year=2026, journal='journal') for k in ['e', 'r']]
            self.fail('Unexpected query: ' + sql)
        with patch.object(retrieval, 'verify_model', side_effect=ConnectionError()):
            result = retrieval.search('protein flavor', run)
        self.assertEqual(result['mode'], 'lexical_graph')
        self.assertEqual(result['embedding_issue'], 'ConnectionError')
        self.assertEqual(len(result['items']), 2)
        self.assertEqual(result['items'][1]['origin'], 'graph_neighbor')
        self.assertEqual(result['sources'][0]['id'], 275)

    def test_migration_remains_inside_importer_transaction(self):
        statements = [s.strip() for s in importer.migration_body().splitlines()]
        self.assertNotIn('COMMIT;', statements)
        self.assertNotIn('BEGIN;', statements)
        self.assertIn('CREATE EXTENSION IF NOT EXISTS vector;', statements)


if __name__ == '__main__':
    unittest.main()
