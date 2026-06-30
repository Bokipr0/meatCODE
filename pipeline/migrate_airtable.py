#!/usr/bin/env python3
"""
Airtable -> Postgres (Neon) migration for the GFI database.

Run AFTER:
  - gfi_schema.sql        (v1)
  - gfi_schema_v2_migration.sql
  - gfi_seed_taxonomies.sql
  - migration_phase1_alter.sql

Usage:
  export AIRTABLE_TOKEN="patXXXXX..."          # Personal Access Token
  export NEON_URL="postgresql://neondb_owner:..."  # full connection string
  python3 migrate_airtable.py

The script is idempotent: it checks for existing rows by external_id and skips them.
Re-running is safe.
"""
import os
import sys
import time
import json
import ssl
import urllib.request
import urllib.parse
import urllib.error

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("Missing psycopg2. Install with:")
    print("  pip3 install psycopg2-binary --break-system-packages")
    sys.exit(1)

# SSL certificate handling — macOS Python often ships without a configured CA bundle.
# Use certifi if available; otherwise fall back to default context.
try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    print("Note: 'certifi' not installed. Install with:")
    print("  pip3 install certifi --break-system-packages")
    print("Falling back to system default SSL context.")
    SSL_CONTEXT = ssl.create_default_context()


# -------------------- CONFIG --------------------
AIRTABLE_TOKEN = os.environ.get("AIRTABLE_TOKEN")
NEON_URL       = os.environ.get("NEON_URL")
BASE_ID        = "appcS9K0FZK2DIPbZ"

if not AIRTABLE_TOKEN:
    print("ERROR: set AIRTABLE_TOKEN in your environment")
    print("  export AIRTABLE_TOKEN=patXXXXX...")
    sys.exit(1)
if not NEON_URL:
    print("ERROR: set NEON_URL in your environment")
    print("  export NEON_URL='postgresql://neondb_owner:...'")
    sys.exit(1)

# Airtable table IDs (from list_tables_for_base)
TABLES = {
    "sources":   "tblej2UC5cGMmHTly",
    "molecules": "tbl092tBNBbGQPeXy",
    "odours":    "tblrRH4AK4MsersdC",
    "experts":   "tblSr0rOzxJePEp0U",
    "claims":    "tblR4j2iVOROSAPgO",
}

# Field ID -> Postgres column for each table.
SOURCE_FIELDS = {
    "fld1O6mzAQuy4eOnn": "name",
    "fldEbWPYtI2frFi4L": "year",
    "fldmRB6OKCMNBrnSD": "venue",
    "fldnG7DEp8uBO8z3P": "url",
    "fld2MMZaZs66ggjoU": "authors",
    "fldtKwxrAhE1KzmE7": "search_query",
    "fldKZTVkc9bfc7lFk": "citation_count",
    "fld34RaqHHeCJcDfo": "top_keywords",
    "fldHRIuK4IoP65AUC": "trust_tier",
    "fldOnqY3o0ylRLPgO": "external_key",
}
SOURCE_LINK_FIELDS = {
    "fldewlJMs2ZvGAv5P": "claims",     # source -> claims
    "fldxKnJjGhufTEfU9": "molecules",  # source -> molecules
}

MOLECULE_FIELDS = {
    "fldAm9xTbV6DgLbTN": "name",
    "fldEYv2oAGelGMQPp": "category",
    "fldQNX2Itk8zGtiO1": "taste",
    "fldqaY21Zcn7C0eUR": "use_notes",
    "fldEJemSt5064skwM": "melting_point",
    "fldxwN4wO4YoPFMrP": "water_solubility",
    "fldDfy9cf6EQIVKxp": "compound_id",
    "fldEgJ0sxXSHhlud8": "odour_source_url",
    "fldt2LeNKxkSrPNM4": "external_key",
    # aliases handled specially (multiline -> TEXT[])
}
MOLECULE_LINK_FIELDS = {
    "fldZXPVf4fFffnCW1": "sources",
    "fldHqAlEQhab4Jy7y": "claims",
    "fldWf8hoek8asEg44": "odours",
}

ODOUR_FIELDS = {
    "fldHEhjNZdoDv7dSZ": "name",
    "fld9t21kPTlwY70l8": "odour_category",
}
ODOUR_LINK_FIELDS = {
    "fld6o2rH0jc7jWRwd": "molecules",
}

CLAIM_FIELDS = {
    "fldsj8xbrnJEaVunb": "claim_text",
    "fldhAbLvMHoTMGp62": "evidence_snippet",
    "fldmhZMaodnzqqGHc": "confidence",
    "fldn5nVKKevMrNK3D": "external_key",
    # stance handled specially (singleSelect -> ENUM)
    # Topic handled specially (multipleSelects -> claim_topics rows)
}
CLAIM_LINK_FIELDS = {
    "fldBt3sHXWauNC5tU": "sources",
    "fldaNR4VUpsQruyp1": "molecules",
}

