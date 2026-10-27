# Component library

The mockup has a stable vocabulary of components. Reuse before inventing.

## Buttons

### Primary

```html
<button class="btn-primary">Continue →</button>
```

```css
.btn-primary {
  background: var(--wine); color: var(--surface);
  padding: 12px 26px; border-radius: 12px;
  font-weight: 700; font-size: 14px;
  border: none; cursor: pointer; box-shadow: var(--shadow);
}
```

### Ghost

```html
<button class="btn-ghost">Skip — explore everything</button>
```

```css
.btn-ghost {
  background: transparent; color: var(--ink-dim);
  padding: 12px 18px; border-radius: 12px;
  font-weight: 500; font-size: 14px;
  border: none; cursor: pointer;
}
```

### Oracle ask (pill, with icon)

```html
<button class="oracle-ask">Ask <span>→</span></button>
```

Pill shape (100px radius), wine background, used specifically inside the Oracle input.

## Chips

### Standard wine-mist chip (for tags, citations)

```html
<span class="chip">Maillard</span>
```

```css
.chip {
  padding: 7px 13px;
  background: var(--wine-mist); color: var(--wine);
  border-radius: 100px;
  font-size: 12.5px; font-weight: 700;
}
```

### Suggestion chip (selectable filter, used on globe scene)

```html
<div class="sug-chip">Maillard</div>            <!-- default -->
<div class="sug-chip selected">Maillard</div>   <!-- active -->
```

```css
.sug-chip {
  padding: 6px 14px;
  background: var(--bg); border: 1.5px solid var(--line-strong);
  border-radius: 100px;
  font-size: 12.5px; font-weight: 700; color: var(--ink-dim);
}
.sug-chip.selected { background: var(--wine); border-color: var(--wine); color: var(--surface); }
```

### Tag chip (`.dash-sug-tag`)

```html
<span class="dash-sug-tag">New paper</span>
```

10.5px uppercase, wine-mist background, wine text, 8px radius. Used on dashboard "For you" suggestion cards.

## Cards

### Dashboard card (3-up row at top of dashboard)

```html
<div class="dash-card">
  <div class="dash-card-title">
    <div class="dash-card-icon"><svg ...></svg></div>
    Community Map
  </div>
  <div class="dash-card-desc">374 researchers and 89 organizations — see who's working on what.</div>
  <div class="dash-card-meta">Updated 2 days ago</div>
</div>
```

### Suggestion card (`.dash-sug`, on dashboard "For you" row)

```html
<div class="dash-sug">
  <div style="flex:1">
    <span class="dash-sug-tag">New paper</span>
    <h4>Hexanal binding by yeast β-glucan</h4>
    <p>2026 study from Wageningen — worth a 5-minute read.</p>
  </div>
</div>
```

### Persona card (onboarding)

```html
<div class="persona-card selected">
  <div class="persona-icon">🎓</div>
  <div class="persona-title">Academic Researcher</div>
  <div class="persona-desc">Papers, claims, expert networks, and the molecules behind your hypothesis.</div>
  <div class="persona-check"></div>
</div>
```

Add `selected` to the wrapper to show wine border + checkmark.

## User card

The full block. Pin to bottom of `.context` panel with `margin-top: auto`. Currently shows Lior Teper / Researcher · MSc / Tel Aviv University.

```html
<div class="user-card">
  <div class="user-avatar">
    <svg class="avatar-svg" viewBox="0 0 44 44">
      <defs>
        <linearGradient id="bgGradL" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="#F4DFDB"/>
          <stop offset="1" stop-color="#EAD2CF"/>
        </linearGradient>
      </defs>
      <rect width="44" height="44" fill="url(#bgGradL)"/>
      <!-- shoulders / shirt -->
      <path d="M4 44 C 6 34, 14 30, 22 30 C 30 30, 38 34, 40 44 Z" fill="#7E2E2E"/>
      <!-- collar -->
      <path d="M18 32 L22 36 L26 32" fill="none" stroke="#FBF4EE" stroke-width="1.2"/>
      <!-- neck -->
      <rect x="19" y="26" width="6" height="6" fill="#E8B89A"/>
      <!-- head -->
      <ellipse cx="22" cy="20" rx="8" ry="9" fill="#E8B89A"/>
      <!-- hair -->
      <path d="M14 19 C 14 12, 18 10, 22 10 C 26 10, 30 12, 30 19 C 30 16, 28 14, 22 14 C 17 14, 15 16, 14 19 Z" fill="#3A2A1F"/>
      <!-- glasses -->
      <circle cx="19" cy="20.5" r="2" fill="none" stroke="#2A1F1F" stroke-width="0.8"/>
      <circle cx="25" cy="20.5" r="2" fill="none" stroke="#2A1F1F" stroke-width="0.8"/>
      <line x1="21" y1="20.5" x2="23" y2="20.5" stroke="#2A1F1F" stroke-width="0.8"/>
      <!-- smile -->
      <path d="M20 24 Q 22 25.5, 24 24" stroke="#7E2E2E" stroke-width="0.9" fill="none" stroke-linecap="round"/>
    </svg>
  </div>
  <div class="user-meta">
    <div class="user-name">Lior Teper</div>
    <div class="user-role">Researcher · MSc</div>
    <div class="user-org">Tel Aviv University</div>
  </div>
</div>
```

