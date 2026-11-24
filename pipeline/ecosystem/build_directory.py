# Last updated: 2026-11-24 UTC · Yochai (PM) with Claude · NEW — builds ecosystem_module.directory_people
"""Build the Ecosystem Directory: one public row per person.

Inputs
  * public.experts (+ organizations) from --source-env (SELECT only). Production is the most complete copy.
  * Daniel's Ecosystem Master workbook (--master, .xlsm/.xlsx). PRIVATE: never commit it. Only public fields are
    read: name, affiliation, role, segment, country, technical domains, LinkedIn URL, Contact ID. Emails,
    relationship / outreach / message data and group membership are never read into the output.
  * sources.authors from --target-env, for paper links (ids must be valid where the table is written).

Merging (high confidence only; anything less stays separate)
  1. Same ORCID, same OpenAlex id, or same LinkedIn profile.
  2. The Master's own expert mapping (sheet "Expert DB Integration": Contact ID <-> experts.id).
  3. Same first+last name AND compatible affiliations (the distinctive words of one affiliation are all in the
     other), between DIFFERENT source batches. Two rows from the same batch were separate entries in that
     source, so a name alone never merges them.
  4. Inside the Master: same name and compatible (or missing) affiliation.
  A merge that would join two different ORCIDs or OpenAlex ids is refused.

Paper links: an author string on a source is linked when its first+last key belongs to exactly one person.
Ambiguous names (two people share them) are not linked and are counted in the report.

Usage
  python pipeline/ecosystem/build_directory.py --master PATH --source-env .env --target-env .env.dev            # dry run
  python pipeline/ecosystem/build_directory.py --master PATH --source-env .env --target-env .env.dev --write    # rebuild table
"""
from __future__ import annotations

import argparse
import collections
import datetime
import importlib.util
import json
import re
import sys
import unicodedata
from pathlib import Path

import openpyxl
import psycopg2
import psycopg2.extras

ROOT = Path(__file__).resolve().parents[2]


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ECO = _load("eco_server", "server/ecosystem.py")       # _clean_org, _country, _sector: one rule set with the page
TAXO = _load("eco_taxonomy", "db/taxonomy.py")
SLUGS = {r["topic_slug"] for r in TAXO.load()}

# ── normalisation ────────────────────────────────────────────────────────────────────────────────────────────
_EXTRA = str.maketrans({"ł": "l", "Ł": "L", "ø": "o", "Ø": "O", "ß": "ss", "æ": "ae", "Æ": "AE", "đ": "d", "Đ": "D",
                        "ı": "i", "œ": "oe"})
TITLES = {"dr", "prof", "professor", "mr", "mrs", "ms", "mx", "phd", "md", "msc", "bsc", "mba", "jr", "sr", "dvm",
          "dphil", "ii", "iii", "assoc", "assistant", "associate", "emeritus", "sir"}


