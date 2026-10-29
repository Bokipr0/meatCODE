# MeatCODE user-testing model

_Last updated: 2026-10-28 15:47 UTC · Project Coordinator · initial model for the user-requested Clarity integration._

MeatCODE is a research platform for flavor and aroma: the Oracle answers literature questions, Science/Research and Ecosystem expose scientific and collaborator resources, and Simulate and Analytics provide additional workflows. The production and dev sites are separate Render services. The current code uses a shared site-password gate, not individual account authentication.

The primary testing question is whether a researcher can obtain a useful Oracle answer and move through the relevant modules without encountering an error. The initial research slice measures navigation adoption, Oracle submissions/completions/failures and duration, and voluntarily submitted ratings/comments. Clarity complements these with masked replay and heatmaps.

Entities are an anonymous browser-tab session, an event, a submitted feedback item, a minimal withdrawal tombstone, and an imported aggregate snapshot. There is no account/organization hierarchy and no cross-device identity. Session count is not a distinct-person count. Dev/prod are recorded separately even when databases or the Clarity project are shared.

Destinations are Microsoft Clarity project z4upnrbddu and the private Neon user_research schema. Scientific evidence, graph entities and embeddings remain separate. Testing feedback is not admitted as scientific evidence or used to train a model automatically. Raw prompts, model answers, attachments, names and email addresses are excluded from event payloads. A tester may deliberately submit a free-text comment to first-party storage only.

This is the initial user-testing instrumentation, not a claim of a full product-wide tracking audit or production activation. Internal testers are included because this phase is user testing; automated QA uses mocks or transactions that are rolled back.

## 2026-10-29 extension

Added PostHog EU project325792 for explicit event analysis and a private MeatCODE dashboard over Neon. The native dashboard contains six charts, including Oracle outcomes and latency; the local dashboard refreshes every three seconds. These destinations retain independent anonymous identities. Historical QA used mocked providers and rolled-back database probes; one real consented dev browser verification, if performed, is reported separately. Neither dashboard is evidence of complete user coverage or scientific answer quality.
