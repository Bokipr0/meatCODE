#!/usr/bin/env python3
"""
MeatCODE Knowledge Graph — MVP builder
Last updated: 2026-08-15 · Advisory · builds TWO graphs from the live Neon corpus and the
bridge between them, then exports one JSON the explorer + the chatbot retrieval demo both read.

WHY TWO GRAPHS (and one bridge)
-------------------------------
  MOLECULE KG — deep chemistry. Nodes: molecules · odours · chemical groups/subgroups ·
    processes. Edges carry the chemistry: which compound smells of what, which compounds
    share an aroma profile, which chemical family they belong to, which cooking process
    generates them. Answers "what else behaves like this compound".

  PAPER KG — the literature. Nodes: sources · topics · tags · the LLM-extracted facets
    (pathway / method / matrix / compound_class / study_type). Answers "who else studied
    this, with what method, in what matrix".

  THE BRIDGE is the point. `source_molecules` currently holds 23 rows for 818 papers, so
  the two halves of MeatCODE are effectively disconnected: you cannot walk from a compound
  to the papers that discuss it. This script MINES that bridge by matching molecule names
  against each paper's abstract + main_claim, so the graph becomes one connected object.
  Mined edges are written with provenance ('mined') and are never confused with curated ones.

Run:
    python3 kg/build_kg.py                # build + write kg/kg_data.json
    python3 kg/build_kg.py --stats-only   # just print what's there
Reads DATABASE_URL from .env (never printed).
"""

import json, os, re, sys, itertools, argparse
from collections import defaultdict, Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)


def db_url():
    for line in open(os.path.join(REPO, ".env"), encoding="utf-8"):
        if line.strip().startswith("DATABASE_URL"):
            return line.split("=", 1)[1].strip()
    raise SystemExit("DATABASE_URL not found in .env")


def norm(s):
    """Normalise a chemical name for matching: lowercase, strip hyphens/spaces/commas.
    '2-Acetyl-pyrazine' and '2 acetylpyrazine' must collide, or the bridge silently misses."""
    return re.sub(r"[\s\-,']", "", (s or "").lower())


# Names too generic to match safely in free text — matching these would flood the graph
# with false edges ('water' appears in every paper and means nothing).
STOP_NAMES = {
    "water", "oxygen", "nitrogen", "air", "salt", "sugar", "acid", "ester", "ketone",
    "alcohol", "aldehyde", "amine", "protein", "fat", "oil", "ash", "gas", "iron", "heme",
}

# Rows that are in `molecules` but are not molecules. These are data-quality bugs in the
# table; the builder reports them so they can be cleaned at source rather than silently
# generating hundreds of nonsense edges.
JUNK_NAMES = {
    "decline", "increase", "decrease", "control", "response", "sample", "mixture",
    "extract", "residue", "fraction", "volatile", "volatiles", "compound", "compounds",
    "flavour", "flavor", "aroma", "odour", "odor", "taste", "texture", "quality",
}


def fetch(cur, q, args=None):
    cur.execute(q, args or ())
    return cur.fetchall()


