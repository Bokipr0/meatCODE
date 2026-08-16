_Last updated: 2026-08-16 · Advisory · new — architecture, data flow, error handling, latency, phasing, metrics and open decisions for wiring the Maillard chemistry simulator into MeatCODE_

# Maillard simulator — integration design of record

**What this document is.** Lior has a working Maillard chemistry simulator: a Docker prototype that
takes precursors (amino acids, sugars, lipids) plus process conditions (temperature, time, pH, water
activity) and predicts aroma compounds with ppb yields, a confidence figure, across 16 reaction
families, with Monte-Carlo uncertainty. A run takes **1–10 seconds**. This doc says how it gets into
MeatCODE without breaking anything, what happens when it breaks, what's realistic before 31 Aug, and
which calls Lior and Daniel still have to make.

**What this document is not.** It is not the simulator's science documentation, and it does not claim
the simulator is validated. Where I'm guessing, I say "guess".

**Who is doing what right now (2026-08-16, parallel run):** UI/UX is producing
`UI-UX Designer/maillard_sim_wireframe.html`; Full-Stack is producing `server/maillard/CONTRACT.md`
+ `server/maillard/adapter.py`, an `/api/simulate` proxy, a `maillard_sim` feature flag, and a second
(disabled) service block in `render.yaml`. Advisory owns this document and `MVP_BOARD.md`.

---

## 0. The one constraint that shapes everything

Production MeatCODE is a Render web service declared in `render.yaml` as `runtime: python`, running
a single stdlib `ThreadingHTTPServer` (`server/meatcode_server.py`). **That process cannot start a
Docker container.** There is no Docker daemon inside a Render `runtime: python` service, and the
filesystem is ephemeral. So there is no version of this where the existing server "just runs the
simulator".

That leaves exactly two shapes, and we should build both:

1. **Separate service.** The simulator ships as its own Docker image, deployed as its own Render
   service (`runtime: docker`), and the existing server talks to it over HTTP.
2. **Dev-only local.** On Lior's Mac, the simulator runs as a local container (or even a CLI call),
   and the same `/api/simulate` endpoint points at `http://localhost:<port>` instead.

The MeatCODE server is the only thing the browser ever talks to. It authenticates the request (the
existing shared-password gate), then proxies. Same-origin, so **no CORS, no second password, no
credentials in the browser**. The simulator service is never exposed to the public internet with a
route the browser knows about.

---

## 1. System diagram

```
                      ┌──────────────────────────────────────────┐
   Lior / reviewer    │  BROWSER — app/meatcode_mockup.html      │
   in a browser  ───► │  #simulate scene                         │
                      │                                          │
                      │  gated on  body.ff-maillard_sim          │◄── Release Center
                      │  (flag OFF ⇒ old synthetic demo,         │    features.json
                      │   clearly labelled "synthetic")          │    dev:true / prod:false
                      └────────────────┬─────────────────────────┘
                                       │ same-origin fetch
                                       │ POST /api/simulate   {precursors, conditions}
                                       │ GET  /api/simulate/{run_id}      (poll)
                                       ▼
        ┌──────────────────────────────────────────────────────────────┐
        │  MeatCODE server — server/meatcode_server.py (Render, python)│
        │  ┌────────────────────────────────────────────────────────┐  │
        │  │ shared-password gate  (already exists, unchanged)      │  │
        │  ├────────────────────────────────────────────────────────┤  │
        │  │ flag check: maillard_sim ON for this APP_ENV?          │  │
        │  │   NO  → 404, as if the endpoint doesn't exist          │  │
        │  ├────────────────────────────────────────────────────────┤  │
        │  │ server/maillard/adapter.py                             │  │
        │  │  · validate input against CONTRACT.md                  │  │
        │  │  · cache lookup (hash of the normalised formulation)   │  │
        │  │  · run registry: run_id → queued|running|done|error    │  │
        │  │  · call the simulator, with a timeout                  │  │
        │  └───────────────┬──────────────────────────┬─────────────┘  │
        └──────────────────┼──────────────────────────┼────────────────┘
                           │                          │
       MAILLARD_URL set    │                          │  MAILLARD_URL unset / localhost
       (hosted path)       ▼                          ▼  (dev-only local path)
   ┌───────────────────────────────────┐   ┌──────────────────────────────────────┐
   │ Maillard service — Render         │   │ Local Docker container on the Mac    │
   │ runtime: docker, own image        │   │   docker run -p 8900 maillard:latest │
   │ POST /simulate  → results JSON    │   │      …or a direct CLI subprocess     │
   │ GET  /health                      │   │ Only reachable from localhost        │
   │ Private, only the MeatCODE        │   │ Never part of the public deploy      │
   │ server calls it                   │   │                                      │
   └───────────────────────────────────┘   └──────────────────────────────────────┘
                           │                          │
                           └──────────┬───────────────┘
                                      ▼
                     results: [{compound, ppb, confidence,
                                reaction_family, ci_low, ci_high}, …]
                     + run metadata (seed, model version, runtime_ms)
```

