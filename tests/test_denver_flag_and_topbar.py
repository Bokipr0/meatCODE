# Last updated: 2026-11-22 UTC · Claude (Fable 5.2) · Denver can be switched off from the Release Center; no Backups/Dashboard buttons on dev
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "app" / "meatcode_mockup.html").read_text(encoding="utf-8")
FLAGS = json.loads((ROOT / "Release Center" / "features.json").read_text(encoding="utf-8"))["flags"]


class DenverFlagTests(unittest.TestCase):
    def test_denver_is_a_registered_switch_that_is_on_everywhere_by_default(self):
        self.assertEqual((FLAGS["denver"]["dev"], FLAGS["denver"]["prod"]), (True, True))   # adding the switch changes nothing
        self.assertEqual(FLAGS["denver"]["kind"], "feature")

    def test_only_an_explicit_off_hides_denver_and_his_note_tab(self):
        self.assertIn("if (flags && flags.denver === false) document.body.classList.add('mc-denver-off');", PAGE)
        self.assertRegex(PAGE, r"body\.mc-denver-off #mcDenver,body\.mc-denver-off #oracleDenverPeek\{display:none!important;\}")
        self.assertNotRegex(PAGE, r"body:not\(\.ff-denver\)")                 # a registry without the entry keeps him visible


class TopbarButtonTests(unittest.TestCase):
    def test_backups_button_is_off_on_dev_and_prod(self):
        self.assertEqual((FLAGS["backup_center"]["dev"], FLAGS["backup_center"]["prod"]), (False, False))
        self.assertIn("body.ff-backup_center .mc-backup-wrap { display: inline-flex; }", PAGE)     # still flag-gated

    def test_dashboard_button_is_hidden_on_dev_only_and_the_dashboard_keeps_its_flag(self):
        self.assertIn("body.mc-development-site .mc-dashboard-btn{display:none!important;}", PAGE)
        self.assertIn("body:not(.ff-live_testing_dashboard) .mc-dashboard-btn{display:none!important;}", PAGE)   # other environments unchanged
        badge = (ROOT / "app" / "assets" / "environment-badge.js").read_text(encoding="utf-8")
        self.assertIn("document.body.classList.add('mc-development-site')", badge)       # set only when /api/version says dev
        self.assertTrue(FLAGS["live_testing_dashboard"]["dev"])               # /research-dashboard still served on dev
        standalone = (ROOT / "app" / "modules" / "graph-oracle.html").read_text(encoding="utf-8")
        self.assertNotIn("mc-dashboard-btn", standalone)
        self.assertIn("mc-devarea-btn", standalone)


if __name__ == "__main__":
    unittest.main()
