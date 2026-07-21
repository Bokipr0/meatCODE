_Last updated: 2026-07-21 12:14 UTC · Advisory · new note: the chats + Lab Stash cache already exists (localStorage), private-window caveat, durability options ranked_

# The chats + Lab Stash cache — what exists, why things "disappear," and how to make it durable

Lior asked for "a cache in which chats + Lab Stash information will be saved." **That cache already
exists and already saves both.** This note explains what it is, the one caveat that almost certainly
explains the disappearing data, the honest limits, and the ranked options for making it more durable.
It is the Lab-Stash companion to `docs/oracle_chat_history_design.md` (chat history + accounts) — same
trust model, same conclusion.

---

## 1. What exists today

Both features already persist client-side in the browser's `localStorage`, verified in
`app/meatcode_mockup.html`:

| Data | Key | Cap | Behaviour |
|---|---|---|---|
| Oracle chats (pinned + history) | `mc_oracle_history_v1` | 25 per list | append on ask; bookmark promotes to Pinned |
| Lab Stash (saved highlights) | `mc_lab_stash_v1` | 100 items | highlight in an answer → Save → filed under its question |

Both are **versioned keys** (`…_v1`, so a future format change can migrate instead of collide),
**bounded** (caps stop unbounded growth), and every read/write is **wrapped in `try/catch`** so a storage
failure degrades to "works for this session, just won't persist" instead of breaking the Oracle. This
IS the cache. No new storage layer needs to be built for the ask as stated.

## 2. The one caveat that almost certainly explains "disappearing" data — private windows

Lior has been testing in a Safari **Private window** (visible in the screenshots). In private/incognito
mode `localStorage` is **ephemeral**: it is isolated to that private session and **wiped the moment the
window closes**. So chats and stash items vanishing between sessions is almost certainly this — the code
is doing exactly what it should; the private window is throwing the saved copy away on close. The mockup
even comments this in place ("private mode: the rail/stash still works for this session, just won't
persist").

**Test to confirm:** open the site in a **normal (non-private) Safari or Chrome window**, save a chat and
a stash item, fully quit and reopen the browser. They will still be there. Normal windows persist across
restarts; private windows do not. This is the single most likely explanation and worth ruling in first
before treating anything as a bug.

## 3. The other honest limits of localStorage

Real, but mostly about expectation-setting, not bugs:
- **Per-browser and per-device.** Lior's laptop and phone hold two unrelated stashes; Safari and Chrome
  on the same laptop hold two more. **Nothing syncs, ever.**
- **Not shared between users.** By design — the stash lives on each person's machine. Good for privacy
  (nobody sees anyone else's saved snippets), but it means there is no "team stash."
- **Cleared if the user clears site data** or resets the browser. No backup, no recovery path from us.
- **Capped (~5–10 MB per origin).** Ample for text chats/snippets; the in-code caps (25 / 100) keep us
  well under it.

## 4. Why client-side is the correct call today (the architecture constraint)

The deployed site sits behind **one shared password** (HTTP Basic Auth in `server/meatcode_server.py`).
Everyone with the link is the *same* principal to the backend — **no user id, no session, no per-person
identity.** So the server cannot store "his" chats or "his" stash: writing them to Neon would put every
visitor's data into one undifferentiated pile that every other visitor could read back. That is worse
than local storage — it looks private while quietly being shared. `localStorage` makes the browser the
identity, which is the honest expression of the trust model we actually have. This matches the standing
decision in `oracle_chat_history_design.md`.

## 5. Durability options, ranked

**(a) Keep localStorage; just set the expectation.** — RECOMMENDED, now.
Cheapest and already correct. Add one quiet UI line ("Saved on this device — use a normal, non-private
window to keep them") and a visible **Clear** control. Zero backend work, no identity needed. This alone
resolves the reported symptom.

**(b) Add an Export / Import button.** — Recommended near-term add.
A "Download my chats + stash" button serialises both keys to a JSON file; an "Import" button reads one
back. This buys **real durability and cross-device/cross-browser transfer with no accounts and no
server** — a backup Lior can keep and reload, or move from laptop to phone. Small, self-contained,
client-only; it fits the validation year. The best value-for-effort upgrade here.

**(c) Real per-user accounts + server-side store.** — The proper long-term answer; defer.
Needs login (users table + magic-link/SSO), `oracle_chats`/stash tables in Neon, and per-user-scoped
API. It is the only thing that gives true cross-device sync and recovery — but it is infrastructure that
produces no validation evidence in 2026. Because the client and server data shapes are the same objects,
today's localStorage becomes a one-time **import source**, not wasted work. **Trigger on a named event —
a WUR / external partner needing their own account — not on a date.**

**Not an option: an anonymous *shared* server store.** Persisting chats/stash server-side *without*
login would make every visitor's saved snippets visible to every other visitor (one shared password =
one shared pile). It looks like a personal feature while being a shared one — do not do this. (Distinct
from an *anonymous question log* for validation evidence, which is a separate, deliberate decision for
Lior + Daniel — see the history design doc.)

## 6. Recommendation

1. **Reassure + relabel (today):** the data is not being lost to a bug — it's the Safari Private window.
   Confirm in a normal window, then add the one-line "saved on this device" note so no one is surprised.
2. **Build Export / Import next:** cheap, account-free durability and cross-device transfer. Defer real
   accounts until a named external/WUR user needs one.
