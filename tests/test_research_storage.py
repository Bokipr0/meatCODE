from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from research_storage import database_url
class StorageTests(unittest.TestCase):
 def test_isolated_target_wins(self):self.assertEqual(database_url({'RESEARCH_DATABASE_URL':'research','DATABASE_URL':'science'},'science'),'research')
 def test_required_missing_never_falls_back(self):self.assertIsNone(database_url({'RESEARCH_DATABASE_REQUIRED':'true','DATABASE_URL':'science'},'science'))
 def test_legacy_only_before_cutover(self):self.assertEqual(database_url({},'science'),'science')
