# Last updated: 2026-11-16 · Codex · OAuth and invitation boundary tests.
import asyncio
import json
import time
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from starlette.testclient import TestClient

from server.mcp_pilot.hosted import InvitedTokenVerifier, Settings, create_hosted_app


SETTINGS = Settings('https://auth.example.org/neondb/auth', 'https://mcp.example.org/mcp', frozenset({'invited@example.org'}))


class OAuthBoundaries(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.private = Ed25519PrivateKey.generate()
        self.verifier = InvitedTokenVerifier(SETTINGS)
        self.verifier.jwks = SimpleNamespace(get_signing_key_from_jwt=lambda _: SimpleNamespace(key=self.private.public_key()))
        self.verifier.identity = AsyncMock(return_value={'sub': 'user-1', 'email': 'invited@example.org', 'email_verified': True})

    def token(self, **changes):
        claims = {'iss': SETTINGS.issuer, 'aud': [SETTINGS.resource, SETTINGS.issuer + '/oauth2/userinfo'],
                  'exp': int(time.time()) + 600, 'sub': 'user-1', 'scope': 'openid email profile', 'client_id': 'chatgpt'}
        claims.update(changes)
        return jwt.encode(claims, self.private, algorithm='EdDSA')

    async def test_verified_invitation_and_array_audience(self):
        result = await self.verifier.verify_token(self.token())
        self.assertEqual(result.subject, 'user-1')
        self.assertEqual(result.resource, SETTINGS.resource)

    async def test_bad_branch_resource_expiry_signature_and_missing_scope(self):
        for change in ({'iss': SETTINGS.issuer + '-dev'}, {'aud': 'https://other.example.org/mcp'},
                       {'exp': int(time.time()) - 5}, {'scope': 'openid'}, {'sub': ''}):
            self.assertIsNone(await self.verifier.verify_token(self.token(**change)))
        other = Ed25519PrivateKey.generate()
        self.assertIsNone(await self.verifier.verify_token(jwt.encode({'iss': SETTINGS.issuer}, other, algorithm='EdDSA')))
        self.verifier.identity.assert_not_awaited()

    async def test_uninvited_unverified_and_mismatched_subject(self):
        for identity in ({'sub': 'user-1', 'email': 'outsider@example.org', 'email_verified': True},
                         {'sub': 'user-1', 'email': 'invited@example.org', 'email_verified': False},
                         {'sub': 'other', 'email': 'invited@example.org', 'email_verified': True}):
            self.verifier._identities.clear()
            self.verifier.identity.return_value = identity
            self.assertIsNone(await self.verifier.verify_token(self.token()))

    async def test_auth_outage_fails_closed(self):
        import httpx
        self.verifier.identity.side_effect = httpx.ConnectError('offline')
        self.assertIsNone(await self.verifier.verify_token(self.token()))


class HostedProtocol(unittest.TestCase):
    def test_authenticated_protocol_discovers_and_calls_scientific_tools(self):
        private = Ed25519PrivateKey.generate()
        verifier = InvitedTokenVerifier(SETTINGS)
        verifier.jwks = SimpleNamespace(get_signing_key_from_jwt=lambda _: SimpleNamespace(key=private.public_key()))
        verifier.identity = AsyncMock(return_value={'sub': 'owner', 'email': 'invited@example.org', 'email_verified': True})
        token = jwt.encode({'iss': SETTINGS.issuer, 'aud': SETTINGS.resource, 'exp': int(time.time()) + 600,
                            'sub': 'owner', 'client_id': 'test-client', 'scope': 'openid email'}, private, algorithm='EdDSA')
        backend = SimpleNamespace(search=lambda query: {'results': [{'id': '880', 'title': query}]},
                                  fetch=lambda id: {'id': id}, graph_search=lambda query, limit: {'items': [], 'limit': limit})
        headers = {'Authorization': 'Bearer ' + token, 'Accept': 'application/json, text/event-stream'}
        with TestClient(create_hosted_app(SETTINGS, backend, verifier), base_url='https://mcp.example.org', headers=headers) as client:
            init = client.post('/mcp', json={'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {
                'protocolVersion': '2025-11-25', 'capabilities': {}, 'clientInfo': {'name': 'test', 'version': '1'}}})
            self.assertEqual(init.status_code, 200)
            listed = client.post('/mcp', json={'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'}).json()
            self.assertEqual({tool['name'] for tool in listed['result']['tools']}, {'search', 'fetch', 'search_knowledge_graph'})
            result = client.post('/mcp', json={'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {
                'name': 'search', 'arguments': {'query': 'cysteine'}}}).json()
            payload = result['result'].get('structuredContent') or json.loads(result['result']['content'][0]['text'])
            self.assertEqual(payload['results'][0]['id'], '880')
            denied = client.post('/mcp', json={'jsonrpc': '2.0', 'id': 4, 'method': 'tools/call', 'params': {
                'name': 'run_sql', 'arguments': {'query': 'DELETE FROM sources'}}}).json()
            self.assertTrue(denied['result']['isError'])

    def test_discovery_and_anonymous_calls_never_reach_backend(self):
        backend = SimpleNamespace(search=lambda _: self.fail('Anonymous request reached scientific data'))
        verifier = SimpleNamespace(verify_token=AsyncMock(return_value=None))
        with TestClient(create_hosted_app(SETTINGS, backend, verifier), base_url='https://mcp.example.org') as client:
            result = client.post('/mcp', json={'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'})
            self.assertEqual(result.status_code, 401)
            self.assertIn('resource_metadata=', result.headers['www-authenticate'])
            metadata = client.get('/.well-known/oauth-protected-resource/mcp').json()
            self.assertEqual(metadata['resource'], SETTINGS.resource)
            self.assertEqual(metadata['authorization_servers'], [SETTINGS.issuer])
            self.assertNotIn('invited', client.get('/api/config').text)
            self.assertEqual(client.get('/healthz').status_code, 200)
            page = client.get('/')
            self.assertIn("frame-ancestors 'none'", page.headers['content-security-policy'])
            self.assertEqual(client.get('/', headers={'host': 'evil.example.org'}).status_code, 400)

    def test_ui_invitation_is_not_an_authorization_token(self):
        verifier = SimpleNamespace(verify_token=AsyncMock(return_value=None))
        with TestClient(create_hosted_app(SETTINGS, SimpleNamespace(), verifier), base_url='https://mcp.example.org') as client:
            self.assertEqual(client.post('/api/invitation', json={'email': 'invited@example.org'}).status_code, 403)
            headers = {'Origin': 'https://mcp.example.org'}
            self.assertTrue(client.post('/api/invitation', json={'email': 'invited@example.org'}, headers=headers).json()['invited'])
            self.assertFalse(client.post('/api/invitation', json={'email': 'outsider@example.org'}, headers=headers).json()['invited'])
            self.assertEqual(client.post('/mcp', headers={'Authorization': 'Bearer fake'}, json={}).status_code, 401)

    def test_hosted_startup_requires_configuration(self):
        with patch.dict('os.environ', {}, clear=True), self.assertRaises(ValueError):
            Settings.from_env()


if __name__ == '__main__':
    unittest.main()
