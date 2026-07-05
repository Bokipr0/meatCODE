# Handoff: MeatCODE screens — Home, Map, Oracle, Research

_Last updated: 2026-07-05 · Claude Design session · new design handoff bundle_

## Overview
Four high-fidelity screen designs for the MeatCODE product surface, built in Claude Design
against the MeatCODE Design System (GFI Israel "seaweed teal" palette): **Home** (workspace
dashboard), **Community Map** (researcher/company network), **Food Oracle** (cite-backed RAG
chatbot), and **Research** (phase picker — Juice / Lipid / Matrix / Volatiles). These correspond
1:1 to the four product surfaces already described in this repo's `README.md` and
`PROJECT_STATE.md`.

## About the design files
Everything in `source/` is a **design reference**, not production code. Each `*.dc.html.txt`
is the literal markup/inline-style source of a Claude Design Component — it will **not run
as-is** in this repo (it depends on a Claude-only component runtime: custom `<x-dc>`/`<x-import>`
tags, a `support.js` loader, and the design-system bundle mounted from a Claude project). Treat
these files as **annotated specs**: every color, spacing value, font size, and copy string in
them is exact and lifted straight off the live design, but the DOM structure, component tags,
and JS are Claude-internal — do not copy them verbatim into the Next.js app.

**The task: recreate these four screens pixel-faithfully inside the real MeatCODE stack.**
Per `PROJECT_STATE.md`, the product's UI direction is heading to Next.js (mockup → Next.js
planned) — implement these as React components there using the app's existing patterns. If no
frontend scaffold exists yet for a given surface, standard React + CSS (or whatever the chosen
Next.js styling approach is — CSS modules/Tailwind/styled-components) is fine; just match values
exactly.

## Fidelity
**High-fidelity.** Pixel-perfect mockups with final colors, typography, spacing computed from
the MeatCODE Design System tokens (see below). Recreate exactly — don't reinterpret spacing or
substitute colors.

## Screens

### 1. Home (`screenshots/01-home.png`, `source/home.dc.html.txt`)
- **Purpose:** Workspace landing page. Greets the user, shows headline org-wide stats, and
  routes into the other three surfaces via domain cards.
- **Layout:** Fixed 64px top bar (white, `1px solid #E5DDD0` bottom border) with logo mark +
  wordmark, a 4-item pill nav (`Map / Home / Oracle / Research`, active = solid teal pill), and
  a search affordance right-aligned. Main content column max-width 1100px, centered, `32px 36px`
  padding.
  - Eyebrow (`MEATCODE · YOUR WORKSPACE`, 11px, 700, 0.18em tracking, teal) → 34px/700 display
    headline with a single 👋 emoji (only emoji use in the whole system) → 15px sub-copy in
    ink-dim.
  - **Stat strip**: one white pill-card row, 4 stats (Sources / Researchers / Organizations /
    Domains), big number in JetBrains Mono, label uppercase 11px below.
  - **3 domain cards** in a row (Community Map / Food Oracle / Research): white card, 16px
    radius, 1px hairline border, **4px left accent border** in the domain's color (teal / teal /
    coral), bold 17px title, 13.5px body copy, small meta line ("Updated 2 days ago" /
    "12 questions this week" / "3 saved queries") in ink-faint.
- **Components:** topbar nav pills, search chip, StatStrip (design-system `data/StatStrip`),
  3× domain Card (design-system `core/Card` with left accent + Icon chip).
- **Colors:** bg `#FAF6EF`, card surface `#FFFFFF`, hairline `#E5DDD0`, teal `#00736E` / teal-deep
  `#015A56`, coral `#C77E5F`, ink `#1A1A1A` / ink-dim `#4A4A4A` / ink-faint `#8A8A8A`.
- **No hover/active states captured in the static mock** — apply the system defaults (card
  hover-lift `translateY(-3px)` + `--shadow-lg`, ~0.18s `--ease-out`).

### 2. Community Map (`screenshots/02-map.png`, `source/map.dc.html.txt`)
- **Purpose:** Browse the expert/organization network; find and evaluate researchers or
  companies relevant to the user's topics.
- **Layout:** Eyebrow `THE COMMUNITY` → 30px/700 headline (wraps 2 lines) top-left; a 340px
  search input top-right (pill, `#fff` fill, hairline border, 🔍 leading glyph as placeholder
  text, not an icon element). Below: a pill **segmented toggle** (Researchers / Companies), the
  active segment solid teal with a small counted badge (`368 in your topics`), the inactive
  segment showing its own count in ink-faint.
