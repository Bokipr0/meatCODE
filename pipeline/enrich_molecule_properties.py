#!/usr/bin/env python3
"""
enrich_molecule_properties.py — populate the migration-0011 target-property columns.

Two independent passes, each writing BOTH the canonical column on `molecules` and a
provenanced row in `molecule_properties`:

  PASS A · system_derived  — RDKit over molecules.smiles (590 rows).
           molecular_weight, formal_charge, tpsa, logp, functional_groups, reactive_groups.
  PASS B · reported        — meaty_volatile_library, unambiguous normalized-name match.
           odor_threshold (raw + numeric), colour where stated.

Rules taken from docs/full_text_parallel_evidence_extraction_strategy.md:
  * the raw expression is always preserved;
  * a value is normalized ONLY when the source is unambiguous — ranges, matrix-qualified
    values and "greater than" limits keep value_num NULL and carry a flag;
  * no unit conversion is performed at extraction time;
  * computed values are marked system_derived and never presented as measurements.

Properties deliberately LEFT NULL (no non-fabricated source available):
  pka, isoelectric_point, redox_potential_v, sequence_conformation,
  boiling_point, vapor_pressure, oav.

Usage:  python3 pipeline/enrich_molecule_properties.py [--dry-run]
"""
from __future__ import annotations
import os, re, sys, argparse
import psycopg2
from psycopg2.extras import execute_batch, Json

from rdkit import Chem, RDLogger
from rdkit.Chem import Descriptors, Crippen, rdMolDescriptors
RDLogger.DisableLog("rdApp.*")

RDKIT_VER = Chem.rdBase.rdkitVersion
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --------------------------------------------------------------------------- #
# Functional groups — SMARTS. Deterministic substructure match, not a guess.
# --------------------------------------------------------------------------- #
FUNCTIONAL_GROUPS = {
    "aldehyde":            "[CX3H1](=O)[#6]",
    "ketone":              "[#6][CX3](=O)[#6]",
    "carboxylic_acid":     "[CX3](=O)[OX2H1]",
    "ester":               "[#6][CX3](=O)[OX2H0][#6]",
    "lactone":             "[C;R](=O)[O;R]",
    "amide":               "[NX3][CX3](=[OX1])",
    "primary_alcohol":     "[OX2H][CX4H2]",
    "alcohol":             "[OX2H][CX4]",
    "phenol":              "[OX2H][c]",
    "ether":               "[OD2]([#6])[#6]",
    "primary_amine":       "[NX3;H2;!$(NC=O)][#6]",
    "secondary_amine":     "[NX3;H1;!$(NC=O)]([#6])[#6]",
    "tertiary_amine":      "[NX3;H0;!$(NC=O)]([#6])([#6])[#6]",
    "thiol":               "[SX2H]",
    "thioether":           "[#16X2H0]([#6])[#6]",
    "disulfide":           "[SX2][SX2]",
    "nitrile":             "[NX1]#[CX2]",
    "alkene":              "[CX3]=[CX3]",
    "alkyne":              "[CX2]#[CX2]",
    "furan":               "c1ccoc1",
    "thiophene":           "c1ccsc1",
    "pyrazine":            "c1cnccn1",
    "pyridine":            "c1ccncc1",
    "pyrrole":             "c1cc[nH]c1",
    "thiazole":            "c1cscn1",
    "oxazole":             "c1cocn1",
    "benzene_ring":        "c1ccccc1",
}

# Reactive handles that matter for Maillard / lipid-oxidation chemistry.
REACTIVE_GROUPS = {
    "carbonyl_electrophile":      "[CX3](=[OX1])[#6,#1]",       # condenses with amines
    "free_amine_nucleophile":     "[NX3;H1,H2;!$(NC=O)][#6]",   # Maillard amine partner
    "thiol_nucleophile":          "[SX2H]",                     # meaty thiol chemistry
    "michael_acceptor":           "[CX3]=[CX3][CX3]=[OX1]",     # a,b-unsaturated carbonyl
    "allylic_ch":                 "[CX4;H1,H2][CX3]=[CX3]",     # lipid-oxidation initiation site
    "bis_allylic_ch":             "[CX3]=[CX3][CX4;H2][CX3]=[CX3]",
    "phenolic_antioxidant":       "[OX2H][c]",
    "disulfide_bridge":           "[SX2][SX2]",
    "reducing_sugar_like":        "[CX3H1](=O)[CX4][OX2H]",
}

_FG = {k: Chem.MolFromSmarts(v) for k, v in FUNCTIONAL_GROUPS.items()}
_RG = {k: Chem.MolFromSmarts(v) for k, v in REACTIVE_GROUPS.items()}
assert all(v is not None for v in _FG.values()), "bad functional-group SMARTS"
assert all(v is not None for v in _RG.values()), "bad reactive-group SMARTS"


