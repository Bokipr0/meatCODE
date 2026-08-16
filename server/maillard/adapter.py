#!/usr/bin/env python3
# Last updated: 2026-08-16 · Fullstack Engineer · NEW — dependency-free Maillard simulator adapter.
#   One interface (`run`, `health`, `validate`) over three backends selected by MAILLARD_MODE:
#   mock (deterministic, seeded, ALWAYS labelled "mode":"mock" + synthetic:true), http (POST to a
#   separate Render docker service at MAILLARD_URL), cli (local `docker exec/run`, dev only).
#   Pure stdlib — the production server only has anthropic + psycopg2-binary available.
"""
MeatCODE ↔ Maillard chemistry simulator — adapter layer.

Why this file exists
--------------------
`server/meatcode_server.py` is a stdlib ThreadingHTTPServer deployed on Render with
`runtime: python`. A Render python web service **cannot spawn Docker containers**, so the
simulator can never run in-process in production. This adapter hides that entirely: the
server calls `adapter.run(request)` and gets back one normalised envelope, whichever of the
three backends happens to be wired up.

Backends (env `MAILLARD_MODE`)
------------------------------
  mock   (default)  Deterministic, seeded, synthetic output derived from the request hash.
                    Every response carries "mode":"mock" and "synthetic": true, and every
                    compound carries "synthetic": true. Nothing here is chemistry — it exists
                    so the UI can be built and demoed honestly before the simulator is wired.
  http              POST {MAILLARD_URL}/simulate — the SEPARATE Render service running the
                    Maillard image (`runtime: docker`). This is the production path.
  cli               Local dev only: `docker exec <MAILLARD_CONTAINER> ...` or
                    `./scripts/docker_maillard.sh run "<json>"` from MAILLARD_REPO.

Env
---
  MAILLARD_MODE       mock | http | cli          (default: mock)
  MAILLARD_URL        base URL of the http backend, e.g. http://maillard-sim:10000
  MAILLARD_TIMEOUT    seconds per attempt        (default: 30)
  MAILLARD_CONTAINER  cli backend container name (default: maillard_validation)
  MAILLARD_REPO       cli backend repo checkout holding scripts/docker_maillard.sh
  MAILLARD_SEED       optional int; pins the mock RNG (otherwise derived from the request)

Contract: see server/maillard/CONTRACT.md — that document, not this file, is what the UI
codes against. Everything below is an implementation of it.
"""

import hashlib
import json
import math
import os
import random
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request

ADAPTER_VERSION = "0.1.0"

# ─── Configuration (read lazily so the server can flip env at runtime in dev) ────────────
DEFAULT_TIMEOUT = 30.0


def _env(name, default=""):
    return (os.environ.get(name) or default).strip()


def mode():
    m = _env("MAILLARD_MODE", "mock").lower()
    return m if m in ("mock", "http", "cli") else "mock"


def _timeout():
    try:
        return max(1.0, float(_env("MAILLARD_TIMEOUT", str(DEFAULT_TIMEOUT))))
    except ValueError:
        return DEFAULT_TIMEOUT


# ─── Error envelope ──────────────────────────────────────────────────────────────────────
# Machine-readable codes the UI branches on. Keep this list and CONTRACT.md in sync.
ERROR_CODES = (
    "INVALID_REQUEST",       # body isn't a usable simulation request at all
    "INVALID_PRECURSOR",     # a named precursor is unknown / malformed / non-positive amount
    "PARAM_OUT_OF_BOUNDS",   # pH / temperature / time / matrix outside the validated envelope
    "SIMULATOR_UNAVAILABLE", # backend not configured, not reachable, or returned 5xx
    "TIMEOUT",               # backend accepted the run but didn't finish in time
    "SIMULATOR_ERROR",       # backend ran and reported its own failure
    "INTERNAL_ERROR",        # adapter bug / unparseable backend output
)


