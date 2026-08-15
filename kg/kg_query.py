#!/usr/bin/env python3
"""
MeatCODE KG — graph-augmented retrieval demo
Last updated: 2026-08-15 · Advisory

THE POINT OF THIS FILE
----------------------
Today the Oracle does flat retrieval: full-text rank over `sources`, take the top 6, hand the
raw text to Claude. The model then has to infer the chemistry itself from prose.

Graph retrieval starts from the *entities* in the question instead of its words:

    question → odour/aroma nodes → molecules that produce them
             → aroma-similar molecules + same chemical class / formation pathway
             → papers linked to any of those molecules
             → rank papers by how much of the relevant chemistry they actually cover

The output isn't a pile of text — it's a **structured answer skeleton**: these compounds,
in these families, formed by this pathway, evidenced by these papers. That is the difference
the Oracle needs: it can say "5 papers support this, they cluster on pyrazines from Maillard"
instead of paraphrasing six abstracts.

Run:  python3 kg/kg_query.py            # runs the demo questions, writes kg/demo_queries.json
"""

import json, os, re, sys
from collections import defaultdict, Counter

HERE = os.path.dirname(os.path.abspath(__file__))


def load():
    with open(os.path.join(HERE, "kg_data.json"), encoding="utf-8") as f:
        return json.load(f)


class KG:
    def __init__(self, d):
        self.d = d
        self.mol = {m["id"]: m for m in d["nodes"]["molecules"]}
        self.od = {o["id"]: o for o in d["nodes"]["odours"]}
        self.pap = {p["id"]: p for p in d["nodes"]["papers"]}
        self.chem = {c["id"]: c for c in d["nodes"]["chem"]}
        self.adj = defaultdict(list)
        for e in d["edges"]:
            self.adj[e["s"]].append((e["t"], e))
            self.adj[e["t"]].append((e["s"], e))

    def neighbours(self, nid, kind=None):
        return [(t, e) for t, e in self.adj[nid] if kind is None or e["kind"] == kind]

    # ---- step 1: find the aroma/odour entry points for a question ----
    def odours_for(self, q):
        ql = q.lower()
        hits = []
        for oid, o in self.od.items():
            n = o["label"].lower()
            if len(n) >= 4 and re.search(r"(?<![a-z])" + re.escape(n) + r"s?(?![a-z])", ql):
                hits.append(oid)
        return hits

    # ---- step 2: molecules producing those odours ----
    def molecules_for_odours(self, odour_ids):
        out = Counter()
        for oid in odour_ids:
            for t, e in self.neighbours(oid, "smells_of"):
                if t.startswith("m"):
                    out[t] += 1
        return out

    # ---- step 3: expand through chemistry (this is what flat search cannot do) ----
    def expand_chemistry(self, seed_mols, max_add=12):
        added = Counter()
        for mid in seed_mols:
            for t, e in self.neighbours(mid, "aroma_similar"):
                if t not in seed_mols:
                    added[t] += e.get("w", 0.4)
        return [m for m, _ in added.most_common(max_add)]

    # ---- step 4: papers evidencing those molecules ----
    def papers_for(self, mol_ids):
        hits = defaultdict(list)
        for mid in mol_ids:
            for t, e in self.neighbours(mid, "mentions"):
                if t.startswith("s"):
                    hits[t].append((mid, e.get("provenance", "curated")))
        return hits

    def profile(self, mol_ids):
        """What chemistry do these molecules have in common? This is the skeleton the
        chatbot gets for free — families and formation pathways, already aggregated."""
        cls, path, grp = Counter(), Counter(), Counter()
        for mid in mol_ids:
            m = self.mol[mid]
            cls[m["category"]] += 1
            if m.get("process"): path[m["process"]] += 1
            if m.get("chem_group"): grp[m["chem_group"]] += 1
        return {"classes": cls.most_common(5), "pathways": path.most_common(3),
                "groups": grp.most_common(4)}

    # ---- the whole pipeline ----
    def graph_retrieve(self, q, top_papers=6):
        od_ids = self.odours_for(q)
        seed = self.molecules_for_odours(od_ids)
        seed_ids = [m for m, _ in seed.most_common(15)]
        expanded = self.expand_chemistry(set(seed_ids))
        all_mols = seed_ids + expanded
        paper_hits = self.papers_for(all_mols)

        ranked = []
        for sid, hits in paper_hits.items():
            p = self.pap[sid]
            coverage = len({h[0] for h in hits})
            rel = (p.get("relevance") or 0) / 100.0
            score = coverage * (0.5 + rel)
            ranked.append((score, coverage, sid))
        ranked.sort(reverse=True)

        return {
            "question": q,
            "odours_matched": [self.od[o]["label"] for o in od_ids],
            "seed_molecules": [self.mol[m]["label"] for m in seed_ids],
            "expanded_molecules": [self.mol[m]["label"] for m in expanded],
            "chemistry_profile": self.profile(all_mols),
            "papers": [{
                "id": self.pap[s]["raw_id"], "title": self.pap[s]["label"],
                "year": self.pap[s]["year"], "relevance": self.pap[s]["relevance"],
                "molecules_covered": cov,
                "which": sorted({self.mol[h[0]]["label"] for h in paper_hits[s]})[:6],
                "claim": self.pap[s]["main_claim"][:180],
            } for sc, cov, s in ranked[:top_papers]],
            "n_candidate_papers": len(ranked),
        }

    # ---- the baseline it has to beat ----
    def flat_retrieve(self, q, top_papers=6):
        """Keyword overlap on title + claim — a stand-in for today's ts_rank behaviour."""
        terms = [t for t in re.split(r"\W+", q.lower()) if len(t) > 3]
        ranked = []
        for sid, p in self.pap.items():
            hay = (p["label"] + " " + p["main_claim"]).lower()
            hit = sum(hay.count(t) for t in terms)
            if hit:
                ranked.append((hit * (0.5 + (p.get("relevance") or 0) / 100.0), hit, sid))
        ranked.sort(reverse=True)
        return {"papers": [{"id": self.pap[s]["raw_id"], "title": self.pap[s]["label"],
                            "year": self.pap[s]["year"], "keyword_hits": h,
                            "claim": self.pap[s]["main_claim"][:180]}
                           for sc, h, s in ranked[:top_papers]],
                "n_candidate_papers": len(ranked)}


