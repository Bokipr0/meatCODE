# Last updated: 2026-10-20 · Codex / Full-Stack · local GROBID MCP operations and path boundaries.
import hashlib
import json
import os
from pathlib import Path
import re
import threading
import urllib.request
import uuid
import xml.etree.ElementTree as ET

NS = {'t': 'http://www.tei-c.org/ns/1.0'}
PARSER_LOCK = threading.Lock()


def roots():
    return Path(os.environ.get('PDF_ROOT', '/pdfs')).resolve(), Path(os.environ.get('OUTPUT_ROOT', '/outputs')).resolve()


def status():
    base = os.environ.get('GROBID_URL', 'http://host.docker.internal:8070').rstrip('/')
    with urllib.request.urlopen(base + '/api/isalive', timeout=10) as response:
        alive = response.read().decode().strip().strip('"') == 'true'
    with urllib.request.urlopen(base + '/api/version', timeout=10) as response:
        version = json.load(response)
    return {'healthy': alive, 'version': version, 'pdf_root': '/pdfs', 'output_root': '/outputs'}


def resolve_pdf(relative_path):
    root, _ = roots()
    relative = Path(relative_path)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('Use a relative path returned by grobid_list_pdfs')
    target = (root / relative).resolve(strict=True)
    if not target.is_relative_to(root) or target.suffix.lower() != '.pdf' or not target.is_file():
        raise ValueError('Only PDFs inside the configured input folder are accepted')
    if target.stat().st_size > 50 * 1024 * 1024:
        raise ValueError('PDF exceeds the 50 MiB request limit')
    with target.open('rb') as stream:
        if not stream.read(1024).lstrip().startswith(b'%PDF-'):
            raise ValueError('Input is not a PDF')
    return target


def list_pdfs():
    root, _ = roots()
    result = []
    for path in sorted(root.rglob('*')):
        if path.suffix.lower() != '.pdf' or not path.is_file() or not path.resolve().is_relative_to(root):
            continue
        result.append({'path': str(path.relative_to(root)), 'bytes': path.stat().st_size})
        if len(result) >= 200:
            break
    return {'pdfs': result, 'root': '/pdfs', 'limit': 200}


def scientific_body(xml):
    root = ET.fromstring(xml)
    if root.tag != '{http://www.tei-c.org/ns/1.0}TEI':
        raise ValueError('GROBID did not return TEI XML')
    body = root.find('t:text/t:body', NS)
    if body is None:
        raise ValueError('TEI has no scientific body')
    # Bibliography, author metadata and XML syntax are deliberately excluded.
    blocks = []
    for element in body.iter():
        if element.tag not in {'{'+NS['t']+'}head', '{'+NS['t']+'}p', '{'+NS['t']+'}figDesc'}:
            continue
        text = re.sub(r'\s+', ' ', ''.join(element.itertext())).strip()
        if text:
            blocks.append(text)
    return root, '\n\n'.join(blocks)


def parse_pdf(relative_path):
    path = resolve_pdf(relative_path)
    pdf = path.read_bytes()
    boundary = 'grobid-' + uuid.uuid4().hex
    field = (f'--{boundary}\r\nContent-Disposition: form-data; name="input"; filename="paper.pdf"\r\n'
             'Content-Type: application/pdf\r\n\r\n').encode() + pdf + b'\r\n'
    for key in ('consolidateHeader', 'consolidateCitations', 'consolidateFunders'):
        field += f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n0\r\n'.encode()
    field += f'--{boundary}--\r\n'.encode()
    base = os.environ.get('GROBID_URL', 'http://host.docker.internal:8070').rstrip('/')
    request = urllib.request.Request(base + '/api/processFulltextDocument', data=field,
        headers={'Content-Type': 'multipart/form-data; boundary=' + boundary})
    if not PARSER_LOCK.acquire(timeout=180):
        raise TimeoutError('The GROBID parser is busy; retry after the current PDF finishes')
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            xml = response.read(25 * 1024 * 1024 + 1)
    finally:
        PARSER_LOCK.release()
    if len(xml) > 25 * 1024 * 1024:
        raise ValueError('TEI response exceeds the configured output limit')
    root, body = scientific_body(xml)
    if not body.strip():
        raise ValueError('No scientific body text was extracted; inspect the PDF manually')
    _, output = roots()
    output.mkdir(parents=True, exist_ok=True)
    result_id = uuid.uuid4().hex
    xml_path = output / (result_id + '.tei.xml')
    text_path = output / (result_id + '.body.txt')
    xml_path.write_bytes(xml)
    text_path.write_text(body)
    report = {'result_id': result_id, 'input_pdf': relative_path,
              'input_sha256': hashlib.sha256(pdf).hexdigest(),
              'tei_file': str(xml_path), 'scientific_body_file': str(text_path),
              'tei_bytes': len(xml), 'body_characters': len(body),
              'body_paragraphs': len(root.findall('.//t:body//t:p', NS)),
              'bibliographic_references': len(root.findall('.//t:listBibl/t:biblStruct', NS)),
              'external_consolidation': False, 'light_rag_or_neon_modified': False}
    (output / (result_id + '.json')).write_text(json.dumps(report, indent=2))
    return report
