#!/usr/bin/env python3
"""
MeatCODE — User Values & Paper-Rating Survey  ·  Typeform generator
Last updated: 2026-07-22 · Advisory · one-shot Typeform builder (mirrors build_google_form.gs)

WHAT THIS DOES
  Creates the same 9-question survey as the Google Form, but in Typeform, by calling
  Typeform's Create API once. Prints the LIVE (share) URL + the EDIT URL. No editor clicking.

HOW TO USE (on your Mac, ~2 min)
  1. Get a free Personal Access Token:
       https://admin.typeform.com/account#/section/tokens
       -> "Generate a new token" -> name it "MeatCODE" -> scopes: forms:write (+ forms:read)
       -> Generate -> copy it (shown only once; it starts with "tfp_").
  2. In Terminal:
       export TYPEFORM_TOKEN="tfp_paste_your_token_here"
       python3 "/Users/lior/Documents/Claude/Projects/Claude Database/meatCODE/docs/user_research/build_typeform.py"
  3. It prints the LIVE (share) link + EDIT link. Done.

  Preview without creating anything (no token, no network):
       python3 build_typeform.py --dry-run

NOTE ON SELECTION LIMITS
  Typeform's API can't hard-enforce "pick up to 3 / exactly 3 / up to 2". Those limits are
  written into the question text here. To actually enforce them: open the form -> click the
  question -> Settings -> "Multiple selection" -> set min/max (about 3 clicks per question).

SECURITY: the token is read from the environment, never hardcoded. Don't paste it into chat
or commit it. Nothing here is stored.
"""

import json, os, sys, urllib.request, urllib.error

PAPER_URL = "https://www.nature.com/articles/srep00196"

