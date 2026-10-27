#!/usr/bin/env python3
"""
build_system_snapshot.py — regenerate platform_docs/SYSTEM_SNAPSHOT.md from LIVE sources.

Why: static docs go stale (memory said 374 experts; Neon says 3,129). This script reads the truth
directly — Neon (both branches), the migrations folder, the feature-flag registry, git refs, the
server's route table and render.yaml — and writes one dated markdown file any new account or agent
can read cold.

Run:   python3 orchestration/build_system_snapshot.py
or:    double-click  "Release Center/refresh-handoff.command"

SECURITY: never writes a connection string, host, password or API key. It reports only whether a
secret is PRESENT, and the names of env vars.
"""
from __future__ import annotations
import datetime, json, os, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "platform_docs" / "SYSTEM_SNAPSHOT.md"

try:
    import psycopg2
except ImportError:
    psycopg2 = None


def env_value(fname: str, key: str) -> str | None:
    p = REPO / fname
    if not p.exists():
        return None
    for line in p.read_text().splitlines():
        if line.startswith(key + "="):
            v = line.split("=", 1)[1].strip().strip('"').strip("'")
            return v or None
    return None


def env_names(fname: str) -> list[str]:
    p = REPO / fname
    if not p.exists():
        return []
    return [l.split("=", 1)[0] for l in p.read_text().splitlines()
            if re.match(r"^[A-Z_0-9]+=", l) and l.split("=", 1)[1].strip()]


# ── Neon ────────────────────────────────────────────────────────────────────
KEY_METRICS = [
    ("sources", "SELECT count(*) FROM sources"),
    ("sources ≥ relevance gate (60)", "SELECT count(*) FROM sources WHERE relevance_llm >= 60"),
    ("sources with DOI", "SELECT count(doi) FROM sources"),
    ("molecules (non-junk)", "SELECT count(*) FROM molecules WHERE NOT is_junk"),
    ("molecules with InChIKey", "SELECT count(inchikey) FROM molecules"),
    ("molecules with CAS", "SELECT count(cas_number) FROM molecules"),
    ("experts", "SELECT count(*) FROM experts"),
    ("paper↔molecule links (source_molecules)", "SELECT count(*) FROM source_molecules"),
    ("claims", "SELECT count(*) FROM claims"),
    ("molecule_properties (provenanced values)", "SELECT count(*) FROM molecule_properties"),
    ("  … citing a paper (source_id set)", "SELECT count(source_id) FROM molecule_properties"),
    ("experiments", "SELECT count(*) FROM experiments"),
    ("processes (T/pH/time conditions)", "SELECT count(*) FROM processes"),
    ("B2 check: quarantined sources still ≥ gate (should be 0)",
     """SELECT count(DISTINCT a.source_id) FROM source_audits a JOIN sources s ON s.id = a.source_id
        WHERE a.verdict = 'quarantine' AND s.relevance_llm >= 60"""),
    ("data-quality audits: last run", "SELECT max(audited_at)::date::text FROM source_audits"),
]


def live_version(url: str):
    """Ask the running server which commit it is on. /api/version is open even behind the password gate."""
    import urllib.request
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": type(e).__name__}


def neon(url: str | None):
    if not url:
        return {"error": "no DATABASE_URL in this env file"}
    if psycopg2 is None:
        return {"error": "psycopg2 not installed (pip install psycopg2-binary)"}
    try:
        c = psycopg2.connect(url, connect_timeout=15)
    except Exception as e:  # never echo the URL
        return {"error": f"connection failed ({type(e).__name__})"}
    cur = c.cursor()
    out = {"metrics": [], "tables": [], "views": [], "molecule_cols": 0}
    for label, sql in KEY_METRICS:
        try:
            cur.execute(sql); out["metrics"].append((label, cur.fetchone()[0]))
        except Exception:
            c.rollback(); out["metrics"].append((label, "n/a"))
    cur.execute("""SELECT table_name FROM information_schema.tables
                   WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY 1""")
    for (t,) in cur.fetchall():
        try:
            cur.execute(f'SELECT count(*) FROM "{t}"'); out["tables"].append((t, cur.fetchone()[0]))
        except Exception:
            c.rollback(); out["tables"].append((t, "n/a"))
    cur.execute("""SELECT table_name FROM information_schema.views
                   WHERE table_schema='public' ORDER BY 1""")
    out["views"] = [r[0] for r in cur.fetchall()]
    cur.execute("""SELECT count(*) FROM information_schema.columns
                   WHERE table_schema='public' AND table_name='molecules'""")
    out["molecule_cols"] = cur.fetchone()[0]
    c.close()
    return out