def error(code, message, field=None, detail=None, retryable=False, backend=None):
    """The ONE error shape every caller sees. `ok` is always present and always False."""
    if code not in ERROR_CODES:
        code = "INTERNAL_ERROR"
    env = {
        "ok": False,
        "mode": backend or mode(),
        "error": {
            "code": code,
            "message": message,
            "retryable": bool(retryable),
        },
    }
    if field:
        env["error"]["field"] = field
    if detail:
        env["error"]["detail"] = detail
    return env


# ─── Validation ──────────────────────────────────────────────────────────────────────────
# Deliberately WIDE bounds: this is an input-sanity gate, not a chemistry claim. The
# simulator is the authority on what it can actually model; anything it rejects comes back
# as SIMULATOR_ERROR / INVALID_PRECURSOR from the backend itself.
BOUNDS = {
    "ph":          (2.0, 12.0),
    "temperature": (20.0, 300.0),   # °C
    "time":        (0.1, 1440.0),   # minutes
}
UNITS = ("mg", "g", "mmol", "mol", "ppm", "ppb", "percent")
MATRICES = ("aqueous", "oil", "emulsion", "dry", "gel", "protein_isolate", "unspecified")
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 \-\(\),'\.\+/]{0,79}$")


def _num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)) and math.isfinite(v):
        return float(v)
    return None


def _validate_group(items, label, out):
    if items is None:
        return
    if not isinstance(items, list):
        return error("INVALID_REQUEST", "precursors.%s must be a list" % label,
                     field="precursors.%s" % label)
    for i, it in enumerate(items):
        where = "precursors.%s[%d]" % (label, i)
        if not isinstance(it, dict):
            return error("INVALID_PRECURSOR", "each precursor must be an object", field=where)
        name = (it.get("name") or "").strip() if isinstance(it.get("name"), str) else ""
        if not name or not _NAME_RE.match(name):
            return error("INVALID_PRECURSOR",
                         "precursor name is missing or contains unsupported characters",
                         field=where + ".name", detail={"value": it.get("name")})
        amount = _num(it.get("amount"))
        if amount is None or amount <= 0:
            return error("INVALID_PRECURSOR", "amount must be a positive number",
                         field=where + ".amount", detail={"value": it.get("amount")})
        unit = (it.get("unit") or "mg")
        if unit not in UNITS:
            return error("INVALID_PRECURSOR", "unit must be one of: " + ", ".join(UNITS),
                         field=where + ".unit", detail={"value": unit, "allowed": list(UNITS)})
        out.append({"class": label, "name": name, "amount": amount, "unit": unit})
    return None


