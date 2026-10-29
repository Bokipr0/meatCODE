"""2026-10-29: offline checks for the demo load-test harness, not live capacity evidence."""
import importlib.util
import json
from pathlib import Path
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

spec=importlib.util.spec_from_file_location('five',Path(__file__).parents[1]/'pipeline/oracle_five_user_check.py')
five=importlib.util.module_from_spec(spec);spec.loader.exec_module(five)

class HarnessTests(unittest.TestCase):
    def exercise(self,done=True):
        lock=threading.Lock(); counters={'active':0,'peak':0}
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_GET(self):
                self.send_response(200);self.end_headers();self.wfile.write(b'page')
            def do_POST(self):
                data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                marker=data['question'].split('exact label ')[1].split('.')[0]
                with lock:
                    counters['active']+=1;counters['peak']=max(counters['peak'],counters['active'])
                time.sleep(.15)
                self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
                self.wfile.write(('event: sources\ndata: []\n\nevent: chunk\ndata: '+marker+'\n\nevent: chunk\ndata:   synthetic answer\n\n'+
                                  ('event: done\ndata: \n\n' if done else '')).encode())
                with lock: counters['active']-=1
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try: report=five.run_clients('http://127.0.0.1:'+str(server.server_port),'test','test',5)
        finally: server.shutdown();server.server_close();thread.join()
        return report,counters
    def test_five_overlapping_answers_and_markers(self):
        report,counters=self.exercise()
        self.assertEqual(counters['peak'],5)
        self.assertEqual(report['completed'],5)
        self.assertEqual(report['marker_check'],'pass')
        for result in report['results']:
            self.assertEqual(result['answer'],result['marker']+'  synthetic answer')
    def test_incomplete_stream_is_not_success(self):
        report,_=self.exercise(False)
        self.assertEqual(report['completed'],0)
        self.assertEqual(report['marker_check'],'needs review')

if __name__=='__main__': unittest.main()
