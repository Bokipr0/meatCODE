# Last updated: 2026-11-21 UTC · Claude (Sonnet 5.5) · unit tests for usage logging in claude_link.BilledClient + server/usage_log.py (no network, no Postgres)
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_link as cl
import usage_log
from accounts_fakes import MemoryUsageStore


def base(usage=(5, 7), fail=False):
    class Manager:
        def __init__(self): self.exited = None
        def __enter__(self): return SimpleNamespace(current_message_snapshot=SimpleNamespace(usage=SimpleNamespace(input_tokens=usage[0], output_tokens=usage[1])),
                                                    get_final_message=lambda: SimpleNamespace(content=[SimpleNamespace(type="text", text="The ANSWER."), SimpleNamespace(type="tool_use")]))
        def __exit__(self, *a): self.exited = a; return False
    def create(**kw):
        if fail: raise RuntimeError("api down")
        return SimpleNamespace(usage=SimpleNamespace(input_tokens=usage[0], output_tokens=usage[1]))
    mgr = Manager()
    return SimpleNamespace(messages=SimpleNamespace(create=create, stream=lambda **kw: mgr)), mgr


class RecorderTests(unittest.TestCase):
    def setUp(self):
        self.seen = []
        self.texts = []
        self.rec = lambda model, i, o, status, **kw: (self.seen.append((model, i, o, status)), self.texts.append(kw))

    def test_create_reports_the_tokens_the_api_returned(self):
        b, _ = base((5, 7))
        cl.BilledClient(b, "uprof_1", recorder=self.rec).messages.create(model="m1", max_tokens=1)
        self.assertEqual(self.seen, [("m1", 5, 7, "ok")])

    def test_stream_reports_on_close_and_is_otherwise_transparent(self):
        b, mgr = base((11, 22))
        with cl.BilledClient(b, "uprof_1", recorder=self.rec).messages.stream(model="m2") as stream:
            self.assertTrue(hasattr(stream, "current_message_snapshot"))             # the real stream object, not a proxy
        self.assertEqual(self.seen, [("m2", 11, 22, "ok")])
        self.assertIsNotNone(mgr.exited)                                             # the SDK's own cleanup still ran

    def test_stream_that_raises_is_logged_as_an_error_and_the_error_propagates(self):
        b, _ = base()
        with self.assertRaises(ValueError):
            with cl.BilledClient(b, "uprof_1", recorder=self.rec).messages.stream(model="m3"):
                raise ValueError("boom")
        self.assertEqual(self.seen[0][3], "error")

    def test_failed_create_is_logged_and_reraised(self):
        b, _ = base(fail=True)
        with self.assertRaises(RuntimeError):
            cl.BilledClient(b, "uprof_1", recorder=self.rec).messages.create(model="m4")
        self.assertEqual(self.seen, [("m4", 0, 0, "error")])

    def test_a_broken_recorder_never_breaks_an_answer(self):
        def bad(*a, **kw): raise OSError("db down")
        b, _ = base()
        self.assertIsNotNone(cl.BilledClient(b, "uprof_1", recorder=bad).messages.create(model="m"))
        with cl.BilledClient(b, "uprof_1", recorder=bad).messages.stream(model="m"):
            pass

    def test_answers_log_the_input_and_the_answer_text_but_helper_calls_do_not(self):
        b, _ = base((5, 7))
        client = cl.BilledClient(b, "uprof_1", recorder=self.rec)
        with client.messages.stream(model="m", system="SYSTEM WITH SOURCES", messages=[
                {"role": "user", "content": "first"}, {"role": "assistant", "content": "reply"},
                {"role": "user", "content": "What makes umami?"}]):
            pass
        self.assertEqual(self.texts[-1], {"input_text": "What makes umami?", "output_text": "The ANSWER."})     # last user message only
        self.assertNotIn("SOURCES", str(self.texts))                                                          # never the system prompt
        client.messages.create(model="m", messages=[{"role": "user", "content": "HELPER PROMPT WITH CLAIMS"}])
        self.assertEqual(self.texts[-1], {"input_text": None, "output_text": None})                           # counts only

    def test_block_style_user_content_and_a_failed_stream_are_handled(self):
        b, _ = base()
        client = cl.BilledClient(b, "uprof_1", recorder=self.rec)
        with client.messages.stream(model="m", messages=[{"role": "user", "content": [{"type": "text", "text": "part one "}, {"type": "text", "text": "part two"}]}]):
            pass
        self.assertEqual(self.texts[-1]["input_text"], "part one part two")
        with self.assertRaises(ValueError):
            with client.messages.stream(model="m", messages=[{"role": "user", "content": "q"}]):
                raise ValueError("boom")
        self.assertEqual((self.seen[-1][3], self.texts[-1]["output_text"]), ("error", None))                  # no answer text on failure

    def test_no_recorder_is_fine(self):
        b, _ = base()
        cl.BilledClient(b, "uprof_1").messages.create(model="m")


class SnapshotTests(unittest.TestCase):
    def test_snapshot_has_last_times_and_a_short_preview_but_never_the_answer(self):
        st = MemoryUsageStore()
        st.record(1, "/api/ask", "m", 10, 5, "ok", input_text="  What   makes\n umami " + "x" * 200, output_text="SECRET ANSWER TEXT")
        snap = usage_log.snapshot(st, 1)
        self.assertRegex(snap["last_used_at"], r"^\d{4}-\d\d-\d\dT")
        self.assertIsNone(snap["last_login_at"])
        self.assertTrue(snap["recent"][0]["preview"].startswith("What makes umami x"))
        self.assertLessEqual(len(snap["recent"][0]["preview"]), 90)
        self.assertNotIn("SECRET ANSWER TEXT", str(snap))

    def test_snapshot_totals_recent_and_labels(self):
        st = MemoryUsageStore()
        st.record(1, "/api/ask", "m", 100, 40, "ok")
        st.record(1, "/api/ecosystem/intent", "m", 10, 5, "error")
        st.record(2, "/api/ask", "m", 7, 7, "ok")
        snap = usage_log.snapshot(st, 1)
        self.assertEqual((snap["requests"], snap["input_tokens"], snap["output_tokens"]), (2, 110, 45))
        self.assertEqual([r["label"] for r in snap["recent"]], ["Ecosystem search", "Oracle answer"])    # newest first
        self.assertEqual(snap["recent"][0]["status"], "error")
        self.assertRegex(snap["month_label"], r"^[A-Z][a-z]+ \d{4}$")

    def test_unknown_route_has_a_neutral_label_and_empty_user_is_zeroes(self):
        self.assertEqual(usage_log.route_label("/api/whatever"), "Claude request")
        snap = usage_log.snapshot(MemoryUsageStore(), 9)
        self.assertEqual((snap["requests"], snap["recent"]), (0, []))


if __name__ == "__main__":
    unittest.main()
