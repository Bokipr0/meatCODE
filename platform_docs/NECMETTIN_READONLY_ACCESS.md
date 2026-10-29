# Necmettin architecture-review database access

_Last updated: 2026-10-29 · Codex._

Recipient: Necmettin Karakaya, necmettin.karakaya@gmail.com. Confirmed from his latest email, “Re: MeatCODE architecture review - moving forward”,29 October2026: he already has Neon project access but needs SQL schema and sample-record inspection, without writes.

## Applied and verified

Forward migration0018 created SQL role `necmettin_review_ro` on existing DEV then production branches. It has CONNECT, schema USAGE and SELECT on the current scientific relations:

- Production: public and moldedup,69 tables/views.
- Development: public, moldedup and lightrag_demo,76 tables/views including the development knowledge graph.

There are no administrator capabilities, role memberships, schema CREATE privileges, write privileges or future-table default grants. No scientific records were changed. Private user_research logs/feedback are excluded; current granted views do not cross into that schema. No sequence modification privileges or grant options were provided. Connection limit3; read-only transactions and15-second statement timeout are defaults, while actual ACLs enforce denial even when the read-only default is disabled.

Verified with the actual new login on each branch: SELECT one sample from every granted relation succeeds (contents not printed or saved); INSERT/UPDATE/DELETE with zero-row predicates are denied42501; user_research.feedback SELECT is denied42501. Role attributes and effective grants show no elevated privileges. No destructive DDL or truncation test was executed.

## Connect and hand off

Keep his existing Neon Viewer project access. Do not upgrade to Editor or share the owner/admin connection: Neon project metadata permissions are separate from SQL privileges, and Viewer does not expose database credentials.

The new direct PostgreSQL connection URLs are in the mode0600 private local file `/private/tmp/meatcode-necmettin-readonly-20261029.env`. This file is outside the application repository and web-serving directory. Share it only with Necmettin through a private channel; do not commit it, paste it into chat or a public URL, or include it in the architecture packet. It contains both NECMETTIN_PROD_DATABASE_URL and NECMETTIN_DEV_DATABASE_URL. Necmettin can use the relevant URL in his PostgreSQL client. Its database username is necmettin_review_ro; email is documented as the recipient, not the SQL username.

The credentials have **not been emailed or otherwise delivered** by this agent. File creation/account verification does not prove Necmettin has received them or connected. The private file lives in temporary storage; Lior should transfer it securely rather than relying on that file as a long-term password store.

If a future scientific relation needs inspection, grant SELECT on that named object after review. New private objects are deliberately not auto-shared. To revoke access, set the role NOLOGIN on each branch and, if immediate disconnection is necessary, terminate only that role’s sessions under a separately authorized action. Removing his Neon Viewer alone does not revoke SQL credentials.

## Evidence

- Migration: db/migrations/0018_necmettin_readonly_review.sql (no password).
- Credential-free verification: data/verification/necmettin-readonly-2026-10-29.json.
- Email: https://mail.google.com/mail/u/?authuser=lior.tep%40gmail.com#all/1a1880a20ff84799 .
- Neon limited-role guidance: https://neon.com/docs/manage/database-access . Roles were created through SQL so neon_superuser membership is never added.
