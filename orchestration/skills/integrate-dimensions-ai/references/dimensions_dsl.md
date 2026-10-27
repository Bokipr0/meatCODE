# Dimensions DSL — quick reference

The Dimensions Search Language (DSL) is a SQL-like query language for the `/api/dsl.json` endpoint. More expressive than the REST query strings of OpenAlex / CrossRef. Authoritative docs at https://docs.dimensions.ai/dsl.

## Anatomy of a query

```
search <SOURCE>
  in <SEARCH_FIELD>
  for "<QUERY>"
where <FILTERS>
return <SOURCE> [<FIELDS>]
limit <N>
skip <N>
sort by <FIELD> asc|desc
```

Every clause is optional except `search` and `return`.

## Sources (what to search)

- `publications` — research papers, conference proceedings (your main use case)
- `grants` — funding records
- `patents` — patent records
- `clinical_trials`
- `policy_documents`
- `datasets`
- `researchers` — author records (a parallel surface for the experts repo)

## Search fields (where to look)

For `publications`:
- `title_only` — fastest, narrowest
- `title_abstract_only` — typical choice (used in the default fetcher)
- `full_data` — title + abstract + concepts + author names

## Common filters (where clauses)

```
where year >= 2015
where year in [2018, 2019, 2020, 2021]
where times_cited >= 10
where journal.title in ["Food Chemistry", "Meat Science"]
where category_for.name in ["Food Science"]
where authors.affiliations.country_name = "Netherlands"
where funders.name = "European Research Council"
```

Filters compose with `and` / `or`. String values quoted; numeric literals not.

## Return clauses (what to get back)

The return clause is space-delimited or `+`-delimited. Useful fields for the flavor pipeline:

```
return publications [
    id + doi + title + year + journal + authors + abstract +
    times_cited + altmetric + concepts + category_for + funders +
    grants + clinical_trials + patents
]
```

Note that `grants`, `clinical_trials`, and `patents` returned alongside a publication are LINKED records (the patents and trials that cite or are cited by this paper). To fetch them directly, switch the `search` source.

## Pagination

```
limit 100   # max per response
skip 0      # offset
```

DSL allows up to `limit 1000` but smaller pages are friendlier for rate-limits and easier to debug. The fetcher in this skill uses `limit 25` by default (driven by the `PER_PAGE` env var that the rest of the pipeline shares).

## Sorting

```
sort by times_cited desc
sort by year desc
sort by altmetric desc
```

Default sort is "relevance" (Dimensions' opaque scoring) — usually what you want.

## Common pitfalls

- **DSL uses double-quoted strings**. If your query keyword contains a double quote, escape it (`\"`). The fetcher already handles this.
- **`limit` cannot exceed 1000 per response** even if the result set is larger. Use `skip` to paginate.
- **Rate limits**: the standard tier allows ~30 requests/minute. The fetcher in this skill sleeps 2 seconds between paginated calls; if you're hitting 429s, raise this.
- **Token expiry**: bearer tokens last ~1 hour. The fetcher caches and auto-refreshes; you only need to handle this manually if you're calling the DSL endpoint outside the fetcher.

## Example queries (paste-ready)

**Find Maillard-reaction papers in food chemistry journals, sorted by altmetric attention:**

```
search publications
  in title_abstract_only
  for "Maillard reaction meat flavor"
where year >= 2015 and category_for.name in ["Food Science"]
return publications [id + doi + title + year + journal + altmetric + concepts]
sort by altmetric desc
limit 50
```

**Find grants funding cysteine-ribose Maillard research at European institutions:**

```
search grants
  in title_abstract_only
  for "cysteine ribose Maillard"
where authors.affiliations.country_name in ["Netherlands", "Germany", "France"]
return grants [id + title + funder + funding_usd + start_year + investigators]
limit 50
```

**Find patents related to plant-based meat flavor:**

```
search patents
  in title_abstract_only
  for "plant based meat flavor"
where year >= 2018
return patents [id + title + year + assignees + concepts]
limit 100
```
