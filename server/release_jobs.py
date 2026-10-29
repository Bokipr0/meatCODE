# Last updated: 2026-10-29 · Codex · tracked local-only publishing jobs; no credentials returned.
"""Terminal launch is not publishing success. Observe the actual exit status."""
import datetime,os,re,signal,subprocess,threading,uuid
from urllib.parse import urlsplit


def authorized_request(headers):
    if headers.get('X-MeatCODE-Release')!='1':return False
    if headers.get('Sec-Fetch-Site') not in (None,'same-origin','none'):return False
    origin=headers.get('Origin');host=headers.get('Host')
    try:
        parsed=urlsplit(origin or '')
        return bool(host and parsed.scheme in ('http','https') and parsed.netloc==host and not parsed.path and not parsed.query and not parsed.fragment)
    except ValueError:return False


def sanitized(text):
    text=re.sub(r'postgres(?:ql)?://[^\s]+','[private database connection]',text)
    text=re.sub(r'\b(?:sk-ant-|phx_)[A-Za-z0-9_\-]+','[private token]',text)
    return text[-8000:]


class Manager:
    def __init__(self):self.lock=threading.Lock();self.jobs={};self.latest=None

    def get(self,identifier=None):
        with self.lock:
            value=self.jobs.get(identifier or self.latest)
            return dict(value) if value else None

    def start(self,root,script,kind):
        if kind not in ('deploy-dev','promote'):raise ValueError('Unknown release action.')
        with self.lock:
            if self.latest and self.jobs[self.latest]['status']=='running':raise RuntimeError('A release is already running.')
            identifier=str(uuid.uuid4());self.latest=identifier
            self.jobs={identifier:{'id':identifier,'kind':kind,'status':'running','started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'message':'Publishing to GitHub…'}}
        threading.Thread(target=self._run,args=(identifier,root,script,kind),daemon=True).start()
        return self.get(identifier)

    def _run(self,identifier,root,script,kind):
        process=None
        try:
            env=dict(os.environ,RELEASE_CENTER_NONINTERACTIVE='1',GIT_TERMINAL_PROMPT='0')
            process=subprocess.Popen(['bash',script],cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,start_new_session=True)
            try:output,_=process.communicate(timeout=180)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGTERM)
                try:output,_=process.communicate(timeout=5)
                except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);output,_=process.communicate()
                raise TimeoutError('Publishing timed out. Check GitHub before retrying.')
            code=process.returncode
            branch='dev' if kind=='deploy-dev' else 'main'
            commit=''
            if code==0:
                result=subprocess.run(['git','rev-parse','origin/'+branch],cwd=root,capture_output=True,text=True,timeout=10,check=True)
                commit=result.stdout.strip()
                if not re.fullmatch('[a-f0-9]{40}',commit):raise ValueError('Could not verify published revision.')
            outcome={'status':'succeeded' if code==0 else 'failed','exit_code':code,'log':sanitized(output),'target_commit':commit,'environment':'dev' if kind=='deploy-dev' else 'prod','message':'GitHub updated; waiting for the hosted build.' if code==0 else 'Publishing failed. See the actual Git output below.'}
        except Exception as exc:
            outcome={'status':'failed','message':str(exc) if isinstance(exc,(TimeoutError,ValueError)) else 'Publishing could not complete. Check the local repository.','log':''}
        outcome['finished_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self.lock:self.jobs[identifier].update(outcome)

manager=Manager()