payload = {
    "title": "MeatCODE — User Values & Paper-Rating Survey",
    "settings": {
        "language": "en",
        "progress_bar": "proportion",
        "show_progress_bar": True,
    },
    "welcome_screens": [{
        "title": "Help shape MeatCODE — 5 minutes, before you've ever used it.",
        "properties": {
            "description": (
                "MeatCODE (a Good Food Institute · GFI Israel initiative) is building an AI "
                "research assistant that answers only from real, cited scientific sources. "
                "Before we show it to you, we want your honest expectations and frustrations "
                "with AI research tools today. There are no right answers — and at the end "
                "we'll ask you to skim one real paper and rate it. Responses are anonymous."
            ),
            "show_button": True,
            "button_text": "Start",
        },
    }],
    "thankyou_screens": [{
        "title": "Thank you — this directly shapes what we build. — Lior & the MeatCODE team, GFI Israel.",
        "properties": {"show_button": False, "share_icons": False},
    }],
    "fields": [
        {
            "title": "Which best describes you?",
            "type": "multiple_choice",
            "properties": {
                "allow_other_choice": True,
                "vertical_alignment": True,
                "choices": [{"label": c} for c in [
                    "Academic researcher / PI",
                    "Grad student or postdoc",
                    "Flavor / food chemist (industry)",
                    "Alt-meat / food-product R&D",
                    "Data / AI / software",
                ]],
            },
            "validations": {"required": True},
        },
        {
            "title": "When you use general AI chatbots (ChatGPT, Claude, Gemini…) for scientific or technical questions, what frustrates you most? (choose up to 3)",
            "type": "multiple_choice",
            "properties": {
                "allow_multiple_selection": True,
                "vertical_alignment": True,
                "choices": [{"label": c} for c in [
                    "It makes things up / hallucinates facts",
                    "I can't verify where the answer came from (no real sources)",
                    "It cites papers that don't exist, or gets them wrong",
                    "Not deep enough in my specific field",
                    "Its knowledge feels outdated",
                    "Answers are generic / surface-level",
                    "It won't admit when it doesn't know",
                    "It blends solid science with weak / blog-level claims",
                ]],
            },
            "validations": {"required": True},
        },
        {
            "title": "In a knowledge-based AI research assistant, which THREE qualities matter most to you? (choose exactly 3)",
            "type": "multiple_choice",
            "properties": {
                "allow_multiple_selection": True,
                "vertical_alignment": True,
                "choices": [{"label": c} for c in [
                    "Every claim backed by a real, citable source",
                    "Accuracy — it never invents facts",
                    "Depth in my specific domain",
                    "Transparency — I can see how it reached the answer",
                    "It says \"I don't know\" when the evidence isn't there",
                    "Speed — it saves me real time",
                    "Breadth — covers the whole field, not just famous papers",
                    "Lets me explore connections (papers ↔ molecules ↔ experts)",
                ]],
            },
            "validations": {"required": True},
        },
        {
            "title": "A research AI would lose your trust immediately if it…",
            "type": "multiple_choice",
            "properties": {
                "allow_multiple_selection": True,
                "allow_other_choice": True,
                "vertical_alignment": True,
                "choices": [{"label": c} for c in [
                    "Invented a citation or reference",
                    "Gave an answer with no sources at all",
                    "Presented a contested claim as settled fact",
                    "Used non-peer-reviewed / blog sources without flagging them",
                    "Couldn't tell me what it's not sure about",
                ]],
            },
            "validations": {"required": True},
        },
        {
            "title": "Today, how much do you trust AI-generated answers when making a real research decision?",
            "type": "opinion_scale",
            "properties": {
                "steps": 5,
                "start_at_one": True,
                "labels": {"left": "Not at all", "right": "Completely"},
            },
            "validations": {"required": True},
        },
        {
            "title": "One quick task — rate a real paper",
            "type": "statement",
            "properties": {
                "description": (
                    "Please open and skim this open-access paper (~5 min), then answer the last four questions.\n\n"
                    "\"Flavor network and the principles of food pairing\" — Ahn, Ahnert, Bagrow & Barabási, "
                    "Scientific Reports (2011).\n"
                    "Link:  " + PAPER_URL + "\n\n"
                    "It's one of the most cited papers connecting food chemistry, aroma compounds and data science."
                ),
                "hide_marks": False,
                "button_text": "I've skimmed it — continue",
            },
        },
        {
            "title": "As a source for a meaty-flavor knowledge base, how would you rate this paper overall?",
            "type": "opinion_scale",
            "properties": {
                "steps": 10,
                "start_at_one": True,
                "labels": {"left": "Not useful", "right": "Essential"},
            },
            "validations": {"required": True},
        },
        {
            "title": "What did you weigh MOST in deciding that rating? (choose up to 2)",
            "type": "multiple_choice",
            "properties": {
                "allow_multiple_selection": True,
                "vertical_alignment": True,
                "choices": [{"label": c} for c in [
                    "Scientific rigor / methods",
                    "Novelty of the idea",
                    "Real-world applicability to flavor work",
                    "How influential / highly-cited it is",
                    "Data quality & reproducibility",
                    "Clarity & how well it's written",
                    "Relevance to meaty flavor specifically",
                    "How well its central claim is actually supported",
                ]],
            },
            "validations": {"required": True},
        },
        {
            "title": "This paper is highly cited — but its central \"food-pairing\" claim is debated (it fits Western cuisines, not Eastern, and later studies push back). Should an AI assistant cite it when answering a researcher?",
            "type": "multiple_choice",
            "properties": {
                "vertical_alignment": True,
                "choices": [{"label": c} for c in [
                    "Yes — it's foundational",
                    "Only with a caveat that the claim is debated",
                    "No — too contested to cite as evidence",
                ]],
            },
            "validations": {"required": True},
        },
        {
            "title": "In one sentence: when MeatCODE decides whether to include a paper like this, what should it prioritize most?",
            "type": "long_text",
            "validations": {"required": True},
        },
    ],
}


def main():
    if "--dry-run" in sys.argv:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        print("\n[dry-run] %d fields, no request sent." % len(payload["fields"]), file=sys.stderr)
        return

    token = os.environ.get("TYPEFORM_TOKEN", "").strip()
    if not token:
        sys.exit('ERROR: set your token first ->  export TYPEFORM_TOKEN="tfp_..."  (see header).')

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        "https://api.typeform.com/forms", data=data, method="POST",
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        sys.exit("Typeform API error %s:\n%s" % (e.code, e.read().decode("utf-8", "replace")))
    except urllib.error.URLError as e:
        sys.exit("Network error: %s" % e.reason)

    form_id = body.get("id", "")
    live = body.get("_links", {}).get("display", "(open your Typeform workspace)")
    print("\nTypeform created!")
    print("   LIVE (share) link:  " + live)
    print("   EDIT link:          https://admin.typeform.com/form/%s/create" % form_id)


if __name__ == "__main__":
    main()
