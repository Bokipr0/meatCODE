#!/usr/bin/env python3
"""
Journal / publisher-access report for the MeatCODE literature corpus.

Read-only. Answers: "how many of my sources sit behind each publisher platform,
and which of those need a paid subscription (ScienceDirect, Wiley, Springer...)?"

Publisher names per DOI prefix were resolved against the CrossRef REST API
(https://api.crossref.org/prefixes/<prefix>) and are hard-coded below so the
report is reproducible offline.

Outputs:
  data/reports/meatcode_journal_access_<UTCstamp>.xlsx
  data/reports/meatcode_journal_access_<UTCstamp>.pdf
"""
from __future__ import annotations

import os
import re
import csv
import sys
import collections
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------- publishers
# prefix -> (CrossRef registrant name, platform you actually read it on, access class)
# access class: OA = free, SUB = paid subscription, MIX = hybrid/varies, PRE = preprint (free)
PREFIX_MAP: dict[str, tuple[str, str, str]] = {
    "10.1016": ("Elsevier BV",                                   "ScienceDirect",          "SUB"),
    "10.3390": ("MDPI AG",                                       "MDPI",                   "OA"),
    "10.1002": ("Wiley",                                         "Wiley Online Library",   "SUB"),
    "10.1111": ("Wiley",                                         "Wiley Online Library",   "SUB"),
    "10.1007": ("Springer Science and Business Media LLC",       "SpringerLink",           "SUB"),
    "10.3389": ("Frontiers Media SA",                            "Frontiers",              "OA"),
    "10.1021": ("American Chemical Society (ACS)",               "ACS Publications",       "SUB"),
    "10.1038": ("Springer Science and Business Media LLC",       "Nature Portfolio",       "MIX"),
    "10.1186": ("Springer Science and Business Media LLC",       "BioMed Central",         "OA"),
    "10.1080": ("Informa UK Limited",                            "Taylor & Francis",       "SUB"),
    "10.1093": ("Oxford University Press (OUP)",                 "Oxford Academic",        "MIX"),
    "10.1371": ("Public Library of Science (PLoS)",              "PLOS",                   "OA"),
    "10.1155": ("Hindawi Limited",                               "Hindawi / Wiley",        "OA"),
    "10.3168": ("American Dairy Science Association",            "ScienceDirect",          "MIX"),
    "10.5851": ("Korean Soc. for Food Science of Animal Res.",   "Food Sci. Anim. Resour.", "OA"),
    "10.1039": ("Royal Society of Chemistry (RSC)",              "RSC Publishing",         "SUB"),
    "10.1177": ("SAGE Publications",                             "SAGE Journals",          "SUB"),
    "10.14202": ("Veterinary World",                             "Veterinary World",       "OA"),
    "10.1097": ("Ovid Technologies (Wolters Kluwer Health)",     "Ovid / LWW",             "SUB"),
    "10.64898": ("openRxiv",                                     "bioRxiv / medRxiv",      "PRE"),
    "10.5713": ("Asian Australasian Assoc. of Animal Prod. Soc.", "AJAS",                  "OA"),
    "10.21203": ("Research Square Platform LLC",                 "Research Square",        "PRE"),
    "10.3892": ("Spandidos Publications",                        "Spandidos",              "MIX"),
    "10.1208": ("Springer Science and Business Media LLC",       "SpringerLink",           "SUB"),
    "10.17113": ("Univ. of Zagreb, Food Tech. & Biotech.",       "Food Technol. Biotechnol.", "OA"),
    "10.4014": ("Korean Soc. for Microbiology and Biotechnology", "J. Microbiol. Biotechnol.", "OA"),
    "10.1159": ("S. Karger AG",                                  "Karger",                 "SUB"),
    "10.14639": ("Pacini Editore",                               "Pacini",                 "MIX"),
    "10.1063": ("AIP Publishing",                                "AIP",                    "SUB"),
    "10.1523": ("Society for Neuroscience",                      "J. Neuroscience",        "MIX"),
    "10.1103": ("American Physical Society (APS)",               "APS",                    "SUB"),
    "10.1163": ("Brill",                                         "Brill",                  "SUB"),
    "10.1098": ("The Royal Society",                             "Royal Society",          "MIX"),
    "10.20944": ("MDPI AG",                                      "MDPI Preprints",         "PRE"),
    "10.1128": ("American Society for Microbiology",             "ASM Journals",           "MIX"),
    "10.4103": ("Medknow",                                       "Medknow",                "OA"),
    "10.7762": ("Korean Society of Clinical Nutrition",          "Clin. Nutr. Res.",       "OA"),
    "10.5511": ("Japanese Soc. for Plant Cell and Mol. Biology", "Plant Biotechnology",    "OA"),
    "10.4081": ("PAGEPress Publications",                        "PAGEPress",              "OA"),
}

ACCESS_LABEL = {
    "SUB": "Paid subscription",
    "OA":  "Open access (free)",
    "MIX": "Hybrid / varies",
    "PRE": "Preprint (free)",
    "UNK": "Unknown (no DOI)",
}
ACCESS_ORDER = {"SUB": 0, "MIX": 1, "UNK": 2, "PRE": 3, "OA": 4}

