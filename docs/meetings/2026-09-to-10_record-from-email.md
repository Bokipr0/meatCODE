<!-- Last updated: 2026-10-11 · Advisory · back-filled from Gmail (read-only) because Wispr Flow has no recorded meetings after 2026-08-01. Facts only, each with date + thread subject. Anything only said aloud in a meeting is NOT here. -->

# Sep–Oct 2026 — what happened, reconstructed from email

**Coverage note:** Wispr Flow returned **no recorded meetings since 2026-08-01**, so this file is built
from Gmail threads only. Calendar invites prove a meeting was scheduled, not what was said. Gaps are
marked *unclear*. Lior: add anything decided verbally.

## Publisher rights — "Data paywall – Summarized (Meatcode)" (2026-08-06 → 09-10)
- **2026-08-06 · Daniel:** roughly 200 corpus papers are paywalled; estimated ~$30 each.
- **2026-09-03 · Omer Brandes (legal):** of 543 free-to-read articles — 335 CC BY, 39 CC BY-NC, 124 CC BY-NC-ND, 26 bronze, 11 no licence, 14 unidentified. Elsevier and Wiley terms forbid AI use without a licence.
- **2026-09-07 · Daniel (decision):** extract facts and relationships with provenance; do not store, reproduce or share full text; answers cite and link to originals; MeatCODE stays open and non-commercial.
- **2026-09-10 · Omer:** start with an informal exploratory enquiry to publishers, not a formal licence request — "you can't un-ask". For paywalled content, follow the publishers' rules.
- **Open:** whether to approach publishers at all (Asana "Legal – publisher rights", Daniel, overdue 2026-10-08).

## Simulator + Atlas — "Updates from Thursday: reaction simulator and AKA Foods' Atlas" (2026-09-14 → 10-11)
- **2026-09-14 · Daniel:** met Pablo (Maillard simulator) and AKA Foods (Atlas). Agreed a joint October meeting with WUR to validate the simulator; AKA Foods offered Atlas sandbox access.
- **2026-10-11 · Lior:** asked for news on sandbox access.
- **2026-10-11 · Daniel:** two new threads — "MeatCODE: introduction and simulator validation with WUR" (Pablo, Prof. Vincenzo Fogliano, Bei Wang; 45-min meeting to test the simulator on Bei's data) and "Atlas and MeatCODE Oracle: follow-up and pilot planning" (AKA Foods; 30-min call). Both asking for times in the next two weeks.

## Knowledge-graph architecture — "Fwd: knowledge graph" (2026-09-14 → 09-22) and follow-ups
- **2026-09-14 · Prof. Yoav Ram → Daniel** (two emails): GROBID → chunk + embed (SPECTER2 for papers; text-embedding-3-large or BGE-M3 for chunks) → LLM relation extraction (LightRAG) with source passage on every edge → graph + vector store → graph-aware retrieval. Embeddings only *propose* links. Estimate: 10–20M embedding tokens for full text on ~1,000 papers; OpenAI Batch halves cost.
- **2026-09-22 · Daniel** forwarded to Lior and Yochai. **Yochai** flagged the conflict with publisher limits ("up to a 200-character snippet"), proposed a staged run (abstracts first, full text on 30–50 papers), and asked Daniel whether Ram would do a short paid design review. *No reply from Daniel in the thread.*
- **2026-09-23 → 10-05 · "knowledge graph for MEAT Code":** Matt Hotze (GFI) offered Vanessa for a trial KG task. Daniel: share with Matt and see if he has proposals. *Outcome unclear.*
- **2026-10-04 · Yochai** (capacity pre-call invite, 2026-10-05): questions for Lior — LightRAG or Neo4j? hosted or local model, GPU? do our PDFs parse in GROBID? where do chunks live?
- **2026-10-05 · Lior → Ram** ("MeatCODE — follow-up on LightRAG proposal", cc Daniel, Yochai): adopt the pattern, keep a chemistry-specific schema, stay on Postgres + pgvector; three questions; offered a design review. **No reply as of 2026-10-11.**
- **2026-10-12 13:00 (scheduled):** Yochai meets Ram, Sherman 328, "on Daniel's recommendation"; Lior invited.

## Work plan and capacity
- **2026-09-29 / 10-01 · Asana status (Yochai):** project **At risk**; open load 41 Daniel / 19 Lior / 10 Yochai.
- **2026-09-30 · Yochai (Asana mention):** the knowledge-machine work plan's capacity and labour split needs Lior's review and approval. *Status unclear.*
- **2026-10-01 · Yochai:** shared "Draft – Knowledge machine work plan".
- **2026-10-07 · Yochai:** shared `MeatCODE_Journeys.pptx`.

## Continuity
- **2026-09-20 · Yochai** ("Before the flight – two small MeatCODE requests"): the DB sits only with Lior; asked for credentials or an access copy plus a shared cloud backup, and for Lior to check his Asana statuses. The matching Asana task was closed 2026-09-21. `/api/backup` and `/api/data-backup` (live on prod since 2026-09-21) give anyone with the site password a full backup.

## Science spec — "MeatCODE Science (aka Educational or Research) spec" (2026-10-11)
- **Daniel → Yochai, cc Lior:** spec folder shared; consider recruiting expert curators; Daniel will set a call with Rebecca (MFL data). **Lior to give Rebecca a 10–15 min overview of the MeatCODE architecture.**

## Other
- **2026-10-07:** Yizhou Ma (WUR) accepted Lior's "Yizhou – Follow up (meat code)" invite. Date and content *unclear*.
- **2026-08-31:** Render reported "Blueprint sync failed for meatCODE server". Production has since deployed normally (2026-09-21), so this appears resolved.
- **2026-10-05:** a GitHub classic token "meatcode-deploy" (repo scope) was created on the `Bokipr0` account.
