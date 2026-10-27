# Last updated: 2026-10-18 09:46 UTC · Codex / RAG · SSE, provenance and frozen-packet checks.
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import benchmark as b


class BenchmarkTests(unittest.TestCase):
    def test_sse_multiline_and_unknown_events(self):
        stream = io.BytesIO(b': heartbeat\r\nevent: chunk\r\ndata: first\r\ndata: second\r\n\r\nevent: done\ndata: \n\n')
        self.assertEqual(list(b.events(stream)), [('chunk', 'first\nsecond'), ('done', '')])

    def test_done_does_not_wait_for_socket_close(self):
        class Response:
            headers = {'Content-Type': 'text/event-stream'}
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def __iter__(self):
                yield from [b'event: sources\n', b'data: [{"id": 12}]\n', b'\n',
                            b'event: chunk\n', b'data: answer [12]\n', b'\n',
                            b'event: done\n', b'data: \n', b'\n']
                raise AssertionError('Read beyond done on keep-alive connection')
        with patch.object(b.urllib.request, 'urlopen', return_value=Response()):
            result = b.capture_one('http://localhost:8000', 'question', {})
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['answer'], 'answer [12]')
        self.assertEqual(result['sources'], [{'id': 12}])
        self.assertIsNone(result['cost'])

    def test_truncated_stream_is_not_success(self):
        class Response(io.BytesIO):
            headers = {'Content-Type': 'text/event-stream'}
        with patch.object(b.urllib.request, 'urlopen', return_value=Response(b'event: chunk\ndata: partial\n\n')):
            self.assertEqual(b.capture_one('http://localhost', 'q', {})['status'], 'incomplete')

    def test_failed_document_and_dangling_graph_refs(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            storage = workspace / 'rag_storage'
            storage.mkdir()
            def write(name, value): (storage / name).write_text(json.dumps(value))
            write('kv_store_doc_status.json', {'ok': {'status': 'processed'}, 'bad': {'status': 'failed'}})
            write('kv_store_text_chunks.json', {'c1': {'full_doc_id': 'ok'}, 'c2': {'full_doc_id': 'bad'}})
            for name in ('entities', 'relationships', 'chunks'):
                write('vdb_' + name + '.json', {'embedding_dim': 1024, 'data': []})
            (storage / 'graph_chunk_entity_relation.graphml').write_text(
                '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">'
                '<key id="s" attr.name="source_id"/><graph>'
                '<node id="n1"><data key="s">c2&lt;SEP&gt;missing</data></node>'
                '<node id="n2"/></graph></graphml>')
            result = b.inventory(workspace)
            self.assertEqual(result['chunks_outside_processed_documents'], 1)
            self.assertEqual(result['provenance_checks']['graph_records_with_unresolved_chunk_refs'], 1)
            self.assertEqual(result['provenance_checks']['graph_records_without_chunk_refs'], 1)
            self.assertEqual(result['provenance_checks']['graph_records_with_nonprocessed_document_refs'], 1)

    def test_changed_frozen_questions_prevent_network_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            packet = Path(directory)
            b.save(packet / 'manifest.json', {'question_sha256': 'wrong'})
            b.save(packet / 'questions.json', {'questions': []})
            with patch.object(b.urllib.request, 'urlopen') as request:
                with self.assertRaisesRegex(ValueError, 'changed'):
                    b.capture(packet, 'http://localhost')
                request.assert_not_called()


if __name__ == '__main__':
    unittest.main()