# --------------------------------------------------------- journal overrides
# Publisher-level defaults are wrong for gold-OA titles hosted on paywalled
# platforms (e.g. "Food Chemistry: X" is free but sits on ScienceDirect).
# Every entry below was checked individually against the OpenAlex /sources API
# (is_oa, is_in_doaj) and/or DOAJ on 2026-08-05. Key = norm_key(journal).
JOURNAL_OVERRIDE: dict[str, tuple[str, str, str]] = {
    # key                                        access, ISSN-L,     basis
    "food chemistry x":                          ("OA",  "2590-1575", "verified: OpenAlex is_oa + DOAJ"),
    "current research in food science":          ("OA",  "2665-9271", "verified: DOAJ (gold OA since 2019)"),
    "poultry science":                           ("OA",  "0032-5791", "verified: DOAJ (gold OA since 2020)"),
    "journal of dairy science":                  ("OA",  "0022-0302", "verified: OpenAlex is_oa + DOAJ"),
    "npj science of food":                       ("OA",  "2396-8370", "verified: OpenAlex is_oa + DOAJ"),
    "food science of animal resources":          ("OA",  "2636-0772", "verified: OpenAlex is_oa + DOAJ"),
    "food chemistry molecular sciences":         ("OA",  "2666-5662", "verified: OpenAlex is_oa + DOAJ"),
    "scientific reports":                        ("OA",  "2045-2322", "verified: OpenAlex is_oa + DOAJ"),
    "ultrasonics sonochemistry":                 ("OA",  "1350-4177", "verified: OpenAlex is_oa + DOAJ"),
    "food chemistry":                            ("SUB", "0308-8146", "verified: OpenAlex is_oa = false"),
    "food research international":               ("SUB", "0963-9969", "verified: OpenAlex is_oa = false"),
    "meat science":                              ("SUB", "0309-1740", "verified: OpenAlex is_oa = false"),
    "international journal of biological macromolecules":
                                                 ("SUB", "0141-8130", "verified: OpenAlex is_oa = false"),
    "journal of food science":                   ("SUB", "0022-1147", "verified: OpenAlex is_oa = false"),
    "journal of agricultural and food chemistry": ("SUB", "0021-8561", "verified: OpenAlex is_oa = false"),
    "comprehensive reviews in food science and food safety":
                                                 ("SUB", "1541-4337", "verified: OpenAlex is_oa = false"),
    "journal of the science of food and agriculture":
                                                 ("SUB", "0022-5142", "verified: OpenAlex is_oa = false"),
    "critical reviews in food science and nutrition":
                                                 ("SUB", "1040-8398", "verified: OpenAlex is_oa = false"),
    "food science and biotechnology":            ("SUB", "1226-7708", "verified: OpenAlex is_oa = false"),
    # Wiley lists this as an OA title but OpenAlex reports is_oa = false.
    # Sources disagree, so it is left as hybrid rather than asserting either.
    "food science and nutrition":                ("MIX", "2048-7177", "CONFLICT: Wiley says OA, OpenAlex says not"),
}


# ------------------------------------------------------------- normalisation
_PARENS = re.compile(r"\s*\([^)]*\)")
_MDPI_TAIL = re.compile(r"\s*:?\s*an open access journal from mdpi\s*$", re.I)
_PUNCT = re.compile(r"[^a-z0-9 ]+")


def norm_key(name: str) -> str:
    """Collapse the many spellings of one journal onto a single key."""
    s = (name or "").strip()
    s = _MDPI_TAIL.sub("", s)
    s = _PARENS.sub("", s)            # "Foods (Basel, Switzerland)" -> "Foods"
    s = s.lower()
    s = s.replace("&", " and ")       # before punctuation stripping, or "&" is lost
    s = _PUNCT.sub(" ", s)            # "Food chemistry: X" -> "food chemistry x"
    s = re.sub(r"\s+", " ", s).strip()
    return s


def canonical_display(variants: collections.Counter) -> str:
    """Pick the nicest surviving spelling: most frequent, tie-break on Title Case."""
    best = sorted(
        variants.items(),
        key=lambda kv: (-kv[1], -sum(1 for c in kv[0] if c.isupper()), len(kv[0])),
    )
    name = best[0][0]
    return _MDPI_TAIL.sub("", _PARENS.sub("", name)).strip().rstrip(",;:")


# ------------------------------------------------------------------- loading
def load_rows() -> list[dict]:
    """Pull straight from Neon; fall back to a cached CSV if one was exported."""
    cached = Path("/tmp/sources_journals.csv")
    dburl = os.environ.get("DATABASE_URL")
    if not dburl:
        envf = REPO / ".env"
        if envf.exists():
            for line in envf.read_text().splitlines():
                if line.strip().startswith("DATABASE_URL"):
                    dburl = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if dburl:
        import psycopg2
        conn = psycopg2.connect(dburl)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, COALESCE(NULLIF(journal,''), NULLIF(venue,'')), doi, url, year, is_review "
            "FROM sources ORDER BY id"
        )
        rows = [
            dict(id=r[0], journal=r[1], doi=r[2], url=r[3], year=r[4], is_review=r[5])
            for r in cur.fetchall()
        ]
        conn.close()
        return rows
    if cached.exists():
        return list(csv.DictReader(cached.open()))
    raise SystemExit("no DATABASE_URL and no cached CSV")


