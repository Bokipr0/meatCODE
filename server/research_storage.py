# Last updated: 2026-10-29 · Codex · isolated research storage; no silent fallback after cutover.
"""Shared resolver for research ingestion, dashboard and maintenance only."""
def database_url(environ, legacy_url=None):
    configured=str(environ.get('RESEARCH_DATABASE_URL') or '').strip()
    if configured:return configured
    if str(environ.get('RESEARCH_DATABASE_REQUIRED','')).strip().lower() in ('1','true','yes','on'):return None
    return legacy_url or environ.get('DATABASE_URL')
