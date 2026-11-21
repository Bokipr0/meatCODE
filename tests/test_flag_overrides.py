# Last updated: 2026-11-22 UTC · Claude (Sonnet 5.5) · live DEV feature switches: a Release Center dev toggle must reach the dev site without a redeploy
import http.client
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))
with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "local-fixture-not-a-key", "DATABASE_URL": "", "APP_ENV": "dev"}):
    import meatcode_server as server

FILE_FLAGS = {"alpha": {"label": "Alpha", "dev": True, "prod": False}, "beta": {"label": "Beta", "dev": False, "prod": True}}


def reset_cache():
    server._flag_overrides_state.update(at=0.0, map={}, ok=False)


class MergeTests(unittest.TestCase):
    def setUp(self):
        reset_cache()
        self.rows, self.calls = [], []
        def fake_rows(sql, params=()):
            self.calls.append(sql)
            if isinstance(self.rows, Exception):
                raise self.rows
            return self.rows
        for p in (patch.object(server, "APP_ENV", "dev"), patch.object(server, "DATABASE_URL", "postgres://dev"),
                  patch.object(server, "pg_rows", fake_rows),
                  patch.object(server, "_read_flags_file", lambda: json.loads(json.dumps(FILE_FLAGS)))):
            p.start()
            self.addCleanup(p.stop)

    def test_a_live_override_wins_over_the_committed_dev_value(self):
        self.rows = [{"key": "alpha", "value": False}]
        flags = server.load_flags()
        self.assertFalse(flags["alpha"]["dev"])                                     # committed True, switched off live
        self.assertEqual((flags["alpha"]["prod"], flags["beta"]["dev"], flags["beta"]["prod"]), (False, False, True))
        self.assertFalse(server._flag_on("alpha"))                                  # what the dev site actually obeys

    def test_overrides_for_unknown_flags_are_ignored(self):
        self.rows = [{"key": "ghost", "value": True}]
        self.assertNotIn("ghost", server.load_flags())

    def test_production_never_reads_overrides(self):
        self.rows = [{"key": "beta", "value": True}]
        with patch.object(server, "APP_ENV", "prod"):
            self.assertEqual(server.load_flags()["beta"]["prod"], True)
            self.assertFalse(server.load_flags()["beta"]["dev"])                    # committed value; override not consulted
        self.assertEqual(self.calls, [])

    def test_no_database_means_no_overrides(self):
        with patch.object(server, "DATABASE_URL", ""):
            self.assertTrue(server.load_flags()["alpha"]["dev"])
        self.assertEqual(self.calls, [])

    def test_the_database_is_asked_at_most_once_per_ttl(self):
        self.rows = [{"key": "alpha", "value": False}]
        for _ in range(5):
            server.load_flags()
        self.assertEqual(len(self.calls), 1)

    def test_a_database_failure_keeps_the_last_known_switches_and_reports_not_live(self):
        self.rows = [{"key": "alpha", "value": False}]
        self.assertFalse(server.load_flags()["alpha"]["dev"])
        self.assertTrue(server._live_dev_available())
        server._flag_overrides_state["at"] = 0.0                                    # TTL elapsed
        self.rows = RuntimeError("db down")
        self.assertFalse(server.load_flags()["alpha"]["dev"])                       # still the last known value
        self.assertFalse(server._live_dev_available())

    def test_a_missing_table_just_means_the_committed_value_stands(self):
        self.rows = RuntimeError('relation "feature_flag_overrides" does not exist')
        self.assertTrue(server.load_flags()["alpha"]["dev"])


class WriteTests(unittest.TestCase):
    def setUp(self):
        reset_cache()

    def fake_connect(self, record, fail=False):
        class Cur:
            def __enter__(s): return s
            def __exit__(s, *a): return False
            def execute(s, sql, params): record.append((sql, params))
        class Conn:
            def cursor(s): return Cur()
            def commit(s): record.append(("commit", None))
            def close(s): record.append(("close", None))
        def connect(url):
            if fail:
                raise RuntimeError("no database")
            return Conn()
        return connect

    def test_set_writes_an_upsert_and_refreshes_the_cache(self):
        rec = []
        server._flag_overrides_state["at"] = 123.0
        with patch.object(server, "APP_ENV", "dev"), patch.object(server, "DATABASE_URL", "postgres://dev"), \
             patch("psycopg2.connect", self.fake_connect(rec)):
            self.assertTrue(server._set_flag_override("alpha", False))
        sql, params = rec[0]
        self.assertIn("INSERT INTO feature_flag_overrides", sql)
        self.assertIn("'dev'", sql)                                                  # the environment is fixed in the statement
        self.assertEqual(params, ("alpha", False))
        self.assertIn(("commit", None), rec)
        self.assertEqual(server._flag_overrides_state["at"], 0.0)

    def test_failures_and_non_dev_servers_never_raise_and_report_false(self):
        with patch.object(server, "APP_ENV", "dev"), patch.object(server, "DATABASE_URL", "postgres://dev"), \
             patch("psycopg2.connect", self.fake_connect([], fail=True)):
            self.assertFalse(server._set_flag_override("alpha", True))
        with patch.object(server, "APP_ENV", "prod"), patch.object(server, "DATABASE_URL", "postgres://x"):
            self.assertFalse(server._set_flag_override("alpha", True))               # production can never write overrides
        with patch.object(server, "APP_ENV", "dev"), patch.object(server, "DATABASE_URL", ""):
            self.assertFalse(server._set_flag_override("alpha", True))


