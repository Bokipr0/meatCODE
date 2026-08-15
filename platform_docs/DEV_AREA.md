_Last updated: 2026-08-15 · Advisory · what the Dev Area is, how it's gated, how to add to it_

# The Dev Area — Lior's internal workbench

## What it is

The Dev Area (`app/dev/`) is a private zone inside the platform where half-built things live
**visibly** instead of invisibly. Before it existed, work-in-progress was scattered: a knowledge-graph
explorer in `kg/`, screen designs in `UI-UX Designer/`, decision docs in `platform_docs/`, and ideas
that existed only in chat. The Dev Area puts them all behind one door so Lior (and Daniel, on the dev
site) can walk through what's coming without any of it leaking into the public product.

It is a **hub page with four sections**:

| Section | What goes in it |
|---|---|
| **Features** | Experimental features and their current state — what's behind each flag, what's ready to promote. |
| **Screens** | Work-in-progress screens: the **Knowledge Graph** explorer (embeds `kg/kg_explorer.html`), the **Meat Fingerprint** placeholder, the **Analytics zone** (GC-MS / HPLC / Olfactory / NMR / Spectroscopy). |
| **Documents** | Links into the docs that explain the in-progress work (`platform_docs/`, decision records). |
| **User screen-flow** | The scenario/screen-flow work (A2) — how a user actually moves through the product. |

It is a workbench, not a product surface. Nothing in it needs to be polished; everything in it needs
to be **honest** (see the placeholder rule below).

## How it's gated

The Dev Area sits behind the **`dev_area`** feature flag in `features.json` — **ON in dev, OFF in
prod**, like every other unfinished feature (see `platform_docs/RELEASE_CENTER.md` for how flags work).

- The app turns the flag into a **`ff-dev_area`** class on `<body>`.
- The **Dev Area button** in the main UI is hidden unless `body.ff-dev_area` is present — so on the
  public production site there is no button, no hint, no route advertised.
- On the staging site (`meatcode-dev`) and the local cockpit the flag is on, so the button shows and
  the whole zone is reachable.
- Rule of thumb: **the Dev Area flag stays OFF in prod, always.** Individual features graduate out of
  the Dev Area by getting their *own* flag flipped on for prod — the Dev Area itself never ships.

## How to add a new screen to the Dev Area

1. **Build the screen** as a file in `app/dev/` (self-contained HTML, same conventions as the rest of
   `app/`). If it wraps an existing artifact (like the KG explorer), embed it rather than duplicating it.
2. **Add a card for it** in the Dev Area hub's **Screens** section, with a one-line honest description
   of what state it's in (working / partial / placeholder).
3. **If the screen is itself an experiment** that might one day go to prod, give it its own entry in
   `features.json` now (dev: true, prod: false) — cheaper than retrofitting the flag later.
4. **Say what it is on the screen itself** — see the rule below.
5. Note it in your `AGENT_UPDATE_LOG.md` entry so the Coordinator can pick it up.

No backend registration is needed — the hub is just links/cards; the gate is the one `ff-dev_area`
class on the button and the zone.

## The placeholder rule (non-negotiable)

**Any screen that isn't backed by real data or a real algorithm must say so, on the screen itself,
where a viewer can't miss it.** A visible label like *"Placeholder — illustrative only, not real
data"* at the top of the screen, not buried in a tooltip.

Why this is a hard rule: 2026 is the validation year, and the project's credibility with external
reviewers (WUR, P1 experts, Daniel's stakeholders) rests on never letting a mock-up be mistaken for a
capability. This is the same principle as the GC-MS "honest preview" decision and the
synthetic-simulation labelling requirement in `MVP_BOARD.md` — the Dev Area just applies it to
internal screens too, because dev-site screenshots have a way of ending up in decks.

Current placeholders under this rule: the **Meat Fingerprint** screen (schema not yet defined — A1)
and any Analytics-zone instrument panel not yet wired to data.
