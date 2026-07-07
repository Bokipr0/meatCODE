#!/usr/bin/env python3
# Last updated: 2026-07-07 10:40 UTC · Algorithm Expert (audit loop) · NEW: LLM source-judge + dynamic audit prioritization
"""Intelligence layer for the recurring data-authentication loop.

Every ~2 days an agent (`pipeline/audit_sources.py`, owned by the Data Engineer)
pulls ~20 sources from Neon by *dynamic priority*, shows each source's info / tags /
connected queries, and judges quality + relevance to keep improving the corpus.
This module is the brain of that loop; `audit_sources.py` imports it.

Three public pieces (stable interface — the Data Engineer codes to this):

  DEFAULT_WEIGHTS : dict
      Tunable weights + shape constants for the audit-priority function.

  rank_for_audit(candidates, weights=None) -> list[dict]
      Sort candidates by DESCENDING `audit_priority` (added to each dict).
      Pure/offline. Blends IMPORTANCE, STALENESS and UNCERTAINTY (see below).

  judge_source(source) -> dict
      LLM-as-judge (Haiku) for ONE source. Judges TAG CORRECTNESS, RELEVANCE
      (meaty PROCESS flavor vs known false-positive classes) and QUALITY
      separately, then a keep/review/quarantine verdict. Robust: never raises.

  update_weights(prev_weights, audit_results) -> dict
      Dynamic reprioritization — nudges per-branch weights from the latest
      batch's verdicts (branches yielding many quarantines get probed harder
      next run), with decay toward neutral so it self-corrects.

Run standalone (no DB needed) for a smoke test:
    python3 pipeline/audit_judge.py
"""
from __future__ import annotations

import math
import os
from collections import Counter
from datetime import date, datetime, timezone
from functools import lru_cache
from pathlib import Path

# --- make the repo root importable (mirrors pipeline/score_*.py) so we can read the taxonomy bible ---
import sys
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

# Canonical branch list (Atlas 5 families). Prefer the taxonomy bible; fall back to the literal set
# so this module still imports/ranks even if db.taxonomy is unavailable.
try:
    from db.taxonomy import BRANCH_ORDER as _BRANCHES  # type: ignore
    _BRANCHES = list(_BRANCHES)
except Exception:  # pragma: no cover - defensive
    _BRANCHES = ["analytics", "flavor_chemistry", "flavor_ingredients", "meat_analogs", "meat_science"]

JUDGE_MODEL = "claude-haiku-4-5-20251001"  # cheap/fast, same model score_relevance.py uses

# =============================================================================
# Tunable weights + shape constants  (ONE home; everything below reads these)
# =============================================================================
# audit_priority = 100 * branch_mult * (
#     IMPORTANCE  : w_priority·priority + w_citations·cites + w_thin_branch·thin
#   + STALENESS   : w_staleness·staleness
#   + UNCERTAINTY : w_uncertainty·uncertainty + w_untagged·untagged )
# The six w_* deliberately sum to 1.0, so the weighted blend lands in [0,1]
# before the branch multiplier and the ×100 readability scaling.
DEFAULT_WEIGHTS: dict = {
    # ---- (a) IMPORTANCE to the platform: audit what matters most ----
    "w_priority":    0.28,   # existing priority_score (0-100): high-value corpus rows
    "w_citations":   0.08,   # citation impact, log-scaled
    "w_thin_branch": 0.09,   # bonus if the source sits in a thin / high-value taxonomy branch
    # ---- (b) STALENESS: audit what hasn't been checked in a while ----
    "w_staleness":   0.25,   # never-audited = max; decays with days-since-last-audit
    # ---- (c) UNCERTAINTY / information gain: audit what we're least sure about ----
    "w_uncertainty": 0.18,   # mid-range relevance_llm (~40-70) is the most informative to check
    "w_untagged":    0.12,   # no tags / no connected_queries = classification we can't yet trust
    # ---- shape constants for the sub-scores ----
    "stale_halflife_days": 30.0,   # staleness reaches 0.5 at this many days since last audit
    "uncertain_center":    55.0,   # relevance_llm value of peak uncertainty (middle of 40-70)
    "uncertain_width":     22.0,   # Gaussian half-width around the center
    "cite_scale":          200.0,  # citation count that saturates the (log) impact sub-score
    "thin_branches":       ["meat_analogs"],  # empirically thinnest branch (white_space_data.md)
    # ---- dynamic per-branch multipliers: THE feedback loop lives here (1.0 = neutral) ----
    "branch_boost": {b: 1.0 for b in _BRANCHES},
    # ---- update_weights() hyperparameters (also tunable) ----
    "learn": {"gain": 1.2, "lr": 0.5, "decay": 0.8, "min": 0.5, "max": 3.0},
}