def validate(request):
    """Return (normalised_request, None) or (None, error_envelope). Cheap, pure, no I/O —
    the server calls this before ever creating a job so bad input fails instantly."""
    if not isinstance(request, dict):
        return None, error("INVALID_REQUEST", "request body must be a JSON object")

    prec = request.get("precursors")
    if not isinstance(prec, dict):
        return None, error("INVALID_REQUEST",
                           "precursors must be an object with 'sugars' and/or 'amino_acids'",
                           field="precursors")
    flat = []
    for key in ("sugars", "amino_acids", "lipids", "other"):
        err = _validate_group(prec.get(key), key, flat)
        if err:
            return None, err
    if not flat:
        return None, error("INVALID_PRECURSOR",
                           "at least one precursor is required (sugars and/or amino_acids)",
                           field="precursors")

    cond = request.get("conditions")
    if not isinstance(cond, dict):
        return None, error("INVALID_REQUEST", "conditions must be an object", field="conditions")
    norm_cond = {}
    for key, api_key in (("ph", "ph"), ("temperature", "temperature_c"), ("time", "time_min")):
        val = _num(cond.get(api_key))
        if val is None:
            return None, error("INVALID_REQUEST", "conditions.%s is required and must be a number" % api_key,
                               field="conditions." + api_key)
        lo, hi = BOUNDS[key]
        if not (lo <= val <= hi):
            return None, error("PARAM_OUT_OF_BOUNDS",
                               "conditions.%s must be between %g and %g" % (api_key, lo, hi),
                               field="conditions." + api_key,
                               detail={"value": val, "min": lo, "max": hi})
        norm_cond[api_key] = val
    matrix = cond.get("matrix") or "unspecified"
    if matrix not in MATRICES:
        return None, error("PARAM_OUT_OF_BOUNDS", "conditions.matrix must be one of: " + ", ".join(MATRICES),
                           field="conditions.matrix",
                           detail={"value": matrix, "allowed": list(MATRICES)})
    norm_cond["matrix"] = matrix
    if cond.get("water_activity") is not None:
        aw = _num(cond.get("water_activity"))
        if aw is None or not (0.0 <= aw <= 1.0):
            return None, error("PARAM_OUT_OF_BOUNDS", "conditions.water_activity must be between 0 and 1",
                               field="conditions.water_activity", detail={"value": cond.get("water_activity")})
        norm_cond["water_activity"] = aw

    opts = request.get("options") if isinstance(request.get("options"), dict) else {}
    norm_opts = {}
    mc = opts.get("monte_carlo_runs")
    if mc is not None:
        mcv = _num(mc)
        if mcv is None or not (1 <= mcv <= 10000):
            return None, error("PARAM_OUT_OF_BOUNDS", "options.monte_carlo_runs must be 1..10000",
                               field="options.monte_carlo_runs", detail={"value": mc})
        norm_opts["monte_carlo_runs"] = int(mcv)
    if opts.get("seed") is not None:
        sv = _num(opts.get("seed"))
        if sv is None:
            return None, error("INVALID_REQUEST", "options.seed must be an integer",
                               field="options.seed")
        norm_opts["seed"] = int(sv)
    tc = opts.get("top_compounds")
    if tc is not None:
        tcv = _num(tc)
        if tcv is None or not (1 <= tcv <= 200):
            return None, error("PARAM_OUT_OF_BOUNDS", "options.top_compounds must be 1..200",
                               field="options.top_compounds", detail={"value": tc})
        norm_opts["top_compounds"] = int(tcv)

    normalised = {
        "precursors": {
            k: [
                {"name": f["name"], "amount": f["amount"], "unit": f["unit"]}
                for f in flat if f["class"] == k
            ]
            for k in ("sugars", "amino_acids", "lipids", "other")
            if any(f["class"] == k for f in flat)
        },
        "conditions": norm_cond,
        "options": norm_opts,
    }
    if isinstance(request.get("label"), str):
        normalised["label"] = request["label"][:120]
    return normalised, None


