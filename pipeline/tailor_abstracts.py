#!/usr/bin/env python3
# Last updated: 2026-08-15 · Data Engineer agent · initial version (deterministic template, first 30 run)
"""
Compose sources.tailored_abstract — a 3–4 sentence MeatCODE-tailored abstract —
by DETERMINISTIC template composition from fields already on the row:
    name, abstract, main_claim, matrix, method, pathway, sensory_descriptor.

No API calls, no generation, no fabrication: every sentence is either a verbatim
extract (first sentence of the stored abstract; the stored main_claim) or a
fixed template whose slots are filled with the row's own tag arrays. Clauses
whose source field is empty are dropped, never invented.

Shape (3–4 sentences):
  1. What was studied  — first sentence of the stored abstract (verbatim).
  2. Matrix / method   — "The work concerns <matrix>, using <method>." (only if tagged)
  3. Main claim        — the stored main_claim (verbatim).
  4. Why it matters    — fixed template naming the tagged pathway(s) and
                         sensory descriptor(s); generic fallback if untagged.

Eligibility: abstract AND main_claim non-empty. Only fills rows where
tailored_abstract IS NULL (use --force to recompose). Ordered by
relevance_llm DESC, id.

Usage (from repo root):
    python3 pipeline/tailor_abstracts.py --limit 30 [--dry-run] [--force]
"""
import argparse
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


def load_env():
    env = REPO_ROOT / ".env"
    if env.is_file():
        for raw in env.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.lower().startswith("export "):
                line = line[7:].lstrip()
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v


def first_sentence(text: str, max_len: int = 400) -> str:
    """Deterministic first-sentence extract (verbatim, whitespace-normalized)."""
    t = re.sub(r"\s+", " ", text).strip()
    # split at the first sentence-ending period followed by a space + uppercase,
    # avoiding common decimal/abbreviation false cuts by requiring the uppercase.
    m = re.search(r"[.!?](?=\s+[A-Z])", t)
    s = t[: m.end()] if m else t
    if len(s) > max_len:
        s = s[:max_len].rsplit(" ", 1)[0].rstrip(",;:") + " …"
    return s


def join_list(items, max_items: int = 3) -> str:
    items = [i.strip() for i in (items or []) if i and i.strip()]
    items = items[:max_items]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def end_period(s: str) -> str:
    s = s.strip()
    return s if s.endswith((".", "!", "?", "…")) else s + "."


def compose(row) -> str:
    name, abstract, main_claim, matrix, method, pathway, sensory = row
    sentences = []
    # 1. what was studied (verbatim extract)
    sentences.append(end_period(first_sentence(abstract)))
    # 2. matrix / method (only from tags)
    mx, me = join_list(matrix), join_list(method)
    if mx and me:
        sentences.append(f"The work concerns {mx}, using {me}.")
    elif mx:
        sentences.append(f"The work concerns {mx}.")
    elif me:
        sentences.append(f"The work uses {me}.")
    # 3. main claim (verbatim)
    sentences.append(end_period(f"Main claim: {main_claim.strip()}"))
    # 4. why it matters for meaty flavor (fixed template from tags)
    pw, sd = join_list(pathway), join_list(sensory)
    if pw and sd:
        sentences.append(
            f"For MeatCODE, this is evidence on {pw} chemistry with reported "
            f"{sd} sensory relevance for building meaty flavor."
        )
    elif pw:
        sentences.append(f"For MeatCODE, this is evidence on {pw} chemistry relevant to building meaty flavor.")
    elif sd:
        sentences.append(f"For MeatCODE, this carries reported {sd} sensory relevance for building meaty flavor.")
    else:
        sentences.append("For MeatCODE, this adds source-backed evidence for building meaty flavor.")
    return " ".join(sentences)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="recompose even if already set")
    args = ap.parse_args()

    load_env()
    import psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()

    cur.execute("SELECT count(*) FROM sources WHERE tailored_abstract IS NOT NULL")
    before = cur.fetchone()[0]

    skip = "" if args.force else "AND tailored_abstract IS NULL"
    cur.execute(
        f"""SELECT id, name, abstract, main_claim, matrix, method, pathway, sensory_descriptor
              FROM sources
             WHERE COALESCE(abstract, '') <> '' AND COALESCE(main_claim, '') <> '' {skip}
             ORDER BY relevance_llm DESC NULLS LAST, id
             LIMIT %s""",
        (args.limit,),
    )
    rows = cur.fetchall()
    print(f"tailored_abstract non-null before: {before}; composing {len(rows)}")

    for r in rows:
        sid = r[0]
        text = compose(r[1:])
        if args.dry_run:
            print(f"--- [{sid}] {r[1][:70]}\n{text}\n")
        else:
            cur.execute("UPDATE sources SET tailored_abstract = %s WHERE id = %s", (text, sid))
    if not args.dry_run:
        conn.commit()

    cur.execute("SELECT count(*) FROM sources WHERE tailored_abstract IS NOT NULL")
    after = cur.fetchone()[0]
    print(f"done | tailored_abstract non-null: {before} -> {after}")
    conn.close()


if __name__ == "__main__":
    main()
