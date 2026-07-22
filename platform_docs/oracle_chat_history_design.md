_Last updated: 2026-07-20 12:34 UTC · Advisory · design + decision record for Oracle chat history (localStorage), voice dictation, and the path to real accounts_

# Oracle chat history & voice dictation — design and decision record

Four Oracle features are shipping in parallel (UI/UX in the mockup, Data Engineer on the SSE `status`
event). Two of them carry architectural weight and are the subject of this note:

- **Chat history with "save to pin"** — new conversations append to a History list; pressing save
  promotes a chat into a Pinned section above it. Persisted in the browser's `localStorage`.
- **Voice dictation** — microphone input in the Oracle composer via the browser's Web Speech API.

Both are the right calls for where MeatCODE is today. Both come with limits that must be stated out
loud rather than discovered later by Daniel or a WUR collaborator.

---

## 1. The identity problem (the crux)

The deployed site is protected by a **single shared password**. `server/meatcode_server.py` implements
HTTP Basic Auth: one username (`SITE_USER`, default `meatcode`) and one password (`SITE_PASSWORD`, set
in the Render dashboard), checked on every request. Everyone who has the link has the *same* credential.

The consequence is blunt and worth writing down: **the server cannot tell people apart.** Lior, Daniel,
a WUR researcher and anyone they forwarded the password to are, to the backend, literally the same
principal. There is no user id, no session, no per-person anything. So "his chat history" is not
something the server can store today — if we wrote chats to Neon, we would be writing them into one
undifferentiated pile that every visitor could read back. That is worse than not having history at all:
it looks like a personal feature while quietly being a shared one.

`localStorage` resolves this cleanly. The browser *is* the identity. Each person's history lives on
their own machine, in their own browser profile, and never touches the server. Nobody sees anybody
else's chats, no schema is invented for accounts we don't have, and no misleading promise of privacy is
made. This is not a shortcut around building auth — it is the honest expression of the trust model we
actually have. When real accounts arrive, localStorage becomes an import source, not wasted work.

## 2. What the localStorage approach genuinely cannot do

It is per-browser and per-device. Lior's laptop and Lior's phone will hold two unrelated histories, and
Safari and Chrome on the same laptop will hold two more. Nothing syncs, ever. Clearing site data,
resetting the browser, or using a private/incognito window wipes or bypasses it — a private-mode session
starts empty and discards everything on close. There is no backup and no recovery path: a lost history
is gone, including pinned chats. Storage is capped by the browser (commonly ~5 MB per origin), so the
implementation must bound what it keeps rather than grow forever. And `localStorage` can *throw* —
Safari with cross-site tracking restrictions, hardened privacy configurations, and quota-exceeded
conditions all raise on read or write, so every access needs a `try/catch` with a graceful in-memory
fallback (the feature degrades to "history for this tab only" instead of breaking the Oracle).

What a user should therefore **not** expect: that their history follows them between devices, survives a
browser cleanup, is backed up anywhere, or can be restored by us. Say this in the UI — one quiet line
under the History header ("Saved on this device only") costs nothing and prevents a bad surprise.

Concrete guardrails for the implementation: namespace the key (e.g. `meatcode.oracle.history.v1`) so a
future format change can migrate rather than collide; cap the list (roughly 25–30 conversations, prune
oldest **unpinned** first, never silently drop a pinned chat); truncate stored answer text; and ship a
visible **Clear history** control from day one — it is both a privacy tool and the escape hatch when the
stored blob gets corrupted.

## 3. Privacy — plain text, on someone else's machine

Oracle questions are stored unencrypted in the visitor's browser and are readable by anyone with access
to that browser profile, plus any devtools session. On a shared or lab machine, the next person to open
the site sees the previous person's research questions in the sidebar.

That matters more here than it would for a consumer app, because the questions are the sensitive part.
"Which thiamine-route precursors work in a pea-protein matrix at low water activity" reveals what GFI or
a partner is investigating well before any result is published. In a pre-competitive project where
partners (WUR, FSI, member companies) share a platform, a question log is a small but real leak of
strategic direction.

**Recommendation:** keep the storage local (do not move chats server-side while identity is shared),
label the History panel as device-local, keep the Clear-history control prominent, and add one sentence
to the Oracle's first-run/empty state: *questions are saved in this browser; use Clear history on a
shared computer.* No encryption theatre — a key stored next to the data protects nothing.

## 4. Voice dictation — the third party in the room

