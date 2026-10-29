# Last updated: 2026-10-25 20:25 UTC · Yochai (PM) with Claude · LIVE people + papers from Neon (live_people):
#   the 8 Oct snapshot's rule re-run as SELECT-only SQL on every request (10-min cache). Verified against Neon
#   via the read-only connector: 155 people / 109 papers = the snapshot's 153 / 108 plus 2 accented names it
#   had missed (José M. Lorenzo, Igor Tomašević). Prev 2026-10-25 19:05 UTC · NEW server helpers for the
#   Ecosystem module (flag `ecosystem_module`). No HTTP here — meatcode_server.py owns routing + auth and hands
#   in pg_rows / the model call, same split as papers_browser.py / reaction_network.py.
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

live_people(pg_rows)   GET /api/ecosystem/people
    The People directory's people + papers, LIVE from Neon (same JSON shape as ecosystem_data.json's "rd").
    Rule (identical to the 8 Oct snapshot): authors of the sources the Oracle trusts (relevance_llm >= 60), split
    on ; or , and matched to public.experts by exact normalised name (accents folded, Prof/Dr and "(…)" dropped,
    letters only, at least 6 letters so short ambiguous names don't mis-match). Several expert rows with the
    same name are one person: lowest id, first non-empty organisation (current_org, else affiliation) / country /
    h-index / ORCID / OpenAlex id.
    Kept when they have >= 2 such papers or an OpenAlex-backed record. source_experts is empty in Neon, hence
    the name match. Public information only: no email, notes, outreach status or relevance score is selected,
    and emails embedded in affiliation text are stripped. Country / sector are inferred from the affiliation
    when experts.country / org_type are empty (they mostly are).
"""
from __future__ import annotations

import datetime
import importlib.util
import json
import os
import re
import threading
import time

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


# ─── Live people + papers (GET /api/ecosystem/people) ────────────────────────────────────────────────────────
# Accent folding without the unaccent extension (not installed on Neon; this module never runs DDL).
_ACCENTS_FROM = "ÀÁÂÃÄÅàáâãäåÇçÈÉÊËèéêëÌÍÎÏìíîïÑñÒÓÔÕÖØòóôõöøÙÚÛÜùúûüÝýÿĆćČčĘęŁłŃńŚśŠšŹźŻżŽžŐőŰűĞğİıŞş"
_ACCENTS_TO = "AAAAAAaaaaaaCcEEEEeeeeIIIIiiiiNnOOOOOOooooooUUUUuuuuYyyCcCcEeLlNnSsSsZzZzZzOoUuGgIiSs"
_NORM_AUTHOR = "regexp_replace(lower(translate({x}, '%s', '%s')), '[^a-z]', '', 'g')" % (_ACCENTS_FROM, _ACCENTS_TO)

LIVE_PEOPLE_SQL = r"""
WITH a AS (
  SELECT s.id AS sid, trim(x) AS author
  FROM sources s, regexp_split_to_table(s.authors, '\s*[;,]\s*') x
  WHERE s.relevance_llm >= 60 AND coalesce(s.authors, '') <> ''),
an AS (SELECT DISTINCT sid, """ + _NORM_AUTHOR.format(x="author") + r""" AS k FROM a),
en AS (
  SELECT e.id, e.name, e.affiliation, e.current_org, e.country, e.h_index, e.orcid, e.openalex_id,
         """ + _NORM_AUTHOR.format(
    x=r"regexp_replace(regexp_replace(e.name, '^(prof\.?\s*)?(dr\.?\s*)?', '', 'i'), '\s*\(.*\)$', '')") + r""" AS k
  FROM experts e),
m AS (SELECT DISTINCT an.k, an.sid FROM an JOIN en ON en.k = an.k WHERE length(an.k) >= 6),
g AS (
  SELECT en.k, min(en.id) AS id,
         (array_agg(en.name ORDER BY en.id))[1] AS name,
         (array_remove(array_agg(coalesce(en.current_org, en.affiliation) ORDER BY en.id), NULL))[1] AS org,
         (array_remove(array_agg(nullif(concat_ws(' ', en.current_org, en.affiliation), '') ORDER BY en.id), NULL))[1]
           AS place,
         (array_remove(array_agg(en.country ORDER BY en.id), NULL))[1] AS country,
         (array_remove(array_agg(en.h_index ORDER BY en.id), NULL))[1] AS h,
         (array_remove(array_agg(en.orcid ORDER BY en.id), NULL))[1] AS orcid,
         (array_remove(array_agg(en.openalex_id ORDER BY en.id), NULL))[1] AS oa
  FROM en WHERE en.k IN (SELECT k FROM m) GROUP BY en.k)
SELECT g.id, g.name, g.org, g.place, g.country, g.h, g.orcid, g.oa,
       (SELECT array_agg(m.sid ORDER BY m.sid) FROM m WHERE m.k = g.k) AS sids
FROM g
WHERE g.oa IS NOT NULL OR (SELECT count(*) FROM m WHERE m.k = g.k) >= 2
ORDER BY g.id
"""

LIVE_PAPERS_SQL = r"""
SELECT s.id, s.name AS t, s.year AS y, coalesce(s.journal, s.venue) AS j, s.doi, s.main_claim AS c,
       cardinality(regexp_split_to_array(s.authors, '\s*[;,]\s*')) AS na,
       coalesce((SELECT array_agg(t.slug ORDER BY t.slug) FROM source_topics st JOIN topics t ON t.id = st.topic_id
                 WHERE st.source_id = s.id), '{}') AS tp
FROM sources s WHERE s.id = ANY(%s) ORDER BY s.id
"""

# experts.country holds a mix of ISO codes and English names.
_COUNTRY_NAMES = {"china": "CN", "usa": "US", "united states": "US", "uk": "GB", "united kingdom": "GB",
                  "germany": "DE", "france": "FR", "spain": "ES", "belgium": "BE", "canada": "CA",
                  "switzerland": "CH", "netherlands": "NL", "italy": "IT", "japan": "JP", "korea": "KR"}

# Fallback when experts.country is empty: the affiliation names the place. Order matters (first match wins).
_COUNTRY_HINTS = [(re.compile(p, re.I), cc) for p, cc in [
    (r"agri-food canada|\bcanada\b|toronto|guelph|alberta|manitoba|saskatchewan|mcgill|british columbia", "CA"),
    (r"\bchina\b|chinese|people's republic|beijing|shanghai|jiangnan|jiangsu|hubei|hunan|henan|anhui|gansu|guangdong|guangxi|"
     r"guangzhou|harbin|hefei|huazhong|jinan|ludong|nanjing|qinghai|shaanxi|sichuan|tianjin|zhengzhou|zhongkai|xihua|xi'an|"
     r"bohai|minzu|lanzhou|changchun|ningbo|xinjiang|zhejiang|hangzhou|shandong|wuhan|shenzhen|chongqing|fujian|yunnan|"
     r"northeast agricultural|north ?west agricult|southwest university|ministry of agriculture and rural affairs", "CN"),
    (r"korea|seoul|jeonbuk|keimyung|sunchon|konkuk|chungnam|chonnam|pusan|busan|kyung", "KR"),
    (r"japan|tokyo|kyoto|osaka", "JP"),
    (r"\busa\b|united states|alabama|new jersey|rutgers|tufts|miami university|parkland college|california|texas|"
     r"florida|iowa|illinois|kansas|oklahoma|nebraska|purdue|cornell|massachusetts|ohio|michigan|wisconsin|"
     r"minnesota|appalachian|north carolina", "US"),
    (r"united kingdom|\buk\b|england|scotland|london|university of reading|nottingham|leeds", "GB"),
    (r"germany|munich|münchen|hohenheim|berlin|hamburg|bonn|dresden", "DE"),
    (r"netherlands|nederland|amsterdam|wageningen|utrecht|delft", "NL"),
    (r"belgium|gembloux|ghent|\bgent\b|leuven|liège|brussels", "BE"),
    (r"switzerland|nestl|zurich|zürich|geneva|lausanne", "CH"),
    (r"\bfrance\b|paris|inrae|dijon|nantes", "FR"),
    (r"\bspain\b|españa|galicia|valencia|madrid|barcelona|instituto de agroqu", "ES"),
    (r"\bitaly\b|milan|bologna|napoli|naples|parma|torino", "IT"),
    (r"sweden|chalmers|uppsala|\blund\b|stockholm", "SE"),
    (r"denmark|copenhagen|aarhus", "DK"),
    (r"finland|helsinki|turku", "FI"),
    (r"estonia|tallinn|tftak", "EE"),
    (r"austria|austrian|vienna|wien|graz", "AT"),
    (r"poland|warsaw|poznan|krakow", "PL"),
    (r"ireland|dublin|teagasc", "IE"),
    (r"new zealand|auckland|massey|otago|agresearch", "NZ"),
    (r"australia|sydney|unsw|melbourne|queensland|csiro", "AU"),
    (r"singapore|a\*star", "SG"),
    (r"thailand|songkla|bangkok|chulalongkorn|kasetsart", "TH"),
    (r"\bindia\b|mysore|delhi|cftri", "IN"),
    (r"brazil|são paulo|sao paulo|campinas|utfpr", "BR"),
    (r"israel|tel aviv|hebrew university|technion|volcani", "IL"),
    (r"serbia|belgrade", "RS"),
]]
_INDUSTRY = re.compile(r"\bco\.|\bltd\b|\binc\b|gmbh|\bb\.v\.|nestl|corp\b|company|\bgroup\b|\badm\b|distillery|"
                       r"tobacco|\bas\b|\bs\.a\b|zuivel o+nderzoek|\bnizo\b", re.I)
_ACADEMIC = re.compile(r"universit|college|school|hochschule|polytechnic|institute of technology", re.I)
_GOV = re.compile(r"ministry|academy of|national institute|research institute|state key laboratory|agri-food canada|"
                  r"inrae|agresearch|a\*star|competence cent|instituut|institute of|instituto|centro tecnol|teagasc|csiro",
                  re.I)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")


def _clean_org(raw):
    """Display name for an affiliation: no emails / 'Electronic address:' tails, and stop at the first part of a
    postal address (a comma-separated part with a digit in it)."""
    if not raw:
        return None
    s = re.split(r"electronic address:", _EMAIL.sub("", str(raw)), flags=re.I)[0]
    s = s.split(";")[0]
    parts = []
    for part in s.split(","):
        if re.search(r"\d", part) and parts:
            break
        parts.append(part.strip())
    out = ", ".join(p for p in parts if p).strip(" ,.")
    return out[:120] or None


def _country(db_value, org):
    v = (db_value or "").strip()
    if len(v) == 2 and v.isalpha():
        return v.upper()
    if v.lower() in _COUNTRY_NAMES:
        return _COUNTRY_NAMES[v.lower()]
    for rx, cc in _COUNTRY_HINTS:
        if org and rx.search(org):
            return cc
    return None


def _sector(org):
    if not org:
        return "unknown"
    if _INDUSTRY.search(org):
        return "industry"
    if _ACADEMIC.search(org):
        return "academic"
    if _GOV.search(org):
        return "ngo"
    return "academic"


_LIVE_TTL = 600            # seconds; the corpus changes on ingest runs, not per request
_LIVE_LOCK = threading.Lock()
_LIVE_CACHE = {"at": 0.0, "data": None}


def live_people(pg_rows):
    """{"source": "live", "as_of": ISO time, "people": [...], "papers": [...]} in ecosystem_data.json's rd shape.
    SELECT-only. Raises on DB errors (the route turns that into a 503 and the page falls back to its snapshot)."""
    with _LIVE_LOCK:
        if _LIVE_CACHE["data"] and time.time() - _LIVE_CACHE["at"] < _LIVE_TTL:
            return _LIVE_CACHE["data"]
    people_rows = pg_rows(LIVE_PEOPLE_SQL, ())
    sids = sorted({int(s) for r in people_rows for s in (r.get("sids") or [])})
    paper_rows = pg_rows(LIVE_PAPERS_SQL, (sids,)) if sids else []
    papers = [{"id": int(r["id"]), "t": r.get("t") or "", "y": r.get("y"), "j": r.get("j"), "doi": r.get("doi"),
               "c": r.get("c"), "tp": list(r.get("tp") or []), "na": r.get("na")} for r in paper_rows]
    have = {p["id"] for p in papers}
    people = []
    for r in people_rows:
        raw_org = r.get("org")
        orcid = (r.get("orcid") or "").strip()
        orcid = re.sub(r"^https?://orcid\.org/", "", orcid) or None
        people.append({
            "id": int(r["id"]), "name": r.get("name") or "", "org": _clean_org(raw_org),
            "country": _country(r.get("country"), r.get("place") or raw_org), "sector": _sector(raw_org),
            "h": r.get("h"), "orcid": orcid, "oa": r.get("oa") or None,
            "sids": [int(s) for s in (r.get("sids") or []) if int(s) in have],
        })
    data = {"source": "live", "as_of": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "people": people, "papers": papers}
    with _LIVE_LOCK:
        _LIVE_CACHE.update(at=time.time(), data=data)
    return data