def build():
    rows = load_rows()
    total = len(rows)

    groups: dict[str, dict] = {}
    for r in rows:
        raw = (r.get("journal") or "").strip()
        key = norm_key(raw) or "(no journal recorded)"
        g = groups.setdefault(key, {"variants": collections.Counter(),
                                    "prefixes": collections.Counter(),
                                    "n": 0, "no_doi": 0, "years": [], "reviews": 0})
        g["n"] += 1
        if raw:
            g["variants"][raw] += 1
        doi = (r.get("doi") or "").strip()
        if doi:
            g["prefixes"][doi.split("/")[0]] += 1
        else:
            g["no_doi"] += 1
        y = r.get("year")
        if y:
            try:
                g["years"].append(int(y))
            except (TypeError, ValueError):
                pass
        rev = r.get("is_review")
        if rev in (True, "True", "true", "t", 1, "1"):
            g["reviews"] += 1

    journals = []
    for key, g in groups.items():
        display = canonical_display(g["variants"]) if g["variants"] else "(no journal recorded)"
        if g["prefixes"]:
            prefix = g["prefixes"].most_common(1)[0][0]
            publisher, platform, access = PREFIX_MAP.get(
                prefix, (f"Other (DOI {prefix})", f"Other (DOI {prefix})", "MIX"))
        else:
            prefix, publisher, platform, access = "", "Unknown (no DOI)", "Unknown (no DOI)", "UNK"

        # journal-level verified override beats the publisher default
        ov = JOURNAL_OVERRIDE.get(key)
        if ov:
            access, issn, basis = ov
        else:
            issn, basis = "", "publisher default (not individually verified)"

        journals.append({
            "journal": display,
            "n": g["n"],
            "pct": g["n"] / total * 100,
            "publisher": publisher,
            "platform": platform,
            "access": access,
            "access_label": ACCESS_LABEL[access],
            "issn": issn,
            "basis": basis,
            "prefix": prefix,
            "no_doi": g["no_doi"],
            "reviews": g["reviews"],
            "yr_min": min(g["years"]) if g["years"] else None,
            "yr_max": max(g["years"]) if g["years"] else None,
            "variants": len(g["variants"]),
            "variant_list": "; ".join(sorted(g["variants"])) if len(g["variants"]) > 1 else "",
        })
    journals.sort(key=lambda d: (-d["n"], d["journal"].lower()))

    # platform rollup -- a platform can host both paid and free titles
    # (ScienceDirect carries Food Chemistry (paid) and Food Chemistry: X (free)),
    # so each platform is reported with its paid/free split rather than one label.
    plats: dict[str, dict] = {}
    for j in journals:
        p = plats.setdefault(j["platform"], {"n": 0, "journals": 0, "publisher": j["publisher"],
                                             "paid": 0, "free": 0, "other": 0})
        p["n"] += j["n"]
        p["journals"] += 1
        if j["access"] == "SUB":
            p["paid"] += j["n"]
        elif j["access"] in ("OA", "PRE"):
            p["free"] += j["n"]
        else:
            p["other"] += j["n"]
    platforms = [dict(platform=k, **v) for k, v in plats.items()]
    for p in platforms:
        p["pct"] = p["n"] / total * 100
        p["access_label"] = ("Paid subscription" if p["paid"] and not p["free"]
                             else "Open access (free)" if p["free"] and not p["paid"]
                             else "Mixed paid + free" if p["paid"] and p["free"]
                             else "Hybrid / unknown")
    platforms.sort(key=lambda d: (-d["paid"], -d["n"]))

    # access rollup
    acc: dict[str, int] = collections.Counter()
    for j in journals:
        acc[j["access"]] += j["n"]
    access_rows = [
        {"access": k, "access_label": ACCESS_LABEL[k], "n": v, "pct": v / total * 100}
        for k, v in sorted(acc.items(), key=lambda kv: ACCESS_ORDER[kv[0]])
    ]

    return dict(rows=rows, total=total, journals=journals,
                platforms=platforms, access_rows=access_rows)


if __name__ == "__main__":
    d = build()
    print(f"total sources: {d['total']}   distinct journals (normalised): {len(d['journals'])}")
    print()
    for a in d["access_rows"]:
        print(f"  {a['access_label']:22s} {a['n']:4d}  {a['pct']:5.1f}%")
    print()
    for p in d["platforms"][:14]:
        print(f"  {p['platform']:26s} tot {p['n']:4d}  paid {p['paid']:4d}  free {p['free']:4d}  {p['access_label']}")
    print()
    for j in d["journals"][:20]:
        print(f"  {j['n']:4d}  {j['journal'][:46]:46s} {j['platform'][:22]:22s} {j['access_label']}")
