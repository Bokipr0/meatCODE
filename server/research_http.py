# Last updated: 2026-10-31 · Self-reported name linked immutably to one research session.
"""HTTP glue only. The caller MUST apply its existing site-password gate first.

Storage and consent validation live in user_research. No model client, database
connection, credentials, IP tracking or application bootstrap is imported here.
"""
from collections import deque
from http.cookies import SimpleCookie, CookieError
import json
import re
import socket
import threading
import time
from urllib.parse import urlsplit

MAX_BODY_BYTES = 16384
CAPTURE_LIMIT = 120
CAPTURE_WINDOW_SECONDS = 60
READ_TIMEOUT_SECONDS = 5
_captures = deque()
_capture_lock = threading.Lock()
_FALSE_VALUES = frozenset(("false", "0", "off", "no"))
_INTERNAL_COOKIE = "__Host-mc_research_internal"
_AUTOMATED_UA = re.compile(r"googlebot|bingbot|duckduckbot|baiduspider|yandexbot|headlesschrome|playwright|puppeteer|python-requests|python-urllib|(?:^|[\s;(])curl(?:/|$)|(?:^|[\s;(])wget(?:/|$)", re.I)


def _browser_exclusion(headers):
    """Conservative exclusions only; never retain or return raw browser headers."""
    if headers is None:
        return ""
    if _single_header(headers, "X-MeatCODE-Internal") == "1":
        return "internal"
    values = headers.get_all("Cookie", []) if hasattr(headers, "get_all") else [headers.get("Cookie", "")]
    for raw in values:
        cookies = SimpleCookie()
        try:
            cookies.load(raw or "")
            value = cookies.get(_INTERNAL_COOKIE)
            if value is not None and value.value == "1":
                return "internal"
        except (ValueError, TypeError, CookieError):
            pass
    agents = headers.get_all("User-Agent", []) if hasattr(headers, "get_all") else [headers.get("User-Agent", "")]
    return "automation" if any(_AUTOMATED_UA.search(value or "") is not None for value in agents) else ""


def _excluded_browser(headers):
    return bool(_browser_exclusion(headers))

_POST_ROUTES = {
    "/api/research/name": "name_session",
    "/api/research/events": "write_events",
    "/api/research/chat": "write_chat",
    "/api/research/feedback": "write_feedback",
    "/api/research/withdraw": "withdraw",
}


def _production_request(app_env, environ, headers):
    """Host is validated from the request, never forwarded/caller-controlled config."""
    if app_env != "prod" or str(environ.get("RENDER", "")).strip().lower() != "true" or headers is None:
        return False
    host = _single_header(headers, "Host")
    return isinstance(host, str) and host.lower() in ("meatcode-oracle.onrender.com", "meatcode-oracle.onrender.com:443")


def effective_config(module, environ, app_env, flag_enabled, database_url, headers=None):
    """Only real production intake may opt in; configuration cannot override scope."""
    settings = dict(environ)
    disabled = str(settings.get("USER_RESEARCH_ENABLED", "")).strip().lower() in _FALSE_VALUES
    production = _production_request(app_env, environ, headers)
    enabled = bool(production and not _excluded_browser(headers) and flag_enabled and database_url and not disabled)
    settings["USER_RESEARCH_ENABLED"] = "1" if enabled else "0"
    raw = module.config(settings, app_env)
    # Explicit allowlist: never return storage URLs, admin tokens or future private fields.
    return {
        "enabled": bool(enabled and raw.get("enabled")),
        "environment": raw["environment"],
        "capture_excluded": "nonproduction" if not production else _browser_exclusion(headers),
        "demo_mode": bool(enabled and raw.get("demo_mode") is True),
        "clarity_project_id": raw["clarity_project_id"] if enabled else "",
        "consent_version": raw["consent_version"],
        "retention_days": raw["retention_days"],
        "posthog": {
            "enabled": bool(enabled and raw.get("posthog", {}).get("enabled")),
            "project_token": raw.get("posthog", {}).get("project_token", "") if enabled else "",
            "api_host": raw.get("posthog", {}).get("api_host", "") if enabled else "",
        },
    }


def _reply(handler, body, status=200):
    content = json.dumps(body, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(content)))
    if handler.close_connection:
        handler.send_header("Connection", "close")
    handler.end_headers()
    try:
        handler.wfile.write(content)
    except (BrokenPipeError, ConnectionResetError):
        pass


def _error(handler, status, code, message, close=False):
    if close:
        handler.close_connection = True
    return _reply(handler, {"ok": False, "error": {"code": code, "message": message}}, status)


def _single_header(headers, name):
    values = headers.get_all(name) if hasattr(headers, "get_all") else None
    if values is not None:
        return values[0] if len(values) == 1 else None
    return headers.get(name)


def _same_origin(headers):
    origin = _single_header(headers, "Origin")
    host = _single_header(headers, "Host")
    site = _single_header(headers, "Sec-Fetch-Site")
    if site is not None and site not in ("same-origin", "none"):
        return False
    if not origin or not host or any(not 33 <= ord(c) <= 126 for c in origin + host):
        return False
    if "?" in origin or "#" in origin:
        return False
    if hasattr(headers, "get_all") and len(headers.get_all("Sec-Fetch-Site", [])) > 1:
        return False
    try:
        parsed = urlsplit(origin)
        # Accessing port also validates its numeric range. Do not trust forwarded hosts.
        parsed.port
        return (parsed.scheme in ("http", "https") and bool(parsed.hostname)
                and parsed.username is None and parsed.password is None
                and not parsed.path and not parsed.query and not parsed.fragment
                and parsed.netloc.lower() == host.lower())
    except ValueError:
        return False


