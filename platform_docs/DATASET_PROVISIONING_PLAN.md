# Governed module provisioning — implementation handoff

_Updated 2026-10-29 · Data/Advisory · Not deployed. Supersedes one-way-only master design._

## Approved direction

Reuse the existing master project; do not create a replacement or rename it blindly.
Create three separate projects in the same selected organization/region: proposed names
`meatcode-oracle`, `meatcode-ecosystem`, `meatcode-simulation`. Check existing projects first.
Each project has its own endpoint, credentials and independent compute settings. No root
credentials in module runtimes; no sibling credentials. Do not grant organization-wide edit access.

Child changes may enter master only after Lior approves their exact revision. Even changes
to prior child contributions require fresh approval. No inferred approval, model approval,
timeout approval or scheduled automatic approval.

## Provisioning sequence

1. Complete private backups of production AND dev, inventory all user databases/roles, and
   restore into an isolated disposable target. Current connection targets cover the configured
   application databases, not proof that every database in the Neon account is included.
2. Connect the Neon account; inspect organization/project IDs, region, plan and existing members.
   Reuse the actual master, create missing module projects, record resource IDs and costs.
3. Seed each with only its approved subset, preserving IDs and provenance. Do not full-clone
   private user research or broad reviewer/admin roles into collaborator projects.
4. Create SQL groups: viewer (published SELECT), contributor (published SELECT + own working
   records/revisions), module runtime, importer/publisher. People get individual logins;
   contributors receive no schema CREATE, role administration or cross-project credentials.
5. Implement append-only submissions and decisions in a private governance schema. Proposed
   fields: contribution UUID, origin component/project, original record ID, actor ID,
   source/evidence references, operation, base version, revision, payload, payload hash,
   submission time; decision separately records reviewer identity, approved revision/hash,
   timestamp and rejection reason. Reviewer identity comes from authenticated Lior, not request text.
6. Separate status: draft → submitted → approved/rejected → published. Submitted payloads
   are immutable; edits create new revisions. Publish compares approved hash and base version;
   stale-base conflicts return to review, never silently overwrite baseline records.
7. Restrict publisher SQL privileges to an approved-revision function/controlled path. Do not
   give a generic child service direct master DML. Keep approval and publication credentials
   distinct. Persist master update + audit + outbox event in one master transaction.
8. Deliver master outbox events to module inboxes; unique event IDs make retries idempotent.
   Track per-module applied version and failures. Preserve original contribution ID to prevent
   reimport loops. Update affected graph/vector/search indexes after publication. Support
   retractions and deletions as reviewed revisions, not untracked destructive operations.
9. Build a review screen with before/after data, evidence, origin, decisions and publication
   status. Only after its records and links exist should a digest automation be scheduled.
   User has not selected cadence. Do not poll a nonexistent queue or create fake notifications.
10. Verify using restricted logins: contributor cannot alter published base, master or sibling;
    cannot approve; changed payload cannot use earlier approval; failed publication is atomic;
    retried delivery produces one change; private memory never exports to shared knowledge.

## Known access and scope

Yochai is the requested Ecosystem collaborator. Lior owns all components and all master
approval. Pablo's Simulation access and Daniel's viewer scope are recommendations, not newly
authorized grants. Preserve Necmettin's already authorized read-only review access pending
an explicit policy change. Existing shared-site backup endpoints also need an access audit
before claiming that the master is accessible only to Lior; do not silently revoke them here.

## Current blocker and safe boundary

Plugin discovery reports Neon available but not installed/connected. SQL database credentials
do not authorize Neon control-plane project creation. No project creation, runtime rerouting,
collaborator invitation, schema migration or scheduler activation has been performed.
Prepare numbered migrations only against inspected target schemas. Backups are read-only.
New application services and automatic synchronization require implementation and verification;
creating a database project alone does not implement this workflow.
