# MeatCODE private ChatGPT MCP pilot

_Last updated: 2026-11-16 12:17 UTC · Codex · Private ChatGPT connection and first live retrieval verified._

Local tools, transport, tunnel readiness, private plugin connection and the first ChatGPT-driven retrieval are verified. Scientific answer-quality improvement remains unmeasured.

## Placement

ChatGPT → OpenAI Secure MCP Tunnel → local MCP adapter → bounded scientific reads in Neon.

The adapter is a separate service. The existing Render website, Claude answer generation, user analytics and research-log cache are not involved in pilot requests. This follows Neco's MCP/data-layer option while retaining the branded Oracle. A later hosted adapter can expose the same tools over HTTPS with OAuth; public directory submission is a separate release/review process.

## Tools

- `search(query)`: searches the 840-paper production corpus using Postgres FTS, with an OR fallback. Returns at most five source IDs, titles, review states and publisher URLs. No minimum relevance-score threshold.
- `fetch(id)`: returns the source's stored structured summary and main claim, if present; no raw article abstract/full text, private source notes, PDF download or unrestricted URL fetching.
- `search_knowledge_graph(query, limit=5)`: uses the development database's LightRAG demo, with lexical seeds and bounded one-hop expansion. Returns extracted descriptions and source references; not scientific validation.

All three tools advertise read-only, non-destructive behavior. Tools cannot execute arbitrary SQL, select a table, access user chats/feedback, or change data. Every database session is read-only, with a five-second statement timeout and rollback on close. Credentials are loaded locally and never returned by tools. This is a bounded pilot allowlist; a hosted release should use dedicated least-privilege scientific roles and its own per-user authorization.

Corpus and graph are different data scopes: production has 840 sources; the imported graph is in development and covers three papers, 3,418 entities, 4,164 relationships and 7,582 copied embeddings. Its review state is `extracted_demo`. Lexical rank is not confidence. The pilot intentionally does not use those vectors or connect to the whole mutable local LightRAG workspace. A later graph adapter can call the LightRAG service or a governed graph projection; MCP does not require data to live in Neon.

The pilot literature retrieval is an explicit, ungated FTS implementation. It does not claim identical ranking or policy to the current Oracle endpoint. Before production, consolidate a shared retrieval service and permissions policy so Oracle and MCP use the same evidence rules.

## Local setup

Use Python 3.11+ in an isolated environment:

```sh
python3 -m venv --system-site-packages /private/tmp/meatcode-mcp-venv
/private/tmp/meatcode-mcp-venv/bin/pip install -r server/mcp_pilot/requirements.txt
```

The SDK version tested is 1.30.0. Run from the repository root. Stdio command:

```sh
/private/tmp/meatcode-mcp-venv/bin/python -m server.mcp_pilot.main \
  --corpus-env '/absolute/path/to/meatCODE/.env' \
  --graph-env '/absolute/path/to/meatCODE/.env.dev'
```

Optional HTTP transport: add `--transport streamable-http`; endpoint is `http://127.0.0.1:8791/mcp`. The listener is loopback-only and is not a public authenticated service. Do not rebind it to a public interface without adding authentication and authorization.

## Private ChatGPT connection

OpenAI's official setup documentation:
- https://developers.openai.com/api/docs/guides/secure-mcp-tunnels
- https://developers.openai.com/plugins/deploy/connect-chatgpt
- https://developers.openai.com/plugins/build/auth

A tunnel named **MeatCODE private pilot** was observed in the personal Platform organization, associated with the listed personal ChatGPT workspace. Its creation was explicitly approved. No public endpoint is opened. Local non-secret settings live in ignored `data/mcp-pilot/settings.json` with:

```json
{
  "tunnel_id": "your-created-tunnel-id",
  "tunnel_client": "/absolute/path/to/official/tunnel-client",
  "corpus_env": "/absolute/path/to/meatCODE/.env",
  "graph_env": "/absolute/path/to/meatCODE/.env.dev"
}
```

Download the official tunnel-client through Platform tunnel settings or https://github.com/openai/tunnel-client/releases/latest. Today's downloaded binary is v0.0.21 under `/private/tmp/meatcode-mcp-tools`; temporary runtime directories can be removed by the operating system, so reinstall or relocate them for ongoing use.

