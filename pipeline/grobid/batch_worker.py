# Last updated: 2026-11-21 21:34 UTC · Claude (Sonnet 5.5) · hosted LightRAG target: https+key validation, unreviewed-document guard, hosted preflight
"""Local PDF inbox -> GROBID -> guarded LightRAG candidate ingestion.

Run once with ``python3 pipeline/grobid/batch_worker.py --once`` or keep polling
with ``--watch``. This never writes to Neon or promotes canonical knowledge.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
import claims  # noqa: E402 - local, evidence-linked scientific claim extraction
import ingestion_control  # noqa: E402 - persistent pause survives manual restarts
sys.path.insert(0, str(HERE / "mcp"))
import core  # noqa: E402 - reuse the existing, local GROBID parser

TEI = "{http://www.tei-c.org/ns/1.0}"
DEFAULT_INBOX = ROOT / "data/grobid/inbox"
DEFAULT_OUTPUT = ROOT / "data/grobid/batch"
DEFAULT_GRAPH = Path.home() / "LightRAG/rag_storage/kv_store_full_docs.json"
TERMINAL = {"processed", "duplicate", "review_required", "failed"}


def paper_doi(tei_xml: bytes | str) -> str | None:
    """Read only the paper header: bibliography DOIs identify *cited* papers."""
    root = ET.fromstring(tei_xml)
    header = root.find(f"{TEI}teiHeader")
    if header is None:
        return None
    source = header.find(f"{TEI}fileDesc/{TEI}sourceDesc/{TEI}biblStruct")
    if source is None:
        return None
    for node in source.iter(f"{TEI}idno"):
        if node.get("type", "").lower() != "doi":
            continue
        value = (node.text or "").strip().lower()
        value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value)
        value = re.sub(r"^doi:\s*", "", value).rstrip(".,; ")
        if re.fullmatch(r"10\.\d{4,9}/\S+", value):
            return value
    return None


def normalized_text(text: str) -> str:
    return " ".join(re.findall(r"[\w]+", text.casefold()))


def text_hash(text: str) -> str:
    return hashlib.sha256(normalized_text(text).encode()).hexdigest()


def shingles(text: str) -> set[bytes]:
    words = normalized_text(text).split()
    if len(words) < 60:
        return set()
    return {
        hashlib.blake2b(" ".join(words[i : i + 7]).encode(), digest_size=8).digest()
        for i in range(len(words) - 6)
    }


def possible_same_text(a: set[bytes], b: set[bytes]) -> bool:
    if not a or not b:
        return False
    shared = len(a & b)
    return shared / min(len(a), len(b)) >= 0.45


def graph_papers(path: Path) -> list[dict]:
    """Fail closed if the current local graph cannot be inventoried."""
    with path.open(encoding="utf-8") as stream:
        documents = json.load(stream)
    if not isinstance(documents, dict):
        raise ValueError("LightRAG full-doc store is not a document dictionary")
    papers = []
    for document in documents.values():
        if not isinstance(document, dict):
            continue
        content = document.get("content") or ""
        if not isinstance(content, str):
            continue
        doi = None
        body = content
        if content.lstrip().startswith("<"):
            try:
                doi = paper_doi(content)
                _, body = core.scientific_body(content)
            except (ET.ParseError, ValueError):
                # A source that cannot be interpreted still remains in the
                # graph inventory; unknown new identities are held for review.
                body = ""
        papers.append(
            {"source": str(document.get("file_path") or "unknown"),
             "doi": doi, "body_hash": text_hash(body) if body else None,
             "shingles": shingles(body)}
        )
    return papers


def connect_ledger(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """CREATE TABLE IF NOT EXISTS papers (
            pdf_sha256 TEXT PRIMARY KEY, pdf_path TEXT NOT NULL,
            paper_doi TEXT, body_sha256 TEXT, body_path TEXT,
            source_id TEXT, track_id TEXT, status TEXT NOT NULL,
            reason TEXT, updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )"""
    )
    connection.execute("CREATE INDEX IF NOT EXISTS papers_doi ON papers(paper_doi)")
    connection.commit()
    return connection


def record(connection: sqlite3.Connection, pdf_hash: str, pdf_path: Path,
           status: str, *, doi: str | None = None, body_hash: str | None = None,
           body_path: Path | None = None, source_id: str | None = None,
           track_id: str | None = None, reason: str | None = None) -> None:
    connection.execute(
        """INSERT INTO papers(pdf_sha256,pdf_path,paper_doi,body_sha256,body_path,
                              source_id,track_id,status,reason)
           VALUES(?,?,?,?,?,?,?,?,?)
           ON CONFLICT(pdf_sha256) DO UPDATE SET
             pdf_path=excluded.pdf_path, paper_doi=excluded.paper_doi,
             body_sha256=excluded.body_sha256, body_path=excluded.body_path,
             source_id=excluded.source_id, track_id=excluded.track_id,
             status=excluded.status, reason=excluded.reason,
             updated_at=CURRENT_TIMESTAMP""",
        (pdf_hash, str(pdf_path), doi, body_hash,
         str(body_path) if body_path else None, source_id, track_id,
         status, reason),
    )
    connection.commit()


def api_json(base: str, method: str, path: str, payload: dict | None = None,
             api_key: str | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    if api_key:
        headers["X-API-Key"] = api_key
    request = urllib.request.Request(base.rstrip("/") + path, data=data,
                                     headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def check_remote_extraction_key(env_path: Path) -> None:
    """Require the existing Anthropic route and a working credential."""
    values = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        name, value = line.split("=", 1)
        values[name.strip()] = value.strip().strip('"').strip("'")
    base = {'binding': values.get('LLM_BINDING'),
            'model': values.get('LLM_MODEL'), 'host': values.get('LLM_BINDING_HOST')}
    validate_anthropic_route(base)
    for prefix in ('EXTRACT', 'KEYWORD', 'QUERY', 'VLM'):
        validate_anthropic_route({
            'binding': values.get(prefix+'_LLM_BINDING') or base['binding'],
            'model': values.get(prefix+'_LLM_MODEL') or base['model'],
            'host': values.get(prefix+'_LLM_BINDING_HOST') or base['host']})
    key = values.get("LLM_BINDING_API_KEY", "")
    if not key:
        raise ValueError("LightRAG Anthropic credential is missing")
    request = urllib.request.Request(
        "https://api.anthropic.com/v1/models?limit=1",
        headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
    )
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            if response.status != 200:
                raise ValueError("LightRAG Anthropic credential check failed")
    except urllib.error.HTTPError as error:
        raise ValueError(f"LightRAG Anthropic credential check returned HTTP {error.code}") from None


def validate_anthropic_route(route: dict) -> None:
    endpoint = urlparse(str(route.get('host') or ''))
    if (route.get('binding') != 'openai'
            or not str(route.get('model') or '').startswith('claude-')
            or endpoint.scheme != 'https' or endpoint.hostname != 'api.anthropic.com'
            or endpoint.port not in (None, 443) or endpoint.username or endpoint.password):
        raise ValueError('Paper reasoning must use the existing Anthropic Claude API; no local-model fallback')


def check_runtime_reasoning(health: dict) -> None:
    """An edited .env is insufficient if the server still has an old role loaded."""
    configuration = health.get('configuration') or {}
    validate_anthropic_route({'binding': configuration.get('llm_binding'),
        'model': configuration.get('llm_model'), 'host': configuration.get('llm_binding_host')})
    roles = configuration.get('role_llm_config') or {}
    for name in ('extract', 'keyword', 'query', 'vlm'):
        if name not in roles:
            raise ValueError('Restart LightRAG and verify all Anthropic reasoning roles before ingestion')
        validate_anthropic_route(roles[name])


def is_local_url(url: str) -> bool:
    return (urlparse(url).hostname or "") in {"127.0.0.1", "localhost", "::1"}


def validate_target(url: str, api_key: str | None) -> None:
    """A hosted LightRAG must be reached over TLS with a key; never leak the key over http."""
    if is_local_url(url):
        return
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.username or parsed.password:
        raise ValueError("Hosted LightRAG URL must be https:// with no embedded credentials")
    if not api_key or len(api_key) < 32:
        raise ValueError("Hosted LightRAG requires LIGHTRAG_API_KEY (>=32 chars) in the environment")


def hosted_unreviewed(base: str, api_key: str | None, known: set[str]) -> list[str]:
    """Documents on the hosted graph that the worker did not admit and the baseline does not contain.

    Anything added through the WebUI, `kgctl upload` or `/documents/text` bypasses the DOI/hash/overlap
    checks, so later admission decisions would be made against an inventory we cannot see.
    """
    unknown, page = [], 1
    while True:
        result = api_json(base, "POST", "/documents/paginated",
                          {"page": page, "page_size": 200}, api_key)
        for doc in result.get("documents", []):
            path = str(doc.get("file_path") or "")
            if path not in known:
                unknown.append(path or str(doc.get("id")))
        if not (result.get("pagination") or {}).get("has_next"):
            return unknown
        page += 1


def poll_submitted(connection: sqlite3.Connection, base: str,
                   api_key: str | None) -> None:
    # A failed LightRAG job can later be recovered through its explicit
    # /reprocess_failed endpoint. Reconcile the same track ID; never re-upload.
    for row in connection.execute(
        "SELECT * FROM papers WHERE status IN ('submitted','failed','reprocessing') AND track_id IS NOT NULL"
    ):
        try:
            result = api_json(base, "GET", f"/documents/track_status/{row['track_id']}",
                              api_key=api_key)
        except (OSError, ValueError) as error:
            print(f"still waiting: {Path(row['pdf_path']).name} ({type(error).__name__})")
            continue
        statuses = {str(doc.get("status", "")).lower() for doc in result.get("documents", [])}
        if row["status"] == "failed" and statuses & {
            "pending", "parsing", "analyzing", "processing", "preprocessed"
        }:
            record(connection, row["pdf_sha256"], Path(row["pdf_path"]), "reprocessing",
                   doi=row["paper_doi"], body_hash=row["body_sha256"],
                   body_path=Path(row["body_path"]) if row["body_path"] else None,
                   source_id=row["source_id"], track_id=row["track_id"])
            print(f"reprocessing: {Path(row['pdf_path']).name}")
            continue
        if "processed" in statuses:
            status, reason = "processed", None
        elif "failed" in statuses:
            status, reason = "failed", "LightRAG reported failed; inspect its document status"
        else:
            continue
        if status == row["status"]:
            continue
        record(connection, row["pdf_sha256"], Path(row["pdf_path"]), status,
               doi=row["paper_doi"], body_hash=row["body_sha256"],
               body_path=Path(row["body_path"]) if row["body_path"] else None,
               source_id=row["source_id"], track_id=row["track_id"], reason=reason)
        print(f"{status}: {Path(row['pdf_path']).name}")


def process_pdf(path: Path, inbox: Path, output: Path, graph: Path,
                connection: sqlite3.Connection, base: str, api_key: str | None,
                min_age: int) -> None:
    if path.is_symlink() or not path.is_file() or time.time() - path.stat().st_mtime < min_age:
        return
    pdf_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    previous = connection.execute(
        "SELECT * FROM papers WHERE pdf_sha256=?", (pdf_hash,)
    ).fetchone()
    if previous and previous["status"] in TERMINAL | {"submitted", "submission_unknown"}:
        if str(path) != previous["pdf_path"]:
            print(f"duplicate file: {path.name}; original {Path(previous['pdf_path']).name}")
        return
    # A fully readable snapshot is required before any graph write.
    existing = graph_papers(graph)
    os.environ["PDF_ROOT"] = str(inbox)
    os.environ["OUTPUT_ROOT"] = str(output)
    os.environ["GROBID_URL"] = os.environ.get("GROBID_URL", "http://127.0.0.1:8070")
    try:
        saved_body = Path(previous['body_path']) if previous and previous['body_path'] else None
        saved_xml = saved_body.with_name(saved_body.name.replace('.body.txt', '.tei.xml')) if saved_body else None
        if (previous and previous['status'] in {'retry_wait', 'extracting_claims'}
                and saved_body and saved_body.is_file() and saved_xml and saved_xml.is_file()):
            parsed = {'tei_file': str(saved_xml), 'scientific_body_file': str(saved_body)}
        else:
            parsed = core.parse_pdf(str(path.relative_to(inbox)))
        xml = Path(parsed["tei_file"]).read_bytes()
        doi = paper_doi(xml)
        body_path = Path(parsed["scientific_body_file"])
        body = body_path.read_text(encoding="utf-8")
        body_digest = text_hash(body)
        body_shingles = shingles(body)
    except urllib.error.HTTPError as error:
        status = "retry_wait" if error.code in {429, 500, 502, 503, 504} else "failed"
        record(connection, pdf_hash, path, status,
               reason=f"GROBID HTTP {error.code}")
        print(f"{status}: {path.name}")
        return
    except (urllib.error.URLError, TimeoutError) as error:
        record(connection, pdf_hash, path, "retry_wait",
               reason=f"GROBID temporarily unreachable: {type(error).__name__}")
        print(f"waiting for GROBID: {path.name}")
        return
    except (OSError, ValueError, ET.ParseError) as error:
        record(connection, pdf_hash, path, "failed", reason=f"GROBID: {type(error).__name__}: {error}")
        print(f"failed to parse: {path.name}")
        return
    others = list(existing)
    for row in connection.execute(
        "SELECT * FROM papers WHERE pdf_sha256<>? AND status IN ('submitted','submission_unknown','processed','duplicate')",
        (pdf_hash,),
    ):
        old_body = Path(row["body_path"]) if row["body_path"] else None
        others.append({"source": row["pdf_path"], "doi": row["paper_doi"],
                       "body_hash": row["body_sha256"],
                       "shingles": shingles(old_body.read_text(encoding="utf-8"))
                       if old_body and old_body.is_file() else set()})
    duplicate = next((other for other in others if
                      (doi and doi == other["doi"]) or
                      body_digest == other["body_hash"]), None)
    if duplicate:
        record(connection, pdf_hash, path, "duplicate", doi=doi,
               body_hash=body_digest, body_path=body_path,
               reason=f"Same paper/content as {duplicate['source']}")
        print(f"duplicate paper: {path.name}; graph unchanged")
        return
    if not doi:
        reason = "No reliable paper DOI in GROBID header; manual identity review required"
    elif any(possible_same_text(body_shingles, other["shingles"]) for other in others):
        reason = "Substantial text overlap with an existing paper; manual identity review required"
    else:
        reason = None
    if reason:
        record(connection, pdf_hash, path, "review_required", doi=doi,
               body_hash=body_digest, body_path=body_path, reason=reason)
        print(f"held for review: {path.name}; graph unchanged")
        return
    source_id = "doi-" + hashlib.sha256(doi.encode()).hexdigest()[:20] + ".txt"
    # Preserve independent, source-scoped assertions before LightRAG merges
    # descriptions. Exact quotes are checked; candidates still need review.
    record(connection, pdf_hash, path, 'extracting_claims', doi=doi,
           body_hash=body_digest, body_path=body_path, source_id=source_id)
    try:
        extracted = claims.extract(Path(parsed["tei_file"]), output, doi,
                                   pdf_hash, path.stem)
        print(f"claims: {path.name}; {len(extracted['claims'])} evidence-linked candidates")
    except (OSError, ValueError, KeyError, ET.ParseError) as error:
        record(connection, pdf_hash, path, "retry_wait", doi=doi,
               body_hash=body_digest, body_path=body_path, source_id=source_id,
               reason=f"Local claim extraction: {type(error).__name__}; graph not submitted")
        print(f"waiting for claim extraction: {path.name} ({type(error).__name__})")
        return
    # Save intent BEFORE the network call. A crash or timeout must never cause
    # an automatic second submission with an unknown first outcome.
    record(connection, pdf_hash, path, "submission_unknown", doi=doi,
           body_hash=body_digest, body_path=body_path, source_id=source_id,
           reason="Submission outcome not yet known; do not retry automatically")
    try:
        result = api_json(base, "POST", "/documents/text",
                          {"text": body, "file_source": source_id}, api_key)
        track_id = result.get("track_id")
        if not track_id:
            raise ValueError("LightRAG did not return a track ID")
    except (OSError, ValueError, urllib.error.HTTPError) as error:
        print(f"submission uncertain: {path.name} ({type(error).__name__}); graph may have changed")
        return
    record(connection, pdf_hash, path, "submitted", doi=doi,
           body_hash=body_digest, body_path=body_path, source_id=source_id,
           track_id=track_id)
    print(f"submitted: {path.name}; awaiting LightRAG processing")


def run_once(args: argparse.Namespace, connection: sqlite3.Connection) -> None:
    if ingestion_control.paused(args.output):
        print('ingestion paused by user or outside the scheduled window')
        return
    poll_submitted(connection, args.lightrag_url, args.api_key)
    if connection.execute(
        "SELECT 1 FROM papers WHERE status='failed' AND track_id IS NOT NULL LIMIT 1"
    ).fetchone():
        print("ingestion paused: a LightRAG extraction failed; repair and reprocess it first")
        return
    if connection.execute(
        "SELECT 1 FROM papers WHERE status='submission_unknown' LIMIT 1"
    ).fetchone():
        print("ingestion paused: a submission outcome needs manual reconciliation")
        return
    if connection.execute(
        "SELECT 1 FROM papers WHERE status IN ('submitted','reprocessing') LIMIT 1"
    ).fetchone():
        print("waiting for the previously submitted paper to finish")
        return
    pdfs = [path for path in sorted(args.inbox.rglob("*")) if path.suffix.lower() == ".pdf"]
    if not pdfs:
        return
    try:
        with urllib.request.urlopen(
            os.environ.get("GROBID_URL", "http://127.0.0.1:8070").rstrip("/") + "/api/isalive",
            timeout=5,
        ) as response:
            if response.read().decode().strip().strip('"') != "true":
                raise ValueError("GROBID did not report healthy")
        validate_target(args.lightrag_url, args.api_key)
        health = api_json(args.lightrag_url, "GET", "/health", api_key=args.api_key)
        check_runtime_reasoning(health)
        if is_local_url(args.lightrag_url):
            check_remote_extraction_key(Path.home() / "LightRAG/.env")
        else:
            # The hosted service owns its credential; its /health role config was checked above.
            known = {p["source"] for p in graph_papers(args.graph)}
            known |= {r["source_id"] for r in connection.execute(
                "SELECT source_id FROM papers WHERE source_id IS NOT NULL")}
            unknown = hosted_unreviewed(args.lightrag_url, args.api_key, known)
            if unknown:
                print(f"ingestion paused: hosted graph holds {len(unknown)} document(s) admitted "
                      f"outside this worker (e.g. {unknown[0]}); review them first")
                return
    except (OSError, ValueError) as error:
        print(f"waiting for local services: {type(error).__name__}; no PDF submitted")
        return
    for path in pdfs:
        process_pdf(path, args.inbox, args.output, args.graph,
                    connection, args.lightrag_url, args.api_key, args.min_age)
        if connection.execute(
            "SELECT 1 FROM papers WHERE status IN ('submitted','submission_unknown','retry_wait') LIMIT 1"
        ).fetchone():
            # Keep extraction one paper at a time. The next pass sees a final
            # result before another remote model request is submitted.
            return


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--once", action="store_true")
    mode.add_argument("--watch", action="store_true")
    mode.add_argument("--status", action="store_true")
    parser.add_argument("--inbox", type=Path, default=DEFAULT_INBOX)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--lightrag-url", default="http://127.0.0.1:9621")
    parser.add_argument("--min-age", type=int, default=30,
                        help="Wait until a copied PDF has been stable for this many seconds")
    parser.add_argument("--interval", type=int, default=60)
    args = parser.parse_args()
    args.inbox = args.inbox.resolve()
    args.output = args.output.resolve()
    args.graph = args.graph.resolve()
    args.api_key = os.environ.get("LIGHTRAG_API_KEY")
    if not args.status:
        try:
            validate_target(args.lightrag_url, args.api_key)
        except ValueError as error:
            raise SystemExit(f"refusing to start: {error}")
    args.inbox.mkdir(parents=True, exist_ok=True)
    args.output.mkdir(parents=True, exist_ok=True)
    if args.status:
        connection = connect_ledger(args.output / "papers.sqlite")
        for status, count in connection.execute(
            "SELECT status, count(*) FROM papers GROUP BY status ORDER BY status"
        ):
            print(f"{status}: {count}")
        for row in connection.execute(
            "SELECT pdf_path,reason FROM papers WHERE status IN "
            "('review_required','submission_unknown','retry_wait','failed') ORDER BY updated_at"
        ):
            print(f"attention: {Path(row['pdf_path']).name}: {row['reason']}")
        connection.close()
        return
    with (args.output / "worker.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise SystemExit("Another GROBID batch worker is already running") from error
        connection = connect_ledger(args.output / "papers.sqlite")
        while True:
            try:
                run_once(args, connection)
            except (OSError, ValueError, json.JSONDecodeError) as error:
                print(f"worker paused: {type(error).__name__}: {error}", file=sys.stderr)
                if args.once:
                    raise SystemExit(1) from error
            if args.once:
                return
            time.sleep(max(args.interval, 10))


if __name__ == "__main__":
    main()
