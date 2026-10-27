---
name: weekly-progress-brief
description: >
  Create a polished weekly progress update as a Word document summarizing the main work completed
  during the past 7 days. Use this skill whenever the user asks for a weekly update, progress brief,
  weekly summary, or says things like "what did I do this week", "weekly report", "progress report",
  "summarize my week", "what moved forward", or "send my weekly". Also triggers on scheduled runs
  of the weekly-progress-brief task. The skill reads session transcripts, scans workspace files for
  recent changes, synthesizes everything into an executive-ready docx, and optionally uploads to
  Google Drive.
---

# Weekly Progress Brief

Generate a polished, executive-ready weekly update document (.docx) by reviewing session transcripts and workspace activity from the past 7 days.

## Why this skill exists

Lior runs multiple workstreams simultaneously — a research database (GFI/Reaktzia), academic coursework, Claude tooling practice, and various automation projects. Manually remembering what shipped each week is tedious. This skill automates the entire pipeline: gather evidence from transcripts and files, distill it into high-signal items, produce a professional Word document, and deliver it to Google Drive.

## End-to-end workflow

The skill has four phases. Execute them in order.

### Phase 1: Gather evidence

The goal is to build a comprehensive picture of meaningful work from the last 7 days. "Meaningful" means: deliverables shipped, decisions made, frameworks designed, documents produced, code written, systems built or advanced. Not: casual Q&A, minor clarifications, or back-and-forth that didn't change direction.

**Step 1a — Read session transcripts.**
Use `mcp__session_info__list_sessions` (limit 40) to get all recent sessions. Read transcripts for every session that looks substantive (skip sessions with no messages or that are clearly empty). Read up to 30 messages per transcript. Look for:

- Files created or edited (Write, Edit tool calls)
- Deliverables mentioned (documents, scripts, dashboards, presentations)
- Decisions or design choices made
- Systems integrated or configured
- Research completed or analyses delivered

When reading transcripts, pay attention to session titles — they often indicate the workstream. Group related work mentally as you go.

**Step 1b — Scan workspace files.**
Check the workspace folders for files modified in the last 7 days:

```bash
find /sessions/*/mnt/ -type f -mtime -7 -not -path '*/node_modules/*' -not -path '*/.git/*' -not -name '*.pyc' | head -50
```

Cross-reference with what you found in transcripts. Files that appear in both are high-confidence deliverables.

### Phase 2: Synthesize

Before writing anything, organize what you found into a mental outline:

1. **Identify workstreams.** Common ones include: GFI Database / Reaktzia, Academic (lab reports, coursework), Claude Tooling (practice sessions, skills, automation), and ad-hoc projects. But infer from the actual data — don't force categories that don't fit this week.

2. **Merge related work.** If three conversations all contributed to the same pipeline feature, that's one item, not three. Summarize the final meaningful result.

3. **Rank by impact.** Lead with the most substantial outcomes. A new database sync pipeline matters more than a small config fix.

4. **Identify open items.** Anything partially completed, blocked, awaiting review, or needing a decision goes in the "In Progress" section.

5. **Drop the noise.** If something was just a quick question that didn't change anything, omit it. The brief should feel like a board update, not a chat log.

### Phase 3: Create the document

Use the `docx` skill to produce a polished Word document. Read the docx SKILL.md for technical instructions on creating the file.

**Document structure — follow this exactly:**

**Title:** `Weekly Update · [Month Day–Day, Year]` (e.g., "Weekly Update · May 15–22, 2026")

**Subtitle:** `Summary of what moved forward this week across my main projects and deliverables`

**Section 1: COMPLETED THIS WEEK**

For each completed item, write:
- A short, strong headline (bold)
- One concise explanatory line underneath

Use checkmark-style formatting. Group similar work so the update stays clean. Typically 4–8 items — enough to capture what mattered, not so many that it feels like a task dump.

**Section 2: IN PROGRESS / NEEDS YOUR INPUT OR APPROVAL**

For each open item:
- A clear headline
- One line of context
- A status label: `In progress`, `Needs your input`, `Needs your approval`, or `Awaiting decision`

**Closing line:** `Lior Teper · Week of [start date]`

**Writing style rules:**
- Professional, strategic, high-clarity tone
- Feels like a founder/research/product weekly brief
- Focus on outcomes, structure, and forward movement
- No trivial back-and-forth or minor questions unless they changed direction
- Compressed, high-signal summaries over long explanations
- Presentation-ready and easy to skim
- No emojis in the document body (checkmarks are fine)

**File naming:** `Weekly_Update_[Month]_[Day]-[Day]_[Year].docx`

Save the file to the workspace folder so Lior can access it immediately.

### Phase 4: Deliver to Google Drive

After creating the docx, offer to upload it to Google Drive in the folder: **Lior Teper → project → Weekly Summary**.

- If this is a **scheduled (automated) run**: ask for confirmation before uploading. State clearly: "I've created the weekly update. Should I upload it to Google Drive?"
- If Lior **explicitly asked** for the upload (e.g., "send my weekly", "push it to Drive"): confirm and proceed.

Use the Google Drive MCP tools (`mcp__3cc7d19e-*`) to create the file in the correct folder. Search for a folder named "Weekly Summary" inside a "project" folder. If the folder path doesn't exist or the Drive MCP isn't connected, save locally and let Lior know.

## Edge cases

- **Nothing meaningful happened this week:** Don't fabricate items. Write a shorter brief with whatever did happen, even if it's just 1–2 items. Honesty > padding.
- **Can't read transcripts (tool unavailable):** Fall back to scanning workspace files only. Note in the document that coverage may be incomplete.
- **Duplicate with previous week's brief:** If you can read the previous week's brief, avoid repeating items unless they carried over as "in progress" and have now been completed.
- **Mixed languages:** Lior works in both English and Hebrew. The weekly brief should be in English. If source material is in Hebrew, translate the key points.

## What NOT to include

- Small chat clarifications or quick factual questions
- Scheduled task runs themselves (don't list "weekly brief generated" as an accomplishment)
- Practice sessions unless they produced a concrete deliverable or skill
- Repeated iterations of the same thing — just summarize the final result
- Internal Claude mechanics (tool calls, memory updates, skill loading)
