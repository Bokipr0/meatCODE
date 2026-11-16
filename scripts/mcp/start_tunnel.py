"""Interactive private pilot launcher. The runtime key stays in process memory only."""
import getpass,json,os,shlex,subprocess,sys
from pathlib import Path

def main():
    root=Path(__file__).resolve().parents[2]
    settings_path=root/'data/mcp-pilot/settings.json'
    if not settings_path.exists():raise SystemExit('Missing local data/mcp-pilot/settings.json; see platform_docs/MCP_PRIVATE_PILOT.md')
    settings=json.loads(settings_path.read_text())
    binary=Path(settings['tunnel_client'])
    command=shlex.join([sys.executable,'-m','server.mcp_pilot.main','--corpus-env',settings['corpus_env'],'--graph-env',settings['graph_env']])
    profile_dir=root/'data/mcp-pilot/profiles';profile_dir.mkdir(parents=True,exist_ok=True)
    profile=profile_dir/'meatcode.yaml'
    os.chdir(root)
    if not profile.exists():
        subprocess.run([str(binary),'init','--sample','sample_mcp_stdio_local','--profile','meatcode','--profile-dir',str(profile_dir),'--tunnel-id',settings['tunnel_id'],'--mcp-command',command,'--health-listen-addr','127.0.0.1:8792'],check=True)
    env=dict(os.environ)
    key=env.get('CONTROL_PLANE_API_KEY') or getpass.getpass('OpenAI runtime API key (hidden; not saved): ')
    if not key.strip():raise SystemExit('No key entered; tunnel not started.')
    env['CONTROL_PLANE_API_KEY']=key.strip()
    # The key is never part of argv, profile YAML or a printed command.
    subprocess.run([str(binary),'doctor','--profile','meatcode','--profile-dir',str(profile_dir),'--explain'],env=env,check=True)
    print('Private pilot ready to start. Keep this terminal open; Ctrl+C stops it.',flush=True)
    print('Health: http://127.0.0.1:8792/readyz',flush=True)
    os.execve(str(binary),[str(binary),'run','--profile','meatcode','--profile-dir',str(profile_dir)],env)

if __name__=='__main__':main()