The org line is wine-colored (`color: var(--wine); font-weight: 700;`) — it's effectively an affiliation badge, not body text.

## Oracle answer block

```html
<div class="oracle-answer">
  <h3>Reaktzia Answer</h3>
  <p>...body paragraph 1...</p>
  <p>...body paragraph 2...</p>
  <div class="oracle-evidence">
    <div class="oracle-evidence-label">Evidence</div>
    <div class="oracle-cite">
      <span class="oracle-cite-chip">Sohail et al. 2022</span>
      <span class="oracle-cite-text">Trends in Food Science — pea protein off-notes</span>
    </div>
  </div>
</div>
```

- Heading is 12px wine uppercase eyebrow style, not a real h3.
- Citations are wine-mist pills paired with grey body text.

## Globe scene (Map)

The globe is a Three.js sphere with researcher dots and great-circle arcs. Filter chips above, detail panel right, legend bottom-left.

```html
<div class="map-page">
  <div class="map-header-row">
    <div>
      <div class="eyebrow">Community</div>
      <h1>Researcher map</h1>
    </div>
    <div class="map-search-wide">🔍 Search researchers, orgs, topics</div>
  </div>

  <div class="suggestion-row">
    <span class="sug-label">Filter by topic</span>
    <div class="sug-chips">
      <div class="sug-chip selected">Maillard</div>
      <div class="sug-chip">Pea protein</div>
      <div class="sug-chip">Aroma volatiles</div>
    </div>
    <div class="sug-count"><b>23</b> matches</div>
  </div>

  <div class="globe-wrap">
    <div id="globe-canvas"></div>
    <div class="globe-detail">
      <h3>Dr. Idan Almog</h3>
      <div class="org">Technion — Faculty of Food Engineering</div>
      <div class="loc">Haifa, IL</div>
      <div class="gd-stats">
        <div class="gd-row">Papers <b>47</b></div>
        <div class="gd-row">h-index <b>22</b></div>
        <div class="gd-row">Open to chat <span class="ok">Yes</span></div>
      </div>
      <div class="gd-tags">
        <span class="chip">Maillard</span>
        <span class="chip">High-temp aroma</span>
      </div>
      <button class="gd-cta">Request intro</button>
    </div>
    <div class="globe-hint">Drag to rotate · scroll to zoom</div>
    <div class="globe-legend">
      <div><span class="gl-dot acad"></span>Academic</div>
      <div><span class="gl-dot ind"></span>Industry</div>
      <div><span class="gl-dot ngo"></span>NGO</div>
    </div>
  </div>
</div>
```

The Three.js setup loads from `https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js` and uses sphere + dot meshes + TubeGeometry arcs along great-circle SLERPs. The full script is at the bottom of the mockup file.

## Dev-nav (dismissable scene picker)

A small dark pill at the bottom that lets you cycle through scenes during development. Hidden in production. Has a × button to dismiss (state in localStorage) and a 'H' keyboard shortcut. There's also a `.dev-show-tab` that appears in the corner when dev-nav is hidden, to bring it back.

```html
<div class="dev-nav">
  <a href="#onboarding">Onboarding</a>
  <a href="#dashboard" class="active">Dashboard</a>
  <a href="#oracle">Oracle</a>
  <a href="#map">Map</a>
  <a href="#research">Research</a>
  <a href="#research-sub">Sub-topics</a>
  <a href="#research-db">Database</a>
  <div class="dev-close">×</div>
</div>
<div class="dev-show-tab">show nav</div>
```

When adding a new scene, add an `<a href="#new-id">` to this list.
