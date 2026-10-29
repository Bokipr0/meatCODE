# Last updated: 2026-10-29 10:49 UTC · Full-Stack · public config allowlist and prior request/privacy boundary regression checks.
import ast
import datetime
from email.message import Message
import gzip
from http.server import SimpleHTTPRequestHandler
import io
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.parse import urlparse

from server import research_http


class InputError(ValueError):
    status, code = 400, "invalid_research_input"


class WithdrawnError(Exception):
    status, code = 410, "research_session_withdrawn"


class StorageError(Exception):
    status, code = 503, "research_storage_unavailable"


class FakeResearch:
    InputError, WithdrawnError, StorageError = InputError, WithdrawnError, StorageError

    def __init__(self):
        self.calls = []
        self.error = None

    def config(self, env, app_env):
        return {"enabled": env.get("USER_RESEARCH_ENABLED") == "1", "environment": app_env,
                "clarity_project_id": "z4upnrbddu", "consent_version": "2026-10-29",
                "retention_days": 90, "private_token": "must-not-be-returned"}

    def _write(self, name, db, env, payload):
        self.calls.append((name, db, env, payload))
        if self.error:
            raise self.error
        return {"ok": True}

    def write_events(self, *args):
        return self._write("events", *args)

    def write_feedback(self, *args):
        return self._write("feedback", *args)

    def withdraw(self, *args):
        return self._write("withdraw", *args)


class ReadSpy(io.BytesIO):
    reads = 0

    def read(self, *args):
        self.reads += 1
        return super().read(*args)


class Handler:
    def __init__(self, path="/api/research/events", body=b"{}", headers=None):
        self.path = path
        self.headers = Message()
        defaults = {"Host": "example.test", "Origin": "https://example.test",
                    "Sec-Fetch-Site": "same-origin", "X-MeatCODE-Research": "1",
                    "Content-Type": "application/json", "Content-Length": str(len(body))}
        if headers:
            defaults.update(headers)
        for k, v in defaults.items():
            if v is not None:
                self.headers[k] = v
        self.rfile, self.wfile = ReadSpy(body), io.BytesIO()
        self.close_connection = False
        self.response_headers = {}
        self.status = None

    def send_response(self, code):
        self.status = code

    def send_header(self, key, value):
        self.response_headers[key] = value

    def end_headers(self):
        pass

    def result(self):
        return json.loads(self.wfile.getvalue())