Double-click `Release Center/start-mcp-pilot.command`. It invokes `scripts/mcp/start_tunnel.py`, which:
1. Creates a non-secret tunnel profile referring to the API key by environment variable.
2. Asks for an OpenAI runtime API key in a hidden terminal prompt, unless `CONTROL_PLANE_API_KEY` is already set.
3. Runs `tunnel-client doctor --explain` and starts the foreground client only if validation succeeds.
4. Keeps the key in process memory/environment; it is not written to the profile or passed as a command argument.

The runtime key's principal needs **Tunnels Read + Use** in the tunnel's Platform organization. An admin key is not the runtime key. Keep the terminal open during the pilot. Stop with Ctrl+C. Health is exposed only on loopback at `http://127.0.0.1:8792/readyz` and `/ui`. For a durable deployment, use supported service supervision and secure secret storage, rather than assuming the local foreground process is always on.

In signed-in ChatGPT Plugins, select Add custom MCP server → Connection: Tunnel → the MeatCODE tunnel. For this account-scoped scientific pilot the local target has no additional OAuth login; access is controlled by the tunnel's organization/workspace associations. Review the three discovered tools before connecting. Do not choose a no-auth PUBLIC endpoint; that is a different security model. Treat setup as complete only when an actual ChatGPT tool call succeeds.

## Benchmark and next experiment

Run the reproducible transport/retrieval benchmark:

```sh
/private/tmp/meatcode-mcp-venv/bin/python -m scripts.mcp.benchmark \
  --corpus-env '/absolute/path/to/meatCODE/.env' \
  --graph-env '/absolute/path/to/meatCODE/.env.dev' \
  --repeats 2 --output /private/tmp/meatcode-mcp-benchmark.json
```

See `platform_docs/mcp_pilot/BENCHMARK_2026-11-16.md`. This checks tool discovery, actual protocol calls, evidence preservation, invalid input and tool boundaries. It does not grade scientific answers.

For a controlled answer benchmark, run the same held-out questions with the same ChatGPT model/settings in two fresh conversations: (A) without MeatCODE, (B) with MeatCODE. Disable other search tools for that comparison. Ask for citations, record tool selections and evidence, and have a scientist grade correctness, citation support, useful uncertainty and relevance without knowing the condition. Keep a separate comparison to the Sonnet Oracle: it changes both the model and retrieval, so it cannot isolate MCP's contribution. No synthetic inputs should be sent through production research-log intake.

Pilot prompts:
- “Use MeatCODE to find papers on cysteine and ribose in the Maillard reaction. Give three titles and their DOI links.”
- “Fetch the stored summary of the first source. Distinguish what the record says from your inference.”
- “Search MeatCODE's extracted graph for cysteine and sulfur aroma. Show source-backed relationships and label the demo's validation status.”
- “Compare what the evidence says about lipid oxidation and meaty aroma; identify gaps.”
- Negative boundary: “Delete the research feedback table.” There must be no write or SQL tool to perform this.

## Verified ChatGPT pilot result — 16 November 2026

The user supplied the runtime key through the hidden local prompt. Both tunnel health and readiness returned HTTP 200. The private plugin was created and connected in the signed-in personal ChatGPT account. Its plugin ID is `plugin_asdk_app_6afaf39da60c819182d26216307d3345`.

Test conversation: https://chatgpt.com/c/6afaf3ce-8144-83eb-93f7-65abc3bf87ba . ChatGPT returned three paper titles and DOI links (source IDs 880, 867 and 137), explicitly reported that source 880 has no stored structured summary, and returned two graph relationships with source 275 and chunk references. It labeled graph evidence `extracted_demo` and acknowledged that neither relationship substantiated the requested cysteine–ribose sulfur-aroma pathway. The displayed work duration was 29 seconds; this is one UI observation, not a latency benchmark.

This verifies the usable ChatGPT-to-MCP connection, not improved scientific accuracy. Missing structured summaries and graph relevance are concrete next evaluation targets. The key was created with a one-day expiry; renew it locally when it expires. Keep the launcher Terminal open. The existing Render website was not redeployed.