def fold(s):
    s = unicodedata.normalize("NFKD", str(s or "").translate(_EXTRA))
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def bare_name(s):
    """Display name without titles, post-nominals, emoji or "(nickname)"."""
    s = re.sub(r"\(.*?\)", " ", str(s or ""))
    s = re.sub(r",\s*(ph\.?\s*d|m\.?\s*d|msc|mba|dvm|dphil|jr|sr|cfs|rd)\b.*$", "", s, flags=re.I)
    s = re.sub(r"^\s*((assoc(iate)?|assist(ant)?)\.?\s+)?(prof(essor)?|dr|mr|mrs|ms)\.?\s+", "", s, flags=re.I)
    s = re.sub(r"[^\w\s.'’-]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def name_tokens(s):
    return [t for t in re.findall(r"[a-z]+", fold(re.sub(r"\(.*?\)", " ", str(s or "")))) if t not in TITLES]


def name_key(s):
    t = name_tokens(s)
    if len(t) < 2 or len(t[-1]) < 2 or len(t[0]) < 2:
        return None
    return t[0] + " " + t[-1]


ORG_ALIAS = [(r"\bpenn state\b", "pennsylvania state"), (r"\buc davis\b", "university of california davis"),
             (r"\bwur\b", "wageningen"), (r"\bcaas\b", "chinese academy agricultural sciences"),
             (r"\bntnu\b", "norwegian university science technology"), (r"\bdtu\b", "technical university denmark"),
             (r"\btum\b", "technical university munich"), (r"\beth\b", "eth zurich"), (r"\bcsic\b", "csic spanish")]
ORG_GENERIC = set((
    "university universite universitat universita universidad universidade univ institute institut instituto istituto "
    "college school department dept faculty division unit section chair group food foods science sciences technology "
    "technologies technological engineering agricultural agriculture agri agro national state key laboratory "
    "laboratories lab labs research center centre centers academy chinese china people peoples republic of and the "
    "for in at on de del della di des du la le les et und fur der van von voor normal medical technical polytechnic "
    "applied life biological biology biotechnology chemistry chemical nutrition health animal plant meat product "
    "products processing quality safety co ltd inc gmbh corp corporation company companies limited llc sa ag bv nv "
    "plc srl spa international global north south east west northwest northeast southwest southeast central new city "
    "province provincial municipal government ministry rural affairs development innovation campus graduate higher "
    "education hospital foundation association council organization organisation network services service solutions "
    "systems self employed freelance independent consultant consulting stealth startup private retired "
    "innovations ingredients ingredient flavors flavours flavor flavour usa us uk"
).split())


def org_words(s):
    """(distinctive words, normalised full string) for one affiliation."""
    t = fold(s)
    for rx, rep in ORG_ALIAS:
        t = re.sub(rx, rep, t)
    words = frozenset(w for w in re.findall(r"[a-z]+", t) if len(w) >= 3 and w not in ORG_GENERIC)
    return words, " ".join(re.findall(r"[a-z0-9]+", t))


def org_compatible(a_orgs, b_orgs):
    """True when some affiliation of a and some affiliation of b agree:
    - the same name, or one name inside the other (at least 12 characters), e.g. 'Chinese Academy of Agricultural
      Sciences' on both sides even though every word is generic; or
    - the distinctive words of the shorter one are all in the other (the page's orgIn rule):
      'Jiangnan University' ~ 'State Key Lab ..., Jiangnan University';
      'Beijing Forestry University' !~ 'Beijing Technology and Business University'."""
    for xw, xs in a_orgs:
        for yw, ys in b_orgs:
            if xs and ys and (xs == ys or (min(len(xs), len(ys)) >= 12 and (xs in ys or ys in xs))):
                return True
            if not xw or not yw:
                continue
            small, big = (xw, yw) if len(xw) <= len(yw) else (yw, xw)
            if sum(len(w) for w in small) >= 4 and small <= big:
                return True
    return False


def norm_orcid(s):
    m = re.search(r"(\d{4}-\d{4}-\d{4}-\d{3}[\dXx])", str(s or ""))
    return m.group(1).upper() if m else None


def norm_oa(s):
    m = re.search(r"(A\d{6,})", str(s or ""), re.I)
    return m.group(1).upper() if m else None


def norm_linkedin(s):
    m = re.search(r"linkedin\.com/in/([^/?#\s]+)", str(s or ""), re.I)
    return m.group(1).lower().rstrip("/") if m else None


COUNTRY_NAMES = {"israel": "IL", "china": "CN", "united states": "US", "usa": "US", "united kingdom": "GB", "uk": "GB",
                 "germany": "DE", "france": "FR", "spain": "ES", "italy": "IT", "netherlands": "NL", "belgium": "BE",
                 "switzerland": "CH", "denmark": "DK", "sweden": "SE", "finland": "FI", "norway": "NO", "poland": "PL",
                 "ireland": "IE", "canada": "CA", "brazil": "BR", "japan": "JP", "south korea": "KR", "korea": "KR",
                 "singapore": "SG", "australia": "AU", "new zealand": "NZ", "india": "IN", "estonia": "EE",
                 "austria": "AT", "portugal": "PT", "greece": "GR", "chile": "CL", "mexico": "MX", "argentina": "AR",
                 "thailand": "TH", "turkey": "TR", "egypt": "EG", "pakistan": "PK", "serbia": "RS", "croatia": "HR",
                 "czechia": "CZ", "czech republic": "CZ", "hong kong": "HK", "taiwan": "TW", "lithuania": "LT"}


def country_code(value, orgs):
    v = str(value or "").strip()
    if v.lower() in COUNTRY_NAMES:
        return COUNTRY_NAMES[v.lower()]
    for org in orgs:
        cc = ECO._country(v, org)
        if cc:
            return cc
    return ECO._country(v, None)


SEGMENT_SECTOR = {
    "academic / research": "academic", "academic / sensory": "academic", "academic researcher": "academic",
    "ecosystem / academic operations": "academic",
    "food / ingredient industry": "industry", "alt-meat / food industry": "industry",
    "flavor / ingredient company": "industry", "technology / service provider": "industry",
    "analytical / sensory / data": "industry", "gc-ms / lc-ms": "industry", "consultant / advisor": "industry",
    "funding / investment": "industry", "industry / funder": "industry",
    "ecosystem / nonprofit": "ngo", "media / events / community": "ngo", "ecosystem / technical": "ngo",
    "r&d / ecosystem": "ngo",
}
ORG_TYPE_SECTOR = {"academy": "academic", "company": "industry", "ngo_gov": "ngo"}
DIM_TOPIC = {"fermentation": "fermentation_topic", "off-note": "off_note_masking", "meat-aroma": "meat_aroma",
             "maillard": "reaction_flavors_topic", "sensory": "consumer_panel_topic",
             "plant-protein": "plant_based_proteins"}
BATCH_SOURCE = {"2026-05-05": "openalex", "2026-05-19": "dimensions", "2026-11-02": "dd_list"}


def classify(text):
    return [r["topic_slug"] for r in TAXO.classify(text or "", top_k=6)]


def read_env(path):
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("DATABASE_URL not found in " + str(path))


def query(url, sql, args=()):
    with psycopg2.connect(url) as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, args)
        return cur.fetchall()