DEMO_QUESTIONS = [
    "What compounds give cooked beef its roasted and nutty aroma?",
    "Which molecules are responsible for sulfurous meaty notes?",
    "What causes green, beany off-notes in plant protein?",
]


def main():
    kg = KG(load())
    out = []
    for q in DEMO_QUESTIONS:
        g = kg.graph_retrieve(q)
        f = kg.flat_retrieve(q)
        out.append({"question": q, "graph": g, "flat": f})

        print("\n" + "=" * 78)
        print("Q:", q)
        print("-" * 78)
        print("GRAPH ROUTE")
        print("  odours matched   :", ", ".join(g["odours_matched"]) or "(none)")
        print("  seed molecules   :", ", ".join(g["seed_molecules"][:10]) or "(none)")
        print("  chem-expanded    :", ", ".join(g["expanded_molecules"][:8]) or "(none)")
        prof = g["chemistry_profile"]
        print("  classes          :", ", ".join(f"{k} x{v}" for k, v in prof["classes"]))
        print("  pathways         :", ", ".join(f"{k} x{v}" for k, v in prof["pathways"]) or "(unknown)")
        print(f"  candidate papers : {g['n_candidate_papers']}  → top {len(g['papers'])}")
        for p in g["papers"]:
            print(f"     [{p['id']}] cov={p['molecules_covered']} rel={p['relevance']} {p['title'][:70]}")
            print(f"          molecules: {', '.join(p['which'])}")
        print("FLAT ROUTE (keyword)")
        print(f"  candidate papers : {f['n_candidate_papers']}  → top {len(f['papers'])}")
        for p in f["papers"]:
            print(f"     [{p['id']}] hits={p['keyword_hits']} {p['title'][:70]}")

        gset = {p["id"] for p in g["papers"]}
        fset = {p["id"] for p in f["papers"]}
        print(f"  OVERLAP: {len(gset & fset)}/{len(gset)} papers in common — "
              f"graph found {len(gset - fset)} the keyword route missed")

    with open(os.path.join(HERE, "demo_queries.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("\nwrote kg/demo_queries.json")


if __name__ == "__main__":
    main()
