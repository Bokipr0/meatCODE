# Last updated: 2026-11-22 11:55 UTC · Claude (Fable 5.2) · continue-on-failure mode + retry cap tests · 2026-11-21 Sonnet 5.5 · hosted-target checks added (28 grobid tests pass)
"""Regression checks for paper-level, pre-graph deduplication."""

from pathlib import Path
import json
import os
import tempfile
import time
import unittest
import urllib.error
from unittest.mock import patch

import batch_worker as worker


def tei(doi: str | None, body: str, cited_doi: str | None = None) -> bytes:
    own_id = f'<idno type="DOI">{doi}</idno>' if doi else ""
    citation = (f'<back><listBibl><biblStruct><idno type="DOI">{cited_doi}</idno>'
                f'</biblStruct></listBibl></back>') if cited_doi else ""
    return (f'<TEI xmlns="http://www.tei-c.org/ns/1.0"><teiHeader><fileDesc>'
            f'<sourceDesc><biblStruct>{own_id}</biblStruct></sourceDesc>'
            f'</fileDesc></teiHeader><text><body><p>{body}</p></body>{citation}'
            f'</text></TEI>').encode()


class BatchWorkerTests(unittest.TestCase):
    def test_paper_doi_never_uses_reference_doi(self):
        self.assertIsNone(worker.paper_doi(tei(None, "Paper text", "10.1234/reference")))
        self.assertEqual(worker.paper_doi(tei("10.1234/OWN", "Paper text",
                                               "10.1234/reference")), "10.1234/own")

    def test_invalid_cloud_key_is_caught_before_ingestion(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / ".env"
            config.write_text("LLM_BINDING_HOST=https://api.anthropic.com/v1\n"
                              "LLM_BINDING=openai\nLLM_MODEL=claude-sonnet-4-6\n"
                              "LLM_BINDING_API_KEY=test-invalid\n")
            error = urllib.error.HTTPError("https://api.anthropic.com/v1/models",
                                           401, "invalid", {}, None)
            with patch.object(worker.urllib.request, "urlopen", side_effect=error):
                with self.assertRaisesRegex(ValueError, "HTTP 401") as caught:
                    worker.check_remote_extraction_key(config)
            self.assertNotIn("test-invalid", str(caught.exception))
            error.close()

    def test_stale_local_keyword_model_blocks_ingestion(self):
        route = {'binding': 'openai', 'model': 'claude-sonnet-4-6',
                 'host': 'https://api.anthropic.com/v1/'}
        config = {'llm_binding': route['binding'], 'llm_model': route['model'],
                  'llm_binding_host': route['host'],
                  'role_llm_config': {k: dict(route) for k in ('extract','keyword','query','vlm')}}
        worker.check_runtime_reasoning({'configuration': config})
        config['role_llm_config']['keyword'] = {'binding':'ollama',
            'model':'qwen3.5:9b','host':'http://localhost:11434'}
        with self.assertRaisesRegex(ValueError, 'Anthropic'):
            worker.check_runtime_reasoning({'configuration': config})

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inbox = self.root / "inbox"
        self.output = self.root / "output"
        self.inbox.mkdir()
        self.output.mkdir()
        self.graph = self.root / "graph.json"
        self.graph.write_text("{}")
        self.ledger = worker.connect_ledger(self.output / "papers.sqlite")
        self.addCleanup(self.ledger.close)

    def pdf(self, name: str, marker: str) -> Path:
        path = self.inbox / name
        path.write_bytes(b"%PDF-1.4\n" + marker.encode())
        os.utime(path, (time.time() - 100, time.time() - 100))
        return path

    def fake_parse(self, doi: str | None, body: str):
        xml = self.output / "source.tei.xml"
        text = self.output / "source.body.txt"
        xml.write_bytes(tei(doi, body))
        text.write_text(body)
        return {"tei_file": str(xml), "scientific_body_file": str(text)}

    def process(self, pdf: Path, doi: str | None, body: str, api):
        with patch.object(worker.core, "parse_pdf",
                          side_effect=lambda _: self.fake_parse(doi, body)) as parse:
            with patch.object(worker, "api_json", side_effect=api) as request, \
                 patch.object(worker.claims, "extract", return_value={'claims': []}):
                worker.process_pdf(pdf, self.inbox, self.output, self.graph,
                                   self.ledger, "http://localhost:9621", None, 0)
        return parse, request

    def status(self, pdf: Path) -> str:
        digest = worker.hashlib.sha256(pdf.read_bytes()).hexdigest()
        return self.ledger.execute(
            "SELECT status FROM papers WHERE pdf_sha256=?", (digest,)
        ).fetchone()["status"]

    def test_hosted_target_requires_https_and_key(self):
        key = "k" * 40
        worker.validate_target("http://127.0.0.1:9621", None)
        worker.validate_target("https://meatcode-lightrag.onrender.com", key)
        for url, k in (("http://meatcode-lightrag.onrender.com", key),
                       ("https://meatcode-lightrag.onrender.com", None),
                       ("https://meatcode-lightrag.onrender.com", "short"),
                       ("https://user:pw@meatcode-lightrag.onrender.com", key)):
            with self.assertRaises(ValueError):
                worker.validate_target(url, k)

    def test_hosted_inventory_flags_documents_added_outside_worker(self):
        pages = [{"documents": [{"file_path": "known.txt"}], "pagination": {"has_next": True}},
                 {"documents": [{"file_path": "webui-upload.pdf"}], "pagination": {"has_next": False}}]
        with patch.object(worker, "api_json", side_effect=pages) as call:
            unknown = worker.hosted_unreviewed("https://h", "k" * 40, {"known.txt"})
        self.assertEqual(unknown, ["webui-upload.pdf"])
        self.assertEqual(call.call_count, 2)

    def test_hosted_run_pauses_before_any_submission_when_graph_has_unreviewed_docs(self):
        self.pdf("a.pdf", "a")
        args = type("A", (), dict(lightrag_url="https://h.example", api_key="k" * 40, inbox=self.inbox,
                                  output=self.output, graph=self.graph, min_age=0))()
        health = {"configuration": {"llm_binding": "openai", "llm_model": "claude-sonnet-4-6",
                  "llm_binding_host": "https://api.anthropic.com/v1/",
                  "role_llm_config": {k: {"binding": "openai", "model": "claude-sonnet-4-6",
                  "host": "https://api.anthropic.com/v1/"} for k in ("extract", "keyword", "query", "vlm")}}}
        class R:
            status = 200
            def __enter__(s): return s
            def __exit__(s, *a): pass
            def read(s): return b"true"
        with patch.object(worker.ingestion_control, "paused", return_value=False), \
             patch.object(worker, "poll_submitted"), \
             patch.object(worker.urllib.request, "urlopen", return_value=R()), \
             patch.object(worker, "api_json", return_value=health), \
             patch.object(worker, "hosted_unreviewed", return_value=["rogue.pdf"]), \
             patch.object(worker, "check_remote_extraction_key") as local_key, \
             patch.object(worker, "process_pdf") as process:
            worker.run_once(args, self.ledger)
        process.assert_not_called()
        local_key.assert_not_called()

    def test_existing_graph_doi_blocks_different_pdf_copy(self):
        old = tei("10.1234/same", "Original paper text with many words")
        self.graph.write_text(json.dumps({"old": {"file_path": "old.pdf", "content": old.decode()}}))
        pdf = self.pdf("new-name.pdf", "different binary bytes")
        _, request = self.process(pdf, "10.1234/same", "Newly parsed body", None)
        self.assertEqual(self.status(pdf), "duplicate")
        request.assert_not_called()

    def test_same_doi_different_pdf_after_submission_is_blocked(self):
        first = self.pdf("first.pdf", "first bytes")
        second = self.pdf("second.pdf", "second bytes")
        _, request_one = self.process(first, "10.1234/same", "First paper text",
                                      lambda *_: {"track_id": "insert-1"})
        self.assertEqual(self.status(first), "submitted")
        self.assertEqual(request_one.call_count, 1)
        _, request_two = self.process(second, "10.1234/same", "Changed OCR text", None)
        self.assertEqual(self.status(second), "duplicate")
        request_two.assert_not_called()

    def test_missing_doi_is_held_even_if_citation_has_doi(self):
        pdf = self.pdf("unidentified.pdf", "bytes")
        _, request = self.process(pdf, None, "Paper body", None)
        self.assertEqual(self.status(pdf), "review_required")
        request.assert_not_called()

    def test_uncertain_submission_never_retries_automatically(self):
        pdf = self.pdf("uncertain.pdf", "bytes")
        second = self.pdf("another-copy.pdf", "different bytes")
        with patch.object(worker.core, "parse_pdf",
                          side_effect=lambda _: self.fake_parse("10.1234/new", "Paper text")) as parse:
            with patch.object(worker, "api_json", side_effect=TimeoutError) as request, \
                 patch.object(worker.claims, "extract", return_value={'claims': []}):
                for _ in range(2):
                    worker.process_pdf(pdf, self.inbox, self.output, self.graph,
                                       self.ledger, "http://localhost:9621", None, 0)
                worker.process_pdf(second, self.inbox, self.output, self.graph,
                                   self.ledger, "http://localhost:9621", None, 0)
        self.assertEqual(self.status(pdf), "submission_unknown")
        self.assertEqual(self.status(second), "duplicate")
        self.assertEqual(parse.call_count, 2)
        self.assertEqual(request.call_count, 1)

    def _hosted_args(self):
        return type("A", (), dict(lightrag_url="https://h.example", api_key="k" * 40, inbox=self.inbox,
                                  output=self.output, graph=self.graph, min_age=0))()

    def _run_once_with(self, args, process):
        health = {"configuration": {}}
        class R:
            status = 200
            def __enter__(s): return s
            def __exit__(s, *a): pass
            def read(s): return b"true"
        with patch.object(worker.ingestion_control, "paused", return_value=False), \
             patch.object(worker, "poll_submitted"), \
             patch.object(worker.urllib.request, "urlopen", return_value=R()), \
             patch.object(worker, "api_json", return_value=health), \
             patch.object(worker, "check_runtime_reasoning"), \
             patch.object(worker, "hosted_unreviewed", return_value=[]), \
             patch.object(worker, "process_pdf", side_effect=process) as called:
            worker.run_once(args, self.ledger)
        return called

    def test_failed_or_unclear_paper_pauses_queue_by_default_but_not_in_continue_mode(self):
        bad, good = self.pdf("a-bad.pdf", "bad"), self.pdf("b-good.pdf", "good")
        worker.record(self.ledger, "h-failed", bad, "failed", track_id="t1", reason="LightRAG reported failed")
        worker.record(self.ledger, "h-unknown", bad, "submission_unknown")
        self.assertEqual(self._run_once_with(self._hosted_args(), lambda *a: None).call_count, 0)
        with patch.dict(os.environ, {"INGEST_CONTINUE_ON_FAILURE": "1"}):
            called = self._run_once_with(self._hosted_args(), lambda *a: None)
        self.assertEqual(called.call_count, 2)   # both inbox files are visited; nothing pauses the pass

    def test_retry_wait_file_is_reached_even_when_finished_files_sort_first(self):
        done, waiting = self.pdf("a-done.pdf", "done"), self.pdf("b-waiting.pdf", "waiting")
        worker.record(self.ledger, "h-done", done, "processed")
        worker.record(self.ledger, "h-wait", waiting, "retry_wait", reason="GROBID temporarily unreachable: URLError")
        for env in ({}, {"INGEST_CONTINUE_ON_FAILURE": "1"}):
            with patch.dict(os.environ, env):
                called = self._run_once_with(self._hosted_args(), lambda *a: None)
            self.assertEqual([c.args[0].name for c in called.call_args_list], ["a-done.pdf", "b-waiting.pdf"])

    def test_repeated_grobid_errors_are_capped_in_continue_mode(self):
        pdf = self.pdf("always-500.pdf", "x")
        err = urllib.error.HTTPError("http://g", 500, "boom", {}, None)
        with patch.object(worker.core, "parse_pdf", side_effect=err), patch.dict(os.environ, {"INGEST_CONTINUE_ON_FAILURE": "1"}):
            for expected in ("retry_wait", "retry_wait", "failed"):
                worker.process_pdf(pdf, self.inbox, self.output, self.graph, self.ledger, "http://localhost:9621", None, 0)
                self.assertEqual(self.status(pdf), expected)
        slow = self.pdf("always-slow.pdf", "y")
        with patch.object(worker.core, "parse_pdf", side_effect=TimeoutError), patch.dict(os.environ, {"INGEST_CONTINUE_ON_FAILURE": "1"}):
            for expected in ("retry_wait", "retry_wait", "failed"):
                worker.process_pdf(slow, self.inbox, self.output, self.graph, self.ledger, "http://localhost:9621", None, 0)
                self.assertEqual(self.status(slow), expected)
        down = self.pdf("grobid-down.pdf", "z")   # service unreachable is not this paper's fault: never capped
        with patch.object(worker.core, "parse_pdf", side_effect=urllib.error.URLError("refused")), patch.dict(os.environ, {"INGEST_CONTINUE_ON_FAILURE": "1"}):
            for _ in range(5):
                worker.process_pdf(down, self.inbox, self.output, self.graph, self.ledger, "http://localhost:9621", None, 0)
        self.assertEqual(self.status(down), "retry_wait")

    def test_claim_failure_blocks_graph_submission(self):
        pdf = self.pdf('claim-failure.pdf', 'claim failure bytes')
        with patch.object(worker.core, 'parse_pdf', side_effect=lambda _: self.fake_parse('10.1234/claims', 'Scientific paper body')), \
             patch.object(worker.claims, 'extract', side_effect=ValueError('Invalid claim output')), \
             patch.object(worker, 'api_json') as request:
            worker.process_pdf(pdf, self.inbox, self.output, self.graph,
                               self.ledger, 'http://localhost:9621', None, 0)
        self.assertEqual(self.status(pdf), 'retry_wait')
        request.assert_not_called()

    def test_recovered_failed_job_uses_original_track_id(self):
        pdf = self.pdf("recovered.pdf", "bytes")
        digest = worker.hashlib.sha256(pdf.read_bytes()).hexdigest()
        worker.record(self.ledger, digest, pdf, "failed", doi="10.1234/recovered",
                      source_id="doi-original.txt", track_id="insert-original")
        with patch.object(worker, "api_json", return_value={"documents": [{"status": "processing"}]}) as request:
            worker.poll_submitted(self.ledger, "http://localhost:9621", None)
        self.assertEqual(self.status(pdf), "reprocessing")
        with patch.object(worker, "api_json", return_value={"documents": [{"status": "processed"}]}):
            worker.poll_submitted(self.ledger, "http://localhost:9621", None)
        self.assertEqual(self.status(pdf), "processed")
        self.assertEqual(request.call_args.args[2],
                         "/documents/track_status/insert-original")


if __name__ == "__main__":
    unittest.main()
