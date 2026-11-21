<!-- Last updated: 2026-11-21 UTC · Claude (Sonnet 5.5) · NEW — runbook for individual accounts + "Connect your Claude organization" (flag user_accounts) -->
# Individual accounts + "Connect your Claude organization" — setup runbook

**What it is.** A landing page (`/welcome`), an account page (`/account`: sign in / create account), a dedicated **Link your Claude organization** screen (`/connect`, Anthropic's official button) and per-person billing: when a signed-in individual asks the Oracle, the request is billed to
*their own* Claude organization through Anthropic's **Claude Platform OAuth → Linked billing** (Beta).
Docs: <https://platform.claude.com/docs/en/manage-claude/oauth-apps/overview> ·
<https://platform.claude.com/docs/en/manage-claude/oauth-apps/organization-billing-connections> ·
Render side: <https://render.com/docs/oidc>.

**Ships dark.** Flag `user_accounts` is OFF in dev and prod. With it off the site is exactly what it was
(one shared password, our key) — the test `tests/test_accounts_server.py::FlagOffTests` pins that.

## How it behaves once on
| Visitor | Gets in with | Oracle / LLM calls are paid by |
|---|---|---|
| Team (shared password) | Basic Auth, as today | **Our** `ANTHROPIC_API_KEY` — unchanged |
| Individual, signed in, **connected** | Email + password session | **Their** Claude organization (`billing_policy.bill_to = user_profile`) |
| Individual, signed in, **not connected** | Email + password session | Nobody — the Oracle answers `402 connect_claude` and the UI points to `/connect`. **Never our key.** |

Covered routes: `/api/ask` (single + guided + consensus), `/api/graph-oracle/ask`, `/api/ecosystem/intent`, `/api/consensus-demo`.
Linking is **not** a "sign in with Claude": Anthropic's flow authorizes *billing* for an organization (approver must be Admin/Billing),
it does not identify a person. Identity is the MeatCODE email + password account.

## One-time setup (in this order — dev service first)
1. **Decide / check** (you): Render workspace is **Pro or higher** (managed OIDC requires it). You are Admin of the Claude
   organization that will own the app (MeatCODE's org — this is the org whose rate limits, model access and data retention apply to linked users' requests).
2. **Apply the migration to dev Neon:** `db/migrations/0031_user_accounts_claude_link.sql` (idempotent; three new tables, nothing existing touched).
3. **Render → Claude API identity (Render docs, "Anthropic" tab):**
   - Console → *Service accounts* → create one with the **Developer** role.
   - Console → *Workload identity federation* → *Issuers* → Custom OIDC, issuer `https://oidc.render.com/<WORKSPACE_ID>` (starts `tea-`), JWKS = OIDC discovery.
   - *Rules* → new rule: subject pattern `workspace:<tea-…>:environment:<evm-… or default>:service:<srv-… or *>`, **expected audience `api.anthropic.com`**, token lifetime **≥ 30 min**.
   - Render dashboard (dev service) → set `ANTHROPIC_FEDERATION_RULE_ID`, `ANTHROPIC_ORGANIZATION_ID`, `ANTHROPIC_SERVICE_ACCOUNT_ID`, `ANTHROPIC_WORKSPACE_ID`, redeploy. Render then sets `ANTHROPIC_IDENTITY_TOKEN_FILE` itself — **don't set it by hand.**
4. **Claude OAuth app** (Console → *OAuth apps* → Create):
   - Name (users see it on Claude's approval page), redirect URI `https://<host>/claude/billing/callback`, capability **Bill and link to organizations**. Copy the **client ID**.
   - *Client authentication* tab: pick the Render issuer + subject pattern, choose the service account from step 3 as the **operator service account**, set a **default workspace** for the app. Note the **expected audience** the tab shows — see Open risk 1.
   - *Permissions* tab → Billing → `billing:attribution`.
   - Status starts as **Test users only**: add the people who will test. Publishing is a separate step (below).
5. **Render env (dev):** `CLAUDE_OAUTH_CLIENT_ID`, `CLAUDE_OAUTH_REDIRECT_URI` (exactly the registered URI), `SIGNUP_MODE=invite`, `SIGNUP_INVITE_CODE=<a code you choose>`. (Names are also listed, commented out, in `render.yaml`.)
6. **Release Center:** turn `user_accounts` ON for dev, `deploy-dev.command`. Open `/connect` — the page lists anything still unconfigured (dev only).
7. **Test as a customer:** create an account with the invite code → *Connect your Claude organization* → approve as a Console user with Admin/Billing who is on the Test-users list → Console → *User profiles* shows the profile **Linked** → ask the Oracle → confirm the usage lands on that organization → *Disconnect* → Oracle answers 402 again.

## Before production (decisions for you / Daniel)
- **Publish the OAuth app.** Unless your org has invoiced billing, Anthropic requires a **DNS TXT proof of the app's homepage domain** and reviews the app. An `onrender.com` address can't be DNS-proven → production needs a **custom domain** on the Render service (redirect URI + homepage on that domain).
- **Sign-up policy.** Default is invitation-only. `open` would let anyone create an account and **read the same corpus API as the team** (signed-in individuals count as authorized, same as shared-password users). Their LLM spend is theirs, but the data exposure is a product call.
- **Privacy wording.** Linked requests run **in MeatCODE's Claude organization**: *our* data-retention terms apply, and the customer's own ZDR / BAA / CMEK arrangements do not. Don't link anyone who needs HIPAA/FERPA/CMEK coverage. Say so on the account page if this goes public.
- **Support.** Anthropic hosts the approval page and the spend-cap / unlink page; every other question from linked users comes to us.

## Open risks I could not verify from here (check on dev, in this order)
1. **Client-assertion audience.** The OAuth app requires the client-assertion JWT's `aud` to equal the value on its *Client authentication* tab. Render issues one token with `aud = api.anthropic.com`. If the tab expects `api.anthropic.com`, it just works. If it expects something else, Render's single token file can't satisfy it (Anthropic's docs suggest a second token file; Render documents none) — then linking needs a different identity provider for the assertion. `CLAUDE_OAUTH_ASSERTION_TOKEN_FILE` is the supported override if you get a second file. *Symptom:* "Claude didn't accept the linking request" and `[claude-link] PAR refused … invalid_client` in the server log.
2. **`ANTHROPIC_API_KEY` next to federation.** Anthropic's guide says the key must not be set when the app authenticates by federation; the shared-password team still needs it. The operator client is built with explicit `credentials=` — confirm in Console → *Workload identity federation → authentication history* that the operator's calls authenticate via the rule (not the key). If they don't, billed requests won't attribute to the customer.
3. **SDK version.** `requirements.txt` now needs `anthropic>=0.99` (has Workload Identity Federation). The native `user_profiles` resource arrives in 2.x; `claude_link.create_user_profile` falls back to a plain POST on older SDKs — unexercised against the real API.
4. **The real round trip** (PAR → approval → token exchange → billed request) has only been tested against fakes. Step 7 above is the first real run.

## Known limits (by Anthropic's design)
- Linking needs an organization that **pays Anthropic directly** (credits or invoice). A Claude chat subscription alone, or an AWS/GCP/Azure-marketplace org, is refused at request time (`403 user_profile_not_billable`); no credit → `402`. The UI currently shows these as a generic Oracle error — a worthwhile follow-up message.
- `billing_policy` is not supported on Message Batches or with billable code-execution tools (neither is used by MeatCODE today).
- "Connected" means linked, not "billing is active".

## Security notes
- No Claude secret is stored. The per-connection access token that Anthropic returns at link time is discarded; only `user_profile_id` and `connection_id` are kept.
- The user-profile ID on a billed request comes from the signed-in session, never from request input. The operator credential *could* bill any linked profile, so keep that rule. Later hardening: per-connection tokens + the app's `disable_operator_only_auth` (needs `offline_access` and encrypted refresh-token storage).
- Passwords: scrypt. Sessions: random token in an HttpOnly, SameSite=Lax (Secure on https) cookie; only its SHA-256 is stored. Sign-up/login are throttled per IP *and* per email, and every account POST is same-origin + JSON-only.
- Profiles are named `MeatCODE user <id>` — no email or name is sent to Anthropic.
- Throttle state is per process (Render runs one instance); the IP comes from `X-Forwarded-For` and can be spoofed, which is why the per-email limit exists.
- A double-click on *Connect* the first time can create one orphan profile in our Claude org (the DB keeps one). Harmless; archive from the Console.
