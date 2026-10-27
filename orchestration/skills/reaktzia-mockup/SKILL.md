---
name: reaktzia-mockup
description: Edit, extend, or extract anything from Lior's Reaktzia HTML mockup — the single-file prototype for the Good Food Institute flavor & aroma research product (Map / Oracle / Research domains). Trigger this skill whenever the user mentions Reaktzia, "the mockup," "the prototype," asks to add or change a screen/scene, tweak the dashboard, redesign the user card, change colors, add a domain tab, add a dock tool, modify the globe, restyle the Oracle, edit a button, or do anything to the file at /Users/lior/Documents/Claude/Projects/Claude Database/reaktzia_mockup.html — even when phrased casually like "tweak the prototype," "add a screen for X," or "make the dashboard show Y." Use this skill instead of guessing the design tokens; the project has a strong wine/pomegranate brand and several established conventions that need to be respected for the mockup to stay coherent.
---

# Reaktzia mockup edits

## What this skill is for

Reaktzia is Lior Teper's research product mockup — a single-file HTML prototype that demonstrates the experience of a flavor and aroma research database for the Good Food Institute. The mockup is the living design artifact: every conversation about visual changes, new screens, copy tweaks, or interaction ideas modifies it.

This skill captures the design system, file structure, and editing conventions so that mockup edits stay on-brand and the file stays coherent across many sessions. Without it, future edits drift — palettes get re-invented, fonts mismatch, scenes get added without dock/topbar/context-panel, and the prototype becomes incoherent.

## File location

```
/Users/lior/Documents/Claude/Projects/Claude Database/reaktzia_mockup.html
```

Single file. ~1,230+ lines. All CSS in `<style>`, all JS at the bottom, scenes as `<section class="scene" id="...">` with one having `class="scene active"` at a time.

## Before editing — always do this

1. **Read the file first.** Don't rely on memory; the user iterates often and the file evolves.
2. **Identify the scene.** There are 7 scenes — see `references/scenes.md`. Each scene is a `<section class="scene" id="...">` that contains its own `.app` grid (topbar + context + canvas + dock).
3. **Use the design tokens, not raw hex.** All colors are CSS variables in `:root` — see `references/design-tokens.md`. Never introduce a new color without checking if a token exists.
4. **Preserve the four shell regions.** Every scene has topbar (top), context panel (left), canvas (center, the only thing that changes scene-to-scene), and dock (bottom). Don't remove them; don't add a 5th region.

## Design system at a glance

**Palette:** wine/pomegranate. `--wine: #7E2E2E` is the brand color; warm cream `--bg: #F2E6DD` and `--surface: #FBF4EE` for backgrounds; `--brass`, `--olive` as secondary accents for industry/NGO.

**Typography:** `Varela Round` (loaded from Google Fonts), with `Heebo` as Hebrew fallback. System fallbacks after. All set via `--round` CSS var. Letter-spacing baseline is `0.005em`.

**Shape language:** rounded everything. 10–22px border-radius on cards. 100px (pill) on chips and buttons. Shadows are wine-tinted, never grey.

**Density:** mid-density. 32–36px canvas padding, 22–28px card padding, 14–18px chip padding.

Full token list lives in `references/design-tokens.md` and the bare CSS is at `assets/design-tokens.css`.

## App shell pattern

Every scene wraps content in this grid:

```html
<section class="scene" id="<name>">
  <div class="app">
    <header class="topbar">...</header>     <!-- brand + domain tabs + search/bell -->
    <aside class="context">...</aside>      <!-- saved views, recents, user card -->
    <main class="canvas">...</main>         <!-- the scene's actual content -->
    <footer class="dock">...</footer>       <!-- 4 persistent tools -->
  </div>
</section>
```

The grid is `grid-template-rows: 64px 1fr 88px; grid-template-columns: 248px 1fr`. Topbar and dock span both columns; context is left of canvas. See `references/app-shell.md` for the full breakdown including the domain tabs (Map / Oracle / Research) and the user card.

## Component library

The mockup has a stable component vocabulary — domain tabs, dock items, chips, cards, persona cards, buttons (primary/ghost), the user card with inline-SVG avatar, the Oracle answer block, the globe scene with filter chips and detail panel. Each has a CSS class and a typical HTML shape. See `references/components.md` for the full inventory with copy-paste snippets.

