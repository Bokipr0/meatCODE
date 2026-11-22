# Last updated: 2026-11-22 UTC · Claude (Sonnet 5.5) · Dev Area: big version/last-update title, newest-first lists, trimmed text
import datetime
import http.client
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))
with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "local-fixture-not-a-key", "DATABASE_URL": "", "APP_ENV": "dev"}):
    import meatcode_server as server

PAGE = (ROOT / "app" / "dev" / "index.html").read_text(encoding="utf-8")


class BuildTimeTests(unittest.TestCase):
    def make(self, tmp, rel, when):
        p = Path(tmp, rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x")
        os.utime(p, (when, when))

    def test_newest_source_file_wins_and_noise_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make(tmp, "server/a.py", 1_700_000_000)
            self.make(tmp, "app/b.html", 1_700_500_000)                   # the newest real file
            self.make(tmp, "README.md", 1_700_100_000)
            self.make(tmp, "data/huge.json", 1_800_000_000)               # excluded directory
            self.make(tmp, ".git/objects/x.json", 1_800_000_000)          # excluded directory
            self.make(tmp, "app/photo.png", 1_800_000_000)                # not a source/doc extension
            self.make(tmp, "node_modules/p/i.js", 1_800_000_000)          # excluded directory
            got = server._newest_file_time(tmp)
        self.assertEqual(datetime.datetime.fromisoformat(got).timestamp(), 1_700_500_000)
        self.assertTrue(got.endswith("+00:00"))                           # UTC, parseable by Date()

    def test_an_empty_or_missing_tree_gives_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(server._newest_file_time(tmp))
        self.assertIsNone(server._newest_file_time("/definitely/not/here"))

    def test_version_endpoint_reports_it(self):
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        self.addCleanup(httpd.server_close)
        self.addCleanup(httpd.shutdown)
        c = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=10)
        c.request("GET", "/api/version")
        body = json.loads(c.getresponse().read())
        c.close()
        self.assertEqual(body["build_time"], server.BUILD_TIME)
        self.assertIn("commit", body)
        if body["build_time"]:
            self.assertLessEqual(datetime.datetime.fromisoformat(body["build_time"]).timestamp(), datetime.datetime.now().timestamp() + 5)


@unittest.skipUnless(shutil.which("node"), "node is needed to run the page's sort function")
class SortTests(unittest.TestCase):
    """Runs the page's own newestFirst() in node, so what is tested is what ships."""

    def order(self, flags, keys=None):
        start = PAGE.index("  function dateKey(s)")
        end = PAGE.index("  function render()")
        code = PAGE[start:end] + "\nconst flags=%s; console.log(JSON.stringify(newestFirst(%s, flags)));" % (
            json.dumps(flags), json.dumps(keys if keys is not None else list(flags)))
        out = subprocess.run(["node", "-e", code], capture_output=True, text=True, timeout=20)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)

    def test_newest_added_first(self):
        flags = {"old": {"added": "2026-07-23"}, "mid": {"added": "2026-10-29"}, "new": {"added": "2026-11-22"}}
        self.assertEqual(self.order(flags), ["new", "mid", "old"])

    def test_same_day_goes_by_updated_then_by_later_registered_first(self):
        flags = {"a": {"added": "2026-11-01"}, "b": {"added": "2026-11-01", "updated": "2026-11-20"},
                 "c": {"added": "2026-11-01"}, "d": {"added": "2026-11-01", "updated": "2026-11-05"}}
        self.assertEqual(self.order(flags), ["b", "d", "c", "a"])         # updated desc, then later-registered (c) before a

    def test_unknown_dates_sink_to_the_bottom_without_breaking_the_sort(self):
        flags = {"none": {}, "bad": {"added": "date unknown"}, "ok": {"added": "2026-01-01"}, "also": {"added": "2026-02-01"}}
        got = self.order(flags)
        self.assertEqual(got[:2], ["also", "ok"])
        self.assertEqual(sorted(got[2:]), ["bad", "none"])

    def test_it_sorts_a_given_subset_only(self):
        flags = {"x": {"added": "2026-01-01"}, "y": {"added": "2026-03-01"}, "z": {"added": "2026-02-01"}}
        self.assertEqual(self.order(flags, ["x", "z"]), ["z", "x"])


class PageTests(unittest.TestCase):
    def test_big_title_slots_and_data_source(self):
        for needle in ('class="ver-kicker"', 'id="verTitle"', 'id="verUpdate"', "Current version", "Last update", "fetch('/api/version'", "build_time"):
            self.assertIn(needle, PAGE)
        self.assertRegex(PAGE, r"\.hero h1\.ver-title \{[^}]*font-weight: 800")        # big and bold
        self.assertRegex(PAGE, r"\.hero \.ver-update \{[^}]*font-weight: 800")

    def test_both_lists_use_the_newest_first_sort(self):
        self.assertIn("newestFirst(keys.filter(function (k) { return (flags[k] || {}).kind !== 'screen'; }), flags)", PAGE)
        self.assertIn("newestFirst(keys.filter(function (k) { return (flags[k] || {}).kind === 'screen'; }), flags)", PAGE)

    def test_explanatory_text_is_gone(self):
        for removed in ("Lior&rsquo;s internal workbench", "Feature flags, work-in-progress screens", 'class="hint"', "How this works",
                        "A screen registered here gets the same", "Feature flags, deploy-dev / promote", "How dev and prod are kept separate",
                        "Open deliverables for the 31 Aug demo", "Living technical status", "Every promoted snapshot, newest-first",
                        "Production data only", "Saves to features.json"):
            self.assertNotIn(removed, PAGE)
        self.assertEqual(len(re.findall(r'<section class="section"', PAGE)), 6)       # the sections themselves are all still there

    def test_row_location_and_notes_are_collapsed_not_deleted(self):
        self.assertIn("<details class=\"more\"><summary>Details</summary>", PAGE)
        self.assertIn("flag-note", PAGE)
        self.assertIn("toggleHTML(key, 'dev'", PAGE)                                # the switches are untouched


if __name__ == "__main__":
    unittest.main()
