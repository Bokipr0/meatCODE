# Last updated: 2026-11-21 UTC · Claude (Sonnet 5.5) · Claude-first profiles (start with the Claude link; name + optional credentials afterwards; pending sessions are not sign-ins). Prior: NEW — individual user accounts (signup / login / sessions) for the `user_accounts` flag
"""Individual MeatCODE user accounts.

Why this exists: the site is gated by ONE shared password (SITE_PASSWORD, HTTP Basic). To let each person
connect *their own* Claude organization (server/claude_link.py) we first need to know who they are.

Scope, deliberately small and stdlib-only (no new dependency):
  * email + password sign-up / login / logout, cookie sessions, a /me probe
  * scrypt password hashes; session tokens stored only as SHA-256 hashes
  * invite-gated sign-up by default (SIGNUP_MODE=invite + SIGNUP_INVITE_CODE) — open registration would
    hand the corpus API to anyone on the internet, which is a product decision, not a default
  * in-memory brute-force throttle, same-origin check on every state-changing request

Nothing here talks to Claude. The functions take a `store` (see PgStore) so tests run without Postgres.
"""
import base64
import hashlib
import hmac
import re
import secrets
import threading
import time
from urllib.parse import urlparse

SESSION_COOKIE = "mc_session"
SESSION_DAYS = 30
MIN_PASSWORD = 10
MAX_PASSWORD = 256            # bounds the cost of one scrypt call
_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2 ** 14, 8, 1
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ─── passwords ───────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=32)
    return "scrypt$%d$%d$%d$%s$%s" % (_SCRYPT_N, _SCRYPT_R, _SCRYPT_P,
                                      base64.b64encode(salt).decode(), base64.b64encode(dk).decode())


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_b64, dk_b64 = stored.split("$")
        if scheme != "scrypt":
            return False
        expected = base64.b64decode(dk_b64)
        got = hashlib.scrypt(password.encode("utf-8"), salt=base64.b64decode(salt_b64),
                             n=int(n), r=int(r), p=int(p), dklen=len(expected))
        return hmac.compare_digest(got, expected)
    except Exception:
        return False


_DUMMY_HASH = hash_password("not-a-real-password")   # equalises timing when the email is unknown


def normalize_email(email):
    e = (email or "").strip()
    if len(e) > 254 or not _EMAIL_RE.match(e):
        return None
    return e.lower()


# ─── sign-up policy ──────────────────────────────────────────────────────────
def signup_mode(env) -> str:
    """invite (default) | open | closed. Anything unrecognised is treated as closed — fail safe."""
    mode = (env.get("SIGNUP_MODE") or "invite").strip().lower()
    return mode if mode in ("invite", "open", "closed") else "closed"


def signup_allowed(env, invite_code) -> (bool, str):
    mode = signup_mode(env)
    if mode == "closed":
        return False, "Sign-up is closed."
    if mode == "open":
        return True, ""
    expected = (env.get("SIGNUP_INVITE_CODE") or "").strip()
    if not expected:
        return False, "Sign-up is by invitation and no invitation code is configured."
    if not hmac.compare_digest((invite_code or "").strip().encode(), expected.encode()):
        return False, "That invitation code isn't valid."
    return True, ""


# ─── throttle (per process; Render runs one instance) ───────────────────────
class Throttle:
    def __init__(self, limit=8, window=900):
        self.limit, self.window = limit, window
        self._hits, self._lock = {}, threading.Lock()

    def _live(self, key, now):
        hits = [t for t in self._hits.get(key, []) if now - t < self.window]
        self._hits[key] = hits
        return hits

    def blocked(self, *keys) -> bool:
        now = time.time()
        with self._lock:
            return any(len(self._live(k, now)) >= self.limit for k in keys)

    def fail(self, *keys):
        now = time.time()
        with self._lock:
            for k in keys:
                self._live(k, now).append(now)
            if len(self._hits) > 5000:                      # hard cap: drop the stalest half
                for k in sorted(self._hits, key=lambda k: max(self._hits[k] or [0]))[:2500]:
                    self._hits.pop(k, None)

    def reset(self, *keys):
        with self._lock:
            for k in keys:
                self._hits.pop(k, None)


THROTTLE = Throttle()


# ─── request helpers ─────────────────────────────────────────────────────────
def same_origin(headers) -> bool:
    """State-changing requests must come from this site. Browsers always send Origin on cross-site POSTs;
    a request with no Origin (curl, server-side) can't be a cross-site form post and is allowed."""
    origin = headers.get("Origin")
    if not origin:
        return True
    host = headers.get("X-Forwarded-Host") or headers.get("Host") or ""
    return urlparse(origin).netloc.lower() == host.split(",")[0].strip().lower()