def db():
    url = None
    for line in open(os.path.join(REPO, ".env")):
        if line.startswith("DATABASE_URL"):
            url = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not url:
        sys.exit("DATABASE_URL not found in .env")
    conn = psycopg2.connect(url)
    conn.autocommit = False
    return conn


UPSERT_PROP = """
INSERT INTO molecule_properties
  (molecule_id, property, value_raw, value_num, unit_raw, unit_norm, uncertainty,
   derivation, method, conditions, source_id, source_ref, source_location, confidence, flags)
VALUES (%(mid)s, %(prop)s, %(raw)s, %(num)s, %(unit_raw)s, %(unit_norm)s, %(unc)s,
        %(deriv)s, %(method)s, %(cond)s, %(sid)s, %(sref)s, %(sloc)s, %(conf)s, %(flags)s)
ON CONFLICT (molecule_id, property, COALESCE(source_ref, '')) DO UPDATE SET
   value_raw=EXCLUDED.value_raw, value_num=EXCLUDED.value_num,
   unit_raw=EXCLUDED.unit_raw, unit_norm=EXCLUDED.unit_norm,
   uncertainty=EXCLUDED.uncertainty, derivation=EXCLUDED.derivation,
   method=EXCLUDED.method, conditions=EXCLUDED.conditions,
   source_id=EXCLUDED.source_id, source_location=EXCLUDED.source_location,
   confidence=EXCLUDED.confidence, flags=EXCLUDED.flags;
"""


def prop(mid, name, *, raw=None, num=None, unit_raw=None, unit_norm=None, unc=None,
         deriv="system_derived", method=None, cond=None, sid=None, sref=None,
         sloc=None, conf=None, flags=None):
    return dict(mid=mid, prop=name, raw=raw, num=num, unit_raw=unit_raw,
                unit_norm=unit_norm, unc=unc, deriv=deriv, method=method,
                cond=Json(cond) if cond else None, sid=sid, sref=sref, sloc=sloc,
                conf=conf, flags=flags)


# --------------------------------------------------------------------------- #
# PASS A — structure-derived descriptors
# --------------------------------------------------------------------------- #
def pass_a(cur):
    cur.execute("SELECT id, name, smiles FROM molecules "
                "WHERE smiles IS NOT NULL AND NOT is_junk ORDER BY id")
    rows = cur.fetchall()
    updates, props, unparsed = [], [], []

    for mid, name, smi in rows:
        m = Chem.MolFromSmiles(smi)
        if m is None:
            unparsed.append((mid, name))
            continue
        mw     = round(Descriptors.MolWt(m), 4)
        charge = Chem.GetFormalCharge(m)
        tpsa   = round(rdMolDescriptors.CalcTPSA(m), 4)
        logp   = round(Crippen.MolLogP(m), 4)
        fgs = sorted(k for k, patt in _FG.items() if m.HasSubstructMatch(patt))
        rgs = sorted(k for k, patt in _RG.items() if m.HasSubstructMatch(patt))

        updates.append((mw, charge, tpsa, logp, fgs or None, rgs or None, mid))

        src = f"rdkit:{RDKIT_VER}"
        # Exact graph-theoretic quantities → confidence 1.0 given the structure.
        props += [
            prop(mid, "molecular_weight", raw=str(mw), num=mw, unit_raw="g/mol",
                 unit_norm="g/mol", method=f"RDKit Descriptors.MolWt ({RDKIT_VER})",
                 sref=src, conf=1.0),
            prop(mid, "formal_charge", raw=str(charge), num=charge,
                 method=f"RDKit GetFormalCharge ({RDKIT_VER})", sref=src, conf=1.0),
            prop(mid, "tpsa", raw=str(tpsa), num=tpsa, unit_raw="A^2", unit_norm="A^2",
                 method=f"RDKit CalcTPSA ({RDKIT_VER})", sref=src, conf=1.0,
                 flags=["polarity_proxy"]),
            # Crippen logP is an ESTIMATOR, not a measurement. Lower confidence + flag.
            prop(mid, "logp", raw=str(logp), num=logp, unit_raw="log10 octanol/water",
                 unit_norm="log10 octanol/water",
                 method=f"RDKit Crippen.MolLogP ({RDKIT_VER})", sref=src, conf=0.60,
                 flags=["estimated_not_measured"]),
            prop(mid, "functional_groups", raw=",".join(fgs) or None,
                 method=f"SMARTS substructure match ({len(_FG)} patterns)",
                 sref=src, conf=0.95),
            prop(mid, "reactive_groups", raw=",".join(rgs) or None,
                 method=f"SMARTS substructure match ({len(_RG)} patterns)",
                 sref=src, conf=0.95),
        ]

    execute_batch(cur, """
        UPDATE molecules SET molecular_weight=%s, formal_charge=%s, tpsa=%s,
               logp=%s, functional_groups=%s, reactive_groups=%s, updated_at=now()
         WHERE id=%s""", updates, page_size=200)
    execute_batch(cur, UPSERT_PROP, props, page_size=200)
    return len(updates), len(props), unparsed


