# How Denver's 30-second reminder works

Updated 3 November 2026. This feature runs in the browser; no model call, server timer or database change is involved.

## The three building blocks

1. **An event** tells the page something happened: a pointer moved, a key was pressed, an input changed, or the user scrolled.
2. **A timestamp** records when that activity happened. `performance.now()` gives elapsed milliseconds on a steady browser clock.
3. **A condition** compares the current time with the timestamp. After 30,000 milliseconds without activity, Denver displays “Still there?”.

The existing Denver animation loop already checks its state regularly, so the implementation reuses that loop instead of adding another repeating timer.

## Where to edit

- `app/assets/denver/denver-widget.js`: the component, event listeners, elapsed-time check and reminder buttons.
- `app/assets/denver/denver-oracle.js`: tells Denver whether Oracle is still answering.
- `pipeline/build_denver_companion.py`: combines the source scripts into the file the platform loads.
- `app/assets/denver/oracle-companion.js`: generated bundle; edit the source files above, then rebuild it.
- `app/meatcode_mockup.html`: loads the bundle with a version in its URL so browsers fetch the updated file.

## Change the delay yourself

Near the top of `denver-widget.js`:

```js
const DENVER_IDLE_PROMPT_MS = 30_000;
```

`30_000` and `30000` are the same number. The underscore only makes it easier to read. Use `60_000` for one minute.

The actual check lives in `idleMotion(now)`:

```js
const idle = now - this.idleSince;
if (idle >= DENVER_IDLE_PROMPT_MS && !this.inviteShown) {
  // Show the reminder once during this quiet period.
}
```

This excerpt omits the surrounding display guards for clarity. Keep those guards in the real code.

`touchDenver()` is the reset function: it sets `this.idleSince = performance.now()`, hides the reminder and allows a reminder in the next idle period. Document event listeners call this function for activity across the page. They use the event's timing only; they do not inspect typed text.

## Why the guards matter

- Opening a note, rating panel or dialog suspends the reminder.
- Oracle answering or a note being saved suspends it too.
- Hidden tabs and other modules do not show it. Returning starts a fresh idle window.
- The reminder is non-modal and does not move keyboard focus.
- “I’m here” restarts the clock; “Leave a note” opens the existing editor.
- Dismissal suppresses repeats until the user interacts again.
- Interactions inside the reminder are handled by its buttons; a global pointer listener must not hide a button before its click completes.
- Event listeners are removed when Denver is disconnected, preventing duplicate listeners after remounting.

## Rebuild and check

From the repository root:

```sh
python3 pipeline/build_denver_companion.py
python3 pipeline/build_denver_companion.py --check
```

Update the `oracle-companion.js?v=...` version in the HTML whenever the bundle changes. Browser tests in `tests/test_denver_client.cjs` use an accelerated clock to check the 30-second boundary without waiting half a minute for each assertion. They also cover activity resets, hidden tabs, pending answers, keyboard focus, dismissal and existing Denver behavior.

This is an inactivity estimate, not proof that a person has left: someone reading quietly for 30 seconds can see the prompt too. Browsers may delay background execution, so the delay is approximate rather than a real-time deadline.
