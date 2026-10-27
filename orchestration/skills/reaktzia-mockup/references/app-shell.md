# App shell pattern

Every scene reuses the same four-region shell. Never break this — the user navigates by recognizing the persistent regions.

## The grid

```css
.app {
  display: grid;
  grid-template-rows: 64px 1fr 88px;
  grid-template-columns: 248px 1fr;
  min-height: 100vh;
}
```

- **Row 1 (64px)** — `.topbar`, spans both columns
- **Row 2 (1fr)** — left: `.context` (248px), right: `.canvas` (the scene's content)
- **Row 3 (88px)** — `.dock`, spans both columns

The onboarding scene is the only exception: it dims the domains and dock with `opacity: 0.4; pointer-events: none;` rather than removing them.

## Topbar pattern

```html
<header class="topbar">
  <div class="brand">
    <div class="brand-logo">R</div>
    <div class="brand-name">Reaktzia</div>
  </div>
  <div class="domains">
    <div class="domain"><svg ...>Map icon</svg>Map</div>
    <div class="domain active"><svg ...>Oracle icon</svg>Oracle</div>
    <div class="domain"><svg ...>Research icon</svg>Research</div>
  </div>
  <div class="topbar-right">
    <div class="topbar-search">⌘K · Search</div>
    <div class="topbar-bell">🔔</div>
  </div>
</header>
```

- The active domain tab gets `class="domain active"` — wine background, white text.
- Map / Oracle / Research is the canonical order. Don't reorder without good reason.
- Brand block is fixed `width: 220px` on the left; topbar-right is also `width: 220px` for symmetry.

### Domain SVG icons (16x16, currentColor)

```html
<!-- Map: concentric circles (globe) -->
<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6">
  <circle cx="8" cy="8" r="6"/><circle cx="8" cy="8" r="2.5"/>
</svg>

<!-- Oracle: chat bubble -->
<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6">
  <path d="M3 4h10v7H8l-3 2v-2H3z"/>
</svg>

<!-- Research: magnifier -->
<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6">
  <path d="M3 7c0-2 2-4 4-4s4 2 4 4-2 4-4 4-4-2-4-4z"/>
  <line x1="10" y1="10" x2="13" y2="13"/>
</svg>
```

## Context panel pattern

```html
<aside class="context">
  <div class="context-section">
    <div class="context-label">Saved Views</div>
    <div class="context-item"><div class="dot" style="background:var(--wine)"></div>Maillard researchers, EU</div>
    <div class="context-item"><div class="dot" style="background:var(--brass)"></div>Pea-protein experts</div>
  </div>

  <div class="context-section">
    <div class="context-label">Recents</div>
    <div class="context-item"><div class="dot"></div>2-acetyl-1-pyrroline</div>
    <div class="context-item"><div class="dot"></div>Sohail et al. 2022</div>
  </div>

  <!-- pinned at the bottom via margin-top: auto -->
  <div class="user-card">
    <div class="user-avatar">
      <svg class="avatar-svg" viewBox="0 0 44 44">
        <!-- inline portrait SVG, see components.md -->
      </svg>
    </div>
    <div class="user-meta">
      <div class="user-name">Lior Teper</div>
      <div class="user-role">Researcher · MSc</div>
      <div class="user-org">Tel Aviv University</div>
    </div>
  </div>
</aside>
```

- Sections are stacked with `gap: 18px`.
- Labels are uppercase, 10px, letter-spacing 0.16em, color `--ink-faint`.
- Items have a `.dot` indicator (6px circle) — colored when tied to a Saved View, default grey for Recents.
- Active item uses `background: var(--wine-mist); color: var(--wine-deep)`.
- The user card pins to the bottom with `margin-top: auto`.

The onboarding scene has an **empty context panel** (`<aside class="context"></aside>`) — the user hasn't set up saved views yet.

## Canvas

The only scene-variable region. Padding `32px 36px 36px`, `overflow: auto`. Don't put navigation elements here — those live in topbar and dock.

## Dock pattern

```html
<footer class="dock">
  <div class="dock-item">
    <div class="dock-icon"><svg viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.8">...</svg></div>
    <div class="dock-text"><small>open</small>Database</div>
  </div>
  <div class="dock-item">
    <div class="dock-icon"><svg ...>...</svg></div>
    <div class="dock-text"><small>navigate</small>Map</div>
  </div>
  <div class="dock-item">
    <div class="dock-icon"><svg ...>...</svg></div>
    <div class="dock-text"><small>personalized</small>For You</div>
  </div>
  <div class="dock-item">
    <div class="dock-icon"><svg ...>...</svg></div>
    <div class="dock-text"><small>help</small>Guide & Tips</div>
  </div>
</footer>
```

Exactly 4 items. Each:
- `.dock-icon`: 34x34, `--wine-mist` background, 10px radius, wine SVG inside.
- `.dock-text small`: 10.5px, uppercase, letter-spacing 0.06em, color `--ink-faint`. Acts as a verb/category.
- `.dock-text` main label: 13.5px, weight 700, color `--ink`.
- `.dock-item` itself: 22px horizontal padding, 12px vertical, 16px radius, `--bg` background, `--line` border.
- Hover: `--wine-mist` background, `--wine-tint` border.

Don't add a 5th item without confirming with Lior. The row is centered with `gap: 14px`, designed for 4.
