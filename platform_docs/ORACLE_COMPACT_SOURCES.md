# Oracle — compact sources and visible next step

Updated 2026-11-18 · Codex · Implemented from Lior’s accepted UI specification; release status below.

## Required behavior

- Show two main sources initially, when available; retain the existing retrieval order. Show the remaining source cards only when **Expand answer** is opened. **Show less** returns to two. There is no separate source-expansion control.
- Each complete source card, including title, stance label and padding, is one native publisher/DOI link. Remove the separate Details / PDF button. Preserve consensus labels and colors. Titles and card text have no underline or added text underline/separator. A record without a usable paper URL retains a single full-card button opening its existing metadata fallback.
- The brief answer includes a recommended **Next step:** before the expansion control. Supporting explanation remains expandable.

## Implementation

`MCOracleAnswer.mount` offers the same native disclosure when an answer has supporting prose **or** more than two sources. The view synchronizes source-card visibility to that disclosure on both toggle and rerender. Each turn owns its own state, and saved-history replay starts collapsed. Consensus still counts the complete retrieved set; hiding cards does not change their assessments or retrieval.

The normal answer style now explicitly requires a practical next-step sentence before the detail boundary. Guided rules previously contradicted this by placing it in the final paragraph before Follow-ups; that rule and its stale Follow-ups requirement are corrected. As a fallback for older answers, an explicit Next step paragraph in the hidden detail is moved into the visible brief, without inventing or generating an action, losing its citation, duplicating it, or modifying the stored plain answer. Older answers without a recorded next step do not get a fabricated one.

No retrieval, schema, API credentials, research capture, Denver, standalone graph demo or hosted MCP changes. Opening a full source card goes to its existing publisher destination; no automatic PDF lookup was added. Prior choices to skip live Claude and Unpaywall tests are respected.

## Validation

- Existing JavaScript split cases plus explicit next-step promotion, no duplication and no invented legacy recommendations passed. Evidence URL/count tests passed.
- Six offline Python presentation/evidence tests passed; Python compile and all19 inline script parses passed.
- Actual local browser: two visible source cards initially; six on expansion; two again on keyboard collapse. Independent turns keep independent disclosure states. A short answer with no supporting prose still exposes the four extra sources through the one Expand answer control. A legacy final Next step is visible without duplication. Reload/replay retains two-card defaults, links, colors and working expansion across four turns. Source cards are native anchors, and hit-testing their inset padding resolves to that same anchor; computed text decoration is none. Separate PDF buttons absent. The local browser reported no console errors.
- Screenshot `/private/tmp/meatcode-compact-sources-preview.jpg` shows labeled sample data. Fixtures make no production research or real model/PDF requests. Model adherence is not measured by these local tests.

## Release

Isolated branch `codex/oracle-compact-sources`, based on `6895f02` (previous runtime `cc9abda`). Publish to development first, verify exact deployed revision/health, then promote the same source to production. Canonical merge must retain unrelated local graph/chat-state work.