# ── inputs ───────────────────────────────────────────────────────────────────────────────────────────────────
EXPERTS_SQL = """
SELECT e.id, e.name, e.affiliation, e.current_org, e.country, o.country AS org_country, o.name AS org_name,
       e.org_type::text AS org_type, e.h_index, e.orcid, e.openalex_id, e.linkedin_url, e.key_research,
       e.dimensions_topics, e.created_at::date::text AS batch,
       CASE WHEN e.notes LIKE '{%%' THEN e.notes::jsonb - 'verification_notes' - 'classification_rationale'
            - 'classification_kind' - 'source_sha256' ELSE NULL END AS dd
FROM experts e LEFT JOIN organizations o ON o.id = e.organization_id
ORDER BY e.id
"""


def expert_records(rows):
    out = []
    for r in rows:
        dd = r.get("dd") or {}
        if isinstance(dd, str):
            dd = json.loads(dd)
        orgs = [o for o in (r.get("current_org"), r.get("affiliation"), r.get("org_name")) if o]
        sites = []
        for u in (json.loads(dd["public_sources"]) if isinstance(dd.get("public_sources"), str) else
                  dd.get("public_sources") or []):
            if isinstance(u, str) and u.startswith("http"):
                sites.append(u)
        topics = [DIM_TOPIC[t] for t in (r.get("dimensions_topics") or []) if t in DIM_TOPIC]
        for c in (json.loads(dd["existing_topic_connections"]) if isinstance(dd.get("existing_topic_connections"), str)
                  else dd.get("existing_topic_connections") or []):
            if isinstance(c, dict) and c.get("slug") in SLUGS:
                topics.append(c["slug"])
        about = dd.get("expertise_area") or r.get("key_research") or None
        topics += classify(about)
        out.append({
            "key": "e%d" % r["id"], "kind": "expert", "eid": r["id"],
            "batch": BATCH_SOURCE.get(r["batch"], "experts_" + r["batch"]),
            "name": r["name"] or "", "orgs": orgs, "role": dd.get("professional_role") or None, "about": about,
            "country_raw": r.get("country") or r.get("org_country"), "segment": None,
            "org_type": r.get("org_type"), "h": r.get("h_index"),
            "orcid": norm_orcid(r.get("orcid")), "oa": norm_oa(r.get("openalex_id")),
            "li": r.get("linkedin_url") if norm_linkedin(r.get("linkedin_url")) else None,
            "sites": sites, "topics": topics, "domains": [dd["expertise_area"]] if dd.get("expertise_area") else [],
            "master_ids": [],
        })
    return out


