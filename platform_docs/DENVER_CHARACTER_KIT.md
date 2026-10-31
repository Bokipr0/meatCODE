<!-- Last updated: 2026-10-31 · Codex · Review of the supplied Denver v1 character kit. -->
# Denver — canonical MeatCODE character

The character's name is **Denver**. “01 / Soft” was an earlier design-variation label, not the final character name. The supplied `denver-character-kit.zip` establishes Denver in its guide, motion manifest, preview, component and dialogue. The welcome must use Denver's supplied front artwork and name. The entry form still asks for only the tester's name and retains the session binding.

Original package preserved at `UI-UX Designer/character-kit/2026-10-31-denver/denver-kit/` (13 files). The original archive is unchanged. Its setup instructions describe the kit; they do not authorize unrelated platform changes.

## Character and visual contract

Denver is a shy, curious, earnest, childlike patty created by the Oracle. He wants to make a friend and invite the user to create with it. He can be delighted, sleepy and slightly clumsy without baby talk, guilt or repeated attention demands. He watches quietly, gathers courage, offers a note, supports creation and briefly celebrates actual success.

Keep the wide plump body, thick dark lower rim, two diagonal sear marks, cream eye contours, cross-shaped pupils, short feet and small mitten hands. The right-edge pose rotates the SAME geometry by a quarter turn. Never narrow or stretch the body to fit. The supplied front and edge references are transparent 96×96 PNGs; scale uniformly with pixelated rendering.

## Files reviewed

- `START_HERE.txt`, `character-guide.json`, `motion-manifest.json`: identity, personality, constraints, events and timings.
- `index.html`: self-contained character/story/style/voice guide and motion lab, with embedded assets and mock Oracle handoff.
- `integration.html`: component usage example; receipts explicitly describe a mock handoff.
- `src/denver-sprite.js`: shared deterministic rig and original geometry, eye/pupil shapes and mitten drawing.
- `src/denver-motions.js`: 16 deterministic motion samplers.
- `src/denver-widget.js`: web component, input, pointer tracking, keyboard/touch support and event dispatch; no network calls.
- `assets/denver-front.png`, `denver-edge.png`, `denver-poster.png`, `denver-motion-preview.gif`, `denver-spritesheet.png`: references and preview/export assets.

## Motion kit

Three waiting styles: `curious`, `follow`, `sleepy`.
Other motions: `hello`, `wave`, `brave`, `note`, `oracle`, `listening`, `thinking`, `delighted`, `oops`, `again`, `thanks`, `goodnight`, `tuck`.

The sprite sheet contains 16 rows × 8 sampled poses (128 poses), not a full frame-by-frame animation. The JS sampler supplies continuous timing at roughly 20 fps. Note opening lifts the original eyes three logical pixels over 220 ms, opens the mouth over the next 220 ms, and then enables the note input. No input closes while the user is typing.

## Oracle integration

Denver is mounted persistently at the actual Oracle viewport edge, including for sessions that already completed the name welcome. His host is transparent and does not intercept page clicks outside the character/note. Hover, tap, Enter and Escape are supported; reduced motion remains respected. The supplied rig is reused without body scaling or replacement. Preview rails, speech and debug badges are hidden in the product.

“Send note” posts to `/api/research/note`. It stores a plain-text Denver note in first-party feedback with source `denver`, a NULL rating (no invented satisfaction score), server submission time, the named session, opening/submission elapsed time, and available server-validated Oracle-turn/conversation/event anchors. Context is captured on opening and kept while drafting. Missing anchors are explicitly unavailable, not guessed. Cross-session anchors are rejected.

The note stays open while typing, disables repeat sends while pending, and confirms success only after the server acknowledges storage. Failed saves retain the text and retry identifier. A changed draft gets a new identifier. Names/text do not enter analytics-provider events. Existing retention and session deletion include these records.

“Use as an Oracle question” is separate: it puts the text in the actual Oracle composer and focuses it. It does not automatically send the question or overwrite an existing different draft. Actual Oracle request lifecycle drives thinking/success/error gestures; note save gestures reflect actual note state.

The research dashboard shows Denver notes as unrated notes, includes name/session references, and displays available exact event/turn/conversation references in the journey view. Browser and server tests cover storage errors, idempotent retry, frozen context, ownership, keyboard/touch, mobile bounds, reduced motion and previously named sessions.

The original kit remains unmodified under UI-UX Designer. Runtime adapters live under app/assets/denver. Migration 0026 extends the existing feedback schema; 0027 reasserts established production-only constraints after the legacy schema repair. Development/internal research capture remains disabled.