def session_token_from_headers(headers) -> str:
    for part in (headers.get("Cookie") or "").split(";"):
        name, _, val = part.strip().partition("=")
        if name == SESSION_COOKIE and val:
            return val
    return ""


def _is_https(headers) -> bool:
    return (headers.get("X-Forwarded-Proto") or "").split(",")[0].strip().lower() == "https"


def cookie_header(token: str, headers, clear=False) -> str:
    parts = ["%s=%s" % (SESSION_COOKIE, "" if clear else token), "Path=/", "HttpOnly", "SameSite=Lax",
             "Max-Age=%d" % (0 if clear else SESSION_DAYS * 86400)]
    if _is_https(headers):
        parts.append("Secure")
    return "; ".join(parts)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def public_user(u) -> dict:
    email = u.get("email")
    name = u.get("display_name") or (email.split("@")[0] if email else "")
    claude_only = bool(u.get("claude_only"))
    return {"id": u["id"], "email": email, "display_name": name, "claude_only": claude_only,
            "has_credentials": bool(email),                          # can sign in with email + password
            "needs_name": claude_only and not (u.get("display_name") or "").strip()}


# ─── operations: each returns (http_status, payload, set_cookie_or_None) ────
def op_signup(store, body, env, ip, headers):
    ok, why = signup_allowed(env, body.get("invite_code"))
    if THROTTLE.blocked("ip:" + ip):
        return 429, {"error": "Too many attempts. Try again in a few minutes."}, None
    if not ok:
        THROTTLE.fail("ip:" + ip)
        return 403, {"error": why}, None
    email = normalize_email(body.get("email"))
    password = body.get("password") or ""
    if not email:
        return 400, {"error": "Enter a valid email address."}, None
    if not isinstance(password, str) or len(password) < MIN_PASSWORD or len(password) > MAX_PASSWORD:
        return 400, {"error": "Use a password of at least %d characters." % MIN_PASSWORD}, None
    if store.get_user_by_email(email):
        return 409, {"error": "An account with this email already exists — sign in instead."}, None
    name = (body.get("display_name") or "").strip()[:80] or None
    user = store.create_user(email, hash_password(password), name)
    token = secrets.token_urlsafe(32)
    store.create_session(_hash_token(token), user["id"], SESSION_DAYS, headers.get("User-Agent", "")[:200])
    return 201, {"ok": True, "user": public_user(user)}, cookie_header(token, headers)


def op_login(store, body, ip, headers):
    email = normalize_email(body.get("email")) or ""
    keys = ("ip:" + ip, "email:" + email)
    if THROTTLE.blocked(*keys):
        return 429, {"error": "Too many attempts. Try again in a few minutes."}, None
    password = body.get("password") or ""
    user = store.get_user_by_email(email) if email and isinstance(password, str) and len(password) <= MAX_PASSWORD else None
    good = verify_password(password if isinstance(password, str) else "", user["password_hash"] if user else _DUMMY_HASH)
    if not (user and good) or user.get("disabled"):
        THROTTLE.fail(*keys)
        return 401, {"error": "Email or password is incorrect."}, None
    THROTTLE.reset(*keys)
    token = secrets.token_urlsafe(32)
    store.create_session(_hash_token(token), user["id"], SESSION_DAYS, headers.get("User-Agent", "")[:200])
    store.touch_login(user["id"])
    return 200, {"ok": True, "user": public_user(user)}, cookie_header(token, headers)


def op_logout(store, headers):
    token = session_token_from_headers(headers)
    if token:
        store.delete_session(_hash_token(token))
    return 200, {"ok": True}, cookie_header("", headers, clear=True)


def current_user(store, headers, allow_pending=False):
    """The signed-in user for this request, or None. Never raises: a store outage reads as 'signed out'.
    A *pending* session (handed out when Claude linking starts, before it completes) is NOT a sign-in: it is
    only returned when the caller explicitly allows it, to finish the link."""
    token = session_token_from_headers(headers)
    if not token:
        return None
    try:
        u = store.session_user(_hash_token(token))
    except Exception:
        return None
    if not u or u.get("disabled"):
        return None
    if u.get("pending") and not allow_pending:
        return None
    return u


# ─── Claude-first accounts: start with the Claude link, add a name (and optionally credentials) afterwards ───
def op_start_claude_profile(store, ip, headers):
    """First click on 'Link your Claude organization' from a visitor with no session: create an unnamed,
    credential-less profile and a PENDING session so the browser can finish the approval. Grants no access.
    Returns (user, set_cookie) or (None, None) when this IP is starting too many."""
    if THROTTLE.blocked("start:" + ip):
        return None, None
    THROTTLE.fail("start:" + ip)                                  # every anonymous start counts, success or not
    try:
        store.purge_stale_provisional()
    except Exception:
        pass
    user = store.create_claude_user()
    token = secrets.token_urlsafe(32)
    store.create_session(_hash_token(token), user["id"], 1, headers.get("User-Agent", "")[:200], pending=True)
    return user, cookie_header(token, headers)


