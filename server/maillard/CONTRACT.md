# Maillard simulator — request / response contract

_Last updated: 2026-08-31 · Project Coordinator · added `mM` / `mmol/L` to accepted units (§2) to match the adapter + the `#simulate` form. Prev: 2026-08-16 · Fullstack — the wire contract between the MeatCODE UI, `server/meatcode_server.py`, and the Maillard chemistry simulator._

This document is what the **UI codes against**. `adapter.py` is an implementation of it, and so is
whatever wraps the Maillard container. If the simulator's own JSON differs, the adapter translates —
the UI never sees the simulator's native shape.

---

## 0. Where this runs (read this before designing against it)

Production MeatCODE is a Render service with `runtime: python` running a stdlib
`ThreadingHTTPServer`. **A Render python service cannot spawn Docker containers**, so the simulator
can never run inside it. Three backends exist, chosen by `MAILLARD_MODE`:

| mode | what it is | where it's used |
|---|---|---|
| `mock` | deterministic synthetic output derived from the request hash | default everywhere until the real service is enabled |
| `http` | `POST {MAILLARD_URL}/simulate` on a **separate Render service** (`runtime: docker`) | the intended production path |
| `cli` | `docker exec`/`docker_maillard.sh` on the local machine | local dev only |

The browser **never** calls the simulator directly. It calls MeatCODE's own same-origin proxy routes
(`/api/simulate*`) so the existing Basic-Auth session covers it and there is no CORS or second
credential. The whole surface is behind the `maillard_sim` feature flag: flag off → `404`.

---

## 1. Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/simulate` | Submit a run. `200` with the full result if it finished fast, `202` with a job id if not. |
| `GET` | `/api/simulate/{job_id}` | Poll a job. `202` + `{status:"running"}` while in flight, `200` + the full result when done (or the error status when it failed). |
| `GET` | `/api/simulate/health` | Which backend is active and whether it's reachable. |

