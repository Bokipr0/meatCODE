#!/usr/bin/env python3
"""
score_claims.py — MeatCODE claim weighting, contradiction detection, consensus clustering.

Dependency-free (stdlib only). Reference implementation of
analysis/kg_model/WEIGHTING_MODEL.md.

Input:  pipeline/out/claim_triplets_v1.json  (Data Engineer's Layer-C output)
        If absent, falls back to an inline SAMPLE corpus that is CLEARLY LABELLED.
        The SAMPLE is illustrative structure, NOT verified chemistry — do not cite it.

Output: ranked claim table, contradiction report, consensus edge table.

Usage:  python3 analysis/kg_model/score_claims.py [--json path] [--params k=v ...]
"""

import argparse
import json
import math
import os
import sys
from collections import defaultdict

# --------------------------------------------------------------------------
# 1. VALUE TABLES  (expert priors — see WEIGHTING_MODEL.md §3; all tunable)
# --------------------------------------------------------------------------

EVIDENCE_TIER = {
    "T1_experimental": 1.00,   # the linked source measured it directly
    "T2_review":       0.75,   # asserted in a review, primary data one hop away
    "T3_inferred":     0.45,   # model-extracted from abstract, unreviewed
    "T4_conjecture":   0.25,   # hypothesis / discussion-section speculation
}
DEFAULT_TIER = 0.45           # matches the 45 legacy Airtable rows (all T3)

METHOD_STRENGTH = {
    "gco_aeda_quant":      1.00,  # GC-O/AEDA + quantification + OAV
    "gcms_quantified":     0.90,  # GC-MS with calibrated concentrations
    "sensory_trained":     0.85,  # trained panel, n>=8, replicated
    "gcms_identification": 0.70,  # peak identified, not quantified
    "model_system":        0.65,  # aqueous/buffer model reaction, not food
    "consumer_panel":      0.60,  # untrained consumers, hedonic only
    "in_silico":           0.40,  # QSAR / prediction only
    "library_compilation": 0.45,  # value copied from a compiled volatile library
    "unspecified":         0.50,  # method not stated in the abstract
}

# live-schema method strings (pipeline/out/claim_triplets_v1.json) -> table key
METHOD_ALIASES = [
    ("gc-o", "gco_aeda_quant"), ("aeda", "gco_aeda_quant"), ("olfactom", "gco_aeda_quant"),
    ("trained sensory", "sensory_trained"), ("descriptive analysis", "sensory_trained"),
    ("consumer", "consumer_panel"),
    ("spme", "gcms_identification"), ("gc-ims", "gcms_identification"),
    ("gc-ms", "gcms_identification"), ("gcms", "gcms_identification"),
    ("metabolomic", "gcms_quantified"), ("quantif", "gcms_quantified"),
    ("library", "library_compilation"), ("model", "in_silico"), ("silico", "in_silico"),
]
TIER_ALIASES = {
    "experimental": "T1_experimental", "review": "T2_review",
    "compiled_library": "T3_inferred", "method": "T3_inferred", "other": "T3_inferred",
    "modeling": "T4_conjecture", "none": "T3_inferred", "": "T3_inferred",
}
DEFAULT_METHOD = 0.50

DIRECTNESS = {
    "target_matrix":   1.00,  # measured in the matrix the claim is about
    "analogous_matrix":0.75,  # beef claim measured in pork, pea claim in soy
    "model_system":    0.60,  # measured in a model reaction system
    "extrapolated":    0.45,  # cross-species / cross-domain inference
    "unknown":         0.55,  # <-- THE GUESS. Conditionless edges land here.
}
DEFAULT_DIRECTNESS = 0.55

PARAMS = {
    "n_saturation":      10.0,  # corroboration count at which c -> 1.0
    "beta_dependence":   0.35,  # weight of each extra source inside one group
    "lambda_contra":     0.35,  # max subtraction from contradiction mass
    "temp_tol_c":        20.0,  # |dT| above this = different condition, not disagreement
    "ph_tol":            1.0,
    "interval_slack":    0.10,  # fractional slack when testing interval overlap
    "min_weight":        0.0,
    "max_weight":        1.0,
}