def op_set_name(store, user, body):
    name = " ".join(str(body.get("display_name") or "").split())      # collapse whitespace/newlines
    if len(name) < 2 or len(name) > 80 or any(ord(c) < 32 for c in name):
        return 400, {"error": "Enter a name between 2 and 80 characters."}
    store.set_display_name(user["id"], name)
    return 200, {"ok": True, "display_name": name}


def op_set_credentials(store, user, body):
    """A Claude-only profile can add email + password so it can sign in from another device."""
    if user.get("email"):
        return 409, {"error": "This profile already has an email."}
    email = normalize_email(body.get("email"))
    password = body.get("password") or ""
    if not email:
        return 400, {"error": "Enter a valid email address."}
    if not isinstance(password, str) or len(password) < MIN_PASSWORD or len(password) > MAX_PASSWORD:
        return 400, {"error": "Use a password of at least %d characters." % MIN_PASSWORD}
    if store.get_user_by_email(email) or not store.set_credentials(user["id"], email, hash_password(password)):
        return 409, {"error": "That email is already used by another account."}
    return 200, {"ok": True, "email": email}


# ─── Postgres store ──────────────────────────────────────────────────────────
class PgStore:
    """Thin psycopg2 wrapper. One short-lived connection per call (Neon pools badly across threads)."""

    def __init__(self, database_url):
        self.url = database_url

    def _run(self, sql, params=(), fetch="none"):
        import psycopg2
        from psycopg2.extras import RealDictCursor
        conn = psycopg2.connect(self.url)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params)
                out = None
                if fetch == "one" and cur.description:
                    row = cur.fetchone()
                    out = dict(row) if row else None
                elif fetch == "all" and cur.description:
                    out = [dict(r) for r in cur.fetchall()]
            conn.commit()
            return out
        finally:
            conn.close()

    def get_user_by_email(self, email):
        return self._run("SELECT id, email, password_hash, display_name, disabled FROM app_users WHERE lower(email)=lower(%s)",
                         (email,), "one")

    def create_user(self, email, password_hash, display_name):
        return self._run("INSERT INTO app_users (email, password_hash, display_name) VALUES (%s,%s,%s) "
                         "RETURNING id, email, display_name, disabled", (email, password_hash, display_name), "one")

    def create_claude_user(self):
        return self._run("INSERT INTO app_users (claude_only) VALUES (TRUE) "
                         "RETURNING id, email, display_name, disabled, claude_only", (), "one")

    def set_display_name(self, user_id, name):
        self._run("UPDATE app_users SET display_name=%s WHERE id=%s", (name, user_id))

    def set_credentials(self, user_id, email, password_hash):
        """False when the email is taken (unique index) — never raises for that."""
        import psycopg2
        try:
            self._run("UPDATE app_users SET email=%s, password_hash=%s WHERE id=%s AND email IS NULL",
                      (email, password_hash, user_id))
            return True
        except psycopg2.errors.UniqueViolation:
            return False

    def activate_sessions(self, user_id):
        """The Claude link completed: this person's pending session becomes a real one."""
        self._run("UPDATE app_sessions SET pending=FALSE, expires_at = now() + (%s || ' days')::interval "
                  "WHERE user_id=%s AND pending", (str(SESSION_DAYS), user_id))

    def purge_stale_provisional(self):
        """Claude-only profiles that never finished linking (abandoned clicks) are removed after a day."""
        self._run("DELETE FROM app_users u WHERE u.claude_only AND u.created_at < now() - interval '1 day' "
                  "AND NOT EXISTS (SELECT 1 FROM claude_connections c WHERE c.user_id=u.id AND c.status='linked')")

    def touch_login(self, user_id):
        self._run("UPDATE app_users SET last_login_at=now() WHERE id=%s", (user_id,))

    def create_session(self, token_hash, user_id, days, user_agent, pending=False):
        self._run("DELETE FROM app_sessions WHERE expires_at < now()")
        self._run("INSERT INTO app_sessions (token_hash, user_id, expires_at, user_agent, pending) "
                  "VALUES (%s,%s, now() + (%s || ' days')::interval, %s, %s)",
                  (token_hash, user_id, str(days), user_agent, bool(pending)))

    def session_user(self, token_hash):
        return self._run("SELECT u.id, u.email, u.display_name, u.disabled, u.claude_only, s.pending FROM app_sessions s "
                         "JOIN app_users u ON u.id = s.user_id WHERE s.token_hash=%s AND s.expires_at > now()",
                         (token_hash,), "one")

    def delete_session(self, token_hash):
        self._run("DELETE FROM app_sessions WHERE token_hash=%s", (token_hash,))
