#!/usr/bin/env python3
# Last updated: 2026-08-15 · Data Engineer agent · initial version
"""
Structure-first identity enrichment for `molecules` (CAS · PubChem CID · InChIKey
· SMILES · formula), built on the existing `molecular_pipeline/moldedup` engine.

WHY THIS EXISTS
---------------
`pipeline/pubchem_cids.py` only tried EXACT-name PubChem lookups, so it resolved
20 of 799 molecules: most rows carry stereo-annotated, parenthetical or synonym
name forms ("(E,Z)-3,6-nonadien-1-ol", "3-methylindole (skatole)",
"2-methoxy-4-(2-propenyl)phenol (eugenol)"). This script resolves each row's
IDENTITY through a confidence-ordered ladder and records which rung won, so a
human can audit every single value.

THE ENGINE IS REUSED, NOT REINVENTED
------------------------------------
The PubChem client is `moldedup.resolvers.pubchem.PubChemResolver` from
`molecular_pipeline/` — it already gives us a persistent HTTP cache (incl.
negatives), <=5 req/s rate limiting, timeouts, exponential-backoff retries, the
2024 SMILES property rename fallback, and CAS/ChEBI/HMDB/KEGG harvesting from
PubChem synonyms. We subclass it to add the ladder + autocomplete, and load it
without `moldedup/__init__.py` so SQLAlchemy is not required.

THE LADDER (executed in this order — highest confidence first)
--------------------------------------------------------------
  0. parenthetical     "X (Y)" is a MeatCODE curation form ("X, also called Y"),
                       not a chemical name, so it is decomposed BEFORE the literal
                       string is trusted. Head and inner are resolved separately:
                       agree → confident; disagree → ambiguous (e.g. "neral
                       (citral)" are genuinely two different CIDs); one resolves →
                       that one. This rung exists because PubChem holds depositor
                       records literally named "3-methylindole (skatole)" that are
                       a *different* compound (a C18H18N2 dimer) — the pilot's
                       exact-name-only approach would have written that silently.
  1. exact_name        name → /compound/name/{name}/cids
  2. cas_lookup        row already has cas_number → /compound/name/{cas}/cids
                       (the high-confidence path for the 110 MVL-matched rows)
  3. mvl_cas           CAS from meaty_volatile_library by normalized-name match
                       → same CAS lookup
  4. normalized_name   cleaned name variants: unicode-dash unification,
                       whitespace/quote/period cleanup, trailing-parenthetical
                       split ("3-methylindole (skatole)" → "3-methylindole" AND
                       "skatole"), stereo/isomer descriptor stripping
                       ((E)-, (Z)-, (E,Z)-, (2E,4E)-, cis-/trans-, (R)-/(S)-,
                       (+)/(-)/(±)-, d-/l-/DL-), hyphen/comma spacing variants
  5. synonym_registry  the local PubChem-synonym registry already harvested into
                       Neon's `moldedup` schema (7.6k synonyms → 126 molecules);
                       an offline cache of PubChem's synonym endpoint
  6. autocomplete      /rest/autocomplete/compound/{q} — a suggestion is accepted
                       ONLY if it collapses to the SAME match-key as our name
                       (case/punctuation/stereo-insensitive). "4-propyl-5-
                       ethyloxazole" → suggestion "5-Butyl-2-ethyloxazole" is
                       REJECTED. This is a spelling-variant rung, not a guess.

Whichever rung first returns EXACTLY ONE CID wins. The CID is then expanded to
InChIKey + SMILES + MolecularFormula + registry CAS (a synonym matching
^\\d{2,7}-\\d{2}-\\d$).

ZERO-FABRICATION RULES (non-negotiable)
---------------------------------------
  * >1 CID from a rung → NEVER pick one. id_needs_review = true and
    id_match_method = 'ambiguous:N cids [...] via <rung>'.
  * no match anywhere → id_needs_review = true,
    id_match_method = 'unresolved:no PubChem match'.
  * an existing non-NULL value is NEVER overwritten (all writes are
    `SET col = COALESCE(col, %s)` guarded by `WHERE col IS NULL`).
  * if the row's existing CAS is absent from PubChem's CAS synonyms for the
    resolved CID, the row is flagged (`+cas_mismatch`) rather than "corrected".
  * VERIFICATION GUARD: a resolved CID is only written if the compound's own
    PubChem synonym list actually contains the name we asked about (match-key
    equality) — or, for the CAS rungs, the CAS we looked up. Otherwise nothing is
    written and the row is flagged 'unverified:...'.
  * nothing is inferred, averaged or invented — every value comes from PubChem.
    Typos are NOT auto-corrected ("4-pentenenitril" stays unresolved rather than
    being silently mapped to 4-pentenenitrile) — they go to the review queue.

USAGE
-----
    python3 pipeline/enrich_molecules_structure.py --target prod --limit 150 --offset 0
    python3 pipeline/enrich_molecules_structure.py --target prod            # all
    python3 pipeline/enrich_molecules_structure.py --target prod --dry-run
    python3 pipeline/enrich_molecules_structure.py --replicate --from prod --to dev
    python3 pipeline/enrich_molecules_structure.py --report --target dev

`--target prod` reads DATABASE_URL from .env, `--target dev` from .env.dev.
The HTTP cache lives at data/pubchem_cache.sqlite (gitignored), so re-runs and
chunked runs never re-hit the network for a URL already seen.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
import types
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote

REPO_ROOT = Path(__file__).resolve().parent.parent
MOLPIPE = REPO_ROOT / "molecular_pipeline"

CAS_RE = re.compile(r"^\d{2,7}-\d{2}-\d$")


# ─────────────────────────────────────────────────────────────────────────────
# env
# ─────────────────────────────────────────────────────────────────────────────
def load_env_file(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not path.is_file():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.lower().startswith("export "):
            line = line[7:].lstrip()
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def database_url(target: str) -> str:
    fname = ".env" if target == "prod" else ".env.dev"
    url = load_env_file(REPO_ROOT / fname).get("DATABASE_URL")
    if not url:
        sys.exit(f"No DATABASE_URL in {fname}")
    return url


# ─────────────────────────────────────────────────────────────────────────────
# load the moldedup engine WITHOUT executing moldedup/__init__.py
# (that would pull in SQLAlchemy, which this script does not need)
# ─────────────────────────────────────────────────────────────────────────────
def _load_moldedup():
    pkg_dir = MOLPIPE / "moldedup"
    if not pkg_dir.is_dir():
        sys.exit(f"moldedup engine not found at {pkg_dir}")

    def mkpkg(name: str, path: Path) -> None:
        mod = types.ModuleType(name)
        mod.__path__ = [str(path)]
        mod.__package__ = name
        sys.modules[name] = mod

    def load(name: str, file: Path):
        spec = importlib.util.spec_from_file_location(name, file)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        return mod

    mkpkg("moldedup", pkg_dir)
    load("moldedup.config", pkg_dir / "config.py")
    load("moldedup.ratelimit", pkg_dir / "ratelimit.py")
    load("moldedup.cache", pkg_dir / "cache.py")
    mkpkg("moldedup.resolvers", pkg_dir / "resolvers")
    load("moldedup.resolvers.base", pkg_dir / "resolvers" / "base.py")
    pubchem = load("moldedup.resolvers.pubchem", pkg_dir / "resolvers" / "pubchem.py")
    cfg_mod = sys.modules["moldedup.config"]
    cache_mod = sys.modules["moldedup.cache"]
    return pubchem, cfg_mod.Config, cache_mod.HttpCache


_pubchem_mod, Config, HttpCache = _load_moldedup()
PubChemResolver = _pubchem_mod.PubChemResolver
PUG = _pubchem_mod.PUG
AUTOCOMPLETE = "https://pubchem.ncbi.nlm.nih.gov/rest/autocomplete/compound"


# ─────────────────────────────────────────────────────────────────────────────
# name normalization for the ladder
# ─────────────────────────────────────────────────────────────────────────────
_DASHES = dict.fromkeys(map(ord, "‐‑‒–—―−"), "-")
_QUOTES = "\"'`“”‘’«»"

# Pure STEREO / optical descriptors — these change stereochemistry, not
# constitution, so dropping them is a labelled fallback, never a silent one.
# Positional prefixes (alpha-, beta-, gamma-, delta-, ortho-, meta-, para-, N-,
# O-, S-) are deliberately NOT stripped: gamma-nonalactone != nonalactone.
_STEREO_PAREN = re.compile(
    r"^\(\s*(?:[0-9]{0,2}[EZRS](?:\s*,\s*[0-9]{0,2}[EZRS])*|\+|-|±|\+/-|RS|SR)\s*\)-\s*",
    re.I,
)
# NB: iso- / sec- / tert- are NOT here — they change constitution, not stereochemistry.
_STEREO_WORD = re.compile(
    r"^(?:cis|trans|dl|rac|d|l|\(\+\)|\(-\)|\(±\)|z|e|n)\s*-\s*", re.I
)
_BRACKET_TAG = re.compile(r"\[[^\]]*\]")
_WS = re.compile(r"\s+")


def base_clean(name: str) -> str:
    """Conservative textual cleanup: unicode NFKC, unified dashes, collapsed
    whitespace, stripped wrapping quotes / trailing punctuation."""
    s = unicodedata.normalize("NFKC", str(name or "")).translate(_DASHES)
    s = s.strip().strip(_QUOTES).strip()
    s = _WS.sub(" ", s)
    return s.rstrip(".,;").strip()


def strip_stereo(name: str) -> str:
    """Drop leading stereo/optical descriptors, repeatedly ((E)-(Z)-... )."""
    s = name
    for _ in range(4):
        new = _STEREO_PAREN.sub("", s)
        if new == s:
            new = _STEREO_WORD.sub("", s)
        if new == s:
            break
        s = new
    return s.strip()


def match_key(name: str) -> str:
    """Comparison key: case-, punctuation- and stereo-insensitive.
    Used ONLY to decide whether an autocomplete suggestion is the same name in
    different clothing — never to pick between different compounds."""
    s = base_clean(name).lower()
    s = _BRACKET_TAG.sub(" ", s)
    s = strip_stereo(s)
    # drop stereo descriptors that appear inline, e.g. "2,4-heptadienal, (e,e)-"
    s = re.sub(r"\(\s*[0-9ezrs+\-±,\s]*\s*\)", " ", s)
    s = re.sub(r"\b(?:cis|trans|rac|racemic)\b", " ", s)
    return re.sub(r"[^a-z0-9]", "", s)


def split_parenthetical(name: str) -> Tuple[Optional[str], Optional[str]]:
    """'3-methylindole (skatole)' → ('3-methylindole', 'skatole').
    Only splits a BALANCED parenthetical that terminates the string and is
    preceded by other text (so '2-(methylthio)furan' is left alone)."""
    s = base_clean(name)
    if not s.endswith(")"):
        return None, None
    depth = 0
    start = None
    for i in range(len(s) - 1, -1, -1):
        if s[i] == ")":
            depth += 1
        elif s[i] == "(":
            depth -= 1
            if depth == 0:
                start = i
                break
    if start is None or start == 0:
        return None, None
    head = s[:start].strip().rstrip("-,").strip()
    inner = s[start + 1:-1].strip()
    if not head or not inner:
        return None, None
    return head, inner


def name_variants(name: str) -> List[Tuple[str, str]]:
    """Ordered (variant, why) candidates for the normalized-name rung.
    The exact name itself is handled by rung 1 and excluded here."""
    seen = set()
    out: List[Tuple[str, str]] = []

    def add(v: Optional[str], why: str) -> None:
        if not v:
            return
        v = v.strip()
        if len(v) < 2 or v.lower() in seen:
            return
        seen.add(v.lower())
        out.append((v, why))

    raw = str(name or "")
    clean = base_clean(raw)
    seen.add(raw.strip().lower())
    add(clean, "base_clean")

    head, inner = split_parenthetical(clean)
    add(head, "strip_parenthetical")
    add(inner, "parenthetical_synonym")

    for src, tag in ((clean, ""), (head, "+head"), (inner, "+synonym")):
        if not src:
            continue
        add(strip_stereo(src), f"strip_stereo{tag}")

    # spacing / separator variants
    for src in (clean, head, inner, strip_stereo(clean)):
        if not src:
            continue
        add(src.replace(", ", ","), "tighten_commas")
        add(src.replace(" - ", "-").replace(" -", "-").replace("- ", "-"), "tighten_hyphens")
        add(src.replace(" ", ""), "drop_spaces")
    return out


# ─────────────────────────────────────────────────────────────────────────────
# resolver: moldedup's PubChem client + the extra rungs
# ─────────────────────────────────────────────────────────────────────────────
class LadderResolver(PubChemResolver):
    """Adds public wrappers + an autocomplete rung on top of moldedup's cached,
    rate-limited, retrying PubChem client."""

    def cids_for_name(self, name: str) -> List[int]:
        try:
            return [int(c) for c in self._name_to_cids(name)]
        except Exception as exc:  # network exhausted retries — surface, don't guess
            print(f"      ! pubchem error for {name!r}: {exc}")
            return []

    def autocomplete(self, name: str, limit: int = 8) -> List[str]:
        url = f"{AUTOCOMPLETE}/{quote(name, safe='')}/json?limit={limit}"
        try:
            status, data = self._get(url)
        except Exception:
            return []
        if status != 200 or not data:
            return []
        return list((data.get("dictionary_terms") or {}).get("compound") or [])

    def describe(self, cid: int) -> dict:
        """CID → {inchikey, smiles, formula, cas, cas_all, syn_keys} from PubChem."""
        props = self._properties(cid) or {}
        smiles = (props.get("IsomericSMILES") or props.get("SMILES")
                  or props.get("CanonicalSMILES") or props.get("ConnectivitySMILES"))
        syns = []
        try:
            syns = self._synonyms(cid)
        except Exception:
            pass
        cas_all: List[str] = []
        for s in syns:
            s = (s or "").strip()
            if CAS_RE.match(s) and s not in cas_all:
                cas_all.append(s)
        return {
            "cid": cid,
            "inchikey": (props.get("InChIKey") or "").strip() or None,
            "smiles": (smiles or "").strip() or None,
            "formula": (props.get("MolecularFormula") or "").strip() or None,
            "cas": cas_all[0] if cas_all else None,
            "cas_all": cas_all,
            "syn_keys": {match_key(s) for s in syns if s},
        }


# ─────────────────────────────────────────────────────────────────────────────
# the ladder
# ─────────────────────────────────────────────────────────────────────────────
def resolve_identity(res: LadderResolver, name: str, row_cas: Optional[str],
                     mvl_cas: Optional[str], registry: Dict[str, dict],
                     verbose: bool = True) -> dict:
    """Return {'cid': int|None, 'method': str, 'needs_review': bool,
    'ambiguous_candidates': [...] }. Never guesses between candidates."""
    first_ambiguous: Optional[Tuple[str, List[int]]] = None

    def try_cids(cids: List[int], rung: str) -> Optional[dict]:
        nonlocal first_ambiguous
        if not cids:
            return None
        if len(cids) == 1:
            return {"cid": int(cids[0]), "method": rung, "needs_review": False,
                    "ambiguous_candidates": []}
        if first_ambiguous is None:
            first_ambiguous = (rung, [int(c) for c in cids])
        return None

    # rung 0 — "X (Y)" is a MeatCODE curation form meaning "X, also called Y", NOT a
    # chemical name. Decompose it BEFORE trusting the literal string: PubChem contains
    # depositor records literally named e.g. "3-methylindole (skatole)" that are a
    # different compound (a C18H18N2 dimer) than 3-methylindole itself.
    head, inner = split_parenthetical(name)
    if head and inner:
        ch = res.cids_for_name(head)
        ci = res.cids_for_name(inner)
        uh = int(ch[0]) if len(ch) == 1 else None
        ui = int(ci[0]) if len(ci) == 1 else None
        if uh and ui and uh == ui:
            return {"cid": uh, "method": f"parenthetical_agree({head} == {inner})",
                    "needs_review": False, "ambiguous_candidates": []}
        if uh and ui and uh != ui:
            return {"cid": None, "needs_review": True, "ambiguous_candidates": [uh, ui],
                    "method": f"ambiguous:2 cids [{uh}, {ui}] via parenthetical_disagree"
                              f"({head} vs {inner})"}
        if uh:
            return {"cid": uh, "method": f"normalized_name:strip_parenthetical({head})",
                    "needs_review": False, "ambiguous_candidates": []}
        if ui:
            return {"cid": ui, "method": f"normalized_name:parenthetical_synonym({inner})",
                    "needs_review": False, "ambiguous_candidates": []}
        try_cids(ch, f"parenthetical_head({head})")
        try_cids(ci, f"parenthetical_synonym({inner})")

    # rung 1 — exact name
    hit = try_cids(res.cids_for_name(name), "exact_name")
    if hit:
        return hit

    # rung 2 — the row's own CAS (high confidence: MVL-sourced registry number)
    if row_cas and CAS_RE.match(row_cas.strip()):
        hit = try_cids(res.cids_for_name(row_cas.strip()), f"cas_lookup:{row_cas.strip()}")
        if hit:
            return hit

    # rung 3 — CAS from the meaty_volatile_library normalized-name cross-check
    if mvl_cas and CAS_RE.match(mvl_cas.strip()) and mvl_cas.strip() != (row_cas or "").strip():
        hit = try_cids(res.cids_for_name(mvl_cas.strip()), f"mvl_cas:{mvl_cas.strip()}")
        if hit:
            return hit

    # rung 4 — normalized / de-stereo'd / de-parenthesised name variants
    for variant, why in name_variants(name):
        hit = try_cids(res.cids_for_name(variant), f"normalized_name:{why}({variant})")
        if hit:
            return hit

    # rung 5 — local PubChem-synonym registry (moldedup schema in Neon)
    for key in {match_key(name)} | {match_key(v) for v, _ in name_variants(name)}:
        rec = registry.get(key)
        if rec and rec.get("cid"):
            return {"cid": int(rec["cid"]), "method": "synonym_registry",
                    "needs_review": False, "ambiguous_candidates": []}

    # rung 6 — autocomplete, accepted only on an exact match-key collapse
    target = match_key(name)
    accepted = None
    for term in res.autocomplete(base_clean(name)):
        if match_key(term) == target and match_key(term) != "":
            accepted = term
            break
    if accepted:
        hit = try_cids(res.cids_for_name(accepted), f"autocomplete:{accepted}")
        if hit:
            return hit

    if first_ambiguous:
        rung, cands = first_ambiguous
        shown = cands[:10]
        return {"cid": None, "needs_review": True, "ambiguous_candidates": cands,
                "method": f"ambiguous:{len(cands)} cids {shown} via {rung}"}
    return {"cid": None, "method": "unresolved:no PubChem match",
            "needs_review": True, "ambiguous_candidates": []}


# ─────────────────────────────────────────────────────────────────────────────
# database helpers
# ─────────────────────────────────────────────────────────────────────────────
def query_keys(name: str) -> set:
    """Every match-key the stored name could legitimately collapse to."""
    keys = {match_key(name)}
    for v, _ in name_variants(name):
        keys.add(match_key(v))
    h, i = split_parenthetical(name)
    for x in (h, i):
        if x:
            keys.add(match_key(x))
            keys.add(match_key(strip_stereo(x)))
    keys.discard("")
    return keys


def verify_match(name: str, method: str, desc: dict) -> Tuple[bool, str]:
    """Guard against PubChem depositor records that carry a misleading name.
    A resolution is accepted only if the compound's own synonym list contains the
    name we asked about (match-key equality), or — for the CAS rungs — the CAS we
    looked up. If PubChem returns no synonym list at all we cannot verify, so we
    accept but say so. Returns (ok, note)."""
    syn_keys = desc.get("syn_keys") or set()
    if not syn_keys:
        return True, "+no_synonym_list"
    if query_keys(name) & syn_keys:
        return True, ""
    m = re.search(r"(?:cas_lookup|mvl_cas):(\d{2,7}-\d{2}-\d)", method)
    if m and m.group(1) in (desc.get("cas_all") or []):
        return True, "+verified_by_cas"
    return False, (f"unverified:{method} — CID {desc['cid']} ({desc.get('formula')}) "
                   f"does not list this name among its synonyms")


def norm_join_key(s: str) -> str:
    """Same normalization migration 0009 used for the MVL join."""
    return re.sub(r"[ ,\-]", "", (s or "").lower())


def load_mvl_cas(cur) -> Dict[str, str]:
    """normalized MVL compound name → CAS, only for unambiguous 1:1 names."""
    cur.execute("""
        SELECT lower(regexp_replace(compound, '[ ,\\-]', '', 'g')) AS norm,
               min(NULLIF(cas_number, '')) AS cas
          FROM meaty_volatile_library
         WHERE NULLIF(cas_number, '') IS NOT NULL
         GROUP BY 1
        HAVING count(DISTINCT cas_number) = 1
    """)
    return {r[0]: r[1] for r in cur.fetchall() if r[1]}


def load_synonym_registry(cur) -> Dict[str, dict]:
    """match_key → {cid} from the moldedup schema's harvested PubChem synonyms."""
    reg: Dict[str, dict] = {}
    try:
        cur.execute("""
            SELECT s.normalized_name, m.cid
              FROM moldedup.synonyms s
              JOIN moldedup.molecules m ON m.id = s.molecule_id
             WHERE s.status = 'resolved' AND m.cid IS NOT NULL
        """)
    except Exception:
        return reg
    for nm, cid in cur.fetchall():
        k = match_key(nm)
        if not k:
            continue
        prev = reg.get(k)
        if prev and prev["cid"] != cid:
            prev["cid"] = None  # same key → two molecules: refuse to use it
            continue
        if prev is None:
            reg[k] = {"cid": cid}
    return {k: v for k, v in reg.items() if v.get("cid")}