**Where the flag gates it — three places, all of them:**

| Layer | What the flag does when OFF |
|---|---|
| Browser (`body.ff-maillard_sim`) | The "Predict reaction" button and the results panel are not rendered. `#simulate` shows the existing synthetic demo with its synthetic label. |
| Server route | `/api/simulate` returns **404**, not 403 — an off feature should look absent, not forbidden. |
| Deploy (`render.yaml`) | The second service block ships **disabled/commented**. No second service is billed until someone deliberately enables it. |

The flag lives in `Release Center/features.json` as `maillard_sim`, `dev: true` / `prod: false`, per
the Dev Area convention. It graduates to prod by flipping `prod` and running `promote-to-prod` — the
same path every other feature takes.

---

## 2. Data-flow walkthrough — the whole journey, hop by hop

The journey Lior described: **Research → Juice/Lipid → molecule corpus → select molecules →
"Predict reaction" → results → save/compare/iterate.**

**Step 1 — Research → Juice or Lipid.**
User clicks a Research tile. Nothing new happens; these scenes already exist. *User sees:* the
existing Research area.

**Step 2 — Molecule corpus.**
The scene lists molecules from Neon via the existing `GET /api/molecules` (server → Neon → server →
browser). This is real data — 799 molecules, categorised, with CAS on 110 of them. *User sees:* a
filterable table they already know.

**Step 3 — Select molecules as precursors.**
Selection is **client-side only**. The user ticks molecules; the browser holds them in a "formulation"
object. Nothing is sent anywhere yet. This reuses the handoff-bus pattern from the screen-flow spec
(`UI-UX Designer/SCREEN_FLOWS_user_journeys.md`) — the selected set travels to `#simulate` as carried
context, with a visible carry banner naming what came across.

> **Honest gap, name it in the UI.** The molecule corpus is a *volatiles* library — mostly reaction
> **products**, not reaction **precursors**. A simulator wants cysteine, ribose, glucose, thiamine,
> specific lipids. The corpus is thin on exactly those. Two options, and Lior has to pick:
> (a) restrict selection to molecules the simulator actually accepts as inputs (small, honest,
> possibly frustrating), or (b) let the user pick anything and have the adapter reject unknowns with
> a clear message. I recommend **(a) with a visible "usable as a precursor" filter** — a UI that
> only offers valid moves beats one that offers everything and then says no.

**Step 4 — Conditions.**
The `#simulate` scene collects temperature, time, pH, water activity, and whatever else
`CONTRACT.md` defines. Each field carries its valid range, shown up front, not discovered by error.
*User sees:* sliders/inputs with the range printed next to them.

**Step 5 — "Predict reaction".**
Browser `POST`s to `/api/simulate` with `{precursors:[…], conditions:{…}}`. Same-origin, so the
existing session cookie/basic-auth carries automatically.

**Step 6 — Server: gate, validate, cache.**
In order: password gate (existing) → flag check → schema validation against `CONTRACT.md` → compute
a hash of the *normalised* formulation (sorted precursors, rounded conditions, simulator version) →
cache lookup. On a cache hit, the server returns the stored result immediately with
`"cached": true` and the timestamp of the original run. On a miss, it registers a `run_id` and
returns `202 {run_id, status:"running"}`.

