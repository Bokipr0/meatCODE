_Last updated: 2026-08-16 14:47 UTC · Advisory · decision + honesty note for the Oracle-demos & corpus-filter run_

# Oracle demos & corpus filter — decision + honesty note

**What this document is.** The Advisory record for the 2026-08-16 parallel run that turned four
reviewer-facing surfaces into working demos: dynamic Research corpus chips, a first-class Analytics
scene, a de-cluttered mockup, and four Oracle capability demos. It states the shared API contract,
the honesty rules that must hold before any of this is shown to a reviewer, where this run sits
relative to the critical path, and the exact click-paths to test each item once it is deployed to dev.

**What this document is not.** It is not a deploy sign-off and it does not reorder the spine. B1
(deploy the backlog) and B2 (quarantine → `relevance_llm` write-back) remain the critical path; this
run is demo-polish layered on top of them. Where I am describing an endpoint or shape a teammate is
still building in this same run, I say so and defer the exact wire details to that endpoint's own
contract when it lands — Full-Stack owns the wire shape, Advisory owns the framing.

---

## 1. What shipped this run

**Task 1 — Research sub-topic chips go dynamic (Juice / Lipid / Analytics).** The Research
sub-topic chips stop being hardcoded and instead live-query the Neon corpus through a new
`GET /api/corpus?phase=&topics=`. Each chip now reflects how many real, tagged sources actually sit
behind that taxonomy slug, so the Research area stops advertising depth the literature doesn't yet
have. This is the piece that most directly advances the Research / J4 planning flow: the same
endpoint powers the "Explore the lipid corpus" Oracle demo (task 4). The honest cost of making the
chips truthful is that some of them will read low or zero — which is the point, and is handled by the
empty/thin-state rule in §2.

**Task 2 — Analytics promoted to a first-class `#analytics` scene.** The Analytics view graduates
out of the Dev Area workbench into an in-product `#analytics` scene, reachable directly from the
Research "Analytics" tile (the `analytics` flag is already `dev:true / prod:true`, status *preview*).
It panels the analytical methods — GC-MS, HPLC, Olfactory, NMR, Spectroscopy. It is a **preview on
real-but-partial data**: GC-MS is backed by the Meaty Volatile Library; the other methods are much
thinner or planned. It must stay labelled *preview* until every panel is wired to real data (§2).

**Task 3 — Dev/staging banner removed from the mockup.** The "DEV · staging" ribbon is removed from
the mockup surface to de-clutter the demo and screenshots. This is cosmetic and low-risk: the banner
was `dev:true / prod:false`, so production never showed it and nothing about the public site changes.
The one honesty caveat (§2) is that dev/staging must still be distinguishable by its URL, since the
visual "this is not prod" cue is now gone. The `dev_banner` flag entry in `Release Center/features.json`
is now moot and can be retired by the Coordinator/Full-Stack in a follow-up — Advisory does not touch
the flag file in this run.

**Task 4 — Four Oracle starter chips become capability demos.** The four Oracle starter chips are
reworked from prompt-stuffers into signposted capability demos:
- **Maillard synthesis route** — a *grounded, cited* Oracle answer via `POST /api/ask`, shown next to
  a reaction schematic. The answer is real retrieval; the schematic is an illustrative pathway diagram,
  **not** simulator output (§2).
- **Explore the lipid corpus** — drives `GET /api/corpus` (same endpoint as the Research chips) to show
  what the corpus actually holds on lipids, with honest counts.
- **Predict with the simulator** — calls `POST /api/simulate`, which is **MOCK / synthetic** by default
  and must render the synthetic banner + disclaimer every time (§2). This is the one demo that is not
  real chemistry.
- **Compare molecules** — runs inline in the Oracle chat via `/api/compare` + `/api/molecules/{id}`
  (aliased as `/api/molecule-profile`), and **never navigates away** from the conversation.

### Shared API contract (one table)

| Endpoint | Method | New / reused | Powers | Honesty constraint |
|---|---|---|---|---|
| `/api/corpus?phase=&topics=` | GET | **new this run** (Full-Stack) | Dynamic Research chips (Juice/Lipid/Analytics) + "Explore the lipid corpus" demo | Returns **real** counts from Neon. A 0-count slug must grey out, not lie. Reflects the still-growing corpus (818 sources, ~40% tagged). |
| `/api/compare` | GET/POST | **new this run** (Full-Stack) | "Compare molecules" inline Oracle demo | Real molecule rows only. Respect `is_junk`. NULL chemistry fields render as "—", never fabricated. |
| `/api/molecule-profile/{id}` | GET | **new this run — alias of `/api/molecules/{id}`** | The per-molecule card inside Compare + inline profiles | Same live row as `/api/molecules/{id}` (`mentions_count`, `papers[]`); a convenience alias, not a second source of truth. |
| `/api/ask` | POST (SSE) | **reused** | "Maillard synthesis route" grounded-answer demo | Grounded + inline-cited; refuses when the corpus doesn't cover the question. The adjacent schematic is illustrative, not a computed result. |
| `/api/simulate` | POST (+ poll) | **reused** | "Predict with the simulator" demo | **MOCK by default** (`MAILLARD_MODE=mock`); every response is `synthetic:true` and carries a disclaimer. Behind `maillard_sim` (**OFF in prod → 404**). |

