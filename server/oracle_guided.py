# Last updated: 2026-10-25 20:30 UTC · Yochai (PM) with Claude · NEW guided-Oracle (elicitation) helpers behind flag
#   `oracle_guided`. Prompt text only + parsing — no HTTP, no SQL, no retrieval (meatcode_server.py owns those and
#   reuses the existing _retrieve_sources / _grounding_system_prompt unchanged). Flag OFF -> nothing here runs.
"""Guided Oracle — the elicitation step from the Oracle spec (section 5, closed 11 Oct; tested in the Oracle Sandbox).

Before answering, one small model call reads the whole conversation and decides: is this a LOOKUP / FORMULATION /
METHOD / LANDSCAPE / GAP / FIND / OUT OF SCOPE question, which parameters are already given or implied, and whether
to ASK for the single most important missing one (max 3 questions per conversation, one per turn, with typical
values to tap) or ANSWER now. When it answers, guided_answer_rules() is appended to the existing grounding prompt so
the answer opens with a "Working from:" playback line and never fills a gap with a fixed default.

Output format stays the production Oracle's: plain prose paragraphs + a final "Follow-ups:" line, real source ids
in [brackets]. The "never narrate retrieval" product rule (2026-07-20) is kept: no [general] markers.
"""
from __future__ import annotations

import json
import re

MAX_QUESTIONS = 3
MAX_HISTORY_TURNS = 12
MAX_TURN_CHARS = 4000

INTENTS = ("LOOKUP", "FORMULATION", "METHOD", "LANDSCAPE", "GAP", "FIND", "OUT_OF_SCOPE", "UNCLEAR")
PARAM_STATUSES = ("given", "implied", "open", "missing")

ELICIT_RULES = """## Role
You are the MeatCODE Oracle, a research assistant for flavour and aroma scientists working on plant-based and cultivated meat. Your users are R&D scientists, analytical chemists, academics and PhD students. Write peer to peer: technical and concise, with no praise or filler.
Right now you are NOT answering. You decide whether to ask one short question first, or to answer now.

## Step 1 - Work out what the user wants
Decide which type the message is. Use the whole conversation, not only the last message.
- LOOKUP: a fact about a compound, precursor or method (threshold, odour descriptor, structure).
- FORMULATION: how to create, strengthen or fix a flavour note in a product.
- METHOD: how to measure or analyse something.
- LANDSCAPE: what is known about a topic.
- GAP: what has not been studied yet.
- FIND: a person, organisation, event or database page.
- OUT_OF_SCOPE: anything else (suppliers, prices, topics outside flavour and aroma).
If two types are equally likely, ask one short question to tell them apart (action "clarify").

## Step 2 - Check what you already have
FORMULATION needs five parameters, in this order of importance:
1. Target note (roasted/grilled beef, boiled beef/broth, chicken fat, pork, bacon/smoky...)
2. Protein base (pea, soy, wheat gluten, mycoprotein, fava, a blend...)
3. Process (high-moisture extrusion, pan-frying, baking, retort, a separate reaction-flavour batch...)
4. pH (an approximate value is fine)
5. Matrix (the final product, fat type and level, binders)
METHOD needs: the analytes or compound class, the sample matrix, the instruments available.
LANDSCAPE: if the topic is broad, you may ask for the purpose (grant, project start, teaching).
GAP needs: the system (protein + process).
LOOKUP and FIND need nothing more. Answer directly.
Take every parameter the user has stated or clearly implied. "My extruded pea burger" gives the protein base, the process and the matrix. Never ask for something you already have.

## Step 3 - Ask or answer
Answer now if any of these is true:
- the type is LOOKUP, FIND or OUT_OF_SCOPE;
- you have at least 4 of the 5 formulation parameters;
- what is missing would not change the core of the answer;
- the user says "just answer", "skip" or similar;
- you have already asked 3 questions in this conversation.
Otherwise, ask for the single most important missing parameter.

How to ask:
- One question per message. Apart from the question, add at most one sentence acknowledging what you already have.
- Say in half a sentence why it matters to the chemistry.
- Offer 3-4 typical values in the sentence and say that "not sure" is fine.
- Example: "Which protein base are you working with? It sets how much cysteine and methionine you have for meaty sulfur notes. For example pea, soy, wheat gluten or mycoprotein, or say 'not sure'."
Never assume the target note. If the user can't name one, describe the three main beef note families in 2-3 lines (roasted/grilled, boiled/brothy, fatty) and ask them to pick.
If the user says "not sure" or skips a parameter, mark it "open" and do not ask about it again.
Reply in the language the user writes in."""

DECISION_FORMAT = """## Output format
Reply with ONLY one JSON object and no other text:
{"intent": "LOOKUP|FORMULATION|METHOD|LANDSCAPE|GAP|FIND|OUT_OF_SCOPE|UNCLEAR",
 "action": "ask|clarify|answer",
 "question": "your message to the user when action is ask or clarify (1-3 sentences, plain text); empty when answering",
 "options": ["3-4 short typical values the user can tap, 1-5 words each; do not include 'not sure'; [] when answering"],
 "params": [{"name": "Target note", "value": "roasted beef", "status": "given"}],
 "why": "one short sentence: why you ask, or why you can answer now"}
- params: for FORMULATION list all five (Target note, Protein base, Process, pH, Matrix); for METHOD list Analytes, Sample matrix, Instruments; for GAP list System; otherwise [].
- status is one of: "given" (the user said it), "implied" (clear from their wording), "open" (the user skipped it or is not sure), "missing" (not known yet). value is null when the status is "open" or "missing"."""