class ReleaseCenterEndpointTests(unittest.TestCase):
    """POST /api/flags/set exactly as the Release Center page calls it (local cockpit: RELEASE_CENTER=1 + loopback)."""

    def setUp(self):
        reset_cache()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "features.json")
        Path(self.path).write_text(json.dumps({"_schema": {"version": 2}, "flags": json.loads(json.dumps(FILE_FLAGS))}, indent=2))
        self.live = []
        def fake_set(key, value):
            self.live.append((key, value))
            self.overrides[key] = value
            return True
        self.overrides = {}
        for p in (patch.object(server, "_resolve_repo_file", lambda name: self.path),
                  patch.object(server, "_set_flag_override", fake_set),
                  patch.object(server, "_flag_overrides", lambda: dict(self.overrides)),
                  patch.object(server, "_live_dev_available", lambda: True),
                  patch.dict(os.environ, {"RELEASE_CENTER": "1"})):
            p.start()
            self.addCleanup(p.stop)
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.addCleanup(self.httpd.server_close)
        self.addCleanup(self.httpd.shutdown)

    def call(self, method, path, body=None):
        c = http.client.HTTPConnection("127.0.0.1", self.httpd.server_address[1], timeout=10)
        try:
            c.request(method, path, body=json.dumps(body) if body is not None else None, headers={"Content-Type": "application/json"})
            r = c.getresponse()
            raw = r.read().decode() or "{}"
            try:
                return r.status, json.loads(raw)
            except ValueError:                                                       # e.g. a plain 404 page
                return r.status, {}
        finally:
            c.close()

    def file_flags(self):
        return json.loads(Path(self.path).read_text())["flags"]

    def test_a_dev_toggle_is_saved_and_made_live_on_the_dev_site(self):
        status, body = self.call("POST", "/api/flags/set", {"key": "alpha", "env": "dev", "value": False})
        self.assertEqual((status, body["ok"], body["live"]), (200, True, True))
        self.assertEqual(self.live, [("alpha", False)])
        self.assertFalse(body["flags"]["alpha"]["dev"])                              # the page redraws from this
        self.assertFalse(self.file_flags()["alpha"]["dev"])                          # and features.json is saved too (deploys stay consistent)

    def test_a_prod_toggle_is_saved_only_and_never_live(self):
        status, body = self.call("POST", "/api/flags/set", {"key": "beta", "env": "prod", "value": False})
        self.assertEqual((status, body["live"]), (200, False))
        self.assertEqual(self.live, [])                                              # production changes only through promote
        self.assertFalse(self.file_flags()["beta"]["prod"])

    def test_a_toggle_never_writes_other_live_overrides_into_the_file(self):
        self.overrides = {"alpha": False}                                            # alpha was switched off live earlier…
        self.call("POST", "/api/flags/set", {"key": "beta", "env": "dev", "value": True})
        flags = self.file_flags()
        self.assertTrue(flags["alpha"]["dev"])                                       # …but the file keeps its committed value
        self.assertTrue(flags["beta"]["dev"])

    def test_bad_requests_change_nothing(self):
        self.assertEqual(self.call("POST", "/api/flags/set", {"key": "ghost", "env": "dev", "value": True})[0], 400)
        self.assertEqual(self.call("POST", "/api/flags/set", {"key": "alpha", "env": "stage", "value": True})[0], 400)
        self.assertEqual(self.call("POST", "/api/flags/set", {"key": "alpha", "env": "dev", "value": "yes"})[0], 400)
        self.assertEqual(self.live, [])
        self.assertEqual(self.file_flags(), FILE_FLAGS)

    def test_the_dashboard_feed_says_whether_dev_switches_are_live(self):
        status, body = self.call("GET", "/api/flags/all")
        self.assertEqual((status, body["live_dev"], body["admin"]), (200, True, True))

    def test_without_the_cockpit_switch_the_route_does_not_exist(self):
        with patch.dict(os.environ, {"RELEASE_CENTER": "0"}):
            self.assertEqual(self.call("POST", "/api/flags/set", {"key": "alpha", "env": "dev", "value": False})[0], 404)


class ReleaseCenterPageTests(unittest.TestCase):
    def test_the_page_says_live_and_explains_it(self):
        html = (Path(__file__).resolve().parents[1] / "app" / "release-center.html").read_text(encoding="utf-8")
        self.assertIn("liveDev", html)
        self.assertIn("live on the dev site now", html)
        self.assertIn("'live':'saved'", html)

    def test_the_migration_cannot_hold_a_production_override(self):
        sql = (Path(__file__).resolve().parents[1] / "db" / "migrations" / "0036_feature_flag_overrides.sql").read_text(encoding="utf-8")
        self.assertIn("CHECK (env = 'dev')", sql)


if __name__ == "__main__":
    unittest.main()