## How to do common edits

### Add a new scene

1. Pick an `id` that doesn't collide (existing: `onboarding`, `dashboard`, `oracle`, `map`, `research`, `research-sub`, `research-db`).
2. Copy `assets/scene-template.html` as your starting point — it has all four shell regions wired up.
3. Mark which domain tab is active in the topbar (`<div class="domain active">`) based on what the scene is.
4. Add an entry to the dev-nav at the bottom of the file (see `references/scenes.md`).
5. Use existing CSS classes wherever possible; only add new ones inside the section's CSS comment block (`/* ── <SceneName> ── */`).

### Change a color or token

1. Edit the `:root` block in the `<style>` section.
2. Don't replace usages — every usage already references the var, so the change propagates.
3. If the user wants a fundamentally new palette (not just a tweak), update `assets/design-tokens.css` too so this skill stays current.

### Add a domain tab (Map / Oracle / Research are the current 3)

Daniel and Lior have considered a 4th domain a few times. If asked:
1. The `.domains` flex row in every topbar needs the new tab added in the same order across all 7 scenes.
2. Pick an SVG icon (16x16, `stroke-width="1.6"`, `fill="none"` style — match the others).
3. Decide what scene the tab points to and update the dev-nav.
4. Confirm with the user that the new tab makes it into the brand story; this is a brand-level change, not a small edit.

### Edit the user card

The user card is at the bottom of `.context` in every "logged-in" scene. It uses an inline SVG avatar (Lior Teper, glasses, dark hair). Name / role / org are hardcoded text. To change the user: edit the three `.user-name`, `.user-role`, `.user-org` divs in every scene that has a context panel. To restyle the avatar: edit the inline `<svg class="avatar-svg">` block — it's a stylized portrait, not a photo, so keep it geometric.

### Add a tool to the bottom dock

There are exactly 4 dock items: Database, Map, For You, Guide & Tips. If adding a 5th, confirm with the user — the row is laid out for 4 and a 5th changes the spacing. Each `.dock-item` has a `.dock-icon` (34x34 wine-mist square with SVG inside) and a `.dock-text` block with a small uppercase label and a main label.

### Write copy

Lior's voice for the mockup is: warm, slightly poetic, technically credible. Examples that match: "Back at it, Lior 👋 — picking up where you left off." "Ask anything about flavor, aroma, or molecules. Every answer is cite-backed and traceable." Avoid: dry product-speak, exclamation marks, generic SaaS phrasing.

## Editing workflow

For small edits (one component, one copy change):
1. Read the relevant section of the file.
2. Use the Edit tool with enough surrounding context to make the old_string unique.
3. Don't take a screenshot — the user opens the file themselves.

For larger edits (new scene, palette overhaul):
1. Read the whole file or large chunks.
2. Plan the change against the design tokens.
3. Make the edit, then list what changed (which scenes, which selectors).
4. Mention any places the change has knock-on effects (e.g., adding a tab means updating every topbar).

## Reference files

Read these when the relevant topic comes up:

- `references/design-tokens.md` — full palette, typography, shadow, spacing tokens
- `references/app-shell.md` — grid structure, topbar pattern, context panel pattern, dock pattern
- `references/components.md` — domain tabs, dock items, chips, cards, buttons, user card, Oracle answer, globe scene
- `references/scenes.md` — the 7 existing scenes, dev-nav, scene-switching JS, how to add a new one

## Assets

- `assets/design-tokens.css` — the `:root` block as a standalone CSS file (copy-paste ready)
- `assets/scene-template.html` — a blank `<section class="scene">` with all four shell regions wired up

## A note on style

When working on this mockup, Lior values:
- **Visual coherence over feature count.** A scene that looks finished beats a scene with more elements.
- **Real-feeling content.** Use plausible researcher names, molecule names (2-acetyl-1-pyrroline, hexanal), and organizations (Givaudan, Wageningen). Avoid Lorem Ipsum.
- **Surgical edits.** When given a note like "tighten the user card," change the user card and nothing else.

The collaboration pattern is: ask 3–4 multi-choice questions before doing creative work, then iterate per-piece on surgical notes. Don't make assumptions about scope — ask before adding scenes or making palette-level changes.
