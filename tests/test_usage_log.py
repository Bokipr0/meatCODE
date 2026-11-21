# Last updated: 2026-11-21 UTC · Claude (Sonnet 5.5) · unit tests for usage logging in claude_link.BilledClient + server/usage_log.py (no network, no Postgres)
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_link as cl
import usage_log
from datetime import datetime, timedelta, timezone
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
        self.assertEqual(self.texts[-1], {"input_text": "What makes umami?", "output_text": "The ANSWER.", "kind": "answer"})   # last user message only
        self.assertNotIn("SOURCES", str(self.texts))                                                          # never the system prompt
        client.messages.create(model="m", messages=[{"role": "user", "content": "HELPER PROMPT WITH CLAIMS"}])
        self.assertEqual(self.texts[-1], {"input_text": None, "output_text": None, "kind": "helper"})        # counts only

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


class CreditErr(Exception):
    def __init__(self, status, text=None):
        super().__init__(text or "HTTP %s" % status)
        self.status_code = status


def refusing(status, text=None):
    """A fake Claude whose requests fail like an API refusal."""
    class Mgr:
        def __enter__(self): raise CreditErr(status, text)
        def __exit__(self, *a): return False
    def create(**kw): raise CreditErr(status, text)
    return SimpleNamespace(messages=SimpleNamespace(create=create, stream=lambda **kw: Mgr()))


class CreditsAndTrialClientTests(unittest.TestCase):
    def setUp(self):
        self.seen, self.flagged = [], []
        self.rec = lambda model, i, o, status, **kw: self.seen.append((status, kw.get("kind")))
        self.hook = lambda: self.flagged.append(1)

    def test_trial_mode_passes_calls_through_unbilled_and_unchanged(self):
        calls = []
        b = SimpleNamespace(messages=SimpleNamespace(create=lambda **kw: calls.append(kw) or SimpleNamespace(usage=None), stream=None))
        cl.BilledClient(b, None, recorder=self.rec).messages.create(model="m", extra_headers={"x": "1"})
        self.assertEqual(calls[0], {"model": "m", "extra_headers": {"x": "1"}})                 # no billing headers/body at all
        self.assertEqual(self.seen, [("ok", "helper")])

    def test_kinds_answer_for_streams_helper_for_create(self):
        b, _ = base()
        client = cl.BilledClient(b, "uprof_1", recorder=self.rec)
        client.messages.create(model="m")
        with client.messages.stream(model="m", messages=[{"role": "user", "content": "q"}]):
            pass
        self.assertEqual(self.seen, [("ok", "helper"), ("ok", "answer")])

    def test_a_billed_call_refused_for_credit_becomes_credits_required_and_flags_it(self):
        for status, text in ((402, None), (403, '{"error":"user_profile_not_billable"}')):
            self.flagged.clear()
            client = cl.BilledClient(refusing(status, text), "uprof_1", recorder=self.rec, on_credits_required=self.hook)
            with self.assertRaises(cl.CreditsRequired):
                with client.messages.stream(model="m", messages=[{"role": "user", "content": "q"}]):
                    pass
            with self.assertRaises(cl.CreditsRequired):
                client.messages.create(model="m")
            self.assertEqual(len(self.flagged), 2, status)
        self.assertIn(("error", "answer"), self.seen)                                            # the failed attempt is still logged

    def test_other_failures_and_the_trial_key_are_never_turned_into_credits_required(self):
        with self.assertRaises(CreditErr):                                                       # a 500 stays a plain failure
            cl.BilledClient(refusing(500), "uprof_1", on_credits_required=self.hook).messages.create(model="m")
        with self.assertRaises(CreditErr):                                                       # our own key out of credit is OUR problem, not the user's
            cl.BilledClient(refusing(402), None, on_credits_required=self.hook).messages.create(model="m")
        self.assertEqual(self.flagged, [])

    def test_the_403_not_billable_wording_counts_as_credit_too(self):
        self.assertTrue(cl.is_credit_error(CreditErr(402)))
        self.assertTrue(cl.is_credit_error(Exception('{"error":"user_profile_not_billable"}')))
        self.assertFalse(cl.is_credit_error(CreditErr(429)))


class TrialStateTests(unittest.TestCase):
    NOW = datetime(2026, 11, 22, 12, 0, tzinfo=timezone.utc)
    POLICY = {"sessions": 2, "idle_minutes": 30, "answers": 3}

    def state(self, *minutes_ago):
        class S:
            def trial_answer_times(self_inner, uid):
                return sorted(self.NOW - timedelta(minutes=m) for m in minutes_ago)
        return usage_log.trial_state(S(), 1, self.POLICY, now=self.NOW)

    def test_fresh_user_has_both_sessions(self):
        s = self.state()
        self.assertEqual((s["allowed"], s["sessions_used"], s["answers_in_session"]), (True, 0, 0))

    def test_answers_within_the_idle_window_are_one_session(self):
        s = self.state(20, 10, 5)                                                  # 3 answers, but the cap (3) ends the session
        self.assertEqual((s["sessions_used"], s["allowed"]), (1, True))            # session 2 is still available
        s = self.state(20, 10)
        self.assertEqual((s["sessions_used"], s["answers_in_session"], s["allowed"]), (1, 2, True))

    def test_a_long_gap_starts_a_new_session_and_two_sessions_end_the_trial(self):
        s = self.state(300, 290, 3)                                                # session 1 long ago, session 2 just started
        self.assertEqual((s["sessions_used"], s["answers_in_session"], s["allowed"]), (2, 1, True))      # may continue session 2
        s = self.state(600, 300, 100)                                              # three separate sessions' worth of gaps
        self.assertEqual((s["sessions_used"], s["allowed"], s["exhausted"]), (3, False, True))
        s = self.state(300, 290, 285, 120)                                         # session 1 (cap hit) then session 2 closed by idle
        self.assertEqual((s["allowed"], s["exhausted"]), (False, True))

    def test_cap_reached_in_the_last_session_ends_the_trial_immediately(self):
        s = self.state(300, 20, 15, 10)                                            # session 1; session 2 = 3 answers (cap), still recent
        self.assertEqual((s["sessions_used"], s["answers_in_session"], s["allowed"]), (2, 0, False))

    def test_trial_can_be_switched_off(self):
        self.assertEqual(usage_log.trial_policy({"TRIAL_SESSIONS": "0"})["sessions"], 0)
        class S:
            def trial_answer_times(self, uid): return []
        self.assertFalse(usage_log.trial_state(S(), 1, usage_log.trial_policy({"TRIAL_SESSIONS": "0"}))["allowed"])

    def test_policy_defaults_and_garbage_values(self):
        self.assertEqual(usage_log.trial_policy({}), {"sessions": 2, "idle_minutes": 30, "answers": 10})
        self.assertEqual(usage_log.trial_policy({"TRIAL_SESSIONS": "lots", "TRIAL_ANSWERS_PER_SESSION": "9999"}),
                         {"sessions": 2, "idle_minutes": 30, "answers": 200})


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