**Step 7 — Server → simulator.**
The adapter calls the simulator over HTTP (hosted) or locally (dev), with a hard timeout. The
MeatCODE server stays responsive throughout — it's a `ThreadingHTTPServer`, so one slow simulation
doesn't block the Oracle or the molecule endpoints. (This is worth stating explicitly because it's
the property that makes the whole design safe.)

**Step 8 — Browser polls.**
`GET /api/simulate/{run_id}` every ~700 ms. Returns `{status:"running", elapsed_ms}` until done, then
the full result. Polling rather than streaming because the endpoint is a plain stdlib handler and the
run is short — SSE would be more elegant and is not worth the complexity here.

**Step 9 — Results.**
*User sees:* a table/chart of predicted compounds with ppb yield, a confidence value, the Monte-Carlo
interval, and the reaction family each came from. Plus, unmissable at the top: **what this is** —
a mechanistic model's prediction, not a measurement — and the simulator version and run seed. Where a
predicted compound exists in the MeatCODE corpus, its name links to `#molecule-detail`. That link is
the thing that makes this feel like *MeatCODE* rather than a bolted-on calculator.

**Step 10 — Save / compare / iterate.**
Save goes to `localStorage` (`mc_saved_simulations_v1`), same as every other saved thing in the app —
because the site is behind one shared password and **there is no per-user identity to key a
server-side store to**. Compare = two saved runs side by side, client-side. Iterate = change one
condition and re-run; the cache makes the *unchanged* neighbours instant.

---

## 3. Error handling and edge cases

The rule underneath all of these: **never show a number the system isn't sure of, and never blame the
user for something the system did.**

| Case | What the system does | What the user is told |
|---|---|---|
| **Simulator service down / unreachable** | Adapter's HTTP call fails or `/health` is red. Server returns `503` with `{error:"simulator_unavailable"}`. No retry storm — one retry after 1 s, then stop. The `#simulate` scene falls back to the labelled synthetic demo. | *"The reaction simulator is offline right now. What you're seeing below is the synthetic demo, not a prediction."* Plus a Retry button. Never a spinner that never ends. |
| **Invalid precursor combination** (simulator accepts the schema but the chemistry is meaningless — e.g. no amino donor, so no Maillard) | The simulator should return a structured refusal, not zeros. The adapter passes it through as `422 {error:"invalid_formulation", reason:…}`. If the simulator instead returns an empty result set, the adapter treats empty-as-refusal and says so rather than rendering an empty table. | *"This combination can't produce a Maillard reaction — there's no amino donor in your selection. Add an amino acid or a peptide source."* Concrete, and it names the fix. |
| **Out-of-bounds parameters** (pH 14, 400 °C, negative time) | Rejected at the **server** before the simulator is called, against the ranges in `CONTRACT.md`. `400 {error:"out_of_range", field:"temperature_c", min:…, max:…}`. The browser also prevents them at input time — but the server never trusts the browser. | Inline, on the offending field: *"Temperature must be between 60 and 250 °C. The model isn't calibrated outside that range."* The second sentence matters — it explains *why*, which builds the right mental model. |
| **In-range but extrapolating** (technically allowed, but far from any calibration data) | Not an error. The result renders with a degraded-confidence badge. Whether the simulator itself reports this is **unknown to me — a question for whoever built it.** If it doesn't, we should not invent the badge. | *"These conditions are at the edge of the model's calibrated range — treat the numbers as directional."* Only if the simulator actually gives us that signal. |
| **Timeout > 30 s** | Adapter kills the call at 30 s. Run marked `error: timeout`. Poll returns it; the browser stops polling. Nothing partial is displayed — a half-finished Monte Carlo is not a result. | *"This run took longer than 30 seconds and was stopped. Try fewer precursors or a shorter reaction time."* If timeouts turn out to be common, that's a simulator-side problem to fix, not a message to soften. |
| **Two users at once** | `ThreadingHTTPServer` handles concurrent requests already. The added risk is the *simulator* — a single container may be single-threaded. The adapter enforces a **concurrency limit (start with 2)**; requests beyond it queue with `status:"queued"` and a position. | *"One simulation is already running — yours starts in a moment."* With the queue position. Honest and calm beats a silent 8-second wait. |
| **Stale / cached result** | The cache key includes the **simulator version**. A new simulator version invalidates every prior key automatically — no stale science can survive a recalibration. Cached results carry `cached:true` and the original run timestamp. | A quiet line under the results: *"Cached result from 14 Aug, simulator v0.3. Re-run to recompute."* With a Re-run button that bypasses the cache. Never hide that a result is cached — a user who tweaks an input and gets a suspiciously instant answer will assume the app is broken. |
| **Simulator returns malformed JSON** | Adapter validates the response shape too, not just the request. Bad shape → `502 {error:"bad_simulator_response"}`, full payload logged server-side. Nothing half-parsed reaches the UI. | *"The simulator returned something we couldn't read. This has been logged."* |
| **Neon asleep while the molecule corpus loads** | Unrelated to the simulator but it happens in the same journey. Existing behaviour: first query wakes it in a few seconds. | Existing loading state; no change needed. |

