#!/usr/bin/env python3
# Last updated: 2026-11-21 21:34 UTC · Claude (Sonnet 5.5) · Render API provisioner (dry-run default)
"""Create the two Render services for the LightRAG sandbox via the Render API.

Dry-run by default: prints payloads (secrets masked), calls nothing. `--apply` creates anything
missing (idempotent by service name; never modifies or deletes an existing service).

Credentials (read from ./.env.cloud, 0600, git-ignored - never printed):
  RENDER_API_KEY            Render Dashboard -> Account Settings -> API Keys
  LIGHTRAG_API_KEY          >=32 chars; generated and saved if absent
  LLM_BINDING_API_KEY       Anthropic key (or pass --anthropic-key-from ~/LightRAG/.env)
  SEED_ARCHIVE_URL / SEED_ARCHIVE_SHA256   baseline archive (or pass --empty for a fresh graph)
Usage: provision_render.py --repo https://github.com/ORG/REPO --branch BRANCH [--owner-id tea-...] [--apply]
"""
import argparse, json, os, re, secrets, sys, urllib.request, urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
API = "https://api.render.com/v1"
SECRET_KEYS = {"LIGHTRAG_API_KEY", "LLM_BINDING_API_KEY", "KEYWORD_LLM_BINDING_API_KEY", "SEED_ARCHIVE_URL"}
OLLAMA, LIGHT = "meatcode-lightrag-ollama", "meatcode-lightrag"


def read_env(path: Path) -> dict:
    out = {}
    if path.exists():
        for line in path.read_text().splitlines():
            m = re.match(r"^\s*([A-Z0-9_]+)\s*=\s*(.*)$", line)
            if m: out[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return out


def blueprint_env() -> list[dict]:
    """Non-secret settings come from render.yaml so there is one source of truth."""
    text = (HERE / "render.yaml").read_text()
    return [{"key": k, "value": v.strip('"')} for k, v in
            re.findall(r"- \{key: (\w+), value: (\"[^\"]*\"|[^,}]+)\}", text)]


def payloads(repo, branch, owner_id, secrets_in: dict, empty: bool):
    if not empty and not (secrets_in.get("SEED_ARCHIVE_URL") and secrets_in.get("SEED_ARCHIVE_SHA256")):
        raise SystemExit("SEED_ARCHIVE_URL and SEED_ARCHIVE_SHA256 required (or --empty): otherwise the service "
                         "would start an EMPTY graph and its disk would then never be seeded")
    key = secrets_in.get("LIGHTRAG_API_KEY", "")
    if len(key) < 32: raise SystemExit("LIGHTRAG_API_KEY must be >=32 chars")
    llm = secrets_in.get("LLM_BINDING_API_KEY")
    if not llm: raise SystemExit("LLM_BINDING_API_KEY missing")
    common = {"ownerId": owner_id, "repo": repo, "branch": branch, "autoDeploy": "no"}
    ollama = {**common, "type": "private_service", "name": OLLAMA, "serviceDetails": {
        "runtime": "docker", "plan": "standard", "region": "frankfurt",
        "envSpecificDetails": {"dockerfilePath": "infra/lightrag-cloud/Dockerfile.ollama",
                               "dockerContext": "infra/lightrag-cloud"},
        "disk": {"name": "ollama-models", "mountPath": "/data", "sizeGB": 5}}}
    env = blueprint_env()
    env += [{"key": "LIGHTRAG_API_KEY", "value": key}, {"key": "LLM_BINDING_API_KEY", "value": llm},
            {"key": "KEYWORD_LLM_BINDING_API_KEY", "value": secrets_in.get("KEYWORD_LLM_BINDING_API_KEY", llm)}]
    if not empty:
        env += [{"key": k, "value": secrets_in[k]} for k in ("SEED_ARCHIVE_URL", "SEED_ARCHIVE_SHA256")]
    light = {**common, "type": "web_service", "name": LIGHT, "envVars": env, "serviceDetails": {
        "runtime": "docker", "plan": "standard", "region": "frankfurt", "healthCheckPath": "/health",
        "envSpecificDetails": {"dockerfilePath": "infra/lightrag-cloud/Dockerfile.lightrag",
                               "dockerContext": "infra/lightrag-cloud"},
        "disk": {"name": "lightrag-data", "mountPath": "/app/data", "sizeGB": 10}}}
    return [ollama, light]          # Ollama first: LightRAG's embedding host must exist


def mask(p):
    q = json.loads(json.dumps(p))
    for e in q.get("envVars", []):
        if e["key"] in SECRET_KEYS: e["value"] = "***"
    return q


class Render:
    def __init__(self, token): self.h = {"Authorization": f"Bearer {token}", "Accept": "application/json",
                                         "Content-Type": "application/json"}
    def call(self, method, path, body=None):
        req = urllib.request.Request(API + path, method=method, headers=self.h,
                                     data=json.dumps(body).encode() if body is not None else None)
        try:
            with urllib.request.urlopen(req, timeout=60) as r: return json.load(r)
        except urllib.error.HTTPError as e:
            raise SystemExit(f"Render API {e.code} {method} {path}: {e.read().decode()[:600]}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True); ap.add_argument("--branch", required=True)
    ap.add_argument("--owner-id"); ap.add_argument("--empty", action="store_true")
    ap.add_argument("--anthropic-key-from"); ap.add_argument("--apply", action="store_true")
    ap.add_argument("--env-file", default=str(Path(".env.cloud")))
    a = ap.parse_args(argv)
    envp = Path(a.env_file); cfg = read_env(envp)
    if a.anthropic_key_from and not cfg.get("LLM_BINDING_API_KEY"):
        cfg["LLM_BINDING_API_KEY"] = read_env(Path(a.anthropic_key_from).expanduser()).get("LLM_BINDING_API_KEY", "")
    if not cfg.get("LIGHTRAG_API_KEY"):
        cfg["LIGHTRAG_API_KEY"] = secrets.token_urlsafe(48)
        with envp.open("a") as f: f.write(f"LIGHTRAG_API_KEY={cfg['LIGHTRAG_API_KEY']}\n")
        envp.chmod(0o600); print(f"generated LIGHTRAG_API_KEY into {envp} (not shown)")
    token = cfg.get("RENDER_API_KEY") or os.environ.get("RENDER_API_KEY")
    if a.apply and not token: sys.exit("RENDER_API_KEY missing from .env.cloud")
    r = Render(token) if token else None
    owner = a.owner_id
    if a.apply and not owner:
        owners = r.call("GET", "/owners?limit=20")
        if len(owners) != 1: sys.exit("multiple workspaces: pass --owner-id " + ", ".join(o["owner"]["id"] for o in owners))
        owner = owners[0]["owner"]["id"]
    plan = payloads(a.repo, a.branch, owner or "<ownerId>", cfg, a.empty)
    if not a.apply:
        print(json.dumps([mask(p) for p in plan], indent=2)); print("\nDRY RUN - nothing created. Re-run with --apply.")
        return
    existing = {s["service"]["name"] for s in r.call("GET", "/services?limit=100")}
    for p in plan:
        if p["name"] in existing: print(f"exists, skipped: {p['name']}"); continue
        res = r.call("POST", "/services", p)
        print(f"created {p['name']}: {res.get('service', res).get('id')}")


if __name__ == "__main__":
    main()