def clean_history(history):
    """[{role: user|assistant, content, kind?}] -> validated, trimmed list (oldest first)."""
    out = []
    if not isinstance(history, list):
        return out
    for t in history[-(MAX_HISTORY_TURNS * 2):]:
        if not isinstance(t, dict):
            continue
        role = t.get("role")
        content = str(t.get("content") or "").strip()[:MAX_TURN_CHARS]
        if role not in ("user", "assistant") or not content:
            continue
        kind = t.get("kind") if t.get("kind") in ("ask", "answer") else ("answer" if role == "assistant" else None)
        out.append({"role": role, "content": content, "kind": kind})
    return out


def questions_asked(history):
    return sum(1 for t in history if t["role"] == "assistant" and t.get("kind") == "ask")


def decision_prompt(history, question, skip):
    conv = "\n\n".join(
        ("USER: " if t["role"] == "user" else "ORACLE (%s): " % (t.get("kind") or "answer")) + t["content"]
        for t in history)
    conv = (conv + "\n\n" if conv else "") + "USER: " + question
    n = questions_asked(history)
    note = ("The user asked you to skip the questions: answer now (action \"answer\").\n" if skip else "")
    return "\n\n---\n\n".join([
        ELICIT_RULES, DECISION_FORMAT,
        "## CONVERSATION SO FAR (oldest first)\n" + conv,
        "%sQuestions you have already asked in this conversation: %d of %d.\nNow write your JSON decision for the last USER message."
        % (note, n, MAX_QUESTIONS)])


def parse_decision(raw, history, skip):
    """Model text -> {intent, action, question, options, params, why}. Forces 'answer' when the question budget is
    spent, the user skipped, or the output is unusable (never blocks the user on a parsing problem)."""
    data = {}
    m = re.search(r"\{.*\}", raw or "", re.S)
    if m:
        try:
            data = json.loads(m.group(0))
        except ValueError:
            data = {}
    intent = str(data.get("intent") or "UNCLEAR").upper().replace(" ", "_")
    if intent not in INTENTS:
        intent = "UNCLEAR"
    action = data.get("action") if data.get("action") in ("ask", "clarify", "answer") else "answer"
    question = str(data.get("question") or "").strip()[:600]
    options = [str(o).strip()[:40] for o in (data.get("options") or []) if str(o).strip()][:4]
    params = []
    for p in data.get("params") or []:
        if isinstance(p, dict) and p.get("name"):
            st = p.get("status") if p.get("status") in PARAM_STATUSES else "missing"
            params.append({"name": str(p["name"])[:40],
                           "value": None if p.get("value") in (None, "") else str(p.get("value"))[:80],
                           "status": st})
    if skip or questions_asked(history) >= MAX_QUESTIONS or (action != "answer" and not question):
        action = "answer"
    return {"intent": intent, "action": action, "question": question if action != "answer" else "",
            "options": options if action != "answer" else [], "params": params[:6],
            "why": str(data.get("why") or "")[:240]}


def retrieval_query(history, question):
    """Retrieval text for the answer: the latest question first, then earlier user turns (their parameters,
    e.g. 'extruded pea burger'), capped so the keyword search stays focused."""
    users = [t["content"] for t in history if t["role"] == "user"]
    return " ".join([question] + users[::-1])[:600]


def guided_answer_rules(decision):
    lines = []
    for p in decision.get("params") or []:
        lines.append("- %s: %s (%s)" % (p["name"], p["value"] if p["value"] else "not known", p["status"]))
    params = "\n".join(lines) if lines else "- (none needed for this question type)"
    return (
        "\n\nGUIDED ANSWER RULES (the user went through MeatCODE's guided questions; these refine, never override, "
        "the rules above):\n"
        "Question type: %s.\nParameters gathered:\n%s\n"
        "- When parameters were gathered (FORMULATION, METHOD, GAP), make the FIRST paragraph one line in exactly "
        "this shape: \"Working from: <the given and implied parameters>. Open: <parameters left open, or none>. "
        "Change any of these and I'll redo it.\"\n"
        "- Never fill an open or missing parameter with a fixed default. Where an open parameter changes the "
        "chemistry, show how the answer differs across the two cases that matter (for example pH below about 5.5 "
        "versus about 6-7; dry high heat versus wet heat).\n"
        "- FORMULATION: give the precursors, then the reaction and conditions, then the key volatiles for the target "
        "note, adjusted for the protein base, process, pH and matrix.\n"
        "- Say plainly what is unknown or untested for this system.\n"
        "- Make the last paragraph before the Follow-ups line one suggested next step, starting \"Next step:\" (an "
        "analytical check, the kind of expert to talk to, or a source to open).\n"
        "- Keep the parameters for the rest of the conversation; if the user changes one, change only that one.\n"
        "- Never quote more than 150 consecutive characters from a source. Reply in the user's language.\n"
        "- Keep the production format: plain prose paragraphs, no bullets or headers, final 'Follow-ups:' line.\n"
        % (decision.get("intent") or "UNCLEAR", params))


def answer_messages(history, question):
    """Anthropic messages: prior turns (asks included, so the model sees what it asked) + the new question.
    Consecutive same-role turns are merged so the list always alternates user/assistant."""
    msgs = []
    for t in history + [{"role": "user", "content": question}]:
        if msgs and msgs[-1]["role"] == t["role"]:
            msgs[-1]["content"] += "\n\n" + t["content"]
        else:
            msgs.append({"role": t["role"], "content": t["content"]})
    if msgs and msgs[0]["role"] != "user":
        msgs = msgs[1:]
    return msgs
