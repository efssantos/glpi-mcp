"""Tests for OIDC access-token verification."""

import asyncio
import unittest
from unittest.mock import MagicMock, patch

import jwt

from core.oauth import OIDCTokenVerifier
from tests.helpers import make_settings


class OIDCTokenVerifierTests(unittest.TestCase):
    @patch("core.oauth.jwt.decode")
    @patch("core.oauth.PyJWKClient")
    def test_accepts_valid_signed_token_and_extracts_scopes(self, jwks_class, decode):
        signing_key = MagicMock()
        signing_key.key = "public-key"
        jwks_class.return_value.get_signing_key_from_jwt.return_value = signing_key
        decode.return_value = {
            "iss": "https://identity.example.test",
            "aud": "glpi-mcp",
            "sub": "user-123",
            "exp": 2000000000,
            "scope": "glpi:read glpi:write",
        }
        settings = make_settings(
            mcp_auth_enabled=True,
            mcp_public_url="https://mcp.example.test/mcp",
            oidc_issuer_url="https://identity.example.test",
            oidc_jwks_url="https://identity.example.test/certs",
            oidc_audience="glpi-mcp",
        )
        verifier = OIDCTokenVerifier(settings)
        result = asyncio.run(verifier.verify_token("signed-token"))
        self.assertEqual(result.client_id, "user-123")
        self.assertEqual(result.scopes, ["glpi:read", "glpi:write"])
        self.assertEqual(result.resource, "https://mcp.example.test/mcp")
        decode.assert_called_once()

    @patch("core.oauth.jwt.decode", side_effect=TypeError("malformed claims"))
    @patch("core.oauth.PyJWKClient")
    def test_rejects_malformed_claims(self, jwks_class, decode):
        jwks_class.return_value.get_signing_key_from_jwt.return_value.key = "public-key"
        settings = make_settings(
            mcp_auth_enabled=True,
            mcp_public_url="https://mcp.example.test/mcp",
            oidc_issuer_url="https://identity.example.test",
            oidc_jwks_url="https://identity.example.test/certs",
            oidc_audience="glpi-mcp",
        )
        self.assertIsNone(asyncio.run(OIDCTokenVerifier(settings).verify_token("malformed")))


    @patch("core.oauth.jwt.decode", side_effect=jwt.InvalidTokenError("invalid"))
    @patch("core.oauth.PyJWKClient")
    def test_rejects_invalid_token(self, jwks_class, decode):
        jwks_class.return_value.get_signing_key_from_jwt.return_value.key = "public-key"
        settings = make_settings(
            mcp_auth_enabled=True,
            mcp_public_url="https://mcp.example.test/mcp",
            oidc_issuer_url="https://identity.example.test",
            oidc_jwks_url="https://identity.example.test/certs",
            oidc_audience="glpi-mcp",
        )
        self.assertIsNone(asyncio.run(OIDCTokenVerifier(settings).verify_token("invalid")))


if __name__ == "__main__":
    unittest.main()
