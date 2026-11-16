# Hosted MeatCODE MCP — invited collaborators

_Last updated: 2026-11-16 21:40 UTC · Codex · Render live and OAuth configured; owner sign-in verification pending._

## Architecture

Collaborator's ChatGPT → OAuth 2.1 / PKCE with Neon Auth → Render scientific MCP → existing Neon science connections. The existing Oracle website, Claude reasoning endpoint, research logs and personal local tunnel are independent.

This is a separate Python web service built with `sh scripts/mcp/build_hosted.sh` and started with `python -m server.mcp_pilot.hosted`. It listens on Render's `PORT`, exposes `/mcp`, and serves its login, consent and connection instructions. A paid Starter instance avoids free-service idle suspension. `/healthz` identifies the source revision. Runtime startup refuses missing identity, invitations or either scientific database connection.

## Identity and invitations

Managed Better Auth was enabled on the existing production branch, adding its managed `neon_auth` schema without changing the platform's shared login. The issuer is returned by Neon, not constructed from a database host. OAuth provider configuration must point at the deployed `/auth/sign-in`, `/auth/consent` and exact `/mcp` resource. Enable CIMD; leave dynamic client registration disabled. Configure the deployed origin as trusted and disable localhost for this identity service.

Email OTP verifies mailbox ownership. Users approve the named client and requested scopes on the consent page. The Neon SDK 0.8.2 preserves the signed authorization query and completes the redirect. Browser secrets and codes are never written to server logs or analytics.

On every MCP request, the server verifies EdDSA signature, exact branch issuer, exact MCP audience, expiration, subject, client ID and `openid email` scopes. It then verifies subject/email via the fixed issuer's userinfo endpoint. Only verified invited emails are accepted. Userinfo results are cached for at most 60 seconds and never beyond token expiry; cache keys are token hashes. Invitation authorization is checked on each request. An identity-provider outage fails closed. Authentication or an invitation hint in the browser never replaces this server check.

The owner-approved addresses are configured privately in Render's `MCP_INVITED_EMAILS`, including both of Yochai's provided addresses and Daniel's confirmed contact address, plus the owner's address for verification. Remove an address and redeploy to revoke its scientific access, including with an existing access token. Neon account registration itself is not the scientific authorization boundary.

Neon currently supplies shared SMTP for OTP delivery. This is suitable for the invited pilot; Neon recommends a custom mail provider for a production rollout and higher delivery limits. No SMTP credentials were invented or copied from chat. Shared development Google OAuth credentials are not used by this login page.

## Scientific privileges

`scripts/mcp/provision_reader.py` created `meatcode_mcp_science_ro` separately on production and development, with independent random credentials. The role has no superuser, database creation, role creation, replication or RLS bypass privileges. It gets SELECT on only the source columns required by the bounded tools; the development role additionally reads the six existing graph projection tables. No future-table default grant, raw `abstract` grant, user-chat grant, write grant or account-management tool is added.

Both roles default to read-only transactions and a five-second statement timeout; the adapter independently enforces the same restrictions. The three tools remain search, fetch and search_knowledge_graph. Graph retrieval remains the three-paper extracted demo using lexical/one-hop retrieval, not vectors or independent scientific validation.

Credentials are in ignored `data/mcp-pilot/hosted-env.json`, mode 0600, and transferred directly to the new Render service's secure environment. They are not in Git, the front end, shared links or collaborator emails. No Anthropic/OpenAI key is required by this retrieval adapter; the caller's ChatGPT supplies answer generation.

## Verification

Offline security tests cover anonymous discovery protection, exact metadata, rejected host headers, configuration failure, invite enforcement, verified email, wrong branch/resource, expired/invalid tokens, missing scopes, userinfo mismatch and identity outages. Live role tests returned literature/graph results and rejected writes and raw abstract reads with 42501. Production auth-schema access was denied; the development branch has no such auth table (42P01).

Before calling deployment complete: verify Render deploy is live, `/healthz` matches the intended commit, unauthenticated `/mcp` returns 401, discovery names the right issuer/resource, real owner sign-in/consent completes, and an authenticated ChatGPT scientific call succeeds. Do not seed tester logs. Collaborator account acceptance must be reported separately from invitations being sent.

## Share instructions

Send the deployed connection page to invited collaborators. Each signs into their own ChatGPT account and adds the service's `/mcp` address as a custom MCP server using OAuth, subject to their ChatGPT account/workspace policies. A published public-directory plugin is a separate process; a plain link does not automatically install an unpublished custom plugin in another account.

References: https://developers.openai.com/plugins/deploy/connect-chatgpt · https://developers.openai.com/plugins/build/auth · https://neon.com/docs/auth/guides/plugins/oauth-provider · https://neon.com/docs/auth/guides/plugins/email-otp · https://render.com/docs/deploys

## Deployment observed — 16 November 2026

Connection page: https://meatcode-mcp.onrender.com/ . MCP resource: https://meatcode-mcp.onrender.com/mcp . Render service `srv-dbtfjv49v7es73agd5vg` in My Workspace / Frankfurt, Starter plan. Dedicated Git branch `codex/private-mcp-pilot`, source `eb8e50fb0cadb72c9622c6cf82f484907cd904e7`. Deployment `dep-dbtfk049v7es73agd9gg` reached live and `/healthz` matched the exact source. The existing website main/dev deployments were not changed.

Live HTTP checks: home/script/config/discovery 200; unauthenticated MCP 401 with correct resource metadata challenge; Neon discovery advertises S256 and CIMD; all three collaborator addresses accepted by invitation check and outsider rejected. OAuth server configured with the exact hosted resource, login and consent pages. Auth verification codes enabled, localhost disabled, only hosted origin trusted. The sign-in UI accepted the owner OTP request; owner was asked to enter it directly in the browser. Full authenticated hosted ChatGPT retrieval remains pending until that handoff finishes. Render connector log retrieval returned a transient 503; live deploy metadata and direct HTTPS checks succeeded.

The authenticated local HTTP protocol fixture also passed using a real EdDSA-signed token plus mocked OIDC userinfo: initialize, exact three-tool discovery, scientific search and refusal of arbitrary SQL. Total focused tests: 12. This does not replace the pending real Neon OAuth browser flow.

ChatGPT created the hosted custom-plugin entry and reached its connection-disclosure dialog. Automatic approval review rejected the final Connect action because relevant chats/memories might be shared beyond the previously authorized scope. User approval was requested; do not retry until it arrives. The service remains protected, and collaborator invitation emails have not been sent.
