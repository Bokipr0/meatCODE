# Last updated: 2026-11-22 UTC · Claude (Fable 5.2) · optional self-issued client assertion (own OIDC issuer: discovery + JWKS) because the OAuth app's audience is fixed and Render's token cannot carry it. Prior: 2026-11-22 UTC · Claude (Fable 5.2) · auth-server requests send a named User-Agent; refusals log the raw reply + the assertion's non-secret claims. Prior: 2026-11-22 UTC · Claude (Sonnet 5.5) · unbilled trial mode, CreditsRequired + needs_credits flag, billing URL. Prior: 2026-11-21 UTC · Claude (Sonnet 5.5) · BilledClient reports token usage to an optional recorder (usage log). Prior: NEW — Claude Platform OAuth "Linked billing" (user pays for their own Claude usage)
"""Let a signed-in MeatCODE user link THEIR OWN Claude organization, so Oracle calls they make are billed to them.

Anthropic docs (Beta — endpoints may change): platform.claude.com/docs/en/manage-claude/oauth-apps/organization-billing-connections
Flow (OAuth 2.0 authorization-code + PKCE, Anthropic is the authorization server):
  begin_link()   create the user's *user profile* in OUR Claude org (once) -> pushed authorization request (PAR)
                 -> send the browser to Claude's approval page
  finish_link()  callback with ?code&state -> exchange the code for a connection id -> store it
  unlink()       revoke the connection at auth.claude.com
  billing_kwargs() the extra headers/body that make ONE request bill the user's org instead of ours

What this module deliberately does NOT do:
  * It stores no Claude token. Linked billing here uses the *operator service account* path: our back end
    authenticates to the Claude API with Workload Identity Federation (Render's managed OIDC token) and names
    the user's profile on each request. The per-connection access token returned at link time is discarded.
    (Hardening to consider later: per-connection tokens + `disable_operator_only_auth`, which need offline_access
    and encrypted refresh-token storage.)
  * It never falls back to our own key for a signed-in user (that decision lives in meatcode_server.py).
  * The profile id sent on a billed request always comes from the signed-in session — never from request input.
"""
import base64
import hashlib
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.request

BILLING_BETA = "user-profiles-billing-2026-10-01"
AUTH_BASE_DEFAULT = "https://auth.claude.com"
PENDING_MINUTES = 10                        # Anthropic's request_uri lives 600 s
BILLING_URL = "https://platform.claude.com/settings/billing"   # where credits are bought ("Buy credits"; Admin/Billing role)
_JWT_BEARER = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"

# Env the feature needs (names only — values are secrets or IDs and live in the Render dashboard).
REQUIRED_ENV = (
    "CLAUDE_OAUTH_CLIENT_ID",          # public client id of the OAuth app (Console -> OAuth apps)
    "CLAUDE_OAUTH_REDIRECT_URI",       # e.g. https://<host>/claude/billing/callback — must match the app exactly
    "ANTHROPIC_FEDERATION_RULE_ID",    # the next four are Render's managed-OIDC settings for the Claude API
    "ANTHROPIC_ORGANIZATION_ID",
    "ANTHROPIC_SERVICE_ACCOUNT_ID",
    "ANTHROPIC_WORKSPACE_ID",
)


class CreditsRequired(Exception):
    """A request billed to the person's own Claude organization was refused because it has no usable credit
    (HTTP 402, or 403 user_profile_not_billable). Carries no provider detail — the UI shows guided wording."""


def is_credit_error(exc) -> bool:
    text = str(exc).lower()
    return getattr(exc, "status_code", None) == 402 or "user_profile_not_billable" in text


class LinkError(Exception):
    """A failure with a message that is safe to show the user. `status` is the HTTP status to answer with."""

    def __init__(self, message, status=502):
        super().__init__(message)
        self.status = status


# ─── configuration ───────────────────────────────────────────────────────────
def token_file(env):
    """Identity JWT used as the OAuth client assertion. Render sets ANTHROPIC_IDENTITY_TOKEN_FILE itself;
    CLAUDE_OAUTH_ASSERTION_TOKEN_FILE overrides it if the OAuth app expects a different audience."""
    return env.get("CLAUDE_OAUTH_ASSERTION_TOKEN_FILE") or env.get("ANTHROPIC_IDENTITY_TOKEN_FILE") or ""


