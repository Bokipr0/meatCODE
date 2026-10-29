# Five-user Oracle demo check

_Updated 2026-10-29 · Local implementation; hosted capacity not yet measured._

## Inventory visibility

Release Center now has **Inventory button**, with independent development and production
switches. Both default ON to preserve current behavior. OFF hides every Inventory topbar
button and prevents its saved-items drawer opening; existing saved items stay in the browser.
**Highlight Inventory** remains a separate appearance setting. This is visibility, not an
access-control restriction on database exports or other endpoints. Publish the local changes
through the existing release process before expecting the new switch on hosted builds.

## Run the live check

Double-click `Release Center/test-five-users.command`. Enter the shared site username and
password when prompted. The password is hidden and not saved. The default target is production,
`https://meatcode-oracle.onrender.com`. This makes five real model requests and uses provider quota.
To test a different environment, from the repository run:

```sh
python3 pipeline/oracle_five_user_check.py --url https://YOUR-STAGING-HOST
```

Five independent HTTP clients each load the application page, then submit distinct scientific
questions simultaneously. This is a bounded concurrency smoke test, not five browser windows.
It uses the single-turn Oracle route, not the optional guided conversation flow. It does not
create research-consent sessions or modify the scientific corpus. Server/provider logs can
still record activity. It does not deploy anything.

The terminal shows completed/failed requests, time to first answer text, total time and source
counts. A private JSON report in `data/demo_checks/` contains the questions, full answers,
timings and status. Five completions with each answer's own unique marker and no foreign
marker are a useful smoke-test result. Missing markers need review: models can ignore the
instruction. Passing markers cannot prove privacy or answer correctness. Review sources and
answer relevance as well; zero sources is reported rather than treated as scientific grounding.

## Verification and limits

The offline harness tests confirmed five overlapping requests and detection of incomplete
streams against a synthetic local server. No hosted five-user result has been claimed.
Browser history isolation, guided follow-ups, research capture, access permissions and sustained
load need separate checks before calling the demo ready. Individual requests have a 180-second
read timeout and elapsed-time checks between received lines; this is not a strict wall-clock SLA.
