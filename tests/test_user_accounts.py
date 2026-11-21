# Last updated: 2026-11-21 UTC · Claude (Sonnet 5.5) · unit tests for server/user_accounts.py (no Postgres)
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import user_accounts as ua
from accounts_fakes import MemoryStore

H = {"User-Agent": "test"}
HTTPS = {"User-Agent": "test", "X-Forwarded-Proto": "https"}
GOOD = "correct horse battery"


def cookie_token(set_cookie):
    return set_cookie.split(";")[0].split("=", 1)[1]


class PasswordTests(unittest.TestCase):
    def test_roundtrip_and_wrong_password(self):
        h = ua.hash_password(GOOD)
        self.assertTrue(h.startswith("scrypt$"))
        self.assertTrue(ua.verify_password(GOOD, h))
        self.assertFalse(ua.verify_password("wrong password!!", h))

    def test_hashes_are_salted(self):
        self.assertNotEqual(ua.hash_password(GOOD), ua.hash_password(GOOD))

    def test_malformed_hash_is_just_false(self):
        for bad in ("", "x", "scrypt$1$2", "md5$a$b$c$d$e", "scrypt$a$b$c$d$e"):
            self.assertFalse(ua.verify_password(GOOD, bad))

    def test_email_normalisation(self):
        self.assertEqual(ua.normalize_email("  Me@Example.COM "), "me@example.com")
        for bad in ("", None, "no-at-sign", "a@b", "a b@c.de", "x" * 250 + "@a.bc"):
            self.assertIsNone(ua.normalize_email(bad))


class SignupPolicyTests(unittest.TestCase):
    def test_default_is_invitation_only_and_needs_a_configured_code(self):
        ok, why = ua.signup_allowed({}, "anything")
        self.assertFalse(ok)
        self.assertIn("no invitation code is configured", why)

    def test_invite_code(self):
        env = {"SIGNUP_INVITE_CODE": "seaweed"}
        self.assertFalse(ua.signup_allowed(env, "")[0])
        self.assertFalse(ua.signup_allowed(env, "SEAWEED")[0])      # case-sensitive
        self.assertTrue(ua.signup_allowed(env, " seaweed ")[0])

    def test_open_closed_and_garbage_mode(self):
        self.assertTrue(ua.signup_allowed({"SIGNUP_MODE": "open"}, "")[0])
        self.assertFalse(ua.signup_allowed({"SIGNUP_MODE": "closed", "SIGNUP_INVITE_CODE": "x"}, "x")[0])
        self.assertEqual(ua.signup_mode({"SIGNUP_MODE": "wide-open-please"}), "closed")   # unknown -> fail safe


