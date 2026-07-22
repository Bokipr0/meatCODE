_Last updated: 2026-07-21 · Advisory · Typeform build spec for the MeatCODE user survey v1_

# Typeform build spec — MeatCODE User Values & Paper-Rating Survey

There's no Typeform connector available to auto-create it, so this is a **block-by-block build sheet** — in Typeform's editor it's ~10 minutes. (If you have a Typeform **Personal Access Token**, I can instead generate it via their Create API — just say so and share nothing here; you'd paste the token into a script on your Mac.)

**Form settings:** Title "MeatCODE — User Values & Paper-Rating Survey" · show progress bar · no email required · one question per screen (Typeform default).

## Welcome screen
Title: **Help shape MeatCODE — 5 minutes, before you've ever used it.**
Text: MeatCODE (a Good Food Institute · GFI Israel initiative) is building an AI research assistant that answers only from real, cited scientific sources. Before we show it to you, we want your honest expectations and frustrations with AI tools today. No right answers — and at the end you'll skim one real paper and rate it. Anonymous.
Button: "Start"

## Blocks (Typeform block type → content)

**1 · Multiple Choice (single, + "Other")** — required
"Which best describes you?"
Academic researcher / PI · Grad student or postdoc · Flavor / food chemist (industry) · Alt-meat / food-product R&D · Data / AI / software · Other
→ *Multiple choice → toggle "Add 'Other' choice".*

**2 · Multiple Choice (Multiple selection ON, limit 3)** — required
"When you use general AI chatbots (ChatGPT, Claude, Gemini…) for scientific questions, what frustrates you most? (up to 3)"
Makes things up / hallucinates · Can't verify the source · Cites papers that don't exist or are wrong · Not deep enough in my field · Knowledge feels outdated · Generic / surface-level · Won't admit when it doesn't know · Blends solid science with weak/blog claims
→ *Settings → "Multiple selection" ON → "Set max" = 3.*

**3 · Multiple Choice (Multiple selection ON, exactly 3)** — required
"Which THREE qualities matter most in a knowledge-based AI research assistant?"
Every claim backed by a real citable source · Never invents facts · Depth in my domain · Transparency (see how it answered) · Says "I don't know" when evidence is thin · Speed · Breadth (whole field, not just famous papers) · Explore connections (papers ↔ molecules ↔ experts)
→ *Multiple selection ON → set min 3 and max 3.*

**4 · Multiple Choice (Multiple selection ON, + "Other")** — required
"A research AI would lose your trust immediately if it…"
Invented a citation · Answered with no sources · Presented a contested claim as settled fact · Used non-peer-reviewed/blog sources without flagging · Couldn't tell me what it's unsure about · Other
→ *Multiple selection ON, no limit; add "Other".*

**5 · Opinion Scale (1–5)** — required
"Today, how much do you trust AI answers when making a real research decision?"
Left label "Not at all" · Right label "Completely" · steps 1–5.

**6 · Statement block (no answer) — the paper**
"One quick task: skim this open-access paper (~5 min), then answer the last four questions.
**Flavor network and the principles of food pairing** — Ahn, Ahnert, Bagrow & Barabási, *Scientific Reports* (2011).
One of the most cited papers connecting food chemistry, aroma compounds and data science."
→ *Add a Statement block; set the button to a link: https://www.nature.com/articles/srep00196 (or paste the link in the text). Keep framing neutral — don't mention the debate yet.*

**7 · Opinion Scale (1–10)** — required
"As a source for a meaty-flavor knowledge base, how would you rate this paper overall?"
Left "Not useful" · Right "Essential" · steps 1–10.

**8 · Multiple Choice (Multiple selection ON, limit 2)** — required
"What did you weigh MOST in deciding that rating? (up to 2)"
Scientific rigor / methods · Novelty · Real-world applicability to flavor work · How influential/cited it is · Data quality & reproducibility · Clarity/writing · Relevance to meaty flavor specifically · How well its central claim is actually supported
→ *Multiple selection ON → max 2.*

**9 · Multiple Choice (single)** — required
"This paper is highly cited — but its central 'food-pairing' claim is debated (fits Western cuisines, not Eastern; later studies push back). Should an AI assistant cite it when answering a researcher?"
Yes — it's foundational · Only with a caveat that the claim is debated · No — too contested to cite as evidence

**10 · Long Text** — required
"In one sentence: when MeatCODE decides whether to include a paper like this, what should it prioritize most?"

## Ending screen
"Thank you — this directly shapes what we build. 🙏  — Lior & the MeatCODE team, GFI Israel."

> Note: blocks 6 is a *statement* (not a question), so the count is **9 real questions** (1–5 + 7–10), matching the Google Form. Keep block 6's framing neutral so the rating in block 7 stays unbiased; the debate is only revealed in block 9.
