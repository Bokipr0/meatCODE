#!/usr/bin/env python3
# Last updated: 2026-07-20 15:05 UTC · Data pipeline · LLM-categorize molecules.category into meat-flavor chemical classes
"""
Categorize MeatCODE molecules into a fixed chemical-class taxonomy and write
`molecules.category` back to Neon.

Why: the Molecules table only had 10/799 rows categorized ("Fats"), so the
category filter (and the Fats landing default) were near-empty. This fills the
NULL / "Unclassified" rows by asking a small model to classify each molecule by
its dominant chemical class, in batches.

Taxonomy (single best class per molecule; "Fats" = fatty acids / glycerides /
lipids, kept compatible with the 10 pre-existing curated "Fats"):
    Fats · Aldehydes · Ketones · Pyrazines · Sulfur compounds · Furans ·
    Nitrogen compounds · Alcohols · Acids · Esters · Lactones · Terpenes ·
    Phenols · Hydrocarbons · Other

Safe by design: only touches rows where category IS NULL OR category='Unclassified'
(the curated Fats/Proteins rows are preserved). Idempotent-ish — re-running only
re-touches still-uncategorized rows.

Run:
    python3 pipeline/categorize_molecules.py --dry-run --limit 40   # preview, no writes
    python3 pipeline/categorize_molecules.py                        # full run, writes to Neon
Reads DATABASE_URL + ANTHROPIC_API_KEY from meatCODE/.env. Needs: pip install anthropic psycopg2-binary
"""
from __future__ import annotations
import argparse, json, re, sys, time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL = "claude-haiku-4-5-20251001"
BATCH_DEFAULT = 40

CATEGORIES = [
    "Fats", "Aldehydes", "Ketones", "Pyrazines", "Sulfur compounds", "Furans",
    "Nitrogen compounds", "Alcohols", "Acids", "Esters", "Lactones", "Terpenes",
    "Phenols", "Hydrocarbons", "Other",
]
_CANON = {c.lower(): c for c in CATEGORIES}

SYSTEM = (
    "You are a flavor/aroma chemist classifying volatile and precursor molecules by their "
    "single dominant chemical class. Choose EXACTLY ONE label per molecule, ONLY from this list:\n"
    + ", ".join(CATEGORIES) + ".\n"
    "Guidance: 'Fats' = fatty acids, mono/di/triglycerides and clearly lipid molecules. "
    "'Sulfur compounds' = anything with a thiol/sulfide/disulfide/thiophene/thiazole (sulfur dominates). "
    "'Pyrazines' get their own label; other N-heterocycles (pyrroles, pyridines, oxazoles, oxazolines) = "
    "'Nitrogen compounds'. 'Furans' includes furanones. Pick by the principal functional group; if a "
    "molecule has several, choose the one most characteristic for aroma chemistry. Use 'Other' only if "
    "none genuinely fit. Return ONLY a JSON array of objects like "
    '[{"id":123,"category":"Aldehydes"}], one per molecule, no prose.'
)


def _env(key):
    envp = REPO_ROOT / ".env"
    if envp.exists():
        for line in envp.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    import os
    return os.environ.get(key)


def _canon(cat):
    if not cat:
        return "Other"
    return _CANON.get(str(cat).strip().lower(), "Other")


def _heuristic(name):
    """Fast, offline classification from the molecule name. Chemical nomenclature
    encodes the functional group, so first-match-by-priority is quite accurate for
    aroma volatiles. Ring/heteroatom classes are checked before suffix rules."""
    n = (name or "").strip().lower()
    def has(*subs):
        return any(s in n for s in subs)
    if has("limonene", "pinene", "terpin", "myrcene", "carene", "terpineol", "linalool",
           "geraniol", "citronell", "caryophyllene", "farnesene", "ocimene", "camphene",
           "sabinene", "menthol", "menthone", "borneol", "cadinene", "humulene", "nerol",
           "citral", "terpene"):
        return "Terpenes"
    if has("pyrazine"):
        return "Pyrazines"
    if has("thiophene", "thiazol", "thiadiazol", "dithiazine", "dithiol", "dithiole",
           "dithian", "trithiolane", "trithiane", "tetrathiane"):
        return "Sulfur compounds"
    if has("furan", "furfur", "furanone"):
        return "Furans"
    if has("pyrrol", "pyridin", "pyrimidin", "oxazol", "isoxazol", "indol", "skatole",
           "piperidin", "morpholin", "quinoxalin", "imidazol", "amine"):
        return "Nitrogen compounds"
    if has("thio", "mercapto", "sulfid", "sulfanyl", "disulf", "trisulf", "sulfur", "sulfhydryl"):
        return "Sulfur compounds"
    if has("palmit", "stear", "oleic", "olei", "linole", "myrist", "lauric", "caproic",
           "caprylic", "capric", "glycer", "fatty", "arachid"):
        return "Fats"
    if has("lactone") or n.endswith("olide"):
        return "Lactones"
    if has("phenol", "guaiacol", "cresol", "eugenol", "vanillin", "vanillate", "catechol",
           "thymol", "carvacrol"):
        return "Phenols"
    if has("acid"):
        return "Acids"
    if (has("acetate", "propanoate", "butanoate", "hexanoate", "octanoate", "benzoate",
            "formate", "butyrate", "caproate", "valerate", "propionate") or n.endswith("oate")):
        return "Esters"
    if n.endswith("al") or has("aldehyde"):
        return "Aldehydes"
    if n.endswith("one") or has("ketone"):
        return "Ketones"
    if n.endswith("ol") or n.endswith("diol") or has("alcohol"):
        return "Alcohols"
    if (has("naphthalene", "benzene", "toluene", "xylene", "styrene", "indene",
            "anthracene", "biphenyl") or n.endswith("ane") or n.endswith("ene") or n.endswith("yne")):
        return "Hydrocarbons"
    return "Other"