class ResearchHTTPTests(unittest.TestCase):
    def setUp(self):
        self.module = FakeResearch()
        with research_http._capture_lock:
            research_http._captures.clear()

    def call(self, handler=None, method="POST", path=None, db="configured-db", env=None, flag=True, module=True):
        h = handler or Handler()
        research_http.handle(h, method, path or h.path, self.module if module else None,
                             db, "prod", env or {}, flag)
        return h

    def test_config_has_public_fields_only_and_no_store(self):
        h = self.call(Handler("/api/research/config"), method="GET", env={"CLARITY_EXPORT_TOKEN": "secret"})
        self.assertEqual(h.status, 200)
        self.assertEqual(set(h.result()), {"enabled", "environment", "clarity_project_id", "consent_version", "retention_days", "posthog"})
        self.assertEqual(set(h.result()["posthog"]), {"enabled", "project_token", "api_host"})
        self.assertTrue(h.result()["enabled"])
        self.assertEqual(h.response_headers["Cache-Control"], "no-store")
        self.assertEqual(h.rfile.reads, 0)

    def test_posthog_config_contains_no_private_fields(self):
        from server import user_research
        token="phc_"+"publicfixture"*3
        env={"POSTHOG_PROJECT_TOKEN":token,"POSTHOG_API_HOST":"https://eu.i.posthog.com",
             "POSTHOG_PERSONAL_API_KEY":"private-fixture","RESEARCH_ADMIN_TOKEN":"private-admin-fixture",
             "CLARITY_EXPORT_TOKEN":"private-clarity-fixture"}
        config=research_http.effective_config(user_research,env,"prod",True,"private-database-fixture")
        self.assertTrue(config["posthog"]["enabled"])
        self.assertEqual(config["posthog"]["project_token"],token)
        self.assertNotIn("private-",json.dumps(config))
        config=research_http.effective_config(user_research,env,"prod",False,"private-database-fixture")
        self.assertFalse(config["posthog"]["enabled"])

    def test_effective_switch_and_database_required(self):
        for env, flag, db, expected in [({}, True, "db", True), ({}, False, "db", False),
                                        ({}, True, "", False), ({"USER_RESEARCH_ENABLED": "1"}, False, "db", False)]:
            with self.subTest(env=env, flag=flag, db=db):
                h = self.call(Handler("/api/research/config"), method="GET", env=env, flag=flag, db=db)
                self.assertEqual(h.result()["enabled"], expected)
        for value in ("false", "0", "off", "no", " FALSE "):
            h = self.call(env={"USER_RESEARCH_ENABLED": value})
            self.assertEqual(h.status, 404)
            self.assertEqual(h.rfile.reads, 0)

    def test_withdrawal_stays_available_when_capture_off(self):
        h = self.call(Handler("/api/research/withdraw"), env={"USER_RESEARCH_ENABLED": "false"}, flag=False)
        self.assertEqual(h.status, 200)
        self.assertEqual(self.module.calls[0][0], "withdraw")

    def test_event_and_feedback_dispatch(self):
        for route, name in (("events", "events"), ("feedback", "feedback")):
            h = self.call(Handler("/api/research/" + route))
            self.assertEqual(h.status, 200)
            self.assertEqual(self.module.calls[-1], (name, "configured-db", "prod", {}))
            self.assertEqual(h.response_headers["Cache-Control"], "no-store")

    def test_length_checks_precede_body_read(self):
        for length, expected in ((None, 411), ("0", 400), ("-1", 400), ("+2", 400),
                                 ("1.5", 400), ("2, 2", 400), ("16385", 413), ("9999999999", 413)):
            with self.subTest(length=length):
                h = self.call(Handler(headers={"Content-Length": length}))
                self.assertEqual(h.status, expected)
                self.assertEqual(h.rfile.reads, 0)
                self.assertTrue(h.close_connection)
                self.assertEqual(h.response_headers["Connection"], "close")

    def test_duplicate_content_length_is_rejected_without_read(self):
        h = Handler()
        h.headers["Content-Length"] = "2"
        self.call(h)
        self.assertEqual(h.status, 411)
        self.assertEqual(h.rfile.reads, 0)

    def test_maximum_sized_body_is_accepted(self):
        body = b'{"padding":"' + b"a" * (research_http.MAX_BODY_BYTES - 14) + b'"}'
        self.assertEqual(len(body), research_http.MAX_BODY_BYTES)
        self.assertEqual(self.call(Handler(body=body)).status, 200)

    def test_transfer_encoding_is_always_rejected(self):
        for encoding in ("chunked", "identity", ""):
            h = self.call(Handler(headers={"Transfer-Encoding": encoding}))
            self.assertEqual(h.status, 400)
            self.assertEqual(h.rfile.reads, 0)

    def test_content_type_and_required_custom_header(self):
        for headers, expected in (({"Content-Type": "text/plain"}, 415),
                                  ({"Content-Type": None}, 415),
                                  ({"X-MeatCODE-Research": None}, 403),
                                  ({"X-MeatCODE-Research": "true"}, 403)):
            h = self.call(Handler(headers=headers))
            self.assertEqual(h.status, expected)
            self.assertEqual(h.rfile.reads, 0)
        self.assertEqual(self.call(Handler(headers={"Content-Type": "application/json; charset=utf-8"})).status, 200)

    def test_origin_and_fetch_metadata_are_strict(self):
        invalid = (None, "null", "https://other.test", "https://example.test/", "https://example.test?",
                   "https://example.test#", "https://user@example.test", "https://u:p@example.test",
                   "ftp://example.test", "https://example.test:443", "https://example.test/path",
                   "https://example.test?q=x", "https://example.test#x", "\x00https://example.test")
        for origin in invalid:
            with self.subTest(origin=origin):
                h = self.call(Handler(headers={"Origin": origin}))
                self.assertEqual(h.status, 403)
                self.assertEqual(h.rfile.reads, 0)
        for site in ("cross-site", "same-site", "unexpected"):
            self.assertEqual(self.call(Handler(headers={"Sec-Fetch-Site": site})).status, 403)
        for site in (None, "none", "same-origin"):
            self.assertEqual(self.call(Handler(headers={"Sec-Fetch-Site": site})).status, 200)

    def test_duplicate_origin_or_fetch_metadata_is_rejected(self):
        for key, value in (("Origin", "https://example.test"), ("Sec-Fetch-Site", "same-origin")):
            h = Handler()
            h.headers[key] = value
            self.assertEqual(self.call(h).status, 403)

    def test_localhost_and_ipv6_origins(self):
        for host, origin in (("localhost:8000", "http://localhost:8000"), ("[::1]:8000", "http://[::1]:8000")):
            self.assertEqual(self.call(Handler(headers={"Host": host, "Origin": origin})).status, 200)

    def test_malformed_truncated_and_non_object_json(self):
        for body in (b"{", b"[]", b"null", b"\xff\xff", b'{"a":' + b"[" * 1100):
            h = self.call(Handler(body=body))
            self.assertEqual(h.status, 400)
            self.assertTrue(h.close_connection)
        self.assertEqual(self.call(Handler(body=b"{}", headers={"Content-Length": "3"})).status, 400)
        self.assertFalse(self.module.calls)

    def test_read_timeout_is_sanitized(self):
        h = Handler()
        h.rfile.read = lambda n: (_ for _ in ()).throw(TimeoutError("private detail"))
        self.assertEqual(self.call(h).status, 400)
        self.assertNotIn("private detail", h.wfile.getvalue().decode())

    def test_process_limit_and_withdrawal_exemption(self):
        with patch.object(research_http.time, "monotonic", return_value=100):
            for _ in range(research_http.CAPTURE_LIMIT):
                self.assertEqual(self.call().status, 200)
            blocked = self.call()
            self.assertEqual(blocked.status, 429)
            self.assertEqual(blocked.rfile.reads, 0)
            self.assertEqual(self.call(Handler("/api/research/withdraw")).status, 200)
        with patch.object(research_http.time, "monotonic", return_value=160):
            self.assertEqual(self.call().status, 200)

    def test_safe_error_mapping(self):
        for error, status in ((InputError("SQL secret body"), 400), (WithdrawnError("SQL secret body"), 410),
                              (StorageError("SQL secret body"), 503), (RuntimeError("SQL secret body"), 503)):
            self.module.error = error
            h = self.call()
            self.assertEqual(h.status, status)
            self.assertNotIn("SQL secret body", h.wfile.getvalue().decode())

    def test_unknown_routes_and_missing_module(self):
        for method, path in (("GET", "/api/research/events"), ("POST", "/api/research/config"),
                             ("GET", "/api/research/export"), ("POST", "/api/research/unknown")):
            h = self.call(Handler(path), method=method)
            self.assertEqual(h.status, 404)
            self.assertEqual(h.rfile.reads, 0)
        self.assertEqual(self.call(module=False).status, 503)
        self.assertEqual(self.call(Handler("/api/research/config"), method="GET", module=False).status, 503)

    def test_server_auth_precedes_research_routes(self):
        source = Path("server/meatcode_server.py").read_text()
        handler = next(n for n in ast.parse(source).body if isinstance(n, ast.ClassDef) and n.name == "Handler")
        selected = [n for n in handler.body if isinstance(n, ast.FunctionDef) and n.name in ("do_GET", "do_POST")]
        module = ast.Module(body=[ast.ClassDef(name="RouteGate", bases=[], keywords=[], body=selected, decorator_list=[])], type_ignores=[])
        ns = {"urlparse": urlparse}
        exec(compile(ast.fix_missing_locations(module), "<isolated-auth-gates>", "exec"), ns)
        gate = ns["RouteGate"]()
        gate.path = "/api/research/events"
        gate._authorized = lambda: False
        gate._deny = lambda: "denied"
        self.assertEqual(gate.do_POST(), "denied")
        self.assertEqual(gate.do_GET(), "denied")

    def test_shared_scientific_backup_excludes_private_research_schema(self):
        source = Path("server/meatcode_server.py").read_text()
        handler = next(n for n in ast.parse(source).body if isinstance(n, ast.ClassDef) and n.name == "Handler")
        backup = next(n for n in handler.body if isinstance(n, ast.FunctionDef) and n.name == "_handle_data_backup_download")
        calls = []

        def run(command, **kwargs):
            calls.append(command)
            return SimpleNamespace(returncode=0, stdout=b"scientific-backup", stderr=b"")

        ns = {"datetime": datetime, "shutil": SimpleNamespace(which=lambda name: "/fake/pg_dump"),
              "subprocess": SimpleNamespace(run=run), "DATABASE_URL": "fake-database", "gzip": gzip}
        exec(compile(ast.Module(body=[backup], type_ignores=[]), "<isolated-backup>", "exec"), ns)
        h = SimpleNamespace(_send_binary=lambda data, mime, filename: data)
        result = ns["_handle_data_backup_download"](h)
        self.assertEqual(gzip.decompress(result), b"scientific-backup")
        self.assertIn("--exclude-schema=user_research", calls[0])

    def test_private_research_exports_cannot_be_served_as_static_files(self):
        tree = ast.parse(Path("server/meatcode_server.py").read_text())
        handler = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Handler")
        selected = [n for n in handler.body if isinstance(n, ast.FunctionDef)
                    and n.name in ("_private_research_path", "send_head", "do_GET")]

        class StaticBase:
            translate_path = SimpleHTTPRequestHandler.translate_path

            def do_GET(self):
                return "served"

            def send_head(self):
                return "headers"

        module = ast.Module(body=[ast.ClassDef(name="StaticGate", bases=[ast.Name(id="StaticBase", ctx=ast.Load())],
                                               keywords=[], body=selected, decorator_list=[])], type_ignores=[])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data/user_research").mkdir(parents=True)
            (root / "data/user_research/export.jsonl").write_text("private")
            (root / "public-alias").symlink_to(root / "data/user_research", target_is_directory=True)
            ns = {"os": os, "SERVE_DIR": directory, "urlparse": urlparse, "APP_ENV": "prod", "StaticBase": StaticBase}
            exec(compile(ast.fix_missing_locations(module), "<isolated-static-boundary>", "exec"), ns)
            h = ns["StaticGate"]()
            h.directory = directory
            h._authorized = lambda: True
            denied = []
            h.send_error = lambda code, message: denied.append(code)
            for path in ("/data/user_research/export.jsonl", "/data/%75ser_research/export.jsonl",
                         "/app/%2e%2e/data/user_research/export.jsonl", "/public-alias/export.jsonl"):
                with self.subTest(path=path):
                    h.path = path
                    self.assertIsNone(h.do_GET())
                    self.assertEqual(denied[-1], 404)
                    self.assertIsNone(h.send_head())
                    self.assertEqual(denied[-1], 404)
            for path in ("/app/meatcode_mockup.html", "/data/scientific.csv", "/data/user_research_public/export.jsonl"):
                h.path = path
                self.assertEqual(h.do_GET(), "served")
                self.assertEqual(h.send_head(), "headers")


if __name__ == "__main__":
    unittest.main()
