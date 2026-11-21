# Last updated: 2026-11-21 UTC · Claude (Sonnet 5.5) · end-to-end test of the accounts layer over a REAL local HTTP server (fake stores, fake Claude)
"""Drives the real Handler (so the wiring in meatcode_server.py is what is tested): landing redirect, pages, sign-up,
cookies, the shared-password gate staying intact, who pays for an Oracle answer, and the Claude callback."""
import base64
import http.client
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "local-fixture-not-a-key", "DATABASE_URL": "", "APP_ENV": "dev"}):
    import meatcode_server as server
import claude_link
import user_accounts
from accounts_fakes import MemoryLinkStore, MemoryStore

BASIC = {"Authorization": "Basic " + base64.b64encode(b"meatcode:team-pw").decode()}
JSON_H = {"Content-Type": "application/json"}
ENV = {"CLAUDE_OAUTH_CLIENT_ID": "client-xyz", "CLAUDE_OAUTH_REDIRECT_URI": "https://site.test/claude/billing/callback",
       "ANTHROPIC_FEDERATION_RULE_ID": "fdrl_1", "ANTHROPIC_ORGANIZATION_ID": "org", "ANTHROPIC_SERVICE_ACCOUNT_ID": "svac_1",
       "ANTHROPIC_WORKSPACE_ID": "wrkspc_1", "SIGNUP_MODE": "invite", "SIGNUP_INVITE_CODE": "seaweed", "APP_ENV": "dev"}


def answer_text(sse):
    """Reassemble the streamed answer: the data lines that follow each `event: chunk`."""
    out, event = [], None
    for line in sse.splitlines():
        if line.startswith("event: "):
            event = line[7:]
        elif line.startswith("data: ") and event == "chunk":
            out.append(line[6:])
    return "".join(out)


def fake_claude(label, log):
    """A fake Anthropic client that records which 'account' answered and with what kwargs."""
    class Stream:
        text_stream = iter("Hello from " + label)
        def __enter__(self): return self
        def __exit__(self, *a): return False
    def stream(**kw):
        log.append((label, kw))
        return Stream()
    def create(**kw):
        log.append((label, kw))
        return SimpleNamespace(content=[SimpleNamespace(type="text", text="{}")])
    return SimpleNamespace(messages=SimpleNamespace(stream=stream, create=create))


