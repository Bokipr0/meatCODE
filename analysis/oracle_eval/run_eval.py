#!/usr/bin/env python3
# Last updated: 2026-07-08 10:20 UTC · Algorithm Expert · initial retrieval-only eval harness for
#   the Oracle's grounded RAG (server/meatcode_server.py's _retrieve_sources). Standalone by design
#   (see "Why standalone" below). See docs/ORACLE_GROUNDED_RETRIEVAL.md for full context.
"""
Oracle RETRIEVAL sanity check.

Runs ONLY the retrieval SQL used by server/meatcode_server.py's `_retrieve_sources()`
for each question in eval_questions.md, against live Neon, and prints/saves the
top-K source titles so a human can eyeball whether retrieval looks relevant BEFORE
trusting the Oracle's grounded answers. Deliberately does NOT call the Anthropic
API — this checks the "find the right passages" half of the pipeline in isolation
(docs/DECISION_Oracle_Answer_Engine.docx's step 2), which is where retrieval quality
problems actually live; the "write the answer" half (step 4) is a separate concern.

Why standalone (duplicates the SQL instead of importing the server module)
----------------------------------------------------------------------------
server/meatcode_server.py does real work at import time — it loads .env, requires
ANTHROPIC_API_KEY, and hard `sys.exit(1)`s if missing, then constructs an Anthropic
client. Importing it here would make a pure DB sanity check depend on the Anthropic
SDK being installed and a key being present, for zero benefit. So this script
duplicates the retrieval SQL as a small, self-contained block. IMPORTANT: if
_RETRIEVAL_SQL / ORACLE_TOP_K / ORACLE_MIN_RELEVANCE change in
server/meatcode_server.py, update the copies below to match (both files carry a
comment pointing at the other).

Usage
-----
    python3 analysis/oracle_eval/run_eval.py
    python3 analysis/oracle_eval/run_eval.py --save results.md
    python3 analysis/oracle_eval/run_eval.py --questions my_questions.md --limit 6
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))  # analysis/oracle_eval -> analysis -> repo root


# ─── tiny .env loader (same convention as server/meatcode_server.py) ──────────
def load_dotenv(path):
    if not path or not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip().strip('"').strip("'")


load_dotenv(os.path.join(REPO_ROOT, ".env"))
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    sys.stderr.write("ERROR: DATABASE_URL not set (checked %s/.env)\n" % REPO_ROOT)
    sys.exit(1)

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    sys.stderr.write(
        "ERROR: psycopg2 not installed.\n"
        "  Run:  pip install psycopg2-binary --break-system-packages\n"
    )
    sys.exit(1)


# ─── retrieval (kept in sync with server/meatcode_server.py's _retrieve_sources) ──
# Two-tier: strict AND-match first (websearch_to_tsquery on the question as typed,
# precise); if that returns nothing, retry once with the same words OR'd together
# (recall fallback -- websearch_to_tsquery ANDs bare words, so ts_rank_cd is
# provably 0 for any source missing even one query term; see
# docs/ORACLE_GROUNDED_RETRIEVAL.md for the empirical case for this).
ORACLE_TOP_K = 6
ORACLE_MIN_RELEVANCE = 60  # relevance_llm gate; sources scored below this are off-topic

RETRIEVAL_SQL = """
    SELECT * FROM (
        SELECT id, name AS title, year, COALESCE(journal, venue) AS journal, venue,
               doi, citation_count,
               ts_rank_cd(search_vec, websearch_to_tsquery('english', %s)) AS rank
        FROM sources
        WHERE search_vec IS NOT NULL
          AND (relevance_llm IS NULL OR relevance_llm >= %s)
    ) ranked
    WHERE rank > 0
    ORDER BY rank DESC
    LIMIT %s
