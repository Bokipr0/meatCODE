# Last updated: 2026-10-29 · Codex · publishing completion, failure, concurrency and origin boundaries.
from email.message import Message
from pathlib import Path
import sys,tempfile,time,unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
import release_jobs

class ReleaseJobTests(unittest.TestCase):
    def test_release_requires_same_origin_and_explicit_custom_header(self):
        for origin,site,marker,allowed in [('http://localhost:8000','same-origin','1',True),('https://evil.example','cross-site','1',False),(None,None,'1',False),('http://localhost:8000','same-origin',None,False)]:
            h=Message();h['Host']='localhost:8000'
            for key,value in [('Origin',origin),('Sec-Fetch-Site',site),('X-MeatCODE-Release',marker)]:
                if value is not None:h[key]=value
            self.assertEqual(release_jobs.authorized_request(h),allowed)

    def test_real_failed_script_is_reported_as_failure_with_actual_error(self):
        with tempfile.TemporaryDirectory() as directory:
            script=Path(directory)/'publish.sh';script.write_text('echo "non-fast-forward rejected"\nexit 1\n')
            manager=release_jobs.Manager();job=manager.start(directory,str(script),'deploy-dev')
            for _ in range(100):
                result=manager.get(job['id'])
                if result['status']!='running':break
                time.sleep(.01)
            self.assertEqual(result['status'],'failed');self.assertEqual(result['exit_code'],1)
            self.assertIn('non-fast-forward',result['log'])

    def test_success_verifies_the_published_remote_ref(self):
        with tempfile.TemporaryDirectory() as directory:
            script=Path(directory)/'publish.sh';script.write_text('test "$RELEASE_CENTER_NONINTERACTIVE" = 1\necho pushed\n')
            class Result:stdout='a'*40
            manager=release_jobs.Manager()
            with patch.object(release_jobs.subprocess,'run',return_value=Result()) as run:
                job=manager.start(directory,str(script),'promote')
                for _ in range(100):
                    result=manager.get(job['id'])
                    if result['status']!='running':break
                    time.sleep(.01)
                self.assertEqual(result['status'],'succeeded');self.assertEqual(result['target_commit'],'a'*40)
                self.assertEqual(run.call_args.args[0],['git','rev-parse','origin/main'])

    def test_parallel_actions_are_rejected_and_credentials_redacted(self):
        manager=release_jobs.Manager();manager.latest='one';manager.jobs['one']={'status':'running'}
        with self.assertRaises(RuntimeError):manager.start('/tmp','unused','promote')
        text=release_jobs.sanitized('postgresql://user:private@host/db sk-ant-private_fixture')
        self.assertNotIn('private@',text);self.assertNotIn('sk-ant-',text)

if __name__=='__main__':unittest.main()
