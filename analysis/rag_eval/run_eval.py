#!/usr/bin/env python3
# Last updated: 2026-08-15 · Algorithm Expert · closed-corpus verify & score harness (answer + verifier
#   passes over the server's exact retrieval semantics). Writes results_<date>.json + results_<date>.md.
"""
MeatCODE RAG eval — closed-corpus VERIFY & SCORE harness.

What Lior asked for: "send a question → closed corpus → verify answers → criticize and
quality score". For each question in questions.json this script:

  (a) RETRIEVES with the SAME query semantics as server/meatcode_server.py's
      _retrieve_sources(): ts_rank_cd over sources.search_vec, citable filter
      (search_vec IS NOT NULL), on-topic gate (relevance_llm IS NULL OR >= 60),
      rank > 0, top-6, with the same OR-query recall fallback.
  (b) ANSWERS with the server's grounding prompt (same SYSTEM_PROMPT + ANSWERING RULES +
      numbered sources block, copied verbatim) — one Sonnet call, non-streaming.
  (c) VERIFIES with a second model call that receives ONLY the question, the retrieved
      sources (title + abstract + main_claim) and the answer, and scores:
        groundedness      0-10  every substantive claim traceable to a listed source
        citation_accuracy 0-10  the [id]s cited actually support the sentences they mark
        coverage          0-10  the answer uses what the sources offer and addresses the question
      plus a list of SPECIFIC criticisms (sentence + what's wrong with it).

Honesty notes baked into interpretation: the server's grounding prompt DELIBERATELY lets
the model answer uncovered parts from general knowledge, uncited (product decision
2026-07-20). The verifier will therefore legitimately dock groundedness on questions the
corpus covers thinly — that is the signal, not a bug in the harness.

Standalone by design (same rationale as analysis/oracle_eval/run_eval.py): importing the
server module would sys.exit without a key and drags in the HTTP handler. The retrieval
SQL + grounding prompt are DUPLICATED here — if they change in server/meatcode_server.py,
update the copies below (both files carry a pointer comment).

Usage:
    python3 analysis/rag_eval/run_eval.py                  # all 8 questions (~8 Sonnet answer + 8 verifier calls)
    python3 analysis/rag_eval/run_eval.py --only Q1,Q5     # subset
    python3 analysis/rag_eval/run_eval.py --dry-run        # retrieval only, no model calls, no files written
    # Chunked runs (for sandboxes with a per-command time cap): run subsets with --suffix,
    # then merge the partials into the canonical results_<date>.json/.md:
    python3 analysis/rag_eval/run_eval.py --only Q1,Q2 --suffix _p1
    python3 analysis/rag_eval/run_eval.py --merge          # merges results_<date>_p*.json → results_<date>.json/.md
Reads DATABASE_URL + ANTHROPIC_API_KEY from meatCODE/.env (never printed).
"""

import argparse, datetime, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))   # analysis/rag_eval -> analysis -> repo root


# ─── .env loader (same convention as the server) ─────────────────────────────
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
API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# ─── retrieval — KEEP IN SYNC with server/meatcode_server.py _retrieve_sources ───
ORACLE_TOP_K = 6
ORACLE_MIN_RELEVANCE = 60
ANSWER_MODEL = "claude-sonnet-4-6"      # same MODEL as the server
VERIFIER_MODEL = "claude-sonnet-4-6"    # judging citation support needs a strong reader
ANSWER_MAX_TOKENS = 1600                # same as server MAX_TOKENS
VERIFIER_MAX_TOKENS = 1200

RETRIEVAL_SQL = """
    SELECT * FROM (
        SELECT id, name AS title, year, COALESCE(journal, venue) AS journal, venue,
               doi, url, abstract, main_claim,
               ts_rank_cd(search_vec, websearch_to_tsquery('english', %s)) AS rank
        FROM sources
        WHERE search_vec IS NOT NULL
          AND (relevance_llm IS NULL OR relevance_llm >= %s)
    ) ranked
    WHERE rank > 0
    ORDER BY rank DESC
    LIMIT %s
"""


def pg_rows(sql, params=()):
    import psycopg2
    from psycopg2.extras import RealDictCursor
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def retrieve(question, limit=ORACLE_TOP_K):
    """(rows, used_fallback) — mirrors the server exactly, incl. the OR recall fallback."""
    rows = pg_rows(RETRIEVAL_SQL, (question, ORACLE_MIN_RELEVANCE, limit))
    if rows:
        return rows, False
    or_query = " OR ".join(question.split())
    if not or_query:
        return [], False
    return pg_rows(RETRIEVAL_SQL, (or_query, ORACLE_MIN_RELEVANCE, limit)), True


