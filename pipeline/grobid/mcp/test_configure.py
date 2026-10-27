# Last updated: 2026-10-20 · Codex / Data + Full-Stack · preserve MCP settings and narrow bind scopes.
from pathlib import Path
import tomllib
import unittest

from configure import update_config


class ConfigureTests(unittest.TestCase):
    def test_preserves_other_settings_and_is_idempotent(self):
        original = '''model = "keep-model"
[mcp_servers.other]
command = "keep-command"
[mcp_servers.MCP_DOCKER]
command = "docker"
args = ["mcp", "gateway", "run", "--profile", "meatcode"]
[mcp_servers.MCP_DOCKER.env]
KEEP = "keep-value"
MCP_GATEWAY_DOCKER_BIND_ALLOWED_PATHS = "/existing"
'''
        updated = update_config(original, Path('/exact/output'))
        result = tomllib.loads(updated)
        self.assertEqual(result['model'], 'keep-model')
        self.assertEqual(result['mcp_servers']['other'], {'command': 'keep-command'})
        env = result['mcp_servers']['MCP_DOCKER']['env']
        self.assertEqual(env['KEEP'], 'keep-value')
        self.assertEqual(env['MCP_GATEWAY_DOCKER_BIND_ALLOWED_PATHS'], '/existing:/Users/lior/LightRAG/inputs')
        self.assertEqual(env['MCP_GATEWAY_DOCKER_BIND_ALLOW_WRITABLE_PATHS'], '/exact/output')
        self.assertEqual(update_config(updated, Path('/exact/output')), updated)

    def test_rejects_unexpected_gateway(self):
        with self.assertRaises(ValueError):
            update_config('[mcp_servers.MCP_DOCKER]\nargs = ["other"]', Path('/output'))


if __name__ == '__main__':
    unittest.main()
