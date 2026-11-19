"""MCP server factory with HTTP transport protections."""

from urllib.parse import urlsplit

from mcp.server.auth.provider import TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings


def create_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    *,
    auth: AuthSettings | None = None,
    token_verifier: TokenVerifier | None = None,
) -> FastMCP:
    transport_security = None
    if auth is not None:
        public_url = urlsplit(str(auth.resource_server_url))
        transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[public_url.netloc],
            allowed_origins=[f"{public_url.scheme}://{public_url.netloc}"],
        )
    return FastMCP(
        "glpi-mcp",
        host=host,
        port=port,
        auth=auth,
        token_verifier=token_verifier,
        transport_security=transport_security,
    )
