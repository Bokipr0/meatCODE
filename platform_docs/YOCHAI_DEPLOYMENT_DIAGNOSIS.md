# Yochai's separate MeatCODE deployment

_Last updated: 2026-10-26 12:57 UTC · Codex / Advisory · Render connected; separate service and missing-key startup failure confirmed._

## Confirmed diagnosis after connecting Render

The service in the screenshot is a separate resource created on 25 October, not the original production service:

| Role | Render name / ID | URL | Branch / latest deploy |
|---|---|---|---|
| Original production | MeatCODE / `srv-d96ftplaeets73da7vng` | https://meatcode-oracle.onrender.com | main / live |
| Existing staging | dev-meatCODE / `srv-d9ghriu1a83c73dr8lj0` | https://meatcode.onrender.com | dev |
| New failed resource | meatcode-oracle / `srv-dbf5eb5g1s2s73ei0td0` | https://meatcode-oracle-0o99.onrender.com | main / update_failed |

All three belong to the accessible My Workspace and are in Oregon. The new service already has its own resource identity, URL and Starter instance. Reuse it for Yochai; creating another sandbox is unnecessary.

The latest failed deployment is `dep-dbfg01rbc2fs73959200`, commit `6394c039749ad0e6d7279dabd00a380dfb95ee87`. Build succeeds; then the configured start command runs and exits with status 1:

```text
2026-10-26 07:24:16 UTC: Build successful
2026-10-26 07:24:30 UTC: Running 'python3 server/meatcode_server.py'
2026-10-26 07:24:31 UTC: ERROR: ANTHROPIC_API_KEY is not set.
2026-10-26 07:24:37 UTC: Exited with status 1
```

This confirms a missing model credential at startup. It is not a cloning error, dependency installation failure, incorrect server path, or evidence that separate servers cannot work. The same commit is live on original production (`dep-dbfg01rbc2fs739591r0`). The latest four returned deploys on the new service all failed; no successful deploy appeared in that returned history.

Render MCP is now connected. Services, deploys and scoped logs were inspected read-only. Secret environment values were neither read nor copied; actual database and site-password configuration on the failed service is not verified by the available service-details response.

## Repair and independence

1. On the **new failed resource**, provision `ANTHROPIC_API_KEY` in Environment. Prefer Yochai's own credential; reusing Lior's credential needs an explicit billing/access decision. Keep the value in Render, not chat or Git. No usable new-service key was supplied in this task.
2. Verify `SITE_PASSWORD` and the intended non-production `DATABASE_URL` on this resource before making it usable. These were not established by the startup log and must not be assumed to have copied from production.
3. Redeploy that resource, then verify its version/health and an authenticated database endpoint. Do not redeploy or change the original production service to repair this resource.
4. For independent development, give Yochai an agreed branch and `APP_ENV=dev`, plus a dedicated Neon branch/role and credential. The existing service currently follows main, and the root Blueprint declares prod settings; it is a separate process but not an independent code-release track yet.
5. Keep the existing service ID. Ensure its managing Blueprint's linked branch and YAML agree with the intended Yochai branch/env so a later sync does not overwrite dashboard-only changes. Inspect Blueprint ownership before changing names, moving management or publishing configuration.

Direct service dashboard: https://dashboard.render.com/web/srv-dbf5eb5g1s2s73ei0td0

The earlier `deployment_templates/render.yochai.example.yaml` is retained only as a configuration reference for creating a new sandbox elsewhere. **Do not create another service from it for this repair.** It still has an explicit uncreated branch placeholder and was never activated.

The local checkout is behind newer remote main Science/Ecosystem code. No pull, merge or overwrite was run. Service ownership confirms the failed resource is in Lior's Render workspace; the API does not establish which individual clicked Create.

## Read the failed deployment before retrying

Open the service itself under the Blueprint, then its failed deployment/event. Capture:

1. Service ID and URL, workspace and region.
2. Branch, failed commit and last successful commit (if any).
3. Whether failure occurred at clone, build, startup or health check; first error line plus relevant traceback.
4. Root Directory, Build Command, Start Command, Python version, Health Check Path.
5. Environment variable names/presence only; keep secret values inside Render.

Use the Render integration or the service's Events/Logs page. A Blueprint sync error and a runtime deploy error are different: inspect Syncs if no deployment was created.

