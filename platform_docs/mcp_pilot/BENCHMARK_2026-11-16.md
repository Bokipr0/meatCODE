# MCP pilot benchmark — 16 November 2026

**Completed:** actual MCP stdio protocol and loopback Streamable HTTP initialization, tool discovery and scientific search. **Not yet established:** a ChatGPT-initiated tool call or any answer-quality gain.

| Retrieval | Calls | Direct median | MCP median | Direct p95 | MCP p95 |
|---|---:|---:|---:|---:|---:|
| search | 10 | 129.88 ms | 132.88 ms | 186.27 ms | 139.27 ms |
| search_knowledge_graph | 10 | 695.51 ms | 715.97 ms | 965.55 ms | 937.44 ms |

Initialization: 181.9 ms. Protocol: 2025-11-25. Official Python MCP SDK 1.30.0.

Five fixed queries, two repeats per tool: Maillard reaction/cysteine/ribose; lipid oxidation/aroma; plant-protein/beany flavor; GC-MS/aroma; deliberate non-match. Both tools returned nonempty results in 8/10 calls and empty results for the deliberate non-match. All 20 MCP results preserved direct retrieval's ordered evidence IDs. This is not precision/recall or a measure of scientific truth.

Other checks passed: source fetch, whitespace query rejection, oversized graph limit rejection, SQL-like source ID rejection, unavailable arbitrary SQL tool, and read-only/non-destructive tool annotations. Database sessions rolled back without writes. No model calls or research-log writes.

Interpretation: MCP transport did not materially change retrieval latency in this small sample. Direct calls preceded MCP calls, so warm caches and network variation can favor MCP; lower p95 does not prove MCP is faster. This is a local protocol benchmark, excluding OpenAI tunnel latency and model generation. Ten calls per retrieval is too small for a reliable production p95.

Graph mode was `lexical_graph`: lexical seeds plus bounded one-hop expansion over an extracted three-paper graph. No pgvector query or model-space compatibility test was performed. Literature and graph have different corpus sizes, so their results do not establish that one retrieval strategy is better.

Next gates: runtime-key authorization, tunnel readiness, private ChatGPT plugin discovery and a real ChatGPT-driven tool call. Then run the same-model, same-question answer comparison described in MCP_PRIVATE_PILOT.md.