class AccountFlowTests(unittest.TestCase):
    def setUp(self):
        ua.THROTTLE.reset(*list(ua.THROTTLE._hits))
        self.store = MemoryStore()
        self.env = {"SIGNUP_MODE": "invite", "SIGNUP_INVITE_CODE": "seaweed"}

    def signup(self, **over):
        body = {"email": "Lior@Example.com", "password": GOOD, "invite_code": "seaweed", "display_name": "Lior"}
        body.update(over)
        return ua.op_signup(self.store, body, self.env, "1.2.3.4", HTTPS)

    def test_signup_creates_user_and_a_hardened_session_cookie(self):
        code, obj, cookie = self.signup()
        self.assertEqual(code, 201)
        self.assertEqual(obj["user"]["email"], "lior@example.com")
        self.assertNotIn("password", str(obj).lower().replace("password_hash", ""))
        for flag in ("HttpOnly", "SameSite=Lax", "Secure", "Path=/"):
            self.assertIn(flag, cookie)
        token = cookie_token(cookie)
        self.assertNotIn(token, self.store.sessions)                     # only the hash is stored
        self.assertEqual(ua.current_user(self.store, {"Cookie": "a=b; mc_session=%s" % token})["email"], "lior@example.com")

    def test_cookie_is_not_marked_secure_over_plain_http(self):
        _, _, cookie = ua.op_signup(self.store, {"email": "a@b.co", "password": GOOD, "invite_code": "seaweed"}, self.env, "ip", H)
        self.assertNotIn("Secure", cookie)

    def test_signup_validation(self):
        self.assertEqual(self.signup(invite_code="nope")[0], 403)
        self.assertEqual(self.signup(email="bad")[0], 400)
        self.assertEqual(self.signup(password="short")[0], 400)
        self.assertEqual(self.signup(password="x" * 300)[0], 400)
        self.assertEqual(self.signup(password=12345678901234)[0], 400)   # not a string
        self.assertEqual(self.store.users, {})

    def test_duplicate_email_is_a_conflict_for_invite_holders_only(self):
        self.assertEqual(self.signup()[0], 201)
        self.assertEqual(self.signup(email="LIOR@example.com")[0], 409)
        self.assertEqual(self.signup(invite_code="nope")[0], 403)        # no leak without the invitation

    def test_login_logout_roundtrip(self):
        self.signup()
        code, _, cookie = ua.op_login(self.store, {"email": "lior@example.com", "password": GOOD}, "ip", H)
        self.assertEqual(code, 200)
        headers = {"Cookie": cookie.split(";")[0]}
        self.assertIsNotNone(ua.current_user(self.store, headers))
        code, _, clear = ua.op_logout(self.store, headers)
        self.assertEqual(code, 200)
        self.assertIn("Max-Age=0", clear)
        self.assertIsNone(ua.current_user(self.store, headers))          # the session is really gone

    def test_wrong_password_and_unknown_email_look_identical(self):
        self.signup()
        a = ua.op_login(self.store, {"email": "lior@example.com", "password": "wrong-password-1"}, "ip", H)
        b = ua.op_login(self.store, {"email": "nobody@example.com", "password": "wrong-password-1"}, "ip", H)
        self.assertEqual(a[:2], b[:2])
        self.assertEqual(a[0], 401)

    def test_throttle_blocks_guessing_then_resets_on_success_elsewhere(self):
        self.signup()
        for _ in range(ua.THROTTLE.limit):
            self.assertEqual(ua.op_login(self.store, {"email": "lior@example.com", "password": "wrong-password-1"}, "9.9.9.9", H)[0], 401)
        # even the right password is refused while blocked — and a different IP can't unlock this account
        self.assertEqual(ua.op_login(self.store, {"email": "lior@example.com", "password": GOOD}, "9.9.9.9", H)[0], 429)
        self.assertEqual(ua.op_login(self.store, {"email": "lior@example.com", "password": GOOD}, "8.8.8.8", H)[0], 429)

    def test_disabled_user_cannot_log_in_or_use_an_old_session(self):
        _, _, cookie = self.signup()
        self.store.users["lior@example.com"]["disabled"] = True
        self.assertEqual(ua.op_login(self.store, {"email": "lior@example.com", "password": GOOD}, "ip", H)[0], 401)
        self.assertIsNone(ua.current_user(self.store, {"Cookie": cookie.split(";")[0]}))

    def test_store_outage_reads_as_signed_out(self):
        class Broken:
            def session_user(self, _):
                raise RuntimeError("db down")
        self.assertIsNone(ua.current_user(Broken(), {"Cookie": "mc_session=abc"}))


class RequestHelperTests(unittest.TestCase):
    def test_same_origin(self):
        ok = ua.same_origin
        self.assertTrue(ok({"Host": "site.test"}))                                       # no Origin: not a browser cross-site post
        self.assertTrue(ok({"Origin": "https://site.test", "Host": "site.test"}))
        self.assertTrue(ok({"Origin": "https://site.test", "Host": "internal:10000", "X-Forwarded-Host": "site.test"}))
        self.assertFalse(ok({"Origin": "https://evil.test", "Host": "site.test"}))
        self.assertFalse(ok({"Origin": "https://site.test.evil.test", "Host": "site.test"}))

    def test_cookie_parsing(self):
        self.assertEqual(ua.session_token_from_headers({"Cookie": "x=1; mc_session=tok; y=2"}), "tok")
        self.assertEqual(ua.session_token_from_headers({"Cookie": "x=1"}), "")
        self.assertEqual(ua.session_token_from_headers({}), "")


if __name__ == "__main__":
    unittest.main()
