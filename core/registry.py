"""MCP server factory."""

from mcp.server.auth.provider import TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP


def create_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    *,
    auth: AuthSettings | None = None,
    token_verifier: TokenVerifier | None = None,
) -> FastMCP:
    return FastMCP(
        "glpi-mcp",
        host=host,
        port=port,
        auth=auth,
        token_verifier=token_verifier,
    )