def _classify_batch(client, rows):
    """rows: list of (id, name). Returns {id: category}."""
    listing = "\n".join(f'{r[0]}\t{r[1]}' for r in rows)
    msg = client.messages.create(
        model=MODEL, max_tokens=3000, system=SYSTEM,
        messages=[{"role": "user", "content": "Classify these molecules (id<TAB>name):\n" + listing}],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    m = re.search(r"\[.*\]", text, re.S)
    if not m:
        return {}
    out = {}
    for obj in json.loads(m.group(0)):
        try:
            out[int(obj["id"])] = _canon(obj.get("category"))
        except Exception:
            continue
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="classify + print, no DB writes")
    ap.add_argument("--limit", type=int, default=0, help="only process the first N rows (0 = all)")
    ap.add_argument("--batch", type=int, default=BATCH_DEFAULT)
    ap.add_argument("--heuristic", action="store_true",
                    help="classify offline from the molecule name (instant, no API) instead of the LLM")
    args = ap.parse_args()

    import psycopg2
    db = _env("DATABASE_URL")
    if not db:
        raise SystemExit("DATABASE_URL not found in .env")
    conn = psycopg2.connect(db)
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM molecules WHERE category IS NULL OR category='Unclassified' ORDER BY id")
    todo = cur.fetchall()
    if args.limit:
        todo = todo[:args.limit]
    mode = "heuristic (name-based, offline)" if args.heuristic else f"LLM {MODEL}"
    print(f"molecules needing a category: {len(todo)}  (mode: {mode}, dry-run={args.dry_run})")
    if not todo:
        conn.close(); return 0

    # ── Offline name-based path: instant, no API. One bulk UPDATE (not 748
    #    round-trips) so it finishes in a single query. ──
    if args.heuristic:
        pairs = [(int(mid), _heuristic(name)) for mid, name in todo]
        tally = {}
        for _, cat in pairs:
            tally[cat] = tally.get(cat, 0) + 1
        if not args.dry_run:
            from psycopg2.extras import execute_values
            execute_values(
                cur,
                "UPDATE molecules AS m SET category = v.cat "
                "FROM (VALUES %s) AS v(id, cat) WHERE m.id = v.id::bigint",
                pairs, template="(%s, %s)", page_size=1000,
            )
            conn.commit()
        print("\nresulting distribution (this run):")
        for c, n in sorted(tally.items(), key=lambda x: -x[1]):
            print(f"  {c:22} {n}")
        print(f"\n{'DRY RUN — no writes' if args.dry_run else f'bulk-updated {len(pairs)} category values in Neon'}")
        conn.close()
        return 0

    try:
        import anthropic
    except ImportError:
        raise SystemExit("anthropic not installed. Run: pip install anthropic")
    client = anthropic.Anthropic(api_key=_env("ANTHROPIC_API_KEY"))

    updated, tally = 0, {}
    for i in range(0, len(todo), args.batch):
        batch = todo[i:i + args.batch]
        try:
            verdicts = _classify_batch(client, batch)
        except Exception as e:
            sys.stderr.write(f"  batch {i//args.batch} failed: {str(e)[:160]}\n"); continue
        for mid, _name in batch:
            cat = verdicts.get(mid, "Other")
            tally[cat] = tally.get(cat, 0) + 1
            if not args.dry_run:
                cur.execute("UPDATE molecules SET category=%s WHERE id=%s", (cat, mid))
                updated += 1
        if not args.dry_run:
            conn.commit()
        print(f"  batch {i//args.batch + 1}/{(len(todo)+args.batch-1)//args.batch} done ({len(batch)} rows)")
        time.sleep(0.1)

    print("\nresulting distribution (this run):")
    for c, n in sorted(tally.items(), key=lambda x: -x[1]):
        print(f"  {c:22} {n}")
    print(f"\n{'DRY RUN — no writes' if args.dry_run else f'wrote {updated} category values to Neon'}")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
