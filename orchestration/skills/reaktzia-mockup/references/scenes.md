# Scenes

The mockup currently has 7 scenes. Each scene is a full-page `<section class="scene" id="...">`. Only one has `class="scene active"` at a time — that's the one displayed.

## Scene inventory

| ID | Purpose | Active domain tab | Distinct components |
|----|---------|-------------------|---------------------|
| `onboarding` | Persona picker (Step 1 of 2) — Academic / Chef / Flavor House / Strategy | none (dimmed) | `.persona-card`, `.btn-primary`/`.btn-ghost` |
| `dashboard` | Home screen, "Back at it, Lior" hero, 3 domain cards, "For you" suggestions | none active (it's the home) | `.dash-card`, `.dash-sug`, `.dash-greeting` |
| `oracle` | Question box + streaming answer + evidence citations + follow-up suggestions | Oracle | `.oracle-input`, `.oracle-answer`, `.oracle-cite` |
| `map` | 3D spinning globe with researcher dots, filter chips, detail panel | Map | `.globe-wrap`, `.suggestion-row`, `.sug-chip`, `.globe-detail` |
| `research` | 6 large bubble grid — pick a research area | Research | `.bubble`, `.bubble-grid` (6 gradient circles) |
| `research-sub` | Sub-topic checklist after picking a bubble | Research | `.sub-card`, `.breadcrumb`, `.sub-actions` |
| `research-db` | Final database table — molecules / sources / scores | Research | `.db-table`, `.db-tags`, `.db-actions` |

## Scene switching

Currently the dev-nav is the only way to switch. Click an `<a href="#scene-id">` and a small JS handler toggles `class="scene active"` on the matching `<section>`.

```js
// Sketch of the scene-switch behavior (full code is at the bottom of the file)
document.querySelectorAll('.dev-nav a').forEach(a => {
  a.addEventListener('click', e => {
    e.preventDefault();
    const id = a.getAttribute('href').slice(1);
    document.querySelectorAll('.scene').forEach(s => s.classList.remove('active'));
    document.getElementById(id).classList.add('active');
    document.querySelectorAll('.dev-nav a').forEach(x => x.classList.remove('active'));
    a.classList.add('active');
  });
});
```

The domain tabs in the topbar also have click handlers that switch to the right scene (Map → `map`, Oracle → `oracle`, Research → `research`).

## Dev-nav dismissability

The dev-nav has a × close button that hides it. State is saved in `localStorage` so it stays hidden across reloads — useful for clean screenshots. Press **H** on the keyboard to toggle it back, or click the small "show nav" tab that appears in the corner when hidden.

```js
// Dev-nav hide/show, persisted
const devNav = document.querySelector('.dev-nav');
const showTab = document.querySelector('.dev-show-tab');
const HIDE_KEY = 'reaktzia-devnav-hidden';

function applyHidden(hidden) {
  devNav.style.display = hidden ? 'none' : 'flex';
  showTab.classList.toggle('visible', hidden);
}
applyHidden(localStorage.getItem(HIDE_KEY) === '1');

document.querySelector('.dev-close').addEventListener('click', () => {
  localStorage.setItem(HIDE_KEY, '1'); applyHidden(true);
});
showTab.addEventListener('click', () => {
  localStorage.removeItem(HIDE_KEY); applyHidden(false);
});
document.addEventListener('keydown', e => {
  if (e.key === 'h' || e.key === 'H') {
    const hidden = localStorage.getItem(HIDE_KEY) === '1';
    if (hidden) { localStorage.removeItem(HIDE_KEY); applyHidden(false); }
    else        { localStorage.setItem(HIDE_KEY, '1'); applyHidden(true); }
  }
});
```

## Adding a new scene

1. **Pick an id.** Use kebab-case. Don't collide with existing ids.
2. **Copy the template.** `assets/scene-template.html` is a complete `<section class="scene">` with all four shell regions wired up.
3. **Place it in the file.** Insert before the `</body>` tag, after the existing scenes but before the dev-nav and the closing `</body>`.
4. **Pick the active domain tab.** If the scene is a Map sub-screen, the Map tab gets `class="domain active"` in the topbar of this scene.
5. **Add a dev-nav entry.** Insert `<a href="#your-id">Your Label</a>` in the dev-nav list. Order it where it fits the user flow.
6. **Add scene-specific CSS.** Put new styles in a fresh comment block in the `<style>` section: `/* ── YourScene ── */`. Reuse design tokens; only add new classes if no existing component fits.
7. **Hook up navigation.** If a button or card in another scene should jump to your new scene, add a click handler (or rely on the existing domain-tab handlers).

## Scene-specific design notes

### Onboarding

The only scene where domains and dock are dimmed (`opacity: 0.4; pointer-events: none`). The context panel is empty. This is the only "pre-product" scene.

### Dashboard

The hero greeting (`Back at it, Lior 👋`) is personalized — keep the warm voice. The "For you, today" row pulls 4 cards with category tags (`New paper`, `Expert`, `Trending`, `Reminder`).

### Oracle

The Oracle question is centered (`max-width: 860px; margin: 0 auto`). The answer block has an eyebrow-style heading (`Reaktzia Answer`), body paragraphs, and an evidence section separated by `border-top: 1px solid var(--line)`.

### Map (Globe)

The globe is the only scene with full-height content (`.map-page { height: 100%; }`). The `.globe-wrap` is a 2-column grid: canvas left, 296px detail panel right. Filter chips drive what dots appear on the globe. Three.js handles rotation (drag), zoom (scroll), and dot rendering.

### Research / Research-sub / Research-db

These three are a flow: pick a bubble → check sub-topics → see the database table. The breadcrumb at the top of `research-sub` and `research-db` reflects this.
