_Last updated: 2026-07-21 · Advisory · MeatCODE pre-use user questionnaire v1 (values + paper-rating test)_

# MeatCODE — User Values & Paper-Rating Survey (v1)

**Goal:** *before* anyone uses MeatCODE, learn (a) what they value most in a knowledge-based AI research tool, (b) what frustrates them in general LLMs (ChatGPT/Claude/…), (c) what they will **not** compromise on — and run a small blind test where they rate one real, contested paper so we can compare human judgment against the LLM/audit and learn *how a paper should be rated*.

**Design rules:** 9 questions total · ~5 minutes · anonymous · the paper is rated **blind first** (Q6–Q7), then the "it's contested" reveal (Q8) tests trust. This is the source of truth; the Google Form and Typeform versions are built from it.

---

## Intro text (top of the form)

> **Help shape MeatCODE — 5 minutes, before you've ever used it.**
> MeatCODE (a Good Food Institute · GFI Israel initiative) is building an AI research assistant that answers only from real, cited scientific sources. Before we show it to you, we want *your* honest expectations and frustrations with AI research tools today. There are no right answers — and at the end we'll ask you to skim one real paper and rate it. Thank you! 🙏 *(Responses are anonymous and used only to guide what we build.)*

---

## Part A — How you work with AI today (5 questions)

**Q1. Which best describes you?**  *(single choice — for segmenting every other answer)*
- Academic researcher / PI
- Grad student or postdoc
- Flavor / food chemist (industry)
- Alt-meat / food-product R&D
- Data / AI / software
- Other → ___

**Q2. When you use general AI chatbots (ChatGPT, Claude, Gemini…) for scientific or technical questions, what frustrates you most?**  *(select up to 3)*
- It makes things up / hallucinates facts
- I can't verify where the answer came from (no real sources)
- It cites papers that don't exist, or gets them wrong
- Not deep enough in my specific field
- Its knowledge feels outdated
- Answers are generic / surface-level
- It won't admit when it doesn't know
- It blends solid science with weak / blog-level claims

**Q3. In a knowledge-based AI research assistant, which THREE qualities matter most to you?**  *(select exactly 3)*
- Every claim backed by a real, citable source
- Accuracy — it never invents facts
- Depth in my specific domain
- Transparency — I can see *how* it reached the answer
- It says "I don't know" when the evidence isn't there
- Speed — it saves me real time
- Breadth — covers the whole field, not just famous papers
- Lets me explore connections (papers ↔ molecules ↔ experts)

**Q4. A research AI would lose your trust immediately if it…**  *(select all that apply)*
- Invented a citation or reference
- Gave an answer with no sources at all
- Presented a contested claim as settled fact
- Used non-peer-reviewed / blog sources without flagging them
- Couldn't tell me what it's *not* sure about
- Other → ___

**Q5. Today, how much do you trust AI-generated answers when making a real research decision?**  *(scale 1–5 · 1 = not at all, 5 = completely)*

---

## Part B — Rate a real paper (the blind test)

**Displayed before Q6 (neutral framing — do NOT reveal the controversy yet):**

> **One quick task.** Please open and skim this open-access paper (~5 min), then answer the last four questions.
> **"Flavor network and the principles of food pairing"** — Ahn, Ahnert, Bagrow & Barabási, *Scientific Reports* (2011).
> 🔗 https://www.nature.com/articles/srep00196
> It's one of the most cited papers connecting food chemistry, aroma compounds and data science.

**Q6. As a source for a meaty-flavor knowledge base, how would you rate this paper overall?**  *(scale 1–10)*

**Q7. What did you weigh MOST in deciding that rating?**  *(select up to 2)*
- Scientific rigor / methods
- Novelty of the idea
- Real-world applicability to flavor work
- How influential / highly-cited it is
- Data quality & reproducibility
- Clarity & how well it's written
- Relevance to *meaty* flavor specifically
- How well its central claim is actually supported

**Q8. This paper is highly cited — but its central "food-pairing" claim is debated (it fits Western cuisines, not Eastern, and later studies push back). Should an AI assistant cite it when answering a researcher?**  *(single choice)*
- Yes — it's foundational
- Only with a caveat that the claim is debated
- No — too contested to cite as evidence

**Q9. In one sentence: when MeatCODE decides whether to include a paper like this, what should it prioritize most?**  *(short open text)*

---

## Why each question — what it lets you infer

| Q | Theme | What you learn / how you'll use it |
|---|---|---|
| 1 | Segment | Slice every answer by audience (researcher vs industry vs data) — values differ sharply. |
| 2 | **Struggles** | Ranked list of what current LLMs get wrong → the pains MeatCODE must beat. |
| 3 | **Top values** | Forced top-3 → the priorities to build first (likely: cited sources + no-hallucination). |
| 4 | **Non-negotiables** | The deal-breakers → your hard guardrails (maps directly to the grounding contract). |
| 5 | Baseline trust | A number to re-measure *after* they try MeatCODE (did trust move?). |
| 6 | Paper rating (blind) | A comparable score, human vs LLM/audit, on the **same** paper. |
| 7 | **Review criteria** | *The gold:* what humans actually weigh when rating a paper → what the audit LLM should weight (rigor? applicability? support-for-claim?). |
| 8 | Contested-source trust | How to handle influential-but-debated papers (cite / caveat / exclude) → a rule for the Oracle. |
| 9 | Rubric in their words | Open prioritization statement → compare across people *and* against the LLM's own rationale. |

**Comparison plan:** run the *same* paper (Ahn 2011) through your audit judge / the Oracle and capture its Q6-style score, its Q7-style criteria, and its Q8 stance. Diff human vs LLM on all three → that gap tells you where the model's rating instinct diverges from your users', and what to tune.

---

## Notes
- Keep Q6/Q7 **before** the Q8 controversy reveal so the initial rating is unbiased.
- All questions required except Q4-"Other" text and Q9 (recommended required for the rubric).
- Estimated completion: 4–6 min (the paper skim is the longest part).
