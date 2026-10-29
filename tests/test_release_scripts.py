# Last updated: 2026-10-29 · Codex · explicit releases must not remain skipped by Render.
from pathlib import Path
import os,subprocess,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]

class ReleaseScriptTests(unittest.TestCase):
    def test_explicit_release_creates_normal_marker_after_skipped_commit(self):
        env=dict(os.environ,GIT_AUTHOR_NAME='Release test',GIT_COMMITTER_NAME='Release test',GIT_AUTHOR_EMAIL='release-test@example.invalid',GIT_COMMITTER_EMAIL='release-test@example.invalid')
        source=(ROOT/'Release Center/deploy-dev.command').read_text()
        block=source[source.index('# An explicit deployment'):source.index('echo "Pushing to staging')]
        with tempfile.TemporaryDirectory() as directory:
            def git(*args):return subprocess.run(['git',*args],cwd=directory,env=env,check=True,capture_output=True,text=True).stdout.strip()
            git('init');git('commit','--allow-empty','-m','Documentation only [skip render]');old=git('rev-parse','HEAD')
            subprocess.run(['bash','-eo','pipefail','-c',block],cwd=directory,env=env,check=True,capture_output=True)
            self.assertNotEqual(git('rev-parse','HEAD'),old)
            self.assertNotIn('[skip render]',git('log','-1','--format=%B'))
            before=git('rev-parse','HEAD')
            subprocess.run(['bash','-eo','pipefail','-c',block],cwd=directory,env=env,check=True,capture_output=True)
            self.assertEqual(git('rev-parse','HEAD'),before)

if __name__=='__main__':unittest.main()
