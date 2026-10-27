---
name: project-board-sync
description: Turn a raw task list — meeting notes, a screenshot of action items, a doc, or a verbal brain-dump — into a tracked project board, then get every teammate or agent working from the same page. Use this whenever the user shares tasks, action items, sprint goals, a roadmap, or meeting output and wants them organized, tracked, prioritized, assigned, or shared with a team — even when phrased casually like "here are my next tasks", "what should we work on next", "keep track of these", "what's still open", or "make sure everyone knows". Also use when the user asks to update the team, sync the agents, brief collaborators, or check what's still open on a project. Prefer this over writing an ad-hoc to-do list: the point is to catch what the list is missing, not to retype it.
---

# Project board & team sync

## What this is actually for

Anyone can retype a task list into a prettier format. That is worth almost nothing — the user already knows what they wrote down.

The value you add is **the gap between the list and reality**: the work that's finished but not shipped, the known blocker that quietly gates half the list, the three items that are secretly one project, the decision nobody has made that stops two of them from starting. A good board tells the user something they didn't know when they handed you the list.

So treat the list as *evidence about what the team is thinking*, not as the specification for your output.

Two audiences, and they need different things:
- **The people/agents doing the work** need to know *which one thing is theirs next*, in a file they'll actually read.
- **The person who owns the project** needs to see the whole shape at once, and re-check it later.

---

## Step 1 — Ground yourself before you write anything

Read the project's real state first. This is the step that makes everything else possible: a board written from the list alone can only repeat the list back.

