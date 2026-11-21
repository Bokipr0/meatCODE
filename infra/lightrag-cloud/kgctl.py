#!/usr/bin/env python3
# Last updated: 2026-11-21 21:34 UTC · Claude (Sonnet 5.5) · KG control CLI, verified against LightRAG 1.5.7
"""kgctl - control plane for the hosted MeatCODE LightRAG knowledge graph.

Config: KG_URL and KG_API_KEY from the environment or ./.env.kg (never committed).
Every mutating command appends a line to kg_audit.jsonl (no secrets) and the
destructive ones require --yes. Read commands never change anything.

  health | status | docs [--status S] | counts
  upload FILE...            text FILE_OR_- --source NAME
  delete-doc ID... --yes    reprocess-failed
  entity-get NAME | entity-create NAME --type T --desc D
  entity-edit NAME --set k=v ...   [--rename NEW]
  entity-merge SRC... --into TARGET --yes   entity-delete NAME --yes
  relation-create SRC TGT --desc D [--keywords K] [--weight W]
  relation-edit SRC TGT --set k=v ...   relation-delete SRC TGT --yes
  export [--label '*'] [--max-nodes N] --out FILE.json
  query "question" [--mode mix|local|global|hybrid|naive]
"""
import argparse, json, os, sys, time, uuid, urllib.request, urllib.error, urllib.parse
from pathlib import Path

AUDIT = Path(os.environ.get("KG_AUDIT_LOG", Path(__file__).with_name("kg_audit.jsonl")))


def load_cfg():
    cfg = {"KG_URL": os.environ.get("KG_URL"), "KG_API_KEY": os.environ.get("KG_API_KEY")}
    envf = Path(".env.kg")
    if envf.exists():
        for line in envf.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                cfg.setdefault(k.strip(), None)
                if not cfg.get(k.strip()):
                    cfg[k.strip()] = v.strip()
    if not cfg.get("KG_URL") or not cfg.get("KG_API_KEY"):
        sys.exit("KG_URL and KG_API_KEY are required (env or .env.kg)")
    return cfg["KG_URL"].rstrip("/"), cfg["KG_API_KEY"]


class KG:
    def __init__(self, url, key, timeout=600):
        self.url, self.key, self.timeout = url, key, timeout

    def call(self, method, path, body=None, query=None, raw=None, headers=None):
        u = self.url + path + ("?" + urllib.parse.urlencode(query) if query else "")
        h = {"X-API-Key": self.key, "Accept": "application/json"}
        data = raw
        if body is not None:
            data = json.dumps(body).encode()
            h["Content-Type"] = "application/json"
        h.update(headers or {})
        req = urllib.request.Request(u, data=data, method=method, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                t = r.read().decode()
                return json.loads(t) if t else {}
        except urllib.error.HTTPError as e:
            sys.exit(f"HTTP {e.code} {method} {path}: {e.read().decode()[:500]}")

    def upload(self, path: Path):
        b = uuid.uuid4().hex
        payload = (f"--{b}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{path.name}\"\r\n"
                   "Content-Type: application/octet-stream\r\n\r\n").encode() + path.read_bytes() + f"\r\n--{b}--\r\n".encode()
        return self.call("POST", "/documents/upload", raw=payload,
                         headers={"Content-Type": f"multipart/form-data; boundary={b}"})


def audit(action, **detail):
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT.open("a") as f:
        f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "action": action, **detail}) + "\n")


def need_yes(a, what):
    if not a.yes:
        sys.exit(f"refusing to {what} without --yes (take a snapshot first: see README 'Backups')")


def kv(pairs):
    out = {}
    for p in pairs or []:
        k, _, v = p.partition("=")
        if not k or not _:
            sys.exit(f"bad --set '{p}', expected key=value")
        out[k] = v
    return out


def out(o):
    print(json.dumps(o, indent=2, ensure_ascii=False))


def build_parser():
    p = argparse.ArgumentParser(prog="kgctl")
    s = p.add_subparsers(dest="cmd", required=True)
    for n in ("health", "status", "counts", "reprocess-failed"):
        s.add_parser(n)
    d = s.add_parser("docs"); d.add_argument("--status"); d.add_argument("--page-size", type=int, default=50)
    u = s.add_parser("upload"); u.add_argument("files", nargs="+")
    t = s.add_parser("text"); t.add_argument("file"); t.add_argument("--source", required=True)
    x = s.add_parser("delete-doc"); x.add_argument("ids", nargs="+"); x.add_argument("--yes", action="store_true")
    e = s.add_parser("entity-get"); e.add_argument("name")
    e = s.add_parser("entity-create"); e.add_argument("name"); e.add_argument("--type", required=True); e.add_argument("--desc", required=True)
    e = s.add_parser("entity-edit"); e.add_argument("name"); e.add_argument("--set", nargs="*"); e.add_argument("--rename")
    e = s.add_parser("entity-merge"); e.add_argument("sources", nargs="+"); e.add_argument("--into", required=True); e.add_argument("--yes", action="store_true")
    e = s.add_parser("entity-delete"); e.add_argument("name"); e.add_argument("--yes", action="store_true")
    r = s.add_parser("relation-create"); r.add_argument("src"); r.add_argument("tgt"); r.add_argument("--desc", required=True); r.add_argument("--keywords", default=""); r.add_argument("--weight", type=float, default=1.0)
    r = s.add_parser("relation-edit"); r.add_argument("src"); r.add_argument("tgt"); r.add_argument("--set", nargs="+", required=True)
    r = s.add_parser("relation-delete"); r.add_argument("src"); r.add_argument("tgt"); r.add_argument("--yes", action="store_true")
    g = s.add_parser("export"); g.add_argument("--label", default="*"); g.add_argument("--max-nodes", type=int, default=100000); g.add_argument("--out", required=True)
    q = s.add_parser("query"); q.add_argument("question"); q.add_argument("--mode", default="mix")
    return p


