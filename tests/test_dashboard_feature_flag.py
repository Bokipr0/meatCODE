# Last updated: 2026-10-29 · Codex · Release Center controls dashboard pages and APIs.
import ast
from pathlib import Path
import unittest
from urllib.parse import urlparse


class DashboardFlagTests(unittest.TestCase):
    def gate(self, enabled):
        tree=ast.parse(Path('server/meatcode_server.py').read_text())
        handler=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Handler')
        selected=[n for n in handler.body if isinstance(n,ast.FunctionDef) and n.name in ('do_GET','do_POST','send_head')]
        class Static:
            def send_head(self):return 'static'
        ns={'urlparse':urlparse,'_flag_on':lambda key:enabled,'APP_ENV':'prod','Static':Static}
        module=ast.Module(body=[ast.ClassDef(name='Gate',bases=[ast.Name(id='Static',ctx=ast.Load())],keywords=[],body=selected,decorator_list=[])],type_ignores=[])
        exec(compile(ast.fix_missing_locations(module),'<dashboard-flag>', 'exec'),ns)
        gate=ns['Gate']();gate._authorized=lambda:True;gate._private_research_path=lambda path:False
        gate._send_json=lambda data,status=200:status;gate.send_error=lambda *args:None
        gate._handle_api_get=lambda path:'enabled-api';gate._deny=lambda:'denied'
        return gate

    def test_flag_off_blocks_pages_queries_and_private_reads(self):
        gate=self.gate(False)
        for path in ('/research-dashboard','/research-dashboard/','/research-dashboard?environment=prod','/app/internal/research-dashboard.html','/api/research/dashboard','/api/research/transcript','/api/research/journey'):
            gate.path=path
            self.assertEqual(gate.do_GET(),404,path)
        gate.path='/api/research/operations';self.assertEqual(gate.do_POST(),404)
        for path in ('/research-dashboard','/app/internal/research-dashboard.html'):
            gate.path=path;self.assertIsNone(gate.send_head())

    def test_on_allows_api_dispatch_without_bypassing_auth(self):
        gate=self.gate(True);gate.path='/api/research/dashboard';self.assertEqual(gate.do_GET(),'enabled-api')
        gate._authorized=lambda:False;self.assertEqual(gate.do_GET(),'denied')

    def test_collection_routes_are_independent_of_dashboard_switch(self):
        gate=self.gate(False);gate.path='/api/research/config';self.assertEqual(gate.do_GET(),'enabled-api')

    def test_registry_is_dev_on_prod_off(self):
        import json
        flag=json.loads(Path('Release Center/features.json').read_text())['flags']['live_testing_dashboard']
        self.assertTrue(flag['dev']);self.assertFalse(flag['prod'])