# =============================================================================
# Small robust helpers
# =============================================================================
def _clamp01(x: float) -> float:
    return 0.0 if x < 0 else (1.0 if x > 1 else x)


def _num(x, default=None):
    """Coerce to float; tolerate None / str / Decimal. Return `default` on failure."""
    if x is None:
        return default
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def _clamp_int(x, default: int) -> int:
    """Coerce to an int in [0,100]; used to sanitise model-returned scores."""
    v = _num(x)
    if v is None:
        return default
    return int(max(0, min(100, round(v))))


def _get(source: dict, *keys, default=None):
    """First present, non-None value among alias keys (e.g. title/name)."""
    for k in keys:
        if k in source and source[k] is not None:
            return source[k]
    return default


def _parse_dt(v):
    """Parse a datetime/date/ISO-string to an aware UTC datetime, or None."""
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    if isinstance(v, date):
        return datetime(v.year, v.month, v.day, tzinfo=timezone.utc)
    s = str(v).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        pass
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except Exception:
        return None


# =============================================================================
# Taxonomy: map a source's tags / connected_queries -> canonical branch(es)
# =============================================================================
@lru_cache(maxsize=1)
def _tax_maps():
    """(topic_name->branch, keyword->branch), both lowercased. Empty if bible unavailable."""
    topic2branch, kw2branch = {}, {}
    try:
        from db.taxonomy import load  # type: ignore
        for r in load():
            tn = (r.get("topic_name") or "").strip().lower()
            kw = (r.get("keyword") or "").strip().lower()
            if tn:
                topic2branch[tn] = r["branch"]
            if kw:
                kw2branch[kw] = r["branch"]
    except Exception:  # pragma: no cover - defensive
        pass
    return topic2branch, kw2branch


def _branches_of(source: dict) -> set[str]:
    """Canonical branches implied by a source's branch/branches/tags/connected_queries."""
    topic2branch, kw2branch = _tax_maps()
    branchset = set(_BRANCHES)
    out: set[str] = set()

    for key in ("branch", "branches"):
        v = source.get(key)
        if isinstance(v, str) and v in branchset:
            out.add(v)
        elif isinstance(v, (list, tuple, set)):
            out |= {x for x in v if x in branchset}

    for t in (source.get("tags") or []):
        ts = str(t).strip().lower()
        if ts in branchset:
            out.add(ts)
        elif ts in topic2branch:
            out.add(topic2branch[ts])

    for q in (source.get("connected_queries") or source.get("queries") or []):
        qs = str(q).strip().lower()
        if qs in kw2branch:
            out.add(kw2branch[qs])
        elif qs in topic2branch:
            out.add(topic2branch[qs])

    return out


# =============================================================================
# Sub-scores for the audit-priority blend  (each returns [0,1])
# =============================================================================
def _imp_priority(source: dict) -> float:
    ps = _num(source.get("priority_score"))
    return 0.5 if ps is None else _clamp01(ps / 100.0)   # unknown -> neutral


def _imp_citations(source: dict, scale: float) -> float:
    c = _num(_get(source, "citation_count", "cites"), 0.0) or 0.0
    return _clamp01(math.log1p(max(0.0, c)) / math.log1p(max(1.0, scale)))


def _imp_thin(source: dict, thin) -> float:
    return 1.0 if (_branches_of(source) & set(thin or [])) else 0.0