def missing_env(env):
    out = [k for k in REQUIRED_ENV if not (env.get(k) or "").strip()]
    if not token_file(env):
        out.append("ANTHROPIC_IDENTITY_TOKEN_FILE (set by Render once the federation rule env var is deployed)")
    return out


def configured(env) -> bool:
    return not missing_env(env)


def auth_base(env) -> str:
    return (env.get("CLAUDE_AUTH_BASE") or AUTH_BASE_DEFAULT).rstrip("/")


# ─── self-issued client assertion (optional) ─────────────────────────────────
# The OAuth app accepts exactly ONE audience for its client assertion, fixed by Anthropic ("https://auth.claude.com").
# Render's managed token always carries "api.anthropic.com" and cannot be re-audienced, so on Render the app is
# authenticated with a JWT this server signs itself: it is its own small OIDC issuer (discovery + JWKS below, served
# publicly by meatcode_server.py) registered in the Console as a second identity provider. The Render token keeps
# doing what it is made for — authenticating our back end to the Claude API.
#   CLAUDE_OAUTH_ISSUER            public issuer URL, must end with OIDC_PATH (e.g. https://<host>/oidc/claude-client)
#   CLAUDE_OAUTH_SIGNING_KEY_PEM   RSA private key, PEM (SECRET — lives only in the Render dashboard)
#   CLAUDE_OAUTH_ASSERTION_AUDIENCE / _SUBJECT   optional overrides of the defaults below
OIDC_PATH = "/oidc/claude-client"
ASSERTION_AUDIENCE_DEFAULT = "https://auth.claude.com"
ASSERTION_SUBJECT_DEFAULT = "meatcode-backend"
ASSERTION_SECONDS = 300
_key_cache = {}


def self_issuer(env) -> str:
    """The issuer URL when this server signs its own client assertions, else ''."""
    iss = (env.get("CLAUDE_OAUTH_ISSUER") or "").strip().rstrip("/")
    return iss if iss.startswith("https://") and iss.endswith(OIDC_PATH) and (env.get("CLAUDE_OAUTH_SIGNING_KEY_PEM") or "").strip() else ""