def build(stats_only=False):
    import psycopg2
    conn = psycopg2.connect(db_url())
    cur = conn.cursor()

    # ---------------- MOLECULE KG ----------------
    molecules = fetch(cur, """
        select id, name, coalesce(category,'Uncategorised')
        from molecules order by id""")
    odours = fetch(cur, "select id, name, coalesce(odour_category,'other') from odours order by id")
    mol_od = fetch(cur, "select molecule_id, odour_id from molecule_odours")

    # The Meaty Volatile Library is the curated chemistry backbone: CAS numbers, chemical
    # group/subgroup, retention indices, odour thresholds, process attribution, beef relevance.
    mvl = fetch(cur, """
        select entry_no, compound, cas_number, chemical_group, subgroup, likely_process,
               odor_descriptor, odor_threshold, beef_relevance_score, cooked_meats_reported
        from meaty_volatile_library""")

    # ---------------- PAPER KG ----------------
    sources = fetch(cur, """
        select id, name, year, journal, citation_count, relevance_llm, priority_score,
               study_type, pathway, method, matrix, compound_class, sensory_descriptor,
               main_claim, abstract, is_review
        from sources order by id""")
    topics = fetch(cur, "select id, name, coalesce(root_branch,''), level from topics")
    src_top = fetch(cur, "select source_id, topic_id from source_topics")
    tags = fetch(cur, "select id, name, category from tags")
    src_tag = fetch(cur, "select source_id, tag_id from source_tags")

    # curated bridges that already exist
    src_mol_curated = fetch(cur, "select source_id, molecule_id from source_molecules")
    claims = fetch(cur, "select id, claim_text, stance, confidence from claims")
    claim_mol = fetch(cur, "select claim_id, molecule_id from claim_molecules")
    claim_src = fetch(cur, "select claim_id, source_id from claim_sources")
    conn.close()

    # ---------------- MINE THE BRIDGE ----------------
    # Match molecule names inside abstract + main_claim. Word-boundary-ish matching on a
    # normalised string; short and generic names are skipped. Every hit is provenance-tagged
    # 'mined' so a reviewer can accept/reject it separately from curated data.
    def _txt(x):
        if x is None:
            return ""
        if isinstance(x, (list, tuple)):
            return " ".join(str(v) for v in x if v)
        return str(x)

    def minable(name):
        """Is this name safe to look for in free text?

        Two failure modes to avoid. (1) Junk rows in `molecules` that are ordinary English
        words — 'Decline' is in the table and would match 20 abstracts discussing a decline
        in something. (2) Names so generic they carry no information ('water'). We accept a
        name when it looks chemical: it has a digit or hyphen, or a recognisable suffix."""
        low = name.strip().lower()
        if len(low) < 5 or low in STOP_NAMES or low in JUNK_NAMES:
            return False
        if re.search(r"[0-9\-]", low):
            return True
        return bool(re.search(
            r"(ol|al|one|ene|ane|yne|ate|ide|ine|thiol|furan|pyrazine|pyrrole|acid|"
            r"ester|aldehyde|phenol|lactone|amine|anol|enal|dienal)$", low))

    def name_regex(name):
        """Match the name allowing flexible separators, tolerating a plural 's', and refusing
        to fire inside a longer chemical token — otherwise bare 'pyrazine' matches
        'methylpyrazine' and the parent term swallows all of its own derivatives."""
        parts = [re.escape(p) for p in re.split(r"[\s\-,']+", name.strip()) if p]
        if not parts:
            return None
        body = r"[\s\-]*".join(parts)
        return re.compile(r"(?<![A-Za-z0-9])" + body + r"s?(?![A-Za-z0-9])", re.I)

    # Longest name first, so 'ethyl acetate' claims the span before bare 'acetate' can.
    cand = [(mid, name) for mid, name, *_ in molecules if minable(name)]
    cand.sort(key=lambda x: -len(x[1]))
    compiled = [(mid, name, name_regex(name)) for mid, name in cand]
    compiled = [c for c in compiled if c[2]]
    skipped = [name for mid, name, *_ in molecules if not minable(name)]

    mined = []
    for s in sources:
        sid = s[0]
        text = _txt(s[14]) + " \n " + _txt(s[13])       # abstract + main_claim
        if not text.strip():
            continue
        taken = []                                      # spans already claimed by a longer name
        for mid, name, rx in compiled:
            for m in rx.finditer(text):
                a, b = m.span()
                if any(a < tb and ta < b for ta, tb in taken):
                    continue                            # overlaps a longer, more specific match
                taken.append((a, b))
                mined.append((sid, mid))
                break                                   # one edge per (paper, molecule)
    mined_set = set(mined)
    curated_set = set((a, b) for a, b in src_mol_curated)

    # ---------------- CHEMISTRY EDGES: shared-aroma similarity ----------------
    # Two compounds that share several odour descriptors behave alike in a formulation.
    # Jaccard over odour sets; keep only strong, non-trivial overlaps or the graph turns to soup.
    od_of = defaultdict(set)
    for mid, oid in mol_od:
        od_of[mid].add(oid)
    mol_ids = [m[0] for m in molecules if len(od_of[m[0]]) >= 2]
    sim_edges = []
    for a, b in itertools.combinations(mol_ids, 2):
        A, B = od_of[a], od_of[b]
        inter = len(A & B)
        if inter >= 2:
            j = inter / len(A | B)
            # Either a strong proportional overlap, or a lot of descriptors in common.
            if j >= 0.34 or inter >= 4:
                sim_edges.append((a, b, round(j, 3), inter))
    sim_edges.sort(key=lambda e: (-e[3], -e[2]))
    sim_edges = sim_edges[:6000]

    # ---------------- MVL ↔ molecules (gives molecules their CAS + chemical family) ----------------
    mvl_by_norm = {norm(r[1]): r for r in mvl}
    mol_mvl = []
    for mid, name, *_ in molecules:
        hit = mvl_by_norm.get(norm(name))
        if hit:
            mol_mvl.append((mid, hit[0]))

    # ---------------- PAPER↔PAPER edges via shared facets ----------------
    # Several of these columns are Postgres text[] (a paper can use 3 methods), so flatten
    # scalars and arrays into one list of values before indexing.
    def vals(x):
        if x is None:
            return []
        if isinstance(x, (list, tuple)):
            return [str(v).strip() for v in x if v is not None and str(v).strip()]
        s = str(x).strip()
        return [s] if s else []

    BAD = {"", "none", "n/a", "na", "unknown", "not specified", "not reported", "null"}
    facet_index = defaultdict(list)   # (facet, value) -> [source_id]
    FACETS = {"study_type": 7, "pathway": 8, "method": 9, "matrix": 10, "compound_class": 11}
    for s in sources:
        for f, idx in FACETS.items():
            for v in vals(s[idx]):
                if v.lower() not in BAD:
                    facet_index[(f, v)].append(s[0])

    stats = {
        "molecules": len(molecules), "odours": len(odours), "molecule_odour_edges": len(mol_od),
        "mvl_entries": len(mvl), "molecules_matched_to_mvl": len(mol_mvl),
        "aroma_similarity_edges": len(sim_edges),
        "sources": len(sources), "topics": len(topics), "source_topic_edges": len(src_top),
        "tags": len(tags), "source_tag_edges": len(src_tag),
        "bridge_curated": len(curated_set), "bridge_mined": len(mined_set),
        "sources_with_any_molecule": len({s for s, _ in mined_set | curated_set}),
        "claims": len(claims),
    }

    if stats_only:
        print(json.dumps(stats, indent=2))
        return stats

    # ---------------- ASSEMBLE EXPORT ----------------
    od_name = {o[0]: o[1] for o in odours}
    od_cat = {o[0]: o[2] for o in odours}
    mvl_by_no = {r[0]: r for r in mvl}
    mvl_of_mol = {m: e for m, e in mol_mvl}
    top_name = {t[0]: t[1] for t in topics}
    tag_name = {t[0]: (t[1], t[2]) for t in tags}

    deg_mol = Counter()
    for s, m in mined_set | curated_set:
        deg_mol[m] += 1

    mol_nodes = []
    for mid, name, cat in molecules:   # taste/use_notes dropped 2026-08-27 (migration 0014)
        e = mvl_by_no.get(mvl_of_mol.get(mid))
        mol_nodes.append({
            "id": f"m{mid}", "raw_id": mid, "label": name, "type": "molecule",
            "category": cat,
            "odours": sorted({od_name[o] for o in od_of[mid]})[:12],
            "n_odours": len(od_of[mid]),
            "papers": deg_mol.get(mid, 0),
            "cas": (e[2] if e else None),
            "chem_group": (e[3] if e else None),
            "subgroup": (e[4] if e else None),
            "process": (e[5] if e else None),
            "threshold": (e[7] if e else None),
            "beef_relevance": (e[8] if e else None),
            "in_mvl": bool(e),
        })
    od_nodes = [{"id": f"o{oid}", "raw_id": oid, "label": nm, "type": "odour",
                 "category": od_cat[oid],
                 "n_molecules": sum(1 for _m, _o in mol_od if _o == oid)} for oid, nm, _c in odours]

    def one(x):
        v = vals(x)
        return v[0] if v else None

    src_nodes = []
    for s in sources:
        claim_txt = " ".join(vals(s[13]))
        src_nodes.append({
            "id": f"s{s[0]}", "raw_id": s[0], "label": str(s[1] or "")[:140], "type": "paper",
            "year": s[2], "journal": str(s[3] or "") or None, "citations": s[4],
            "relevance": s[5], "priority": float(s[6]) if s[6] is not None else None,
            "study_type": one(s[7]), "pathway": vals(s[8])[:4], "method": vals(s[9])[:4],
            "matrix": vals(s[10])[:4], "compound_class": vals(s[11])[:4], "sensory": vals(s[12])[:6],
            "main_claim": claim_txt[:400], "is_review": s[15],
        })

    edges = []
    for mid, oid in mol_od:
        edges.append({"s": f"m{mid}", "t": f"o{oid}", "kind": "smells_of", "graph": "molecule"})
    for a, b, j, inter in sim_edges:
        edges.append({"s": f"m{a}", "t": f"m{b}", "kind": "aroma_similar",
                      "graph": "molecule", "w": j, "shared": inter})
    for sid, tid in src_top:
        edges.append({"s": f"s{sid}", "t": f"t{tid}", "kind": "about_topic", "graph": "paper"})
    for sid, mid in curated_set:
        edges.append({"s": f"s{sid}", "t": f"m{mid}", "kind": "mentions", "graph": "bridge",
                      "provenance": "curated"})
    for sid, mid in mined_set - curated_set:
        edges.append({"s": f"s{sid}", "t": f"m{mid}", "kind": "mentions", "graph": "bridge",
                      "provenance": "mined"})

    topic_nodes = [{"id": f"t{tid}", "raw_id": tid, "label": nm, "type": "topic",
                    "branch": br, "level": lv} for tid, nm, br, lv in topics]

    # ---------------- DEEP CHEMISTRY SCAFFOLD ----------------
    # Chemical class (all 799 molecules), functional group + subgroup (MVL-matched), and
    # formation pathway (Maillard / lipid oxidation). These turn a flat molecule list into a
    # navigable chemistry: "show me sulfur compounds formed by Maillard that smell roasted".
    chem_nodes, seen_chem = [], set()

    def chem_node(kind, label):
        if not label:
            return None
        nid = f"c{kind}:{norm(label)}"
        if nid not in seen_chem:
            seen_chem.add(nid)
            chem_nodes.append({"id": nid, "label": str(label), "type": "chem", "kind": kind})
        return nid

    for m in mol_nodes:
        cid = chem_node("class", m["category"])
        if cid:
            edges.append({"s": m["id"], "t": cid, "kind": "in_class", "graph": "molecule"})
        gid = chem_node("group", m.get("chem_group"))
        if gid:
            edges.append({"s": m["id"], "t": gid, "kind": "functional_group", "graph": "molecule"})
        sgid = chem_node("subgroup", m.get("subgroup"))
        if sgid:
            edges.append({"s": m["id"], "t": sgid, "kind": "subgroup", "graph": "molecule"})
        pid = chem_node("pathway", m.get("process"))
        if pid:
            edges.append({"s": m["id"], "t": pid, "kind": "formed_by", "graph": "molecule"})

    # Odour-category rollup, so aroma families are first-class and browsable.
    for o in od_nodes:
        cid = chem_node("odour_family", o["category"])
        if cid:
            edges.append({"s": o["id"], "t": cid, "kind": "odour_family", "graph": "molecule"})

    stats["chem_scaffold_nodes"] = len(chem_nodes)
    stats["total_edges"] = len(edges)
    stats["names_skipped_as_unminable"] = len(skipped)

    out = {
        "generated_utc": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "stats": stats,
        "nodes": {"molecules": mol_nodes, "odours": od_nodes, "papers": src_nodes,
                  "topics": topic_nodes, "chem": chem_nodes},
        "edges": edges,
        "facets": {f"{f}|{v}": ids for (f, v), ids in facet_index.items() if len(ids) >= 2},
    }
    # Neon returns NUMERIC as Decimal and dates as date objects; neither is JSON-native.
    def jsonable(o):
        import decimal, datetime as _dt
        if isinstance(o, decimal.Decimal):
            return float(o)
        if isinstance(o, (_dt.date, _dt.datetime)):
            return o.isoformat()
        return str(o)

    path = os.path.join(HERE, "kg_data.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, default=jsonable)
    print(f"wrote {path}  ({os.path.getsize(path)/1e6:.1f} MB)")
    print(json.dumps(stats, indent=2))
    return stats


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--stats-only", action="store_true")
    build(p.parse_args().stats_only)
