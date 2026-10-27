_Last updated: 2026-08-15 · Advisory · decision record — knowledge graph architecture + what to do next_

# Decision record: the knowledge graph — what we built, what's blocking it, what's next

## What we built

**Two graphs, not one:**

1. **The molecule graph** — deep chemistry. Built from the Meaty Volatile Library backbone: molecules
   with their classes, formation pathways, and aroma descriptors, connected to each other. This side
   is genuinely good — you can already walk "sulfur compounds, formed by Maillard, that smell roasted"
   and get a correct, navigable answer.
2. **The paper graph** — the literature. Sources connected to topics, tags, and experts.

Both are **projected straight out of Neon Postgres** (`kg/build_kg.py` → `kg_data.json` →
`kg_explorer.html`, now embedded as a Dev Area screen). **There is no graph database, and that's
deliberate:** the graph is a *view* of data we already govern in Postgres, rebuilt in seconds by
re-running one script. A Neo4j-style setup would add a fourth data home to keep in sync — exactly the
smearing problem the three-homes model exists to prevent. Nothing we've hit so far needs one.

## The bottleneck: the bridge

The two graphs are only useful **together** — "show me the papers about the chemistry I'm looking at."
That connection is the bridge (`source_molecules`), and it's starving:

- **Curated:** 23 rows. For 818 papers. Essentially nothing.
- **Mined** (name-matching molecule names in titles/abstracts, kept separate with `provenance='mined'`):
  **712 edges** — a 30× improvement, but still only **~13% of molecules** and **~34% of papers** have
  any link at all.
- The test that says it all: the **roasted/nutty query** finds *perfect chemistry* on the molecule
  side and **0 papers** on the other side. The graph knows the answer; it can't cite it.

So the KG's limiting factor is not graph tech, not visualization, not schema — it's **bridge density**.

## The useful coincidence: claim extraction IS bridge densification

We've long wanted claim extraction ("paper X reports that molecule Y contributes aroma Z under
condition W") for the Oracle. Extracting a claim *necessarily* links a paper to a molecule — every
claim is a bridge edge **plus** the evidence on it. They are the same unit of work, so we shouldn't
run them as two projects. One LLM pass over a paper yields: bridge edges (typed, with provenance),
claim records for retrieval (the Algorithm lane is already surfacing claims into `/api/ask`), and
raw material for the white-space map (lane 5 / A5's actual purpose).

## The prerequisite: canonical molecule IDs

Extraction is only as good as its landing spots. "2-acetylpyrazine", "2-Acetyl pyrazine" and a CAS
number must resolve to **one** molecule row, or mined/extracted edges scatter across duplicates and
the density numbers lie. The Data lane's current work — CAS backfill from the MVL, `is_junk` flagging,
the new identity columns — is therefore **not a side quest; it's step zero of the bridge.** Sequence:
canonical IDs first, extraction second.

## Recommendation

**Next move: densify the bridge via claim extraction on ~50 papers** (highest-relevance,
already-tagged ones first), landing on canonical molecule IDs, writing edges with
`provenance='extracted'` so they're reviewable separately from curated and name-mined ones.

- **Success check:** re-run the roasted/nutty query — it should return papers. Track the two link
  percentages (molecules linked, papers linked) before/after as the KG's health metric.
- **Scope guard:** 50 papers is a validation batch, not a corpus-wide run. If the extracted edges hold
  up under spot-checking (Daniel's review loop), *then* scale.
- **Standing decisions reaffirmed:** no graph database; the KG stays a Postgres projection; the KG
  explorer stays behind the Dev Area flag until the bridge makes it demoable.