# --------------------------------------------------------------------------
# 2. SAMPLE CORPUS — *** SAMPLE / ILLUSTRATIVE STRUCTURE ONLY ***
#    Used only when pipeline/out/claim_triplets_v1.json is missing.
#    Values are placeholders to exercise the algorithm. NOT citable chemistry.
# --------------------------------------------------------------------------

SAMPLE_TRIPLETS = [
    {"claim_id": "S1", "subject": "2-methyl-3-furanthiol", "predicate": "increases",
     "object": "meaty_aroma_intensity", "axis": "aroma_intensity", "polarity": "+",
     "evidence_tier": "T1_experimental", "method": "gco_aeda_quant", "directness": "target_matrix",
     "source_id": "src_124", "source_group": "grp_A",
     "conditions": {"matrix": "cooked_beef", "temp_c": 140, "ph": 5.5},
     "measurement": {"quantity": "OAV", "low": 120, "high": 180, "unit": "OAV"}},

    {"claim_id": "S2", "subject": "2-methyl-3-furanthiol", "predicate": "increases",
     "object": "meaty_aroma_intensity", "axis": "aroma_intensity", "polarity": "+",
     "evidence_tier": "T1_experimental", "method": "gcms_quantified", "directness": "target_matrix",
     "source_id": "src_137", "source_group": "grp_B",
     "conditions": {"matrix": "cooked_beef", "temp_c": 145, "ph": 5.4},
     "measurement": {"quantity": "OAV", "low": 90, "high": 200, "unit": "OAV"}},

    {"claim_id": "S3", "subject": "2-methyl-3-furanthiol", "predicate": "increases",
     "object": "meaty_aroma_intensity", "axis": "aroma_intensity", "polarity": "+",
     "evidence_tier": "T2_review", "method": "unspecified", "directness": "analogous_matrix",
     "source_id": "src_144", "source_group": "grp_B",
     "conditions": {"matrix": "cooked_pork", "temp_c": 140},
     "measurement": {}},

    # numeric conflict with S1/S2 under the SAME conditions -> real contradiction
    {"claim_id": "S4", "subject": "2-methyl-3-furanthiol", "predicate": "increases",
     "object": "meaty_aroma_intensity", "axis": "aroma_intensity", "polarity": "+",
     "evidence_tier": "T1_experimental", "method": "gcms_quantified", "directness": "target_matrix",
     "source_id": "src_155", "source_group": "grp_C",
     "conditions": {"matrix": "cooked_beef", "temp_c": 142, "ph": 5.5},
     "measurement": {"quantity": "OAV", "low": 5, "high": 12, "unit": "OAV"}},

    # polarity conflict, but DIFFERENT matrix -> condition divergence, NOT contradiction
    {"claim_id": "S5", "subject": "hexanal", "predicate": "increases",
     "object": "green_offnote_intensity", "axis": "off_note_intensity", "polarity": "+",
     "evidence_tier": "T1_experimental", "method": "sensory_trained", "directness": "target_matrix",
     "source_id": "src_311", "source_group": "grp_D",
     "conditions": {"matrix": "pea_protein_isolate", "temp_c": 25, "ph": 7.0},
     "measurement": {"quantity": "sensory_score", "low": 6.0, "high": 7.5, "unit": "pt"}},

    {"claim_id": "S6", "subject": "hexanal", "predicate": "increases",
     "object": "green_offnote_intensity", "axis": "off_note_intensity", "polarity": "-",
     "evidence_tier": "T1_experimental", "method": "sensory_trained", "directness": "target_matrix",
     "source_id": "src_333", "source_group": "grp_E",
     "conditions": {"matrix": "soy_protein_concentrate", "temp_c": 90, "ph": 4.5},
     "measurement": {"quantity": "sensory_score", "low": 1.0, "high": 2.0, "unit": "pt"}},

    # genuine polarity contradiction, same conditions
    {"claim_id": "S7", "subject": "hexanal", "predicate": "increases",
     "object": "green_offnote_intensity", "axis": "off_note_intensity", "polarity": "-",
     "evidence_tier": "T3_inferred", "method": "unspecified", "directness": "unknown",
     "source_id": "src_355", "source_group": "grp_F",
     "conditions": {"matrix": "pea_protein_isolate", "temp_c": 25},
     "measurement": {}},

    # lone, weakly-supported claim — shows the single-source floor
    {"claim_id": "S8", "subject": "thiamine", "predicate": "yields",
     "object": "2-methyl-3-furanthiol", "axis": "formation_rate", "polarity": "+",
     "evidence_tier": "T3_inferred", "method": "in_silico", "directness": "extrapolated",
     "source_id": "src_699", "source_group": "grp_G",
     "conditions": {}, "measurement": {}},
]

