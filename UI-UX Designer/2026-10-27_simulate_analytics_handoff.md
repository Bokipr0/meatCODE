# Simulate sidebar and Analytics visibility

_Last updated: 2026-10-27 11:41 UTC · Codex UI/UX · local edits and current-main patch verified; unpublished._

The local `app/meatcode_mockup.html` now removes the three requested sections from the Simulate left sidebar: Recent simulations, SLR family, and Saved presets. Its profile card remains, and the inputs, condition controls, Predict action, output cards, and synthetic-result labels remain intact.

Analytics now appears in the top navigation when **Analytics zone** (`analytics`) is enabled in that environment. That chip opens the existing in-app `#analytics` workspace. The old `analytics_module` flag is used only when the flags response has no `analytics` key: an explicit `analytics:false` overrides `analytics_module:true`. The `analytics_workspace` flag still controls the Dev Area listing; it is not an extra requirement for opening Analytics in the platform. Preview, illustrative, estimate, and demo-dataset labels remain unchanged.

## Publication safety

GitHub main was inspected through the connected GitHub tool before editing. Its mockup blob was `850b4a208c83ebfe9c1754e463baa48540b403d5`. It contains Science, Ecosystem, guided Oracle, and hidden-Research navigation changes that are absent from this local checkout. The local file has **not** been replaced with main, and publishing this stale local file wholesale could regress those newer modules.

`2026-10-27_simulate_analytics_main.patch` applies these same surgical changes to that inspected main version while preserving the newer modules. The patch was applied to a temporary copy with the system `patch` tool and matched the browser-verified candidate exactly. Reconcile the local checkout with the current remote through the normal Release Center workflow before publication; if main has advanced again, inspect/rebase this small patch against it. No commit, deployment, feature-toggle value, database, or environment variable was changed by this UI work.

## Verification

- Every nonempty inline script passes `node --check`: 14 in the local file, 17 in the patched current-main candidate.
- Isolated headless Chromium exercised both versions using delayed local API fixtures: Analytics zone alone displays the nav chip, click opens the workspace, the deep-linked scene highlights the chip, the legacy-only registry still works, and explicit Analytics OFF overrides a legacy ON.
- Both versions remove exactly the requested Simulate sections and retain the profile and Predict action. The Analytics iframe renders its existing honesty labels. Current-main Science and Ecosystem nav chips remain present.
- No browser JavaScript errors in either version. Browser fixtures tested the UI, not live database/model availability; parent investigation covers Oracle/Render separately.

## Ready-to-paste log entry

2026-10-27 11:41 UTC · Codex UI/UX — Removed Simulate sidebar Recent simulations/SLR family/Saved presets from `app/meatcode_mockup.html`; preserved profile, controls, Predict/results, and synthetic warnings. Fixed Analytics nav to follow canonical `analytics` zone flag, with `analytics_module` fallback only when canonical key is absent, so explicit OFF wins. Coordinated registry semantics with Release Controls. Compared GitHub main before edits and preserved newer Science/Ecosystem/guided Oracle code via exact main-applicable patch in `UI-UX Designer/2026-10-27_simulate_analytics_main.patch`; local checkout remains stale and needs reconciliation before publication. Node syntax checks (14 local/17 main scripts), clean patch application, and isolated Chromium interaction checks passed, with zero page errors. No commit/deploy/external mutation; parent coordinates publication and shared state.