- **Below the toggle, a two-pane row:**
  - **Left (map field):** teal-mist (`#B5DDD8`-family) irregular landmass shapes on a soft
    teal-tinted rounded panel, with small solid-teal dot pins marking expert locations (a
    stylized world/region map, not a real geo API in this mock).
  - **Right (ranked list):** panel header `EXPERTS IN YOUR TOPICS` + a pill count badge
    (`5 SHOWN`). Below, a scrollable stack of expert row-cards: name (bold 15px), affiliation
    (13.5px ink-dim), location (12.5px ink-faint), and a right-aligned match indicator. Two
    variants exist in this bundle — screenshot 1 shows a plain `MATCH` label, screenshot 2 shows
    a numeric match score (94, 91, 86, 83) above the `MATCH` label in teal JetBrains Mono —
    confirm with the design owner which is canonical before building (likely the scored
    version, since Home's stat strip and this list both lean on mono numerals for credibility).
- **Colors:** panel bg `--bg-deep` variants, map fill teal-tint family, active toggle teal
  `#00736E`, row hairlines `--line`, hover = teal-mist tint per system defaults.

### 3. Food Oracle (`screenshots/03-oracle.png`, `source/oracle.dc.html.txt`)
- **Purpose:** Ask a natural-language flavor/aroma question; get a cite-backed answer grounded
  in the literature corpus (per `docs/DECISION_Oracle_Answer_Engine.md`'s single-pass hybrid RAG
  design).
- **Layout:** Centered column, capped ~860px per system spec. Large centered title `Ask the Food
  Oracle` (34px/700) + centered 15px sub-copy. Below, the **ask panel**: a large white rounded
  card (22px radius = `--radius-2xl`), containing an 18px input placeholder line, two topic
  **chips** (`Maillard chemistry` teal-tint, `Off-note masking` coral-tint) as quick-filter
  affordances, and a solid teal pill **Ask ↑** button bottom-right.
  - Below the ask panel: a row of 4 **starter-question pills** (outlined, hairline border,
    13.5px, wrap to 2×2 on narrower widths) — real example questions, e.g. "How do I mask beany
    off-notes in pea protein?"
  - Below that: an empty/waiting **answer well** — dashed hairline border (`--line-strong`,
    system convention for empty states), centered small loading dot + `Waiting on your question`
    (15px bold) + 13.5px helper copy ("Pick a starter above or type your own...").
- **Components:** chip (teal/coral tint variants), pill button, CiteChip (`data/CiteChip` — not
  visible in this waiting state; appears once an answer streams in, per system's cite-backed
  answer pattern), starter-question pill row, empty-state well.
- **Not built in this bundle:** the populated answer state (streamed answer text + inline
  citation chips + a paper-detail modal) and the loading/typing-dots state — the design-system
  guide documents these patterns (Oracle typing dots, CiteChip) but this handoff only covers the
  **empty/ask state**. Flag to the design owner if the answered state is needed before build.

### 4. Research (`screenshots/04-research.png`, `source/research.dc.html.txt`)
- **Purpose:** Phase picker — the entry point into the molecular/mechanistic database, narrowing
  by physical phase before drilling into sub-topics.
- **Layout:** Centered header block: eyebrow `RESEARCH · PICK YOUR PHASE` (coral, uppercase,
  0.18em tracking) → centered 30px/700 headline → centered 15px sub-copy, max-width \~640px.
  Below, a **2-column grid** of phase cards (4 total — Juice, Lipid, Matrix, Volatiles; Matrix
  and Volatiles are below the fold in the captured screenshot).
  - Each card: white surface, 16px radius, hairline border, **4px left accent border** in the
    phase's own color (Juice = teal-tint, Lipid = coral, Matrix = olive, Volatiles = plum — per
    the system's 5-accent palette), a colored letter-chip (rounded-8px square, single capital
    letter, tinted bg + solid-color letter) top-left, bold 20px phase name, a small uppercase
    tag pill (e.g. `WATER-BASED`, `FAT-BASED` — outlined, phase-colored), 13.5px description
    copy, and a bottom-right `OPEN SUB-TOPICS →` link in the phase color (13px, bold, uppercase,
    small tracking).
- **Colors:** Juice teal-tint, Lipid coral (`#C77E5F` / `#F2D7C8` tint), Matrix olive
  (`#7A8C5F` / `#D6DCC4` tint per source order), Volatiles plum (`#7C5A8F` / `#E9DEF0` tint).