---

## 4. The latency question, answered honestly

**The conflict, stated plainly.** The product brief says "<3 s feels instant". The simulator takes
**1–10 s**. Those are not the same number and no amount of UI polish makes a 10-second Monte-Carlo
run into a 3-second one. Anyone who tells you otherwise is describing an animation, not a simulation.

**What's actually true about the two numbers.** "<3 s feels instant" is itself sloppy: nothing above
about 1 s feels instant to a human. What research on perceived performance actually supports is
roughly — under 100 ms feels instantaneous, up to ~1 s keeps the user's flow of thought unbroken, and
**up to ~10 s keeps their attention if and only if you show honest progress**. Past 10 s, they leave
and do something else. So the simulator's 1–10 s sits precisely in the band where *feedback quality*
decides whether it feels acceptable. This is the real target, not "<3 s".

**What to do, in priority order:**

1. **Submit → poll, never a blocking request.** Already in the design. The user gets an immediate
   `202` and a run id. The app is never frozen. This is the single biggest win.
2. **Show real progress, not a generic spinner.** If the simulator can report Monte-Carlo iteration
   count or stage ("initialising → 16 reaction families → sampling 500 draws → aggregating"), stream
   it into the poll response and show it. **Real** progress. If the simulator can't report progress,
   show elapsed time and the reaction families being evaluated as static text — informative, and not
   a lie.
3. **Cache identical formulations.** Hash the normalised inputs + simulator version. During a demo,
   the second showing of the same formulation is instant, legitimately. During iteration, going back
   to a previous formulation is instant. This is the highest-value optimisation for the 31 Aug demo
   specifically, because a demo re-runs the same thing repeatedly.
4. **Pre-warm the demo path.** Before the 31 Aug demo, run the 3–5 formulations that will be shown so
   they're all cached. Legitimate — the cache is real and labelled as cached. **What makes it
   legitimate is that the label stays on.**
5. **Fill the wait with something useful.** While the simulation runs, show the selected precursors,
   what the 16 reaction families are, and the corpus papers relevant to those precursors. The wait
   becomes reading time instead of dead time. Cheap to build, and it makes MeatCODE look like a
   knowledge product rather than a calculator with a loading bar.
6. **Set expectation up front.** The button can say *"Predict reaction (takes ~5 s)"*. Told in
   advance, 8 s is fine; unannounced, 4 s feels broken.

**What NOT to fake — explicitly:**

- **Do not show a fake progress bar** that animates on a timer independent of the actual run. It will
  desynchronise from reality — finishing at 100% while still waiting, or jumping from 40% to done —
  and once a reviewer notices, everything else we say about honesty is worth less.
- **Do not stream partial Monte-Carlo results** as if they were final. Partial draws have wider
  uncertainty than the display would imply. Either show them *with* their honest (wide) interval, or
  not at all.
- **Do not pre-compute results and pass them off as live** for the demo. Caching is fine **because
  it says it's cached**; a hidden lookup table is not caching, it's a fake.
- **Do not lower the reported Monte-Carlo sample count to hit a latency target without saying so.**
  If we run 200 draws instead of 1000 to be fast, the confidence intervals change, and the results
  panel must state the draw count.