EXPERT_FIELDS = {
    "fldRnZyFrNsqQkDEr": "name",
    "fldxLZGgtGkCziPFA": "affiliation",
    "fldRWlCMBIsdonoU2": "country",
    "fld5Aq61uimgyVMeK": "relevance_score",
    "fldE24TDMc8GCxcQL": "h_index",
    "fldSqUbbQa0lXl16P": "total_papers",
    "fldAnf9rwBkwNjbbJ": "email",
    "fldq3fCfYMaClhhrG": "orcid",
    "fldJ2vtcVxg8c2awx": "key_research",
    "fldoGXunqDohbi4m7": "keywords",
    "fldWhgWPDd6ryKCbq": "linkedin_url",
    "fldNEXmNzH2fMbJAX": "knowledge_gaps",
    "fldQJDzLi85nRMpSv": "openalex_id",
    # research_field handled specially (singleSelect -> ENUM)
    # outreach_status handled specially (singleSelect -> ENUM, with mapping)
    # org_type handled specially (Expert Type singleSelect -> ENUM)
}
EXPERT_LINK_FIELDS = {
    "fldoC28JP8NVYK4yL": "experts",  # related researchers
}

# Outreach status normalization
OUTREACH_MAP = {
    "auto-discovered":     "auto_discovered",
    "shortlisted":         "shortlisted",
    "outreach sent":       "outreach_sent",
    "replied":             "replied",
    "meeting scheduled":   "meeting_scheduled",
    "advisor":             "advisor",
    "not a fit":           "not_a_fit",
    "not contacted":       "not_contacted",
}

# Expert org type
ORG_TYPE_MAP = {
    "ngo":       "ngo_gov",
    "ngo/gov":   "ngo_gov",
    "academic":  "academy",
    "academy":   "academy",
    "industry":  "company",
    "company":   "company",
    "culinary":  "culinary",
}

# Research field normalization (loose match)
def normalize_research_field(value):
    if not value: return None
    v = value.lower().strip()
    mapping = {
        "flavor chemistry":      "flavor_chemistry",
        "flavour chemistry":     "flavor_chemistry",
        "meat science":          "meat_science",
        "food science":          "food_science",
        "analytical chemistry":  "analytical_chemistry",
        "sensory science":       "sensory_science",
        "fermentation":          "fermentation",
        "plant protein":         "plant_protein",
        "cell culture":          "cell_culture",
        "culinary":              "culinary",
    }
    return mapping.get(v, "other")


# -------------------- AIRTABLE FETCH --------------------
def fetch_airtable_table(table_id, base_id=BASE_ID):
    """Paginates through every record in an Airtable table. Returns list of records with id + fields."""
    url = f"https://api.airtable.com/v0/{base_id}/{table_id}"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}"}
    all_records = []
    offset = None
    while True:
        params = {"pageSize": 100, "returnFieldsByFieldId": "true"}
        if offset: params["offset"] = offset
        full = url + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(full, headers=headers)
        try:
            with urllib.request.urlopen(req, context=SSL_CONTEXT) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            print(f"  HTTP {e.code}: {e.read().decode()}")
            raise
        all_records.extend(data["records"])
        offset = data.get("offset")
        if not offset: break
        time.sleep(0.2)  # gentle on rate limits
    return all_records