# ─── grounding prompt — copied from server/meatcode_server.py (keep in sync) ──
SYSTEM_PROMPT = (
    "You are MeatCODE Oracle — a flavor & aroma research assistant for "
    "GFI Israel. Answer concisely (3–5 short paragraphs max). Focus on "
    "meat-flavor chemistry: Maillard, sulfur volatiles, lipid oxidation, "
    "off-note masking, plant-protein flavor systems, cultivated meat, "
    "and the analytical techniques behind them (GC-MS, GC-O, SPME, etc.). "
    "Use plain prose paragraphs separated by blank lines. Cite compounds "
    "by name. After the main answer, add a final line starting with "
    "'Follow-ups:' followed by 2–3 short follow-up questions separated "
    "by ' · ' (a space, middle dot, space). Do not use markdown headers, "
    "bullets, or code blocks."
)


def format_sources_block(rows):
    if not rows:
        return ("SOURCES: (none listed for this question — answer from your own knowledge, "
                "uncited, and say nothing about sources or coverage)")
    parts = []
    for r in rows:
        meta = " · ".join(filter(None, [str(r["year"]) if r.get("year") else None, r.get("journal")]))
        snippet = (r.get("abstract") or "").strip()
        if len(snippet) > 500:
            snippet = snippet[:500].rsplit(" ", 1)[0] + "…"
        parts.append("[%s] %s%s\n%s" % (
            r["id"], r.get("title") or "(untitled)",
            (" (" + meta + ")") if meta else "",
            snippet or "(no abstract on file)"))
    return "SOURCES:\n\n" + "\n\n".join(parts)


def grounding_system_prompt(rows, used_fallback=False):
    fallback_note = (
        "\nSome listed sources were matched loosely, so term overlap does not "
        "guarantee relevance — read each abstract and only cite ones that actually "
        "address the question. Never mention this matching detail to the user.\n"
        if used_fallback else ""
    )
    return SYSTEM_PROMPT + (
        "\n\nANSWERING RULES (read carefully):\n"
        "Answer the question directly and usefully, in your normal voice.\n"
        "Numbered sources may be listed below. Where one genuinely supports a point "
        "you make, cite it inline using the exact bracket number shown immediately "
        "before that source (for example, if a source is labeled [123], write [123] "
        "in your answer — not [1]).\n"
        "NEVER invent a citation number, and NEVER attach a citation to a claim that "
        "the cited source does not actually support.\n"
        "Where the listed sources do not cover part of the question, simply answer "
        "that part from your own knowledge of flavour and aroma chemistry, leaving it "
        "uncited. Do not flag it, hedge it, or apologise for it.\n"
        "NEVER describe your own information sources or how you obtained anything. Do "
        "not mention the corpus, the database, retrieval, searching, what was or was "
        "not found, or whether something came from the listed sources versus your own "
        "knowledge. Never open with a caveat about coverage, and never say you cannot "
        "answer. Just give the answer." + fallback_note + "\n"
        + format_sources_block(rows)
    )


# ─── verifier pass ─────────────────────────────────────────────────────────────
VERIFIER_INSTRUCTIONS = """You are a strict scientific RAG auditor. You receive a question, a CLOSED set of numbered sources (the only material the answering system was given), and the answer it produced. Judge the answer against ONLY those sources — do not reward correct facts that the sources do not contain.

Score three dimensions, each an integer 0-10:

1. groundedness — what fraction of the answer's substantive scientific claims is traceable to the listed sources' titles/abstracts/claims? 10 = every claim traceable; 5 = roughly half; 0 = the sources played no real role. Uncited claims that do NOT appear in any source count against this score even if they are true chemistry.

2. citation_accuracy — for each inline [id] citation: does that specific source actually support the sentence(s) it is attached to? 10 = every citation checks out; deduct for citations to sources that are only tangentially related, and score 0 if any citation id does not exist in the source list.

3. coverage — how well does the answer use what the sources offer AND address the question asked? 10 = the relevant content of the sources is exploited and the question is fully addressed; low = the answer ignores relevant retrieved material or leaves the question substantially unanswered.

Then list criticisms: 2-6 SPECIFIC problems, each naming the exact sentence or citation at fault and what is wrong (unsupported claim, over-claimed citation, ignored source, off-topic source retrieved, vagueness, etc.). If retrieval clearly returned weak/irrelevant sources, say so — that is a retrieval criticism, not an answer criticism, but record it.

Respond with ONLY a JSON object:
{"groundedness": <0-10>, "citation_accuracy": <0-10>, "coverage": <0-10>,
 "citations_found": ["<id>", ...], "criticisms": ["...", "..."], "verdict": "<one-sentence overall judgement>"}"""


