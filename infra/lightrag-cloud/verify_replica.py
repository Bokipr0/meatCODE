#!/usr/bin/env python3
# Last updated: 2026-11-21 21:34 UTC · Claude (Sonnet 5.5) · baseline verifier
"""Compare a running LightRAG (local replica or Render) against the frozen baseline MANIFEST.
Read-only. Exit 0 only if graph counts and document counts match and auth is enforced.
Usage: verify_replica.py --manifest data/backups/.../MANIFEST.json   (KG_URL/KG_API_KEY from env or .env.kg)
"""
import argparse, json, sys, urllib.request, urllib.error
import kgctl


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--manifest", required=True)
    a = ap.parse_args(argv)
    m = json.loads(open(a.manifest).read())
    url, key = kgctl.load_cfg()
    kg = kgctl.KG(url, key)
    checks = []
    try:
        urllib.request.urlopen(url + "/documents/status_counts", timeout=20)
        checks.append(("auth enforced (no key rejected)", False))
    except urllib.error.HTTPError as e:
        checks.append(("auth enforced (no key rejected)", e.code in (401, 403)))
    h = kg.call("GET", "/health")
    checks.append(("version 1.5.7", h.get("core_version") == "1.5.7"))
    sc = kg.call("GET", "/documents/status_counts")["status_counts"]
    want = m["documents"]["by_status"]
    checks.append((f"documents {want}", all(sc.get(k) == v for k, v in want.items()) and sc["all"] == m["documents"]["total"]))
    g = kg.call("GET", "/graphs", query={"label": "*", "max_depth": 10, "max_nodes": 100000})
    n, e = len(g["nodes"]), len(g["edges"])
    checks.append((f"graph {m['graph']['nodes']} nodes / {m['graph']['edges']} edges (got {n}/{e})",
                   (n, e) == (m["graph"]["nodes"], m["graph"]["edges"])))
    for name, ok in checks:
        print(("PASS " if ok else "FAIL ") + name)
    sys.exit(0 if all(ok for _, ok in checks) else 1)


if __name__ == "__main__":
    main()
