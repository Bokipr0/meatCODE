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

## Product integration still required

1. Mount the companion at the actual Oracle viewport edge. The shipped component is a preview with an opaque background, rail, speech and motion-status badge. Remove that preview framing in the product adapter; only the character and open note should receive pointer input. Avoid a full-screen interactive overlay and do not obscure the Oracle composer.
2. Respect reduced motion. Automatic product state changes must call `play(name, false)`; the default `play(name)` explicitly forces animation on. Provide click, touch and keyboard alternatives to hover. Preserve drafts across failures and intentional closing.
3. `denver:note` carries `detail.text` only. Connect it to FIRST-PARTY RESEARCH submission and the already named session. The current kit saves nothing. Replace preview receipts with actual pending/success/error states and disable duplicate sends until the request settles. Never fabricate a helpful/neutral/unhelpful rating for this plain-text note.
4. Capture the originating session, conversation, Oracle turn and event references when the note opens, plus submission time; preserve that context while the user types or navigates. A session join alone cannot prove which turn the note refers to. Null references must remain null when no turn/event exists. Validate ownership server-side and keep names/text out of external analytics.
5. `denver:oracle-request` is a SEPARATE action carrying the draft to Oracle. It must not silently reinterpret a research note as an Oracle question. Use the real composer/handoff and its actual request lifecycle.
6. `thinking`, `delighted` and `oops` must correspond to real pending, acknowledged success and failure. The preview's “ready for the Oracle” receipt is not proof of storage or an Oracle response.

Current integration: Denver's supplied artwork/name in the name-only welcome; session-name persistence retained. The complete character kit has been received and reviewed. The edge widget, research-note API/context anchors and Oracle handoff are not yet connected by this naming correction.