> The precise query params and JSON shapes for the two brand-new endpoints (`/api/corpus`,
> `/api/compare`) and the `/api/molecule-profile` alias are Full-Stack's to freeze in the server /
> its own contract as they land this run. This table is the **agreed behaviour and honesty
> boundary**, not the wire spec — where they differ, the endpoint's own contract wins on shape,
> this doc wins on framing.

---

## 2. Honesty rules that must hold

These are the non-negotiables. If any one of them slips, the run stops being an honest demo and starts
being a misleading one.

**1. The simulator demo is MOCK — always banner it, never present it as chemistry.**
"Predict with the simulator" calls `/api/simulate`, which runs in `MAILLARD_MODE=mock` by default:
deterministic pseudo-data derived from the request hash, with every response stamped `synthetic:true`
and carrying the disclaimer *"SYNTHETIC PLACEHOLDER — deterministic pseudo-data … Not a chemistry
simulation. Do not cite, export, or present as a result."* (`server/maillard/CONTRACT.md` §0 and §3;
`Release Center/features.json` → `maillard_sim`). The `maillard_sim` flag is **`prod:false`** — the
real Docker simulator does not exist in production, because a Render `runtime: python` service cannot
spawn Docker. Therefore:
- The results panel must render the synthetic banner + disclaimer on **every** mock response — no
  "clean" screenshot without it.
- ppb yields, confidence intervals and reaction-family shares from the mock backend are placeholders.
  They must never be cited, exported, or spoken about as if they were chemistry.
