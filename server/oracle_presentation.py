# Last updated: 2026-11-18 09:04 UTC · Codex · Compact source expansion and visible next steps.
"""Presentation-only streaming boundary; no retrieval, model or persistence changes."""

DETAIL_MARKER = '[[MEATCODE_DETAILS]]'

ANSWER_STYLE = (
    "Lead with the information that most directly helps this user answer their question or make a decision. "
    "Use a clear, practical, conversational voice. Start with the answer itself: no introductory essay, "
    "praise, academic framing, broad background, or recap of the question. "
    "The visible short answer must be 2-4 concise sentences, at most 100 words. "
    "Give the key recommendation or finding first and its most important reason. "
    "End the visible short answer with one concrete recommended action, starting 'Next step:'. "
    "Put that next step BEFORE [[MEATCODE_DETAILS]], never only in the supporting explanation. "
    "For a factual lookup, recommend a useful verification or source to consult rather than inventing an experiment. "
    "Keep essential conditions, uncertainty and qualifications in that short answer; "
    "never hide a qualification that changes the recommendation in the supporting detail. "
    "Keep necessary scientific names, units and valid source citations, but explain jargon briefly. "
    "For a simple question, the short answer can stand alone. If useful supporting explanation remains, "
    "write the exact marker [[MEATCODE_DETAILS]] on its own line after the short answer, then give "
    "2-3 short supporting paragraphs, usually no more than 250 words total. If the user explicitly asks "
    "for a protocol or a detailed comparison, keep the necessary steps, conditions and units in the detail. "
    "The interface hides everything after "
    "that marker behind an Expand answer control. Do not repeat the short answer in the detail, "
    "and do not tell the user to click a button. Do not emit a details marker without useful detail. "
    "Use plain prose paragraphs separated by blank lines, with no markdown headings, bullets or code blocks. "
    "Do not add suggested follow-up questions or a Follow-ups line."
)


class AnswerSections:
    """Strip an internal marker across arbitrary chunks; older SSE clients keep plain prose."""
    def __init__(self):
        self.buffer = ''
        self.detail = False

    def feed(self, text):
        if self.detail:
            return [('chunk', text)] if text else []
        self.buffer += text
        index = self.buffer.find(DETAIL_MARKER)
        if index >= 0:
            before, after = self.buffer[:index], self.buffer[index + len(DETAIL_MARKER):]
            self.buffer = ''
            self.detail = True
            return ([('chunk', before)] if before else []) + [('answer_section', '{"section":"detail"}')] + ([('chunk', after)] if after else [])
        # Only retain a suffix that could be the start of the boundary. Ordinary text streams immediately.
        keep = 0
        for length in range(1, min(len(self.buffer), len(DETAIL_MARKER) - 1) + 1):
            if self.buffer.endswith(DETAIL_MARKER[:length]):
                keep = length
        ready = self.buffer[:-keep] if keep else self.buffer
        self.buffer = self.buffer[-keep:] if keep else ''
        return [('chunk', ready)] if ready else []

    def finish(self):
        # A model truncated part-way through our internal marker must not expose it as product text.
        remaining = self.buffer if len(self.buffer) < 5 else ''
        self.buffer = ''
        return [('chunk', remaining)] if remaining else []
