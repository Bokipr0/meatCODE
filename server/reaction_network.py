# Last updated: 2026-08-31 15:09 UTC · Full-Stack · GET /api/reaction-network builder
#   Curated, honestly-labelled reaction-network skeleton for the Research journey
#   (precursors → heat/reaction network → volatiles → analytical/sensory profile),
#   ENRICHED with real data from Neon where it exists. TWO separate branches:
#     • aqueous → Maillard + Strecker (precursors: reducing sugars, free amino acids, peptides)
#     • lipid   → lipid oxidation + β-oxidation (precursors: fatty acids, triglycerides, phospholipids)
#   Precursors + reactions + precursor→reaction edges are a HARDCODED skeleton, vocab-aligned
#   to the taxonomy pathways (db/taxonomy/keywords_topics.json); every one is flagged
#   backed=false because it is structural-only (there are no stored reaction edges in Neon).
#   Volatiles are pulled LIVE from the `meaty_volatile_library` table (273 curated meat
#   volatiles, each with likely_process / chemical_group / beef_relevance_score / a
#   cooked-meats citation list); those are flagged backed=true. If the DB is unreachable the
#   builder degrades to a small curated volatile list (backed=false) and representative
#   analytical/sensory numbers — it never raises, so the Research page can never 500.
#
# This module owns ZERO SQL execution: the caller passes a `query(sql, params) -> list[dict]`
# accessor (meatcode_server.pg_rows) so all connection handling / SELECT-only discipline
# stays in one place. Pass query=None (or let it raise) to force the degraded path.

import re

# ─── Volatile source: the Meaty Volatile Library (real, per-branch) ──────────────────
# mentions_count = number of cooked-meat matrices that reported the compound, derived from
# the `cooked_meats_reported` citation string (e.g. "beef[71], chicken[15,42], pork[10]"
# → 3) by counting the ']' citation-closers. Honest proxy for "how often seen in real
# cooked meat", ranked highest-first. `class` = the library's chemical_group.
_VOLATILE_SQL = """
    SELECT compound AS name,
           chemical_group AS class,
           (length(coalesce(cooked_meats_reported,'')) -
            length(replace(coalesce(cooked_meats_reported,''),']',''))) AS mentions_count,
           beef_relevance_score::float AS score,
           odor_descriptor
    FROM meaty_volatile_library
    WHERE likely_process = ANY(%s)
      AND compound IS NOT NULL AND btrim(compound) <> ''
    ORDER BY mentions_count DESC, beef_relevance_score DESC NULLS LAST, compound
    LIMIT %s
"""
_VOLATILE_LIMIT = 12

# analytical: detected = catalogued MVL volatiles for the branch; aligned = those that also
# exist as a row in the molecule corpus (name match) — i.e. carried through to the molecular
# DB; test_only = catalogued in the library only (not yet mirrored into `molecules`).
_ANALYTICAL_SQL = """
    SELECT COUNT(*) AS detected,
           COUNT(*) FILTER (
               WHERE EXISTS (SELECT 1 FROM molecules m
                             WHERE lower(m.name) = lower(v.compound))
           ) AS aligned
    FROM meaty_volatile_library v
    WHERE v.likely_process = ANY(%s)
      AND v.compound IS NOT NULL AND btrim(v.compound) <> ''
"""

# All descriptors of the branch's volatiles → the sensory radar is COMPUTED from real odour
# words (frequency of each axis' keyword set), then normalised. Representative, not a panel.
_DESCRIPTORS_SQL = """
    SELECT odor_descriptor FROM meaty_volatile_library
    WHERE likely_process = ANY(%s)
      AND compound IS NOT NULL AND odor_descriptor IS NOT NULL
"""

# Eight fixed sensory axes + the odour keywords that vote for each.
_SENSORY_AXES = [
    ("Roasted",   ("roast", "toast", "popcorn", "coffee", "grilled", "burnt")),
    ("Meaty",     ("meat", "broth", "bouillon", "savor", "savour", "umami", "brothy")),
    ("Fatty",     ("fat", "oily", "tallow", "lard", "waxy", "creamy")),
    ("Green",     ("green", "grass", "fresh", "herbal", "cucumber", "leaf")),
    ("Sulfurous", ("sulf", "sulph", "onion", "garlic", "potato", "egg", "cabbage")),
    ("Nutty",     ("nut", "almond", "hazelnut", "peanut")),
    ("Caramel",   ("caramel", "sweet", "honey", "malt", "butter", "chocolate", "vanilla")),
    ("Rancid",    ("rancid", "sour", "chees", "sweaty", "putrid", "pungent", "paint")),
]

