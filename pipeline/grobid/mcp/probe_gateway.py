#!/usr/bin/env python3
# Last updated: 2026-10-20 · Codex / Full-Stack · actual JSON-RPC MCP gateway verification.
import argparse
import json
import os
from pathlib import Path
import selectors
import subprocess
import tempfile
import time

REPO = Path(__file__).resolve().parents[3]


class Gateway:
    def __init__(self):
        env = dict(os.environ)
        env['MCP_GATEWAY_DOCKER_BIND_ALLOW_WRITABLE_PATHS'] = str(REPO/'data/grobid/mcp')
        env['MCP_GATEWAY_DOCKER_BIND_ALLOWED_PATHS'] = '/Users/lior/LightRAG/inputs'
        self.log = tempfile.TemporaryFile()
        self.process = subprocess.Popen(['docker','mcp','gateway','run','--profile','meatcode'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log, env=env)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.process.stdout, selectors.EVENT_READ)
        self.buffer = b''
        self.counter = 0

    def send(self, value):
        self.process.stdin.write((json.dumps(value)+'\n').encode())
        self.process.stdin.flush()

    def request(self, method, params, timeout=150):
        self.counter += 1
        wanted = self.counter
        self.send({'jsonrpc':'2.0','id':wanted,'method':method,'params':params})
        deadline = time.monotonic()+timeout
        while time.monotonic()<deadline:
            while b'\n' in self.buffer:
                line, self.buffer = self.buffer.split(b'\n',1)
                try: data=json.loads(line)
                except (ValueError,UnicodeDecodeError): continue
                if data.get('id') == wanted:
                    if 'error' in data: raise RuntimeError(json.dumps(data['error']))
                    return data['result']
            if not self.selector.select(min(1,max(0,deadline-time.monotonic()))):
                continue
            raw=os.read(self.process.stdout.fileno(),65536)
            if not raw:
                self.log.seek(0)
                raise RuntimeError('Gateway exited: '+self.log.read().decode(errors='replace')[-2000:])
            self.buffer += raw
        raise TimeoutError('Gateway request timed out: '+method)

    def call(self, tool, arguments=None):
        result=self.request('tools/call',{'name':tool,'arguments':arguments or {}},timeout=240)
        if result.get('isError'): raise RuntimeError(json.dumps(result))
        if result.get('structuredContent'):
            data=result['structuredContent']
            return data.get('result',data)
        for content in result.get('content',[]):
            if content.get('type')=='text':
                try:return json.loads(content['text'])
                except ValueError:pass
        raise ValueError('Tool returned no structured result')

    def close(self):
        self.process.terminate()
        try:self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:self.process.kill();self.process.wait()
        self.selector.close();self.log.close()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--parse', help='Optional relative PDF path to parse through MCP')
    args=parser.parse_args()
    gateway=Gateway()
    try:
        gateway.request('initialize',{'protocolVersion':'2025-06-18','capabilities':{},
            'clientInfo':{'name':'meatcode-grobid-verification','version':'1.0'}})
        gateway.send({'jsonrpc':'2.0','method':'notifications/initialized'})
        tools=gateway.request('tools/list',{})['tools']
        names=[t['name'] for t in tools]
        missing=[name for name in ['grobid_status','grobid_list_pdfs','grobid_parse_pdf']
                 if not any(n.endswith(name) for n in names)]
        if missing:
            gateway.log.seek(0)
            raise RuntimeError('Missing tools '+str(missing)+'; available '+str(names)+
                               '; log: '+gateway.log.read().decode(errors='replace')[-8000:])
        selected={name:next(n for n in names if n.endswith(name)) for name in
                  ['grobid_status','grobid_list_pdfs','grobid_parse_pdf']}
        report={'profile':'meatcode','grobid_tools':selected,
                'status':gateway.call(selected['grobid_status']),
                'pdfs':gateway.call(selected['grobid_list_pdfs'])}
        assert report['status']['healthy']
        if args.parse:
            report['parsed']=gateway.call(selected['grobid_parse_pdf'],{'relative_path':args.parse})
            assert report['parsed']['body_paragraphs']>0
        output=REPO/'data/grobid/mcp-gateway-verification.json'
        output.write_text(json.dumps(report,indent=2))
        print(json.dumps(report,indent=2))
    finally:
        gateway.close()


if __name__=='__main__':main()
