# MeatCODE — governed datasets and permissions

_29 October 2026 · Agreed approval rule; infrastructure provisioning pending Neon connection._

**Flow:** Master → approved module copies → child contributions → Lior's review → master → affected modules. No child has credentials to write directly into the master. Tags record origin; your approval controls admission.

## Components and collaborators

- **Master / Lior:** Owns the shared record, access policy, backup recovery and final approval. Existing records are tagged as the baseline at migration; baseline does not mean scientifically verified. New contributions retain their component, project, contributor and source identity.
- **Oracle / Lior:** Reads published scientific evidence and maintains its own derived indexes and private user context. Proposed scientific additions enter the review queue. Personal memory, prompts and feedback do not become shared scientific knowledge by default. Additional collaborator not assigned.
- **Ecosystem / Yochai; Lior owner:** Yochai can read its published base and add/edit working ecosystem records. He submits changes for your review; cannot modify the master, sibling datasets, shared base or permissions.
- **Simulation / Lior owner; Pablo proposed collaborator:** Stores models, inputs and run outputs. If assigned, Pablo can contribute simulation records within this component. Predictions remain labelled predictions and require your approval before entering shared knowledge. No new account grant until collaborator assignment is confirmed.
- **Review / Lior only:** Sees added, modified and withdrawn records with before/after differences and provenance. Approves or rejects a specific immutable revision. A later edit requires fresh approval; rejected or pending records never propagate.

## Simple roles

- **Owner:** Lior. Manage a component and its access; only Lior can approve master publication.
- **Contributor:** Read the assigned module's published data; write working records and submit revisions. No master/sibling/admin access.
- **Viewer:** Read only explicitly shared records. Daniel is a proposed stakeholder viewer; scope is not yet granted. Necmettin's existing scientific read-only review access is preserved, not expanded.
- **Publisher service:** Applies only the exact revision approved by Lior; distributes versioned updates. No permission to approve. Module applications use separate service credentials.

## Safe updates, notifications and backups

- Every contribution carries origin component/project, source record, contributor, time, evidence, revision/hash and review decision. Preserve original identity when redistributing, preventing Ecosystem → master → Oracle → master duplication loops.
- Accepted updates publish as versions: Ecosystem can inform Oracle through the master. Delivery is asynchronous with retry/deduplication; modules may briefly show different versions. No claim of simultaneous cross-database transactions.
- A scheduled digest will list pending changes, age and review links; it will never approve or publish. Frequency and review interface remain undecided; no schedule activated.
- Take a full production and development database backup before restructuring. Keep private archives outside publication, verify archive integrity, and run a restore drill before migration. Refresh/export jobs must preserve module-owned additions.

**Deployment status:** Existing databases remain in place. Three separate Neon module projects, contributor accounts, the approval interface and synchronization jobs are not live yet. Neon account authorization is required to provision the projects.
