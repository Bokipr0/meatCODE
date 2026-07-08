#!/usr/bin/env python3
"""LLM extraction pass — fill the per-source tag columns on `sources`.

For each source (title + abstract), Claude (Haiku) extracts:
  pathway[] · method[] · sensory_descriptor[] · matrix[] · compound_class[]  (arrays)
  study_type · main_claim  (text)
and writes them to the flat columns added in migration 0005. The prompt is seeded
with the project's CANONICAL vocabulary (reactions / analytical_methods /
sensory_attributes / product_contexts) so tags stay consistent and can later be
promoted into the normalized junction tables.

Resumable: only processes rows where `main_claim IS NULL`. Run in chunks:
    python3 pipeline/tag_sources.py --limit 8        # validation
    python3 pipeline/tag_sources.py --limit 200      # a chunk
    python3 pipeline/tag_sources.py                  # all remaining
"""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load_env():
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("DATABASE_URL") or line.startswith("ANTHROPIC_API_KEY"):
            k, v = line.split("=", 1); os.environ.setdefault(k, v.strip())

def conn():
    import psycopg2
    return psycopg2.connect(os.environ["DATABASE_URL"])

MODEL = "claude-haiku-4-5-20251001"
BATCH = 8

def vocab(cur):
    def names(t):
        cur.execute(f"select name from {t} order by name"); return [r[0] for r in cur.fetchall()]
    return {
        "pathway (reactions)": names("reactions"),
        "method (analytical_methods)": names("analytical_methods"),
        "sensory_descriptor (sensory_attributes)": names("sensory_attributes"),
        "matrix (product_contexts)": names("product_contexts"),
    }

def system_prompt(v):
    lines = "\n".join(f"  {k}: {', '.join(vals)}" for k, vals in v.items())
    return (
        "You tag meaty-process-flavor literature. For each paper (title + abstract) extract:\n"
        "  pathway[]            reaction/formation pathways (Maillard, Strecker, lipid oxidation, thiamine degradation, nucleotide degradation, ...)\n"
        "  method[]             analytical/experimental methods (GC-MS, GC-O, SPME, sensory panel, ...)\n"
        "  sensory_descriptor[] aroma/taste descriptors (roasted, meaty, sulfurous, umami, off-note, ...)\n"
        "  matrix[]             food matrix/system studied (beef, chicken, plant protein, model system, ...)\n"
        "  compound_class[]     main compound classes (pyrazines, aldehydes, thiols, furanones, ...)\n"
        "  study_type           ONE of: review, experimental, patent, modeling, method, other\n"
        "  main_claim           ONE concise sentence: the paper's core finding.\n\n"
        "PREFER these canonical terms when they fit (else use a short lowercase term):\n" + lines + "\n\n"
        "Use [] when a category doesn't apply. Keep tags short (1-3 words). Base tags ONLY on the text; "
        "do not invent. Return ONLY a JSON array, one object per paper, each with keys "
        "id, pathway, method, sensory_descriptor, matrix, compound_class, study_type, main_claim."
    )

def extract(client, sys_prompt, items):
    lines = [f'id={i} | {n} | {(a or "")[:600]}' for i, n, a in items]
    m = client.messages.create(model=MODEL, max_tokens=1500, system=sys_prompt,
        messages=[{"role": "user", "content": "Tag these papers:\n\n" + "\n\n".join(lines)}])
    t = m.content[0].text.strip()
    return json.loads(t[t.find("["):t.rfind("]") + 1])

def as_list(x):
    if isinstance(x, list): return [str(s).strip() for s in x if str(s).strip()]
    if x: return [str(x).strip()]
    return []

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    load_env()
    if not os.environ.get("ANTHROPIC_API_KEY"): sys.exit("ANTHROPIC_API_KEY missing in .env")
    import anthropic
    client = anthropic.Anthropic()
    cn = conn(); cur = cn.cursor()
    sysp = system_prompt(vocab(cur))
    lim = f"limit {args.limit}" if args.limit else ""
    cur.execute(f"select id, name, abstract from sources where main_claim is null order by priority_score desc nulls last {lim}")
    todo = cur.fetchall()
    if not todo: print("Nothing to tag — all sources have main_claim."); return
    print(f"tagging {len(todo)} sources in batches of {BATCH} ({MODEL})...")
    upd = ("update sources set pathway=%s, method=%s, sensory_descriptor=%s, matrix=%s, "
           "compound_class=%s, study_type=%s, main_claim=%s where id=%s")
    done = 0
    for k in range(0, len(todo), BATCH):
        batch = todo[k:k + BATCH]
        try:
            recs = {int(d["id"]): d for d in extract(client, sysp, batch)}
        except Exception as e:
            print(f"  ! batch {k//BATCH+1} failed: {str(e)[:90]}"); continue
        for sid, name, _ in batch:
            d = recs.get(sid)
            if not d: continue
            cur.execute(upd, (as_list(d.get("pathway")), as_list(d.get("method")),
                as_list(d.get("sensory_descriptor")), as_list(d.get("matrix")),
                as_list(d.get("compound_class")), (d.get("study_type") or None),
                (d.get("main_claim") or None), sid))
            done += 1
        cn.commit()
        print(f"  batch {k//BATCH+1}: tagged {done}/{len(todo)}")
    print(f"done. tagged {done} sources.")
    cn.close()

if __name__ == "__main__":
    main()