def _staleness(source: dict, halflife: float) -> float:
    """1.0 for never-audited; grows from 0 toward 1 as days-since-audit rises."""
    days = _num(source.get("days_since_audit"))
    if days is None:
        la = _get(source, "last_audited_at", "last_audit", "audited_at")
        if la is not None:
            dt = _parse_dt(la)
            if dt is not None:
                days = max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0)
    if days is not None:
        return _clamp01(1.0 - 0.5 ** (days / max(1.0, halflife)))
    # no date info: distinguish "audited before but undated" from "never audited"
    ac = source.get("audit_count")
    if ac not in (None, "", 0, "0"):
        return 0.6                      # audited at some point, date unknown -> moderately stale
    return 1.0                          # never audited -> maximum staleness


def _uncertainty(source: dict, center: float, width: float) -> float:
    """Peaks at mid-range relevance_llm (~55); high when no machine relevance exists yet."""
    rel = _num(source.get("relevance_llm"))
    if rel is None:
        return 0.85
    return math.exp(-((rel - center) ** 2) / (2.0 * width * width))


def _untagged(source: dict) -> float:
    has_tags = bool(source.get("tags"))
    has_q = bool(source.get("connected_queries") or source.get("queries"))
    if not has_tags and not has_q:
        return 1.0
    if has_tags and has_q:
        return 0.0
    return 0.5


def _branch_mult(source: dict, boost: dict) -> float:
    b = _branches_of(source)
    if not b:
        return 1.0
    vals = [float(boost.get(x, 1.0)) for x in b]
    return sum(vals) / len(vals)


def _merged_weights(weights: dict | None) -> dict:
    """DEFAULT_WEIGHTS with `weights` overlaid (nested dicts merged, not replaced)."""
    import copy
    w = copy.deepcopy(DEFAULT_WEIGHTS)
    if weights:
        for k, v in weights.items():
            if isinstance(v, dict) and isinstance(w.get(k), dict):
                w[k] = {**w[k], **v}
            else:
                w[k] = v
    return w


def _audit_priority(source: dict, w: dict) -> float:
    importance = (
        w["w_priority"] * _imp_priority(source)
        + w["w_citations"] * _imp_citations(source, w.get("cite_scale", 200.0))
        + w["w_thin_branch"] * _imp_thin(source, w.get("thin_branches", []))
    )
    staleness = w["w_staleness"] * _staleness(source, w.get("stale_halflife_days", 30.0))
    uncertainty = (
        w["w_uncertainty"] * _uncertainty(source, w.get("uncertain_center", 55.0), w.get("uncertain_width", 22.0))
        + w["w_untagged"] * _untagged(source)
    )
    raw = importance + staleness + uncertainty          # ~[0,1] (the six weights sum to 1.0)
    return round(100.0 * raw * _branch_mult(source, w.get("branch_boost", {})), 2)


def rank_for_audit(candidates: list[dict], weights: dict | None = None) -> list[dict]:
    """Return candidates sorted by DESCENDING audit_priority; each dict gains an
    'audit_priority' float. Pure and offline — safe to call without a DB or API key.

    Blends three ideas (see DEFAULT_WEIGHTS):
      (a) IMPORTANCE  — priority_score, citations, thin/high-value branch.
      (b) STALENESS   — never-audited or long-since-audited rank higher.
      (c) UNCERTAINTY — mid-range relevance_llm and untagged sources are most informative.
    Missing fields degrade gracefully to neutral values; never raises.
    """
    w = _merged_weights(weights)
    out = []
    for c in (candidates or []):
        c = dict(c)                       # don't mutate the caller's dict
        c["audit_priority"] = _audit_priority(c, w)
        out.append(c)
    out.sort(key=lambda d: d["audit_priority"], reverse=True)
    return out