PERSON_SHEETS_SKIP = {"README", "Dashboard", "Coverage Gaps", "Group Definitions",
                      "Expert DB Source", "Expert DB Integration", "Expert DB Outreach"}


def _sheet_rows(wb, title):
    it = wb[title].iter_rows(values_only=True)
    hdr = [str(h).strip() if h is not None else "" for h in next(it)]
    for r in it:
        d = {hdr[i]: r[i] for i in range(min(len(hdr), len(r))) if hdr[i] and r[i] not in (None, "")}
        if d.get("Name"):
            yield d


def master_records(path):
    """Public fields only. Returns (records, mapping Contact ID -> [experts.id])."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    recs = []
    for title in wb.sheetnames:
        if title in PERSON_SHEETS_SKIP:
            continue
        for i, d in enumerate(_sheet_rows(wb, title)):
            role = str(d.get("Role") or d.get("Role / Career Stage") or "").strip()
            if re.search(r"meatcode expert database", role, re.I):     # placeholder the Master gave imported rows
                role = ""
            domains =[x.strip() for x in re.split(r"[;|]", str(d.get("Technical Domains") or d.get("Primary Domain") or ""))
                       if x.strip()]
            recs.append({
                "key": "m:%s:%d" % (title, i), "kind": "master", "batch": "master",
                "cid": str(d.get("Contact ID") or "").strip() or None,
                "name": bare_name(d["Name"]), "orgs": [str(d["Affiliation"]).strip()] if d.get("Affiliation") else [],
                "role": role or None, "about": None,
                "country_raw": d.get("Country/Region"), "segment": str(d.get("Segment") or "").strip().lower() or None,
                "org_type": None, "h": None, "orcid": None, "oa": None,
                "li": str(d["LinkedIn URL"]).strip() if norm_linkedin(d.get("LinkedIn URL")) else None,
                "sites": [], "topics": classify(" ; ".join(domains)), "domains": domains, "master_ids": [],
            })
    mapping = {}
    if "Expert DB Integration" in wb.sheetnames:
        for d in _sheet_rows(wb, "Expert DB Integration"):
            cid = str(d.get("Contact ID") or "").strip()
            ids = []
            for x in re.split(r"[;,]", str(d.get("Expert DB IDs") or "")):
                try:
                    ids.append(int(float(x)))
                except ValueError:
                    pass
            if cid and ids:
                mapping[cid] = ids
    return recs, mapping


# ── merging ──────────────────────────────────────────────────────────────────────────────────────────────────
class Components:
    def __init__(self, recs):
        self.recs = recs
        self.parent = list(range(len(recs)))
        self.ids = [{"orcid": {r["orcid"]} - {None}, "oa": {r["oa"]} - {None}} for r in recs]
        self.why = collections.Counter()
        self.refused = 0

    def find(self, i):
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def union(self, a, b, why):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        for f in ("orcid", "oa"):
            if self.ids[ra][f] and self.ids[rb][f] and not (self.ids[ra][f] & self.ids[rb][f]):
                self.refused += 1
                return False
        self.parent[rb] = ra
        for f in ("orcid", "oa"):
            self.ids[ra][f] |= self.ids[rb][f]
        self.why[why] += 1
        return True

    def groups(self):
        g = collections.defaultdict(list)
        for i in range(len(self.recs)):
            g[self.find(i)].append(self.recs[i])
        return list(g.values())


def merge(recs, cid_to_experts):
    for r in recs:
        r["nk"] = name_key(r["name"])
        rt = name_tokens(r["name"])
        r["nk_rev"] = (rt[-1] + " " + rt[0]) if r["nk"] else None
        r["ow"] = [org_words(o) for o in r["orgs"]]
    C = Components(recs)
    # 1. shared identifiers
    for field, why in (("orcid", "same ORCID"), ("oa", "same OpenAlex id")):
        seen = {}
        for i, r in enumerate(recs):
            if r[field]:
                if r[field] in seen:
                    C.union(seen[r[field]], i, why)
                else:
                    seen[r[field]] = i
    seen = {}
    for i, r in enumerate(recs):
        slug = norm_linkedin(r["li"])
        if slug:
            if slug in seen:
                C.union(seen[slug], i, "same LinkedIn profile")
            else:
                seen[slug] = i
    # 2. the Master's own mapping to experts.id
    by_eid = {r["eid"]: i for i, r in enumerate(recs) if r["kind"] == "expert"}
    for i, r in enumerate(recs):
        for eid in cid_to_experts.get(r.get("cid") or "", []):
            if eid in by_eid:
                C.union(by_eid[eid], i, "Master mapping to experts.id")
    for cid, eids in cid_to_experts.items():                  # Master marked these expert rows as one person
        for a, b in zip(eids, eids[1:]):
            if a in by_eid and b in by_eid:
                C.union(by_eid[a], by_eid[b], "Master mapping to experts.id")
    # Master rows across sheets with the same Contact ID
    seen = {}
    for i, r in enumerate(recs):
        if r.get("cid"):
            if r["cid"] in seen:
                C.union(seen[r["cid"]], i, "same Master Contact ID")
            else:
                seen[r["cid"]] = i
    # 3 + 4. name + affiliation
    by_name = collections.defaultdict(list)
    for i, r in enumerate(recs):
        if r["nk"]:
            by_name[r["nk"]].append(i)
    for i, r in enumerate(recs):                              # reversed order (Wang Wei / Wei Wang)
        if r["nk_rev"] and r["nk_rev"] in by_name and r["nk_rev"] != r["nk"]:
            by_name[r["nk_rev"]].append(i)
    same_batch_kept = 0
    for idx in by_name.values():
        idx = sorted(set(idx))
        for x in range(len(idx)):
            for y in range(x + 1, len(idx)):
                a, b = recs[idx[x]], recs[idx[y]]
                if a["batch"] == b["batch"]:
                    if a["batch"] == "master" and (not a["orgs"] or not b["orgs"] or org_compatible(a["ow"], b["ow"])):
                        C.union(idx[x], idx[y], "Master duplicate (name + affiliation)")
                    elif org_compatible(a["ow"], b["ow"]) and C.find(idx[x]) != C.find(idx[y]):
                        same_batch_kept += 1
                    continue
                if org_compatible(a["ow"], b["ow"]):
                    C.union(idx[x], idx[y], "same name + same affiliation")
    return C, same_batch_kept


# ── people ───────────────────────────────────────────────────────────────────────────────────────────────────
BATCH_RANK = {"dd_list": 0, "master": 1, "openalex": 2, "dimensions": 3}


def first(vals):
    for v in vals:
        if v not in (None, "", []):
            return v
    return None


def build_person(group):
    experts = sorted((r for r in group if r["kind"] == "expert"), key=lambda r: r["eid"])
    masters = [r for r in group if r["kind"] == "master"]
    by_rank = sorted(group, key=lambda r: BATCH_RANK.get(r["batch"], 9))
    pid = str(experts[0]["eid"]) if experts else "m-" + (first(r.get("cid") for r in masters) or masters[0]["key"])
    name = first(r["name"] for r in sorted(experts, key=lambda r: BATCH_RANK.get(r["batch"], 9))) or masters[0]["name"]
    orgs_raw = [o for r in by_rank for o in r["orgs"]]
    orgs, seenw = [], set()
    for o in orgs_raw:
        c = ECO._clean_org(o)
        if c and fold(c) not in seenw:
            seenw.add(fold(c))
            orgs.append(c)
    org = orgs[0] if orgs else None
    seg = first(r["segment"] for r in masters)
    sector = SEGMENT_SECTOR.get(seg or "")
    if not sector:
        sector = first(ORG_TYPE_SECTOR.get(r["org_type"]) for r in experts) or ECO._sector(org)
    country = None
    for r in by_rank:
        country = country_code(r["country_raw"], r["orgs"]) if (r["country_raw"] or r["orgs"]) else None
        if country:
            break
    topics = collections.Counter(t for r in group for t in r["topics"] if t in SLUGS)
    domains = []
    for r in by_rank:
        for d in r["domains"]:
            if d and d not in domains:
                domains.append(d)
    sites = []
    for r in group:
        for u in r["sites"]:
            if u not in sites and not norm_linkedin(u):
                sites.append(u)
    sources = sorted({"gfi_contacts" if r["batch"] == "master" else r["batch"] for r in group})
    keys = sorted({k for r in group for k in (r["nk"],) if k})
    return {
        "id": pid, "name": bare_name(name) or name, "org": org, "orgs": orgs, "sector": sector or "unknown",
        "role": first(r["role"] for r in by_rank), "about": first(r["about"] for r in by_rank),
        "country": country, "topics": [t for t, _ in topics.most_common()], "domains": domains[:8],
        "h_index": max([r["h"] for r in group if r["h"] is not None], default=None),
        "orcid": first(r["orcid"] for r in group), "openalex_id": first(r["oa"] for r in group),
        "linkedin_url": first(r["li"] for r in by_rank), "website_urls": sites[:4],
        "expert_ids": [r["eid"] for r in experts], "master_ids": sorted({r["cid"] for r in masters if r.get("cid")}),
        "sources": sources, "name_keys": keys, "papers": [],
    }


SOURCES_SQL = """
SELECT s.id, s.authors, coalesce((SELECT array_agg(t.slug) FROM source_topics st JOIN topics t ON t.id = st.topic_id
                                 WHERE st.source_id = s.id), '{}') AS tp
