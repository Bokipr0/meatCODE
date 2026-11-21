#!/usr/bin/env python3
# Last updated: 2026-11-21 21:34 UTC · Claude (Sonnet 5.5) · immutable baseline snapshot tool
"""Freeze the local LightRAG workspace as an immutable, verifiable baseline.

Read-only against the live workspace. Refuses to run while lightrag-server is
listening on :9621 (files could be mid-write). Produces, in --out:
  rag_storage.tar.gz   exact copy of the workspace
  MANIFEST.json        per-file sha256/size, graph node/edge counts, doc counts,
                       embedding config (never secrets), archive sha256
Usage: make_baseline.py [--src ~/LightRAG/rag_storage] [--env ~/LightRAG/.env] --out DIR
"""
import argparse, hashlib, json, re, socket, sys, tarfile, time
from pathlib import Path
import xml.etree.ElementTree as ET

SAFE_ENV = {"LLM_MODEL", "EMBEDDING_MODEL", "EMBEDDING_DIM", "EMBEDDING_BINDING",
            "QUERY_LLM_MODEL", "EXTRACT_LLM_MODEL", "KEYWORD_LLM_MODEL", "OLLAMA_EMBEDDING_NUM_CTX"}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def graph_counts(p: Path):
    nodes = edges = 0
    for _, el in ET.iterparse(p, events=("end",)):
        t = el.tag.rsplit("}", 1)[-1]
        if t == "node": nodes += 1
        elif t == "edge": edges += 1
        el.clear()
    return nodes, edges


def server_running() -> bool:
    s = socket.socket(); s.settimeout(1)
    try:
        return s.connect_ex(("127.0.0.1", 9621)) == 0
    finally:
        s.close()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(Path.home() / "LightRAG/rag_storage"))
    ap.add_argument("--env", default=str(Path.home() / "LightRAG/.env"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--force", action="store_true", help="run even if :9621 is listening")
    a = ap.parse_args(argv)
    src, out = Path(a.src), Path(a.out)
    if server_running() and not a.force:
        sys.exit("lightrag-server is running on :9621 - stop it first for a consistent snapshot")
    if out.exists() and any(out.iterdir()):
        sys.exit(f"{out} is not empty; baselines are immutable - choose a new directory")
    out.mkdir(parents=True, exist_ok=True)

    files = sorted(p for p in src.rglob("*") if p.is_file() and p.name != ".DS_Store")
    manifest = {"created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "lightrag_version": "1.5.7", "source_dir": str(src), "files": {}}
    for p in files:
        manifest["files"][str(p.relative_to(src))] = {"sha256": sha256(p), "bytes": p.stat().st_size}
    g = src / "graph_chunk_entity_relation.graphml"
    manifest["graph"] = dict(zip(("nodes", "edges"), graph_counts(g))) if g.exists() else None
    ds = src / "kv_store_doc_status.json"
    if ds.exists():
        docs = json.loads(ds.read_text())
        by = {}
        for d in docs.values():
            by[d.get("status", "?")] = by.get(d.get("status", "?"), 0) + 1
        manifest["documents"] = {"total": len(docs), "by_status": by}
    env = {}
    for line in Path(a.env).read_text().splitlines():
        m = re.match(r"^([A-Z_]+)=(.*)$", line.strip())
        if m and m.group(1) in SAFE_ENV:
            env[m.group(1)] = m.group(2)
    manifest["config"] = env

    arc = out / "rag_storage.tar.gz"
    with tarfile.open(arc, "w:gz") as t:
        for p in files:
            t.add(p, arcname=str(p.relative_to(src)))
    manifest["archive"] = {"name": arc.name, "sha256": sha256(arc), "bytes": arc.stat().st_size}
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=2))
    for p in [arc, out / "MANIFEST.json"]:
        p.chmod(0o444)
    print(json.dumps({k: manifest[k] for k in ("graph", "documents", "archive", "config")}, indent=2))


if __name__ == "__main__":
    main()