def request_fingerprint(normalised):
    """Stable hash of a normalised request — the mock's seed AND a natural cache key."""
    blob = json.dumps(normalised, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# ─── Backend: mock ───────────────────────────────────────────────────────────────────────
# EVERY value below is synthetic. The compound names are a fixed vocabulary of
# commonly-discussed Maillard volatiles used purely as realistic-looking LABELS; the
# numbers attached to them are a seeded RNG shaped by the request, not chemistry. Both the
# envelope and each compound are marked synthetic so nothing can masquerade as a real run.
_MOCK_COMPOUNDS = [
    ("2-acetyl-1-pyrroline", "roasty / popcorn"),
    ("2-methyl-3-furanthiol", "meaty / brothy"),
    ("bis(2-methyl-3-furyl) disulfide", "meaty"),
    ("methional", "boiled potato"),
    ("furfural", "sweet / caramellic"),
    ("5-hydroxymethylfurfural", "caramellic"),
    ("2,5-dimethylpyrazine", "roasted / nutty"),
    ("2-ethyl-3,5-dimethylpyrazine", "roasted"),
    ("3-(methylthio)propanal", "savoury"),
    ("furfuryl mercaptan", "coffee-like"),
    ("2-furanmethanethiol", "roasty"),
    ("maltol", "caramellic"),
    ("hexanal", "green / fatty"),
    ("(E,E)-2,4-decadienal", "fried / fatty"),
    ("1-octen-3-ol", "mushroom"),
    ("2-acetylthiazole", "nutty / popcorn"),
]
# Placeholder family vocabulary for the mock ONLY. The real simulator's 16 reaction
# families are the authority; the UI must treat family ids as OPAQUE strings (CONTRACT.md).
_MOCK_FAMILIES = [
    "amadori_rearrangement", "strecker_degradation", "sugar_fragmentation",
    "pyrazine_formation", "thiol_formation", "furan_formation",
    "aldol_condensation", "retro_aldol", "dehydration", "cyclization",
    "lipid_oxidation", "lipid_maillard_interaction", "thiazole_formation",
    "pyrrole_formation", "melanoidin_polymerization", "sulfur_recombination",
]
_MOCK_OFF_NOTES = [
    ("burnt", "over-roasted / acrid"),
    ("sulfurous", "eggy / cabbage"),
    ("green", "beany / grassy"),
    ("cardboard", "oxidised / stale"),
]

MOCK_DISCLAIMER = (
    "SYNTHETIC PLACEHOLDER — deterministic pseudo-data derived from the request hash by "
    "server/maillard/adapter.py in mock mode. Not a chemistry simulation. Do not cite, "
    "export, or present as a result."
)


def _mock_run(normalised, fingerprint):
    seed_env = _env("MAILLARD_SEED")
    seed = normalised.get("options", {}).get("seed")
    if seed is None and seed_env:
        try:
            seed = int(seed_env)
        except ValueError:
            seed = None
    if seed is None:
        seed = int(fingerprint[:12], 16)
    rng = random.Random(seed)
    t0 = time.time()

    cond = normalised["conditions"]
    temp, tmin, ph = cond["temperature_c"], cond["time_min"], cond["ph"]
    # A monotone "extent" knob so the mock at least MOVES with the inputs (higher temp /
    # longer time / higher pH → larger yields). Still synthetic; no kinetics implied.
    extent = (temp / 150.0) * (1.0 - math.exp(-tmin / 30.0)) * (0.6 + ph / 14.0)
    n_prec = sum(len(v) for v in normalised["precursors"].values())
    mass = sum(p["amount"] for v in normalised["precursors"].values() for p in v)

    top_n = normalised.get("options", {}).get("top_compounds", 8)
    picks = _MOCK_COMPOUNDS[:]
    rng.shuffle(picks)
    picks = picks[:min(top_n, len(picks))]

    compounds = []
    for rank, (name, descriptor) in enumerate(picks, start=1):
        base = extent * mass * rng.uniform(0.4, 4.0) * (1.0 / rank) * 12.0
        spread = base * rng.uniform(0.15, 0.55)
        conf = max(0.05, min(0.95, 0.9 - 0.06 * rank + rng.uniform(-0.08, 0.08)))
        fams = rng.sample(_MOCK_FAMILIES, k=rng.randint(1, 3))
        weights = [rng.random() for _ in fams]
        tot = sum(weights) or 1.0
        compounds.append({
            "rank": rank,
            "name": name,
            "descriptor": descriptor,
            "yield_ppb": round(base, 2),
            "confidence": round(conf, 3),
            "confidence_interval_ppb": [round(max(0.0, base - spread), 2), round(base + spread, 2)],
            "ci_level": 0.95,
            "reaction_families": [
                {"family": f, "contribution": round(w / tot, 3)} for f, w in zip(fams, weights)
            ],
            "synthetic": True,
        })
    compounds.sort(key=lambda c: c["yield_ppb"], reverse=True)
    for i, c in enumerate(compounds, start=1):
        c["rank"] = i

    off_notes = []
    for tag, descriptor in _MOCK_OFF_NOTES:
        risk = max(0.0, min(1.0, rng.uniform(0.0, 0.5) + (0.3 if temp > 200 else 0.0)))
        if risk > 0.15:
            off_notes.append({
                "tag": tag, "descriptor": descriptor,
                "risk": round(risk, 3),
                "level": "high" if risk > 0.6 else ("medium" if risk > 0.35 else "low"),
                "synthetic": True,
            })

    fam_totals = {}
    for c in compounds:
        for f in c["reaction_families"]:
            fam_totals[f["family"]] = fam_totals.get(f["family"], 0.0) + f["contribution"] * c["yield_ppb"]
    grand = sum(fam_totals.values()) or 1.0
    families = sorted(
        ({"family": k, "share": round(v / grand, 3), "synthetic": True} for k, v in fam_totals.items()),
        key=lambda d: d["share"], reverse=True)

    duration = time.time() - t0
    return {
        "ok": True,
        "mode": "mock",
        "synthetic": True,
        "disclaimer": MOCK_DISCLAIMER,
        "request": normalised,
        "run": {
            "simulator": "maillard-mock",
            "simulator_version": "mock-" + ADAPTER_VERSION,
            "adapter_version": ADAPTER_VERSION,
            "seed": seed,
            "monte_carlo_runs": normalised.get("options", {}).get("monte_carlo_runs", 0),
            "duration_ms": int(duration * 1000),
            "fingerprint": fingerprint,
            "precursor_count": n_prec,
        },
        "compounds": compounds,
        "reaction_families": families,
        "off_notes": off_notes,
        "warnings": ["Mock backend: results are synthetic placeholders, not chemistry."],
    }


# ─── Backend: http (the separate Render docker service) ──────────────────────────────────
def _http_post(url, payload, timeout):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json",
                                          "Accept": "application/json",
                                          "User-Agent": "meatcode-maillard-adapter/" + ADAPTER_VERSION})
    token = _env("MAILLARD_TOKEN")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", "replace")
    return json.loads(raw)