FROM sources s WHERE coalesce(s.authors, '') <> ''
"""


def link_papers(people, source_rows):
    index = collections.defaultdict(set)
    for i, p in enumerate(people):
        for k in p["name_keys"]:
            index[k].add(i)
    linked = ambiguous = short_skipped = 0
    for s in source_rows:
        for raw in re.split(r"\s*[;,]\s*", s["authors"] or ""):
            k = name_key(bare_name(raw))
            if not k:
                continue
            hit = index.get(k)
            if not hit:
                t = k.split()
                hit = index.get(t[1] + " " + t[0])
            if not hit:
                continue
            if len(hit) > 1:
                ambiguous += 1
                continue
            p = people[next(iter(hit))]
            # Very short names ("Yu Fu", "Li Hou") are shared by many authors outside the directory: link them only
            # for people the OpenAlex batch found through the corpus itself.
            if len(k.replace(" ", "")) < 7 and "openalex" not in p["sources"]:
                short_skipped += 1
                continue
            if s["id"] not in p["papers"]:
                p["papers"].append(s["id"])
                linked += 1
                for t in s["tp"] or []:
                    if t in SLUGS and t not in p["topics"]:
                        p["topics"].append(t)
    for p in people:
        p["papers"].sort()
    return linked, ambiguous, short_skipped


COLUMNS = ["id", "name", "org", "orgs", "role", "about", "country", "sector", "topics", "domains", "h_index", "orcid",
           "openalex_id", "linkedin_url", "website_urls", "papers", "expert_ids", "master_ids", "sources", "name_keys"]


def write(url, people):
    ddl = (ROOT / "db/migrations/0037_ecosystem_directory.sql").read_text(encoding="utf-8")
    now = datetime.datetime.now(datetime.timezone.utc)
    with psycopg2.connect(url) as conn, conn.cursor() as cur:
        cur.execute(ddl)
        cur.execute("TRUNCATE ecosystem_module.directory_people")
        psycopg2.extras.execute_values(
            cur, "INSERT INTO ecosystem_module.directory_people (%s, built_at) VALUES %%s" % ", ".join(COLUMNS),
            [tuple(p[c] for c in COLUMNS) + (now,) for p in people], page_size=500)
    return now


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--master", required=True, help="Ecosystem Master workbook (private; not in git)")
    ap.add_argument("--source-env", required=True, help="env file whose DATABASE_URL holds the experts (SELECT only)")
    ap.add_argument("--target-env", required=True, help="env file whose DATABASE_URL gets the table")
    ap.add_argument("--write", action="store_true", help="rebuild the table (default: report only)")
    ap.add_argument("--samples", type=int, default=0, help="print N example merges by name + affiliation")
    a = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    src, dst = read_env(a.source_env), read_env(a.target_env)
    erecs = expert_records(query(src, EXPERTS_SQL))
    mrecs, cid_map = master_records(a.master)
    recs = erecs + mrecs
    C, same_batch_kept = merge(recs, cid_map)
    groups = C.groups()
    people = [build_person(g) for g in groups]
    ids = collections.Counter(p["id"] for p in people)
    assert all(n == 1 for n in ids.values()), "duplicate person ids"
    linked, ambiguous, short_skipped = link_papers(people, query(dst, SOURCES_SQL))
    rel = {r["id"] for r in query(dst, "SELECT id FROM sources WHERE relevance_llm >= 60")}

    print("Input: %d expert rows, %d Master rows (%d distinct Contact IDs)" % (
        len(erecs), len(mrecs), len({r['cid'] for r in mrecs if r['cid']})))
    print("Merges:", dict(C.why), "| refused for conflicting ORCID/OpenAlex:", C.refused,
          "| same-batch same-name same-affiliation kept apart:", same_batch_kept)
    print("People: %d" % len(people))
    print("  by source mix:", collections.Counter("+".join(p["sources"]) for p in people).most_common(10))
    print("  sector:", dict(collections.Counter(p["sector"] for p in people)))
    print("  with country: %d | org: %d | role: %d | topics: %d | LinkedIn: %d | website: %d | ORCID/OpenAlex: %d" % (
        sum(bool(p["country"]) for p in people), sum(bool(p["org"]) for p in people),
        sum(bool(p["role"]) for p in people), sum(bool(p["topics"]) for p in people),
        sum(bool(p["linkedin_url"]) for p in people), sum(bool(p["website_urls"]) for p in people),
        sum(bool(p["orcid"] or p["openalex_id"]) for p in people)))
    print("  paper links: %d (skipped: %d ambiguous names, %d very short names) | people with papers: %d | with "
          "trusted (relevance >= 60) papers: %d" % (linked, ambiguous, short_skipped,
                                                    sum(bool(p["papers"]) for p in people),
                                                    sum(any(s in rel for s in p["papers"]) for p in people)))
    if a.samples:
        shown = 0
        for g in groups:
            kinds = {r["batch"] for r in g}
            if len(g) > 1 and len(kinds) > 1 and shown < a.samples:
                print("   ~", " | ".join("%s [%s] %s" % (r["name"], r["batch"], (r["orgs"] or ["-"])[0][:45]) for r in g))
                shown += 1
    if a.write:
        at = write(dst, people)
        print("Wrote %d rows to ecosystem_module.directory_people at %s" % (len(people), at.isoformat(timespec="seconds")))
    else:
        print("Dry run: nothing written (add --write).")


if __name__ == "__main__":
    sys.exit(main())
