# How the Oracle Finds Its Answers — a plain-English design decision

_Last updated: 2026-06-30 12:55 UTC · advisory session + Algorithm Expert agent · first version_

**Status:** Draft for review (Lior + Daniel). **Audience:** anyone — no technical background needed.
**Purpose:** decide how the MeatCODE Oracle turns a user's question into a trustworthy, source-backed answer.

---

## In one sentence

We will build the Oracle as **one smart librarian that finds the few best passages and then writes a cited answer from them** — not as a crowd of competing "expert robots" that each read everything and then vote.

---

## The question we're answering

When someone asks the Oracle *"why does my pea-protein burger taste like cardboard?"*, what happens behind the scenes to produce a good, trustworthy answer? There are many ways to build this. This document picks one and explains why.

A helpful picture for the whole document: **think of MeatCODE as a library.**
- The **sources** (papers, patents) are the books.
- The **tags** we put on each source are the labels on the shelves.
- The **AI** is a very well-read writer who will only write using pages we hand it.
- A good answer = handing the writer *the right few pages* and asking it to explain them clearly, with references.

---

## The idea we considered

The proposal was: give every source up to 5 tags; create many specialised "expert robots," each responsible for a field (e.g. a *lipid-oxidation* robot linked to ~50 tags); when a source matches enough of a field's tags, "summon" that field's robot to read it; then have all the summoned robots compare notes and vote on the single best answer.

It's a creative idea, and the instinct behind it is good. But after stress-testing it (I reviewed it, and so did the project's "Algorithm Expert" — independently, we reached the same conclusion), we recommend **keeping the goal and changing the method.**

---

## The verdict

**Keep the goal:** answers should draw on the *right* specialist knowledge, and should stay inside a trustworthy set of sources.
**Change the method:** don't build the crowd-of-robots-that-vote. It's expensive, slow, hard to trust, and doesn't actually answer better. Build one clear pipeline instead.

This isn't caution for its own sake — it's directly in line with the project's stated #1 risk: *building the full vision too early.* The simpler design gets a working, demoable Oracle far sooner.

---

## Why — explained simply

**1. Finding pages and understanding pages are two different jobs.**
The hard part is *finding the right pages*. The proposal uses tags to decide which robot **reads** a source — but that's just a slow, expensive way of doing a search. A good search engine already finds the right pages in a fraction of a second, for a fraction of the cost. Don't hire a robot to do a search's job.

**2. "Enough matching tags" is a shaky way to choose.**
"Summon the robot if a source shares 5 tags" is an arbitrary line. With only 5 tags per source, a genuinely useful source with 4 matches gets ignored, while an off-topic one that happens to share 5 generic tags ("meat," "aroma," "GC-MS") triggers a whole robot. And the best sources sit *between* fields (e.g. lipid **and** Maillard), so almost everything ends up summoning several robots anyway — which defeats the "specialist" idea.

**3. A vote between identical robots isn't a real vote.**
Every "expert robot" is the *same* underlying AI wearing a different hat. If it misreads something, **all** the robots misread it the same way. So when they "agree," that agreement is meaningless — it's one opinion echoed five times, not five independent checks. Voting only helps when the voters can fail independently. These can't.

**4. It's slow, costly, and unpredictable — bad for demos.**
Every question would fire off many AI calls and wait for the slowest one. Worse, the answer could change from one run to the next (different robots summoned → different vote). That's exactly what you don't want when showing stakeholders, and it makes it nearly impossible to measure whether a change made the Oracle better or worse.

---

## What we keep from your idea

Two parts are genuinely valuable and we're keeping them:

- **The tags.** Up to a few strong tags per source is excellent — but we use them as **shelf labels to narrow the search**, not as a trigger to summon robots.
- **The "expert lens."** Answering *as a lipid-oxidation specialist* really does improve quality. We keep it — but as a **hat the one writer puts on** for that question, chosen automatically, not as a separate robot running in the background. Same benefit, a fraction of the cost.

---

## How the Oracle will actually work (four simple steps)

For each question, one clean pipeline:

1. **Understand the question.** A quick step reads the question and predicts which *tags/fields* it's about (e.g. "off-flavour, lipid oxidation, sensory: metallic"). This decides *where in the library to look* — it does **not** summon anyone.

2. **Find the best passages.** Search the library three complementary ways at once — by **meaning** (modern "semantic" search), by **keywords** (the exact-word search we already have), and **narrowed by the tags** from step 1 — and combine the results. This is where the real work happens.

3. **Pick the top few.** Take the ~30 most promising passages and do a quick quality check to keep only the best ~6. (This single step improves answers more than any robot-crowd ever would.)

4. **Write the answer.** Hand those ~6 passages to the AI, ask it to answer **using only those passages**, wearing the right specialist "hat," with **references** to each source — and, crucially, to say *"the evidence doesn't cover this"* when it doesn't. No made-up answers.

If a question genuinely spans several fields ("compare lipid-oxidation vs. Maillard contributions to warmed-over flavour"), we handle it by **breaking it into smaller questions, answering each, then combining** — one writer, step by step — rather than a crowd voting. We add that only later, and only if we see real questions that need it.

---

## How we make the answers trustworthy ("authenticating" the data)

This was part of your original concern, and it's the right one. Trust doesn't come from robots agreeing — it comes from **provenance**: every answer is built only from real sources and shows its references; each source carries an **evidence-strength** label (strong / moderate / preliminary); only sources with enough text to be searched can be cited; and a human review step can approve borderline material. That's how we make the Oracle *defensible* to expert reviewers.

---

## The plan: this month vs. later

**This month (enough for a credible demo):**
- Prepare the sources for meaning-based search (a one-time setup on the database).
- Build the four-step pipeline above: understand → find → pick top few → write with references.
- Create a **test set of 30–50 real R&D questions with the correct sources noted by hand**, so we can measure the Oracle objectively and catch regressions. (Most teams skip this and regret it.)

**Later (only if the test set shows we need it):**
- Smarter question-understanding that learns from real usage.
- A stronger "pick the best few" step.
- The break-it-into-smaller-questions mode for genuinely multi-field questions.

**Probably never:** the crowd-of-expert-robots-that-vote. It's the textbook example of the over-building our own risk register warns against.

---

## Mini-glossary (plain definitions)

- **Source / passage** — a paper (or a chunk of one) in our library.
- **Tag** — a label on a source (its topic, method, product, etc.), used to narrow searches.
- **Semantic search / "embeddings"** — searching by *meaning* rather than exact words, so "beany off-note" can find a paper about "hexanal in pea protein" even without matching words.
- **RAG (retrieval-augmented generation)** — the whole approach of *first find real sources, then let the AI answer from them* (instead of answering from memory).
- **Reranking** — a quick second look that reorders search results to put the truly best few on top.
- **Persona / "expert hat"** — a set of instructions that makes the one AI answer as a specialist in a given field.