# --------------------------------------------------------------------------- #
# PASS B — reported odour thresholds from the Meaty Volatile Library
# --------------------------------------------------------------------------- #
_NUM = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*$")

def parse_threshold(raw: str):
    """Return (value_num, conditions, flags). Normalize only unambiguous values."""
    txt = (raw or "").strip()
    flags, cond, num = [], {}, None
    if not txt:
        return None, None, ["empty"]

    head, _, tail = txt.partition(",")
    if tail.strip():
        cond["matrix"] = tail.strip()
        flags.append("matrix_qualified")
    head = head.strip()

    if re.search(r"greater than|less than|[<>≥≤]", head, re.I):
        flags.append("limit_not_point_value")
    elif re.search(r"[~–—-]|\bto\b", head):
        flags.append("range_not_point_value")
    elif (mm := _NUM.match(head)):
        num = float(mm.group(1))

    # The MVL has no unit column and Sohail et al. Table 1/2 units are not recorded
    # in the DB. Per the extraction strategy we do NOT guess or convert units.
    flags.append("unit_not_stated_in_source")
    return num, (cond or None), flags


def pass_b(cur):
    cur.execute(r"""
        WITH mv AS (
          SELECT lower(regexp_replace(compound,'[ ,\-]','','g')) AS norm,
                 min(entry_no)                        AS entry_no,
                 min(NULLIF(odor_threshold,''))       AS thr,
                 min(source_table)                    AS tbl,
                 min(source_pdf)                      AS pdf
            FROM meaty_volatile_library
           GROUP BY 1
          HAVING count(DISTINCT COALESCE(odor_threshold,'')) = 1
        )
        SELECT m.id, mv.entry_no, mv.thr, mv.tbl, mv.pdf
          FROM molecules m
          JOIN mv ON lower(regexp_replace(m.name,'[ ,\-]','','g')) = mv.norm
         WHERE mv.thr IS NOT NULL AND NOT m.is_junk
    """)
    rows = cur.fetchall()
    updates, props, normalized = [], [], 0

    for mid, entry_no, thr, tbl, pdf in rows:
        num, cond, flags = parse_threshold(thr)
        if num is not None:
            normalized += 1
        # odor_threshold_ppb stays NULL: the column asserts ppb and the source does
        # not state a unit. The numeric lives in molecule_properties.value_num.
        updates.append((thr, mid))
        props.append(prop(
            mid, "odor_threshold", raw=thr, num=num,
            unit_raw=None, unit_norm=None,
            deriv="reported",
            method="literature compilation (odour threshold as tabulated)",
            cond=cond, sref=f"mvl:entry_no={entry_no}",
            sloc=f"{pdf} · {tbl}", conf=0.80, flags=flags))

    execute_batch(cur, "UPDATE molecules SET odor_threshold_raw=%s, updated_at=now() "
                       "WHERE id=%s", updates, page_size=200)
    execute_batch(cur, UPSERT_PROP, props, page_size=200)
    return len(updates), normalized


# --------------------------------------------------------------------------- #
# Cross-check: RDKit MW vs the independent moldedup.molecules MW
# --------------------------------------------------------------------------- #
def crosscheck(cur):
    cur.execute("""
        SELECT count(*), count(*) FILTER (WHERE abs(m.molecular_weight - d.molecular_weight) > 0.5)
          FROM molecules m JOIN moldedup.molecules d ON d.inchikey = m.inchikey
         WHERE m.molecular_weight IS NOT NULL AND d.molecular_weight IS NOT NULL""")
    return cur.fetchone()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    conn = db(); cur = conn.cursor()
    a_rows, a_props, unparsed = pass_a(cur)
    b_rows, b_norm = pass_b(cur)
    checked, mismatched = crosscheck(cur)

    print(f"PASS A  molecules updated : {a_rows}")
    print(f"PASS A  provenance rows   : {a_props}")
    print(f"PASS A  unparsable SMILES : {len(unparsed)} {unparsed[:5]}")
    print(f"PASS B  thresholds written: {b_rows}  (numeric-normalized: {b_norm})")
    print(f"CHECK   MW vs moldedup    : {checked} compared, {mismatched} mismatched (>0.5 g/mol)")

    if mismatched:
        conn.rollback(); sys.exit("ABORT: molecular-weight cross-check failed — rolled back.")
    if args.dry_run:
        conn.rollback(); print("\nDRY RUN — rolled back.")
    else:
        conn.commit(); print("\nCOMMITTED.")


if __name__ == "__main__":
    main()
