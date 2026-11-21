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
        def __enter__(self): return SimpleNamespace(current_message_snapshot=SimpleNamespace(usage=SimpleNamespace(input_tokens=usage[0], output_tokens=usage[1])))
        def __exit__(self, *a): self.exited = a; return False
    def create(**kw):
        if fail: raise RuntimeError("api down")
        return SimpleNamespace(usage=SimpleNamespace(input_tokens=usage[0], output_tokens=usage[1]))
    mgr = Manager()
    return SimpleNamespace(messages=SimpleNamespace(create=create, stream=lambda **kw: mgr)), mgr


class RecorderTests(unittest.TestCase):
    def setUp(self):
        self.seen = []
        self.rec = lambda model, i, o, status: self.seen.append((model, i, o, status))

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
        def bad(*a): raise OSError("db down")
        b, _ = base()
        self.assertIsNotNone(cl.BilledClient(b, "uprof_1", recorder=bad).messages.create(model="m"))
        with cl.BilledClient(b, "uprof_1", recorder=bad).messages.stream(model="m"):
            pass

    def test_no_recorder_is_fine(self):
        b, _ = base()
        cl.BilledClient(b, "uprof_1").messages.create(model="m")


class SnapshotTests(unittest.TestCase):
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
