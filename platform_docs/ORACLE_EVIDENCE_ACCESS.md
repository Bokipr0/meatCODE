# Oracle evidence access and Denver placement

Updated 2026-11-17 · Codex · Implementation verified locally; deployment record follows.

Lior reported source pills/citation315 inaccessible, Denver feedback overlapping answer text, extra action buttons, and a mismatch between four neutral classifications and six retrieved sources.

## Result

- Full source titles and known inline citations are native publisher/DOI links, including keyboard/new-tab support. Details / PDF opens the paper metadata. Older saved citations without bibliographic data retain a details-button fallback. Publisher links remain usable if the metadata request fails, using the streamed source metadata. Paper dialogs sit above Denver. Normalized DOI URLs avoid double-prefixing and unsafe non-HTTP links are rejected.
- Open-PDF lookup is explicitly initiated with **Check open PDF** in paper details. It reuses the existing cached Unpaywall resolver through the signed-in `/api/papers/{id}/access` route, independently of the separate papers-browser feature flag. It does not proxy publisher content or bypass subscription access. Available open PDFs get an Open / download PDF link; absent/unavailable lookups keep publisher access and an honest explanation.
- Denver's rating, note and idle prompts appear below the character. Wide screens reserve a right-hand area while a panel is open. Compact screens put the companion panel above the visible conversation in normal layout flow, rather than overlaying it. Existing rating cadence, consent, event linkage and note submission logic are unchanged. Native fallback note placement also moved below the portrait.
- Answer cards no longer generate Try next, Related molecules, Open in Science or Experts on this actions, and no molecule suggestion request is made. Expand answer is the answer action; source-access controls remain. Composer navigation and guided clarification choices remain usable. The prompt no longer requests follow-up questions; old responses still have their trailing Follow-ups text removed.
- Consensus previously emitted `agree`, but the client read only `support`, hiding supportive counts. The display now derives every count from per-source assessments for the displayed retrieved set. Supports is green, Opposes rust, Neutral blue; missing or invalid assessments are **Not assessed**, never silently neutral. The server normalizes numeric/string IDs and reports missing assessments explicitly. The assessed central claim is exposed when returned. This is a model assessment of the retrieved sources, not systematic consensus across the corpus or proof of every sentence.
- Bibliographic metadata and per-source assessments are saved with new browser-history turns, so replay retains links and colors. Old chats without these fields are not assigned invented stances. Metadata is bounded and excludes raw claim records.

## Paper315

Neon record315 was read directly with the existing detail query and matched the title/DOI:

**Unveiling the role of oxylipins in the formation of off-flavor in pea protein isolates**

- DOI: https://doi.org/10.1016/j.foodres.2025.118315
- Exact publisher page, verified via web search: https://www.sciencedirect.com/science/article/pii/S0963996925026559

A proposed live Unpaywall availability check was rejected by automatic approval review because it would transmit the configured contact email and DOI to api.unpaywall.org. Lior explicitly chose to skip that check and retain the publisher link. No live PDF availability for315 or live Claude answer/stance quality is claimed. The download control was tested only against a labeled local fixture file.

## Validation

Six offline Python tests cover normal/guided stream compatibility, boundaries, six-source accounting with numeric/string IDs, missing/invalid assessments, and the independent PDF-access route without the papers-browser flag. JavaScript tests cover six-source totals, agree/support compatibility, unknown IDs, absent assessments, DOI normalization and unsafe links. All19 inline scripts parse and the Denver generated bundle matches its sources.

Actual local-browser checks verified six displayed sources and 2 support + 4 neutral, native DOI links, paper details, a completed sample PDF download, saved-history links/colors, absence of extra answer actions, and below-character rating/note placement. At1280×720, the rating panel began below the character and beyond the answer's right edge. At800×800, it was above the visible conversation and within the viewport. These are deterministic fixture results, not scientific model evaluations. No production research events were submitted.

## Deployment

Prepared on isolated `codex/oracle-evidence-access`, based on prior verified release documentation `ae5d20b` (runtime7081ab4). Canonical folder contains unrelated local work and is synchronized only with scoped edits. Stage on dev first, then promote the same source to production. Hosted MCP and Neon schema are unchanged.
