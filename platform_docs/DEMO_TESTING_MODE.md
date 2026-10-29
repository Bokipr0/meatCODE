# Demo testing mode

_Last updated: 2026-10-29 17:32 UTC · Codex · owner-requested automatic first-use collection_

Lior requested automatic testing during demos until he decides otherwise. A brief notice replaces
the blocking optional-consent dialog. Usage and newly submitted Oracle conversations start on the
first trusted click, Enter or form submission after research configuration is available. If first
interaction precedes configuration, activation follows when enabled configuration arrives; already
submitted turns are not retrospectively imported. Details/feedback remain manually accessible.

New policy `2026-10-29-demo-v1` records automatic first-use activation. It must not be interpreted
as explicit checkbox consent. Existing `consent` and `full_chat_consent` wire fields are retained
for compatibility; the version distinguishes demo activation from the previous optional policy.
The new policy requires migration0021_research_demo_policy.sql to expand the allowed policy versions; it was applied to both dedicated research databases by the integrated release. Existing sessions are not rewritten.

New questions, answers, clarification choices, citations and journey timing go to private MeatCODE
research storage under the existing 90-day policy. Earlier chats, unsent text, attachment contents
and account details remain excluded. Clarity remains masked; PostHog receives bounded metadata.
Provider enablement, URL checks, feature gates, and withdrawal/deletion remain in effect.
A stop decision remains effective for the tab, including reload; it is not silently reversed.

Deploy `app/assets/user-research.js` and `server/user_research.py` together. Existing research
must be enabled; the mode does not override the global off switch. `RESEARCH_DEMO_MODE` defaults
to true. Set it to false and restart/redeploy to restore the optional consent dialog.

Validation: backend research unittest suite; local Chromium fixture with synthetic endpoints tests
no modal, no accept/decline controls, no pre-interaction collection, first-request transcript capture,
stop/deletion, globally disabled mode, and existing optional-mode provider/privacy regressions.
No live provider delivery or hosted deployment was performed. Repository protocol reserves
publication for Lior through Release Center (CLAUDE.md, Agent operating protocol).