def run(a, kg: KG):
    c = a.cmd
    if c == "health": return out(kg.call("GET", "/health"))
    if c == "status": return out(kg.call("GET", "/documents/pipeline_status"))
    if c == "counts": return out(kg.call("GET", "/documents/status_counts"))
    if c == "docs":
        body = {"page": 1, "page_size": a.page_size}
        if a.status: body["status_filter"] = a.status
        return out(kg.call("POST", "/documents/paginated", body))
    if c == "upload":
        for f in a.files:
            p = Path(f)
            if not p.is_file(): sys.exit(f"not a file: {f}")
            r = kg.upload(p); audit("upload", file=p.name, result=r); out(r)
        return
    if c == "text":
        txt = sys.stdin.read() if a.file == "-" else Path(a.file).read_text()
        r = kg.call("POST", "/documents/text", {"text": txt, "file_source": a.source})
        audit("text", source=a.source, chars=len(txt), result=r); return out(r)
    if c == "delete-doc":
        need_yes(a, "delete documents")
        r = kg.call("DELETE", "/documents/delete_document", {"doc_ids": a.ids, "delete_file": False, "delete_llm_cache": False})
        audit("delete-doc", ids=a.ids, result=r); return out(r)
    if c == "reprocess-failed":
        r = kg.call("POST", "/documents/reprocess_failed"); audit("reprocess-failed", result=r); return out(r)
    if c == "entity-get": return out(kg.call("GET", "/graphs", query={"label": a.name, "max_depth": 1, "max_nodes": 50}))
    if c == "entity-create":
        r = kg.call("POST", "/graph/entity/create", {"entity_name": a.name, "entity_data": {"entity_type": a.type, "description": a.desc}})
        audit("entity-create", name=a.name); return out(r)
    if c == "entity-edit":
        data = kv(a.set)
        if a.rename: data["entity_name"] = a.rename
        if not data: sys.exit("nothing to edit")
        r = kg.call("POST", "/graph/entity/edit", {"entity_name": a.name, "updated_data": data, "allow_rename": bool(a.rename), "allow_merge": False})
        audit("entity-edit", name=a.name, fields=sorted(data)); return out(r)
    if c == "entity-merge":
        need_yes(a, "merge entities")
        r = kg.call("POST", "/graph/entities/merge", {"entities_to_change": a.sources, "entity_to_change_into": a.into})
        audit("entity-merge", sources=a.sources, into=a.into); return out(r)
    if c == "entity-delete":
        need_yes(a, "delete an entity")
        r = kg.call("DELETE", "/graph/entity/delete", {"entity_name": a.name}); audit("entity-delete", name=a.name); return out(r)
    if c == "relation-create":
        r = kg.call("POST", "/graph/relation/create", {"source_entity": a.src, "target_entity": a.tgt,
                    "relation_data": {"description": a.desc, "keywords": a.keywords, "weight": a.weight}})
        audit("relation-create", src=a.src, tgt=a.tgt); return out(r)
    if c == "relation-edit":
        r = kg.call("POST", "/graph/relation/edit", {"source_id": a.src, "target_id": a.tgt, "updated_data": kv(a.set)})
        audit("relation-edit", src=a.src, tgt=a.tgt); return out(r)
    if c == "relation-delete":
        need_yes(a, "delete a relation")
        r = kg.call("DELETE", "/graph/relation/delete", {"source_entity": a.src, "target_entity": a.tgt})
        audit("relation-delete", src=a.src, tgt=a.tgt); return out(r)
    if c == "export":
        g = kg.call("GET", "/graphs", query={"label": a.label, "max_depth": 10, "max_nodes": a.max_nodes})
        Path(a.out).write_text(json.dumps(g)); print(f"wrote {a.out}: {len(g.get('nodes', []))} nodes, {len(g.get('edges', []))} edges")
        return
    if c == "query":
        return out(kg.call("POST", "/query", {"query": a.question, "mode": a.mode, "include_references": True}))


def main(argv=None):
    a = build_parser().parse_args(argv)
    url, key = load_cfg()
    run(a, KG(url, key))


if __name__ == "__main__":
    main()
