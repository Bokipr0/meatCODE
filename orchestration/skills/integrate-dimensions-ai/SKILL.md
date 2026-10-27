---
name: integrate-dimensions-ai
description: |
  Integrate Dimensions.ai as an additional literature data source into a Flavor Intelligence-style
  multi-source academic pipeline (alongside OpenAlex, Semantic Scholar, PubMed, CrossRef, SerpAPI/Google
  Scholar). Use this skill whenever the user mentions Dimensions.ai, the Dimensions DSL API,
  scientometric API access, the Digital Science research database, or wants to add a sixth (or any new)
  academic literature source to their pipeline.py. Also use when the user wants to enrich their
  bibliographic data with grants linkage, Altmetric scores, Concepts tagging, patents, or clinical
  trials — features Dimensions provides that the other five sources do not. The skill branches on
  whether the user already has API access: if yes, it walks through fetcher implementation and
  registration; if no, it drafts a Scientometric Research Program application. Don't skip this skill
  just because the user already has a working pipeline — the integration pattern + auth flow is
  non-obvious and gets reused for other future sources.
---

# Integrate Dimensions.ai into the Flavor Intelligence pipeline

This skill adds Dimensions.ai as a new fetcher in a multi-source literature pipeline that follows the pattern in `pipeline.py` — each source is a function `fetch_<name>(keyword, state, branch)` returning a list of paper dicts, registered in the `FETCHERS` dict.

## Why Dimensions over what we already have

The existing five sources (OpenAlex, Semantic Scholar, PubMed, CrossRef, SerpAPI) overlap heavily on raw publication coverage — adding Dimensions does NOT meaningfully expand the set of papers found. Its value is in the **enrichment fields** the others don't expose:

- **Grants linkage** — every paper is connected to the grants that funded it (funder + award amount). Lets you ask "which labs are well-funded for Strecker degradation work?"
- **Altmetric scores** — social, news, and policy attention scores attached to each paper. Surfaces papers with industry/policy traction beyond raw citations.
- **Concepts tagging** — machine-derived semantic tags. Can be used as a pre-filter so the Claude topic classifier only runs on papers Dimensions already pre-tagged with a relevant concept (saves API spend).
- **Patents + clinical trials** — same DSL queries return these alongside publications. Surfaces industry R&D activity that's invisible in academic-only sources.
- **Grey literature** — better indexing of policy briefs, government reports, NGO publications. Useful for NGO-track expert discovery.

State this trade-off explicitly to the user when proposing the integration so they're not surprised when "new papers added" is modest.

## Step 1 — Confirm access status

Ask the user up-front: "Do you already have Dimensions API access (an API key or institutional credentials), or is this a fresh integration?" Three possibilities, with very different paths:

- **Has an API key from the Scientometric Research Program** → go to Step 2A.
- **Has institutional access** (university library subscribes) → go to Step 2B. They'll need to retrieve a username + password from their library, then use `POST /auth/login` to exchange for a temporary token.
- **No access yet** → go to Step 3 (draft the scientometric program application).

If the user is uncertain, ask whether their institution has a Dimensions subscription. For Israeli universities, Tel Aviv University and the Hebrew University have had institutional access historically; the librarian can confirm in a few minutes. The free Scientometric Research Program is the most common path for GFI-adjacent researchers and takes a few days to a week from application to approval.

## Step 2A — Integration with an existing API key

When the user already has an API key, the integration is small and well-defined:

1. **Copy `scripts/fetch_dimensions.py`** from this skill into the user's project folder (the one with `pipeline.py`). It's a complete drop-in implementation that mirrors the shape of the existing fetchers (`fetch_openalex`, `fetch_semantic_scholar`, etc.) — same signature, same paper-dict output, same pagination + rate-limit handling, same cursor-state pattern.

2. **Register it in `pipeline.py`** by adding two lines:
   ```python
   from fetch_dimensions import fetch_dimensions   # near the top imports
   ...
   FETCHERS = {
       "openalex":   fetch_openalex,
       "s2":         fetch_semantic_scholar,
       "pubmed":     fetch_pubmed,
       "crossref":   fetch_crossref,
       "serpapi":    fetch_serpapi,
       "dimensions": fetch_dimensions,   # ← add this line
   }
   ```

3. **Add `DIMENSIONS_API_KEY` to `.env`**. The function reads it via `os.environ["DIMENSIONS_API_KEY"]`. Also add a `DIMENSIONS_AUTH_TYPE` set to either `"api_key"` (the Scientometric Research Program model) or `"login"` (institutional username/password). The function reads both and branches.

4. **Verify** by running the pipeline against one keyword with `--databases dimensions` only:
   ```bash
   python pipeline.py --keywords keywords_topics.json --databases dimensions --workers 1 \
                      --max-pages 1 --per-page 5
   ```
   You should see a handful of papers come back with `db_source = "dimensions"` and additional fields under a `dimensions_meta` key (grants, altmetric, concepts).

5. **Update the topic-driven sleep rate** in `pipeline.py`'s `sleep_db()` dict — Dimensions allows ~30 requests/minute on the standard tier, so use `"dimensions": 2.0` seconds between paginated calls.

