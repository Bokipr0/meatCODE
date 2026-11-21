# Last updated: 2026-11-21 UTC · Claude (Sonnet 5.5) · unit tests for server/claude_link.py (fake stores, fake auth server — no network)
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_link as cl
from accounts_fakes import MemoryLinkStore

USER = {"id": 7, "email": "u@example.com", "display_name": "U"}


def env_for(tmp, **over):
    path = os.path.join(tmp, "token")
    Path(path).write_text("jwt-1\n")
    env = {"CLAUDE_OAUTH_CLIENT_ID": "client-xyz", "CLAUDE_OAUTH_REDIRECT_URI": "https://site.test/claude/billing/callback",
           "ANTHROPIC_FEDERATION_RULE_ID": "fdrl_1", "ANTHROPIC_ORGANIZATION_ID": "org", "ANTHROPIC_SERVICE_ACCOUNT_ID": "svac_1",
           "ANTHROPIC_WORKSPACE_ID": "wrkspc_1", "ANTHROPIC_IDENTITY_TOKEN_FILE": path, "APP_ENV": "dev"}
    env.update(over)
    return env


class FakeAuthServer:
    """Stands in for auth.claude.com: records each call and answers from a queue of (status, body)."""

    def __init__(self, *answers):
        self.answers, self.calls = list(answers), []

    def __call__(self, url, payload, timeout=10):
        self.calls.append((url, payload))
        return self.answers.pop(0)


class FakeOp:
    """Our operator client: counts user-profile creations."""

    def __init__(self):
        self.created = []
        self.user_profiles = SimpleNamespace(create=self._create)

    def _create(self, **kw):
        self.created.append(kw)
        return SimpleNamespace(id="uprof_%d" % len(self.created))


class ConfigTests(unittest.TestCase):
    def test_missing_env_is_named_and_configured_is_false(self):
        self.assertFalse(cl.configured({}))
        self.assertIn("CLAUDE_OAUTH_CLIENT_ID", cl.missing_env({}))
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(cl.configured(env_for(tmp)))
            self.assertEqual(cl.missing_env(env_for(tmp, CLAUDE_OAUTH_CLIENT_ID="")), ["CLAUDE_OAUTH_CLIENT_ID"])

    def test_pkce_challenge_matches_the_rfc7636_example(self):
        self.assertEqual(cl.s256("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"), "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM")

    def test_client_assertion_is_read_fresh_and_override_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = env_for(tmp)
            self.assertEqual(cl.client_assertion(env), "jwt-1")
            Path(env["ANTHROPIC_IDENTITY_TOKEN_FILE"]).write_text("jwt-2")     # Render rotated the file
            self.assertEqual(cl.client_assertion(env), "jwt-2")
            other = os.path.join(tmp, "other")
            Path(other).write_text("jwt-other")
            self.assertEqual(cl.client_assertion({**env, "CLAUDE_OAUTH_ASSERTION_TOKEN_FILE": other}), "jwt-other")

    def test_missing_or_empty_token_file_is_a_clean_503(self):
        for path in ("/nonexistent/file", ""):
            with self.assertRaises(cl.LinkError) as cx:
                cl.client_assertion({"ANTHROPIC_IDENTITY_TOKEN_FILE": path})
            self.assertEqual(cx.exception.status, 503)

    def test_public_status_hides_setup_detail_in_prod(self):
        store = MemoryLinkStore()
        self.assertIn("setup_missing", cl.public_status(store, USER, {"APP_ENV": "dev"}))
        self.assertNotIn("setup_missing", cl.public_status(store, USER, {"APP_ENV": "prod"}))


