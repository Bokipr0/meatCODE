#!/usr/bin/env python3
# Last updated: 2026-10-20 · Codex / Full-Stack · narrowly configure the existing Docker MCP connection.
import argparse
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import tomllib

REPO = Path(__file__).resolve().parents[3]


def update_config(text, output):
    original = tomllib.loads(text)
    server = original['mcp_servers']['MCP_DOCKER']
    if server.get('args') != ['mcp', 'gateway', 'run', '--profile', 'meatcode']:
        raise ValueError('Expected the existing meatcode Docker gateway; no unrelated server was changed')
    pattern = r'(?ms)^\[mcp_servers\.MCP_DOCKER\]\s*\n(.*?)(?=^\[|\Z)'
    match = re.search(pattern, text)
    if not match or re.search(r'(?m)^env\s*=', match.group(1)):
        raise ValueError('Unsupported inline environment; no configuration changed')
    timeout = max(90, server.get('startup_timeout_sec', 0))
    block = match.group(0)
    if re.search(r'(?m)^startup_timeout_sec\s*=', block):
        block = re.sub(r'(?m)^startup_timeout_sec\s*=.*$', 'startup_timeout_sec = '+str(timeout), block)
    else:
        block = block.rstrip() + '\nstartup_timeout_sec = '+str(timeout)+'\n\n'
    updated = text[:match.start()] + block + text[match.end():]
    expected = copy.deepcopy(original)
    target = expected['mcp_servers']['MCP_DOCKER']
    target['startup_timeout_sec'] = timeout
    for key, path in [
        ('MCP_GATEWAY_DOCKER_BIND_ALLOWED_PATHS', '/Users/lior/LightRAG/inputs'),
        ('MCP_GATEWAY_DOCKER_BIND_ALLOW_WRITABLE_PATHS', str(output)),
    ]:
        existing = server.get('env', {}).get(key, '')
        paths = list(filter(None, existing.split(os.pathsep)))
        if path not in paths:
            paths.append(path)
        value = os.pathsep.join(paths)
        env_pattern = r'(?ms)^\[mcp_servers\.MCP_DOCKER\.env\]\s*\n(.*?)(?=^\[|\Z)'
        env_match = re.search(env_pattern, updated)
        line = key+' = '+json.dumps(value)
        if env_match:
            env_block = env_match.group(0)
            if re.search(r'(?m)^'+key+r'\s*=', env_block):
                env_block = re.sub(r'(?m)^'+key+r'\s*=.*$', line, env_block)
            else:
                env_block = env_block.rstrip()+'\n'+line+'\n\n'
            updated = updated[:env_match.start()] + env_block + updated[env_match.end():]
        else:
            updated = updated.rstrip()+'\n\n[mcp_servers.MCP_DOCKER.env]\n'+line+'\n'
        target.setdefault('env', {})[key] = value
    if tomllib.loads(updated) != expected:
        raise ValueError('Unexpected configuration change; original preserved')
    return updated


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    config = Path.home()/'.codex/config.toml'
    output = REPO/'data/grobid/mcp'
    original = config.read_text()
    updated = update_config(original, output)
    catalog = Path.home()/'.docker/mcp/catalogs/meatcode/grobid-server.yaml'
    if args.apply:
        output.mkdir(parents=True, exist_ok=True)
        catalog.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(Path(__file__).with_name('grobid-server.yaml'), catalog)
        if updated != original:
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
            backup = config.with_name('config.toml.before-grobid-'+stamp+'.bak')
            backup.write_text(original)
            backup.chmod(0o600)
            temporary = config.with_name('config.toml.grobid-new')
            temporary.write_text(updated)
            temporary.chmod(config.stat().st_mode & 0o777)
            os.replace(temporary, config)
    print(json.dumps({'mode': 'applied' if args.apply else 'preview', 'profile': 'meatcode',
        'catalog_entry': str(catalog), 'writable_output': str(output), 'startup_timeout_sec': 90}))


if __name__ == '__main__':
    main()