def _capture_allowed():
    now = time.monotonic()
    with _capture_lock:
        while _captures and now - _captures[0] >= CAPTURE_WINDOW_SECONDS:
            _captures.popleft()
        if len(_captures) >= CAPTURE_LIMIT:
            return False
        _captures.append(now)
        return True


def _read_payload(handler, withdrawal=False, max_bytes=MAX_BODY_BYTES):
    headers = handler.headers
    if "Transfer-Encoding" in headers:
        return None, (400, "invalid_framing", "Transfer encoding is not supported.")
    length = _single_header(headers, "Content-Length")
    if length is None:
        return None, (411, "length_required", "A single Content-Length is required.")
    if not re.fullmatch(r"[0-9]{1,10}", length):
        return None, (400, "invalid_length", "Content-Length must be a positive integer.")
    length = int(length)
    if length <= 0:
        return None, (400, "invalid_length", "Content-Length must be a positive integer.")
    if length > max_bytes:
        return None, (413, "body_too_large", "Research request exceeds the size limit.")
    content_type = _single_header(headers, "Content-Type") or ""
    if content_type.split(";", 1)[0].strip().lower() != "application/json":
        return None, (415, "json_required", "Research requests must use application/json.")
    if _single_header(headers, "X-MeatCODE-Research") != "1" or not _same_origin(headers):
        return None, (403, "same_origin_required", "Research requests must come from this platform.")
    if not withdrawal and not _capture_allowed():
        return None, (429, "research_rate_limited", "Research requests are temporarily limited. Please retry later.")
    connection = getattr(handler, "connection", None)
    previous_timeout = None
    try:
        if connection is not None:
            previous_timeout = connection.gettimeout()
            connection.settimeout(READ_TIMEOUT_SECONDS)
        raw = handler.rfile.read(length)
        if len(raw) != length:
            return None, (400, "invalid_json", "Research request is not valid JSON.")
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            return None, (400, "invalid_json", "Research request must be a JSON object.")
        return payload, None
    except (ValueError, RecursionError, OSError, socket.timeout):
        return None, (400, "invalid_json", "Research request is not valid JSON.")
    finally:
        if connection is not None:
            try:
                connection.settimeout(previous_timeout)
            except OSError:
                pass


def handle(handler, method, path, module, database_url, app_env, environ, flag_enabled):
    """Production-only public config and bounded write routes, after site authentication."""
    if method == "GET" and path == "/api/research/config":
        if module is None:
            return _error(handler, 503, "research_unavailable", "Research settings are temporarily unavailable.")
        try:
            return _reply(handler, effective_config(module, environ, app_env, flag_enabled, database_url, handler.headers))
        except Exception:
            return _error(handler, 503, "research_unavailable", "Research settings are temporarily unavailable.")
    if method != "POST" or path not in _POST_ROUTES:
        return _error(handler, 404, "not_found", "Research endpoint not found.", close=method == "POST")
    if not _production_request(app_env, environ, handler.headers):
        return _error(handler, 404, "research_disabled", "Research capture is disabled on this server.", close=True)
    try:
        secure_origin = urlsplit(_single_header(handler.headers, "Origin") or "").scheme == "https"
    except ValueError:
        secure_origin = False
    if not secure_origin:
        return _error(handler, 403, "same_origin_required", "Research requests must come from this platform.", close=True)
    # Exclusion precedes parsing, rate accounting and all storage. Withdrawal stays
    # available on production so stopping capture never prevents session deletion.
    if path != "/api/research/withdraw" and _excluded_browser(handler.headers):
        return _error(handler, 404, "research_excluded", "This browser is excluded from research collection.", close=True)
    if module is None:
        return _error(handler, 503, "research_unavailable", "Research storage is temporarily unavailable.", close=True)
    try:
        enabled = effective_config(module, environ, app_env, flag_enabled, database_url, handler.headers)["enabled"]
    except Exception:
        return _error(handler, 503, "research_unavailable", "Research settings are temporarily unavailable.", close=True)
    if path != "/api/research/withdraw" and not enabled:
        return _error(handler, 404, "research_disabled", "Research capture is disabled.", close=True)
    payload, error = _read_payload(handler, withdrawal=path == "/api/research/withdraw", max_bytes=393216 if path=="/api/research/chat" else MAX_BODY_BYTES)
    if error:
        return _error(handler, *error, close=True)
    try:
        result = getattr(module, _POST_ROUTES[path])(database_url, app_env, payload)
        return _reply(handler, result)
    except module.InputError:
        return _error(handler, 400, "invalid_research_input", "Research input is invalid.")
    except module.WithdrawnError:
        return _error(handler, 410, "research_session_withdrawn", "This research session was withdrawn.")
    except Exception:
        # Includes StorageError and unexpected failures. Never disclose SQL, user text or secrets.
        return _error(handler, 503, "research_storage_unavailable", "Research storage is temporarily unavailable.")
