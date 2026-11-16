#!/bin/sh
# Last updated: 2026-11-16 · Codex · Separate hosted MCP build, without website changes.
set -eu
python -m pip install -r server/mcp_pilot/requirements-hosted.txt
cd server/mcp_pilot/web
npm ci --ignore-scripts
npm run build