# ─── Curated per-branch skeleton (the honest structural backbone) ────────────────────
_BRANCHES = {
    "aqueous": {
        "mvl_processes": ["Maillard", "Both"],
        "note": ("Curated aqueous-phase skeleton (Maillard + Strecker). Precursors, reactions "
                 "and their edges are structural (no stored reaction edges in Neon); volatiles "
                 "and mention counts are live from the Meaty Volatile Library."),
        "precursors": [
            {"id": "p:reducing_sugars",  "name": "Reducing sugars"},
            {"id": "p:free_amino_acids", "name": "Free amino acids"},
            {"id": "p:peptides",         "name": "Peptides"},
        ],
        "reactions": [
            {"id": "r:maillard", "name": "Maillard reaction",   "pathway": "maillard"},
            {"id": "r:strecker", "name": "Strecker degradation", "pathway": "strecker"},
        ],
        "precursor_edges": [
            ("p:reducing_sugars",  "r:maillard"),
            ("p:free_amino_acids", "r:maillard"),
            ("p:peptides",         "r:maillard"),
            ("p:free_amino_acids", "r:strecker"),
        ],
        # chemical_group → reaction that best explains that class of volatile
        "group_to_reaction": {
            "aldehydes": "r:strecker",
        },
        "default_reaction": "r:maillard",
        "fallback_volatiles": [
            {"name": "2,5-dimethylpyrazine", "class": "Nitrogen-containing compounds"},
            {"name": "methional",            "class": "Sulfur containing compounds"},
            {"name": "2-methylbutanal",      "class": "aldehydes"},
            {"name": "2,3-butanedione",      "class": "oxygen containing compounds"},
            {"name": "2-acetylthiazole",     "class": "Sulfur containing compounds"},
        ],
        "fallback_analytical": {"detected": 116, "aligned": 47, "test_only": 69},
        "fallback_sensory": [
            {"axis": "Roasted", "value": 0.55}, {"axis": "Meaty", "value": 0.45},
            {"axis": "Fatty", "value": 0.15}, {"axis": "Green", "value": 0.20},
            {"axis": "Sulfurous", "value": 0.60}, {"axis": "Nutty", "value": 0.40},
            {"axis": "Caramel", "value": 0.50}, {"axis": "Rancid", "value": 0.15},
        ],
    },
    "lipid": {
        "mvl_processes": ["Lipid oxidation", "Both"],
        "note": ("Curated lipid-phase skeleton (lipid oxidation + β-oxidation). Precursors, "
                 "reactions and their edges are structural (no stored reaction edges in Neon); "
                 "volatiles and mention counts are live from the Meaty Volatile Library."),
        "precursors": [
            {"id": "p:fatty_acids",   "name": "Unsaturated fatty acids"},
            {"id": "p:triglycerides", "name": "Triglycerides"},
            {"id": "p:phospholipids", "name": "Phospholipids"},
        ],
        "reactions": [
            {"id": "r:lipid_oxidation", "name": "Lipid oxidation", "pathway": "lipid_oxidation"},
            {"id": "r:beta_oxidation",  "name": "β-oxidation",     "pathway": "lipid_oxidation"},
        ],
        "precursor_edges": [
            ("p:triglycerides", "r:lipid_oxidation"),
            ("p:phospholipids", "r:lipid_oxidation"),
            ("p:fatty_acids",   "r:lipid_oxidation"),
            ("p:fatty_acids",   "r:beta_oxidation"),
            ("p:triglycerides", "r:beta_oxidation"),
        ],
        "group_to_reaction": {
            "ketones": "r:beta_oxidation",
            "lactones": "r:beta_oxidation",
        },
        "default_reaction": "r:lipid_oxidation",
        "fallback_volatiles": [
            {"name": "hexanal",             "class": "aldehydes"},
            {"name": "1-octen-3-ol",        "class": "alcohols"},
            {"name": "(E,E)-2,4-decadienal", "class": "aldehydes"},
            {"name": "nonanal",             "class": "aldehydes"},
            {"name": "2-heptanone",         "class": "ketones"},
            {"name": "γ-nonalactone",       "class": "lactones"},
        ],
        "fallback_analytical": {"detected": 175, "aligned": 62, "test_only": 113},
        "fallback_sensory": [
            {"axis": "Roasted", "value": 0.15}, {"axis": "Meaty", "value": 0.25},
            {"axis": "Fatty", "value": 0.70}, {"axis": "Green", "value": 0.55},
            {"axis": "Sulfurous", "value": 0.15}, {"axis": "Nutty", "value": 0.30},
            {"axis": "Caramel", "value": 0.20}, {"axis": "Rancid", "value": 0.45},
        ],
    },
}

