# GROBID through Docker MCP

_Last updated: 2026-10-20 · Codex / Data + Full-Stack · local MCP adapter._

The existing Codex `MCP_DOCKER` connection runs Docker MCP Gateway with profile `meatcode`.
That profile now includes the local `meatcode/grobid-mcp:0.1.0` adapter alongside Playwright.
The adapter calls the separate GROBID service at `host.docker.internal:8070`.

Tools:

- `grobid_status`: check the parser's health and version.
- `grobid_list_pdfs`: list up to 200 PDFs under `/Users/lior/LightRAG/inputs`.
- `grobid_parse_pdf`: accept a listed relative path and save TEI XML, scientific body text
  and a JSON manifest locally. For example: `__parsed__/kosowska 2017.pdf`.

Files returned under container `/outputs` are saved on the Mac in
`data/grobid/mcp/` under this repository. Input PDFs are mounted read-only. The exact output
directory is the only newly allowed writable bind. API keys, Docker socket and database
credentials are not mounted into this adapter. Parsing makes no Neon or LightRAG writes.
External bibliographic consolidation is disabled. Cleaned body text excludes the TEI header
and bibliography; scientific extraction quality still needs review before ingestion.

## Start and verify

Start Docker Desktop, then run `Release Center/start-grobid.command`.
Reload Codex's MCP connection or restart Codex after initial setup to load the new tools.

From the repository, the reproducible setup is:

```sh
docker build -t meatcode/grobid-mcp:0.1.0 pipeline/grobid/mcp
python3 pipeline/grobid/mcp/configure.py --apply
docker mcp profile server add meatcode --server file:///Users/lior/.docker/mcp/catalogs/meatcode/grobid-server.yaml
python3 pipeline/grobid/mcp/probe_gateway.py --parse '__parsed__/kosowska 2017.pdf'
```

Python 3.11+ is required for the host configuration script. The adapter image uses Python 3.12
and official MCP Python SDK 1.26.0. The configuration script preserves unrelated TOML settings,
backs up changed Codex configuration, sets a 90-second minimum startup timeout, and adds exact
input/output bind allowlists. These local paths are specific to Lior's Mac.

The verification script launches its own gateway client, calls the actual MCP tools and saves
`data/grobid/mcp-gateway-verification.json`. It terminates only that test gateway on completion;
GROBID remains running. Unit checks: `python3 -m unittest discover -s pipeline/grobid/mcp`.
