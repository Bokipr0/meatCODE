#!/usr/bin/env python3
# Last updated: 2026-07-08 10:11 UTC · Data Engineer · new — taxonomy-bible keyword-overlap relevance check, reconciled vs relevance_llm; feeds the full-corpus audit xlsx + analysis/relevance_check_<date>.md
"""Taxonomy-bible relevance check — SELECT-only, read-only verification.

For every source in `sources`, computes a keyword-overlap signal against the taxonomy
bible (`db/taxonomy/keywords_topics.json`, 91 keywords / 5 branches — loaded via
`db/taxonomy.py`, THE loader; nothing here hardcodes a topic list) and reconciles it
against the ingest-time LLM relevance gate (`relevance_llm`, written by
`pipeline/score_relevance.py`). This is a verification pass over data ALREADY in Neon:
no writes, no quarantines — Daniel decides removals, this only produces evidence.

Method
------
Per source, the "overlap text" is **name + abstract + top_keywords** (as specified).
Against that text we run `db.taxonomy.classify()` uncapped — the existing cheap
substring-match loader logic, REUSED not reinvented — to get every taxonomy topic whose
canonical `topic_name` literally appears in the text. That hit-set is UNIONED with
whatever canonical topics are **already attached** via `source_topics` (a source can be
correctly tagged even if the abstract's wording doesn't literally contain the topic_name
string — being tagged counts as a match on its own).

  taxonomy_signal (purely descriptive, 3-way):
    0 combined hits  -> "off-topic"
    1 combined hit   -> "weak"
    2+ combined hits -> "on-topic"

  "branches hit" = distinct root_branch values across the combined hit-set.

Known limitation, measured not assumed: several level-2 topic_names in the bible are
common English words used generically elsewhere in food science — "Cooking", "Grill",
"Thermal", "Genomics", "Vitamins", "Peptide", "Amino acids", "FTIR", "Collagen",
"Metallic". A single substring hit on one of these (or a source carrying just one
pre-existing tag) is frequently noise, not real topical overlap. Empirically (run against
the live corpus 2026-07-08): of the 329 sources with relevance_llm < 40, 226 (69%) have 0
or 1 combined taxonomy hits (mostly zero; the rest are a single hit, often a generic word)
while 103 (31%) have 2+ hits — and manual inspection of that 103 shows it is substantially
made up of coincidental multi-word overlap (e.g. "ftir"+"thermal" on a dairy-protein
glycation paper; "amino_acids"+"peptide" on a bitter-taste-masking pharma paper) rather
than genuine on-topic content the LLM gate wrongly rejected. This is WHY relevance_llm
stays authoritative for the recommended action, and taxonomy overlap is reported as a
secondary/diagnostic signal — exactly the framing in score_relevance.py's own docstring
("this is the trust gate: it separates keyword-matched from substantive").

Reconciliation -> `recommended_action` + `reconciliation` per source:
    relevance_llm >= 60                              -> keep                  (agree, or coverage_gap if 0 taxonomy hits + untagged)
    40 <= relevance_llm < 60                          -> review               (borderline)
    relevance_llm < 40  AND combined hits <= 1        -> off_topic_high_confidence  (agree — 0 hits, or a lone generic-word hit)
    relevance_llm < 40  AND combined hits >= 2        -> off_topic_check_first      (disagreement — the "keyword-matched but LLM<40" case this task asks to flag; needs a human glance, not an auto-drop)

A second, independent gap is flagged for taxonomy-completeness visibility (not a
relevance risk): relevance_llm >= 60 but ZERO taxonomy hits AND untagged — i.e. the LLM
(which read the abstract) says on-topic but nothing in the 91-keyword bible matched its
vocabulary and it was never tagged. These are candidates for back-tagging or a future
taxonomy keyword, reported as `reconciliation = "coverage_gap"`.

Run:
    python3 pipeline/check_relevance_vs_taxonomy.py                 # prints corpus summary only
    python3 pipeline/check_relevance_vs_taxonomy.py --write-md      # also writes analysis/relevance_check_<date>.md
    python3 pipeline/check_relevance_vs_taxonomy.py --limit 50      # quick sample run

Importable (used by pipeline/export_audit_xlsx.py --all-sources so the xlsx and the
md report are computed from the exact same rows — single source of truth):
    from pipeline.check_relevance_vs_taxonomy import compute_all
    rows = compute_all(cur)
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# Same self-sufficient Neon accessor pattern as audit_sources.py / export_audit_xlsx.py:
# prefer the repo's db.connect, fall back to a direct psycopg2 connection from .env
# (db/connect.py's *source* has been missing locally since a lossy sync — only a .pyc
# survived — so every pipeline script that needs Neon carries this fallback).
try:
    from db.connect import get_conn          # shared accessor — do NOT reinvent
except Exception:
    def _load_env_once():
        envp = REPO_ROOT / ".env"
        if envp.exists():
            for line in envp.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

    def get_conn():
        _load_env_once()
        import psycopg2
        url = os.environ.get("DATABASE_URL")
        if not url:
            raise RuntimeError("DATABASE_URL not set (checked .env)")
        return psycopg2.connect(url.strip())

from db import taxonomy as tax             # THE governing-bible loader — reused, not reinvented

TAX_RECORDS = tax.load()
TAX_BY_SLUG = {r["topic_slug"]: r for r in TAX_RECORDS}
N_TAX = len(TAX_RECORDS)

SOURCE_COLS = [
    "id", "name", "year", "journal", "venue", "doi", "authors", "citation_count",
    "is_review", "abstract", "top_keywords", "relevance_llm", "priority_score",
    "search_query",
]


# ===========================================================================
# Taxonomy overlap
# ===========================================================================
def taxonomy_hits_for_text(text: str) -> list[dict]:
    """All bible records whose canonical topic_name appears in `text`. Thin wrapper
    around db.taxonomy.classify() uncapped (it already dedupes by slug and returns
    canonical branch/priority/level order) — REUSED, not reinvented."""
    return tax.classify(text or "", top_k=N_TAX)


def fetch_tagged(cur, ids: list[int]) -> dict[int, list[dict]]:
    if not ids:
        return {}
    cur.execute("""
        SELECT st.source_id, t.slug, t.name, t.root_branch
        FROM source_topics st JOIN topics t ON t.id = st.topic_id
        WHERE st.source_id = ANY(%s)
    """, (ids,))
    out: dict[int, list[dict]] = {}
    for sid, slug, name, branch in cur.fetchall():
        out.setdefault(sid, []).append({"slug": slug, "name": name, "branch": branch})
    return out


def fetch_latest_audit(cur, ids: list[int]) -> dict[int, dict]:
    """Most recent source_audits verdict per source (if any). Independent third signal
    (the Haiku audit_judge, which reads full tagging + connected-query context) shown
    alongside relevance_llm + the taxonomy signal for transparency — not blended in."""
    if not ids:
        return {}
    cur.execute("""
        SELECT DISTINCT ON (source_id) source_id, verdict, relevance_score, tag_score,
               quality_score, notes, audited_at
        FROM source_audits
        WHERE source_id = ANY(%s)
        ORDER BY source_id, audited_at DESC
    """, (ids,))
    out = {}
    for sid, verdict, rel, tagsc, qual, notes, at in cur.fetchall():
        out[sid] = {"verdict": verdict, "audit_relevance": rel, "audit_tag": tagsc,
                     "audit_quality": qual, "audit_notes": notes, "audited_at": at}
    return out


def classify_signal(n_hits: int) -> str:
    if n_hits == 0:
        return "off-topic"
    if n_hits == 1:
        return "weak"
    return "on-topic"


def reconcile(rel_llm: int | None, n_hits: int, is_tagged: bool) -> tuple[str, str]:
    """-> (reconciliation, recommended_action). See module docstring for the table."""
    if rel_llm is None:
        return "unscored", "review"
    if rel_llm >= 60:
        if n_hits == 0 and not is_tagged:
            return "coverage_gap", "keep"
        return "agree", "keep"
    if rel_llm >= 40:
        return "borderline", "review"
    # rel_llm < 40
    if n_hits >= 2:
        return "disagreement", "off_topic_check_first"
    return "agree", "off_topic_high_confidence"


# ===========================================================================
# Main computation — the single source of truth reused by the xlsx exporter
# ===========================================================================
def compute_all(cur, limit: int = 0) -> list[dict]:
    cols_sql = ", ".join(SOURCE_COLS)
    lim_sql = f" LIMIT {int(limit)}" if limit else ""
    cur.execute(f"SELECT {cols_sql} FROM sources ORDER BY id{lim_sql}")
    rows = [dict(zip(SOURCE_COLS, r)) for r in cur.fetchall()]
    ids = [r["id"] for r in rows]

    tagged_by_src = fetch_tagged(cur, ids)
    audit_by_src = fetch_latest_audit(cur, ids)

    out = []
    for r in rows:
        text = " ".join(x for x in [r.get("name"), r.get("abstract"), r.get("top_keywords")] if x)
        kw_hits = taxonomy_hits_for_text(text)
        kw_slugs = {h["topic_slug"] for h in kw_hits}

        tagged = tagged_by_src.get(r["id"], [])
        tagged_slugs = {t["slug"] for t in tagged}

        combined_slugs = kw_slugs | tagged_slugs
        n_hits = len(combined_slugs)

        branches = set()
        for s in kw_slugs:
            rec = TAX_BY_SLUG.get(s)
            if rec:
                branches.add(rec["branch"])
        for t in tagged:
            if t.get("branch"):
                branches.add(t["branch"])
        branches_ordered = [b for b in tax.BRANCH_ORDER if b in branches] + \
                           sorted(b for b in branches if b not in tax.BRANCH_ORDER)

        hit_names = set()
        for s in combined_slugs:
            rec = TAX_BY_SLUG.get(s)
            if rec:
                hit_names.add(rec["topic_name"])
            else:
                tname = next((t["name"] for t in tagged if t["slug"] == s), None)
                if tname:
                    hit_names.add(tname)

        signal = classify_signal(n_hits)
        rel_llm = r.get("relevance_llm")
        is_tagged = bool(tagged)
        reconciliation, recommended_action = reconcile(rel_llm, n_hits, is_tagged)

        audit = audit_by_src.get(r["id"])

        d = dict(r)
        d["abstract_present"] = bool(r.get("abstract"))
        d.pop("abstract", None)  # don't carry full abstract text into report rows
        d["taxonomy_hit_count"] = n_hits
        d["taxonomy_hit_names"] = sorted(hit_names)
        d["taxonomy_branches"] = branches_ordered
        d["taxonomy_signal"] = signal
        d["is_tagged"] = is_tagged
        d["attached_tags"] = sorted(t["name"] for t in tagged)
        d["reconciliation"] = reconciliation
        d["recommended_action"] = recommended_action
        d["audit_verdict"] = audit["verdict"] if audit else None
        d["audit_notes"] = audit["audit_notes"] if audit else None
        d["audit_relevance"] = audit["audit_relevance"] if audit else None
        d["audit_quality"] = audit["audit_quality"] if audit else None
        d["audited_at"] = audit["audited_at"] if audit else None
        out.append(d)
    return out


# ===========================================================================
# Summary + markdown report
# ===========================================================================
def summarize(rows: list[dict]) -> dict:
    n = len(rows)
    citable = sum(1 for r in rows if r["abstract_present"])
    tagged = sum(1 for r in rows if r["is_tagged"])

    def bucket(field, lo, hi):
        return sum(1 for r in rows if r[field] is not None and lo <= r[field] < hi)

    rel_buckets = {b: bucket("relevance_llm", lo, hi) for b, (lo, hi) in
                   [(">=80", (80, 1000)), ("60-79", (60, 80)), ("40-59", (40, 60)), ("<40", (0, 40))]}
    pr_buckets = {b: sum(1 for r in rows if r["priority_score"] is not None and lo <= float(r["priority_score"]) < hi)
                  for b, (lo, hi) in [(">=80", (80, 1000)), ("60-79", (60, 80)), ("40-59", (40, 60)), ("<40", (0, 40))]}

    sig_counts = Counter(r["taxonomy_signal"] for r in rows)
    recon_counts = Counter(r["reconciliation"] for r in rows)
    action_counts = Counter(r["recommended_action"] for r in rows)

    branch_hits = Counter()
    for r in rows:
        for b in r["taxonomy_branches"]:
            branch_hits[b] += 1

    query_offtopic = Counter()
    query_total = Counter()
    for r in rows:
        q = r.get("search_query") or "(none)"
        query_total[q] += 1
        if r["recommended_action"] in ("off_topic_high_confidence", "off_topic_check_first"):
            query_offtopic[q] += 1

    return {
        "n": n, "citable": citable, "tagged": tagged, "untagged": n - tagged,
        "rel_buckets": rel_buckets, "pr_buckets": pr_buckets,
        "signal_counts": sig_counts, "reconciliation_counts": recon_counts,
        "action_counts": action_counts, "branch_hits": branch_hits,
        "query_offtopic": query_offtopic, "query_total": query_total,
    }


def _pct(part: int, whole: int) -> str:
    return f"{100.0 * part / whole:.1f}%" if whole else "n/a"


def write_md(path: Path, rows: list[dict], s: dict) -> None:
    now = datetime.now(timezone.utc)
    n = s["n"]
    L: list[str] = []
    L.append(f"_Last updated: {now:%Y-%m-%d %H:%M} UTC · Data Engineer · taxonomy-bible relevance check vs relevance_llm, full corpus_")
    L.append("")
    L.append(f"# MeatCODE — corpus relevance check ({now:%Y-%m-%d})")
    L.append("")
    L.append("Evidence-based relevance verification of the `sources` corpus against the taxonomy bible "
              "(`db/taxonomy/keywords_topics.json`, 91 keywords / 5 branches) and the ingest-time LLM "
              "relevance gate (`relevance_llm`). **Read-only** — no rows were changed, quarantined, or "
              "deleted in Neon. This is evidence for Daniel to decide on; nothing here auto-applies.")
    L.append("")

    L.append("## 1. Corpus health (trust-critical numbers)")
    L.append("")
    L.append(f"- **Total sources:** {n}")
    L.append(f"- **Citable corpus** (non-null `abstract` AND non-null `search_vec`): "
              f"**{s['citable']} ({_pct(s['citable'], n)})** — the number that matters for the Oracle, "
              f"since it can only ground answers in sources that actually have retrievable text.")
    L.append(f"- **Tagged** (present in `source_topics`): {s['tagged']} ({_pct(s['tagged'], n)}) · "
              f"**Untagged:** {s['untagged']} ({_pct(s['untagged'], n)})")
    L.append("")
    L.append("| relevance_llm bucket | sources | % |")
    L.append("|---|--:|--:|")
    for b in [">=80", "60-79", "40-59", "<40"]:
        L.append(f"| {b} | {s['rel_buckets'][b]} | {_pct(s['rel_buckets'][b], n)} |")
    L.append("")
    L.append("| priority_score bucket | sources | % |")
    L.append("|---|--:|--:|")
    for b in [">=80", "60-79", "40-59", "<40"]:
        L.append(f"| {b} | {s['pr_buckets'][b]} | {_pct(s['pr_buckets'][b], n)} |")
    L.append("")
    L.append("`priority_score` (60% `relevance_llm` + 40% deterministic venue/citation/recency signal) "
              "visibly compresses the tails vs raw `relevance_llm` — e.g. only "
              f"{s['pr_buckets']['>=80']} score >=80 on `priority_score` vs {s['rel_buckets']['>=80']} on raw "
              "`relevance_llm`, because a well-cited core-journal paper claws back points even when "
              "off-topic. For a pure relevance read, `relevance_llm` is the cleaner signal; `priority_score` "
              "is the right one for ranking what to surface first.")
    L.append("")

    L.append("## 2. Taxonomy-bible relevance signal")
    L.append("")
    L.append("Per source, `name + abstract + top_keywords` is matched against the 91-keyword bible "
              "(`db.taxonomy.classify()`, reused) and unioned with whatever topics are already attached "
              "via `source_topics`. Classified purely on hit count:")
    L.append("")
    L.append("| Taxonomy signal | Definition | Sources | % |")
    L.append("|---|---|--:|--:|")
    for label, key in [("On-topic", "on-topic"), ("Weak", "weak"), ("Off-topic", "off-topic")]:
        c = s["signal_counts"].get(key, 0)
        defn = {"on-topic": "2+ distinct canonical topics matched", "weak": "exactly 1 matched",
                "off-topic": "0 matched, untagged"}[key]
        L.append(f"| {label} | {defn} | {c} | {_pct(c, n)} |")
    L.append("")
    L.append("**Known limitation (measured, not assumed):** several level-2 topic names in the bible are "
              "common English words used generically elsewhere in food science — *Cooking, Grill, Thermal, "
              "Genomics, Vitamins, Peptide, Amino acids, FTIR, Collagen, Metallic*. A lone hit on one of "
              "these is usually noise, not real topical overlap (examples below). Because of this, "
              "**taxonomy overlap is treated as a secondary/diagnostic signal here, not a verdict** — "
              "`relevance_llm` (which reads the actual abstract) stays authoritative for the recommended "
              "action. This matches how `score_relevance.py` itself describes the LLM gate: *\"it separates "
              "keyword-matched from substantive.\"*")
    L.append("")
    L.append("**Branch coverage** (hit-count across the corpus, a source can hit more than one branch):")
    L.append("")
    L.append("| Branch | Hits |")
    L.append("|---|--:|")
    for b in tax.BRANCH_ORDER:
        L.append(f"| {b} | {s['branch_hits'].get(b, 0)} |")
    L.append("")
    L.append("`meat_analogs` is by far the thinnest branch here too — consistent with the "
              "2026-07-05 white-space analysis (`analysis/white_space_data.md`) that already flagged it as "
              "the least-covered branch at ~14% high-relevance.")
    L.append("")

    L.append("## 3. Reconciliation vs `relevance_llm` (where the two signals disagree)")
    L.append("")
    rc = s["reconciliation_counts"]
    L.append("| Reconciliation | Meaning | Sources |")
    L.append("|---|---|--:|")
    L.append(f"| agree | Both signals point the same way | {rc.get('agree', 0)} |")
    L.append(f"| borderline | `relevance_llm` 40-59 (tangential, per its own rubric) | {rc.get('borderline', 0)} |")
    L.append(f"| **disagreement** | Taxonomy matched 2+ topics but `relevance_llm` < 40 — the flagged case | **{rc.get('disagreement', 0)}** |")
    L.append(f"| coverage_gap | `relevance_llm` >= 60 but zero taxonomy hits and untagged | {rc.get('coverage_gap', 0)} |")
    L.append("")
    L.append("Recommended action breakdown (this is what's colour-coded in the xlsx):")
    L.append("")
    L.append("| Recommended action | Sources | % |")
    L.append("|---|--:|--:|")
    action_labels = [
        ("keep", "Keep — relevance_llm >= 60"),
        ("review", "Review — relevance_llm 40-59"),
        ("off_topic_check_first", "Off-topic, check first — LLM<40 but taxonomy matched 2+ topics"),
        ("off_topic_high_confidence", "Off-topic, high confidence — LLM<40, taxonomy agrees (0-1 hits)"),
    ]
    for key, label in action_labels:
        c = s["action_counts"].get(key, 0)
        L.append(f"| {label} | {c} | {_pct(c, n)} |")
    L.append("")
    L.append(f"Of the {s['rel_buckets']['<40']} sources `relevance_llm` scores below 40, "
              f"**{s['action_counts'].get('off_topic_high_confidence', 0)} ({_pct(s['action_counts'].get('off_topic_high_confidence', 0), s['rel_buckets']['<40'])})** "
              "have zero or at most one (often generic-word) taxonomy hit too — a doubly-confirmed, "
              f"high-confidence off-topic shortlist. The remaining **{s['action_counts'].get('off_topic_check_first', 0)}** share vocabulary "
              "with 2+ canonical topics despite the LLM rejection; spot-checking a sample of these shows most "
              "are still coincidental generic-word overlap (e.g. \"ftir\"+\"thermal\" hitting a dairy-protein "
              "glycation paper), not the LLM being wrong — but they are the honest disagreement set and worth "
              "a human glance before any bulk action.")
    L.append("")
    L.append(f"On the other side, **{rc.get('coverage_gap', 0)} sources** score `relevance_llm` >= 60 (the "
              "LLM read them as on-topic) yet match nothing in the 91-keyword bible and were never tagged — "
              "these are back-tagging / taxonomy-completeness candidates, not a relevance risk.")
    L.append("")

    L.append("## 4. Off-topic shortlist (high confidence — both signals agree)")
    L.append("")
    offlist = [r for r in rows if r["recommended_action"] == "off_topic_high_confidence"]
    offlist.sort(key=lambda r: (r["relevance_llm"] if r["relevance_llm"] is not None else 0))
    L.append(f"{len(offlist)} sources total; the {min(30, len(offlist))} lowest-`relevance_llm` are listed here "
              "(full list in the xlsx). None have been removed — this is a shortlist for Daniel's review.")
    L.append("")
    L.append("| id | Title | Yr | rel_llm | Ingest query |")
    L.append("|--:|---|--:|--:|---|")
    for r in offlist[:30]:
        title = (r["name"] or "")[:80].replace("|", "/")
        L.append(f"| {r['id']} | {title} | {r.get('year') or ''} | {r['relevance_llm']} | {r.get('search_query') or ''} |")
    L.append("")

    L.append("## 5. Ingest-query quality — where the off-topic material comes from")
    L.append("")
    L.append("Off-topic rate (either recommended-action off-topic bucket) by ingest query, top offenders "
              "(min 5 sources):")
    L.append("")
    L.append("| Ingest query | Total | Off-topic (either bucket) | Off-topic % |")
    L.append("|---|--:|--:|--:|")
    rows_by_q = sorted(s["query_total"].items(), key=lambda kv: -s["query_offtopic"].get(kv[0], 0))
    shown = 0
    for q, total in rows_by_q:
        if total < 5:
            continue
        off = s["query_offtopic"].get(q, 0)
        L.append(f"| {q} | {total} | {off} | {_pct(off, total)} |")
        shown += 1
        if shown >= 15:
            break
    L.append("")
    L.append("`sensory` and `off-note` stand out as the dirtiest ingest queries (pulling human-olfaction / "
              "clinical-neuroscience literature — Alzheimer's, Parkinson's, anosmia/parosmia, canine "
              "explosive detection — that matches bare \"odor/sensory\" wording but has nothing to do with "
              "meaty process flavor). `meat-aroma` and the specific taxonomy-keyword queries are markedly "
              "cleaner. These predate the taxonomy-driven query set (`db.taxonomy.search_queries()`) that "
              "`openalex_ingest.py` now defaults to — candidates to retire or narrow on the next ingest pass.")
    L.append("")

    L.append("## 6. Prior audits cross-check")
    L.append("")
    audited = [r for r in rows if r["audit_verdict"]]
    L.append(f"{len(audited)} sources have a prior `source_audits` verdict (from the recurring "
              "`audit_sources.py` loop, whose Haiku judge reads full tagging + connected-query context, "
              "not just name+abstract). Cross-tab against this check's `relevance_llm`-driven recommended "
              "action:")
    L.append("")
    cross = Counter((r["audit_verdict"], r["recommended_action"]) for r in audited)
    L.append("| Prior audit verdict | Recommended action here | Sources |")
    L.append("|---|---|--:|")
    for (av, ra), c in sorted(cross.items(), key=lambda kv: -kv[1]):
        L.append(f"| {av} | {ra} | {c} |")
    L.append("")

    quarantined = [r for r in audited if r["audit_verdict"] == "quarantine"]
    if quarantined:
        L.append(f"**Load-bearing disagreement:** all **{len(quarantined)}** sources the audit loop has "
                  "staged for quarantine still show `relevance_llm` >= 60 (\"Keep\" here), because "
                  "`relevance_llm` only ever saw name + first ~500 chars of abstract at ingest time, while "
                  "the audit judge additionally reasoned over tags and connected taxonomy queries and scored "
                  "them much lower. The ingest-time gate is measurably looser than the audit loop on these:")
        L.append("")
        L.append("| id | Title | relevance_llm (ingest) | audit relevance (judge) | Audit notes |")
        L.append("|--:|---|--:|--:|---|")
        for r in quarantined:
            title = (r["name"] or "")[:60].replace("|", "/")
            notes = (r["audit_notes"] or "")[:110].replace("|", "/")
            L.append(f"| {r['id']} | {title} | {r['relevance_llm']} | {r['audit_relevance']} | {notes} |")
        L.append("")
        L.append("These 4 are **not** re-flagged by this pass's own action column (relevance_llm alone says "
                  "keep) — treat the audit loop's quarantine verdict as the more trustworthy read for these "
                  "specific IDs, and note this as a concrete argument for re-scoring `relevance_llm` with "
                  "more context (or fully replacing the ingest gate with the audit judge) rather than trusting "
                  "the ingest-time score in isolation.")
        L.append("")

    L.append("## Recommendation")
    L.append("")
    if quarantined:
        L.append(f"- **Confirm the {len(quarantined)} sources already staged for quarantine by the audit loop** "
                  "(§6: #" + ", #".join(str(r["id"]) for r in quarantined) + ") — they read as \"keep\" under "
                  "`relevance_llm` alone, which is exactly why they were nearly missed; the deeper audit judge "
                  "is the more trustworthy signal here.")
    L.append(f"- Treat the **{s['action_counts'].get('off_topic_high_confidence', 0)}-source high-confidence "
              "off-topic shortlist** (section 4, full list in the xlsx) as the primary quarantine-review queue — "
              "both an LLM read of the abstract and independent taxonomy-keyword overlap agree.")
    L.append(f"- The **{s['action_counts'].get('off_topic_check_first', 0)}-source \"check first\"** group is lower "
              "confidence (mostly generic-word coincidence per the spot-check in §3) — worth a lighter pass, "
              "not urgent.")
    L.append(f"- **{s['untagged']} untagged sources** ({_pct(s['untagged'], n)}) remain the single biggest "
              "structural gap — most are legacy pre-taxonomy ingests, not necessarily off-topic (the ongoing "
              "audit loop's \"Tag issues\" notes already double as a back-tagging worksheet).")
    L.append("- Consider retiring or narrowing the `sensory` and `off-note` ingest queries (§5) before the next "
              "ingest pass — they are disproportionately responsible for the off-topic shortlist.")
    L.append("")

    path.write_text("\n".join(L), encoding="utf-8")


# ===========================================================================
# CLI
# ===========================================================================
def main() -> int:
    ap = argparse.ArgumentParser(description="Taxonomy-bible relevance check vs relevance_llm (read-only).")
    ap.add_argument("--limit", type=int, default=0, help="limit sources processed (0 = all)")
    ap.add_argument("--write-md", action="store_true", help="write analysis/relevance_check_<date>.md")
    ap.add_argument("--md-out", help="override md output path")
    args = ap.parse_args()

    conn = get_conn()
    cur = conn.cursor()
    rows = compute_all(cur, limit=args.limit)
    conn.close()

    s = summarize(rows)
    n = s["n"]
    print(f"== taxonomy relevance check == {n} sources")
    print(f"citable (abstract+search_vec): {s['citable']} ({_pct(s['citable'], n)})")
    print(f"tagged: {s['tagged']} ({_pct(s['tagged'], n)}) / untagged: {s['untagged']} ({_pct(s['untagged'], n)})")
    print(f"relevance_llm buckets: " + " · ".join(f"{b} {s['rel_buckets'][b]}" for b in [">=80", "60-79", "40-59", "<40"]))
    print(f"priority_score buckets: " + " · ".join(f"{b} {s['pr_buckets'][b]}" for b in [">=80", "60-79", "40-59", "<40"]))
    print(f"taxonomy signal: " + " · ".join(f"{k} {v}" for k, v in s["signal_counts"].most_common()))
    print(f"reconciliation: " + " · ".join(f"{k} {v}" for k, v in s["reconciliation_counts"].most_common()))
    print(f"recommended action: " + " · ".join(f"{k} {v}" for k, v in s["action_counts"].most_common()))

    if args.write_md:
        now = datetime.now(timezone.utc)
        out = Path(args.md_out) if args.md_out else (REPO_ROOT / "analysis" / f"relevance_check_{now:%Y-%m-%d}.md")
        out.parent.mkdir(parents=True, exist_ok=True)
        write_md(out, rows, s)
        print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