| Observed error | Likely next action |
|---|---|
| Repository permission / clone failure | Give the correct Render GitHub connection access to this private repository; check the selected branch exists. GitHub collaborator access does not by itself grant Render workspace access. |
| `requirements.txt` not found | Set Root Directory to the repository root; the build command expects root requirements. |
| Cannot open `server/meatcode_server.py` | Keep Root Directory at repo root with the full start path, or adjust both paths consistently. |
| `ModuleNotFoundError` / dependency build failure | Check the exact module and install log for that commit before changing dependencies. |
| No open ports / startup or health timeout | Check that the configured command runs the long-lived server, binds `0.0.0.0:$PORT`, and uses `/api/health`. Current remote code supports this; a wrong command or branch can still fail. |
| Database endpoint or Oracle fails after the site starts | Configure that service's own `DATABASE_URL` and `ANTHROPIC_API_KEY`; inspect the specific request error. Missing app credentials alone are not proof of a build failure. |
| Blueprint sync succeeds but new secret is absent | For an existing Blueprint, `sync: false` does not prompt for newly added secret values. Add them to the individual service environment. |

Retry only after correcting the confirmed cause. Do not use the screenshot's Manual sync button to experiment with production settings.

## Reference configuration for a future independent sandbox

The proposal is saved in `deployment_templates/render.yochai.example.yaml`. It is outside the root production Blueprint and has not been activated.

| Setting | Proposed value |
|---|---|
| Repository | `Bokipr0/meatCODE` |
| Branch | A new agreed Yochai branch based on the chosen current remote commit; template has an explicit placeholder |
| Name | `meatcode-yochai` (verify availability before creation) |
| Root Directory | Repository root / blank |
| Runtime | Python 3.12.4, matching the working production Blueprint |
| Build / start | `pip install -r requirements.txt` / `python3 server/meatcode_server.py` |
| Health | `/api/health` |
| Environment | `APP_ENV=dev`, separate `SITE_PASSWORD`, dedicated `DATABASE_URL`, own `ANTHROPIC_API_KEY`, `MAILLARD_MODE=mock` |
| Database | Prefer a dedicated Neon development branch/copy and role for Yochai; do not point experiments at production. Creation/access provisioning has not been performed. |
| Plan | Template uses free for an initial interactive sandbox; this can sleep and is not the final private-API hosting choice. No plan or billing change made. |
| Region | Oregon as shown in the screenshot; verify Lior's actual service region before relying on a shared private network. |

For this investigation, reuse the existing failed service identified above. The table and example are reference settings if a genuinely new sandbox is needed elsewhere; they are not an instruction to create a fourth MeatCODE service. Keep the root production Blueprint unchanged until the managed-service/branch plan has been reviewed.

Required secret values must be provisioned in Render; they are not copied from local `.env` files, committed, or pasted into chat. Optional `UNPAYWALL_EMAIL` and `ECOSYSTEM_CONTACT_EMAIL` can be set if those capabilities are needed; their absence is not an established cause of this failed deployment.

After deploying, verify the **new service's** `/api/version` reports its intended commit and `env=dev`, verify `/api/health`, verify the password gate and one authenticated database-backed endpoint, and then test Oracle only if model access is intended. None of those checks for a new service have run yet.

## Connecting the services later

```text
Yochai branch -> Yochai Render service -> Yochai Neon branch
                         ^
                         | authenticated API, with timeout and versioned JSON contract
                         |
Lior main -> Lior Render service -> production Neon
                         |
                    Oracle browser
```

Once Yochai's functionality has an explicit API, Lior's backend can call it and return the result to Oracle. Decide the request/response fields, authentication and timeout behavior before adding that call. Keep browser requests going through Lior's backend.

If both services are in the **same Render workspace and region**, private networking can connect them, subject to any environment isolation rules. A **free web service cannot receive private-network requests**, so an always-on/internal API would need an eligible plan or private-service deployment. If Yochai uses his own separate workspace/account, authenticated HTTPS between the public service URLs is the simpler connection; Render's shared private network does not cross workspaces. An isolated service can still be in the same team workspace; separate billing ownership is not required for code/deploy independence.

## Fallback

If a separate service cannot be provisioned, the existing `meatcode-dev` staging service can temporarily host a jointly agreed branch. This shares the staging deployment and database risk; it is not Yochai's independent server. Production remains on `main`. Integrate reviewed code through the usual staging/review/release process rather than making production his development environment.

## Sources

- Remote Blueprint: https://github.com/Bokipr0/meatCODE/blob/main/render.yaml
- Remote server: https://github.com/Bokipr0/meatCODE/blob/main/server/meatcode_server.py
- Production version: https://meatcode-oracle.onrender.com/api/version
- Deploy behavior and failure handling: https://render.com/docs/deploys
- Troubleshooting: https://render.com/docs/troubleshooting-deploys
- Blueprint setup, replication and custom path: https://render.com/docs/infrastructure-as-code
- Blueprint secrets and fields: https://render.com/docs/blueprint-spec
- Private networking and plan limits: https://render.com/docs/private-network

No root deployment file, service, credential, permission, repository branch or live deployment was changed. These local documents are ready for review and the normal publication process.
