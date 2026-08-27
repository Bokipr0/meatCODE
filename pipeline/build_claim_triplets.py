#!/usr/bin/env python3
"""
build_claim_triplets.py  --  MeatCODE reified claim-triplet builder (v1)

Builds REIFIED claim nodes (the claim is the node, not a flat edge) from data that
ALREADY EXISTS in Neon.  Nothing is invented: every field carries a `provenance`
string naming the tables/columns it was derived from.  Unknown == null, never guessed.

Triplet classes
  A  molecule  --contributes_to-->  odour/sensory descriptor   (molecule_odours x odours)
  B  molecule  --reported_in-->     paper                      (source_molecules curated + text-mined)
  C  molecule  --formed_by-->       pathway                    (meaty_volatile_library.likely_process, sources.pathway)
  D  paper     --asserts-->         claim statement            (sources.main_claim + facets)  [1 per paper = a limitation]
  E  molecule  --curated_claim-->   claim statement            (claims / claim_molecules / claim_sources)

Weight
  raw = evidence_tier * method_strength * directness * corroboration - contradiction_penalty
  normalised to 0-1 by the max raw observed in the run; components kept for audit.

Output: pipeline/out/claim_triplets_v1.json  (+ .csv flat view)
Read-only against the DB.  No writes, no DDL.
"""
import os
import re
import csv
import json
import math
from pathlib import Path
from collections import defaultdict

import psycopg2
import psycopg2.extras

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "pipeline" / "out"
OUT_JSON = OUT_DIR / "claim_triplets_v1.json"
OUT_CSV = OUT_DIR / "claim_triplets_v1.csv"


def db():
    url = os.environ.get("DATABASE_URL")
    if not url:
        for line in (REPO / ".env").read_text().splitlines():
            if line.strip().startswith("DATABASE_URL"):
                url = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    if not url:
        raise SystemExit("DATABASE_URL not found")
    return psycopg2.connect(url)


# ---------------------------------------------------------------- scoring ---
def evidence_tier(study_type):
    """sources.study_type -> tier factor"""
    st = (study_type or "").lower()
    if st == "experimental":
        return 1.0, "experimental"
    if st == "review":
        return 0.8, "review"
    if st in ("method", "modeling", "other"):
        return 0.6, st
    return 0.6, "unknown"


def method_strength(methods):
    """sources.method (text[]) -> strongest method factor present"""
    ms = [m.lower() for m in (methods or [])]
    if not ms:
        return 0.4, None
    best, label = 0.4, None
    for m in ms:
        if "olfactometr" in m or "oav" in m or "sniff" in m:
            v = 1.0
        elif "panel" in m or "descriptive analysis" in m or "sensory" in m:
            v = 0.9
        elif "gc-ms" in m or "gc/ms" in m or "spme" in m or "metabolomic" in m or "lipidomic" in m:
            v = 0.8
        else:
            v = 0.4
        if v > best:
            best, label = v, m
    return best, label


MEAT_MATRIX = re.compile(
    r"beef|pork|chicken|steak|sausage|burger|meat|broth|stock|duck|lamb|pigeon|turkey|fish|bacon|ham",
    re.I,
)
ANALOGUE_MATRIX = re.compile(r"analogue|analog|plant protein|pea|soy|hybrid|cultivated|fermentation-derived|fat system|seasoning|process flavor", re.I)


def directness(matrices):
    """sources.matrix (text[]) -> directness factor"""
    mx = matrices or []
    if not mx:
        return 0.5, None
    joined = " | ".join(mx)
    if MEAT_MATRIX.search(joined) and "analogue" not in joined.lower():
        return 1.0, joined
    if ANALOGUE_MATRIX.search(joined):
        return 0.7, joined
    if re.search(r"model system", joined, re.I):
        return 0.5, joined
    return 0.5, joined


