# Design tokens

All design decisions in the mockup go through these CSS variables. Edit the variable to change the whole product; never inline a hex code in a component.

## Palette — wine / pomegranate

The brand is built around a deep wine red against a warm cream cream-pink background. Brass and olive serve as secondary accents.

| Token | Hex | Where it shows up |
|-------|-----|-------------------|
| `--bg` | `#F2E6DD` | App background (warm cream-pink) |
| `--bg-deep` | `#ECDCD0` | Domain tabs container, search pill, dock items |
| `--surface` | `#FBF4EE` | Cards, topbar, dock, context panel |
| `--surface-2` | `#F7EBE0` | User card, table header rows, secondary surfaces |
| `--wine` | `#7E2E2E` | **Primary brand color.** Logo, active tabs, primary buttons, accent text |
| `--wine-deep` | `#5E1F1F` | Headings on wine background, deepest accents |
| `--wine-soft` | `#A14848` | Hover states, gradients |
| `--wine-tint` | `#EAD2CF` | Card borders on hover, soft accents |
| `--wine-mist` | `#F4DFDB` | Active-state backgrounds (subtle), chip backgrounds |
| `--ink` | `#2A1F1F` | Body text |
| `--ink-dim` | `#6B5550` | Secondary text (descriptions, meta) |
| `--ink-faint` | `#9C8478` | Tertiary text (placeholders, eyebrow labels in nav) |
| `--line` | `#E2D2CB` | Default border |
| `--line-strong` | `#D2BCAF` | Stronger borders (selected states, sub-card outlines) |
| `--brass` | `#A8814E` | Industry dots on globe, secondary accent |
| `--brass-soft` | `#E6D2B8` | Brass backgrounds |
| `--olive` | `#7A8C5F` | NGO dots, "ok" / success accent |
| `--olive-soft` | `#D6DCC4` | Olive backgrounds |

## Shadows

Always wine-tinted, never grey.

```css
--shadow:    0 4px 16px rgba(94, 31, 31, 0.07);
--shadow-lg: 0 10px 32px rgba(94, 31, 31, 0.10);
```

`--shadow` for cards, buttons, the logo. `--shadow-lg` for the bubble grid in the Research scene.

## Typography

```css
--round: "Varela Round", "Heebo", -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
```

Loaded via:

```html
<link href="https://fonts.googleapis.com/css2?family=Varela+Round&display=swap" rel="stylesheet">
```

Hebrew text falls through to Heebo. Letter-spacing baseline `0.005em` on body. Font-smoothing is antialiased.

### Type scale

| Class | Size | Weight | Use |
|-------|------|--------|-----|
| `.h1` (or `h1` inside hero) | 34–36px | 700 | Page hero titles, Oracle question heading |
| `.h2` | 22px | 700 | Section titles |
| Card title (`.dash-card-title`, `.globe-detail h3`) | 16–19px | 700 | Card and panel headings |
| Body `<p>` | 13–16px | 400 | Descriptions, Oracle answer body |
| `.muted` | inherits size | 400 | Greyed body text (uses `--ink-dim`) |
| `.faint` | inherits | 400 | Tertiary text (uses `--ink-faint`) |
| `.eyebrow` | 11px | 700 | Uppercase wine label above titles, letter-spacing 0.16em |
| Section label (`.context-label`, `.dash-section-title`) | 10–12px | 700 | Uppercase grey label, letter-spacing 0.12–0.18em |

## Shape

| Use | Border-radius |
|-----|---------------|
| Buttons, chips, dots, dev-nav | 100px (pill) |
| Cards, dock items, oracle input | 14–22px |
| Avatars | 50% |
| Small icons inside dock/dash card | 10–12px |

## Spacing rhythm

- Canvas padding: `32px 36px 36px`
- Card padding: `20–24px`
- Card gap (in grids): `14–22px`
- Chip padding: `5–8px vertical`, `12–18px horizontal`
- Section gap inside context panel: `18px`