The Web Speech API is not evenly supported: Chrome and Edge implement `webkitSpeechRecognition`, Safari
has it with quirks, Firefox effectively does not. The mic button must be **feature-detected and hidden**
where unsupported, never shown-and-broken, and the composer must remain fully usable by typing.

The larger issue is where the audio goes. Chrome's implementation is **not** on-device: captured audio is
sent to Google's speech servers for transcription and the text comes back. So a spoken research question
leaves the machine and reaches a third party that is not GFI, not Neon and not Anthropic. For a
pre-competitive initiative with partner-sensitive topics, that is a real consideration, not a footnote —
and it is exactly the sort of thing a WUR legal or IP contact will ask about.

**Recommendation:** ship it, but disclose it. A short tooltip or helper line on the mic control —
*"Dictation uses your browser's speech service; audio may be processed by the browser vendor. For
sensitive questions, type instead."* — is enough, and it is honest. Request the microphone only on
click (never on page load), stop the recogniser as soon as dictation ends, and never auto-send: the
transcript lands in the input for the user to read and edit before submitting. Do not store audio.

## 5. Migration path to real accounts

The move to genuine per-user history is a small, well-understood project, and it should happen **before
any external rollout** where non-GFI people are named users — a WUR pilot is the natural trigger.

Sequencing, cheapest first: (1) replace raw Basic Auth with a **session cookie** — same shared password,
but a longer-lived signed session; this fixes the re-login friction already logged as an annoyance and
puts the session plumbing in place. (2) Add per-user login: a `users` table (id, email, name, org, hashed
password or — better — a magic-link / SSO provider so we never hold passwords), and swap the shared
credential for it. (3) Add `oracle_chats` (id, user_id, title, pinned, created_at, updated_at) and
`oracle_messages` (id, chat_id, role, content, sources jsonb, created_at) in Neon, with the usual
forward-only migration. (4) Add `GET/POST/PATCH/DELETE /api/chats` on `meatcode_server.py`, scoped by the
session's user id — the scoping is the whole point, so it must be enforced server-side, not in the
client. (5) Ship a **one-time import**: on first authenticated load, if a localStorage history exists,
offer "import your saved chats into your account", POST them, then mark the local copy migrated. Because
the client shape and the server shape are the same objects, this is a serialisation exercise, not a
rewrite — which is the main reason the current design is safe to build now.

**Should we do it now? No.** 2026 is the validation year, and auth is exactly the kind of infrastructure
that feels like progress while producing no validation evidence. The corpus, retrieval quality and the
Phase 1 literature target are what determine whether this project earns a Phase 4 scale-up; a login
screen is not. The roadmap already places "auth + feedback" as the *last* Oracle phase — that judgement
still holds. Build accounts when one of these becomes true: a named external partner needs their own
account; multiple people are provably sharing a machine or a password beyond a trusted circle; anything
partner-confidential is being entered; or cross-device history becomes a repeated real complaint rather
than a hypothetical.

One thing worth doing *sooner* and separately: an **anonymous, server-side log of Oracle questions** (no
identity, just question + timestamp + whether retrieval found sources). It needs no auth, and it is the
single best evidence source for the validation year — what people actually ask is the product signal
Daniel will want in Phase 3. It carries its own privacy weight, so it is a decision for Lior and Daniel,
not something to slip in: if adopted, disclose it in the UI and treat the log as internal-confidential.

## 6. Risks and recommendation summary

The real risks are small and mostly about expectation-setting, not engineering. **Perceived data loss** —
someone clears their browser, loses pinned chats, and concludes the product is unreliable; mitigate with
the device-local label. **Shared-machine exposure** — previous questions visible to the next user;
mitigate with the Clear-history control and the empty-state note. **Third-party audio** — spoken
questions transcribed by the browser vendor; mitigate with disclosure and a type-instead recommendation.
**Silent breakage** — `localStorage` throwing in privacy modes, or Firefox users seeing a dead mic
button; mitigate with `try/catch` plus feature detection. **Storage growth** — mitigate with a hard cap
that prunes unpinned chats first.

Recommendation, in order: ship both features as designed with the disclosures and guardrails above; do
**not** build accounts during the validation year; move the shared password to a session cookie when
re-login friction next comes up; and raise the anonymous question-log question with Daniel now, because
it is cheap, it is the most valuable validation instrument available, and it is the one item here that
genuinely needs a decision rather than an implementation.