def _http_run(normalised, fingerprint):
    base = _env("MAILLARD_URL").rstrip("/")
    if not base:
        return error("SIMULATOR_UNAVAILABLE",
                     "MAILLARD_MODE=http but MAILLARD_URL is not set.",
                     retryable=False, backend="http")
    url = base + "/simulate"
    timeout = _timeout()
    last = None
    for attempt in (1, 2):                      # retry ONCE, only on transport-level failure
        started = time.time()
        try:
            raw = _http_post(url, normalised, timeout)
            return _normalise_backend_result(raw, "http", fingerprint, time.time() - started)
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", "replace")[:500]
            except Exception:
                pass
            if 400 <= e.code < 500:             # the simulator rejected the INPUT — don't retry
                return _backend_client_error(e.code, body, "http")
            last = error("SIMULATOR_UNAVAILABLE", "Maillard service returned HTTP %d." % e.code,
                         detail={"body": body}, retryable=True, backend="http")
        except (urllib.error.URLError, OSError) as e:
            reason = getattr(e, "reason", e)
            is_timeout = "timed out" in str(reason).lower()
            last = error("TIMEOUT" if is_timeout else "SIMULATOR_UNAVAILABLE",
                         "Maillard service did not respond in %gs." % timeout if is_timeout
                         else "Maillard service unreachable: %s" % str(reason)[:200],
                         retryable=True, backend="http")
        except ValueError as e:
            return error("INTERNAL_ERROR", "Maillard service returned unparseable output: %s" % str(e)[:200],
                         backend="http")
        if attempt == 1:
            time.sleep(0.5)
    return last


def _backend_client_error(status, body, backend):
    """Map a 4xx from the simulator into our vocabulary, preferring its own code if it
    speaks the contract."""
    try:
        parsed = json.loads(body)
    except Exception:
        parsed = {}
    code = (parsed.get("error") or {}).get("code") if isinstance(parsed.get("error"), dict) else None
    if code in ERROR_CODES:
        return error(code, (parsed["error"].get("message") or "Rejected by the simulator."),
                     field=parsed["error"].get("field"), backend=backend)
    return error("INVALID_REQUEST", "Simulator rejected the request (HTTP %d)." % status,
                 detail={"body": body[:300]}, backend=backend)