# --------------------------------------------------------------------------
# 2b. NORMALISER — live Layer-C schema -> internal triplet form
#     Live schema: subject/object are objects; conditions{matrix,pH,temperature_c,...};
#     measurement{method:[...],value,unit}; evidence{source_id,study_type,tier,year,...}
# --------------------------------------------------------------------------


def _first(v):
    if isinstance(v, list):
        return v[0] if v else None
    return v


def _map_method(raw):
    """Take the STRONGEST method listed (a paper that did GC-O and GC-MS did GC-O)."""
    if not raw:
        return "unspecified"
    items = raw if isinstance(raw, list) else [raw]
    best, best_v = "unspecified", -1.0
    for it in items:
        s = str(it).lower()
        for frag, key in METHOD_ALIASES:
            if frag in s and METHOD_STRENGTH[key] > best_v:
                best, best_v = key, METHOD_STRENGTH[key]
    return best


def normalise(t):
    """Accepts either the internal form (subject is a str) or the live Layer-C form."""
    if isinstance(t.get("subject"), str):
        return t
    subj, obj = t.get("subject") or {}, t.get("object") or {}
    cond, meas, ev = (t.get("conditions") or {}), (t.get("measurement") or {}), (t.get("evidence") or {})
    matrix = _first(cond.get("matrix"))
    val = meas.get("value")
    m = {}
    if isinstance(val, (int, float)):
        m = {"quantity": _first(meas.get("unit")) or "value",
             "unit": _first(meas.get("unit")), "low": float(val), "high": float(val)}
    return {
        "claim_id": t.get("claim_id"),
        "subject": subj.get("name") or subj.get("type") or "?",
        "predicate": t.get("predicate") or "relates_to",
        "object": obj.get("name") or obj.get("type") or "?",
        "axis": t.get("predicate") or "relates_to",
        "polarity": "-" if str(t.get("polarity")).startswith("neg") else "+",
        "evidence_tier": TIER_ALIASES.get(str(ev.get("tier") or ev.get("study_type")).lower(),
                                          "T3_inferred"),
        "method": _map_method(meas.get("method")),
        # matrix stated but match to the claim's target is unverified -> analogous, not target
        "directness": "analogous_matrix" if matrix else "unknown",
        "source_id": ev.get("source_id"),
        "source_group": ev.get("source_id") or t.get("claim_id"),
        "conditions": {"matrix": matrix, "temp_c": cond.get("temperature_c"), "ph": cond.get("pH")},
        "measurement": m,
        "_stored_weight": t.get("weight"),
        "_class": t.get("class"),
    }


# --------------------------------------------------------------------------
# 3. CORE SCORING
# --------------------------------------------------------------------------


def base_score(t):
    """b = evidence_tier x method_strength x directness  in (0, 1]."""
    tier = EVIDENCE_TIER.get(t.get("evidence_tier"), DEFAULT_TIER)
    meth = METHOD_STRENGTH.get(t.get("method"), DEFAULT_METHOD)
    dire = DIRECTNESS.get(t.get("directness"), DEFAULT_DIRECTNESS)
    return tier * meth * dire, tier, meth, dire


