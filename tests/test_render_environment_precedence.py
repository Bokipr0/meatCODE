# Last updated: 2026-10-28 UTC · Full-Stack · isolate dotenv loading without bootstrapping server or model clients.
import ast
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class RenderEnvironmentTests(unittest.TestCase):
    def load(self, source, environ, root_key="root-key", server_key="server-key", dev_key="dev-key"):
        tree = ast.parse(source)
        start = next(i for i, n in enumerate(tree.body) if isinstance(n, ast.FunctionDef) and n.name == "load_dotenv")
        end = next(i for i, n in enumerate(tree.body) if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == "_resolve_cache" for t in n.targets))
        loader = ast.Module(body=tree.body[start:end], type_ignores=[])
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "server").mkdir()
            for file, key, db in ((root / ".env", root_key, "root-db"),
                                  (root / "server/.env", server_key, "server-db"),
                                  (root / ".env.dev", dev_key, "dev-db")):
                file.write_text("ANTHROPIC_API_KEY=" + key + "\nDATABASE_URL=" + db + "\n")
            ns = {"os": os, "REPO_ROOT": str(root), "HERE": str(root / "server")}
            with patch.dict(os.environ, environ, clear=True):
                exec(compile(loader, "<isolated-dotenv>", "exec"), ns)
                result = dict(os.environ)
            return result, ns

    def test_render_env_wins_over_every_dotenv_in_prod_and_dev(self):
        source = Path("server/meatcode_server.py").read_text()
        for environment in ("prod", "dev"):
            result, ns = self.load(source, {"RENDER": "true", "APP_ENV": environment,
                                          "ANTHROPIC_API_KEY": "dashboard-key", "DATABASE_URL": "dashboard-db"})
            self.assertEqual(result["ANTHROPIC_API_KEY"], "dashboard-key")
            self.assertEqual(result["DATABASE_URL"], "dashboard-db")
            self.assertTrue(ns["IS_RENDER"])
            self.assertEqual(ns["APP_ENV"], environment)

    def test_render_missing_key_is_not_filled_from_stale_secret_file(self):
        result, _ = self.load(Path("server/meatcode_server.py").read_text(), {"RENDER": "true"})
        self.assertNotIn("ANTHROPIC_API_KEY", result)
        self.assertNotIn("DATABASE_URL", result)

    def test_local_prod_preserves_root_then_server_fallback(self):
        result, ns = self.load(Path("server/meatcode_server.py").read_text(), {"ANTHROPIC_API_KEY": "stale-shell"})
        self.assertEqual(result["ANTHROPIC_API_KEY"], "server-key")
        self.assertEqual(result["DATABASE_URL"], "server-db")
        self.assertEqual(ns["APP_ENV"], "prod")
        self.assertFalse(ns["IS_RENDER"])

    def test_local_dev_overlay_preserved_and_blank_key_does_not_erase(self):
        source = Path("server/meatcode_server.py").read_text()
        result, _ = self.load(source, {"APP_ENV": "dev"})
        self.assertEqual(result["ANTHROPIC_API_KEY"], "dev-key")
        self.assertEqual(result["DATABASE_URL"], "dev-db")
        result, _ = self.load(source, {"APP_ENV": "dev"}, dev_key="")
        self.assertEqual(result["ANTHROPIC_API_KEY"], "server-key")
        self.assertEqual(result["DATABASE_URL"], "dev-db")

    def test_api_key_outer_whitespace_trim_without_importing_client(self):
        tree = ast.parse(Path("server/meatcode_server.py").read_text())
        assignment = next(n for n in tree.body if isinstance(n, ast.Assign)
                          and any(isinstance(t, ast.Name) and t.id == "API_KEY" for t in n.targets))
        module = ast.Module(body=[assignment], type_ignores=[])
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "  dummy-key \n"}, clear=True):
            ns = {"os": os}
            exec(compile(module, "<isolated-key-normalization>", "exec"), ns)
            self.assertEqual(ns["API_KEY"], "dummy-key")


if __name__ == "__main__":
    unittest.main()