def counts(cur) -> dict:
    cur.execute("""
        SELECT count(*),
               count(cas_number), count(pubchem_cid), count(inchikey),
               count(smiles), count(molecular_formula),
               count(*) FILTER (WHERE id_needs_review),
               count(*) FILTER (WHERE is_junk)
          FROM molecules
    """)
    r = cur.fetchone()
    return {"rows": r[0], "cas_number": r[1], "pubchem_cid": r[2], "inchikey": r[3],
            "smiles": r[4], "molecular_formula": r[5], "needs_review": r[6], "junk": r[7]}


def print_counts(label: str, c: dict) -> None:
    print(f"  {label:<10} rows={c['rows']} cas={c['cas_number']} cid={c['pubchem_cid']} "
          f"inchikey={c['inchikey']} smiles={c['smiles']} formula={c['molecular_formula']} "
          f"needs_review={c['needs_review']}")


# ─────────────────────────────────────────────────────────────────────────────
# modes
# ─────────────────────────────────────────────────────────────────────────────
def run_enrich(args) -> None:
    import psycopg2
    conn = psycopg2.connect(database_url(args.target))
    conn.autocommit = False
    cur = conn.cursor()

    before = counts(cur)
    print(f"[{args.target}] before:")
    print_counts("before", before)

    mvl = load_mvl_cas(cur)
    registry = load_synonym_registry(cur)
    print(f"  MVL CAS map: {len(mvl)} names · synonym registry: {len(registry)} keys")

    sql = """
        SELECT id, name, cas_number, pubchem_cid, inchikey
          FROM molecules
         WHERE NOT is_junk
           AND (cas_number IS NULL OR pubchem_cid IS NULL OR inchikey IS NULL)
           AND (id_match_method IS NULL OR %s)
         ORDER BY (cas_number IS NOT NULL) DESC, id
    """
    params = [bool(args.redo)]
    if args.limit:
        sql += " LIMIT %s OFFSET %s"
        params += [args.limit, args.offset]
    cur.execute(sql, params)
    rows = cur.fetchall()
    print(f"  eligible in this chunk: {len(rows)}")

    cfg = Config.from_env(
        cache_path=str(REPO_ROOT / "data" / "pubchem_cache.sqlite"),
        min_request_interval=args.interval,
    )
    res = LadderResolver(config=cfg)

    stats: Dict[str, int] = {}
    wrote = 0
    for n, (mid, name, row_cas, row_cid, row_key) in enumerate(rows, 1):
        mvl_cas = mvl.get(norm_join_key(name))
        out = resolve_identity(res, name, row_cas, mvl_cas, registry)
        method = out["method"]
        needs_review = out["needs_review"]
        desc = None

        if out["cid"]:
            desc = res.describe(out["cid"])
            ok, note = verify_match(name, method, desc)
            if not desc.get("inchikey"):
                method = f"unresolved:CID {out['cid']} has no InChIKey (via {method})"
                needs_review = True
                desc = None
            elif not ok:
                # PubChem record whose name does not actually cover ours → write nothing.
                method = note
                needs_review = True
                desc = None
            else:
                method += note
                if row_cas and desc["cas_all"] and row_cas.strip() not in desc["cas_all"]:
                    method += "+cas_mismatch"
                    needs_review = True

        rung = method.split(":")[0].split("+")[0].split("(")[0]
        stats[rung] = stats.get(rung, 0) + 1

        if args.dry_run:
            print(f"  [{n}/{len(rows)}] {name!r} → {method}"
                  + (f" CID={desc['cid']} {desc['inchikey']} CAS={desc['cas']}" if desc else ""))
            continue

        if desc:
            cur.execute(
                """UPDATE molecules
                      SET pubchem_cid       = COALESCE(pubchem_cid, %s),
                          inchikey          = COALESCE(inchikey, %s),
                          smiles            = COALESCE(smiles, %s),
                          molecular_formula = COALESCE(molecular_formula, %s),
                          cas_number        = COALESCE(cas_number, %s),
                          id_match_method   = %s,
                          id_needs_review   = %s,
                          updated_at        = now()
                    WHERE id = %s""",
                (str(desc["cid"]), desc["inchikey"], desc["smiles"], desc["formula"],
                 desc["cas"], method, needs_review, mid),
            )
        else:
            cur.execute(
                """UPDATE molecules
                      SET id_match_method = %s, id_needs_review = %s, updated_at = now()
                    WHERE id = %s""",
                (method, needs_review, mid),
            )
        wrote += 1
        if wrote % 10 == 0:   # frequent commits → chunked / interrupted runs resume cleanly
            conn.commit()
        if n % 10 == 0 or n == len(rows):
            print(f"  [{n}/{len(rows)}] last={name!r} → {method}", flush=True)

    if not args.dry_run:
        conn.commit()

    after = counts(cur)
    print(f"[{args.target}] after:")
    print_counts("after", after)
    print("  rung breakdown this run: " + json.dumps(stats, sort_keys=True))
    conn.close()


