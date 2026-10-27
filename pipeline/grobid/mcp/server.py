# Last updated: 2026-10-20 · Codex / Full-Stack · GROBID MCP server for the Docker gateway.
from mcp.server.fastmcp import FastMCP
import core

mcp = FastMCP('grobid', instructions=(
    'Local scientific PDF parsing through GROBID. First list the available PDFs, then pass a '
    'relative path to grobid_parse_pdf. Inputs are read-only. Output files remain local. '
    'Parsing does not import anything into LightRAG or Neon and is not scientific validation.'))


@mcp.tool()
def grobid_status() -> dict:
    """Check the local GROBID API health and parser version."""
    return core.status()


@mcp.tool()
def grobid_list_pdfs() -> dict:
    """List PDFs in the read-only LightRAG inputs folder; paths are relative to that folder."""
    return core.list_pdfs()


@mcp.tool()
def grobid_parse_pdf(relative_path: str) -> dict:
    """Parse one listed PDF into local TEI XML and scientific body text without bibliography.

    Returns local output paths and metadata, not full article text. No graph/database writes.
    """
    return core.parse_pdf(relative_path)


if __name__ == '__main__':
    mcp.run(transport='stdio')
