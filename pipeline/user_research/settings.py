# Last updated: 2026-10-28 15:51 UTC · Data/Backend · explicit environment configuration, without printing secrets.
"""CLI-only settings; .env.dev overlays non-empty values, matching the server."""
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[2]


def settings(environment, environ=None, root=None):
    if environment not in ('dev', 'prod'):
        raise ValueError('environment must be dev or prod')
    result = dict(os.environ if environ is None else environ)
    # On Render, its private runtime configuration is authoritative. A leftover
    # local dotenv file must never replace a dashboard-managed database or token.
    if str(result.get('RENDER', '')).strip().lower() == 'true':
        return result
    root = Path(root) if root is not None else ROOT
    for path in [root / '.env'] + ([root / '.env.dev'] if environment == 'dev' else []):
        if not path.is_file():
            continue
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            value = value.strip().strip('\"\'')
            if value:
                result[key.strip()] = value
    return result