def effective_n(groups, p=PARAMS):
    """Independence-discounted source count.

    groups: {group_id: count}. First source in a group counts 1.0, each
    additional source from the same group counts beta (<1) because papers from
    one lab / citation clique are not independent evidence.
    """
    n_eff = 0.0
    for _g, k in groups.items():
        n_eff += 1.0 + p["beta_dependence"] * (k - 1)
    return max(n_eff, 1.0)


def corroboration(n_eff, p=PARAMS):
    """c = (1 + ln n_eff) / (1 + ln N_sat), capped at 1.0.

    Log, not linear: the 2nd independent replication is worth far more than the
    12th. Linear n would let volume beat quality outright.
    """
    c = (1.0 + math.log(n_eff)) / (1.0 + math.log(p["n_saturation"]))
    return min(c, 1.0)


# ---------- contradiction logic -------------------------------------------

def _cond(t, key):
    return (t.get("conditions") or {}).get(key)


def conditions_comparable(a, b, p=PARAMS):
    """Return (comparable: bool, reason: str).

    THE IMPORTANT CASE: two claims that look opposed but were measured in a
    different matrix / temperature / pH are not disagreeing. They are two facts.
    """
    ma, mb = _cond(a, "matrix"), _cond(b, "matrix")
    if ma and mb and ma != mb:
        return False, "matrix %s vs %s" % (ma, mb)
    ta, tb = _cond(a, "temp_c"), _cond(b, "temp_c")
    if ta is not None and tb is not None and abs(ta - tb) > p["temp_tol_c"]:
        return False, "temp %.0fC vs %.0fC" % (ta, tb)
    pa, pb = _cond(a, "ph"), _cond(b, "ph")
    if pa is not None and pb is not None and abs(pa - pb) > p["ph_tol"]:
        return False, "pH %.1f vs %.1f" % (pa, pb)
    return True, "conditions overlap"


def intervals_disjoint(a, b, p=PARAMS):
    ma, mb = a.get("measurement") or {}, b.get("measurement") or {}
    if not ma or not mb:
        return False, None
    if ma.get("quantity") != mb.get("quantity") or ma.get("unit") != mb.get("unit"):
        return False, None
    if any(ma.get(k) is None or mb.get(k) is None for k in ("low", "high")):
        return False, None
    s = p["interval_slack"]
    alo, ahi = ma["low"] * (1 - s), ma["high"] * (1 + s)
    blo, bhi = mb["low"] * (1 - s), mb["high"] * (1 + s)
    if ahi < blo or bhi < alo:
        return True, "[%g,%g] vs [%g,%g] %s" % (
            ma["low"], ma["high"], mb["low"], mb["high"], ma.get("unit") or "")
    return False, None


def edge_key(t):
    return (t["subject"], t.get("axis") or t["predicate"], t["object"])


def detect(triplets, p=PARAMS):
    """Pairwise pass within each (subject, axis, object) edge."""
    contradictions, divergences = [], []
    by_edge = defaultdict(list)
    for t in triplets:
        by_edge[edge_key(t)].append(t)

    skipped = 0
    for key, group in by_edge.items():
        if len(group) > 150:      # O(n^2) guard; huge edges are same-polarity duplicates
            skipped += 1
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                pol_conflict = a.get("polarity") != b.get("polarity")
                num_conflict, detail = intervals_disjoint(a, b, p)
                if not (pol_conflict or num_conflict):
                    continue
                comparable, reason = conditions_comparable(a, b, p)
                rec = {"edge": key, "a": a["claim_id"], "b": b["claim_id"],
                       "kind": "polarity" if pol_conflict else "interval",
                       "detail": detail or ("%s vs %s" % (a.get("polarity"), b.get("polarity"))),
                       "reason": reason}
                (contradictions if comparable else divergences).append(rec)
    if skipped:
        print("  [note] %d edge(s) with >150 claims skipped by the O(n^2) contradiction guard"
              % skipped, file=sys.stderr)
    return contradictions, divergences


# ---------- weighting + consensus -----------------------------------------