"""


def _run(query_text, limit):
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(RETRIEVAL_SQL, (query_text, ORACLE_MIN_RELEVANCE, limit))
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def retrieve(question, limit=ORACLE_TOP_K):
    """Returns (rows, used_fallback) -- mirrors server/meatcode_server.py's
    _retrieve_sources() exactly, including the OR-query recall fallback."""
    rows = _run(question, limit)
    if rows:
        return rows, False
    or_query = " OR ".join(question.split())
    if not or_query:
        return [], False
    return _run(or_query, limit), True


def load_questions(path):
    """Parse one question per numbered ('1.', '1)') or bulleted ('-', '*') line."""
    questions = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        m = re.match(r"^(?:\d+[.)]|[-*])\s+(\S.*)$", line)
        if m:
            questions.append(m.group(1).strip())
    return questions


def format_row(r):
    meta_bits = []
    if r.get("year"):
        meta_bits.append(str(r["year"]))
    if r.get("journal"):
        meta_bits.append(r["journal"])
    if r.get("citation_count") is not None:
        meta_bits.append("%d citations" % r["citation_count"])
    meta = ", ".join(meta_bits)
    rank = r.get("rank") or 0
    return "[%s] rank=%.4f  %s%s" % (
        r["id"], rank, r.get("title") or "(untitled)",
        (" (" + meta + ")") if meta else "",
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--questions", default=os.path.join(HERE, "eval_questions.md"),
                     help="markdown file with one question per numbered/bulleted line")
    ap.add_argument("--save", default=None,
                     help="also write results as markdown to this path (relative to CWD)")
    ap.add_argument("--limit", type=int, default=ORACLE_TOP_K, help="top-K per question")
    args = ap.parse_args()

    questions = load_questions(args.questions)
    if not questions:
        sys.stderr.write("No questions parsed from %s\n" % args.questions)
        sys.exit(1)

    zero_hit = 0
    fallback_used = 0
    out_lines = [
        "# Oracle retrieval eval — results",
        "",
        "_Retrieval-only sanity check: runs the exact two-tier ts_rank_cd/search_vec ranking logic "
        "from server/meatcode_server.py's `_retrieve_sources()` against live Neon for each question "
        "in eval_questions.md. Does NOT call the Anthropic API — this checks retrieval quality alone._",
        "",
        "Filter: `search_vec IS NOT NULL AND (relevance_llm IS NULL OR relevance_llm >= %d) AND rank > 0`, "
        "`ORDER BY ts_rank_cd(search_vec, websearch_to_tsquery('english', query)) DESC LIMIT %d`. Tier 1 "
        "runs `query = question` (strict AND); if that returns 0 rows, tier 2 (\"OR-fallback\" below) "
        "retries with `query = question's words joined by \" OR \"` (recall fallback)."
        % (ORACLE_MIN_RELEVANCE, args.limit),
        "",
    ]

    for i, q in enumerate(questions, 1):
        print("=" * 78)
        print("Q%d: %s" % (i, q))
        out_lines.append("## Q%d: %s" % (i, q))
        try:
            rows, used_fallback = retrieve(q, args.limit)
        except Exception as e:
            print("  ERROR: %s" % e)
            out_lines.append("- ERROR: %s" % e)
            out_lines.append("")
            continue
        if used_fallback:
            fallback_used += 1
            print("  (tier 1 strict match returned 0 rows -- showing tier 2 OR-fallback)")
            out_lines.append("- _tier 1 strict match returned 0 rows — showing tier 2 OR-fallback:_")
        if not rows:
            zero_hit += 1
            print("  (0 sources retrieved even after OR-fallback — corpus doesn't cover this)")
            out_lines.append("- **0 sources retrieved even after OR-fallback** — corpus doesn't cover this.")
        for r in rows:
            line = format_row(r)
            print("  " + line)
            out_lines.append("- " + line)
        out_lines.append("")

    summary = (
        "%d/%d questions returned 0 sources. %d/%d needed the tier-2 OR-fallback "
        "(tier-1 strict AND-match alone returned 0 rows for them)."
        % (zero_hit, len(questions), fallback_used, len(questions))
    )
    print("=" * 78)
    print(summary)
    out_lines.insert(5, "**Summary:** " + summary)
    out_lines.insert(6, "")

    if args.save:
        with open(args.save, "w", encoding="utf-8") as f:
            f.write("\n".join(out_lines) + "\n")
        print("\nSaved to %s" % args.save)


if __name__ == "__main__":
    main()
