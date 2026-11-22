# Last updated: 2026-11-22 UTC · Claude (Fable 5.2) · the classic Oracle must actually tell the process-map panel an answer finished
"""Regression for 3b396cc: the 'answer finished' event was dispatched from streamSSE() using askOracle()'s local `q`,
which is not in scope there; the ReferenceError was swallowed and the panel never loaded a map."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "app" / "meatcode_mockup.html").read_text(encoding="utf-8")


def function_body(name):
    start = PAGE.index("function %s(" % name)
    end = PAGE.index("\n}\n", start)
    return PAGE[start:end]


class ProcessMapWiringTests(unittest.TestCase):
    def test_stream_handler_announces_the_answer_with_names_it_can_see(self):
        body = function_body("streamSSE")
        self.assertIn("mc:oracle-answer-done", body)
        self.assertNotRegex(body, r"question:\s*q\b")                       # askOracle's local, not visible here
        self.assertIn("mcOracleActiveQuestion", body)
        self.assertRegex(PAGE, r"\nvar mcOracleActiveQuestion\b")           # a page-level variable …
        self.assertIn("mcOracleActiveQuestion = q;", function_body("askOracle"))   # … set when a question is asked

    def test_both_ends_of_the_stream_announce_once_and_never_for_a_question_back(self):
        body = function_body("streamSSE")
        self.assertEqual(len(re.findall(r"if \(!askedTurn\) mcNotifyAnswerDone\(\);", body)), 2)   # `done` block + closed stream
        self.assertIn("if (answerNotified || !askedQuestion || !fullText) return;", body)

    def test_panel_script_is_loaded_and_listens(self):
        self.assertIn('<script src="/app/assets/oracle-process-map.js" defer></script>', PAGE)
        panel = (ROOT / "app" / "assets" / "oracle-process-map.js").read_text(encoding="utf-8")
        self.assertIn("document.addEventListener('mc:oracle-answer-done'", panel)
        self.assertIn("'/api/graph-oracle/ask'", panel)


if __name__ == "__main__":
    unittest.main()