**Recommendation:** stop targeting "<3 s". Target **"immediate acknowledgement, honest progress, and
a median run under 5 s"**. Make that the written performance requirement and delete "<3 s" from the
brief, because a requirement nobody can meet is a requirement everybody ignores.

---

## 5. MVP scope and phasing

### Phase 1 — single simulation (the only phase with a real shot before 31 Aug)

- **In:** one formulation in, one result out. Precursor selection from a filtered corpus view;
  condition inputs with ranges; `/api/simulate` submit-and-poll through the proxy; results table with
  ppb, confidence, Monte-Carlo interval, reaction family; links from predicted compounds into
  `#molecule-detail`; all error states from §3; caching; behind `maillard_sim`, **dev ON / prod OFF**.
- **Explicitly out:** comparison, optimisation, history beyond `localStorage`, storing anything in
  Neon, user accounts, uploading custom precursors, any claim of experimental validation.
- **Honest prerequisite:** a **frozen input/output contract** (`server/maillard/CONTRACT.md`) and a
  simulator image that runs somewhere reachable. If the contract is still moving on 24 Aug, Phase 1
  does not land — the UI cannot be built against a shape that changes.

### Phase 2 — comparison

- **In:** run two or three formulations and see them side by side; diff the compound lists; "what
  changed when I raised the temperature 20 °C".
- **Out:** statistical significance between runs (Monte-Carlo intervals overlap constantly and we'd
  be inviting over-reading), automated interpretation of the difference.
- **Honest prerequisite:** Phase 1 stable **and** a decision on where saved runs live. Comparison over
  `localStorage` is buildable in a day; comparison over a shared server-side history needs identity,
  which we don't have. Also depends on the existing Flow-2 comparison work in the screen-flow spec —
  reuse it, don't rebuild it.

### Phase 3 — Bayesian optimisation ("find me conditions that maximise 2-acetylthiazole")

- **In:** an objective, a search over the condition space, a suggested formulation.
- **Out:** everything, for now.
- **Honest prerequisite:** this needs **tens to hundreds of simulator runs per optimisation**. At
  1–10 s each that's minutes to an hour of compute per query, on a service we haven't paid for yet.
  It also needs the simulator to be trustworthy enough that optimising *against* it means something —
  otherwise we're finding the maximum of a model's artefact. **This is a 2027 item.** Naming it in a
  roadmap is fine; scheduling it in 2026 is not.

### Phase 4 — history and collaboration

- **In:** durable run history, sharing a run with a colleague, annotating results.
- **Out:** everything until identity exists.
- **Honest prerequisite:** **per-user accounts.** The whole site is behind one shared password. There
  is no "who" to attach a history to. This is blocked on a product decision far bigger than the
  simulator, and it's the same block that pushed Oracle chat history client-side
  (`platform_docs/oracle_chat_history_design.md`).

### Recommendation for 31 Aug — plainly

**Phase 1, flagged, on demo data. Nothing more.**

Concretely, what I think should be true on 31 Aug:

- The Maillard simulator is wired end-to-end and works, **on the dev site**, behind `maillard_sim`.
- It runs on **3–5 pre-agreed demo formulations** whose results are cached and sanity-checked by
  someone who knows the chemistry (Lior, ideally reviewed by Daniel).
- Production stays **OFF**. The public `#simulate` scene keeps its synthetic demo with its synthetic
  label — which is what MVP_BOARD lane 6 already requires, and that requirement does not go away just
  because a real simulator now exists in the building.
- The second Render service either runs on the free tier for the demo window or is spun up for the
  day. **Do not add $7/mo of always-on infrastructure for a feature that is off in production.**

**And the thing I most want on the record:** B1 (deploy the v12.1→v12.7 backlog) and B2 (quarantine →
`relevance_llm` write-back) are still the critical path, and neither has moved. A month of built,
verified work is not live, and Daniel-rejected sources are still retrievable by the Oracle. The
Maillard simulator is more exciting than both. That is exactly why it is dangerous: it is the kind of
work that displaces unglamorous critical-path work without anyone deciding to. **If Maillard
integration and B1/B2 compete for the same hours before 31 Aug, B1 and B2 win.** A simulator inside an
undeployed app demos to nobody.

