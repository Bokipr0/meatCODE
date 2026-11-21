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
from accounts_fakes import MemoryLinkStore, MemoryStore, MemoryUsageStore

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
        current_message_snapshot = SimpleNamespace(usage=SimpleNamespace(input_tokens=11, output_tokens=22))
        def get_final_message(self): return SimpleNamespace(content=[SimpleNamespace(type="text", text="Hello from " + label)])
        def __enter__(self): return self
        def __exit__(self, *a): return False
    def stream(**kw):
        log.append((label, kw))
        return Stream()
    def create(**kw):
        log.append((label, kw))
        return SimpleNamespace(content=[SimpleNamespace(type="text", text="{}")], usage=SimpleNamespace(input_tokens=3, output_tokens=4))
    return SimpleNamespace(messages=SimpleNamespace(stream=stream, create=create))


class AccountsServerTests(unittest.TestCase):
    def setUp(self):
        user_accounts.THROTTLE.reset(*list(user_accounts.THROTTLE._hits))
        self.users, self.links, self.calls = MemoryStore(), MemoryLinkStore(), []
        self.usage = MemoryUsageStore(self.users)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        token = os.path.join(tmp.name, "token")
        Path(token).write_text("jwt")
        env = {**os.environ, **ENV, "ANTHROPIC_IDENTITY_TOKEN_FILE": token}
        patches = [
            patch.object(server, "_accounts_on", lambda: True),
            patch.object(server, "_acct_store", lambda: (self.users, self.links)),
            patch.object(server, "_usage_store", lambda: self.usage),
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
        status, _, hdr = self.call("GET", "/", headers=BASIC)                                         # the landing page is the front door for the team too…
        self.assertEqual((status, hdr["location"]), (302, "/welcome"))
        self.assertIs(self.call("GET", "/api/account/me", headers=BASIC)[1]["team"], True)             # …where they get an "Open MeatCODE" button
        self.assertIs(self.call("GET", "/api/account/me")[1]["team"], False)

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

    def test_billed_requests_are_logged_to_the_users_own_profile_and_nothing_else_is(self):
        cookie = self.sign_up()
        self.links.ensure_row(1)
        self.links.rows[1].update(status="linked", connection_id="ocon_1", user_profile_id="uprof_ME")
        self.assertEqual(self.ask(cookie)[0], 200)
        self.assertEqual([(r["user_id"], r["route"], r["input_tokens"], r["output_tokens"], r["status"]) for r in self.usage.rows],
                         [(1, "/api/ask", 11, 22, "ok")])
        row = self.usage.rows[0]                                                     # tied to THAT Claude user, their session, their input and the answer
        self.assertEqual((row["user_profile_id"], row["connection_id"]), ("uprof_ME", "ocon_1"))
        self.assertEqual(row["session_ref"], user_accounts.session_ref({"Cookie": cookie["Cookie"]}))
        self.assertEqual(len(row["session_ref"]), 12)
        self.assertNotIn(cookie["Cookie"].split("=", 1)[1], str(row))                # never the cookie itself
        self.assertEqual((row["input_text"], row["output_text"]), ("What makes meaty flavour?", "Hello from OPERATOR"))
        self.assertIn(1, self.usage.last_used)                                       # last Claude use stamped for that person
        self.assertEqual(self.ask(BASIC)[0], 200)                                    # team traffic is not attributed to anyone
        self.assertEqual(len(self.usage.rows), 1)

    def test_usage_endpoint_is_private_per_user_and_degrades_quietly(self):
        self.assertEqual(self.call("GET", "/api/account/usage")[0], 401)
        cookie = self.sign_up("a@example.com")
        self.usage.record(1, "/api/ask", "m", 100, 50, "ok")
        self.usage.record(2, "/api/ask", "m", 9999, 9999, "ok")                      # someone else's usage
        status, body, _ = self.call("GET", "/api/account/usage", headers=cookie)
        self.assertEqual(status, 200)
        self.assertEqual((body["available"], body["requests"], body["input_tokens"], body["output_tokens"]), (True, 1, 100, 50))
        self.assertEqual([x["label"] for x in body["recent"]], ["Oracle answer"])
        self.assertRegex(body["recent"][0]["at"], r"^\d{4}-\d\d-\d\dT")              # ISO, parseable in every browser
        for private in ("input_text", "output_text"):                                # the log keeps text; the endpoint never returns the answer
            self.assertNotIn(private, json.dumps(body))
        self.assertIn("last_used_at", body)
        with patch.object(server, "_usage_store", lambda: (_ for _ in ()).throw(RuntimeError("table missing"))):
            self.assertEqual(self.call("GET", "/api/account/usage", headers=cookie)[1], {"available": False})

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
    def start_claude(self, headers=None):
        """POST /api/account/claude/start with Anthropic and our operator client faked out."""
        class Op:
            user_profiles = SimpleNamespace(create=lambda **kw: SimpleNamespace(id="uprof_1"))
        with patch.object(server, "_operator_client", lambda: Op()), \
             patch.object(claude_link, "client_assertion", lambda env: "jwt"), \
             patch.object(claude_link, "_post_json", lambda url, payload, timeout=10: (201, {"request_uri": "urn:req:1"})):
            return self.call("POST", "/api/account/claude/start", {}, {"Origin": "http://127.0.0.1:%d" % self.port, **(headers or {})})

    def finish_claude(self, cookie, state="st-1", **query):
        """Pretend Claude's approval page sent the browser back (code exchange faked)."""
        uid = next(u["id"] for u in self.users.by_id.values() if u["claude_only"])
        self.links.ensure_row(uid)
        self.links.rows[uid].update(user_profile_id="uprof_%d" % uid)
        self.links.set_pending(uid, claude_link._hash(state), "v" * 64)
        qs = "state=%s&" % state + "&".join("%s=%s" % kv for kv in query.items())
        with patch.object(claude_link, "client_assertion", lambda env: "jwt"), \
             patch.object(claude_link, "_post_json", lambda url, payload, timeout=10: (200, {"connection_id": "ocon_9"})):
            return self.call("GET", "/claude/billing/callback?" + qs, headers=cookie)

    def test_signed_in_email_user_can_start_linking_too(self):
        status, body, _ = self.start_claude(self.sign_up())
        self.assertEqual(status, 200, body)
        self.assertTrue(body["url"].startswith("https://auth.claude.com/oauth/authorize?"))

    # ── Claude-first: the Claude button is the way in ───────────────────────
    def test_new_visitor_starts_with_claude_and_no_account_but_gets_no_access_yet(self):
        status, body, hdr = self.start_claude()
        self.assertEqual(status, 200, body)
        self.assertTrue(body["url"].startswith("https://auth.claude.com/oauth/authorize?"))
        cookie = {"Cookie": hdr["set-cookie"].split(";")[0]}
        self.assertEqual([(u["claude_only"], u["email"]) for u in self.users.by_id.values()], [(True, None)])
        self.assertEqual(self.call("GET", "/app/meatcode_mockup.html", headers=cookie)[0], 401)       # pending is not a sign-in
        self.assertEqual(self.call("POST", "/api/account/profile", {"display_name": "Dana"}, {**cookie, "Origin": "http://127.0.0.1:%d" % self.port})[0], 401)
        me = self.call("GET", "/api/account/me", headers=cookie)[1]
        self.assertIs(me["signed_in"], False)

    def test_completing_the_link_grants_access_then_asks_for_a_name(self):
        origin = {"Origin": "http://127.0.0.1:%d" % self.port}
        cookie = {"Cookie": self.start_claude()[2]["set-cookie"].split(";")[0]}
        status, _, hdr = self.finish_claude(cookie, code="abc")
        self.assertEqual((status, hdr["location"]), (302, "/connect?claude=linked"))
        self.assertEqual(self.call("GET", "/app/meatcode_mockup.html", headers=cookie)[0], 200)      # now the session counts
        me = self.call("GET", "/api/account/me", headers=cookie)[1]
        self.assertEqual((me["signed_in"], me["claude"]["status"], me["user"]["needs_name"], me["user"]["has_credentials"]),
                         (True, "linked", True, False))
        self.assertEqual(self.call("POST", "/api/account/profile", {"display_name": "x"}, {**cookie, **origin})[0], 400)
        status, body, _ = self.call("POST", "/api/account/profile", {"display_name": "Dana Levi"}, {**cookie, **origin})
        self.assertEqual((status, body["display_name"]), (200, "Dana Levi"))
        me = self.call("GET", "/api/account/me", headers=cookie)[1]
        self.assertEqual((me["user"]["display_name"], me["user"]["needs_name"]), ("Dana Levi", False))

    def test_the_claude_link_completing_is_recorded_as_a_login_and_shown_with_last_use(self):
        origin = {"Origin": "http://127.0.0.1:%d" % self.port}
        cookie = {"Cookie": self.start_claude()[2]["set-cookie"].split(";")[0]}
        uid = next(iter(self.users.by_id))
        self.assertNotIn("last_login_at", self.users.by_id[uid])
        self.finish_claude(cookie, code="abc")
        self.assertIn("last_login_at", self.users.by_id[uid])                        # activation = login time, stored on the user
        self.assertEqual(self.ask(cookie)[0], 200)                                   # a real answer on the linked org…
        body = self.call("GET", "/api/account/usage", headers=cookie)[1]
        self.assertTrue(body["last_login_at"] and body["last_used_at"])               # …so both times are now on the profile
        self.assertEqual(body["recent"][0]["preview"], "What makes meaty flavour?")
        self.call("POST", "/api/account/login", {"email": "none@example.com", "password": "x"}, origin)   # (smoke: login path unaffected)

    def test_a_declined_link_leaves_the_visitor_signed_out(self):
        cookie = {"Cookie": self.start_claude()[2]["set-cookie"].split(";")[0]}
        status, _, hdr = self.finish_claude(cookie, error="access_denied")
        self.assertEqual(hdr["location"], "/connect?claude=denied")
        self.assertEqual(self.call("GET", "/app/meatcode_mockup.html", headers=cookie)[0], 401)

    def test_anonymous_starts_are_throttled(self):
        for _ in range(user_accounts.THROTTLE.limit):
            self.assertEqual(self.start_claude()[0], 200)
        self.assertEqual(self.start_claude()[0], 429)

    def test_a_claude_only_profile_can_add_credentials_for_other_devices(self):
        origin = {"Origin": "http://127.0.0.1:%d" % self.port}
        cookie = {"Cookie": self.start_claude()[2]["set-cookie"].split(";")[0]}
        self.finish_claude(cookie, code="abc")
        body = {"email": "dana@example.com", "password": "correct horse battery"}
        self.assertEqual(self.call("POST", "/api/account/credentials", body, origin)[0], 401)                # needs a real session
        self.assertEqual(self.call("POST", "/api/account/credentials", body, {**cookie, **origin})[0], 200)
        status, _, hdr = self.call("POST", "/api/account/login", body, origin)                               # a different device
        self.assertEqual(status, 200)
        me = self.call("GET", "/api/account/me", headers={"Cookie": hdr["set-cookie"].split(";")[0]})[1]
        self.assertEqual((me["user"]["email"], me["claude"]["status"]), ("dana@example.com", "linked"))      # same profile, same link
        self.assertEqual(self.call("POST", "/api/account/credentials", body, {**cookie, **origin})[0], 409)  # already has an email

    def test_everyone_can_see_whether_claude_linking_is_set_up_and_dev_sees_what_is_missing(self):
        me = self.call("GET", "/api/account/me")[1]
        self.assertEqual(me["claude_setup"], {"available": True})                        # fully configured in this test env
        with patch.dict(os.environ, {"CLAUDE_OAUTH_CLIENT_ID": ""}):
            setup = self.call("GET", "/api/account/me")[1]["claude_setup"]               # a signed-out visitor, APP_ENV=dev
            self.assertEqual(setup["available"], False)
            self.assertEqual(setup["setup_missing"], ["CLAUDE_OAUTH_CLIENT_ID"])
            with patch.dict(os.environ, {"APP_ENV": "prod"}):
                self.assertEqual(self.call("GET", "/api/account/me")[1]["claude_setup"], {"available": False})   # never names config in prod

    def test_callback_after_the_cookie_was_lost_restarts_from_the_claude_screen(self):
        status, _, hdr = self.call("GET", "/claude/billing/callback?state=x&code=y")
        self.assertEqual((status, hdr["location"]), (302, "/connect?claude=expired"))

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
        for needle in ('class="claude-button', "Link your Claude organization", "#D97757", "/api/account/claude/start", "/api/account/me",
                       "Your name", "/api/account/profile"):
            self.assertIn(needle, body)
        for gone in ("Create account", "I already have one", "needAccount"):             # Claude is the way in: no account form here
            self.assertNotIn(gone, body)
        for gone in ("What happens next", "You stay in control", "You'll need"):          # one centred column, no side cards
            self.assertNotIn(gone, body)
        self.assertIn("saved on your profile", body)                                     # the storage notice must stay
        for page in ("/connect", "/welcome", "/account"):
            html = self.call("GET", page)[1]
            self.assertNotRegex(html, r"<script[^>]+src=|<link[^>]+href=\"https?://|@import", page)   # self-contained: no third-party loads
        self.assertIn("/connect", self.call("GET", "/welcome")[1])                                  # the landing page leads into it

    def test_landing_has_one_button_the_gfi_lockup_and_the_new_copy(self):
        html = self.call("GET", "/welcome")[1]
        self.assertEqual(html.count('class="btn primary"'), 1)                       # exactly one button on the page…
        self.assertEqual(html.count(">Connect Claude<"), 1)                          # …and it is Connect Claude (hero only; no top-right twin)
        for gone_too in ("Team member?", "Owner: Daniel", "<footer"):                # footer removed
            self.assertNotIn(gone_too, html)
        for gone in ("Create account", "Create your account", "Bring your own Claude", ">Sign in<"):
            self.assertNotIn(gone, html)
        self.assertIn("MeatCODE is an open-source, free platform", html)
        self.assertNotIn("d.team", html)                                             # no shared-password shortcut on the landing page
        self.assertIn("data:image/png;base64,", html)                                   # logo is embedded: works from the server and from file://
        self.assertIn("/connect", html)

    def test_profile_menu_script_is_served_to_signed_in_people_only(self):
        self.assertEqual(self.call("GET", "/app/assets/account-menu.js")[0], 401)
        status, body, _ = self.call("GET", "/app/assets/account-menu.js", headers=self.sign_up())
        self.assertEqual(status, 200)
        self.assertIn("/api/account/usage", body)
        self.assertIn("/welcome", body)                                              # logout returns to the landing page
        self.assertNotIn("innerHTML", body)                                          # server strings only via textContent

    def test_the_gfi_logo_is_public_but_other_assets_stay_gated(self):
        status, _, hdr = self.call("GET", "/app/assets/gfi_logo.png")
        self.assertEqual((status, hdr["content-type"]), (200, "image/png"))
        self.assertEqual(self.call("GET", "/app/assets/oracle-answer.js")[0], 401)



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