# ── repo-side facts ─────────────────────────────────────────────────────────
def migrations():
    d = REPO / "db" / "migrations"
    return sorted(p.name for p in d.glob("[0-9][0-9][0-9][0-9]_*.sql")) if d.exists() else []


def flags():
    p = next(REPO.glob("**/features.json"), None)
    if not p:
        return []
    data = json.loads(p.read_text())
    rows = []
    for k, v in data.get("flags", {}).items():
        rows.append((k, v.get("kind", ""), v.get("status", ""), v.get("dev"), v.get("prod"),
                     v.get("added", "")))
    return rows


def git_facts():
    g = REPO / ".git"
    head = (g / "HEAD").read_text().strip().replace("ref: refs/heads/", "") if (g / "HEAD").exists() else "?"
    heads = sorted(p.name for p in (g / "refs" / "heads").glob("*")) if (g / "refs" / "heads").exists() else []
    tags = sorted(p.name for p in (g / "refs" / "tags").glob("prod-*")) if (g / "refs" / "tags").exists() else []
    packed = g / "packed-refs"
    if packed.exists():
        for line in packed.read_text().splitlines():
            m = re.search(r"refs/tags/(prod-\S+)", line)
            if m and m.group(1) not in tags:
                tags.append(m.group(1))
    remote = ""
    cfg = g / "config"
    if cfg.exists():
        m = re.search(r'\[remote "origin"\][^\[]*url = (\S+)', cfg.read_text())
        remote = m.group(1) if m else ""
    return head, heads, sorted(tags), remote


def ref(path: str) -> str:
    p = REPO / ".git" / path
    if p.exists():
        return p.read_text().strip()
    packed = REPO / ".git" / "packed-refs"
    if packed.exists():
        for line in packed.read_text().splitlines():
            if line.endswith(" " + path):
                return line.split()[0]
    return ""


def tag_for(commit: str) -> str:
    d = REPO / ".git" / "refs" / "tags"
    if d.exists():
        for t in d.glob("prod-*"):
            if t.read_text().strip().startswith(commit[:12]):
                return t.name
    return ""


def routes():
    p = REPO / "server" / "meatcode_server.py"
    if not p.exists():
        return []
    src = p.read_text()
    found = set(re.findall(r'"(/api/[A-Za-z0-9_\-/.]+)"', src))
    found |= {m.replace("(\\d+)", "{id}") for m in re.findall(r'r"\^(/api/[^"$]+)\$?"', src)}
    return sorted({r.rstrip("/") for r in found})


def render_services():
    p = REPO / "render.yaml"
    if not p.exists():
        return []
    active = []
    for line in p.read_text().splitlines():
        if line.strip().startswith("#"):
            continue
        m = re.match(r"\s+name:\s*(\S+)", line)
        if m:
            active.append(m.group(1))
    return active


def coordination_files():
    rows = []
    for f in ["ROLES.md", "CLAUDE.md", "PROJECT_STATE.md", "MVP_BOARD.md",
              "TEAM_BROADCAST.md", "AGENT_UPDATE_LOG.md"]:
        p = REPO / f
        if p.exists():
            txt = p.read_text(errors="ignore")
            if f == "AGENT_UPDATE_LOG.md":   # newest entry heading, not the stale header stamp
                m = re.search(r"^## ([0-9]{4}-[0-9]{2}-[0-9]{2})", txt, re.M)
            else:
                m = re.search(r"[Ll]ast updated:?\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", txt)
            rows.append((f, len(txt.splitlines()), m.group(1) if m else "—"))
    return rows


def skills():
    d = REPO / "orchestration" / "skills"
    return sorted(p.parent.name for p in d.glob("*/SKILL.md")) if d.exists() else []


