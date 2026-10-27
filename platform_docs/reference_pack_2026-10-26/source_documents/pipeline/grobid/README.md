# Local GROBID through Docker

_Last updated: 2026-10-20 · Codex / Data + Full-Stack · Docker API and MCP adapter setup._

GROBID is available at **http://localhost:8070**. The container is named `meatcode-grobid`.
It parses PDFs into TEI XML. It is a separate ingestion service, not an LLM or vector database.

This setup reuses the already downloaded `grobid/grobid:0.8.2` image, pinned by digest. It runs
the amd64 image through Docker's emulation on this Apple Silicon Mac, with a 4 GiB memory limit,
two CPUs and a Docker health check. The HTTP port binds only to the local machine. No PDFs or
credentials are mounted into the container by default; a parsing request uploads its selected PDF
to this local service. Neither Neon nor LightRAG is modified by starting GROBID.

Start using `Release Center/start-grobid.command`, or run from the repository:

```sh
docker compose -f pipeline/grobid/compose.yaml up -d --wait --wait-timeout 240
curl --fail http://localhost:8070/api/isalive
docker compose -f pipeline/grobid/compose.yaml logs --tail 30
docker compose -f pipeline/grobid/compose.yaml stop
```

To parse one local PDF and retain TEI locally:

```sh
mkdir -p data/grobid
curl --fail --max-time 180 \
  -F 'input=@/absolute/path/paper.pdf' \
  -F consolidateHeader=0 -F consolidateCitations=0 \
  http://localhost:8070/api/processFulltextDocument \
  -o data/grobid/paper.tei.xml
```

Consolidation is disabled in this example, so external bibliographic consolidation is not
requested. Inspect parsing quality before extraction. Feed cleaned scientific sections into
LightRAG rather than blindly ingesting the entire TEI XML including its bibliography.

The Docker MCP `meatcode` profile now also contains a local GROBID adapter. It exposes health,
PDF listing and PDF parsing tools through the existing Codex `MCP_DOCKER` connection.
See [MCP setup and tools](mcp/README.md). Reload the MCP connection or restart Codex after setup.

Primary documentation:
[GROBID Docker](https://grobid.readthedocs.io/en/latest/Grobid-docker/),
[GROBID API](https://grobid.readthedocs.io/en/latest/Grobid-service/),
[Docker MCP Toolkit](https://docs.docker.com/ai/mcp-catalog-and-toolkit/get-started/).

## Verification

Verified 2026-10-20 21:03 UTC: health API returned `true`, version API returned `0.8.2` / revision
`a91ee48`, and one existing local PDF returned HTTP 200 with well-formed TEI XML
(26 body paragraphs, 62 bibliography entries, 96,780 bytes) in 27.64 seconds.
Smoke output and machine-readable check: ignored `data/grobid/`. This checks service operation,
not scientific extraction accuracy. Container remained healthy with no OOM kill/restart.