## Interactions & behavior
None of the four captures are interactive prototypes with wired transitions — they are static
high-fidelity screens. Apply the design system's documented defaults everywhere a state isn't
explicitly shown:
- Card hover: `translateY(-3px)` + `--shadow-lg`, ~0.18s, `cubic-bezier(0.16, 1, 0.3, 1)`.
- Buttons: background/shadow transition ~0.15s; outline buttons fill teal solid on hover.
- Active nav / active toggle segment: teal-mist bg (inactive) or solid teal (active), per screen.
- Oracle: typing-dots loop while an answer streams (documented in the system guide, not
  captured here — build per that description).
- Table/list rows (Map's expert list): hairline separators, teal-mist tint on row hover.

## State management
- **Map:** toggle state (Researchers vs. Companies) drives which count badge and list renders.
- **Oracle:** question state machine — idle/empty (captured) → loading (typing dots, not
  captured) → answered with citations (not captured) — needs the answer-rendering + CiteChip
  work described in `docs/DECISION_Oracle_Answer_Engine.md`.
- **Research:** no state beyond navigation — each phase card is a link into that phase's
  sub-topic view (not part of this bundle).
- Data (stats, expert list, phase descriptions) is placeholder/sample text from the mockup —
  wire to the real Neon-backed data per `PROJECT_STATE.md`'s three-homes model, not hardcoded.

## Design tokens
Pulled directly from the design system (`_ds/.../tokens/*.css`) — use these values, don't
re-derive new ones:

**Color** — bg `#FAF6EF`, bg-deep `#F2EBDA`, surface `#FFFFFF`, surface-2 `#F7F0E0` · teal
`#00736E`, teal-deep `#015A56`, teal-soft `#4FA59F`, teal-tint `#B5DDD8`, teal-mist `#E0F0EE` ·
ink `#1A1A1A`, ink-dim `#4A4A4A`, ink-faint `#8A8A8A` · line `#E5DDD0`, line-strong `#D2C8B5` ·
coral `#C77E5F` / coral-soft `#F2D7C8` · olive `#7A8C5F` / olive-soft `#D6DCC4` · plum `#7C5A8F`
/ plum-soft `#E9DEF0`.

**Type** — Varela Round (brand/UI), JetBrains Mono (data/molecular names/metrics). Scale: display
34px, h1 30px, h2 22px, h3 17px, lg 18px, body-lg 15px, base 13.5px, sm 12.5px, xs 11px,
2xs 9.5px. Weights 400/700 only. Eyebrow tracking 0.18em uppercase; large display tracking
-0.01em.

**Spacing** — 4/6/8/10/12/14/16/18/22/28/36px scale.

**Radius** — 8px chips/icon-chips, 12px buttons/inputs, 16px cards/tables, 20px large panels,
22px modals/Oracle input, 100px full pills.

**Shadow** — `--shadow: 0 4px 16px rgba(0,67,64,.08)`, `--shadow-lg: 0 10px 32px rgba(0,67,64,.12)`
— always teal-tinted, never neutral gray.

**Motion** — `cubic-bezier(0.16, 1, 0.3, 1)`; 0.12s/0.15s/0.18s durations.

## Assets
- No new icons/imagery introduced — all glyphs are the design system's existing inline-SVG
  `Icon` set (stroke, `viewBox 0 0 16 16`, `stroke-width 1.6`, round caps).
- No MeatCODE logo file exists (per the design system guide) — screens use an "M" chip mark +
  wordmark, consistent with the existing product.

## Files in this bundle
```
handoff/
  README.md                    ← this file
  screenshots/01-home.png       04-research.png  — reference renders, use for exact visual QA
  source/home.dc.html.txt       — reference markup/inline-style source (see "About the design
  source/map.dc.html.txt          files" above — NOT runnable in this repo, spec only)
  source/oracle.dc.html.txt
  source/research.dc.html.txt
```
Suggested repo location: `UI-UX Designer/design_handoffs/2026-07-05_home-map-oracle-research/`
(keeps it alongside the existing v8 polish pass per `PROJECT_STATE.md`'s "design deliverables
live in `UI-UX Designer/`" convention).

## For the agent team (per CLAUDE.md conventions)
Two snippets are included to paste in per this repo's own protocol:
- `AGENT_UPDATE_LOG_ENTRY.md` → paste at the **top** of `AGENT_UPDATE_LOG.md`.
- `PROJECT_STATE_ADDITION.md` → merge into the relevant sections of `PROJECT_STATE.md`.

This bundle was prepared outside the mounted sandbox (Claude Design has no git write access to
`Bokipr0/meatCODE`), so — consistent with the existing rule that pushes happen via
`sync_meatcode.command` — a human (or the first agent session with repo write access) needs to
drop this folder in and commit/push it before other agents will see it.
