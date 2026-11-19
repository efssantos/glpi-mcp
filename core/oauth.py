"""OIDC bearer-token verification for remote MCP access."""

import asyncio
from typing import Any

import jwt
from jwt import PyJWKClient

from mcp.server.auth.provider import AccessToken, TokenVerifier

from core.config import Settings


class OIDCTokenVerifier(TokenVerifier):
    """Verify signed access tokens using an OIDC provider's published JWKS."""

    def __init__(self, settings: Settings) -> None:
        if not all((settings.oidc_issuer_url, settings.oidc_jwks_url, settings.oidc_audience)):
            raise ValueError("OIDC issuer, JWKS URL, and audience must be configured.")
        self.issuer = settings.oidc_issuer_url
        self.audience = settings.oidc_audience
        self.resource = settings.mcp_public_url
        self.jwks = PyJWKClient(settings.oidc_jwks_url, cache_keys=True, timeout=5)

    def _decode(self, token: str) -> dict[str, Any]:
        signing_key = self.jwks.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience=self.audience,
            issuer=self.issuer,
            options={"require": ["exp", "iss", "aud"]},
        )

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            claims = await asyncio.to_thread(self._decode, token)
        except (jwt.PyJWTError, OSError, ValueError, KeyError):
            return None

        raw_scopes = claims.get("scope", claims.get("scp", []))
        if isinstance(raw_scopes, str):
            scopes = raw_scopes.split()
        elif isinstance(raw_scopes, list) and all(isinstance(item, str) for item in raw_scopes):
            scopes = raw_scopes
        else:
            return None

        client_id = claims.get("client_id") or claims.get("azp") or claims.get("sub")
        if not isinstance(client_id, str) or not client_id:
            return None

        return AccessToken(
            token=token,
            client_id=client_id,
            scopes=scopes,
            expires_at=int(claims["exp"]),
            resource=self.resource,
        )


def build_authentication(settings: Settings):
    """Build the MCP resource-server authentication components."""
    if not settings.mcp_auth_enabled:
        return None, None

    from mcp.server.auth.settings import AuthSettings

    auth = AuthSettings(
        issuer_url=settings.oidc_issuer_url,
        resource_server_url=settings.mcp_public_url,
        required_scopes=[settings.mcp_read_scope],
    )
    return auth, OIDCTokenVerifier(settings)