All three require the site's Basic Auth **and** the `maillard_sim` flag being on for the current
`APP_ENV`. Flag off → `404 {"error":"not found"}` (the route behaves as if it doesn't exist).

### Why submit → poll

Runs are 1–10 s and Monte-Carlo settings can push past that. Rather than pretend a 10 s request is
instant, `POST /api/simulate` waits up to `MAILLARD_SYNC_WAIT` seconds (default 8) for the job to
finish inline. Fast runs therefore come back in one round trip with `200`; slow ones return `202`
and the UI polls. **The UI must handle both** — branch on the HTTP status, or equivalently on
`status` in the body.

---

## 2. Request

```jsonc
{
  "precursors": {
    "sugars":      [ { "name": "D-glucose", "amount": 180, "unit": "mg" } ],
    "amino_acids": [ { "name": "L-cysteine", "amount": 120, "unit": "mg" } ],
    "lipids":      [ ],          // optional
    "other":       [ ]           // optional
  },
  "conditions": {
    "ph": 5.6,                   // required, 2.0 – 12.0
    "temperature_c": 140,        // required, 20 – 300
    "time_min": 30,              // required, 0.1 – 1440
    "matrix": "aqueous",         // optional, default "unspecified"
    "water_activity": 0.85       // optional, 0 – 1
  },
  "options": {                   // all optional
    "monte_carlo_runs": 200,     // 1 – 10000
    "seed": 12345,               // pins the run; omit for a request-derived seed
    "top_compounds": 8           // 1 – 200, default 8
  },
  "label": "beef-broth base"     // optional, free text ≤120 chars, echoed back
}
```

- At least **one** precursor across all groups is required.
- `unit` ∈ `mg | g | mmol | mol | ppm | ppb | percent | mM | mmol/L` (default `mg`). _(`mM` / `mmol/L` added 2026-08-31: the `#simulate` form submits mM; the mock treats it as a concentration, no conversion. Real backends may convert or reject per their own capability.)_
- `matrix` ∈ `aqueous | oil | emulsion | dry | gel | protein_isolate | unspecified`.
- Bounds are an **input-sanity gate, not a chemistry claim** — deliberately wide. The simulator
  remains the authority on what it can model and may still reject an in-bounds request.

---

## 3. Success response

```jsonc
{
  "ok": true,
  "status": "done",
  "job_id": "3f1c…",
  "mode": "mock",                 // mock | http | cli — WHICH BACKEND PRODUCED THIS
  "synthetic": true,              // true ⇒ NOT a real simulation. UI must show a banner.
  "disclaimer": "…",              // present only when synthetic
  "request": { … },               // the normalised request actually run
  "run": {
    "simulator": "maillard-mock",
    "simulator_version": "mock-0.1.0",
    "adapter_version": "0.1.0",
    "seed": 201847959912731,
    "monte_carlo_runs": 200,
    "duration_ms": 3,
    "fingerprint": "sha256…"      // stable hash of the normalised request; also the cache key
  },
  "compounds": [                  // ranked, highest yield first
    {
      "rank": 1,
      "name": "2-methyl-3-furanthiol",
      "descriptor": "meaty / brothy",
      "yield_ppb": 412.77,
      "confidence": 0.84,                       // 0–1
      "confidence_interval_ppb": [301.2, 524.3],
      "ci_level": 0.95,
      "reaction_families": [                    // attribution, contributions sum to ~1
        { "family": "thiol_formation", "contribution": 0.71 },
        { "family": "strecker_degradation", "contribution": 0.29 }
      ],
      "synthetic": true
    }
  ],
  "reaction_families": [ { "family": "thiol_formation", "share": 0.34 } ],
  "off_notes": [ { "tag": "burnt", "descriptor": "over-roasted / acrid",
                   "risk": 0.42, "level": "medium" } ],
  "warnings": [ "Mock backend: results are synthetic placeholders, not chemistry." ]
}
```

### Fields the UI may rely on

**Always present, always these types:**

| Field | Type | Note |
|---|---|---|
| `ok` | bool | `true` on success, `false` on every error |
| `mode` | string | one of `mock` / `http` / `cli` |
| `synthetic` | bool | **must** drive a visible "not a real simulation" banner when `true` |
| `run.adapter_version` | string | |
| `run.fingerprint` | string | |
| `compounds` | array | may be empty; each item always has `rank`, `name`, `synthetic` |
| `reaction_families` | array | may be empty |
| `off_notes` | array | may be empty |
| `warnings` | array of strings | may be empty |

**Present but nullable — render defensively:** `descriptor`, `yield_ppb`, `confidence`,
`confidence_interval_ppb`, `ci_level`, `run.simulator_version`, `run.seed`,
`run.monte_carlo_runs`, `request`.

**Opaque to the UI:** `reaction_families[].family` ids. The simulator owns the 16-family
vocabulary; treat ids as strings, title-case them for display, do not hardcode a list or attach
meaning to unknown ids. (`adapter.py`'s mock uses a placeholder vocabulary that will not necessarily
match the real one.)

**Never rely on:** compound ordering being stable across simulator versions (`rank` is
per-response), or `yield_ppb` being comparable across different `mode`s.

### Job-in-progress response (`202`, from either `POST /api/simulate` or the poll route)

```json
{ "ok": true, "status": "running", "job_id": "8bd7dc9328944326",
  "poll": "/api/simulate/8bd7dc9328944326", "submitted_at": "2026-08-16T14:29:52+00:00",
  "elapsed_ms": 2002, "mode": "http" }
```

`status` ∈ `queued | running | done | error`. Poll no faster than every 1 s; give up after ~120 s
and surface a `TIMEOUT`. Jobs are held in memory for 1 hour and are **not** durable across a
restart — a missing job id returns `JOB_NOT_FOUND`, which the UI should treat as "resubmit".

---

## 4. Error response

One shape for every failure, at every layer:

```json
{
  "ok": false,
  "mode": "http",
  "error": {
    "code": "PARAM_OUT_OF_BOUNDS",
    "message": "conditions.temperature_c must be between 20 and 300",
    "field": "conditions.temperature_c",
    "detail": { "value": 900, "min": 20, "max": 300 },
    "retryable": false
  }
}
```

`code` is the only thing the UI should branch on. `message` is human-readable but not stable.
`field` and `detail` are optional.

| `code` | HTTP | Meaning | Suggested UI |
|---|---|---|---|
| `INVALID_REQUEST` | 400 | body isn't a usable request (missing `precursors`, bad JSON shape) | inline form error |
| `INVALID_PRECURSOR` | 400 | a precursor is unnamed, non-positive, or has a bad unit | highlight `field` |
| `PARAM_OUT_OF_BOUNDS` | 400 | pH / temp / time / matrix / options outside the accepted envelope | highlight `field`, show `detail.min`/`max` |
| `SIMULATOR_UNAVAILABLE` | 503 | backend not configured, unreachable, or 5xx | "Simulator offline" state; offer retry |
| `TIMEOUT` | 504 | accepted but didn't finish in time | offer retry, suggest fewer Monte-Carlo runs |
| `SIMULATOR_ERROR` | 502 | the simulator ran and reported its own failure | show `message`, offer retry |
| `JOB_NOT_FOUND` | 404 | unknown / expired job id | "expired — resubmit" |
| `INTERNAL_ERROR` | 500 | adapter bug / unparseable backend output | generic failure, log it |
| `FEATURE_DISABLED` | 404 | `maillard_sim` off for this env — route returns a bare `{"error":"not found"}` | should not be reachable from the UI |

`error.retryable` is a hint: `true` for transport-level problems, `false` for anything caused by the
input.

---

## 5. Worked example

**Request**

```
POST /api/simulate
Content-Type: application/json
Authorization: Basic <the shared site credential, sent as credentials:'same-origin'>

{
  "precursors": {
    "sugars": [{"name": "D-glucose", "amount": 180, "unit": "mg"},
               {"name": "D-ribose",  "amount": 60,  "unit": "mg"}],
    "amino_acids": [{"name": "L-cysteine",   "amount": 120, "unit": "mg"},
                    {"name": "L-methionine", "amount": 40,  "unit": "mg"}]
  },
  "conditions": {"ph": 5.6, "temperature_c": 140, "time_min": 30, "matrix": "aqueous"},
  "options": {"monte_carlo_runs": 200, "top_compounds": 3},
  "label": "beef-broth base"
}
```

**Response (`200`, mock backend, trimmed to 3 compounds)**

```json
{
  "ok": true,
  "status": "done",
  "job_id": "b7c0e1f2a9d34c58",
  "mode": "mock",
  "synthetic": true,
  "disclaimer": "SYNTHETIC PLACEHOLDER — deterministic pseudo-data derived from the request hash by server/maillard/adapter.py in mock mode. Not a chemistry simulation. Do not cite, export, or present as a result.",
  "run": {
    "simulator": "maillard-mock",
    "simulator_version": "mock-0.1.0",
    "adapter_version": "0.1.0",
    "seed": 201847959912731,
    "monte_carlo_runs": 200,
    "duration_ms": 1,
    "fingerprint": "b7c0e1f2a9d34c58…"
  },
  "compounds": [
    {"rank": 1, "name": "2-methyl-3-furanthiol", "descriptor": "meaty / brothy",
     "yield_ppb": 4103.55, "confidence": 0.861, "confidence_interval_ppb": [3218.4, 4988.7],
     "ci_level": 0.95,
     "reaction_families": [{"family": "thiol_formation", "contribution": 0.63},
                           {"family": "strecker_degradation", "contribution": 0.37}],
     "synthetic": true},
    {"rank": 2, "name": "2-acetyl-1-pyrroline", "descriptor": "roasty / popcorn",
     "yield_ppb": 1877.20, "confidence": 0.792, "confidence_interval_ppb": [1402.1, 2352.3],
     "ci_level": 0.95,
     "reaction_families": [{"family": "pyrazine_formation", "contribution": 1.0}],
     "synthetic": true},
    {"rank": 3, "name": "methional", "descriptor": "boiled potato",
     "yield_ppb": 640.08, "confidence": 0.735, "confidence_interval_ppb": [488.0, 792.2],
     "ci_level": 0.95,
     "reaction_families": [{"family": "strecker_degradation", "contribution": 1.0}],
     "synthetic": true}
  ],
  "reaction_families": [{"family": "thiol_formation", "share": 0.41, "synthetic": true},
                        {"family": "strecker_degradation", "share": 0.33, "synthetic": true},
                        {"family": "pyrazine_formation", "share": 0.26, "synthetic": true}],
  "off_notes": [{"tag": "sulfurous", "descriptor": "eggy / cabbage", "risk": 0.31,
                 "level": "low", "synthetic": true}],
  "warnings": ["Mock backend: results are synthetic placeholders, not chemistry."]
}
```

**Error example (`400`)**

```json
{"ok": false, "mode": "mock",
 "error": {"code": "INVALID_PRECURSOR", "message": "amount must be a positive number",
           "field": "precursors.sugars[0].amount", "detail": {"value": -5},
           "retryable": false}}
```

---

## 6. Caching

`run.fingerprint` is a SHA-256 of the *normalised* request (including the seed once resolved), so
identical inputs produce an identical fingerprint. Deterministic runs (explicit `options.seed`) are
therefore safely cacheable by fingerprint. Runs **without** an explicit seed are seeded from the
request hash, which makes them reproducible too — but caching those hides genuine Monte-Carlo
variance, so cache only when a seed was given. No cache is implemented yet; the key is reserved.

---

## 7. Environment reference

| Var | Default | Meaning |
|---|---|---|
| `MAILLARD_MODE` | `mock` | `mock` / `http` / `cli` |
| `MAILLARD_URL` | — | base URL of the http backend (Render internal URL) |
| `MAILLARD_TOKEN` | — | optional bearer token for the http backend |
| `MAILLARD_TIMEOUT` | `30` | seconds per attempt; the http backend retries once on transport failure |
| `MAILLARD_SYNC_WAIT` | `8` | seconds `POST /api/simulate` waits inline before returning `202` |
| `MAILLARD_MAX_CONCURRENCY` | `4` | simultaneous simulator runs allowed through the proxy |
| `MAILLARD_CONTAINER` | `maillard_validation` | cli backend container name |
| `MAILLARD_REPO` | — | cli backend checkout containing `scripts/docker_maillard.sh` |
| `MAILLARD_SEED` | — | pins the mock RNG globally (demo reproducibility) |