# ─── Backend: cli (local docker — DEV ONLY) ──────────────────────────────────────────────
def _cli_run(normalised, fingerprint):
    if not shutil.which("docker"):
        return error("SIMULATOR_UNAVAILABLE",
                     "MAILLARD_MODE=cli but `docker` is not on PATH. This backend is local-dev only "
                     "(a Render python service cannot run Docker).", backend="cli")
    repo = _env("MAILLARD_REPO")
    payload = json.dumps(normalised, separators=(",", ":"))
    script = os.path.join(repo, "scripts", "docker_maillard.sh") if repo else ""
    if script and os.path.exists(script):
        cmd = [script, "run", payload]
        cwd = repo
    else:
        container = _env("MAILLARD_CONTAINER", "maillard_validation")
        cmd = ["docker", "exec", "-i", container, "maillard", "run", "--json", "-"]
        cwd = None
    timeout = _timeout()
    started = time.time()
    try:
        proc = subprocess.run(cmd, cwd=cwd or None, input=payload, capture_output=True,
                              text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return error("TIMEOUT", "Local Maillard container did not finish in %gs." % timeout,
                     retryable=True, backend="cli")
    except OSError as e:
        return error("SIMULATOR_UNAVAILABLE", "Could not start the Maillard container: %s" % str(e)[:200],
                     backend="cli")
    if proc.returncode != 0:
        return error("SIMULATOR_ERROR", "Maillard container exited %d." % proc.returncode,
                     detail={"stderr": (proc.stderr or "")[:500]}, backend="cli")
    out = (proc.stdout or "").strip()
    start = out.find("{")
    if start < 0:
        return error("INTERNAL_ERROR", "Maillard container produced no JSON.",
                     detail={"stdout": out[:300]}, backend="cli")
    try:
        raw = json.loads(out[start:])
    except ValueError as e:
        return error("INTERNAL_ERROR", "Unparseable simulator output: %s" % str(e)[:200], backend="cli")
    return _normalise_backend_result(raw, "cli", fingerprint, time.time() - started)


# ─── Normalising a real backend's payload into the contract ──────────────────────────────
def _normalise_backend_result(raw, backend, fingerprint, elapsed):
    """The Maillard prototype's JSON is NOT assumed to match our contract. Anything it
    already provides is passed through; anything missing is filled with nulls rather than
    invented. If it reports its own error, that wins."""
    if not isinstance(raw, dict):
        return error("INTERNAL_ERROR", "Simulator returned a non-object payload.", backend=backend)
    if raw.get("ok") is False or raw.get("error"):
        err = raw.get("error")
        if isinstance(err, dict) and err.get("code") in ERROR_CODES:
            return error(err["code"], err.get("message") or "Simulator error.",
                         field=err.get("field"), detail=err.get("detail"), backend=backend)
        return error("SIMULATOR_ERROR", str(err or raw.get("message") or "Simulator reported a failure.")[:300],
                     backend=backend)

    compounds = raw.get("compounds") or raw.get("predictions") or []
    out_compounds = []
    for i, c in enumerate(compounds if isinstance(compounds, list) else [], start=1):
        if not isinstance(c, dict):
            continue
        ci = c.get("confidence_interval_ppb") or c.get("ci") or None
        fams = c.get("reaction_families") or c.get("families") or []
        if isinstance(fams, list):
            fams = [f if isinstance(f, dict) else {"family": str(f), "contribution": None} for f in fams]
        else:
            fams = []
        out_compounds.append({
            "rank": c.get("rank") or i,
            "name": c.get("name") or c.get("compound") or "(unnamed)",
            "descriptor": c.get("descriptor") or c.get("odor") or None,
            "yield_ppb": c.get("yield_ppb", c.get("yield", None)),
            "confidence": c.get("confidence"),
            "confidence_interval_ppb": ci if isinstance(ci, list) and len(ci) == 2 else None,
            "ci_level": c.get("ci_level", 0.95),
            "reaction_families": fams,
            "synthetic": False,
        })

    run = raw.get("run") if isinstance(raw.get("run"), dict) else {}
    return {
        "ok": True,
        "mode": backend,
        "synthetic": False,
        "request": raw.get("request"),
        "run": {
            "simulator": run.get("simulator") or raw.get("simulator") or "maillard",
            "simulator_version": run.get("version") or raw.get("version"),
            "adapter_version": ADAPTER_VERSION,
            "seed": run.get("seed", raw.get("seed")),
            "monte_carlo_runs": run.get("monte_carlo_runs", raw.get("monte_carlo_runs")),
            "duration_ms": run.get("duration_ms", int(elapsed * 1000)),
            "fingerprint": fingerprint,
        },
        "compounds": out_compounds,
        "reaction_families": raw.get("reaction_families") or [],
        "off_notes": raw.get("off_notes") or raw.get("off_note_risks") or [],
        "warnings": raw.get("warnings") or [],
    }


# ─── Public interface ────────────────────────────────────────────────────────────────────
def run(request):
    """Validate + execute one simulation. ALWAYS returns a dict with a boolean `ok` and a
    `mode`; never raises. On success the shape is the success envelope in CONTRACT.md, on
    failure the error envelope."""
    normalised, err = validate(request)
    if err:
        return err
    fingerprint = request_fingerprint(normalised)
    m = mode()
    try:
        if m == "http":
            return _http_run(normalised, fingerprint)
        if m == "cli":
            return _cli_run(normalised, fingerprint)
        return _mock_run(normalised, fingerprint)
    except Exception as e:                       # last-resort net: the server must never 500
        return error("INTERNAL_ERROR", "Adapter failure: %s" % str(e)[:200], backend=m)


def health():
    """Which backend is active and is it reachable. Cheap; safe to poll."""
    m = mode()
    info = {"ok": False, "mode": m, "adapter_version": ADAPTER_VERSION,
            "synthetic": m == "mock", "timeout_s": _timeout()}
    if m == "mock":
        info.update(ok=True, reachable=True, detail="Mock backend — synthetic output only.")
        return info
    if m == "http":
        base = _env("MAILLARD_URL").rstrip("/")
        info["url"] = base or None
        if not base:
            info.update(reachable=False, detail="MAILLARD_URL is not set.")
            return info
        try:
            req = urllib.request.Request(base + "/health", method="GET",
                                         headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=min(_timeout(), 10.0)) as resp:
                body = resp.read().decode("utf-8", "replace")[:500]
            info.update(ok=True, reachable=True, detail=body)
        except Exception as e:
            info.update(reachable=False, detail="unreachable: %s" % str(e)[:200])
        return info
    container = _env("MAILLARD_CONTAINER", "maillard_validation")
    info["container"] = container
    if not shutil.which("docker"):
        info.update(reachable=False, detail="`docker` not on PATH (cli backend is local-dev only).")
        return info
    try:
        proc = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", container],
                              capture_output=True, text=True, timeout=10)
        running = proc.returncode == 0 and proc.stdout.strip() == "true"
        info.update(ok=running, reachable=running,
                    detail=(proc.stdout or proc.stderr or "").strip()[:200])
    except Exception as e:
        info.update(reachable=False, detail=str(e)[:200])
    return info


if __name__ == "__main__":                       # python3 server/maillard/adapter.py → smoke test
    demo = {
        "precursors": {
            "sugars": [{"name": "D-glucose", "amount": 180, "unit": "mg"},
                       {"name": "D-ribose", "amount": 60, "unit": "mg"}],
            "amino_acids": [{"name": "L-cysteine", "amount": 120, "unit": "mg"},
                            {"name": "L-methionine", "amount": 40, "unit": "mg"}],
        },
        "conditions": {"ph": 5.6, "temperature_c": 140, "time_min": 30, "matrix": "aqueous"},
        "options": {"monte_carlo_runs": 200, "top_compounds": 6},
        "label": "beef-broth base",
    }
    print(json.dumps(health(), indent=2))
    print(json.dumps(run(demo), indent=2))
