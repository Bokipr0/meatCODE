# Last updated: 2026-10-25 19:05 UTC · Yochai (PM) with Claude · NEW server helpers for the Ecosystem module
#   (flag `ecosystem_module`). No HTTP and no SQL here — meatcode_server.py owns routing + auth and hands in the
#   model call, same split as papers_browser.py / reaction_network.py.
"""MeatCODE Ecosystem — server-side helpers for app/modules/ecosystem.html.

bootstrap()            GET /api/ecosystem/bootstrap
    The topic taxonomy (read from the bible, db/taxonomy/keywords_topics.json, via db/taxonomy.py — never a
    hardcoded copy) plus the GFI contact address used for "Ask GFI for an introduction" and
    "Suggest a correction / remove me" (env ECOSYSTEM_CONTACT_EMAIL; empty -> the UI says requests aren't
    switched on yet).

read_intent(body, call_model)   POST /api/ecosystem/intent  {text, prev}
    Turns a free-text request ("our pea patty tastes beany after grilling") into the structured reading the
    Ecosystem ranks with: intent, taxonomy topics, sector, region, since, person. The prompt is built HERE from
    validated fields only (the browser never sends a prompt), and the model's JSON is validated against the
    allowed values before it goes back. The browser falls back to its local keyword reader on any error.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INTENTS = ("collaborate", "partner", "review", "explore", "learn", "events", "person")
SECTORS = ("all", "academic", "industry", "ngo")
REGIONS = ("any", "europe", "north_america", "asia_pacific", "israel", "latin_america")
MAX_TEXT = 600

_TAXONOMY = None


def _load_bible():
    """db/taxonomy.py's load() (canonical order), imported by path so server/ needs no package setup."""
    spec = importlib.util.spec_from_file_location(
        "meatcode_taxonomy", os.path.join(REPO_ROOT, "db", "taxonomy.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.load()


def taxonomy():
    """[{b: branch, s: topic_slug, n: topic_name}], one row per topic slug, bible order."""
    global _TAXONOMY
    if _TAXONOMY is None:
        seen, out = set(), []
        for r in _load_bible():
            slug = r.get("topic_slug")
            if not slug or slug in seen:
                continue
            seen.add(slug)
            out.append({"b": r.get("branch") or "", "s": slug, "n": r.get("topic_name") or slug})
        _TAXONOMY = out
    return _TAXONOMY


def bootstrap():
    return {
        "taxonomy": taxonomy(),
        "contact_email": os.environ.get("ECOSYSTEM_CONTACT_EMAIL", "").strip(),
        "data_url": "/app/modules/ecosystem_data.json",
    }


def _clean_prev(prev):
    if not isinstance(prev, dict):
        return None
    slugs = {t["s"] for t in taxonomy()}
    since = prev.get("since")
    return {
        "intent": prev.get("intent") if prev.get("intent") in INTENTS else "collaborate",
        "topics": [s for s in (prev.get("topics") or []) if s in slugs][:6],
        "sector": prev.get("sector") if prev.get("sector") in SECTORS else "all",
        "region": prev.get("region") if prev.get("region") in REGIONS else "any",
        "since": since if isinstance(since, int) and 1990 <= since <= 2100 else None,
    }


def build_prompt(text, prev):
    tax = "\n".join("%s: %s" % (t["s"], t["n"]) for t in taxonomy())
    return (
        "You read requests in a directory of meat-flavor R&D experts and turn them into a structured intent. "
        "Reply with JSON only.\n"
        "Fields:\n"
        '- "intent": one of "collaborate" (research partner, bench work), "partner" (industry/commercial partner, '
        'supplier, scale-up), "review" (reviewer, advisor, validation, seniority), "explore" (who works on X, '
        'landscape, where), "learn" (courses, training, upskilling), "events" (conferences, webinars, meetups, '
        'places to present), "person" (user names a specific person).\n'
        '- "topics": up to 6 slugs from the taxonomy below that best capture the scientific subject. '
        "Use only listed slugs.\n"
        '- "sector": "all" | "academic" | "industry" | "ngo" (NGO or government).\n'
        '- "region": "any" | "europe" | "north_america" | "asia_pacific" | "israel" | "latin_america".\n'
        '- "since": a year if the user limits recency, else null.\n'
        '- "person": the name if intent is "person", else "".\n'
        'If the request only refines the previous one (e.g. "only industry"), keep the previous topics and intent '
        "unless changed.\n"
        "Previous reading: %s\n"
        "Taxonomy (slug: name):\n%s\n\n"
        "Request: %s" % (json.dumps(prev) if prev else "none", tax, text)
    )


def read_intent(body, call_model):
    """Validated intent dict. Raises ValueError on a bad request or unusable model output."""
    if not isinstance(body, dict):
        raise ValueError("body must be a JSON object")
    text = str(body.get("text") or "").strip()[:MAX_TEXT]
    if not text:
        raise ValueError("missing 'text'")
    prev = _clean_prev(body.get("prev"))
    raw = call_model(build_prompt(text, prev))
    m = re.search(r"\{.*\}", raw or "", re.S)
    if not m:
        raise ValueError("no JSON in model output")
    data = json.loads(m.group(0))
    slugs = {t["s"] for t in taxonomy()}
    since = data.get("since")
    return {
        "intent": data.get("intent") if data.get("intent") in INTENTS else "collaborate",
        "topics": [s for s in (data.get("topics") or []) if isinstance(s, str) and s in slugs][:6],
        "sector": data.get("sector") if data.get("sector") in SECTORS else "all",
        "region": data.get("region") if data.get("region") in REGIONS else "any",
        "since": since if isinstance(since, int) and 1990 <= since <= 2100 else None,
        "person": str(data.get("person") or "")[:120],
    }