DEFAULT_BRANCH = "aqueous"


def _slug(name):
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return s or "x"


def _sensory_from_descriptors(descriptors):
    """Compute the 8-axis radar from real odour descriptors (keyword frequency, normalised
    to the busiest axis so the shape is readable). Returns representative 0..1 values."""
    text = " ".join((d or "").lower() for d in descriptors)
    raw = []
    for axis, keys in _SENSORY_AXES:
        raw.append((axis, sum(text.count(k) for k in keys)))
    peak = max((c for _a, c in raw), default=0) or 1
    return [{"axis": a, "value": round(min(1.0, c / peak), 2)} for a, c in raw]


def build(branch, query=None):
    """Assemble the /api/reaction-network payload for one branch.

    `query` is a callable(sql, params)->list[dict] (meatcode_server.pg_rows) or None.
    Never raises: any DB problem (query is None, connection down, table missing) degrades
    to the curated skeleton with backed=false volatiles + representative profile numbers.
    status is always "preview" — this is an explicitly curated/preview surface."""
    branch = (branch or "").strip().lower()
    if branch not in _BRANCHES:
        branch = DEFAULT_BRANCH
    cfg = _BRANCHES[branch]

    precursors = [{"id": p["id"], "name": p["name"], "backed": False} for p in cfg["precursors"]]
    reactions = [{"id": r["id"], "name": r["name"], "pathway": r["pathway"], "backed": False}
                 for r in cfg["reactions"]]
    reaction_ids = {r["id"] for r in reactions}
    edges = [{"from": a, "to": b} for a, b in cfg["precursor_edges"]]

    volatiles = []
    analytical = None
    sensory = None
    db_ok = False
    rows = ana_rows = desc_rows = None
    if query is not None:
        try:
            rows = query(_VOLATILE_SQL, (cfg["mvl_processes"], _VOLATILE_LIMIT))
            ana_rows = query(_ANALYTICAL_SQL, (cfg["mvl_processes"],))
            desc_rows = query(_DESCRIPTORS_SQL, (cfg["mvl_processes"],))
            db_ok = True
        except Exception:
            db_ok = False

    if db_ok and rows:
        backed_reactions = set()
        for r in rows:
            vid = "v:" + _slug(r.get("name"))
            volatiles.append({
                "id": vid,
                "name": r.get("name"),
                "class": r.get("class") or "",
                "mentions_count": int(r.get("mentions_count") or 0),
                "backed": True,
            })
            rxn = cfg["group_to_reaction"].get((r.get("class") or "").strip(), cfg["default_reaction"])
            if rxn not in reaction_ids:
                rxn = cfg["default_reaction"]
            edges.append({"from": rxn, "to": vid})
            backed_reactions.add(rxn)
        # A reaction that genuinely produced real, cited volatiles is now corpus-backed.
        for rr in reactions:
            if rr["id"] in backed_reactions:
                rr["backed"] = True

        detected = int((ana_rows[0].get("detected") if ana_rows else 0) or 0)
        aligned = int((ana_rows[0].get("aligned") if ana_rows else 0) or 0)
        analytical = {
            "detected": detected,
            "aligned": aligned,
            "test_only": max(0, detected - aligned),
            "note": ("From the Meaty Volatile Library: detected = catalogued volatiles for this "
                     "branch; aligned = also present in the molecule corpus; test_only = library-only."),
        }
        sensory = _sensory_from_descriptors([d.get("odor_descriptor") for d in (desc_rows or [])])
        note = cfg["note"]
    else:
        for fv in cfg["fallback_volatiles"]:
            volatiles.append({
                "id": "v:" + _slug(fv["name"]),
                "name": fv["name"],
                "class": fv["class"],
                "mentions_count": 0,
                "backed": False,
            })
            edges.append({"from": cfg["default_reaction"], "to": "v:" + _slug(fv["name"])})
        fa = cfg["fallback_analytical"]
        analytical = {
            "detected": fa["detected"], "aligned": fa["aligned"], "test_only": fa["test_only"],
            "note": "Representative counts — database unavailable, volatiles shown are curated placeholders.",
        }
        sensory = [dict(s) for s in cfg["fallback_sensory"]]
        note = cfg["note"] + " Database unavailable — volatiles are curated placeholders (backed=false)."

    return {
        "branch": branch,
        "status": "preview",
        "note": note,
        "precursors": precursors,
        "reactions": reactions,
        "volatiles": volatiles,
        "edges": edges,
        "analytical": analytical,
        "sensory": sensory,
    }