def score(triplets, p=PARAMS):
    contradictions, divergences = detect(triplets, p)
    contra_partners = defaultdict(set)
    for c in contradictions:
        contra_partners[c["a"]].add(c["b"])
        contra_partners[c["b"]].add(c["a"])

    by_id = {t["claim_id"]: t for t in triplets}
    bases = {}
    for t in triplets:
        b, tier, meth, dire = base_score(t)
        bases[t["claim_id"]] = (b, tier, meth, dire)

    # consensus clusters: agreeing claims on one edge, keyed by (edge, polarity,
    # condition bucket) so a condition-divergent claim forms its own cluster.
    clusters = defaultdict(list)
    for t in triplets:
        bucket = _cond(t, "matrix") or "any_matrix"
        clusters[(edge_key(t), t.get("polarity"), bucket)].append(t)

    rows = []
    for ckey, members in clusters.items():
        groups = defaultdict(int)
        for m in members:
            groups[m.get("source_group") or m.get("source_id")] += 1
        n_eff = effective_n(groups, p)
        c = corroboration(n_eff, p)

        for m in members:
            b, tier, meth, dire = bases[m["claim_id"]]
            opp = contra_partners.get(m["claim_id"], set())
            w_self = b
            w_opp = sum(bases[o][0] for o in opp if o in bases)
            frac = (w_opp / (w_opp + w_self)) if (w_opp + w_self) > 0 else 0.0
            penalty = p["lambda_contra"] * frac
            w = max(p["min_weight"], min(p["max_weight"], b * c - penalty))
            rows.append({
                "claim_id": m["claim_id"], "edge": "%s -[%s]-> %s" % ckey[0],
                "polarity": m.get("polarity"), "matrix": ckey[2],
                "tier": tier, "method": meth, "direct": dire,
                "base": b, "n_eff": n_eff, "corrob": c,
                "penalty": penalty, "weight": w,
                "conflicts": sorted(opp),
            })

    # edge weight = noisy-OR over supporting claim weights, minus noisy-OR of opposing
    edges = defaultdict(lambda: {"support": [], "oppose": []})
    for r in rows:
        side = "support" if r["polarity"] != "-" else "oppose"
        edges[(r["edge"], r["matrix"])][side].append(r["weight"])

    def noisy_or(ws):
        acc = 1.0
        for w in ws:
            acc *= (1.0 - w)
        return 1.0 - acc

    edge_rows = []
    for (e, matrix), sides in edges.items():
        s, o = noisy_or(sides["support"]), noisy_or(sides["oppose"])
        edge_rows.append({"edge": e, "matrix": matrix, "n_support": len(sides["support"]),
                          "n_oppose": len(sides["oppose"]), "support": s, "oppose": o,
                          "edge_weight": max(0.0, s - o)})

    rows.sort(key=lambda r: -r["weight"])
    edge_rows.sort(key=lambda r: -r["edge_weight"])
    return rows, edge_rows, contradictions, divergences, by_id