def verifier_prompt(question, rows, answer):
    src_parts = []
    for r in rows:
        claim = r.get("main_claim")
        if isinstance(claim, (list, tuple)):
            claim = " ".join(str(v) for v in claim if v)
        src_parts.append("[%s] %s (%s)\nABSTRACT: %s\nMAIN_CLAIM: %s" % (
            r["id"], r.get("title") or "(untitled)", r.get("year") or "n.d.",
            (r.get("abstract") or "(none)").strip()[:900],
            (str(claim).strip() if claim else "(none)")[:400]))
    return (
        "QUESTION:\n%s\n\nCLOSED SOURCE SET:\n\n%s\n\nANSWER UNDER AUDIT:\n%s"
        % (question, "\n\n".join(src_parts) or "(retrieval returned ZERO sources)", answer)
    )


def call_model(client, model, max_tokens, system, user):
    kwargs = dict(model=model, max_tokens=max_tokens,
                  messages=[{"role": "user", "content": user}])
    if system:
        kwargs["system"] = system
    resp = client.messages.create(**kwargs)
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


def parse_verifier_json(text):
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("verifier returned no JSON")
    data = json.loads(m.group(0))
    out = {}
    for k in ("groundedness", "citation_accuracy", "coverage"):
        v = data.get(k)
        out[k] = max(0, min(10, int(v))) if isinstance(v, (int, float)) else None
    out["criticisms"] = [str(c) for c in (data.get("criticisms") or [])][:8]
    out["verdict"] = str(data.get("verdict") or "")[:400]
    out["citations_found"] = [str(c) for c in (data.get("citations_found") or [])][:20]
    return out


# ─── main ──────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="MeatCODE closed-corpus RAG eval")
    ap.add_argument("--only", default="", help="comma-separated question ids, e.g. Q1,Q5")
    ap.add_argument("--dry-run", action="store_true", help="retrieval only — no model calls, no files")
    ap.add_argument("--suffix", default="", help="append to results filenames (chunked runs, e.g. _p1)")
    ap.add_argument("--merge", action="store_true",
                    help="merge today's results_<date>_p*.json partials into the final results files")
    args = ap.parse_args()

    if args.merge:
        import glob as _glob
        date = datetime.date.today().isoformat()
        merged, seen = [], set()
        for p in sorted(_glob.glob(os.path.join(HERE, "results_%s_p*.json" % date))):
            with open(p, encoding="utf-8") as f:
                for r in json.load(f)["results"]:
                    if r["id"] not in seen:
                        seen.add(r["id"])
                        merged.append(r)
        if not merged:
            sys.exit("ERROR: no results_%s_p*.json partials found to merge" % date)
        merged.sort(key=lambda r: r["id"])
        write_outputs(merged)
        return

    if not DATABASE_URL:
        sys.exit("ERROR: DATABASE_URL not set (checked %s/.env)" % REPO_ROOT)

    with open(os.path.join(HERE, "questions.json"), encoding="utf-8") as f:
        questions = json.load(f)["questions"]
    if args.only:
        keep = {t.strip().upper() for t in args.only.split(",") if t.strip()}
        questions = [q for q in questions if q["id"].upper() in keep]

    client = None
    if not args.dry_run:
        if not API_KEY:
            sys.exit("ERROR: ANTHROPIC_API_KEY not set (checked %s/.env)" % REPO_ROOT)
        import anthropic
        client = anthropic.Anthropic(api_key=API_KEY)

    results = []
    for q in questions:
        qid, question = q["id"], q["question"]
        print("=" * 78)
        print("%s [%s]: %s" % (qid, q.get("topic", ""), question))
        rows, used_fallback = retrieve(question)
        print("  retrieved %d sources%s: %s" % (
            len(rows), " (OR-fallback)" if used_fallback else "",
            ", ".join("[%s]" % r["id"] for r in rows)))
        rec = {
            "id": qid, "topic": q.get("topic"), "question": question,
            "retrieval": {
                "n_sources": len(rows), "used_fallback": used_fallback,
                "source_ids": [r["id"] for r in rows],
                "sources": [{"id": r["id"], "title": r.get("title"), "year": r.get("year"),
                             "rank": float(r["rank"]) if r.get("rank") is not None else None}
                            for r in rows],
            },
        }
        if args.dry_run:
            results.append(rec)
            continue

        # (b) ANSWER — same grounding prompt as the live server
        try:
            answer = call_model(client, ANSWER_MODEL, ANSWER_MAX_TOKENS,
                                grounding_system_prompt(rows, used_fallback), question)
        except Exception as e:
            rec["error"] = "answer call failed: %s" % str(e)[:300]
            results.append(rec)
            print("  ANSWER ERROR: %s" % rec["error"])
            continue
        rec["answer"] = answer
        cited = sorted(set(re.findall(r"\[(\d+)\]", answer)))
        rec["cited_ids"] = cited
        print("  answer: %d chars, cites %s" % (len(answer), cited or "nothing"))

        # (c) VERIFY — second model call, closed context only
        try:
            vtext = call_model(client, VERIFIER_MODEL, VERIFIER_MAX_TOKENS,
                               VERIFIER_INSTRUCTIONS, verifier_prompt(question, rows, answer))
            rec["verifier"] = parse_verifier_json(vtext)
        except Exception as e:
            rec["verifier"] = {"error": "verifier failed: %s" % str(e)[:300]}
        v = rec["verifier"]
        if "error" not in v:
            print("  scores: groundedness=%s citation_accuracy=%s coverage=%s"
                  % (v["groundedness"], v["citation_accuracy"], v["coverage"]))
        else:
            print("  VERIFIER ERROR: %s" % v["error"])
        results.append(rec)

    if args.dry_run:
        print("\n(dry run — no files written)")
        return
    write_outputs(results, suffix=args.suffix)