---

## 6. Success metrics

Measurable, with a stated way to measure them. Where we can't measure something yet, that's said.

**Speed**

| Metric | Target | How measured |
|---|---|---|
| Time to first acknowledgement (POST → `202`) | < 300 ms, p95 | Server-side timing in the adapter; logged per run |
| End-to-end run time, cold (no cache) | median < 5 s, p95 < 12 s | `runtime_ms` recorded per run |
| Cache hit → result | < 200 ms | Same log, `cached:true` runs |
| Cache hit rate during a demo session | > 60% | Ratio in the run log |
| Runs exceeding the 30 s timeout | < 1% | Count of `error:timeout` |

**Reliability**

| Metric | Target | How measured |
|---|---|---|
| Successful runs / total submitted | > 98% (excluding user-input rejections) | Run registry statuses |
| Simulator `/health` uptime during demo windows | 100% | Health poll every 60 s, logged |
| Runs producing a malformed response | 0 | `bad_simulator_response` count |
| Errors that reach the user as a raw stack trace or bare 500 | **0, non-negotiable** | Manual review of every error path before the demo |

**Accuracy vs lab data — and how we'd even know**

This is the honest part. **We currently have no way to measure this**, and we should stop pretending
otherwise the moment anyone asks.

- There is **no lab dataset in MeatCODE** to validate ppb predictions against. The corpus is
  literature; the molecule library has no measured yields under stated conditions.
- The realistic first measurement is **literature-derived**: pull, say, **20 published GC-MS results
  where the paper states precursors, conditions, and measured compound concentrations**, run the same
  formulation through the simulator, and score it. This is a genuine piece of work — probably 1–2
  weeks of extraction and curation, and it overlaps neatly with the claim-extraction work already
  recommended in `platform_docs/KG_DECISION.md`.
- The metric, once we can compute it: **rank correlation** (does the simulator get the *order* of the
  top aroma compounds right — Spearman ρ, target > 0.6 as a first bar) matters far more than absolute
  ppb error. Mechanistic models of this kind are usually order-of-magnitude tools. Reporting absolute
  error alone would make an actually-useful model look terrible.
- Secondary: **top-5 overlap** — of the five compounds the simulator ranks highest, how many appear in
  the paper's reported top five. Target > 3/5. Easy to explain to Daniel, which matters.
- Until that exists, every result carries the same label: **prediction from a mechanistic model, not
  validated against laboratory measurement.** That label is not a caveat we hope to remove quietly;
  it is the honest state, and it comes off only when there's a number to replace it with.

**User engagement** (with N≈5–15, treat all of this as signal, not statistics)

| Metric | Why it tells us something |
|---|---|
| Simulations run per session | 1 = they looked. 5+ = they iterated, which is the actual value hypothesis. |
| Iteration depth (runs that changed only one parameter from the previous) | The clearest evidence the tool supports thinking, not just demoing. |
| Saved / compared runs | Weak proxy for "I want to come back to this". |
| Clicks from a predicted compound into `#molecule-detail` | Tests whether the simulator↔corpus link is the differentiator we believe it is. |
| Expert reaction, mid-Sept P1 sessions | Structured question: *"Would you use this to choose your next experiment?"* — one open answer per reviewer beats any counter. |

---

## 7. Ownership and maintenance

| Thing | Owner | What that means in practice |
|---|---|---|
| **The simulator itself** (chemistry, 16 reaction families, kinetics, Monte-Carlo, calibration) | **Lior** (with Daniel as scientific reviewer) | Nobody else can judge whether a number is right. All chemistry changes originate here. |
| **The Docker image and its deployment** | **Full-Stack** | Builds the image, owns the Render service block, `/health`, resource sizing. |
| **The contract** (`server/maillard/CONTRACT.md`) | **Full-Stack, with Lior's sign-off on the fields** | The frozen boundary. Changing it is a versioned event, not an edit. |
| **The adapter + proxy** (`server/maillard/adapter.py`, `/api/simulate`) | **Full-Stack** | Validation, caching, timeouts, run registry, error mapping. |
| **The `#simulate` UI** | **UI/UX** | Wireframe → live scene, all states from §3, honest labelling. |
| **The flag and its prod state** | **Lior** | Only Lior flips `prod: true`, from the Mac. |
| **This document, phasing, scope discipline** | **Advisory** | Updated whenever a phase closes or a decision in §8 resolves. |

