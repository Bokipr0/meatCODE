#!/usr/bin/env python3
"""LLM relevance gate — score each source 0-100 on how directly it concerns
meaty PROCESS flavor, using Claude (Haiku, cheap). Stores `relevance_llm`.

This is the trust gate: it separates "keyword-matched" from "substantive".
After a full pass, re-run score_priority.py so priority_score blends it in (60/40).

Run:  python3 pipeline/score_relevance.py --limit 24        # validation
      python3 pipeline/score_relevance.py --limit 400       # a chunk
      python3 pipeline/score_relevance.py                   # all unscored
Only scores rows where relevance_llm IS NULL, so it resumes safely across runs.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db.connect import get_conn, _load_env
from psycopg2.extras import execute_values

MODEL = "claude-haiku-4-5-20251001"
BATCH = 12
SYSTEM = (
    "You curate a knowledge hub on MEATY PROCESS FLAVOR (how savory/meaty flavor and aroma "
    "arise from precursors + cooking chemistry: Maillard/Strecker reactions, lipid oxidation, "
    "thiamine/nucleotide degradation, volatiles, sensory of meat and meat-analog flavor, and "
    "the analytics/ingredients behind them). Score each paper 0-100 for how DIRECTLY it serves "
    "this scope: 90-100 core; 60-89 relevant; 30-59 tangential; 0-29 off-topic. "
    "Return ONLY a JSON array like [{\"id\":123,\"score\":88}] — no prose."
)


def score_batch(client, items):
    lines = [f'id={i} | {n} | {(a or "")[:500]}' for i, n, a in items]
    msg = client.messages.create(
        model=MODEL, max_tokens=800, system=SYSTEM,
        messages=[{"role": "user", "content": "Score these papers:\n\n" + "\n\n".join(lines)}],
    )
    text = msg.content[0].text.strip()
    text = text[text.find("["): text.rfind("]") + 1]
    return {int(d["id"]): max(0, min(100, int(d["score"]))) for d in json.loads(text)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="max rows to score (0 = all unscored)")
    args = ap.parse_args()

    _load_env()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY not set in meatCODE/.env")
    import anthropic
    client = anthropic.Anthropic()

    conn = get_conn(); cur = conn.cursor()
    lim = f"limit {args.limit}" if args.limit else ""
    cur.execute(f"select id, name, abstract from sources where relevance_llm is null "
                f"order by id {lim}")
    todo = cur.fetchall()
    if not todo:
        print("Nothing to score — all rows have relevance_llm."); return
    print(f"scoring {len(todo)} sources in batches of {BATCH} ({MODEL})...")

    done = 0
    for k in range(0, len(todo), BATCH):
        batch = todo[k:k + BATCH]
        try:
            scores = score_batch(client, batch)
        except Exception as e:
            print(f"  ! batch {k//BATCH} failed: {str(e)[:80]}"); continue
        pairs = [(i, s) for i, s in scores.items()]
        if pairs:
            execute_values(cur,
                "UPDATE sources s SET relevance_llm = v.sc::smallint "
                "FROM (VALUES %s) AS v(id, sc) WHERE s.id = v.id::bigint",
                pairs, template="(%s,%s)")
            conn.commit(); done += len(pairs)
        print(f"  batch {k//BATCH+1}: scored {len(pairs)} (total {done})")
    print(f"done. scored {done} sources. Re-run score_priority.py to blend into priority_score.")
    conn.close()


if __name__ == "__main__":
    main()