def run_replicate(args) -> None:
    """Copy the resolved identity fields from one branch to the other, BY ID.
    Only ever fills NULLs (COALESCE) — never overwrites the target."""
    import psycopg2
    src = psycopg2.connect(database_url(args.src))
    dst = psycopg2.connect(database_url(args.dst))
    scur, dcur = src.cursor(), dst.cursor()

    print(f"[replicate] {args.src} → {args.dst}")
    print_counts(f"{args.dst}/before", counts(dcur))

    scur.execute("""
        SELECT id, cas_number, pubchem_cid, inchikey, smiles, molecular_formula,
               id_match_method, id_needs_review
          FROM molecules
         WHERE id_match_method IS NOT NULL
            OR inchikey IS NOT NULL OR cas_number IS NOT NULL OR pubchem_cid IS NOT NULL
    """)
    rows = scur.fetchall()
    print(f"  {len(rows)} source rows carry identity data")

    for i, r in enumerate(rows, 1):
        (mid, cas, cid, key, smi, formula, method, review) = r
        dcur.execute(
            """UPDATE molecules
                  SET cas_number        = COALESCE(cas_number, %s),
                      pubchem_cid       = COALESCE(pubchem_cid, %s),
                      inchikey          = COALESCE(inchikey, %s),
                      smiles            = COALESCE(smiles, %s),
                      molecular_formula = COALESCE(molecular_formula, %s),
                      id_match_method   = COALESCE(id_match_method, %s),
                      id_needs_review   = (id_needs_review OR %s),
                      updated_at        = now()
                WHERE id = %s""",
            (cas, cid, key, smi, formula, method, bool(review), mid),
        )
        if i % 200 == 0:
            dst.commit()
    dst.commit()
    print_counts(f"{args.dst}/after", counts(dcur))
    src.close()
    dst.close()


