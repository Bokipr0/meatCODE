# MeatCODE — 10-Minute Live Demo Run-of-Show

_Last updated: 2026-08-31 13:39 UTC · Advisory · 10-minute demo run-of-show_

> **What this is:** a segment-by-segment script for a **live walkthrough of the deployed MeatCODE site** (not slides), balanced across the full journey. Rehearse it against a timer. Every talking point is grounded in the **real backend** — grounded RAG over **~818 real sources**, **live corpus counts**, honest previews. **Do not overclaim.**
>
> **⚠️ Read the [Pre-Demo Checklist](#pre-demo-checklist) FIRST.** The three new endpoints (`/api/corpus`, `/api/compare`, `/api/simulate`) are **404 until deployed** — so the demo MUST run on **deployed staging** or **localhost**, not the current public prod site.

---

## At-a-glance timing (sums to 9:00 + 1:00 buffer ≤ 10 min)

| # | Segment | Scene / entry | Budget | Running |
|---|---------|---------------|--------|---------|
| — | **Opening hook** | `#oracle` (landing) | 0:30 | 0:30 |
| 1 | **Oracle** — grounded, cited answer | `#oracle` | 2:30 | 3:00 |
| 2 | **Research → live corpus** | `#research` → `#research-sub` | 1:45 | 4:45 |
| 3 | **Analytics** — GC-MS / NMR methods browser | `#analytics` | 1:15 | 6:00 |
| 4 | **Simulator** — Maillard (MOCK, synthetic) | `#simulate` · Predict (live) | 1:30 | 7:30 |
| 5 | **Compare** — inline molecule diff | Oracle chip → `/api/compare` | 1:00 | 8:30 |
| — | **Close** — the ask / what's next | `#oracle` | 0:30 | 9:00 |

**Route logic (minimal scene-jumping):** start on Oracle → Research → Analytics is one click from Research → Simulate → **land back on Oracle** for the live simulator beat, which sets up Compare (also an Oracle chip) → close on Oracle. You end where you started.

---

## Opening hook — 0:30

**Where:** you're already on the Oracle landing (`#oracle` is the default scene; the logo always routes here).

**Say (pick ~2 lines):**
- "MeatCODE is a source-backed research platform for meaty flavour chemistry. Everything you'll see is grounded in a curated corpus of ~818 real papers — not a chatbot guessing."
- "The thesis: meaty flavour should be engineered as **process flavour** — the cooking chemistry (precursor + lipid + matrix + heat), not just a flavour mix added at the end."
- "I'll walk the full journey in under ten minutes: ask the Oracle, narrow the live corpus, browse the measurement methods, run the simulator, and compare molecules."

**Fallback:** if the page is slow to load, this is your Neon warm-up moment — keep talking; the first query wakes the DB.

---

## Segment 1 — Oracle (grounded, cited answer) — 2:30

> The strongest journey. Give it the most time. This is the honest core: **grounded RAG, real citations, refuses when the corpus doesn't cover it.**

**Click-path:**
1. On `#oracle`, in the composer, either:
   - **type a real question** into the textarea (`#oracleTextarea`) and press **Enter** / **Ask** — e.g. _"What compounds drive the roasted, brothy note in cooked beef, and what's the evidence?"_; **or**
   - click the **"Maillard synthesis route"** starter chip (a **capability demo**) — it first draws a reaction-route schematic strip, then auto-asks a grounded, cited question.
2. Watch the answer **stream** in the thread: the phase label ("Digging the MeatCODE database…"), then **source pills** appear (coral, each with a `[id]`), then the answer text streams token-by-token, then related-molecule chips at the end.
3. **Click one citation pill** to show it opens the real source.

**What to say (2–3, grounded):**
- "Every answer is retrieved from our own corpus first — **~818 sources**, keyword/full-text search, gated to a relevance score of **≥ 60** — then the model is only allowed to answer **from those retrieved papers**, and it **cites the real source IDs**."
- "If the corpus doesn't cover something, it **says so** — 'the corpus doesn't cover this' — rather than fall back on training knowledge and make something up. That refusal is the point: it's the front-line guard against hallucination."
- "Notice the citations are clickable — you can open the paper behind any claim. This is built to be **checkable**, which is what reviewers and Daniel's sign-off process need."

**Honest caveat (say if asked about depth):** "Our own RAG eval flags that the cited claims are solid but the surrounding depth is still thin in places — that's exactly the corpus-trust work we're doing next."

**Time budget:** 2:30 (≈0:20 setup, ≈1:30 streaming + narration, ≈0:40 open a citation + follow-up beat).

**One-line fallback:** if streaming stalls or `/api/ask` errors, click into an already-answered chat in the **Oracle History** rail (left) and narrate that — the citations are still real.

---

## Segment 2 — Research → live corpus — 1:45

> The "these numbers are real, not decorative" beat. Chips re-query the actual corpus.

**Click-path:**
1. Click the **Research** nav chip (topbar) → lands on `#research`.
2. Click the **Juice** phase card (the water-based aroma phase) → routes to `#research-sub` (`mc_phase = juice`).
3. On `#research-sub`, the sub-topic cards each carry real **taxonomy slugs**; **3 are pre-picked**. **Toggle a couple** on/off (e.g. add **"Plant-juice volatiles"**, add **"Polar top-notes"**) — the **count line** (`0 sub-topics picked` → updates) and the **per-card count badges** re-render from a live `GET /api/corpus?phase=juice&topics=…` call. **Zero-count cards grey out.**
4. _(Optional, if time)_ breadcrumb back and pick **Lipid** to show a different phase's live counts (lipid-oxidation aldehydes, frying chemistry, etc.).
5. Point at **"Generate database →"** — "this builds a filtered database around exactly these topics."

**What to say (2–3, grounded):**
- "These aren't hardcoded numbers — each chip maps to a **real taxonomy slug**, and the counts you see re-query the **live corpus** every time I toggle one."
- "This is how a researcher narrows from a whole phase down to just the chemistry they care about — and the platform stays honest: a topic with **no sources shows a zero and greys out**, it doesn't fake coverage."
- "The taxonomy underneath is one governed 'bible' — 91 keywords across five branches — so the whole database sorts and filters the same consistent way."

**Time budget:** 1:45 (≈0:25 to Research + Juice, ≈1:00 toggling chips + narrating live counts, ≈0:20 gesture at Generate / Lipid).

**One-line fallback:** if `/api/corpus` 404s or hangs, the sub-topic cards still toggle visually — say "the counts you'd normally see here are a live corpus query; it's the endpoint that's still deploying" and move on.

---

## Segment 3 — Analytics (GC-MS / NMR measurements browser) — 1:15

> The new first-class `#analytics` methods browser. **Honest preview** — status chips are truthful.

**Click-path:**
1. From `#research`, click the **Analytics** phase card → routes to the in-product `#analytics` scene. _(If you're on `#research-sub`, use the breadcrumb: Research → Analytics card. You can also reach it via the Oracle "Explore the lipid corpus"-style flow, but the Research → Analytics card is the clean path.)_
2. Press the **GC-MS** method card — it carries the **"DATA EXISTS"** status chip — it multi-selects and pulls its live corpus slice into the results panel (`GET /api/corpus?phase=analytics&topics=gcms_topic,hs_spme_topic,gc_olfactometry`).
3. Press the **NMR** card — it carries the **"PLANNED"** status chip — it adds to the selection and the live counts update.
4. Point at the row of status chips: GC-MS **DATA EXISTS**, the rest **PLANNED**.

**What to say (2–3, grounded):**
- "This is the methods layer — the measurement families MeatCODE speaks. Click one and it pulls that method's **live slice of the corpus**."
- "The status chips are **deliberately honest**: only **GC-MS** has reference data today, via our **Meaty Volatile Library**. NMR and the others are **PLANNED** — they're pressable and they'll show you the literature we have, but we're not pretending there's an analytical engine behind them yet."
- "So this is a genuine **preview**: real corpus counts under every method, honest labels about what's actually backed."

**Time budget:** 1:15 (≈0:15 to Analytics, ≈0:50 press GC-MS + NMR + narrate, ≈0:10 status-chip honesty line).

**One-line fallback:** if the corpus call fails, the method cards still select — say "each of these is a live corpus query when deployed; the honest status chips are the real point here" and move on.

---

## Segment 4 — Simulator (Maillard, MOCK · synthetic) — 1:30

> Frame it honestly: **"a model we're building — tell us if the chemistry is plausible."** This is a hypothesis tool, **not real chemistry yet.**

**Click-path reality (updated 2026-08-31):** the `#simulate` scene's **"Predict outcomes"** button is now wired **live** to `POST /api/simulate` (MOCK backend, `synthetic:true`) and renders the mandatory **`SYNTHETIC — NOT A REAL SIMULATION`** banner + disclaimer. The Oracle **"Predict with the simulator"** chip runs the same live MOCK inline in the chat. Use the dedicated `#simulate` scene for this segment — it's the richer surface.

**Recommended click-path:**
1. Click the **Simulate** nav chip → `#simulate`. Show **"Set up your reaction"**: precursors (L-Cysteine × D-Ribose, editable amounts in **mM**), conditions (110 °C, 30 min, pH 5.5, Aw 0.85), matrix family, run mode. Read the credit line: **"Engine: Pablo Casares · PabloAMC/Maillard · 16-family SLR benchmark set · MeatCODE adapter layer."**
2. Press **"Predict outcomes"** → the live MOCK returns and fills the card: the predictability bar, the ranked **synthetic** compound table (meaty-forward for Cys×Ribose: 2-acetylthiazole, 2-furfurylthiol, bis(2-methyl-3-furyl) disulfide, 2-methyl-3-furanthiol, 2-acetyl-1-pyrroline…), off-notes, and the **`SYNTHETIC — NOT A REAL SIMULATION`** banner + disclaimer. Say the honest framing here.
3. *(Optional)* mention the same model is one click away inside the Oracle chat via the **"Predict with the simulator"** chip — but don't spend time; head to Oracle next for Compare.

**What to say (2–3, grounded + honest):**
- "This is a **model we're building** — it maps your precursors and conditions onto a Maillard benchmark grid and predicts which volatiles to expect. It's built on Pablo Casares' open Maillard simulator with our adapter layer."
- "I want to be completely straight: right now this runs in **mock mode** — every value is **synthetic**, deterministic placeholder data, and the platform **labels it that way on every result**. It's not chemistry yet."
- "The ask to you: **tell us if this shape of prediction is plausible** — that's the validation we need before we wire the real engine."

**Time budget:** 1:30 (≈0:45 `#simulate` input + live Predict outcomes, ≈0:30 honest framing + read the synthetic banner, ≈0:15 buffer).

**One-line fallback:** if `maillard_sim` is off or `/api/simulate` 404s, the Predict button shows the honest _"turn on the **maillard_sim** flag in the Release Center to run it"_ state — narrate the setup form as "the target UI" and skip the live call.

---

## Segment 5 — Compare (inline molecule diff) — 1:00

> You're already on Oracle from Segment 4. Compare is a capability chip — no scene change.

**Click-path:**
1. In the Oracle composer, click the **"Compare molecules"** chip → an inline compare form appends to the thread.
2. Enter **1–2 molecules** (name or corpus id) — e.g. **`2-methyl-3-furanthiol`** and **`2-acetyl-1-pyrroline`** — click **Compare** → `POST /api/compare` returns a **side-by-side profile diff**, with the fields that **differ** highlighted.
3. _(Optional)_ enter a molecule you know isn't in the corpus to show it returns **`in_corpus: false`** — "no invented chemistry."

**What to say (2–3, grounded):**
- "Compare aligns two molecule profiles from the corpus side-by-side and highlights **exactly what differs** — class, aroma, sources."
- "And it stays honest: if a molecule **isn't in our corpus**, it says so — `in corpus: false` — it never **fabricates** a profile to fill the gap."
- "This runs inline, right in the conversation — no navigating away."

**Time budget:** 1:00 (≈0:10 open form, ≈0:35 enter + compare + narrate diff, ≈0:15 optional in-corpus:false beat).

**One-line fallback:** if `/api/compare` 404s, the form shows _"the comparison API loads once it is deployed"_ — say "this is a two-molecule diff over the live corpus; it's mid-deploy" and go to the close.

---

## Close — 0:30 (the ask / what's next)

**Say (the ask):**
- "So that's the full journey: a **grounded Oracle** you can check, a **live corpus** you can narrow, an honest **methods preview**, a **simulator** we want your read on, and **inline compare** — all over ~818 real, cited sources."
- "**What's next:** we **deploy this backlog to the public site**, and we take it to **external P1 expert validation in mid-September**. Between now and then we're closing corpus trust — making sure every source the Oracle can cite has passed the relevance gate."
- "**The ask today:** [is this the right shape for the P1 validation demo? / green-light the deploy? / your read on the simulator's plausibility?] — pick the decision you actually need from the room."

---

## Honest framing lines — keep these handy

Say these proactively; don't wait to be caught out. Honesty is the credibility.

- **Mock simulator:** _"The simulator runs in mock mode today — every value is synthetic, deterministic placeholder data, labelled as such on every result. It's a model we're building, not real chemistry yet. We want your read on whether the predictions are plausible."_
- **Analytics preview:** _"The methods browser is a preview. Only GC-MS has reference data today — via our Meaty Volatile Library. NMR and the rest are marked PLANNED; they show the literature we have, not an analytical engine."_
- **Corpus still growing:** _"The corpus is ~818 sources and growing. About 39% currently pass our relevance gate — so the Oracle only retrieves from that governed, on-topic slice. Tightening that gate is the active work."_
- **Grounding, not guessing:** _"Every Oracle answer is retrieved from our corpus first and cites real sources; if the corpus doesn't cover a question, it refuses rather than invent."_
- **Compare / molecules:** _"If a molecule isn't in our corpus, the platform says so — it never fabricates a profile."_
- **Enrichment reality (if pushed):** _"Molecule structure fields and expert enrichment are still thin — we leave them blank rather than guess. That's deliberate."_

---

## Pre-Demo Checklist

> **Do this the day before, and a fast re-check 15 minutes before you present.** The whole demo depends on running against a build that actually has the new endpoints.

### 1. Deploy first — the demo canNOT run on the current public prod site
The three headline endpoints — **`/api/corpus`**, **`/api/compare`**, **`/api/simulate`** — are **new and 404 until deployed**. Choose ONE host:
- **Deployed staging (recommended):** run **`deploy-dev.command`** → verify the private staging URL → demo there. _(Do NOT rely on `promote-to-prod` unless you intend the public site to carry it.)_
- **Localhost:** run **`run-local.command`** (sets `APP_ENV=dev`, which enables dev flags). _(CLAUDE.md also documents `run_oracle.command` as a localhost launcher.)_

### 2. Turn the simulator flag ON
The simulator routes **404 as if absent** unless **`maillard_sim`** is **ON for the demo environment (dev)**.
- Check `features.json` (Release Center) — `maillard_sim` dev column = true.
- Verify live: **`GET /api/flags`** shows `maillard_sim: true`; **`GET /api/simulate/health`** shows backend **`mock`** + reachable.

### 3. Wake Neon
Neon Postgres **auto-sleeps**; the first query after idle wakes it (a few seconds). **Run one warm-up** (open the Oracle and ask anything, or hit `/api/corpus`) a minute before you start so the first live click isn't a cold-start stall.

### 4. Get past the shared-password gate
The site is behind **one shared password** (HTTP Basic Auth) — every route except `/api/health` requires it. **Log in once** in the browser tab you'll present from.

### 5. Confirm the Oracle is healthy
**`GET /api/health`** → expect `{ ok, db_ok: true, has_anthropic_key: true, model }`. If `db_ok` or `has_anthropic_key` is false, the Oracle won't answer — fix the `.env` before the room fills.

### 6. One full dry-run against the timer
Rehearse the **entire run end-to-end once**, watching the clock. Specifically confirm:
- Oracle streams and a **citation opens**.
- Toggling Research sub-topic chips **moves the live counts**.
- Analytics GC-MS / NMR **pull a corpus slice**.
- Both the `#simulate` **"Predict outcomes"** button and the Oracle **"Predict with the simulator"** chip call the live `/api/simulate` MOCK and **show the `SYNTHETIC — NOT A REAL SIMULATION` banner** (wired 2026-08-31) — confirm the banner fires in your dry-run.
- Compare returns a **side-by-side diff**.

### 7. Have the fallbacks staged
Keep a **second browser tab already logged in** as a hot spare. Know each segment's one-line fallback (above). If a live call fails, narrate the designed state and keep moving — never debug live.

---

### Quick verification block (run these before you present)

```
GET /api/health            → { ok:true, db_ok:true, has_anthropic_key:true, model:… }
GET /api/flags             → { … "maillard_sim": true … }
GET /api/simulate/health   → { mode:"mock", reachable:true, … }
GET /api/corpus?phase=lipid → 200 with { totals:{papers,molecules}, phase_topics, rows }
```
All four green = you're clear to demo.