def norm_key(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


# ------------------------------------------------------------------ build ---
def main():
    conn = db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # ---- reference data -----------------------------------------------
    cur.execute("""
        select id, name, year, study_type, method, matrix, pathway,
               compound_class, sensory_descriptor, main_claim, abstract,
               citation_count, relevance_llm, priority_score, doi, is_review
        from sources
    """)
    sources = {r["id"]: r for r in cur.fetchall()}

    cur.execute("""
        select id, name, cas_number, inchikey, pubchem_cid, category, is_junk
        from molecules where coalesce(is_junk,false) = false
    """)
    molecules = {r["id"]: r for r in cur.fetchall()}

    cur.execute("select id, name, odour_category from odours")
    odours = {r["id"]: r for r in cur.fetchall()}

    cur.execute("select molecule_id, odour_id from molecule_odours")
    mol_odour = cur.fetchall()

    cur.execute("select source_id, molecule_id from source_molecules")
    curated_bridge = {(r["source_id"], r["molecule_id"]) for r in cur.fetchall()}

    cur.execute("""
        select entry_no, cas_number, compound, likely_process, chemical_group,
               subgroup, odor_descriptor, odor_threshold, beef_relevance_score,
               cooked_meats_reported
        from meaty_volatile_library
    """)
    mvl = cur.fetchall()

    cur.execute("select id, claim_text, stance, confidence, notes, evidence_snippet from claims")
    claims = {r["id"]: r for r in cur.fetchall()}
    cur.execute("select claim_id, source_id from claim_sources")
    claim_sources = defaultdict(list)
    for r in cur.fetchall():
        claim_sources[r["claim_id"]].append(r["source_id"])
    cur.execute("select claim_id, molecule_id from claim_molecules")
    claim_molecules = defaultdict(list)
    for r in cur.fetchall():
        claim_molecules[r["claim_id"]].append(r["molecule_id"])

    triplets = []
    stats = defaultdict(int)

    def source_context(src):
        """Return (conditions, measurement, evidence, factors) from ONE sources row."""
        if src is None:
            return (
                {"matrix": None, "pH": None, "temperature_c": None, "time_min": None, "process": None},
                {"method": None, "value": None, "unit": None},
                {"source_id": None, "study_type": None, "tier": None, "year": None, "citation_count": None},
                (0.6, 0.4, 0.5, "unknown", None, None),
            )
        et, et_label = evidence_tier(src["study_type"])
        msv, m_label = method_strength(src["method"])
        dv, d_label = directness(src["matrix"])
        conditions = {
            # sources.matrix is the only condition column that is actually populated.
            "matrix": (src["matrix"] or None) and list(src["matrix"]),
            "pH": None,            # processes.ph  -> table is EMPTY (0 rows)
            "temperature_c": None,  # processes.temperature_c -> EMPTY
            "time_min": None,       # processes.time_min -> EMPTY
            "process": (src["pathway"] or None) and list(src["pathway"]),
        }
        measurement = {
            "method": (src["method"] or None) and list(src["method"]),
            "value": None,  # no numeric measurement column exists anywhere in the schema
            "unit": None,
        }
        evidence = {
            "source_id": src["id"],
            "study_type": src["study_type"],
            "tier": et_label,
            "year": src["year"],
            "citation_count": src["citation_count"],
        }
        return conditions, measurement, evidence, (et, msv, dv, et_label, m_label, d_label)

    def add(cid, cls, subj, pred, obj, src, provenance, polarity="positive",
            override=None, group_key=None):
        conditions, measurement, evidence, (et, msv, dv, *_l) = source_context(src)
        if override:
            conditions.update(override.get("conditions", {}))
            measurement.update(override.get("measurement", {}))
            evidence.update(override.get("evidence", {}))
            et = override.get("evidence_tier", et)
            msv = override.get("method_strength", msv)
            dv = override.get("directness", dv)
        triplets.append({
            "claim_id": cid,
            "class": cls,
            "subject": subj,
            "predicate": pred,
            "object": obj,
            "polarity": polarity,
            "conditions": conditions,
            "measurement": measurement,
            "evidence": evidence,
            "weight": None,
            "weight_components": {
                "evidence_tier": round(et, 3),
                "method_strength": round(msv, 3),
                "directness": round(dv, 3),
                "corroboration": None,
                "contradiction_penalty": 0.0,
            },
            "provenance": provenance,
            "_group": group_key or (
                f"{subj.get('type')}:{subj.get('id')}|{pred}|{obj.get('type')}:{obj.get('id') or norm_key(obj.get('name'))}"
            ),
        })
        stats[cls] += 1

    # ---- CLASS A: molecule -contributes_to-> sensory descriptor -------
    for r in mol_odour:
        m = molecules.get(r["molecule_id"])
        o = odours.get(r["odour_id"])
        if not m or not o:
            continue
        add(
            f"A-{m['id']}-{o['id']}",
            "A_molecule_contributes_to_descriptor",
            {"type": "molecule", "id": m["id"], "name": m["name"], "inchikey": m["inchikey"]},
            "contributes_to",
            {"type": "sensory_descriptor", "id": o["id"], "name": o["name"],
             "category": o["odour_category"]},
            None,
            "derived:molecule_odours(molecule_id,odour_id) x odours(name,odour_category) x molecules(name,inchikey)",
        )

    # ---- CLASS B: molecule -reported_in-> paper -----------------------
    # B1 curated bridge (source_molecules)
    for (sid, mid) in curated_bridge:
        m, s = molecules.get(mid), sources.get(sid)
        if not m or not s:
            continue
        add(
            f"B-cur-{sid}-{mid}",
            "B_molecule_reported_in_paper",
            {"type": "molecule", "id": m["id"], "name": m["name"], "inchikey": m["inchikey"]},
            "reported_in",
            {"type": "paper", "id": s["id"], "name": s["name"]},
            s,
            "derived:source_molecules(curated) x sources(matrix,pathway,method,study_type,year,citation_count)",
        )

    # B2 text-mined bridge: molecule name occurring in the paper's own text fields.
    # Honest, reproducible, lower provenance grade than the curated bridge.
    name_index = []
    for mid, m in molecules.items():
        nm = (m["name"] or "").strip().lower()
        if len(nm) < 6 or nm.isdigit():
            continue
        name_index.append((mid, nm, re.compile(r"(?<![a-z0-9])" + re.escape(nm) + r"(?![a-z0-9])")))
    for sid, s in sources.items():
        blob = " ".join(filter(None, [
            s["name"], s["main_claim"], s["abstract"],
            " ".join(s["compound_class"] or []),
            " ".join(s["sensory_descriptor"] or []),
        ])).lower()
        if not blob:
            continue
        for mid, nm, rx in name_index:
            if nm in blob and rx.search(blob):
                if (sid, mid) in curated_bridge:
                    continue
                m = molecules[mid]
                add(
                    f"B-min-{sid}-{mid}",
                    "B_molecule_reported_in_paper",
                    {"type": "molecule", "id": m["id"], "name": m["name"], "inchikey": m["inchikey"]},
                    "reported_in",
                    {"type": "paper", "id": s["id"], "name": s["name"]},
                    s,
                    "derived:text-mined molecules.name in sources(name,main_claim,compound_class,sensory_descriptor) x sources facets",
                )

    # ---- CLASS C: molecule -formed_by-> pathway -----------------------
    cas_to_mol = defaultdict(list)
    for mid, m in molecules.items():
        if m["cas_number"]:
            cas_to_mol[m["cas_number"].strip()].append(mid)
    PROC_MAP = {"Maillard": ["Maillard reaction"], "Lipid oxidation": ["Lipid oxidation"],
                "Both": ["Maillard reaction", "Lipid oxidation"]}
    for r in mvl:
        cas = (r["cas_number"] or "").strip()
        for mid in cas_to_mol.get(cas, []):
            m = molecules[mid]
            for pw in PROC_MAP.get(r["likely_process"], [r["likely_process"]] if r["likely_process"] else []):
                add(
                    f"C-mvl-{r['entry_no']}-{mid}-{norm_key(pw)}",
                    "C_molecule_formed_by_pathway",
                    {"type": "molecule", "id": m["id"], "name": m["name"], "inchikey": m["inchikey"]},
                    "formed_by",
                    {"type": "pathway", "id": norm_key(pw), "name": pw},
                    None,
                    "derived:meaty_volatile_library(cas_number,likely_process,chemical_group,odor_threshold,beef_relevance_score) x molecules.cas_number",
                    override={
                        "conditions": {
                            "matrix": ([r["cooked_meats_reported"]]
                                       if r["cooked_meats_reported"] else None),
                            "process": [pw],
                        },
                        "measurement": {
                            "method": ["literature-compiled volatile library"],
                            "value": r["odor_threshold"],
                            "unit": "odor threshold (as recorded in meaty_volatile_library.odor_threshold)",
                        },
                        "evidence": {"source_id": None, "study_type": "compiled_library",
                                     "tier": "compiled_library", "year": None, "citation_count": None},
                        "evidence_tier": 0.8,
                        "method_strength": 0.8 if r["odor_threshold"] else 0.4,
                        "directness": 1.0,  # library is beef/cooked-meat scoped by construction
                    },
                )

    # C2: pathway attribution carried by the paper a molecule is reported in
    for t in list(triplets):
        if t["class"] != "B_molecule_reported_in_paper":
            continue
        for pw in (t["conditions"]["process"] or []):
            add(
                f"C-src-{t['evidence']['source_id']}-{t['subject']['id']}-{norm_key(pw)}",
                "C_molecule_formed_by_pathway",
                t["subject"],
                "formed_by",
                {"type": "pathway", "id": norm_key(pw), "name": pw},
                sources.get(t["evidence"]["source_id"]),
                "derived:(molecule reported_in paper) x sources.pathway",
            )

    # ---- CLASS D: paper-level claim node ------------------------------
    for sid, s in sources.items():
        if not s["main_claim"]:
            continue
        add(
            f"D-{sid}",
            "D_paper_asserts_claim",
            {"type": "paper", "id": sid, "name": s["name"]},
            "asserts",
            {"type": "claim_statement", "id": f"main_claim:{sid}", "name": s["main_claim"]},
            s,
            "derived:sources.main_claim x sources(matrix,pathway,method,study_type,year,citation_count,compound_class,sensory_descriptor)",
            group_key=f"paperclaim|{norm_key(s['main_claim'])[:120]}",
        )

    # ---- CLASS E: existing curated claims -----------------------------
    NEG = re.compile(r"\b(decreas|reduc|inhibit|suppress|mask|lower|no (?:significant )?effect|does not|not associated)\w*", re.I)
    for cid, c in claims.items():
        srcs = [sources.get(x) for x in claim_sources.get(cid, [])] or [None]
        mols = claim_molecules.get(cid, []) or [None]
        polarity = "negative" if c["stance"] == "contradicts" else "positive"
        if NEG.search(c["claim_text"] or ""):
            polarity = "negative"
        for mid in mols:
            m = molecules.get(mid) if mid else None
            subj = ({"type": "molecule", "id": m["id"], "name": m["name"], "inchikey": m["inchikey"]}
                    if m else {"type": "claim_only", "id": None, "name": None})
            for s in srcs:
                add(
                    f"E-{cid}-{mid}-{s['id'] if s else 'nosrc'}",
                    "E_curated_claim",
                    subj,
                    "curated_claim",
                    {"type": "claim_statement", "id": f"claim:{cid}", "name": c["claim_text"]},
                    s,
                    "derived:claims(claim_text,stance,confidence) x claim_molecules x claim_sources x sources facets",
                    polarity=polarity,
                    override={"evidence": {"curated_confidence": float(c["confidence"]) if c["confidence"] is not None else None,
                                           "stance": c["stance"]}},
                    group_key=f"E|mol:{mid}|{norm_key(c['claim_text'])[:120]}",
                )

    # ---- corroboration + contradiction --------------------------------
    groups = defaultdict(list)
    for t in triplets:
        groups[t["_group"]].append(t)

    # contradiction: same subject + semantically-same object, opposing polarity.
    # For free-text claim statements the object id is unique per row, so we key on the
    # normalised claim wording with polarity words stripped -- otherwise a "supports" and a
    # "contradicts" version of the same assertion could never collide.
    POLWORDS = re.compile(r"\b(increas\w*|decreas\w*|reduc\w*|enhanc\w*|inhibit\w*|suppress\w*|mask\w*|not|no|does)\b", re.I)

    def obj_key(t):
        o = t["object"]
        if o.get("type") == "claim_statement":
            return POLWORDS.sub("", norm_key(o.get("name")))[:160]
        return o.get("id") or norm_key(o.get("name"))

    so_groups = defaultdict(set)
    so_members = defaultdict(list)
    for t in triplets:
        k = (t["subject"].get("type"), t["subject"].get("id"),
             t["object"].get("type"), obj_key(t))
        so_groups[k].add(t["polarity"])
        so_members[k].append(t)
    contradicted = {k for k, pol in so_groups.items() if len(pol) > 1}
    n_contradiction_pairs = len(contradicted)
    contradicted_triplets = 0

    for t in triplets:
        g = groups[t["_group"]]
        # independent = distinct source_ids backing the same S-P-O
        n_ind = len({x["evidence"]["source_id"] for x in g if x["evidence"]["source_id"]}) or 1
        corrob = 1.0 + math.log(n_ind)
        k = (t["subject"].get("type"), t["subject"].get("id"),
             t["object"].get("type"), obj_key(t))
        pen = 0.25 if k in contradicted else 0.0
        if pen:
            contradicted_triplets += 1
        wc = t["weight_components"]
        wc["corroboration"] = round(corrob, 3)
        wc["contradiction_penalty"] = pen
        wc["n_independent_sources"] = n_ind
        t["_raw"] = wc["evidence_tier"] * wc["method_strength"] * wc["directness"] * corrob - pen

    max_raw = max((t["_raw"] for t in triplets), default=1.0) or 1.0
    for t in triplets:
        t["weight"] = round(max(0.0, min(1.0, t["_raw"] / max_raw)), 4)
        t.pop("_raw", None)

    consensus = {k: len({x["evidence"]["source_id"] for x in v if x["evidence"]["source_id"]})
                 for k, v in groups.items()}
    consensus_clusters = {k: n for k, n in consensus.items() if n >= 2}

    for t in triplets:
        t.pop("_group", None)

    # ---- write --------------------------------------------------------
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(triplets, indent=2, default=str))
    with OUT_CSV.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["claim_id", "class", "subject_type", "subject_id", "subject_name",
                    "predicate", "object_type", "object_id", "object_name", "polarity",
                    "matrix", "process", "method", "study_type", "year", "citation_count",
                    "weight", "n_independent_sources", "provenance"])
        for t in triplets:
            w.writerow([
                t["claim_id"], t["class"], t["subject"]["type"], t["subject"]["id"], t["subject"]["name"],
                t["predicate"], t["object"]["type"], t["object"]["id"], (t["object"]["name"] or "")[:200],
                t["polarity"],
                "|".join(t["conditions"]["matrix"] or []), "|".join(t["conditions"]["process"] or []),
                "|".join(t["measurement"]["method"] or []),
                t["evidence"].get("study_type"), t["evidence"].get("year"), t["evidence"].get("citation_count"),
                t["weight"], t["weight_components"]["n_independent_sources"], t["provenance"],
            ])

    # ---- report -------------------------------------------------------
    n = len(triplets)
    mols_cov = {t["subject"]["id"] for t in triplets if t["subject"]["type"] == "molecule"}
    papers_cov = {t["evidence"]["source_id"] for t in triplets if t["evidence"]["source_id"]}
    with_matrix = sum(1 for t in triplets if t["conditions"]["matrix"])
    with_process = sum(1 for t in triplets if t["conditions"]["process"])
    with_method = sum(1 for t in triplets if t["measurement"]["method"])
    with_value = sum(1 for t in triplets if t["measurement"]["value"] not in (None, ""))
    fully_null_cond = sum(1 for t in triplets
                          if not t["conditions"]["matrix"] and not t["conditions"]["process"])
    numeric_cond = sum(1 for t in triplets if any(
        t["conditions"][k] is not None for k in ("pH", "temperature_c", "time_min")))

    print("\n" + "=" * 78)
    print("MeatCODE reified claim-triplets v1  —  build report")
    print("=" * 78)
    print(f"{'TRIPLETS BY CLASS':<52}{'COUNT':>10}{'% TOTAL':>14}")
    print("-" * 78)
    for cls in sorted(stats):
        print(f"{cls:<52}{stats[cls]:>10}{100*stats[cls]/n:>13.1f}%")
    print("-" * 78)
    print(f"{'TOTAL':<52}{n:>10}{100.0:>13.1f}%")
    print()
    print(f"{'COVERAGE':<52}{'COUNT':>10}{'% OF POOL':>14}")
    print("-" * 78)
    print(f"{'molecules appearing as a subject':<52}{len(mols_cov):>10}{100*len(mols_cov)/len(molecules):>13.1f}%")
    print(f"{'papers cited as evidence':<52}{len(papers_cov):>10}{100*len(papers_cov)/len(sources):>13.1f}%")
    print()
    print(f"{'CONDITIONS / MEASUREMENT FILL':<52}{'COUNT':>10}{'% TRIPLETS':>14}")
    print("-" * 78)
    print(f"{'has matrix (real value)':<52}{with_matrix:>10}{100*with_matrix/n:>13.1f}%")
    print(f"{'has process/pathway (real value)':<52}{with_process:>10}{100*with_process/n:>13.1f}%")
    print(f"{'has method (real value)':<52}{with_method:>10}{100*with_method/n:>13.1f}%")
    print(f"{'has numeric measurement value':<52}{with_value:>10}{100*with_value/n:>13.1f}%")
    print(f"{'has pH / temperature / time':<52}{numeric_cond:>10}{100*numeric_cond/n:>13.1f}%")
    print(f"{'ZERO conditions (matrix+process both null)':<52}{fully_null_cond:>10}{100*fully_null_cond/n:>13.1f}%")
    print()
    print(f"{'CONSENSUS / CONFLICT':<52}{'COUNT':>10}")
    print("-" * 78)
    print(f"{'distinct S-P-O groups':<52}{len(groups):>10}")
    print(f"{'consensus clusters (>=2 independent sources)':<52}{len(consensus_clusters):>10}")
    print(f"{'max independent sources on one S-P-O':<52}{max(consensus.values(), default=0):>10}")
    print(f"{'contradicted subject-object pairs':<52}{n_contradiction_pairs:>10}")
    print(f"{'triplets carrying a contradiction penalty':<52}{contradicted_triplets:>10}")
    print()
    print(f"weight: normalised 0-1 (raw / max_raw={max_raw:.3f}); components kept per triplet")
    print(f"written: {OUT_JSON}")
    print(f"written: {OUT_CSV}")

    top = sorted(consensus_clusters.items(), key=lambda kv: -kv[1])[:8]
    if top:
        print("\nTOP CONSENSUS CLUSTERS (S-P-O backed by most independent papers)")
        for k, v in top:
            print(f"  {v:>3} sources  {k[:100]}")

    if contradicted:
        print("\nCONTRADICTED SUBJECT-OBJECT PAIRS")
        for k in list(contradicted)[:10]:
            names = {m["subject"]["name"] for m in so_members[k]}
            pol = {m["polarity"] for m in so_members[k]}
            print(f"  {k[0]}:{k[1]} x {k[2]} -> polarities {sorted(pol)}  subj={list(names)[:1]}")

    conn.close()


if __name__ == "__main__":
    main()
