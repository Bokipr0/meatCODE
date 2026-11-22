# Last updated: 2026-11-22 UTC · Claude (Fable 5.2) · guided elicitation in the Graph Oracle (ask first / answer with a brief)
"""The Graph Oracle reuses the classic Oracle's elicitation step when the page sends guided:true: one small model call
decides to ASK one question or to answer; when it answers, the gathered parameters steer retrieval and the prompt."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))
import graph_oracle as g

FIXTURE = '''<graphml xmlns="http://graphml.graphdrawing.org/xmlns"><key id="d" attr.name="description"/><key id="s" attr.name="source_id"/><key id="t" attr.name="entity_type"/><graph edgedefault="undirected"><node id="cysteine"><data key="d">Cysteine is a sulfur amino acid precursor.</data><data key="s">c1</data><data key="t">precursor</data></node><node id="pea protein"><data key="d">Pea protein is a plant protein base.</data><data key="s">c2</data><data key="t">ingredient</data></node><node id="roasting"><data key="d">Roasting is a dry heat process.</data><data key="s">c3</data><data key="t">process</data></node><edge id="edge-1" source="cysteine" target="roasting"><data key="d">Cysteine reacts during roasting.</data><data key="s">c1</data></edge></graph></graphml>'''
ASK = {"intent": "FORMULATION", "action": "ask", "question": "Which protein base are you working with?",
       "options": ["Pea", "Soy"], "why": "It sets the precursor pool.",
       "params": [{"name": "Target note", "value": "roasted beef", "status": "given"},
                  {"name": "Protein base", "value": None, "status": "missing"}]}
ANSWER_NOW = {"intent": "FORMULATION", "action": "answer", "question": "", "options": [], "why": "Enough is known.",
              "params": [{"name": "Target note", "value": "roasted beef", "status": "given"},
                         {"name": "Protein base", "value": "pea protein", "status": "given"}]}
MAP = {"answer": "Use [cysteine].", "ingredient_question": True, "focus": "Precursors", "title": "T",
       "stages": {"Precursors": ["cysteine"]}, "relation_ids": []}


class GuidedGraphOracleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        path = Path(self.tmp.name) / "graph.graphml"
        path.write_text(FIXTURE)
        self.env = patch.dict(os.environ, {"KG_ORACLE_GRAPH_PATH": str(path),
                                           "KG_ORACLE_STATE_DIR": str(Path(self.tmp.name) / "state")})
        self.env.start()
        g.CACHE.clear()
        self.session, self.prompts = "tester-session-capability-0123456789", []

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def model(self, *replies):
        queue = [json.dumps(r) if not isinstance(r, (str, Exception)) else r for r in replies]

        def call(prompt):
            self.prompts.append(prompt)
            reply = queue.pop(0)
            if isinstance(reply, Exception):
                raise reply
            return reply
        return call

    def ask(self, body, *replies):
        return g.dispatch("ask", body, self.session, self.model(*replies))

    def test_asks_one_question_first_and_builds_nothing(self):
        out = self.ask({"question": "how do I get roasted notes", "guided": True, "history": []}, ASK)
        self.assertEqual(out["ask"]["question"], "Which protein base are you working with?")
        self.assertEqual(out["ask"]["options"], ["Pea", "Soy"])
        self.assertIsNone(out["map"])
        self.assertIsNone(out["answer"])
        self.assertEqual(len(self.prompts), 1)                       # the decision call only — no answer call yet
        self.assertIn("CONVERSATION SO FAR", self.prompts[0])

    def test_answer_uses_the_brief_for_retrieval_and_tells_the_model(self):
        history = [{"role": "user", "content": "notes from roasting"},
                   {"role": "assistant", "kind": "ask", "content": "Which protein base are you working with?"}]
        out = self.ask({"question": "the usual one", "guided": True, "history": history}, ANSWER_NOW, MAP)
        self.assertEqual(out["answer"], "Use [cysteine].")
        self.assertEqual(out["brief"]["question_type"], "FORMULATION")
        payload = json.loads(self.prompts[1][self.prompts[1].index('{"question"'):])
        self.assertEqual(payload["brief"]["parameters"][1], {"name": "Protein base", "value": "pea protein", "status": "given"})
        # "the usual one" matches nothing in the graph: the records come from the brief ("pea protein") and the
        # earlier user turn ("roasting"), i.e. the elicited parameters decide what is retrieved.
        ids = {n["id"] for n in payload["graph"]["nodes"]}
        self.assertIn("pea protein", ids)
        self.assertIn("roasting", ids)

    def test_skip_answers_without_the_decision_call(self):
        out = self.ask({"question": "cysteine", "guided": True, "history": [], "skip": True}, MAP)
        self.assertEqual(out["answer"], "Use [cysteine].")
        self.assertEqual(len(self.prompts), 1)

    def test_question_budget_is_three_per_conversation(self):
        history = []
        for i in range(3):
            history += [{"role": "user", "content": "q%d" % i}, {"role": "assistant", "kind": "ask", "content": "ask %d" % i}]
        out = self.ask({"question": "cysteine", "guided": True, "history": history}, ASK, MAP)
        self.assertNotIn("ask", out)
        self.assertEqual(out["answer"], "Use [cysteine].")

    def test_a_failed_or_garbled_decision_never_blocks_the_answer(self):
        for bad in (RuntimeError("model down"), "not json at all"):
            self.prompts.clear()
            out = self.ask({"question": "cysteine", "guided": True, "history": []}, bad, MAP)
            self.assertEqual(out["answer"], "Use [cysteine].")

    def test_without_guided_nothing_changes(self):
        out = self.ask({"question": "cysteine"}, MAP)
        self.assertEqual(out["answer"], "Use [cysteine].")
        self.assertEqual(len(self.prompts), 1)
        self.assertNotIn("brief", out)
        self.assertIsNone(json.loads(self.prompts[0][self.prompts[0].index('{"question"'):])["brief"])


if __name__ == "__main__":
    unittest.main()