def _b64u(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _signing_key(env):
    """(private_key, public JWK incl. kid). Parsed once per key value; never logged."""
    pem = (env.get("CLAUDE_OAUTH_SIGNING_KEY_PEM") or "").strip().replace("\\n", "\n")
    tag = _hash(pem)
    if tag not in _key_cache:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        key = serialization.load_pem_private_key(pem.encode("utf-8"), password=None)
        if not isinstance(key, rsa.RSAPrivateKey) or key.key_size < 2048:
            raise ValueError("signing key must be RSA, 2048 bits or more")
        pub = key.public_key().public_numbers()
        jwk = {"e": _b64u(pub.e.to_bytes((pub.e.bit_length() + 7) // 8, "big")), "kty": "RSA",
               "n": _b64u(pub.n.to_bytes((pub.n.bit_length() + 7) // 8, "big"))}
        kid = _b64u(hashlib.sha256(json.dumps(jwk, sort_keys=True, separators=(",", ":")).encode()).digest())  # RFC 7638
        _key_cache.clear()
        _key_cache[tag] = (key, {**jwk, "kid": kid, "use": "sig", "alg": "RS256"})
    return _key_cache[tag]


def oidc_discovery(env):
    """The issuer's discovery document, or None when self-issuing is off."""
    iss = self_issuer(env)
    if not iss:
        return None
    return {"issuer": iss, "jwks_uri": iss + "/jwks.json", "id_token_signing_alg_values_supported": ["RS256"],
            "response_types_supported": ["id_token"], "subject_types_supported": ["public"]}


def oidc_jwks(env):
    """Public keys only. None when self-issuing is off or the key cannot be read."""
    if not self_issuer(env):
        return None
    try:
        return {"keys": [_signing_key(env)[1]]}
    except Exception as e:
        sys.stderr.write("[claude-link] signing key unusable: %s\n" % type(e).__name__)
        return None


def _self_assertion_claims(env, now=None) -> dict:
    now = int(now if now is not None else time.time())
    return {"iss": self_issuer(env),
            "sub": (env.get("CLAUDE_OAUTH_ASSERTION_SUBJECT") or ASSERTION_SUBJECT_DEFAULT).strip(),
            "aud": (env.get("CLAUDE_OAUTH_ASSERTION_AUDIENCE") or ASSERTION_AUDIENCE_DEFAULT).strip(),
            "iat": now, "nbf": now - 5, "exp": now + ASSERTION_SECONDS, "jti": secrets.token_urlsafe(16)}


def _sign_assertion(env) -> str:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    key, jwk = _signing_key(env)
    head = _b64u(json.dumps({"alg": "RS256", "typ": "JWT", "kid": jwk["kid"]}, separators=(",", ":")).encode())
    body = _b64u(json.dumps(_self_assertion_claims(env), separators=(",", ":")).encode())
    sig = key.sign(("%s.%s" % (head, body)).encode("ascii"), padding.PKCS1v15(), hashes.SHA256())
    return "%s.%s.%s" % (head, body, _b64u(sig))


def client_assertion(env) -> str:
    """The JWT that authenticates the OAuth app to auth.claude.com. Self-signed (fresh, single use) when
    CLAUDE_OAUTH_ISSUER + CLAUDE_OAUTH_SIGNING_KEY_PEM are set; otherwise the identity token file, read fresh
    on every call because Render rotates it."""
    if self_issuer(env):
        try:
            return _sign_assertion(env)
        except Exception as e:
            sys.stderr.write("[claude-link] could not sign the client assertion: %s\n" % type(e).__name__)
            raise LinkError("Claude linking isn't available on this server right now.", 503)
    try:
        with open(token_file(env), "r", encoding="utf-8") as fh:
            jwt = fh.read().strip()
    except OSError:
        raise LinkError("Claude linking isn't available on this server right now.", 503)
    if not jwt:
        raise LinkError("Claude linking isn't available on this server right now.", 503)
    return jwt


def s256(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode()


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


# ─── HTTP to auth.claude.com (stdlib; the body never contains a secret we log) ──
USER_AGENT = "MeatCODE-claude-link/1.0 (+https://github.com/Bokipr0/meatCODE)"


def _post_json(url, payload, timeout=10):
    # A named User-Agent is required: the stdlib default ("Python-urllib/x.y") is refused at the edge with a bare
    # 403 before the OAuth server ever sees the request (seen on dev 2026-11-21: 403, no JSON, no attempt recorded).
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers={"content-type": "application/json", "accept": "application/json",
                                          "user-agent": USER_AGENT}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        raw = b""
        try:
            raw = e.read() or b""
            body = json.loads(raw.decode("utf-8") or "{}")
            if not isinstance(body, dict):
                body = {}
        except Exception:
            body = {}
        if not isinstance(body.get("error"), str):
            # Not the documented {"error", "error_description"} shape (edge block, rate limit, outage): keep what
            # the server said so the log explains the refusal. The response never echoes our assertion.
            body["_raw"] = "content-type=%s server=%s body=%s" % (
                e.headers.get("content-type"), e.headers.get("server"),
                " ".join(raw.decode("utf-8", "replace").split())[:400])
        return e.code, body
    except Exception as e:                                    # DNS, timeout, TLS …
        sys.stderr.write("[claude-link] request to auth server failed: %s\n" % type(e).__name__)
        raise LinkError("Couldn't reach Claude. Please try again in a moment.", 502)


def assertion_claims(env) -> str:
    """Non-secret claims of the identity JWT (never the token or its signature), for the refusal log:
    the OAuth app accepts exactly one audience, so `aud` is the first thing to compare with the Console."""
    if self_issuer(env):
        try:
            c = _self_assertion_claims(env)
            return "self-signed aud=%s iss=%s sub=%s lifetime_s=%s kid=%s" % (
                c["aud"], c["iss"], c["sub"], ASSERTION_SECONDS, _signing_key(env)[1]["kid"])
        except Exception as e:
            return "self-signed, key unreadable (%s)" % type(e).__name__
    try:
        with open(token_file(env), "r", encoding="utf-8") as fh:
            part = fh.read().strip().split(".")[1]
        c = json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))
        return "aud=%s iss=%s sub=%s lifetime_s=%s has_jti=%s" % (
            c.get("aud"), c.get("iss"), c.get("sub"),
            (c.get("exp") - c.get("iat")) if isinstance(c.get("exp"), int) and isinstance(c.get("iat"), int) else None,
            "jti" in c)
    except Exception as e:
        return "unreadable (%s)" % type(e).__name__


def _log_refusal(step, status, body, env=None):
    # error codes are fixed vocabulary; error_description can name a config problem — useful to Lior in the log.
    sys.stderr.write("[claude-link] %s refused: HTTP %s error=%s desc=%s\n" % (
        step, status, str(body.get("error"))[:60], str(body.get("error_description"))[:300]))
    if body.get("_raw"):
        sys.stderr.write("[claude-link] %s refusal detail: %s\n" % (step, body["_raw"]))
    if env is not None:
        sys.stderr.write("[claude-link] %s client assertion: %s\n" % (step, assertion_claims(env)))


# ─── operator client (our back end -> Claude API, via Workload Identity Federation) ──
def operator_client(env):
    """Anthropic SDK client that authenticates with Render's OIDC token (no API key). Needs a recent SDK."""
    try:
        import anthropic
        creds = anthropic.WorkloadIdentityCredentials(
            identity_token_provider=anthropic.IdentityTokenFile(env["ANTHROPIC_IDENTITY_TOKEN_FILE"]),
            federation_rule_id=env["ANTHROPIC_FEDERATION_RULE_ID"],
            organization_id=env["ANTHROPIC_ORGANIZATION_ID"],
            service_account_id=env["ANTHROPIC_SERVICE_ACCOUNT_ID"],
            workspace_id=env["ANTHROPIC_WORKSPACE_ID"],
        )
        return anthropic.Anthropic(credentials=creds)
    except (ImportError, AttributeError, KeyError) as e:
        sys.stderr.write("[claude-link] operator client unavailable: %s\n" % type(e).__name__)
        raise LinkError("Claude linking isn't available on this server right now.", 503)


def billing_kwargs(user_profile_id: str) -> dict:
    """Keyword args for client.messages.create()/stream() that bill THIS request to the linked user."""
    return {
        "extra_headers": {"anthropic-user-profile-id": user_profile_id, "anthropic-beta": BILLING_BETA},
        "extra_body": {"billing_policy": {"type": "billing_policy", "bill_to": "user_profile"}},
    }


class BilledClient:
    """Duck-types the slice of the Anthropic client MeatCODE uses (`.messages.create` / `.messages.stream`).

    With a `user_profile_id` every call is billed to that person's Claude organization. With `None` it passes calls
    straight through to `base_client` unbilled — used for the free trial sessions on MeatCODE's own key.
    `recorder(model, input_tokens, output_tokens, status, input_text=, output_text=, kind=)` is called once per call
    (kind 'answer' for streamed answers, 'helper' for the small supporting calls); it is best-effort and never affects
    the request. `on_credits_required()` fires when Claude refuses a *billed* call for lack of credit; the caller then
    gets CreditsRequired instead of a raw provider error."""

    def __init__(self, base_client, user_profile_id, recorder=None, on_credits_required=None):
        self._base, self._rec, self._on_credits = base_client, recorder, on_credits_required
        self._extra = billing_kwargs(user_profile_id) if user_profile_id else None
        self.messages = self._Messages(self)

    def _with_billing(self, kw):
        """Caller's own extra_headers/extra_body are kept; the billing fields always win (no-op for the trial)."""
        if not self._extra:
            return dict(kw)
        out = dict(kw)
        out["extra_headers"] = {**(kw.get("extra_headers") or {}), **self._extra["extra_headers"]}
        out["extra_body"] = {**(kw.get("extra_body") or {}), **self._extra["extra_body"]}
        return out

    def _record(self, model, input_tokens, output_tokens, status, input_text=None, output_text=None, kind=None):
        if not self._rec:
            return
        try:
            self._rec(model, int(input_tokens or 0), int(output_tokens or 0), status,
                      input_text=input_text, output_text=output_text, kind=kind)
        except Exception as e:                                   # never let logging break an answer
            sys.stderr.write("[claude-link] usage log failed: %s\n" % type(e).__name__)

    def _credit_refused(self, exc):
        """Billed call refused for lack of credit -> note it and raise the guided error. Anything else: re-raise as is."""
        if self._extra and is_credit_error(exc):
            if self._on_credits:
                try:
                    self._on_credits()
                except Exception as e:
                    sys.stderr.write("[claude-link] credits flag failed: %s\n" % type(e).__name__)
            raise CreditsRequired("credits required") from exc

    class _Messages:
        def __init__(self, outer):
            self._o = outer

        def create(self, **kw):
            o = self._o
            try:
                resp = o._base.messages.create(**o._with_billing(kw))
            except Exception as e:
                o._record(kw.get("model"), 0, 0, "error", kind="helper")
                o._credit_refused(e)
                raise
            usage = getattr(resp, "usage", None)
            o._record(kw.get("model"), getattr(usage, "input_tokens", 0), getattr(usage, "output_tokens", 0), "ok", kind="helper")
            return resp

        def stream(self, **kw):
            o = self._o
            return _RecordedStream(o, kw.get("model"), o._base.messages.stream(**o._with_billing(kw)),
                                   _last_user_text(kw.get("messages")))


def _last_user_text(messages):
    """The person's input to an answer call: the text of the last user message (None if it can't be read)."""
    try:
        for m in reversed(messages or []):
            if m.get("role") == "user":
                content = m.get("content")
                if isinstance(content, str):
                    return content
                return "".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text") or None
    except Exception:
        pass
    return None


class _RecordedStream:
    """Wraps the SDK's stream context manager: behaves identically, and when it closes reports the token usage plus
    the input and the answer text (answer calls only — helper `create` calls log counts, never text)."""

    def __init__(self, outer, model, manager, input_text=None):
        self._outer, self._model, self._manager, self._stream, self._input = outer, model, manager, None, input_text

    def __enter__(self):
        try:
            self._stream = self._manager.__enter__()             # this is where the HTTP request is made
        except Exception as e:
            self._outer._record(self._model, 0, 0, "error", input_text=self._input, kind="answer")
            self._outer._credit_refused(e)
            raise
        return self._stream

    def __exit__(self, exc_type, exc, tb):
        input_tokens = output_tokens = 0
        try:
            usage = getattr(getattr(self._stream, "current_message_snapshot", None), "usage", None)
            input_tokens, output_tokens = getattr(usage, "input_tokens", 0) or 0, getattr(usage, "output_tokens", 0) or 0
        except Exception:
            pass
        output_text = None
        if not exc_type:
            try:
                final = self._stream.get_final_message()          # the stream is already consumed: returns at once
                output_text = "".join(getattr(b, "text", "") for b in final.content if getattr(b, "type", "") == "text") or None
            except Exception:
                pass
        self._outer._record(self._model, input_tokens, output_tokens, "error" if exc_type else "ok",
                            input_text=self._input, output_text=output_text, kind="answer")
        return self._manager.__exit__(exc_type, exc, tb)


# ─── Postgres store for the connection row ──────────────────────────────────
class PgLinkStore:
    def __init__(self, database_url):
        self.url = database_url

    def _run(self, sql, params=(), fetch=False):
        import psycopg2
        from psycopg2.extras import RealDictCursor
        conn = psycopg2.connect(self.url)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params)
                row = (cur.fetchone() if fetch and cur.description else None)
            conn.commit()
            return dict(row) if row else None
        finally:
            conn.close()

    def get(self, user_id):
        return self._run("SELECT * FROM claude_connections WHERE user_id=%s", (user_id,), True)

    def ensure_row(self, user_id):
        self._run("INSERT INTO claude_connections (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING", (user_id,))

    def set_profile(self, user_id, profile_id):
        self._run("UPDATE claude_connections SET user_profile_id=%s, updated_at=now() WHERE user_id=%s",
                  (profile_id, user_id))

    def set_pending(self, user_id, state_hash, verifier):
        self._run("UPDATE claude_connections SET pending_state_hash=%s, pending_verifier=%s, "
                  "pending_expires_at=now() + (%s || ' minutes')::interval, last_error=NULL, updated_at=now(), "
                  "status = CASE WHEN status='linked' THEN status ELSE 'pending' END WHERE user_id=%s",
                  (state_hash, verifier, str(PENDING_MINUTES), user_id))

    def take_pending(self, user_id, state_hash):
        """Atomically consume the pending authorization (single use): returns the verifier or None."""
        row = self._run("WITH old AS (SELECT user_id, pending_verifier AS v FROM claude_connections "
                        "              WHERE user_id=%s AND pending_state_hash=%s AND pending_expires_at > now() "
                        "              FOR UPDATE) "
                        "UPDATE claude_connections c SET pending_state_hash=NULL, pending_verifier=NULL, "
                        "pending_expires_at=NULL, updated_at=now() FROM old WHERE c.user_id = old.user_id "
                        "RETURNING old.v AS v", (user_id, state_hash), True)
        return row["v"] if row else None

    def mark_linked(self, user_id, connection_id):
        self._run("UPDATE claude_connections SET status='linked', connection_id=%s, linked_at=now(), "
                  "last_error=NULL, updated_at=now() WHERE user_id=%s", (connection_id, user_id))

    def mark_revoked(self, user_id, error=None):
        self._run("UPDATE claude_connections SET status='revoked', last_error=%s, updated_at=now() WHERE user_id=%s",
                  (error, user_id))

    def set_error(self, user_id, code):
        self._run("UPDATE claude_connections SET last_error=%s, updated_at=now() WHERE user_id=%s", (code, user_id))

    def set_needs_credits(self, user_id, flag):
        self._run("UPDATE claude_connections SET needs_credits=%s, needs_credits_at = CASE WHEN %s THEN now() ELSE needs_credits_at END, "
                  "updated_at=now() WHERE user_id=%s", (bool(flag), bool(flag), user_id))


def create_user_profile(op, user_id) -> str:
    """Create the 'user profile' in OUR Claude org that stands for this MeatCODE user. No personal data is sent:
    the name is opaque and the reference ties it back to our row. Uses the SDK resource when the installed SDK
    has it (anthropic >= 2.x); otherwise the same call through the SDK's generic POST."""
    name, ref = "MeatCODE user %d" % user_id, {"reference_id": "meatcode-user-%d" % user_id}
    if hasattr(op, "user_profiles"):
        return op.user_profiles.create(name=name, external_user_details=ref).id
    data = op.post("/v1/user_profiles", cast_to=dict, body={"name": name, "external_user_details": ref},
                   options={"headers": {"anthropic-version": "2026-10-21"}})
    pid = data.get("id") if isinstance(data, dict) else None
    if not pid:
        raise LinkError("Couldn't start linking. Please try again, or contact the MeatCODE team.", 502)
    return pid


# ─── the flow ────────────────────────────────────────────────────────────────
def begin_link(store, user, env, op_client=None, op_factory=None) -> str:
    """Returns the Claude approval-page URL to send the browser to. `op_factory` lets the server hand in its
    cached operator client lazily (only built when this user still needs a profile)."""
    if not configured(env):
        raise LinkError("Claude linking isn't set up on this server yet.", 503)
    store.ensure_row(user["id"])
    row = store.get(user["id"]) or {}
    profile_id = row.get("user_profile_id")
    if not profile_id:
        op = op_client or (op_factory() if op_factory else operator_client(env))
        try:
            profile_id = create_user_profile(op, user["id"])
        except LinkError:
            raise
        except Exception as e:
            sys.stderr.write("[claude-link] user profile create failed: %s %s\n" % (type(e).__name__, str(e)[:300]))
            raise LinkError("Couldn't start linking. Please try again, or contact the MeatCODE team.", 502)
        store.set_profile(user["id"], profile_id)

    state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(64)
    store.set_pending(user["id"], _hash(state), verifier)
    status, body = _post_json(auth_base(env) + "/v1/oauth/par", {
        "response_type": "code",
        "client_id": env["CLAUDE_OAUTH_CLIENT_ID"],
        "redirect_uri": env["CLAUDE_OAUTH_REDIRECT_URI"],
        "scope": "billing:attribution",
        "connection_type": "organization_shared",
        "connection_auth_target": "platform",
        "user_profile_id": profile_id,
        "state": state,
        "code_challenge": s256(verifier),
        "code_challenge_method": "S256",
        "client_assertion_type": _JWT_BEARER,
        "client_assertion": client_assertion(env),
    })
    if status != 201 or not body.get("request_uri"):
        _log_refusal("PAR", status, body, env)
        store.set_error(user["id"], "par_refused")
        raise LinkError("Claude didn't accept the linking request. The MeatCODE team has been notified in the server log.", 502)
    from urllib.parse import urlencode
    return "%s/oauth/authorize?%s" % (auth_base(env), urlencode(
        {"client_id": env["CLAUDE_OAUTH_CLIENT_ID"], "request_uri": body["request_uri"]}))


# Fixed vocabulary shown on the account page — never reflect arbitrary text from the callback URL.
CALLBACK_REASONS = ("linked", "denied", "expired", "failed")


def finish_link(store, user, params, env) -> str:
    """Handle the callback query. Returns one of CALLBACK_REASONS (the page shows fixed text for each)."""
    def first(key):                                            # accepts parse_qs lists or plain dicts
        v = params.get(key)
        return (v[0] if v else "") if isinstance(v, list) else (v or "")
    state, code, err = first("state"), first("code"), first("error")
    if not state:
        return "failed"
    verifier = store.take_pending(user["id"], _hash(state))     # also burns the state: a replayed callback finds nothing
    if not verifier:
        return "expired"
    if err or not code:
        store.set_error(user["id"], "denied" if err == "access_denied" else "callback_error")
        return "denied" if err == "access_denied" else "failed"
    status, body = _post_json(auth_base(env) + "/v1/oauth/token", {
        "grant_type": "authorization_code",
        "code": code,
        "code_verifier": verifier,
        "redirect_uri": env["CLAUDE_OAUTH_REDIRECT_URI"],
        "client_id": env["CLAUDE_OAUTH_CLIENT_ID"],
        "client_assertion_type": _JWT_BEARER,
        "client_assertion": client_assertion(env),
    }, timeout=10)
    connection_id = body.get("connection_id") if status == 200 else None
    if not connection_id:
        _log_refusal("token exchange", status, body, env)
        store.set_error(user["id"], "exchange_failed")
        return "failed"
    store.mark_linked(user["id"], connection_id)               # the access token in `body` is intentionally dropped
    return "linked"


def unlink(store, user, env) -> None:
    row = store.get(user["id"]) or {}
    connection_id = row.get("connection_id")
    if not connection_id or row.get("status") not in ("linked", "revoked"):
        return
    # Stop billing locally first: even if Claude is unreachable, MeatCODE will never bill this connection again.
    store.mark_revoked(user["id"])
    status, body = _post_json(auth_base(env) + "/v1/oauth/revoke", {
        "connection_id": connection_id,
        "client_id": env["CLAUDE_OAUTH_CLIENT_ID"],
        "client_assertion_type": _JWT_BEARER,
        "client_assertion": client_assertion(env),
    })
    if status != 200:
        _log_refusal("revoke", status, body, env)
        store.mark_revoked(user["id"], "remote_revoke_failed")
        raise LinkError("Disconnected here, but Claude didn't confirm. You can also unlink MeatCODE from the "
                        "Claude Console (Settings → OAuth apps).", 502)


def public_status(store, user, env) -> dict:
    row = store.get(user["id"]) or {}
    ready = configured(env)
    out = {"available": ready, "status": row.get("status") or "unlinked",
           "linked_at": row.get("linked_at"), "needs_attention": row.get("last_error") == "remote_revoke_failed",
           "needs_credits": bool(row.get("needs_credits")), "billing_url": BILLING_URL}
    if not ready and (env.get("APP_ENV") or "").lower() != "prod":
        out["setup_missing"] = missing_env(env)               # dev only: tells the team what to configure
    return out


def billing_profile_for(store, user):
    """The user profile id to bill, or None when the user hasn't linked (or has revoked)."""
    row = store.get(user["id"]) or {}
    return row.get("user_profile_id") if row.get("status") == "linked" else None