class AccountsServerTests(unittest.TestCase):
    def setUp(self):
        user_accounts.THROTTLE.reset(*list(user_accounts.THROTTLE._hits))
        self.users, self.links, self.calls = MemoryStore(), MemoryLinkStore(), []
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        token = os.path.join(tmp.name, "token")
        Path(token).write_text("jwt")
        env = {**os.environ, **ENV, "ANTHROPIC_IDENTITY_TOKEN_FILE": token}
        patches = [
            patch.object(server, "_accounts_on", lambda: True),
            patch.object(server, "_acct_store", lambda: (self.users, self.links)),
            patch.object(server, "SITE_PASSWORD", "team-pw"),
            patch.object(server, "client", fake_claude("OUR-KEY", self.calls)),
            patch.object(server, "_operator_client", lambda: fake_claude("OPERATOR", self.calls)),
            patch.object(server, "DATABASE_URL", ""),
            patch.object(os, "environ", env),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.addCleanup(self.httpd.server_close)
        self.addCleanup(self.httpd.shutdown)
        self.port = self.httpd.server_address[1]

    def call(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            h = dict(headers or {})
            data = None
            if body is not None:
                data, h = json.dumps(body), {**JSON_H, **h}
            conn.request(method, path, body=data, headers=h)
            r = conn.getresponse()
            if "text/event-stream" in (r.getheader("Content-Type") or ""):
                # The server leaves the socket open after a stream (existing behaviour, keep-alive header), so read to `done`.
                lines = []
                while True:
                    line = r.fp.readline().decode("utf-8", "replace")
                    if not line:
                        break
                    lines.append(line)
                    if line.strip() == "event: done":
                        break
                raw = "".join(lines)
            else:
                raw = r.read().decode("utf-8", "replace")
            try:
                parsed = json.loads(raw)
            except ValueError:
                parsed = raw
            return r.status, parsed, {k.lower(): v for k, v in r.getheaders()}
        finally:
            conn.close()

    def sign_up(self, email="a@example.com"):
        status, body, hdr = self.call("POST", "/api/account/signup", {"email": email, "password": "correct horse battery", "invite_code": "seaweed"},
                                      {"Origin": "http://127.0.0.1:%d" % self.port})
        self.assertEqual(status, 201, body)
        return {"Cookie": hdr["set-cookie"].split(";")[0]}

    # ── landing + pages ──────────────────────────────────────────────────────
    def test_visitors_land_on_welcome_and_pages_need_no_password(self):
        status, _, hdr = self.call("GET", "/")
        self.assertEqual((status, hdr["location"]), (302, "/welcome"))
        for path in ("/welcome", "/account", "/login", "/connect"):
            status, body, hdr = self.call("GET", path)
            self.assertEqual(status, 200, path)
            self.assertRegex(body, r"<title>[^<]*MeatCODE")
            self.assertIn("no-cache", hdr.get("cache-control", ""))
        status, body, _ = self.call("GET", "/api/account/me")
        self.assertEqual((status, body["signed_in"], body["signup_mode"]), (200, False, "invite"))

    def test_shared_password_team_flow_is_unchanged(self):
        self.assertEqual(self.call("GET", "/app/meatcode_mockup.html")[0], 401)                       # still gated
        self.assertEqual(self.call("GET", "/app/meatcode_mockup.html", headers=BASIC)[0], 200)
        self.assertEqual(self.call("GET", "/", headers=BASIC)[0], 302)                                # team goes straight to the product
        self.assertEqual(self.call("GET", "/", headers=BASIC)[2]["location"], "/app/meatcode_mockup.html")

    # ── sign-up / session ───────────────────────────────────────────────────
    def test_signup_session_unlocks_the_site_and_logout_locks_it(self):
        cookie = self.sign_up()
        self.assertEqual(self.call("GET", "/app/meatcode_mockup.html", headers=cookie)[0], 200)
        status, me, _ = self.call("GET", "/api/account/me", headers=cookie)
        self.assertEqual((me["signed_in"], me["user"]["email"], me["claude"]["status"]), (True, "a@example.com", "unlinked"))
        self.call("POST", "/api/account/logout", {}, {**cookie, "Origin": "http://127.0.0.1:%d" % self.port})
        self.assertEqual(self.call("GET", "/app/meatcode_mockup.html", headers=cookie)[0], 401)

    def test_account_api_refuses_cross_origin_and_non_json_posts(self):
        body = {"email": "a@example.com", "password": "correct horse battery", "invite_code": "seaweed"}
        self.assertEqual(self.call("POST", "/api/account/signup", body, {"Origin": "https://evil.test"})[0], 403)
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request("POST", "/api/account/signup", body="email=a", headers={"Content-Type": "application/x-www-form-urlencoded"})
        self.assertEqual(conn.getresponse().status, 415)
        conn.close()
        self.assertEqual(self.users.users, {})

    def test_signup_without_the_invitation_is_refused(self):
        status, body, _ = self.call("POST", "/api/account/signup", {"email": "a@example.com", "password": "correct horse battery", "invite_code": "guess"})
        self.assertEqual(status, 403)

    # ── who pays for an Oracle answer ───────────────────────────────────────
    def ask(self, headers):
        return self.call("POST", "/api/ask", {"question": "What makes meaty flavour?"}, headers)

    def test_team_member_uses_our_key_exactly_as_before(self):
        status, body, _ = self.ask(BASIC)
        self.assertEqual(status, 200)
        self.assertEqual(answer_text(body), "Hello from OUR-KEY")
        label, kw = self.calls[0]
        self.assertEqual(label, "OUR-KEY")
        self.assertNotIn("extra_body", kw)

    def test_signed_in_individual_without_a_link_is_asked_to_connect_and_our_key_is_never_used(self):
        status, body, _ = self.ask(self.sign_up())
        self.assertEqual(status, 402)
        self.assertEqual(body["error"], "connect_claude")
        self.assertEqual(self.calls, [])                                                             # nothing was spent anywhere

    def test_signed_in_individual_with_a_link_is_billed_to_their_own_profile(self):
        cookie = self.sign_up()
        self.links.ensure_row(1)
        self.links.rows[1].update(status="linked", connection_id="ocon_1", user_profile_id="uprof_ME")
        status, body, _ = self.ask(cookie)
        self.assertEqual(status, 200)
        self.assertEqual(answer_text(body), "Hello from OPERATOR")
        self.assertTrue(self.calls)
        for label, kw in self.calls:
            self.assertEqual(label, "OPERATOR")                                                      # never OUR-KEY
            self.assertEqual(kw["extra_headers"]["anthropic-user-profile-id"], "uprof_ME")
            self.assertEqual(kw["extra_body"]["billing_policy"]["bill_to"], "user_profile")

    def test_a_revoked_link_stops_billing_immediately(self):
        cookie = self.sign_up()
        self.links.ensure_row(1)
        self.links.rows[1].update(status="revoked", connection_id="ocon_1", user_profile_id="uprof_ME")
        self.assertEqual(self.ask(cookie)[0], 402)

    def test_ecosystem_and_consensus_routes_also_refuse_unlinked_individuals(self):
        cookie = self.sign_up()
        with patch.object(server, "_flag_on", lambda key: key == "ecosystem_module"), patch.object(server, "ecosystem", object()):
            self.assertEqual(self.call("POST", "/api/ecosystem/intent", {"q": "x"}, cookie)[0], 402)
        with patch.object(server, "DATABASE_URL", "postgres://never-contacted"):    # route checks this first; 402 comes before any query
            self.assertEqual(self.call("GET", "/api/consensus-demo?q=umami", headers=cookie)[0], 402)
        self.assertEqual(self.calls, [])

    # ── Claude link endpoints ───────────────────────────────────────────────
    def test_start_requires_sign_in_then_returns_the_approval_url(self):
        origin = {"Origin": "http://127.0.0.1:%d" % self.port}
        self.assertEqual(self.call("POST", "/api/account/claude/start", {}, origin)[0], 401)
        cookie = {**self.sign_up(), **origin}
        class Op:
            user_profiles = SimpleNamespace(create=lambda **kw: SimpleNamespace(id="uprof_1"))
        with patch.object(server, "_operator_client", lambda: Op()), \
             patch.object(claude_link, "client_assertion", lambda env: "jwt"), \
             patch.object(claude_link, "_post_json", lambda url, payload, timeout=10: (201, {"request_uri": "urn:req:1"})):
            status, body, _ = self.call("POST", "/api/account/claude/start", {}, cookie)
        self.assertEqual(status, 200, body)
        self.assertTrue(body["url"].startswith("https://auth.claude.com/oauth/authorize?"))

    def test_start_when_not_configured_is_a_clean_503(self):
        origin = {"Origin": "http://127.0.0.1:%d" % self.port}
        cookie = {**self.sign_up(), **origin}
        with patch.dict(os.environ, {"CLAUDE_OAUTH_CLIENT_ID": ""}):
            status, body, _ = self.call("POST", "/api/account/claude/start", {}, cookie)
        self.assertEqual(status, 503)
        self.assertNotIn("CLAUDE_OAUTH", json.dumps(body))                                           # no config names leak to users

    def test_callback_links_and_redirects_with_fixed_wording_only(self):
        cookie = self.sign_up()
        self.links.ensure_row(1)
        self.links.rows[1].update(user_profile_id="uprof_1")
        self.links.set_pending(1, claude_link._hash("st-1"), "v" * 64)
        with patch.object(claude_link, "client_assertion", lambda env: "jwt"), \
             patch.object(claude_link, "_post_json", lambda url, payload, timeout=10: (200, {"connection_id": "ocon_9"})):
            status, _, hdr = self.call("GET", "/claude/billing/callback?state=st-1&code=abc", headers=cookie)
        self.assertEqual((status, hdr["location"]), (302, "/connect?claude=linked"))
        self.assertEqual(self.links.rows[1]["status"], "linked")
        # a hostile callback can't make the page say anything: reasons are a fixed vocabulary
        status, _, hdr = self.call("GET", "/claude/billing/callback?state=zzz&error=<script>alert(1)</script>", headers=cookie)
        self.assertEqual(hdr["location"], "/connect?claude=expired")

    def test_connect_screen_uses_the_official_claude_button_and_loads_nothing_external(self):
        status, body, _ = self.call("GET", "/connect")
        self.assertEqual(status, 200)
        for needle in ('class="claude-button', "Link your Claude organization", "#D97757", "/api/account/claude/start", "/api/account/me"):
            self.assertIn(needle, body)
        for page in ("/connect", "/welcome", "/account"):
            html = self.call("GET", page)[1]
            self.assertNotRegex(html, r"<script[^>]+src=|<link[^>]+href=\"https?://|@import", page)   # self-contained: no third-party loads
        self.assertIn("/connect", self.call("GET", "/welcome")[1])                                  # the landing page leads into it

    def test_landing_has_one_button_the_gfi_lockup_and_the_new_copy(self):
        html = self.call("GET", "/welcome")[1]
        self.assertEqual(html.count('class="btn primary"'), 2)                       # nav + hero: the same single action
        self.assertEqual(html.count(">Connect Claude<"), 2)
        for gone in ("Create account", "Create your account", "Bring your own Claude", ">Sign in<"):
            self.assertNotIn(gone, html)
        self.assertIn("MeatCODE is an open-source, free platform", html)
        self.assertIn("/app/assets/gfi_logo.png", html)
        self.assertIn("/connect", html)

    def test_the_gfi_logo_is_public_but_other_assets_stay_gated(self):
        status, _, hdr = self.call("GET", "/app/assets/gfi_logo.png")
        self.assertEqual((status, hdr["content-type"]), (200, "image/png"))
        self.assertEqual(self.call("GET", "/app/assets/oracle-answer.js")[0], 401)

    def test_callback_without_a_session_goes_to_sign_in(self):
        status, _, hdr = self.call("GET", "/claude/billing/callback?state=x&code=y")
        self.assertEqual((status, hdr["location"]), (302, "/account?claude=signin&next=/connect"))


class FlagOffTests(unittest.TestCase):
    """With the flag off the site is exactly what it was: no new routes, no landing redirect."""

    def test_flag_off_means_no_account_routes(self):
        with patch.object(server, "_accounts_on", lambda: False), patch.object(server, "SITE_PASSWORD", "team-pw"):
            httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
            threading.Thread(target=httpd.serve_forever, daemon=True).start()
            try:
                def get(path):
                    c = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=10)
                    c.request("GET", path)
                    r = c.getresponse()
                    r.read()
                    c.close()
                    return r.status
                self.assertEqual(get("/"), 401)                    # the shared-password prompt, as before
                self.assertEqual(get("/welcome"), 401)             # not served, not even to look at
                self.assertEqual(get("/api/account/me"), 401)
            finally:
                httpd.shutdown()
                httpd.server_close()

    def test_registry_flag_is_dev_only(self):
        flag = json.loads(Path("Release Center/features.json").read_text())["flags"]["user_accounts"]
        self.assertEqual((flag["dev"], flag["prod"]), (True, False))      # staging only; production stays off until Lior flips it


if __name__ == "__main__":
    unittest.main()
