# UI/UX Design Notes — v8 polish pass

_Art director: Claude · 2026-06-30 (v8 r1) → 2026-07-01 (v8 r2) → 2026-07-07 (lean v1 exploration) → 2026-07-08 (v9 forward-port + deploy-safety check) · base file: `app/meatcode_mockup.html`_

This folder holds design-review iterations of the MeatCODE product UI. The canonical product
mockup lives at `../app/meatcode_mockup.html`; files here are candidates pending Lior's approval to
promote.

## v8 — `MeatCODE_mockup_v8_UIUX-polish.html`

Polish pass on the GFI seaweed-teal product UI. All changes verified (markup balanced, zero leftover
wine/red hexes, all scenes intact).

**Applied**
- **Avatar recolored wine→teal** — the profile card SVG hardcoded `#7E2E2E` in all 10 scenes; now on-brand.
- **Research bubbles** rebuilt on teal/coral/olive (removed three maroon-red gradients that clashed).
- **Globe gradient** shifted from cold sky-blue to a teal-tint that belongs to the palette.
- **Emoji bell → SVG line icon** across all 9 topbars (consistent with the icon set; OS-independent).
- **Onboarding personas realigned** to the four real audiences from the strategy deck: Academic
  Researcher · Alt-Meat Startup · Flavor / Ingredient Co. · GFI / Funder (dropped off-strategy "Chef").
- **Dashboard now fronts all 5 domains** — added Toolbench + Simulate cards (previously only Map/Oracle/
  Research had a home entry point).
- **Simulate marked "Preview"** — it's the future-facing element; honest framing for the validation demo.
- **Molecular names set in monospace** in the database table — small move, real analytical-instrument credibility.

**Round 2 — dashboard visual upgrade (2026-07-01)**
Round 1 read as too subtle (its changes sat on non-default scenes and small elements), so this round
targets the default dashboard for immediate visible impact:
- **Per-domain color accents** — each of the 5 cards carries its domain color as a left border + a
  tinted icon chip (Map teal · Oracle deep-teal · Research coral · Toolbench olive · Simulate sage).
- **Hover-lift cards** — cards raise with a shadow on hover (`translateY(-3px)` + `--shadow-lg`).
- **Hero upgrade** — added an eyebrow ("MeatCODE · your workspace") and a 4-metric stat strip
  (1,000+ Sources · 374 Researchers · 89 Organizations · 5 Domains); numbers set in monospace.
- **Accented "For you" cards** — coral left border + hover lift, matching the card language.

_Note: these changes were applied and markup-verified but not yet visually rendered — the Claude-in-Chrome
extension was disconnected and the sandbox has no browser. Reconnect it to screenshot-verify future passes._

**Deliberately deferred (need Lior's sign-off — structural, not cosmetic)**
- Collapse the two competing nav systems (top domain bar vs. bottom dock overlap on Map / Database / For You).
- Wire cross-domain links (Oracle answer → open in Database / Map; Map expert → their papers).
- Roll out a second typeface for body/data (keep Varela Round for brand + headings).

**To promote v8 to canonical:** superseded by v9 below — promote v9 instead.

---

## v9 — `MeatCODE_mockup_v9.html` · v8 polish forward-ported onto the newer canonical (2026-07-08)

Between v8 and now, other sessions advanced the canonical `app/meatcode_mockup.html` well past v8 — it's the
version the Render site serves, and now includes a **Database** scene (Molecules/Experts/Companies/Sources
with live filter/sort + XLSX export), a full **Simulate/Prediction** engine, **Toolbench moved inside
Research**, Oracle history, and a live company card. That file never received the v8 polish. **v9 = a copy of
the current canonical with the v8 polish re-applied**, adapted to the new IA:

- Avatar wine→teal (18 leftover `#7E2E2E`), bell emoji→SVG (9 topbars), globe → teal, bubbles → teal/coral/olive.
- Onboarding personas realigned to the 4 real audiences (Academic · Alt-Meat Startup · Flavor/Ingredient Co. · GFI/Funder).
- Dashboard upgrade — eyebrow + a **real-corpus** stat strip (818 Sources · 799 Molecules · 374 Experts · 5
  Domains), per-domain color-accented hover-lift cards now fronting **all 5 domains** (Map · Oracle · Research ·
  **Database** · **Simulate**), each routing on click; accented "For you" cards. (v8's Toolbench/Simulate cards
  became Database/Simulate here, since Toolbench folded into Research.)

**Deployment-safety verification (2026-07-08) — v9 is safe to promote + deploy:**
- All **8 `<script>` blocks byte-identical** to canonical → no JS touched.
- Every **`fetch()` / `API_BASE` / `/api/…` line identical** → frontend↔API contract unchanged; the same-origin
  `API_BASE` guard fix is intact (Database/Experts/Companies won't fall back to "offline").
- **No new external dependencies** (same d3 + xlsx CDNs).
- Every diff hunk is cosmetic (CSS + dashboard/persona HTML + per-scene avatar/bell). Markup balanced
  (11/11 sections, 986/986 divs); 0 inline-script syntax errors.
- Promotion = overwrite `app/meatcode_mockup.html` (same served path) → server code, routing and API untouched.
- Minor cosmetic-only caveat: dashboard icon tints use CSS `color-mix()` (supported in all current browsers;
  degrades gracefully if not). Not browser-rendered yet — reconnect Claude-in-Chrome to screenshot-verify.

**To promote v9 to canonical + live:** replace `app/meatcode_mockup.html` with `MeatCODE_mockup_v9.html`, then run `deploy.command`.

## Parallel exploration — `meatcode_lean_v1.html` (2026-07-07)

A separate, deliberately **less-busy** direction (not a polish of the canonical): collapses the 5 domains into
**4 categories — Home / Oracle / Data / Map**, each a chooser→refine→detail funnel, single top nav (dock
retired). Kept as a design study; **v9 remains the rich "north-star" product.**