# -------------------- MAIN --------------------
def main():
    print("Connecting to Neon...")
    conn = psycopg2.connect(NEON_URL)
    conn.autocommit = False
    cur = conn.cursor()

    # ============================================================
    # STAGE 1: main tables (Sources, Molecules, Odours, Claims, Experts)
    # ============================================================

    # ---- Sources ----
    print("\n[1/5] Fetching Sources from Airtable...")
    sources = fetch_airtable_table(TABLES["sources"])
    print(f"  Got {len(sources)} sources. Inserting into Postgres...")
    for r in sources:
        f = r["fields"]
        row = {col: f.get(field_id) for field_id, col in SOURCE_FIELDS.items()}
        cur.execute("""
            INSERT INTO sources (external_id, name, year, venue, url, authors, search_query,
                                 citation_count, top_keywords, trust_tier, external_key)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (external_id) DO NOTHING
        """, (
            r["id"], row["name"], row["year"], row["venue"], row["url"],
            row["authors"], row["search_query"], row["citation_count"],
            row["top_keywords"], row["trust_tier"], row["external_key"],
        ))
    conn.commit()
    print(f"  Inserted {len(sources)} sources.")

    # ---- Molecules ----
    print("\n[2/5] Fetching Molecules from Airtable...")
    molecules = fetch_airtable_table(TABLES["molecules"])
    print(f"  Got {len(molecules)} molecules. Inserting into Postgres...")
    for r in molecules:
        f = r["fields"]
        row = {col: f.get(field_id) for field_id, col in MOLECULE_FIELDS.items()}
        # aliases: multilineText -> TEXT[]
        aliases_raw = f.get("fld2ozz7RBXPBAJlC")
        aliases = [a.strip() for a in aliases_raw.splitlines() if a.strip()] if aliases_raw else None
        cur.execute("""
            INSERT INTO molecules (external_id, name, category, taste, use_notes, melting_point,
                                   water_solubility, compound_id, odour_source_url, external_key, aliases)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (external_id) DO NOTHING
        """, (
            r["id"], row["name"], row["category"], row["taste"], row["use_notes"],
            row["melting_point"], row["water_solubility"], row["compound_id"],
            row["odour_source_url"], row["external_key"], aliases,
        ))
    conn.commit()
    print(f"  Inserted {len(molecules)} molecules.")

    # ---- Odours ----
    print("\n[3/5] Fetching Odours from Airtable...")
    odours = fetch_airtable_table(TABLES["odours"])
    print(f"  Got {len(odours)} odours. Inserting into Postgres...")
    for r in odours:
        f = r["fields"]
        row = {col: f.get(field_id) for field_id, col in ODOUR_FIELDS.items()}
        cur.execute("""
            INSERT INTO odours (external_id, name, odour_category)
            VALUES (%s, %s, %s)
            ON CONFLICT (external_id) DO NOTHING
        """, (r["id"], row["name"], row["odour_category"]))
    conn.commit()
    print(f"  Inserted {len(odours)} odours.")

    # ---- Claims ----
    print("\n[4/5] Fetching Claims from Airtable...")
    claims = fetch_airtable_table(TABLES["claims"])
    print(f"  Got {len(claims)} claims. Inserting into Postgres...")
    for r in claims:
        f = r["fields"]
        row = {col: f.get(field_id) for field_id, col in CLAIM_FIELDS.items()}
        # stance: singleSelect dict -> str
        stance_raw = f.get("fldsd4OjIhEc1XlaW")
        stance = stance_raw["name"] if isinstance(stance_raw, dict) else (stance_raw or "neutral")
        stance = stance.lower()
        cur.execute("""
            INSERT INTO claims (external_id, claim_text, stance, confidence, evidence_snippet, external_key)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (external_id) DO NOTHING
        """, (
            r["id"], row["claim_text"], stance, row["confidence"],
            row["evidence_snippet"], row["external_key"],
        ))
        # claim_topics from multipleSelects 'Topic'
        topics = f.get("fldjCZpCHbAzy2Ksi")
        if topics:
            # Get the new claim id
            cur.execute("SELECT id FROM claims WHERE external_id = %s", (r["id"],))
            claim_id_row = cur.fetchone()
            if claim_id_row:
                claim_id = claim_id_row[0]
                for t in topics:
                    name = t["name"] if isinstance(t, dict) else t
                    cur.execute("""
                        INSERT INTO claim_topics (claim_id, topic) VALUES (%s, %s)
                        ON CONFLICT DO NOTHING
                    """, (claim_id, name))
    conn.commit()
    print(f"  Inserted {len(claims)} claims (+ topics).")

    # ---- Experts ----
    print("\n[5/5] Fetching Experts from Airtable...")
    experts = fetch_airtable_table(TABLES["experts"])
    print(f"  Got {len(experts)} experts. Inserting into Postgres...")
    for r in experts:
        f = r["fields"]
        row = {col: f.get(field_id) for field_id, col in EXPERT_FIELDS.items()}
        # research_field
        rf_raw = f.get("fldlMWf6AOm7ZfZC5")
        rf_name = rf_raw["name"] if isinstance(rf_raw, dict) else rf_raw
        research_field = normalize_research_field(rf_name)
        # outreach_status
        os_raw = f.get("fldf5EEkgQQumjga8")
        os_name = (os_raw["name"] if isinstance(os_raw, dict) else os_raw) or "Not contacted"
        outreach = OUTREACH_MAP.get(os_name.lower().strip(), "not_contacted")
        # org_type (Expert Type)
        et_raw = f.get("fldEsVPMgfhTVJcXV")
        et_name = (et_raw["name"] if isinstance(et_raw, dict) else et_raw) or ""
        org_type = ORG_TYPE_MAP.get(et_name.lower().strip()) or None

        cur.execute("""
            INSERT INTO experts (external_id, name, affiliation, country, relevance_score,
                                 h_index, total_papers, email, orcid, key_research, keywords,
                                 linkedin_url, knowledge_gaps, openalex_id,
                                 research_field, outreach_status, org_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (external_id) DO NOTHING
        """, (
            r["id"], row["name"], row["affiliation"], row["country"], row["relevance_score"],
            row["h_index"], row["total_papers"], row["email"], row["orcid"], row["key_research"],
            row["keywords"], row["linkedin_url"], row["knowledge_gaps"], row["openalex_id"],
            research_field, outreach, org_type,
        ))
    conn.commit()
    print(f"  Inserted {len(experts)} experts.")

    # ============================================================
    # STAGE 2: join tables (resolve linked records via external_id)
    # ============================================================
    print("\n--- Stage 2: linked records ---")

    def resolve_link(link_field, src_records, src_table, link_target_table, join_table_sql):
        """Walk each source record, look up Airtable rec IDs in link_field, INSERT into join."""
        n = 0
        for r in src_records:
            f = r["fields"]
            links = f.get(link_field) or []
            if not links: continue
            for linked in links:
                linked_id = linked["id"] if isinstance(linked, dict) else linked
                cur.execute(join_table_sql, (r["id"], linked_id))
                n += cur.rowcount
        return n

    # source -> claims
    n = resolve_link("fldewlJMs2ZvGAv5P", sources, "sources", "claims", """
        INSERT INTO claim_sources (claim_id, source_id)
        SELECT c.id, s.id
        FROM sources s, claims c
        WHERE s.external_id = %s AND c.external_id = %s
        ON CONFLICT DO NOTHING
    """)
    print(f"  source->claims:   {n} rows")

    # source -> molecules
    n = resolve_link("fldxKnJjGhufTEfU9", sources, "sources", "molecules", """
        INSERT INTO source_molecules (source_id, molecule_id)
        SELECT s.id, m.id
        FROM sources s, molecules m
        WHERE s.external_id = %s AND m.external_id = %s
        ON CONFLICT DO NOTHING
    """)
    print(f"  source->molecules: {n} rows")

    # molecule -> odours
    n = resolve_link("fldWf8hoek8asEg44", molecules, "molecules", "odours", """
        INSERT INTO molecule_odours (molecule_id, odour_id)
        SELECT m.id, o.id
        FROM molecules m, odours o
        WHERE m.external_id = %s AND o.external_id = %s
        ON CONFLICT DO NOTHING
    """)
    print(f"  molecule->odours: {n} rows")

    # claim -> sources & claim -> molecules (also derivable from source side, but we cover both)
    n = resolve_link("fldBt3sHXWauNC5tU", claims, "claims", "sources", """
        INSERT INTO claim_sources (claim_id, source_id)
        SELECT c.id, s.id
        FROM claims c, sources s
        WHERE c.external_id = %s AND s.external_id = %s
        ON CONFLICT DO NOTHING
    """)
    print(f"  claim->sources:   {n} rows")

    n = resolve_link("fldaNR4VUpsQruyp1", claims, "claims", "molecules", """
        INSERT INTO claim_molecules (claim_id, molecule_id)
        SELECT c.id, m.id
        FROM claims c, molecules m
        WHERE c.external_id = %s AND m.external_id = %s
        ON CONFLICT DO NOTHING
    """)
    print(f"  claim->molecules: {n} rows")

    # expert -> related experts
    n = 0
    for r in experts:
        f = r["fields"]
        related = f.get("fldoC28JP8NVYK4yL") or []
        for linked in related:
            linked_id = linked["id"] if isinstance(linked, dict) else linked
            cur.execute("""
                INSERT INTO expert_relations (expert_a_id, expert_b_id, relation_type)
                SELECT a.id, b.id, 'related'
                FROM experts a, experts b
                WHERE a.external_id = %s AND b.external_id = %s AND a.id <> b.id
                ON CONFLICT DO NOTHING
            """, (r["id"], linked_id))
            n += cur.rowcount
    print(f"  expert->expert:   {n} rows")

    conn.commit()

    # ============================================================
    # STAGE 3: verification
    # ============================================================
    print("\n--- Verification ---")
    for tbl in ["sources", "molecules", "odours", "claims", "experts",
                "claim_sources", "claim_molecules", "source_molecules",
                "molecule_odours", "claim_topics", "expert_relations"]:
        cur.execute(f"SELECT COUNT(*) FROM {tbl}")
        n = cur.fetchone()[0]
        print(f"  {tbl:<22} {n:>6} rows")

    cur.close()
    conn.close()
    print("\nMigration complete.")


if __name__ == "__main__":
    main()