**How new calibrations propagate when lab data arrives — the loop:**

1. Lab data (WUR GC-MS, or literature-extracted ground truth) lands.
2. Lior recalibrates the simulator and **bumps its version string** — e.g. `0.3` → `0.4`. This is
   mandatory, not cosmetic.
3. New Docker image built and deployed to the Maillard service.
4. **Every cached result invalidates automatically**, because the version is part of the cache key.
   No stale science can survive a recalibration. This is the whole reason the version is in the key.
5. The adapter records the simulator version on **every** run, so any saved or screenshotted result
   can be traced to the model that produced it.
6. If the validation numbers from §6 improve, the results-panel label is updated to state what the
   model has now been checked against — with the specific number, not a vibe.
7. Advisory logs the recalibration in `AGENT_UPDATE_LOG.md` and updates this doc's phase status.

**A version string is the cheapest thing in this whole design and the one that prevents the worst
failure** — someone showing a stakeholder a number from a model that no longer exists.

---

## 8. Open decisions for Lior + Daniel

1. **Is the simulator validated enough to show externally in mid-Sept?**
   Internal on 31 Aug is low-risk — an internal audience understands "prototype". P1 experts in
   mid-Sept are flavour chemists who will read ppb values as claims. Options: (a) don't show it
   externally at all; (b) show it explicitly framed as "a model we're building, tell us if the
   chemistry is plausible" and harvest their critique as validation input; (c) show it as a
   capability. **My recommendation: (b).** It converts our biggest weakness — no validation data —
   into the exact thing we're asking experts for, and it's the only option where being unvalidated
   isn't embarrassing. (c) is the one that costs credibility we can't rebuy.

2. **Does a second Render service get paid for?**
   A `runtime: docker` service on Render's starter tier is roughly $7/mo, doubling the hosting bill.
   Options: (a) free tier, accepting 30–60 s cold starts — which stacks on top of a 10 s run and
   makes the first demo click feel broken unless it's pre-warmed; (b) paid starter, always on;
   (c) dev-only local on Lior's Mac, no hosted service at all until the feature graduates.
   **My recommendation: (c) until 31 Aug, then (b) only if the simulator is going into the mid-Sept
   external sessions.** Don't pay monthly for something that's off in production.

3. **Does simulation output get stored in Neon, or stay client-side?**
   Client-side (`localStorage`) is consistent with every other saved thing in the app and needs no
   identity. Neon storage would give durable history, cross-device access, and — the real argument —
   **a dataset of what people actually asked the simulator**, which is validation-year evidence we
   currently have none of. But it needs a table, a retention answer, and it partly reopens the
   anonymous-logging question already open as MVP_BOARD decision 3.
   **My recommendation: client-side for Phase 1; fold "store simulation runs" into the same yes/no as
   the anonymous question log** — they're the same decision wearing two hats, and deciding them
   separately will produce an inconsistent privacy story.

4. **Which precursors can a user actually pick?**
   Restrict selection to simulator-accepted inputs, or allow anything and reject on submit? (§2 step
   3.) This is a small UI decision with a large credibility consequence and it blocks the wireframe.
   **Needs Lior's answer this week.**

5. **Does the "<3 s" requirement get formally retired?**
   §4 argues it should be replaced with "immediate acknowledgement, honest progress, median under
   5 s". Someone has to actually strike it from the brief, or it will resurface as a failed
   requirement in a review.

6. **Does the simulator report its own extrapolation/confidence-degradation signal?**
   Not a Lior-and-Daniel decision so much as a fact I don't have. If yes, we surface it. If no, we do
   not invent it, and the results panel is quieter than we'd like.

7. **Do we accept the sequencing — B1/B2 before Maillard?**
   §5 says yes and says why. If Lior disagrees, that's a legitimate call, but it should be made out
   loud and written down, because the default failure mode is that the exciting work quietly wins and
   nobody notices the deploy backlog is now two months old.