- This is consistent with MVP_BOARD lane 6 ("the `#simulate` scene must be visibly labelled
  synthetic") and A8 (integration is Phase-1-only, flagged, on demo data). A real simulator existing
  in the building does not change what production shows.

**2. The corpus chips must show honest empty/thin states.**
`/api/corpus` returns the real tagged-source counts, and the corpus is still growing and unevenly
tagged: of 818 sources only ~40% are tagged to canonical topics, and only 319/818 (39%) pass the
Oracle relevance gate. Several taxonomy slugs are sparsely tagged or empty. So:
- A **0-count chip greys out** (disabled, muted) rather than presenting itself as a live, populated
  filter. A chip that looks clickable but returns nothing is a small lie that a reviewer will catch.
- A **thin** chip (a handful of sources) should not be dressed up as a rich one — the count is the
  honest signal, show it.
- This is the same reality the knowledge-graph work already surfaced (A5: the roasted/nutty query
  "finds perfect chemistry, 0 papers" because the paper↔molecule bridge is thin). The chips must not
  paper over that gap; densifying the corpus (lane 2 / B2) is what fixes it, not the chip UI.

**3. The Analytics scene is a preview on real-but-partial data.**
The `#analytics` scene is *preview*, not a live analytical engine. GC-MS is backed by the Meaty
Volatile Library (real data); HPLC, Olfactory, NMR and Spectroscopy are thinner or planned
(`features.json` → `analytics`; Dev-Area rule A7: "panels not wired to data must carry placeholder
labels until they are"). So each panel carries an honest status: real-data panels say what they're
backed by, not-yet-wired panels say *placeholder / preview*. The scene keeps its **preview** label
until every panel is wired to real data. Promoting the scene into the product does **not** promote it
out of preview.

**4. The grounded-answer demo's schematic is illustrative.**
The "Maillard synthesis route" chip pairs a grounded, cited `/api/ask` answer with a reaction
schematic. The answer is real retrieval and refuses when the corpus doesn't cover the question. The
schematic beside it is a **representative pathway diagram**, not a computed or simulated route — it
must not be read as, or captioned as, simulator output.

**5. The dev banner removal must not erase the prod/staging distinction.**
With the "DEV · staging" ribbon gone from the mockup, the only cue that staging is staging is its URL.
That is acceptable (prod never showed the banner), but nobody should demo the dev site and let a
reviewer assume it is production, or vice-versa.

---

## 3. Scope discipline — where this run sits

**These four tasks are demo-polish and reviewer-facing capability signals.** They make MeatCODE
*show better*: the Research area stops over-claiming, the Oracle's four chips visibly demonstrate four
distinct capabilities, Analytics becomes a real destination, and the surface is cleaner. For the
internal 31 Aug demo and the mid-Sept P1 sessions, that is genuinely worth doing — a capability the
reviewer can't see is a capability that doesn't count.

**But this run does not reorder the spine.** Per MVP_BOARD and the 2026-08-16 broadcast, the critical
path is unchanged and unmoved:
- **B1 — deploy the v12.1 → v12.7 backlog.** `[CP]`, still `🔴`. A month of built, verified work is
  not live. **Everything in this run is invisible until B1 lands** — a great demo inside an undeployed
  app demos to nobody.
- **B2 — close the quarantine → `relevance_llm` write-back.** `[CP]`, still `🔴`. Daniel-rejected
  sources remain retrievable and citable by the Oracle. This is also what makes the corpus chips'
  counts *trustworthy* rather than merely *honest about being untrustworthy* — until B2 closes, a
  chip's count can include sources Daniel has already rejected.

The failure mode to name out loud: exciting, reviewer-facing work like this quietly displaces
unglamorous critical-path work without anyone deciding to. **If this run and B1/B2 compete for the
same hours, B1 and B2 win.** This run is worth shipping — it just ships *on top of* the spine, not
*instead of* it. (Same argument, same conclusion as `platform_docs/MAILLARD_INTEGRATION.md` §5.)

---

## 4. Reviewer-facing "what this is / what it isn't"

*A short block Lior can hand an external P1 user. Plain, honest, no hedging-by-omission.*

> **The Oracle** answers from MeatCODE's own literature corpus and cites the specific sources it used.
> When the corpus doesn't cover your question, it says so rather than guessing. It is grounded and
> cited — not a general chatbot dressed up as a science tool.
>
> **The Research corpus filter** reflects the real, still-growing literature we've collected. If a
> topic chip looks thin or greyed-out, that's the truth about our current coverage of that topic, not
> a broken screen. The corpus is being actively expanded; the counts you see are today's counts.
>
> **The reaction simulator** is a **labelled placeholder**. What it returns today is synthetic
> demo data — a stand-in for a real Maillard chemistry simulator we are integrating, not a chemistry
> result. Every simulator result is banner-marked as synthetic. Do not read the numbers as predictions.
>
> **The Analytics view** is an early **preview**. GC-MS is backed by our Meaty Volatile Library; the
> other methods (HPLC, olfactory, NMR, spectroscopy) are placeholders while we wire real data behind
> them. We're showing you the shape of the tool, not a finished analytical engine.
>
> In short: the Oracle and the literature are real and cited; the simulator and most of Analytics are
> honestly-labelled previews. We'd rather show you the seams than hide them — telling us where the
> thin parts are is exactly the feedback we want.

---

## 5. How to test each of the four (once deployed to dev)

*Click-paths assume the dev site is live (B1) and the relevant flags are ON in dev.*

**Task 1 — Dynamic Research corpus chips**
1. Open the dev app → **Research**.
2. Confirm the Juice / Lipid / Analytics sub-topic chips render **counts**, not static labels.
3. Click a well-tagged chip (e.g. a Lipid slug) → the filtered corpus view loads real sources.
4. Find a sparse slug → confirm it is **greyed/disabled** (0-count), not clickable-but-empty.
5. Network tab: confirm the chips call `GET /api/corpus?phase=…&topics=…` and that counts match the
   returned payload.

**Task 2 — First-class Analytics scene**
1. Research tile **Analytics** → confirm it routes to the in-product `#analytics` scene (not into the
   Dev Area).
2. Confirm the scene is **labelled *preview***.
3. Confirm the **GC-MS** panel names its backing (Meaty Volatile Library) and the HPLC / Olfactory /
   NMR / Spectroscopy panels carry **placeholder / preview** labels — none of them imply live data.

**Task 3 — Dev banner removed**
1. Load the dev mockup → confirm the "DEV · staging" ribbon is **gone**.
2. Confirm the top bar and layout render correctly with the ribbon removed (nothing overlaps the space
   it used to occupy).
3. Sanity-check: you can still tell dev from prod by the URL.

**Task 4 — Four Oracle capability demos**
1. Open **Oracle** → confirm four starter chips.
2. **Maillard synthesis route** → grounded, cited answer streams in + a schematic renders beside it;
   citations resolve to real sources; the schematic is not captioned as a simulation.
3. **Explore the lipid corpus** → `/api/corpus`-driven view of the lipid literature with honest counts.
4. **Predict with the simulator** → results render **with the synthetic banner + disclaimer visible**;
   confirm `synthetic:true` in the `/api/simulate` response and that ppb/confidence are labelled
   placeholder.
5. **Compare molecules** → a comparison card renders **inline in the chat** (via `/api/compare` +
   `/api/molecules/{id}` / `/api/molecule-profile`); confirm you **never navigate away** from the
   Oracle conversation and that NULL chemistry fields show "—" rather than invented values.

---

## Appendix — anchors this doc relies on

- Simulator MOCK / synthetic: `server/maillard/CONTRACT.md` §0 (mode table), §3 (`synthetic:true` +
  disclaimer); `Release Center/features.json` → `maillard_sim` (`prod:false`, mock default);
  `platform_docs/MAILLARD_INTEGRATION.md` §5 (Phase-1-only, prod OFF).
- Corpus thin/empty reality: `PROJECT_STATE.md` headline numbers (818 sources · ~40% tagged · 39%
  pass the relevance gate); `MVP_BOARD.md` lane 2, A5, B2.
- Analytics preview: `Release Center/features.json` → `analytics`; `MVP_BOARD.md` A7.
- Critical path unchanged: `MVP_BOARD.md` B1/B2; `TEAM_BROADCAST.md` (2026-08-16).