class BillingTests(unittest.TestCase):
    def test_billing_kwargs_shape(self):
        kw = cl.billing_kwargs("uprof_9")
        self.assertEqual(kw["extra_headers"]["anthropic-user-profile-id"], "uprof_9")
        self.assertEqual(kw["extra_headers"]["anthropic-beta"], cl.BILLING_BETA)
        self.assertEqual(kw["extra_body"]["billing_policy"], {"type": "billing_policy", "bill_to": "user_profile"})

    def test_billed_client_adds_billing_to_create_and_stream_and_keeps_caller_extras(self):
        seen = []
        class Manager:                                     # the SDK's stream() is a context manager
            def __enter__(self): return "STREAM"
            def __exit__(self, *a): return False
        base = SimpleNamespace(messages=SimpleNamespace(create=lambda **kw: seen.append(("create", kw)) or "R",
                                                        stream=lambda **kw: seen.append(("stream", kw)) or Manager()))
        billed = cl.BilledClient(base, "uprof_9")
        mine = {"extra_headers": {"x-mine": "1", "anthropic-user-profile-id": "uprof_EVIL"}, "extra_body": {"k": 1}}
        self.assertEqual(billed.messages.create(model="m", max_tokens=5, **mine), "R")
        with billed.messages.stream(model="m") as stream:
            self.assertEqual(stream, "STREAM")             # callers get the SDK's own stream object
        (_, c), (_, s) = seen
        self.assertEqual(c["model"], "m")
        self.assertEqual(c["extra_headers"]["x-mine"], "1")
        self.assertEqual(c["extra_headers"]["anthropic-user-profile-id"], "uprof_9")       # billing fields always win
        self.assertEqual(c["extra_body"]["k"], 1)
        self.assertEqual(c["extra_body"]["billing_policy"]["bill_to"], "user_profile")
        self.assertEqual(s["extra_body"]["billing_policy"]["bill_to"], "user_profile")
        self.assertEqual(mine["extra_headers"]["anthropic-user-profile-id"], "uprof_EVIL")  # caller's dict untouched

    def test_billing_profile_only_when_linked(self):
        store = MemoryLinkStore()
        self.assertIsNone(cl.billing_profile_for(store, USER))
        store.ensure_row(7)
        store.set_profile(7, "uprof_1")
        for status, expect in (("pending", None), ("revoked", None), ("linked", "uprof_1")):
            store.rows[7]["status"] = status
            self.assertEqual(cl.billing_profile_for(store, USER), expect, status)

    def test_user_profile_falls_back_to_generic_post_on_older_sdks(self):
        calls = []
        op = SimpleNamespace(post=lambda path, cast_to, body, options: calls.append((path, body, options)) or {"id": "uprof_77"})
        self.assertEqual(cl.create_user_profile(op, 5), "uprof_77")
        path, body, options = calls[0]
        self.assertEqual(path, "/v1/user_profiles")
        self.assertEqual(body["external_user_details"], {"reference_id": "meatcode-user-5"})
        self.assertNotIn("@", str(body))                                                    # no personal data is sent
        self.assertIn("anthropic-version", options["headers"])


class LinkFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = env_for(self.tmp.name)
        self.store = MemoryLinkStore()

    def begin(self, auth, op=None):
        with patch.object(cl, "_post_json", auth):
            return cl.begin_link(self.store, USER, self.env, op_client=op or FakeOp())

    def test_not_configured_is_503_and_creates_nothing(self):
        op = FakeOp()
        with self.assertRaises(cl.LinkError) as cx:
            cl.begin_link(self.store, USER, {}, op_client=op)
        self.assertEqual(cx.exception.status, 503)
        self.assertEqual(op.created, [])

    def test_begin_creates_one_profile_sends_a_correct_par_and_returns_the_approval_url(self):
        op, auth = FakeOp(), FakeAuthServer((201, {"request_uri": "urn:req:abc", "expires_in": 600}))
        url = self.begin(auth, op)
        self.assertEqual(op.created[0]["external_user_details"], {"reference_id": "meatcode-user-7"})
        self.assertEqual(self.store.rows[7]["user_profile_id"], "uprof_1")
        self.assertEqual(self.store.rows[7]["status"], "pending")
        endpoint, par = auth.calls[0]
        self.assertEqual(endpoint, "https://auth.claude.com/v1/oauth/par")
        self.assertEqual(par["scope"], "billing:attribution")
        self.assertEqual((par["connection_type"], par["connection_auth_target"]), ("organization_shared", "platform"))
        self.assertEqual(par["user_profile_id"], "uprof_1")
        self.assertEqual(par["client_assertion"], "jwt-1")
        self.assertEqual(par["code_challenge"], cl.s256(self.store.rows[7]["pending_verifier"]))   # challenge belongs to the stored verifier
        self.assertEqual(cl._hash(par["state"]), self.store.rows[7]["pending_state_hash"])
        self.assertGreaterEqual(len(self.store.rows[7]["pending_verifier"]), 43)                    # PKCE minimum length
        self.assertEqual(url, "https://auth.claude.com/oauth/authorize?client_id=client-xyz&request_uri=urn%3Areq%3Aabc")
        # a second attempt reuses the profile (Anthropic: one profile per organization — never mint a new one)
        self.begin(FakeAuthServer((201, {"request_uri": "urn:req:def"})), op)
        self.assertEqual(len(op.created), 1)

    def test_par_refusal_is_a_clean_error_with_no_url(self):
        with self.assertRaises(cl.LinkError) as cx:
            self.begin(FakeAuthServer((400, {"error": "invalid_client", "error_description": "audience mismatch"})))
        self.assertEqual(cx.exception.status, 502)
        self.assertNotIn("audience", str(cx.exception))                  # config detail goes to the log, not the user
        self.assertEqual(self.store.rows[7]["last_error"], "par_refused")

    def callback(self, auth, **params):
        with patch.object(cl, "_post_json", auth):
            return cl.finish_link(self.store, USER, params, self.env)

    def started(self):
        self.begin(FakeAuthServer((201, {"request_uri": "urn:req:abc"})))
        row = self.store.rows[7]
        return row["pending_verifier"]

    def state_for(self, verifier):
        # tests know the state only through its hash; re-issue a known one
        self.store.rows[7]["pending_state_hash"] = cl._hash("known-state")
        return "known-state"

    def test_successful_callback_links_and_stores_only_the_connection_id(self):
        verifier = self.started()
        state = self.state_for(verifier)
        auth = FakeAuthServer((200, {"connection_id": "ocon_1", "access_token": "SECRET-TOKEN", "expires_in": 3600}))
        self.assertEqual(self.callback(auth, state=state, code="the-code"), "linked")
        endpoint, body = auth.calls[0]
        self.assertEqual(endpoint, "https://auth.claude.com/v1/oauth/token")
        self.assertEqual(body["code_verifier"], verifier)
        self.assertEqual(body["code"], "the-code")
        self.assertEqual(body["redirect_uri"], self.env["CLAUDE_OAUTH_REDIRECT_URI"])
        row = self.store.rows[7]
        self.assertEqual((row["status"], row["connection_id"]), ("linked", "ocon_1"))
        self.assertNotIn("SECRET-TOKEN", str(row))                       # the per-connection token is dropped, never stored
        self.assertIsNone(row["pending_verifier"])

    def test_callback_is_single_use_and_state_must_match(self):
        verifier = self.started()
        state = self.state_for(verifier)
        self.assertEqual(self.callback(FakeAuthServer(), state="wrong-state", code="c"), "expired")   # no network call
        ok = FakeAuthServer((200, {"connection_id": "ocon_1"}))
        self.assertEqual(self.callback(ok, state=state, code="c"), "linked")
        self.assertEqual(self.callback(FakeAuthServer(), state=state, code="c"), "expired")           # replay finds nothing
        self.assertEqual(self.callback(FakeAuthServer(), code="c"), "failed")                         # no state at all

    def test_expired_pending_authorization(self):
        verifier = self.started()
        state = self.state_for(verifier)
        self.store.rows[7]["pending_expires_at"] = time.time() - 1
        self.assertEqual(self.callback(FakeAuthServer(), state=state, code="c"), "expired")

    def test_user_declines_and_exchange_failure(self):
        state = self.state_for(self.started())
        self.assertEqual(self.callback(FakeAuthServer(), state=state, error="access_denied"), "denied")
        self.assertEqual(self.store.rows[7]["status"], "pending")        # nothing was linked
        state = self.state_for(self.started())
        bad = FakeAuthServer((400, {"error": "unauthorized_client"}))
        self.assertEqual(self.callback(bad, state=state, code="c"), "failed")
        self.assertNotEqual(self.store.rows[7]["status"], "linked")

    def test_unlink_revokes_remotely_and_stops_billing(self):
        self.store.ensure_row(7)
        self.store.rows[7].update(status="linked", connection_id="ocon_1", user_profile_id="uprof_1")
        auth = FakeAuthServer((200, {"revoked_connection_ids": ["ocon_1"]}))
        with patch.object(cl, "_post_json", auth):
            cl.unlink(self.store, USER, self.env)
        self.assertEqual(auth.calls[0][0], "https://auth.claude.com/v1/oauth/revoke")
        self.assertEqual(auth.calls[0][1]["connection_id"], "ocon_1")
        self.assertEqual(self.store.rows[7]["status"], "revoked")
        self.assertIsNone(cl.billing_profile_for(self.store, USER))

    def test_unlink_when_claude_is_unreachable_still_stops_billing_locally(self):
        self.store.ensure_row(7)
        self.store.rows[7].update(status="linked", connection_id="ocon_1", user_profile_id="uprof_1")
        with patch.object(cl, "_post_json", FakeAuthServer((503, {}))):
            with self.assertRaises(cl.LinkError):
                cl.unlink(self.store, USER, self.env)
        self.assertIsNone(cl.billing_profile_for(self.store, USER))        # never billed again from here
        self.assertEqual(self.store.rows[7]["last_error"], "remote_revoke_failed")
        self.assertTrue(cl.public_status(self.store, USER, self.env)["needs_attention"])

    def test_unlink_with_nothing_linked_is_a_noop(self):
        with patch.object(cl, "_post_json", FakeAuthServer()):
            cl.unlink(self.store, USER, self.env)                           # would raise IndexError if it called out


