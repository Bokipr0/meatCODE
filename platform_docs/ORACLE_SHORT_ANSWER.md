# Oracle - short answer first, detail on request

_Last updated: 2026-11-17 · Codex · Live on development and production; local browser verification passed._

Lior requested a less formal, less academic first answer that leads with the information most useful to the actual question, plus a clickable way to expand. This is the specific authorization to implement the presentation change; the broader development-priority PDF remains reference material.

## Resulting behavior

The normal and guided Oracle share a practical response style: a direct recommendation/finding first, a key reason and a next step when useful. The opening is 2-4 concise sentences, at most 100 words in the model instructions. Essential conditions and qualifications belong in this opening. Useful supporting detail follows; the model normally keeps it to 2-3 short paragraphs, with enough room for a specifically requested protocol/comparison.

The UI initially shows the opening and a native, keyboard-accessible **Expand answer** disclosure. **Show less** collapses it. Short answers with no supporting text have no unnecessary control. Citations are clickable in both parts. Expansion reveals already generated text: it sends no new question, retrieval or model request.

Guided answers put their "Working from" parameter recap in the supporting section, after the useful first answer. Clarification decisions and their frequency are unchanged.

## Implementation

- `server/oracle_presentation.py` owns shared style and an incremental separator filter. The model uses an internal `[[MEATCODE_DETAILS]]` marker. It is removed across arbitrary model chunk boundaries before any `chunk` event is sent. An additive `answer_section` SSE event identifies where detail starts. Older clients keep clean plain prose; consensus and research capture receive no internal marker.
- `server/meatcode_server.py` uses the filter in both standard and guided answer paths; model selection, retrieval rules, citation policy, consensus and existing research routing are unchanged.
- `app/assets/oracle-answer.js` renders the opening plus a native details/summary control. It preserves expanded state and focused control during streaming. Until a boundary arrives, a short second opening paragraph stays visible. A model that ignores the format, and older answers without metadata, use a paragraph/sentence-aware 120-word presentation fallback; the rest remains available on expansion.
- The existing conversation store keeps the full plain answer and an optional numeric opening boundary. The per-turn answer allowance rises from 4,000 to 12,000 characters so longer supporting explanations survive replay. Existing conversation/turn counts and storage error handling remain bounded and unchanged. Previously truncated text cannot be recovered.
- The new script has a safe full-text fallback if loading fails. No DB migration, production test-user record, new feature toggle or analytics event is introduced.

This changes the Oracle website. It does not impose a short-answer interface on ChatGPT's separately hosted MeatCODE MCP plugin.

## Verification

- Four Python tests: exact marker handling at every possible chunk split; brief/legacy prose preservation; incomplete-marker suppression; real standard and guided HTTP handler logic with a dummy SDK/model stream, no network or DB access.
- JavaScript checks: format boundaries, short and legacy text, 120-word cap, whole-text preservation, invalid metadata and Unicode.
- Existing local five-user SSE harness and incomplete-stream regressions passed (two tests).
- All 19 inline scripts parse; Python modules compile; JavaScript parses.
- Actual browser/local HTTP fixture: 48-word two-paragraph preview remains visible; supporting detail is initially hidden; expansion and Enter-key collapse work; supporting citations open their modal; saved-chat replay preserves the exact opening and a 5,000+ character explanation; a short response has no disclosure; a legacy response remains expandable; a slow stream retains expansion and keyboard focus. One streaming issue was found and corrected: a qualification in a second short paragraph must not fold before the explicit model boundary arrives.
- Local fixture counters showed one ask after expansion/collapse/replay, and zero research writes. Fixture source records and answers are explicitly labeled as sample data. The full production model/network style smoke is separate from these tests.

## Live-model validation limit

Automatic approval review rejected a proposed direct Claude style smoke because it would send one sample query plus up to six retrieved scientific source records (titles/abstracts/stored claims) to Anthropic without specific approval for that payload. Lior explicitly chose “Skip the live model test.” No live Claude test was run. Local fixtures verify presentation and protocol behavior; they do not measure model answer quality.

## Deployment record

Source release `7081ab48021eb3dbd053824bcc535f4c897d36e0`, isolated `codex/oracle-answer-disclosure` from website main/dev base `33cc8b8`.

- Development: `dep-dbu76hajnfac73e69c5g` terminal **live**; public `/api/version` confirmed exact source and `/api/health` returned 200. These health fields check configuration presence, not real model/database execution. The asset URL correctly retained the existing sign-in gate (unauthenticated 401).
- Production: the same source was fast-forwarded to main; deployment `dep-dbu77q5bedkc73f6b4ig` is terminal **live**. Public `/api/version` confirmed exact source `7081ab48021eb3dbd053824bcc535f4c897d36e0` and `/api/health` returned 200. No real model question was submitted.
- Scoped edits were merged into the canonical working folder without publishing its extensive unrelated changes. Its existing local turn status/synchronization arguments were preserved; canonical inline-script and Python checks passed.
- Local preview screenshots: `data/verification/oracle-short-answer-20261117/collapsed-local-fixture.jpg` and `expanded-local-fixture.jpg`. They show sample answers, not a Claude quality evaluation.
- The separate hosted MCP branch/service remains unchanged.