Look for whatever the project already keeps:
- Status or state docs (`PROJECT_STATE.md`, `STATUS.md`, `ROADMAP.md`, `CHANGELOG.md`, agent instructions like `CLAUDE.md`, a README's status section)
- An existing board or task file, and any connected tracker (Asana, Linear, Jira, GitHub Issues) — check before inventing a new home
- Recent activity: `git log --oneline -20`, recently modified files, open branches, an update log
- Prior conversation in this session — decisions the user already made count as evidence

You're building three lists in your head: **what's genuinely done**, **what's claimed but unverified**, and **what's known-broken**. If the project keeps no state at all, say so — that itself is a finding worth reporting, and the board you write becomes its first one.

Keep this proportional. A quick read of the status doc plus a glance at recent commits is usually enough; don't audit an entire codebase before writing a board.

## Step 2 — Find the real shape of the list

Lists get written in meeting order, which is almost never working order. Before you organize anything, work out:

- **What's actually one thing?** Several items often serve a single deliverable. If three action items all feed one tool, say that plainly — a list of 13 that's really 4 projects is far less frightening and far easier to sequence.
- **What depends on what?** If B can't start until A lands, that ordering matters more than any priority label someone assigned.
- **What's a task vs. a whole workstream?** "Documentation" and "add the export button" don't belong at the same altitude. Note it rather than pretending they're peers.
- **What does this item actually mean?** Vague entries ("placeholder", "improve X") are where projects rot. Either pin down the concrete first deliverable or flag it as needing definition.

## Step 3 — Find what's missing (this is the valuable part)

The list reflects what was top-of-mind in a meeting. Reality usually contains items nobody said out loud. Hunt specifically for:

- **Finished but not shipped** — work that's built, merged, or committed but not deployed/released/published. Extremely common, and it silently blocks demos.
- **Known debt that gates a listed item** — if the list says "improve data quality" and you found an open data-integrity bug in the status doc, those are the same item and one of them has a name.
- **Decisions, not tasks** — work that can't start until a human picks a direction (see Step 5).
- **The unglamorous infrastructure** — testing, deploy access, credentials, environments, backups. Rarely listed, frequently the actual bottleneck.

Put these in a clearly separate section — something like "Not on your list, but blocking" — so the user can see instantly what you added and judge it. Never quietly blend your additions into their list; they need to be able to reject them.

For each, give the specific reason it matters, not a generic warning. "A month of built work isn't deployed, so nothing on this board is demoable" lands. "Consider deploying regularly" doesn't.

## Step 4 — Assign status, owner, and the critical path

**Status must be evidence-based.** Mark something done only if you saw evidence; mark it blocked only if you can name the blocker. When you don't know, "unknown / needs confirmation" is a legitimate and useful status — inventing a confident status is worse than admitting the gap, because the user will act on it.

**Owner** = whoever or whatever does the work: a person, a team, a lane, a named agent. If ownership is genuinely unclear, that's a finding to surface, not a blank to fill in silently.

**Critical path** — mark the small number of items that block other items. If everything is marked critical, nothing is; three or four is usually the honest number. This is the single most useful annotation on the board, because it answers "what do I do Monday morning."

## Step 5 — Surface decisions instead of resolving them

When two reasonable people would choose differently and you'd have to guess, that's a **decision**, not a task. Scope calls, data sources, build-vs-defer, whether to collect user data — these belong in their own short list addressed to the humans who own them.

State what's blocked by each decision, so its cost is visible: "until this is settled, these two items can't start." That converts a vague open question into something with a price tag, which is what actually gets it answered.

If the user makes a decision during the conversation, record it in the board and status doc as decided, with the date — otherwise it gets re-litigated in three weeks.

## Step 6 — Write the board where it will actually be read

Fit the project's existing conventions rather than inventing a parallel universe. If there's already a tracker or board file, update it. Only create a new home when there genuinely isn't one, and then say where you put it and why.

**For the team/agents — a file in the repo.** Plain markdown, tables are fine. It needs: a pointer telling agents when to read and update it, the grouped items with owner + status + critical-path marking, the blockers you added, and the open decisions. Cross-link it from the project's main status doc so nobody has to be told twice.

**For the project owner — a visual board**, when the environment supports it (in Cowork, a persistent artifact they can reopen; otherwise a standalone HTML file). `assets/board_template.html` is a working starting point — adapt it rather than building a dashboard from scratch. Keep it to what earns its space: counts by status, the grouped items, status filtering, and a deadline countdown if there's a date.

Both views must come from the same content. If they can drift, they will, and then the user trusts neither — so write the file first and generate the visual from it.

## Step 7 — Broadcast so the team is genuinely on the same page

A board nobody reads changes nothing. Push the update into wherever the team actually looks — a broadcast/announcement file, the agent instructions file, a channel message, or a summary the user can forward.

What makes a broadcast work:

- **Lead with what changed since last time**, not with a full re-listing. People skim.
- **One next move per owner.** Not their whole queue — the single thing they should pick up, and why it matters. A table of owner → next move → why is usually the right density.
- **Dependency order, explicitly.** "A blocks B; don't start B yet" prevents the most expensive kind of wasted work.
- **Process changes get their own callout.** If how people work has changed — a retired command, a new release flow, a new convention — say so loudly and name the stale instructions it overrides. Agents and teammates follow whatever the docs said last, so an unannounced process change silently produces wrong work for weeks.
- **Tell them what to ask about rather than guess.** List the open decisions and instruct people to bring them to the owner. This is what stops five people inventing five different answers.

## Step 8 — Log it

Append a short entry to the project's history/update log if one exists: what changed, why, what was decided, what's next. It costs a paragraph and it's how the *next* session — human or agent — knows this happened without re-deriving it.

---

## Guardrails

- **Don't invent status or progress.** An honest "unknown" beats a confident guess every time; the user is going to make plans out of whatever you write.
- **Keep your additions visibly separate** from the user's own list so they can accept or reject them individually.
- **Don't create a second home for tasks** if the project already has one. Duplicate boards diverge and then nobody trusts either.
- **Don't gold-plate the dashboard.** It's a working tool, not a product surface.
- **Say what you couldn't verify.** If you couldn't check whether something shipped, say that plainly rather than picking a status.

## A quick sanity check before you hand it over

Ask yourself: *does this tell the user anything they didn't already know?* If the board is a faithful reformatting of their list with no additions, no dependency insight, no critical path, and no open decisions, you've done the low-value version — go back to Steps 2 and 3.