# =============================================================================
# LLM-as-judge (Haiku): one source at a time, robust to any failure
# =============================================================================
JUDGE_SYSTEM = (
    "You are a strict DATA-QUALITY JUDGE for a knowledge base on MEATY PROCESS FLAVOR: how "
    "savory/meaty flavor and aroma are GENERATED during cooking from precursors and reaction "
    "chemistry — the Maillard reaction, Strecker degradation, lipid oxidation, thiamine (B1) "
    "degradation, nucleotide/sugar breakdown, and the resulting volatile aroma compounds, plus "
    "the analytics (GC-MS, GC-O, OAV/AEDA, sensory panels) and ingredients (protein hydrolysates, "
    "yeast extract, reaction flavors) behind them.\n\n"
    "Judge ONE paper on three axes, each 0-100, grounded ONLY in the abstract provided "
    "(do not use outside knowledge, do not invent facts or tags):\n\n"
    "1. TAG CORRECTNESS (tag_score): do the STORED TAGS actually reflect the abstract? In "
    "tag_issues list concrete, abstract-grounded problems — wrong tags (\"tagged 'lipid oxidation' "
    "but abstract is about protein solubility\"), missing obvious tags (\"missing: Maillard\"), or "
    "over-broad tags. Empty list if the tags are fine. If no abstract is given, score ~50 and say so.\n"
    "2. RELEVANCE (relevance_score): is it TRULY about meat / meat-analog PROCESS-flavor generation "
    "(precursor -> reaction -> aroma), not a mere keyword match? DOWN-score the known false-positive "
    "classes: human nutrition/health outcomes, food safety/contaminants/residues, microbiology/"
    "shelf-life/spoilage, packaging, animal husbandry/growth, or pure analytical-method papers with no "
    "flavor target. Scale: 90-100 core mechanism; 60-89 clearly relevant; 40-59 tangential; 0-39 off-topic.\n"
    "3. QUALITY (quality_score): reward rigor signals visible in the text — GC-MS/GC-O, OAV/AEDA, "
    "quantification, a validated sensory/descriptive panel, a peer-reviewed food/flavor venue, or a "
    "genuine review/meta-analysis. Penalize vague, non-quantified, or clearly off-domain/predatory venues.\n\n"
    "Then set verdict: \"keep\" (relevant AND decent quality AND tags roughly right); \"review\" "
    "(borderline, uncertain, or mixed signals a human should check); \"quarantine\" (off-topic false "
    "positive OR clearly low quality).\n\n"
    "Return ONLY a JSON object, no prose, no code fence:\n"
    "{\"tag_score\":int,\"tag_issues\":[str],\"relevance_score\":int,\"quality_score\":int,"
    "\"verdict\":\"keep|review|quarantine\",\"notes\":\"<=200 chars, why\"}"
)


def _judge_prompt(source: dict) -> str:
    title = _get(source, "title", "name", default="(no title)")
    year = _get(source, "year", default="?")
    journal = _get(source, "journal", "venue", default="?")
    doi = _get(source, "doi", default="")
    cites = _get(source, "citation_count", "cites", default="?")
    is_rev = _get(source, "is_review", default=False)
    tags = source.get("tags") or []
    cq = source.get("connected_queries") or source.get("queries") or []
    abstract = (_get(source, "abstract", default="") or "")[:1400]
    lines = [
        f"TITLE: {title}",
        f"YEAR: {year}   JOURNAL: {journal}   CITATIONS: {cites}   IS_REVIEW: {is_rev}",
        (f"DOI: {doi}" if doi else ""),
        f"STORED TAGS: {', '.join(map(str, tags)) if tags else '(none)'}",
        f"CONNECTED QUERIES: {', '.join(map(str, cq)) if cq else '(none)'}",
        "ABSTRACT:",
        abstract or "(no abstract provided)",
    ]
    return "\n".join(ln for ln in lines if ln != "")


def _verdict_from_scores(rel: int, qual: int, tag: int) -> str:
    """Deterministic fallback/repair mapping when the model omits a valid verdict."""
    if rel < 40 or qual < 35:
        return "quarantine"
    if rel >= 65 and qual >= 55 and tag >= 55:
        return "keep"
    return "review"


def _extract_json_obj(text: str) -> dict:
    """Slice the outermost {...} and parse. Raises on failure (caught by judge_source)."""
    import json
    i, j = text.find("{"), text.rfind("}")
    if i == -1 or j == -1 or j < i:
        raise ValueError("no JSON object in model output")
    return json.loads(text[i:j + 1])