## Step 2B — Integration via institutional login

The auth flow is slightly different: instead of an API key, the user POSTs username+password to `https://app.dimensions.ai/api/auth.json` and gets back a short-lived bearer token (valid ~1 hour). The fetcher in `scripts/fetch_dimensions.py` already supports this — set `DIMENSIONS_AUTH_TYPE=login` and provide `DIMENSIONS_USERNAME` + `DIMENSIONS_PASSWORD` in `.env`. The function caches the token in memory and refreshes when it expires.

Otherwise, identical to Step 2A — drop in the file, register it, run a verification fetch.

## Step 3 — Apply for the Scientometric Research Program

If the user has no access yet, the path is to apply for the free non-commercial program. It's targeted at academic scientometric research, which a flavor-chemistry literature mapping project qualifies for cleanly.

1. **Read `references/scientometric_application.md`** — a ready-to-edit application template tuned for a flavor-research use case. It's three short paragraphs covering: (a) research aims, (b) intended use of the data, (c) institutional affiliation and PI/supervisor.

2. **Personalize the template** with the user's actual research focus, institution, and supervisor. The application reviewers care most about: legitimate non-commercial research aims, clear methodology, institutional backing.

3. **Submit at** `https://dimensions.ai/scientometric-research-program`. Approval typically arrives in 3-7 business days.

4. **In the meantime**, the existing five sources continue to work fine. There's no blocker.

## Step 4 — DSL query semantics

The integration uses the Dimensions Search Language (DSL) — a SQL-like query language that's more expressive than the REST query strings of OpenAlex/CrossRef. The fetcher already templates the right query, but if the user wants to customize search behavior, read `references/dimensions_dsl.md` for the cheat sheet (field names, filters, return clauses, pagination).

Common customization the user might ask about:

- **Date filtering** — append `where year >= 2015` to the DSL query.
- **Field-of-research filter** — `where category_for.name in ["Food Science"]` narrows results.
- **Return additional fields** — extend the `return publications [...]` clause with fields like `funders`, `grants`, `altmetric`, `concepts`, `category_for`.

## Step 5 — Map Dimensions fields into the pipeline's record shape

The fetcher already does this mapping, but document the choices so the user understands what's preserved:

| Dimensions field      | Pipeline record key   | Notes |
|-----------------------|-----------------------|-------|
| `id`                  | `id`                  | Used as a fallback when no DOI |
| `doi`                 | `id` (preferred)      | Same uid pattern as other sources |
| `title`               | `title`               | |
| `year`                | `year`                | |
| `journal.title`       | `venue`               | |
| `authors[].full_name` | `authors`             | |
| `abstract`            | `abstract`            | |
| `times_cited`         | `citations`           | |
| `concepts`            | `concepts`            | Maps cleanly to existing concepts field |
| `altmetric`           | `dimensions_meta.altmetric`  | Stored as sidecar, not pushed to Airtable directly |
| `funders` / `grants`  | `dimensions_meta.grants`     | Sidecar — surfaces in dashboard later |

The `dimensions_meta` sidecar is intentional — it doesn't collide with the existing extraction record shape, and the pipeline's downstream code (Claude extraction, composite score, Layer E write) ignores unknown keys. The Streamlit dashboard or sync_layer_e_to_neon.py can opt into rendering or persisting the sidecar fields later.

## Step 6 — Topic-classifier interaction

If the user's pipeline has the Claude topic classifier wired up (see `pipeline.py` — `claude_classify_topics`), Dimensions' `concepts` field can be used as a cheap pre-filter. The fetcher already populates `paper["dimensions_meta"]["concepts"]` (when present). To use it as a pre-filter, add this check in the pipeline worker before calling the Claude classifier:

```python
dim_concepts = (paper.get("dimensions_meta") or {}).get("concepts") or []
if paper.get("db") == "dimensions" and dim_concepts:
    # cheap heuristic: skip if no dimensions concept overlaps with our leaf-topic names
    leaf_names = {t["name"].lower() for t in _LEAF_TOPICS}
    if not any(c["concept"].lower() in leaf_names for c in dim_concepts):
        # No Dimensions concept matches our topic tree — skip Claude classifier
        extracted["relevant"] = False
        continue
```

This can save 30-50% of Claude classifier calls on Dimensions papers. The pre-filter is OPTIONAL — the Claude classifier handles unfiltered input correctly, it's just slower.

## Quick reference

Files bundled with this skill:

- `scripts/fetch_dimensions.py` — the drop-in fetcher function. Copy into the project folder next to `pipeline.py`.
- `references/scientometric_application.md` — application template for the free non-commercial program.
- `references/dimensions_dsl.md` — DSL query language cheat sheet.

## What this skill does NOT do

- It does not provision a Dimensions account. The user does that.
- It does not configure access tier upgrades or institutional license negotiation. The user does that.
- It does not migrate existing data. New Dimensions-fetched papers flow into the existing pipeline naturally; no migration needed.