# --------------------------------------------------------------------------
# 4. REPORT
# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    default_json = os.path.normpath(os.path.join(here, "..", "..", "pipeline", "out",
                                                 "claim_triplets_v1.json"))
    ap.add_argument("--json", default=default_json)
    ap.add_argument("--params", nargs="*", default=[], help="override e.g. lambda_contra=0.5")
    ap.add_argument("--top", type=int, default=20, help="rows to print per table")
    args = ap.parse_args()

    for kv in args.params:
        k, _, v = kv.partition("=")
        if k in PARAMS:
            PARAMS[k] = float(v)
        else:
            sys.exit("unknown param: %s (known: %s)" % (k, ", ".join(sorted(PARAMS))))

    if os.path.exists(args.json):
        with open(args.json) as f:
            data = json.load(f)
        triplets = data.get("triplets", data) if isinstance(data, dict) else data
        origin = "LIVE  %s  (%d triplets)" % (args.json, len(triplets))
    else:
        triplets = SAMPLE_TRIPLETS
        origin = ("*** SAMPLE DATA *** (%s not found) — illustrative structure only, "
                  "NOT verified chemistry, do not cite" % args.json)

    triplets = [normalise(t) for t in triplets]
    rows, edges, contras, divs, by_id = score(triplets)

    print("=" * 108)
    print("MeatCODE claim weighting — w = tier x method x directness x corroboration - contradiction")
    print("source: " + origin)
    print("=" * 108)

    hdr = ("%-6s %-46s %-4s %5s %5s %5s %6s %6s %6s %6s %6s"
           % ("claim", "edge", "pol", "tier", "meth", "dir", "base", "n_eff", "corr", "pen", "W"))
    print("\n[0] CORPUS SUMMARY")
    ws = [r["weight"] for r in rows]
    ws_sorted = sorted(ws)
    def q(p):
        return ws_sorted[min(len(ws_sorted) - 1, int(p * len(ws_sorted)))]
    print("  claims scored      : %d   distinct edges: %d" % (len(rows), len(edges)))
    print("  weight  min/med/max: %.3f / %.3f / %.3f    p90 %.3f" % (
        ws_sorted[0], q(0.5), ws_sorted[-1], q(0.9)))
    print("  contradictions     : %d      condition divergences: %d" % (len(contras), len(divs)))
    tiers = defaultdict(int)
    for t in triplets:
        tiers[t.get("evidence_tier")] += 1
    print("  tier mix           : " + "  ".join("%s=%d" % kv for kv in sorted(tiers.items())))
    stored = [(t["_stored_weight"], next((r["weight"] for r in rows
                                          if r["claim_id"] == t["claim_id"]), None))
              for t in triplets[:400] if t.get("_stored_weight") is not None]
    stored = [(a, b) for a, b in stored if b is not None]
    if stored:
        da = sum(abs(a - b) for a, b in stored) / len(stored)
        print("  vs stored `weight` (first 400): mean |diff| %.3f  "
              "(stored mean %.3f, recomputed mean %.3f)" % (
                  da, sum(a for a, _ in stored) / len(stored),
                  sum(b for _, b in stored) / len(stored)))

    print("\n[1] RANKED CLAIMS (top %d of %d)" % (min(args.top, len(rows)), len(rows)))
    print(hdr)
    print("-" * 108)
    for r in rows[:args.top]:
        print("%-6s %-46s %-4s %5.2f %5.2f %5.2f %6.3f %6.2f %6.3f %6.3f %6.3f" % (
            r["claim_id"], r["edge"][:46], r["polarity"], r["tier"], r["method"],
            r["direct"], r["base"], r["n_eff"], r["corrob"], r["penalty"], r["weight"]))

    print("\n[2] CONTRADICTIONS (comparable conditions — genuine disagreement) — showing %d of %d"
          % (min(args.top, len(contras)), len(contras)))
    if not contras:
        print("  none")
    for c in contras[:args.top]:
        print("  %s <-> %s  [%s]  %s   (%s)" % (c["a"], c["b"], c["kind"], c["detail"], c["reason"]))

    print("\n[3] CONDITION DIVERGENCES (look opposed, are NOT — different context) — showing %d of %d"
          % (min(args.top, len(divs)), len(divs)))
    if not divs:
        print("  none")
    for d in divs[:args.top]:
        print("  %s <-> %s  [%s]  %s   -> split by %s" % (
            d["a"], d["b"], d["kind"], d["detail"], d["reason"]))

    print("\n[4] CONSENSUS EDGES (noisy-OR over agreeing claims, per condition bucket) — top %d of %d"
          % (min(args.top, len(edges)), len(edges)))
    print("%-46s %-26s %4s %4s %7s %7s %8s" % (
        "edge", "matrix", "n+", "n-", "supp", "opp", "EDGE_W"))
    print("-" * 108)
    for e in edges[:args.top]:
        print("%-46s %-26s %4d %4d %7.3f %7.3f %8.3f" % (
            e["edge"][:46], e["matrix"][:26], e["n_support"], e["n_oppose"],
            e["support"], e["oppose"], e["edge_weight"]))
    print()


if __name__ == "__main__":
    main()