def _normalize_judgment(d: dict) -> dict:
    ts = _clamp_int(d.get("tag_score"), 50)
    rs = _clamp_int(d.get("relevance_score"), 50)
    qs = _clamp_int(d.get("quality_score"), 50)
    issues = d.get("tag_issues") or []
    if isinstance(issues, str):
        issues = [issues]
    issues = [str(x) for x in issues][:8]
    verdict = str(d.get("verdict", "")).strip().lower()
    if verdict not in ("keep", "review", "quarantine"):
        verdict = _verdict_from_scores(rs, qs, ts)
    notes = str(d.get("notes", "") or "")[:240]
    return {
        "tag_score": ts, "tag_issues": issues,
        "relevance_score": rs, "quality_score": qs,
        "verdict": verdict, "notes": notes,
    }


# lazily-built, cached Anthropic client (mirrors score_relevance.py: reads ANTHROPIC_API_KEY from env)
_CLIENT = None


def _load_env() -> None:
    """Minimal .env loader — mirrors db.connect._load_env (setdefault, skip #/blank)."""
    env = _REPO_ROOT / ".env"
    if env.is_file():
        for line in env.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def _get_client():
    global _CLIENT
    if _CLIENT is None:
        _load_env()
        import anthropic  # imported lazily so the module loads/ranks even without the SDK
        _CLIENT = anthropic.Anthropic()
    return _CLIENT


def judge_source(source: dict) -> dict:
    """LLM-as-judge for ONE source (Haiku, low temperature). Returns:
        {'tag_score': int0-100, 'tag_issues': list[str],
         'relevance_score': int0-100, 'quality_score': int0-100,
         'verdict': 'keep'|'review'|'quarantine', 'notes': str}
    Robust by contract: on ANY error (no API key, no SDK, bad JSON, timeout) it returns a
    safe 'review' verdict with an explanatory note instead of raising — so one bad source
    never crashes the batch.
    """
    try:
        client = _get_client()
        msg = client.messages.create(
            model=JUDGE_MODEL,
            max_tokens=420,
            temperature=0.0,                       # deterministic-ish
            system=JUDGE_SYSTEM,
            messages=[{"role": "user", "content": "Judge this paper:\n\n" + _judge_prompt(source)}],
        )
        text = (msg.content[0].text or "").strip()
        return _normalize_judgment(_extract_json_obj(text))
    except Exception as e:
        return {
            "tag_score": 50, "tag_issues": [],
            "relevance_score": 50, "quality_score": 50,
            "verdict": "review",
            "notes": f"judge unavailable -> defaulted to review: {str(e)[:140]}",
        }


# =============================================================================
# Dynamic reprioritization: nudge per-branch weights from the batch's verdicts
# =============================================================================
def update_weights(prev_weights: dict, audit_results: list[dict]) -> dict:
    """Dynamic reprioritization feedback loop.

    For each canonical branch, look at this batch's quarantine rate
    (quarantines / audited_in_branch) and move that branch's multiplier toward
    a target of  1 + gain·quarantine_rate  (so a branch full of junk gets probed
    harder next run). Every branch — seen or not — then DECAYS toward the neutral
    1.0, so one-off spikes fade and the system self-corrects as a branch cleans up.
    Returns a NEW merged weights dict (prev_weights left untouched).
    """
    w = _merged_weights(prev_weights)
    lp = w.get("learn", {})
    gain = float(lp.get("gain", 1.2))
    lr = float(lp.get("lr", 0.5))
    decay = float(lp.get("decay", 0.8))
    lo = float(lp.get("min", 0.5))
    hi = float(lp.get("max", 3.0))

    boost = dict(w.get("branch_boost", {}))
    for b in _BRANCHES:                       # make sure every canonical branch is present
        boost.setdefault(b, 1.0)

    audited, quar = Counter(), Counter()
    for r in (audit_results or []):
        verdict = str(r.get("verdict", "")).strip().lower()
        for b in (_branches_of(r) or set()):
            audited[b] += 1
            if verdict == "quarantine":
                quar[b] += 1

    for b in list(boost.keys()):
        prev = float(boost[b])
        if audited.get(b):
            target = 1.0 + gain * (quar[b] / audited[b])
            moved = prev + lr * (target - prev)
        else:
            moved = prev                      # branch absent this batch -> only decay applies
        newv = 1.0 + decay * (moved - 1.0)    # pull toward neutral 1.0
        boost[b] = round(min(hi, max(lo, newv)), 3)

    w["branch_boost"] = boost
    return w


