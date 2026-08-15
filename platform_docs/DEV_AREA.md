_Last updated: 2026-08-15 · Fullstack Engineer · documented the feature/screen REGISTRY (schema v2), the date + location convention, toggle semantics, and the register-a-new-entry recipe · prev: Advisory · what the Dev Area is, how it's gated, how to add to it_

# The Dev Area — Lior's internal workbench

## What it is

The Dev Area (`app/dev/`) is a private zone inside the platform where half-built things live
**visibly** instead of invisibly. Before it existed, work-in-progress was scattered: a knowledge-graph
explorer in `kg/`, screen designs in `UI-UX Designer/`, decision docs in `platform_docs/`, and ideas
that existed only in chat. The Dev Area puts them all behind one door so Lior (and Daniel, on the dev
site) can walk through what's coming without any of it leaking into the public product.

It is a **hub page with five sections**:

| Section | What goes in it |
|---|---|
| **Features** | The **registry** of every flagged feature — what it is, when it was added, where it lives, and a Dev/Prod toggle each. |
| **Screens** | The same registry, filtered to `kind: "screen"` — each screen also carries its **destination** (where it lands in the product when its switch goes ON). |
| **Documents** | Links into the docs that explain the in-progress work (`platform_docs/`, decision records). |
| **User screen-flow** | The scenario/screen-flow work (A2) — how a user actually moves through the product. |
| **Versions** | Promoted production snapshots (read-only on hosted dev; rollback runs from the Mac). |

---

## The registry (`Release Center/features.json`, schema v2)

Every feature **and** every screen is one entry in `Release Center/features.json`, under the
top-level `flags` object. One entry answers three questions Lior asks constantly: *what is it*,
*when did it arrive*, *where in the product does it live* — plus it carries the switch that turns it
on or off.

```json
"attach_button": {
  "label":       "Attach button",
  "description": "Attach a data file or paper to an Oracle question (client-side preview).",
  "kind":        "feature",            // "feature" | "screen"
  "added":       "2026-08-15",          // YYYY-MM-DD, or "unknown" — never a guess
  "updated":     "2026-08-15",          // optional, last material revision
  "status":      "preview",             // "live" | "preview" | "placeholder"
  "where": {
    "screen": "Oracle",
    "spot":   "Ask box, immediately left of the mic",
    "file":   "app/meatcode_mockup.html"
  },
  "note":        "optional caveat or known issue",
  "dev":  true,
  "prod": false
}
```

Screen entries add two more fields:

```json
  "destination": "Research tile → Analytics",   // where it lands in the product when ON
  "url":         "/app/dev/analytics.html"
```

**Conventions**

- **`added` comes from `AGENT_UPDATE_LOG.md`**, not from memory. If the log has no date for something,
  write `"unknown"` — an invented date is worse than an admitted gap.
- **`where.spot` must be findable by a human in ten seconds**: *"top bar, immediately right of
  Inventory"*, *"Ask box, left of the mic"*. Not *"in the header area"*.
- **`status` is an honesty field**, the same rule as the placeholder rule below. `live` = real and
  working; `preview` = works but isn't backed by real data or a real algorithm, and says so on screen;
  `placeholder` = illustrative only.
- **`destination` is Lior's decision, per screen** — some screens land on a Research tile, some become
  a top-nav tab, some stay Dev-Area-only forever (the Versions screen, for example).
- **Backward compatibility is load-bearing.** `dev` and `prod` are the only behavioural fields. The
  server reads them (`load_flags()`), `GET /api/flags` reduces each entry to one boolean for the
  current `APP_ENV`, and the app turns every ON flag into a `ff-<key>` class on `<body>`. Everything
  else in an entry is descriptive metadata that only the Dev Area hub and the Release Center render.
  A top-level `_schema` block documents the fields inline; `save_flags()` preserves it on write.

## What a toggle actually does

Flipping **Dev** or **Prod** in the hub `POST`s to `/api/flags/set`, which rewrites that one boolean
in `features.json` and leaves every other field untouched. Nothing about the running site changes at
that instant:

1. The write lands in `Release Center/features.json` in the repo (committed config, not a secret).
2. The change reaches the **dev site** on your next `deploy-dev` — that server then serves
   `ff-<key>` for whatever `dev` now says.
3. It reaches **production** only via `promote-to-prod`, and only for what `prod` says.

**Writes are Mac-only, by design.** `/api/flags/set` and `/api/flags/upsert` are gated on
`_local_admin_ok()` — `RELEASE_CENTER=1` (set only by `release-center.command`) **and** a loopback
caller. Anywhere else they return 404. The reason is not paranoia: a hosted Render box has an
ephemeral filesystem and no git, so a write there would be silently lost on the next restart and
never reach the repo. On the hosted dev site the hub therefore renders the toggles disabled behind
the banner *"Read-only here — flip features on your Mac (release-center.command or press H), then
deploy-dev"*.

## Register a new feature or screen

**From the UI (preferred, local cockpit only)**

1. Start the cockpit: double-click `release-center.command` (or `run_oracle.command` for read-only).
2. Open the Dev Area → **Features** → **“+ Add a new entry to the registry”**.
3. Fill key, name, kind, status, what-it-is, and the three `where` fields (screen · spot · file);
   for a screen also destination + URL. Leave *Added* blank to stamp today.
4. **Register it** → `POST /api/flags/upsert` writes the entry (`dev: true`, `prod: false`) and the
   table re-renders. The same form updates an existing entry — pass the same key and only the fields
   you want changed; everything else is preserved.
5. Gate the thing itself on `body.ff-<key>` in CSS, or `document.body.classList.contains('ff-<key>')`
   in JS. **Use the exact key** — an underscore key does not match a hyphenated CSS selector.
6. `deploy-dev` to see it on staging.

**By hand** — add the same object to `Release Center/features.json` directly. Keep `dev`/`prod` and
fill in `kind`/`added`/`status`/`where`; the hub renders whatever is there.

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
2. **Register it** (`kind: "screen"`) via the hub's *Add a new entry* form or by hand in
   `Release Center/features.json` — with its `added` date, `where`, `status`, `destination` and `url`.
   The hub's **Screens** section renders itself from the registry, so there is no card to hand-write:
   register it and it appears, with its own Dev/Prod toggle.
3. **Say what it is on the screen itself** — see the placeholder rule below.
4. Note it in your `AGENT_UPDATE_LOG.md` entry so the Coordinator can pick it up (and so the next
   agent has a real date to put in `added`).

The Dev Area zone as a whole is still gated by the single `ff-dev_area` class on the button; each
screen's own flag decides whether it is ON in each environment (rows that are OFF for the current
environment render greyed out), and its `destination` records where it lands in the product.

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
