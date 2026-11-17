# Last updated: 2026-11-17 · Codex · Stream boundaries and response-style contract.
from pathlib import Path
import io
import os
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'server'))
from oracle_presentation import AnswerSections, DETAIL_MARKER


class PresentationTests(unittest.TestCase):
    def test_boundary_is_stripped_at_every_possible_chunk_split(self):
        raw = 'Start with the useful recommendation [880].\n\n' + DETAIL_MARKER + '\n\nThe evidence and conditions [144].\n\nFollow-ups: What next?'
        expected = raw.replace(DETAIL_MARKER, '')
        for step in range(1, len(raw) + 1):
            stream = AnswerSections()
            events = []
            for index in range(0, len(raw), step):
                events.extend(stream.feed(raw[index:index+step]))
            events.extend(stream.finish())
            self.assertEqual(''.join(text for event, text in events if event == 'chunk'), expected)
            self.assertEqual([value for event, value in events if event == 'answer_section'], ['{"section":"detail"}'])

    def test_brief_only_and_legacy_answers_are_preserved(self):
        for text in ['Short answer.', 'One paragraph.\n\nAnother paragraph [12].', 'A literal bracket [']:
            stream = AnswerSections()
            events = stream.feed(text) + stream.finish()
            self.assertEqual(''.join(value for event, value in events if event == 'chunk'), text)
            self.assertFalse(any(event == 'answer_section' for event, _ in events))

    def test_incomplete_internal_marker_is_not_shown(self):
        stream = AnswerSections()
        events = stream.feed('Useful answer.\n\n[[MEATCODE_DET') + stream.finish()
        self.assertEqual(''.join(value for event, value in events if event == 'chunk'), 'Useful answer.\n\n')


class EndpointPresentationTests(unittest.TestCase):
    def test_real_standard_and_guided_handlers_stream_plain_text_with_one_detail_boundary(self):
        # A dummy SDK key and an in-memory model replace all credentials, networking and DB reads.
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'local-fixture-not-a-key', 'DATABASE_URL': '', 'APP_ENV': 'dev'}):
            import meatcode_server as server
        raw = 'Useful recommendation [101].\n\n' + DETAIL_MARKER + '\n\nSupporting explanation [102].'
        for guided in (False, True):
            calls = []
            class Stream:
                text_stream = iter(raw)
                def __enter__(self): return self
                def __exit__(self, *args): return False
            def stream(**kwargs):
                calls.append(kwargs)
                return Stream()
            fake = SimpleNamespace(messages=SimpleNamespace(stream=stream, create=lambda **_: SimpleNamespace(
                content=[SimpleNamespace(type='text', text='{"action":"answer","intent":"LOOKUP"}')])))
            handler = server.Handler.__new__(server.Handler)
            handler.path = '/api/ask'
            handler.wfile = io.BytesIO()
            handler.send_response = lambda *args: None
            handler.send_header = lambda *args: None
            handler.end_headers = lambda: None
            handler._authorized = lambda: True
            handler._read_json_body = lambda: {'question': 'Fixture question'}
            with patch.object(server, 'client', fake), patch.object(server, 'DATABASE_URL', ''), patch.object(server, '_flag_on', return_value=False):
                if guided: handler._handle_guided_ask({'skip': True, 'history': []}, 'Fixture question')
                else: handler.do_POST()
            wire = handler.wfile.getvalue().decode()
            self.assertEqual(wire.count('event: answer_section'), 1)
            self.assertIn('event: done', wire)
            self.assertNotIn(DETAIL_MARKER, wire)
            self.assertEqual(len(calls), 1)

if __name__ == '__main__':
    unittest.main()