# =============================================================================
# Standalone smoke-test (no DB, no API key required)
# =============================================================================
if __name__ == "__main__":
    import json as _json

    print("=== audit_judge.py self-test (no DB) ===\n")

    mock = [
        {   # core, on-topic, well-tagged -> expect keep (when the API key is set)
            "id": 101,
            "title": "Formation of meaty aroma volatiles in cysteine-ribose Maillard model systems",
            "year": 2022, "journal": "Food Chemistry", "citation_count": 41,
            "is_review": False, "relevance_llm": 88, "priority_score": 84,
            "tags": ["flavor_chemistry", "GCMS", "Lipid oxidation"],
            "connected_queries": ["Maillard-Lipid interaction", "meaty aroma"],
            "abstract": ("Cysteine-ribose model systems were heated and volatiles analysed by GC-MS "
                         "and GC-O; key odorants (2-furfurylthiol, 2-methyl-3-furanthiol) were "
                         "quantified and odour activity values (OAV) computed; a trained sensory "
                         "panel confirmed the meaty, roasted character."),
        },
        {   # keyword-matched nutrition study -> off-topic false positive, expect quarantine
            "id": 202,
            "title": "Dietary red meat intake and cardiovascular risk: a prospective cohort study",
            "year": 2019, "journal": "Nutrition Reviews", "citation_count": 12,
            "is_review": False, "relevance_llm": 47, "priority_score": 33,
            "tags": ["meat_science", "Lipid oxidation"],
            "connected_queries": ["red meat"],
            "abstract": ("We followed 20,000 adults for 10 years; higher red-meat consumption was "
                         "associated with elevated cardiovascular events. No flavor, aroma, or "
                         "volatile chemistry was analysed."),
        },
    ]
    for s in mock:
        print(f"judge_source(id={s['id']}): {_json.dumps(judge_source(s), ensure_ascii=False)}")

    print("\n=== rank_for_audit (DESC audit_priority) ===")
    pool = mock + [
        {"id": 303, "title": "Untitled untagged preprint", "abstract": "", "relevance_llm": 55},  # untagged + mid-rel + never audited -> should top
        {"id": 404, "title": "Advances in meat-analog flavor: a review", "year": 2005,
         "journal": "Meat Science", "citation_count": 320, "is_review": True,
         "priority_score": 72, "tags": ["HMMA (high-moisture meat analogs)"],
         "last_audited_at": "2026-01-01"},                                                          # thin branch, high cites, long-ago audit
    ]
    for c in rank_for_audit(pool):
        print(f"  id={c['id']:<4} audit_priority={c['audit_priority']:<7} "
              f"rel_llm={c.get('relevance_llm')} priority={c.get('priority_score')} "
              f"branches={sorted(_branches_of(c)) or '[]'}")

    print("\n=== update_weights: branch_boost after a quarantine-heavy batch ===")
    demo_results = [
        dict(mock[0], verdict="keep"),
        dict(mock[1], verdict="quarantine"),
        {"tags": ["HMMA (high-moisture meat analogs)"], "verdict": "quarantine"},
        {"tags": ["LMMA (low-moisture meat analogs / TVP)"], "verdict": "quarantine"},
    ]
    nw = update_weights(DEFAULT_WEIGHTS, demo_results)
    print("  before:", _json.dumps(DEFAULT_WEIGHTS["branch_boost"], ensure_ascii=False))
    print("  after :", _json.dumps(nw["branch_boost"], ensure_ascii=False))
    print("  (meat_analogs probed harder next run; a clean branch decays back toward 1.0)")

    print("\nself-test OK")
