# Last updated: 2026-11-22 UTC · Claude (Fable 5.2) · the model call must fit the installed Anthropic SDK; unexpected failures are logged
"""Regression for dev 2026-11-21: `messages.create(temperature=0, …)` raised TypeError on the Anthropic SDK 2.x (no such
argument), and the module's catch-all showed only "Graph Oracle is unavailable" with nothing in the log."""
import contextlib
import inspect
import io
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))
import graph_oracle as g
from anthropic.resources.messages import Messages


class FakeHandler:
    def __init__(self):
        self.headers, self.sent = {"Content-Length": "2", "X-KG-Session": "s" * 40}, None

    def _read_json_body(self):
        return {"question": "q"}

    def _send_json(self, obj, code=200):
        self.sent = (code, obj)


def sdk_shaped_client(calls):
    """A client whose create() rejects exactly what the real SDK's create() rejects."""
    signature = inspect.signature(Messages.create)

    def create(**kw):
        signature.bind(None, **kw)                              # TypeError on any argument the SDK does not have
        calls.append(kw)
        return SimpleNamespace(content=[SimpleNamespace(type="text", text="MODEL TEXT")])
    return SimpleNamespace(messages=SimpleNamespace(create=create))


class ModelCallTests(unittest.TestCase):
    def run_ask(self, client, dispatch):
        handler = FakeHandler()
        with patch.object(g, "dispatch", dispatch), patch.object(g, "source_label", lambda: "hosted_lightrag_graph"):
            g.handle(handler, "ask", client, "claude-test-model")
        return handler.sent

    def test_model_call_uses_only_arguments_the_installed_sdk_accepts(self):
        calls = []
        sent = self.run_ask(sdk_shaped_client(calls), lambda action, body, session, reason: {"answer": reason("PROMPT")})
        self.assertEqual(sent, (200, {"answer": "MODEL TEXT"}))
        self.assertEqual(calls[0]["model"], "claude-test-model")
        self.assertEqual(calls[0]["messages"], [{"role": "user", "content": "PROMPT"}])
        self.assertNotIn("temperature", calls[0])

    def test_unexpected_failure_is_named_in_the_log_but_not_to_the_person(self):
        def boom(action, body, session, reason):
            raise TypeError("unexpected keyword argument 'x'")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code, body = self.run_ask(sdk_shaped_client([]), boom)
        self.assertEqual(code, 503)
        self.assertNotIn("keyword", body["error"])
        self.assertIn("[graph-oracle] ask failed: TypeError unexpected keyword argument 'x'", err.getvalue())


if __name__ == "__main__":
    unittest.main()