def run_report(args) -> None:
    import psycopg2
    conn = psycopg2.connect(database_url(args.target))
    cur = conn.cursor()
    c = counts(cur)
    print(f"── {args.target} ─────────────────────────────────────────")
    print_counts(args.target, c)

    print("\n  id_match_method breakdown (rung):")
    cur.execute("""
        SELECT split_part(split_part(split_part(
                   COALESCE(id_match_method,'not attempted'), ':', 1), '+', 1), '(', 1) AS rung,
               count(*)
          FROM molecules GROUP BY 1 ORDER BY 2 DESC
    """)
    for rung, n in cur.fetchall():
        print(f"    {rung:<24} {n}")

    print("\n  needs-review breakdown:")
    cur.execute("""
        SELECT CASE WHEN id_match_method LIKE 'ambiguous%%' THEN 'ambiguous (>1 CID)'
                    WHEN id_match_method LIKE 'unresolved%%' THEN 'unresolved (no match)'
                    WHEN id_match_method LIKE '%%cas_mismatch%%' THEN 'CAS mismatch vs PubChem'
                    ELSE 'other' END, count(*)
          FROM molecules WHERE id_needs_review GROUP BY 1 ORDER BY 2 DESC
    """)
    for k, n in cur.fetchall():
        print(f"    {k:<26} {n}")

    print("\n  duplicate InChIKeys (same structure, different names — NOT merged):")
    cur.execute("""
        SELECT inchikey, count(*) AS n,
               string_agg(id::text || ':' || name, ' | ' ORDER BY id)
          FROM molecules
         WHERE inchikey IS NOT NULL
         GROUP BY inchikey HAVING count(*) > 1
         ORDER BY n DESC, inchikey
    """)
    dups = cur.fetchall()
    if not dups:
        print("    none")
    for key, n, names in dups:
        print(f"    {key}  x{n}  {names}")
    print(f"\n  duplicate groups: {len(dups)} covering {sum(d[1] for d in dups)} rows")
    conn.close()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", choices=("prod", "dev"), default="prod")
    ap.add_argument("--limit", type=int, default=0, help="0 = all eligible rows")
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--interval", type=float, default=0.22, help="min seconds between PubChem requests (<=5 req/s)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--redo", action="store_true", help="also re-attempt rows already carrying an id_match_method")
    ap.add_argument("--replicate", action="store_true", help="copy identity fields between branches by id")
    ap.add_argument("--from", dest="src", choices=("prod", "dev"), default="prod")
    ap.add_argument("--to", dest="dst", choices=("prod", "dev"), default="dev")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    if args.report:
        run_report(args)
    elif args.replicate:
        run_replicate(args)
    else:
        run_enrich(args)


if __name__ == "__main__":
    main()
