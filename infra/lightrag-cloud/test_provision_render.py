# Last updated: 2026-11-21 21:34 UTC · Claude (Sonnet 5.5) · provisioner tests
import json, unittest
import provision_render as pr

CFG = {"LIGHTRAG_API_KEY": "k" * 48, "LLM_BINDING_API_KEY": "sk-ant-x", "SEED_ARCHIVE_URL": "https://s3/x?sig=1", "SEED_ARCHIVE_SHA256": "ab" * 32}

class T(unittest.TestCase):
    def test_ollama_first_private_and_disks(self):
        o, l = pr.payloads("r", "b", "own", CFG, False)
        self.assertEqual((o["type"], l["type"]), ("private_service", "web_service"))
        self.assertEqual(o["serviceDetails"]["disk"]["mountPath"], "/data")
        self.assertEqual(l["serviceDetails"]["disk"]["mountPath"], "/app/data")
        self.assertEqual(o["serviceDetails"]["plan"], "standard"); self.assertEqual(l["serviceDetails"]["plan"], "standard")
        self.assertEqual(l["autoDeploy"], "no")
    def test_env_from_blueprint_includes_graph_cap_and_embedding_host(self):
        _, l = pr.payloads("r", "b", "own", CFG, False)
        d = {e["key"]: e["value"] for e in l["envVars"]}
        self.assertEqual(d["MAX_GRAPH_NODES"], "20000"); self.assertEqual(d["EMBEDDING_DIM"], "1024")
        self.assertEqual(d["EMBEDDING_BINDING_HOST"], "http://meatcode-lightrag-ollama:11434")
        self.assertEqual(d["KEYWORD_LLM_MODEL"], "claude-sonnet-4-6")
    def test_refuses_silent_empty_graph(self):
        with self.assertRaises(SystemExit): pr.payloads("r", "b", "own", {**CFG, "SEED_ARCHIVE_URL": ""}, False)
        pr.payloads("r", "b", "own", {**CFG, "SEED_ARCHIVE_URL": ""}, True)
    def test_short_key_rejected(self):
        with self.assertRaises(SystemExit): pr.payloads("r", "b", "own", {**CFG, "LIGHTRAG_API_KEY": "short"}, False)
    def test_mask_hides_secrets(self):
        _, l = pr.payloads("r", "b", "own", CFG, False)
        s = json.dumps(pr.mask(l)); self.assertNotIn("sk-ant-x", s); self.assertNotIn("k" * 48, s); self.assertNotIn("sig=1", s)

if __name__ == "__main__": unittest.main()
