"""2026-10-29: bounded five-client live Oracle smoke test; no database writes/deploys.
Uses real model calls. Reports are private, under ignored data/demo_checks.
This checks HTTP/SSE concurrency, not browser storage or comprehensive tenant isolation.
"""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import getpass
import json
import os
from pathlib import Path
import threading
import time
import urllib.request
import urllib.error
from urllib.parse import urlsplit
import uuid

TOPICS = [
    'What role does cysteine play in producing meaty aromas during Maillard reactions?',
    'How can lipid oxidation contribute to off-flavours in plant-based meat?',
    'How does cooking temperature influence pyrazine formation?',
    'What approaches can reduce beany aroma in pea protein products?',
    'What is the difference between aroma and umami taste in meat alternatives?',
]

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError('Redirect refused: verify the website URL before sending credentials.')

def run_clients(base, user, password, timeout=180):
    barrier = threading.Barrier(5, timeout=timeout)
    stamp = uuid.uuid4().hex[:10]
    markers = ['DEMO_'+stamp+'_'+str(i+1) for i in range(5)]
    auth = base64.b64encode((user+':'+password).encode()).decode()
    def client(i):
        result = {'client':i+1, 'question':TOPICS[i], 'marker':markers[i],
                  'success':False, 'answer':'', 'events':[], 'source_count':0}
        opener = urllib.request.build_opener(NoRedirect())
        headers = {'Authorization':'Basic '+auth}
        started = None
        try:
            with opener.open(urllib.request.Request(base+'/app/meatcode_mockup.html',headers=headers), timeout=timeout) as page:
                result['page_status'] = page.status
                if page.status != 200: raise RuntimeError('Page did not return HTTP 200')
            barrier.wait()
            started = time.monotonic()
            result['started_utc'] = datetime.now(timezone.utc).isoformat()
            body = {'question': 'Begin your answer with the exact label '+markers[i]+'. '+TOPICS[i]}
            req = urllib.request.Request(base+'/api/ask',data=json.dumps(body).encode(),
                                         headers={**headers,'Content-Type':'application/json'},method='POST')
            with opener.open(req,timeout=timeout) as response:
                result['http_status'] = response.status
                if 'text/event-stream' not in response.headers.get('Content-Type',''):
                    raise RuntimeError('Expected an Oracle event stream')
                event, lines, size = '', [], 0
                for raw in response:
                    if time.monotonic()-started > timeout: raise TimeoutError('Answer exceeded time budget')
                    size += len(raw)
                    if size > 2_000_000: raise RuntimeError('Response exceeded safety limit')
                    line = raw.decode('utf-8').rstrip('\r\n')
                    if line.startswith('event:'): event = line[6:].strip()
                    elif line.startswith('data:'):
                        # SSE removes at most one separator space; remaining spaces are content.
                        value = line[5:]
                        lines.append(value[1:] if value.startswith(' ') else value)
                    elif not line:
                        data = '\n'.join(lines)
                        result['events'].append(event)
                        if event == 'chunk':
                            result.setdefault('first_text_seconds',round(time.monotonic()-started,2))
                            result['answer'] += data
                        elif event == 'sources': result['source_count'] = len(json.loads(data))
                        elif event == 'error': raise RuntimeError('Oracle returned an error event')
                        elif event == 'done':
                            result['success'] = bool(result['answer'].strip())
                            break
                        event, lines = '', []
                if not result['success']: raise RuntimeError('Stream ended without a completed answer')
            result['own_marker_present'] = markers[i] in result['answer']
            result['foreign_marker_present'] = any(m in result['answer'] for j,m in enumerate(markers) if i != j)
        except Exception as exc:
            barrier.abort()
            # Do not dump request headers, URLs with credentials, or provider diagnostics.
            result['error_type'] = type(exc).__name__
            if isinstance(exc, urllib.error.HTTPError): result['http_status'] = exc.code
            elif isinstance(exc, RuntimeError): result['error'] = str(exc)
        finally:
            if started is not None: result['elapsed_seconds'] = round(time.monotonic()-started,2)
        return result
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(client,range(5)))
    return {'target':base,'created_utc':datetime.now(timezone.utc).isoformat(),
            'mode':'five independent HTTP clients, single-turn Oracle, real provider calls',
            'completed':sum(r['success'] for r in results),
            'marker_check':'pass' if all(r.get('own_marker_present') and not r.get('foreign_marker_present') for r in results) else 'needs review',
            'limitations':'Not a browser test, scientific accuracy evaluation, or proof of complete user isolation. No consented research sessions are created.',
            'results':results}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--url',default='https://meatcode-oracle.onrender.com')
    args=p.parse_args()
    base=args.url.rstrip('/')
    url=urlsplit(base)
    if url.scheme not in ('https','http') or not url.hostname or url.username or url.password or url.query or url.fragment or url.path:
        p.error('Use only the website origin, without a path or credentials.')
    if url.scheme!='https' and url.hostname not in ('localhost','127.0.0.1','::1'):
        p.error('Remote websites require HTTPS.')
    print('This sends FIVE simultaneous questions using real model calls to '+base)
    print('Keep other demo traffic low while measuring. No files or database records are modified by this client.')
    user=input('Site username [meatcode]: ').strip() or 'meatcode'
    password=getpass.getpass('Site password (hidden; not saved): ')
    print('Running five clients. Allow up to a few minutes...')
    report=run_clients(base,user,password)
    os.umask(0o077)
    out=Path(__file__).resolve().parents[1]/'data/demo_checks'
    out.mkdir(parents=True,exist_ok=True)
    path=out/('five-users-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'.json')
    path.write_text(json.dumps(report,indent=2)+'\n')
    for r in report['results']:
        print('Client',r['client'], 'OK' if r['success'] else 'FAILED',
              'first text:',r.get('first_text_seconds','-'),'s; total:',r.get('elapsed_seconds','-'),
              's; sources:',r['source_count'],r.get('error_type',''))
    print('Completed:',str(report['completed'])+'/5; answer-marker check:',report['marker_check'])
    print('Questions, answers and timings saved to:',path)
    print('Missing markers require review; a passing marker check is not a privacy guarantee.')
    return 0 if report['completed']==5 and report['marker_check']=='pass' else 1

if __name__=='__main__': raise SystemExit(main())