# ── render markdown ─────────────────────────────────────────────────────────
def main():
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    prod = neon(env_value(".env", "DATABASE_URL"))
    dev = neon(env_value(".env.dev", "DATABASE_URL"))
    head, heads, tags, remote = git_facts()

    L = []
    w = L.append
    w(f"# SYSTEM SNAPSHOT — generated {now}")
    w("")
    w("> **Generated file — do not hand-edit.** Regenerate with `Release Center/refresh-handoff.command` "
      "(or `python3 orchestration/build_system_snapshot.py`). Everything here was read live from Neon, "
      "git and the repo at the time above. No secrets are written — only whether they are present.")
    w("")
    # ── what is actually running ──
    v = live_version("https://meatcode-oracle.onrender.com/api/version")
    dev_head = ref("refs/remotes/origin/dev") or ref("refs/heads/dev")
    w("## What is live right now (verified, not assumed)")
    w("")
    if "error" in v:
        w(f"- Production `/api/version` unreachable ({v['error']}) — deploy state NOT verified this run.")
    else:
        pc = v.get("commit_full", "")
        t = tag_for(pc)
        same = dev_head.startswith(pc[:12]) if dev_head else False
        w(f"- **Production** runs commit `{pc[:12]}`{f' = `{t}`' if t else ''}, branch `{v.get('branch')}`, "
          f"env `{v.get('env')}`, started {v.get('server_started_utc','?')}, model `{v.get('model')}`.")
        w(f"- **`dev` on GitHub** is at `{dev_head[:12] or '?'}`. "
          + ("Production is identical to dev — nothing waiting to promote."
             if same else "Dev is AHEAD of production — run `promote-to-prod.command` to ship it "
                          "(see PROJECT_STATE for what's waiting)."))
    w("")
    w("## Neon Postgres — key metrics")
    w("")
    if "error" in prod and "error" in dev:
        w(f"- production: {prod['error']}"); w(f"- dev: {dev['error']}")
    else:
        pm = dict(prod.get("metrics", [])); dm = dict(dev.get("metrics", []))
        w("| Metric | production (`.env`) | dev branch (`.env.dev`) |")
        w("|---|---:|---:|")
        for label, _ in KEY_METRICS:
            w(f"| {label} | {pm.get(label, prod.get('error', '—'))} | {dm.get(label, dev.get('error', '—'))} |")
        w("")
        w(f"`molecules` has **{prod.get('molecule_cols', '?')}** columns on production.")
    w("")
    w("<details><summary>All tables with row counts (production)</summary>")
    w("")
    w("| Table | Rows |"); w("|---|---:|")
    for t, n in prod.get("tables", []):
        w(f"| `{t}` | {n} |")
    w("")
    w(f"Views ({len(prod.get('views', []))}): " + ", ".join(f"`{v}`" for v in prod.get("views", [])))
    w("</details>")
    w("")
    m = migrations()
    rng = f" ({m[0][:4]}–{m[-1][:4]})" if m else ""
    w(f"## Schema migrations — {len(m)} numbered files in `db/migrations/`{rng}")
    w("")
    w("Latest: " + ", ".join(f"`{x}`" for x in m[-5:]) if m else "none found")
    w("")
    w("## GitHub")
    w("")
    w(f"- Remote: `{remote or 'not found'}`")
    w(f"- Local branches: {', '.join(f'`{h}`' for h in heads)} · checked out: **`{head}`**")
    w(f"- Production release tags ({len(tags)}): " + (", ".join(f"`{t}`" for t in tags[-6:]) or "none"))
    w("")
    w("## Render")
    w("")
    rs = render_services()
    w(f"- Services declared (uncommented) in `render.yaml`: {', '.join(f'`{s}`' for s in rs) or 'none'}")
    w("- Production URL: https://meatcode-oracle.onrender.com (health: `/api/health`, version: `/api/version`)")
    w("- Staging service `meatcode-dev` is created in the Render dashboard (branch `dev`), not in render.yaml.")
    w("")
    w("## Secrets present on this machine (names only)")
    w("")
    for f in [".env", ".env.dev", ".env.prod"]:
        names = env_names(f)
        w(f"- `{f}`: " + (", ".join(f"`{n}`" for n in names) if names else "_absent or empty_"))
    w("")
    fl = flags()
    w(f"## Feature flags — {len(fl)} in `Release Center/features.json`")
    w("")
    w("| Flag | Kind | Status | dev | prod | Added |"); w("|---|---|---|:-:|:-:|---|")
    for k, kind, st, d, p, a in fl:
        w(f"| `{k}` | {kind} | {st} | {'✅' if d else '—'} | {'✅' if p else '—'} | {a} |")
    w("")
    r = routes()
    w(f"## Server API — {len(r)} routes in `server/meatcode_server.py` (local `{head}` checkout — production may lag; see 'What is live')")
    w("")
    w(", ".join(f"`{x}`" for x in r))
    w("")
    w("## Coordination files (the agent spine)")
    w("")
    w("| File | Lines | Last-updated stamp |"); w("|---|---:|---|")
    for f, n, d in coordination_files():
        w(f"| `{f}` | {n} | {d} |")
    w("")
    sk = skills()
    w(f"## Agent skills versioned in the repo — {len(sk)} in `orchestration/skills/`")
    w("")
    w(", ".join(f"`{s}`" for s in sk) if sk else "_none_")
    w("")
    OUT.write_text("\n".join(L) + "\n")
    print(f"wrote {OUT.relative_to(REPO)}  ({len(L)} lines)")


if __name__ == "__main__":
    main()
