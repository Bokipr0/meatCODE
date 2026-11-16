# Last updated: 2026-11-16 · Codex · Authenticated hosted scientific MCP.
"""Render entry point. Never starts a public listener without OAuth and invitations."""
import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import anyio
import httpx
import jwt
import uvicorn
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.transport_security import TransportSecuritySettings
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import FileResponse, HTMLResponse, JSONResponse, Response

from server.mcp_pilot.backend import Backend
from server.mcp_pilot.main import create_server

WEB = Path(__file__).with_name('web')


@dataclass(frozen=True)
class Settings:
    issuer: str
    resource: str
    invited: frozenset[str]

    @property
    def origin(self):
        value = urlsplit(self.resource)
        return f'{value.scheme}://{value.netloc}'

    @classmethod
    def from_env(cls):
        issuer = os.environ.get('NEON_AUTH_BASE_URL', '').rstrip('/')
        base = os.environ.get('MCP_PUBLIC_URL') or os.environ.get('RENDER_EXTERNAL_URL', '')
        resource = base.rstrip('/') + '/mcp'
        for value in (issuer, base):
            parsed = urlsplit(value)
            if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise ValueError('Hosted MCP requires configured HTTPS identity and public origins')
        if urlsplit(base).path not in ('', '/'):
            raise ValueError('MCP_PUBLIC_URL must be an origin without a path')
        invited = frozenset(e.strip().lower() for e in os.environ.get('MCP_INVITED_EMAILS', '').split(',') if e.strip())
        if not invited or any('@' not in e for e in invited):
            raise ValueError('At least one invited email must be configured')
        if not all(os.environ.get(key) for key in ('MCP_DATABASE_URL', 'MCP_GRAPH_DATABASE_URL')):
            raise ValueError('Both restricted scientific connections must be configured')
        return cls(issuer, resource, invited)


class InvitedTokenVerifier:
    """Verify the exact branch/resource, then the verified, invited email via OIDC."""
    def __init__(self, settings):
        self.settings = settings
        self.jwks = jwt.PyJWKClient(settings.issuer + '/.well-known/jwks.json', timeout=5)
        self._identities = {}

    def claims(self, token):
        key = self.jwks.get_signing_key_from_jwt(token)
        return jwt.decode(token, key.key, algorithms=['EdDSA'], audience=self.settings.resource,
                          issuer=self.settings.issuer, options={'require': ['exp', 'iss', 'aud', 'sub']})

    async def identity(self, token):
        async with httpx.AsyncClient(timeout=5, follow_redirects=False) as client:
            response = await client.get(self.settings.issuer + '/oauth2/userinfo',
                                        headers={'Authorization': 'Bearer ' + token})
            response.raise_for_status()
            return response.json()

    async def verify_token(self, token):
        if not isinstance(token, str) or len(token) > 16384:
            return None
        try:
            claims = await anyio.to_thread.run_sync(self.claims, token)
            scopes = claims.get('scope', '').split()
            if not {'openid', 'email'}.issubset(scopes):
                return None
            if not isinstance(claims.get('sub'), str) or not claims['sub'] or not isinstance(claims.get('client_id'), str):
                return None
            digest = hashlib.sha256(token.encode()).hexdigest()
            cached = self._identities.get(digest)
            now = time.time()
            if cached and cached[0] > now:
                identity = cached[1]
            else:
                identity = await self.identity(token)
                # Bounded cache; no bearer credentials retained as keys or values.
                self._identities = {k: v for k, v in self._identities.items() if v[0] > now}
                if len(self._identities) >= 256:
                    self._identities.clear()
                self._identities[digest] = (min(now + 60, claims['exp']), identity)
            email = identity.get('email', '').strip().lower()
            if identity.get('sub') != claims['sub'] or identity.get('email_verified') is not True or email not in self.settings.invited:
                return None
            return AccessToken(token=token, client_id=claims['client_id'], scopes=scopes,
                               expires_at=claims['exp'], subject=claims['sub'], resource=self.settings.resource)
        except (jwt.PyJWTError, httpx.HTTPError, ValueError, TypeError, KeyError, AttributeError):
            return None


class BrowserHeaders(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers.update({
            'Cache-Control': 'no-store',
            'Referrer-Policy': 'no-referrer',
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self' https://*.neon.tech https://*.neon.com; frame-src https://*.neon.tech https://*.neon.com; img-src 'self' data:; form-action 'self'; base-uri 'none'; frame-ancestors 'none'",
        })
        return response


def create_hosted_app(settings=None, backend=None, verifier=None):
    settings = settings or Settings.from_env()
    verifier = verifier or InvitedTokenVerifier(settings)
    backend = backend or Backend()
    server = create_server(backend, host='0.0.0.0', port=int(os.environ.get('PORT', '10000')),
        auth=AuthSettings(issuer_url=settings.issuer, resource_server_url=settings.resource,
                          required_scopes=['openid', 'email'], validate_token_resource=True),
        token_verifier=verifier,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=True,
            allowed_hosts=[urlsplit(settings.resource).netloc],
            allowed_origins=[settings.origin, 'https://chatgpt.com']))

    @server.custom_route('/healthz', methods=['GET'])
    async def health(request):
        return JSONResponse({'status': 'ok', 'service': 'MeatCODE MCP', 'authentication': 'required',
                             'revision': os.environ.get('RENDER_GIT_COMMIT', 'local')})

    @server.custom_route('/api/config', methods=['GET'])
    async def config(request):
        return JSONResponse({'issuer': settings.issuer, 'resource': settings.resource})

    @server.custom_route('/api/invitation', methods=['POST'])
    async def invitation(request):
        # This is a UX hint only. Tool authorization always checks OIDC identity.
        if request.headers.get('origin') != settings.origin or request.headers.get('content-type', '').split(';')[0] != 'application/json':
            return Response(status_code=403)
        body = b''
        async for chunk in request.stream():
            body += chunk
            if len(body) > 512:
                return Response(status_code=413)
        try:
            email = json.loads(body)['email'].strip().lower()
        except (KeyError, ValueError, TypeError, AttributeError):
            return Response(status_code=400)
        return JSONResponse({'invited': email in settings.invited})

    @server.custom_route('/assets/signin.js', methods=['GET'])
    async def script(request):
        return FileResponse(WEB / 'dist' / 'signin.js', media_type='text/javascript')

    @server.custom_route('/assets/signin.css', methods=['GET'])
    async def style(request):
        return FileResponse(WEB / 'signin.css', media_type='text/css')

    @server.custom_route('/', methods=['GET'])
    @server.custom_route('/auth/sign-in', methods=['GET'])
    @server.custom_route('/auth/consent', methods=['GET'])
    async def page(request):
        return HTMLResponse((WEB / 'signin.html').read_text())

    app = server.streamable_http_app()
    app.add_middleware(BrowserHeaders)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=[urlsplit(settings.resource).hostname])
    return app


if __name__ == '__main__':
    # No request/access logs: OAuth query strings and credentials must not enter logs.
    uvicorn.run(create_hosted_app(), host='0.0.0.0', port=int(os.environ.get('PORT', '10000')),
                access_log=False, log_level='warning')
