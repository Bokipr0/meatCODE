# UI/UX Design Notes — v8 polish pass

_Art director: Claude · 2026-06-30 · base file: `app/meatcode_mockup.html` (identical copy at pass start)_

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

**Deliberately deferred (need Lior's sign-off — structural, not cosmetic)**
- Collapse the two competing nav systems (top domain bar vs. bottom dock overlap on Map / Database / For You).
- Wire cross-domain links (Oracle answer → open in Database / Map; Map expert → their papers).
- Roll out a second typeface for body/data (keep Varela Round for brand + headings).

**To promote v8 to canonical:** replace `app/meatcode_mockup.html` with this file (once approved), then push.