class AuthServerRequestTest(unittest.TestCase):
    """The request to Claude's auth host must be identifiable, and a refusal must explain itself in the log."""

    def test_request_names_itself_and_a_non_json_refusal_is_kept_for_the_log(self):
        import io
        import urllib.error
        seen = {}

        def refuse(req, timeout=None):
            seen["ua"] = req.get_header("User-agent")
            raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {"content-type": "text/plain", "server": "edge"},
                                         io.BytesIO(b"error code: 1010"))

        with patch.object(cl.urllib.request, "urlopen", refuse):
            status, body = cl._post_json("https://auth.example/v1/oauth/par", {"client_assertion": "SECRET.JWT.SIG"})
        self.assertEqual(status, 403)
        self.assertTrue(seen["ua"].startswith("MeatCODE-claude-link/"))     # never the stdlib default
        self.assertIn("error code: 1010", body["_raw"])
        self.assertNotIn("SECRET", body["_raw"])

    def test_documented_json_error_is_passed_through_unchanged(self):
        import io
        import urllib.error

        def refuse(req, timeout=None):
            raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {"content-type": "application/json"},
                                         io.BytesIO(b'{"error": "invalid_client", "error_description": "aud"}'))

        with patch.object(cl.urllib.request, "urlopen", refuse):
            self.assertEqual(cl._post_json("https://auth.example/x", {}),
                             (401, {"error": "invalid_client", "error_description": "aud"}))

    def test_assertion_claims_show_audience_but_never_the_token(self):
        import base64
        import json
        import os
        import tempfile
        claims = {"aud": "api.anthropic.com", "iss": "https://idp", "sub": "svc", "iat": 100, "exp": 400, "jti": "j"}
        seg = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
        with tempfile.NamedTemporaryFile("w", suffix=".jwt", delete=False) as fh:
            fh.write("HEADERPART.%s.SIGNATUREPART" % seg)
        try:
            out = cl.assertion_claims({"ANTHROPIC_IDENTITY_TOKEN_FILE": fh.name})
        finally:
            os.unlink(fh.name)
        self.assertIn("aud=api.anthropic.com", out)
        self.assertIn("lifetime_s=300", out)
        self.assertIn("has_jti=True", out)
        self.assertNotIn("SIGNATUREPART", out)
        self.assertNotIn(seg, out)
        self.assertTrue(cl.assertion_claims({}).startswith("unreadable"))


if __name__ == "__main__":
    unittest.main()
