#!/bin/zsh
cd "$(dirname "$0")/.." || exit 1
MCP_PYTHON="${MEATCODE_MCP_PYTHON:-/private/tmp/meatcode-mcp-venv/bin/python}"
if [[ ! -x "$MCP_PYTHON" ]]; then
  print 'The MCP pilot environment is missing. See platform_docs/MCP_PRIVATE_PILOT.md for setup.'
  read '?Press Enter to close.'
  exit 1
fi
"$MCP_PYTHON" -m scripts.mcp.start_tunnel
read '?Press Enter to close.'
