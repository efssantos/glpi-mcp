"""Scope-based authorization for GLPI MCP tools."""

from mcp.server.auth.middleware.auth_context import get_access_token

from core.config import Settings


def require_scope(settings: Settings, scope: str) -> None:
    """Require a scope for authenticated HTTP requests; leave stdio unchanged."""
    if not settings.mcp_auth_enabled:
        return
    token = get_access_token()
    if token is None:
        raise PermissionError("An authenticated MCP access token is required.")
    if scope not in token.scopes:
        raise PermissionError(f"The access token is missing the required scope: {scope}.")