def write_outputs(results, suffix=""):
    """Write results_<date><suffix>.json (+ the .md scoreboard when suffix is empty,
    i.e. this is the final/merged output rather than a chunk partial)."""
    date = datetime.date.today().isoformat()
    scored = [r for r in results if isinstance(r.get("verifier"), dict) and "error" not in r["verifier"]
              and all(r["verifier"].get(k) is not None for k in ("groundedness", "citation_accuracy", "coverage"))]

    def avg(key):
        return round(sum(r["verifier"][key] for r in scored) / len(scored), 1) if scored else None

    summary = {
        "date": date,
        "n_questions": len(results),
        "n_scored": len(scored),
        "avg_groundedness": avg("groundedness"),
        "avg_citation_accuracy": avg("citation_accuracy"),
        "avg_coverage": avg("coverage"),
        "answer_model": ANSWER_MODEL, "verifier_model": VERIFIER_MODEL,
        "retrieval": "search_vec ts_rank_cd · relevance_llm>=%d gate · top-%d · OR fallback"
                     % (ORACLE_MIN_RELEVANCE, ORACLE_TOP_K),
    }
    jpath = os.path.join(HERE, "results_%s%s.json" % (date, suffix))
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "results": results}, f, ensure_ascii=False, indent=1, default=str)
    if suffix:
        print("Wrote partial %s (run --merge when all chunks are done)" % jpath)
        return

    lines = [
        "# RAG eval scoreboard — %s" % date, "",
        "_Last updated: %s · Algorithm Expert · closed-corpus verify & score run (analysis/rag_eval/run_eval.py)._" % date, "",
        "Answer model `%s` · verifier `%s` · retrieval: %s" % (ANSWER_MODEL, VERIFIER_MODEL, summary["retrieval"]), "",
        "| Q | topic | sources | fallback | cites | grounded /10 | cite-acc /10 | coverage /10 | verdict |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        v = r.get("verifier") or {}
        err = r.get("error") or v.get("error")
        lines.append("| %s | %s | %d | %s | %s | %s | %s | %s | %s |" % (
            r["id"], r.get("topic", ""), r["retrieval"]["n_sources"],
            "yes" if r["retrieval"]["used_fallback"] else "no",
            ",".join(r.get("cited_ids", [])) or "—",
            v.get("groundedness", "—"), v.get("citation_accuracy", "—"), v.get("coverage", "—"),
            (err or v.get("verdict", ""))[:160].replace("|", "/"),
        ))
    lines += ["",
              "**Averages (%d/%d scored):** groundedness **%s** · citation accuracy **%s** · coverage **%s**"
              % (len(scored), len(results), summary["avg_groundedness"],
                 summary["avg_citation_accuracy"], summary["avg_coverage"]),
              "", "## Criticisms per question", ""]
    for r in results:
        v = r.get("verifier") or {}
        lines.append("### %s — %s" % (r["id"], r["question"]))
        for c in v.get("criticisms", []):
            lines.append("- %s" % c)
        if not v.get("criticisms"):
            lines.append("- _(none recorded)_")
        lines.append("")
    mpath = os.path.join(HERE, "results_%s.md" % date)
    with open(mpath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print("=" * 78)
    print("Wrote %s and %s" % (jpath, mpath))
    print("AVG: groundedness=%s citation_accuracy=%s coverage=%s (%d/%d scored)"
          % (summary["avg_groundedness"], summary["avg_citation_accuracy"],
             summary["avg_coverage"], len(scored), len(results)))


if __name__ == "__main__":
    main()
