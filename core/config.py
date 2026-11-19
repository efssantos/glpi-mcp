"""Environment based configuration for the MCP server."""

from dataclasses import dataclass
import math
import os
from urllib.parse import urlsplit


def _read_bool(name: str, default: str = "false") -> bool:
    value = os.getenv(name, default).strip().lower()
    if value in {"1", "true", "yes"}:
        return True
    if value in {"0", "false", "no"}:
        return False
    raise ValueError(f"{name} must be a boolean value.")


def _validate_https_url(value: str, name: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError(f"{name} must be an absolute HTTPS URL without credentials, query, or fragment.")
    return value


@dataclass(frozen=True)
class Settings:
    glpi_url: str
    glpi_app_token: str | None = None
    glpi_user_token: str | None = None
    glpi_username: str | None = None
    glpi_password: str | None = None
    glpi_api_path: str = "/apirest.php"
    request_timeout: float = 30.0
    verify_tls: bool = True
    mcp_transport: str = "stdio"
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8000
    mcp_proxy_mode: bool = False
    mcp_auth_enabled: bool = False
    mcp_public_url: str | None = None
    oidc_issuer_url: str | None = None
    oidc_jwks_url: str | None = None
    oidc_audience: str | None = None
    mcp_read_scope: str = "glpi:read"
    mcp_write_scope: str = "glpi:write"

    @classmethod
    def from_env(cls) -> "Settings":
        url = os.getenv("GLPI_URL", "").strip().rstrip("/")
        try:
            timeout = float(os.getenv("GLPI_TIMEOUT", "30"))
            port = int(os.getenv("MCP_PORT", "8000"))
        except ValueError as exc:
            raise ValueError("GLPI_TIMEOUT and MCP_PORT must be valid numeric values.") from exc
        transport = os.getenv("MCP_TRANSPORT", "stdio").strip().lower()
        host = os.getenv("MCP_HOST", "127.0.0.1").strip()
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("GLPI_TIMEOUT must be a finite number greater than zero.")
        if url:
            parsed_url = urlsplit(url)
            if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
                raise ValueError("GLPI_URL must be an absolute HTTP or HTTPS URL.")
            if parsed_url.username or parsed_url.password:
                raise ValueError("Do not embed credentials in GLPI_URL; use the token or credential environment variables.")
        if not 1 <= port <= 65535:
            raise ValueError("MCP_PORT must be between 1 and 65535.")
        if transport not in {"stdio", "streamable-http"}:
            raise ValueError("MCP_TRANSPORT must be 'stdio' or 'streamable-http'.")
        if not host:
            raise ValueError("MCP_HOST must not be empty.")

        proxy_mode = _read_bool("MCP_PROXY_MODE")
        auth_enabled = _read_bool("MCP_AUTH_ENABLED")
        public_url = os.getenv("MCP_PUBLIC_URL", "").strip()
        issuer_url = os.getenv("OIDC_ISSUER_URL", "").strip()
        jwks_url = os.getenv("OIDC_JWKS_URL", "").strip()
        audience = os.getenv("OIDC_AUDIENCE", "").strip()
        read_scope = os.getenv("MCP_READ_SCOPE", "glpi:read").strip()
        write_scope = os.getenv("MCP_WRITE_SCOPE", "glpi:write").strip()
        if auth_enabled:
            if transport != "streamable-http":
                raise ValueError("MCP_AUTH_ENABLED requires MCP_TRANSPORT=streamable-http.")
            if not all((public_url, issuer_url, jwks_url, audience, read_scope, write_scope)):
                raise ValueError("Remote authentication requires MCP_PUBLIC_URL, OIDC_ISSUER_URL, OIDC_JWKS_URL, OIDC_AUDIENCE, and both MCP scopes.")
            public_url = _validate_https_url(public_url, "MCP_PUBLIC_URL")
            issuer_url = _validate_https_url(issuer_url, "OIDC_ISSUER_URL")
            jwks_url = _validate_https_url(jwks_url, "OIDC_JWKS_URL")
        if transport == "streamable-http" and host not in {"127.0.0.1", "localhost", "::1"}:
            if not proxy_mode:
                raise ValueError("Non-loopback HTTP binding requires MCP_PROXY_MODE=true and a private network behind an authenticated reverse proxy.")
            if not auth_enabled:
                raise ValueError("Non-loopback HTTP binding requires MCP_AUTH_ENABLED=true.")

        return cls(
            glpi_url=url,
            glpi_app_token=os.getenv("GLPI_APP_TOKEN") or None,
            glpi_user_token=os.getenv("GLPI_USER_TOKEN") or None,
            glpi_username=os.getenv("GLPI_USERNAME") or None,
            glpi_password=os.getenv("GLPI_PASSWORD") or None,
            glpi_api_path="/" + os.getenv("GLPI_API_PATH", "apirest.php").strip("/"),
            request_timeout=timeout,
            verify_tls=os.getenv("GLPI_VERIFY_TLS", "true").strip().lower() not in {"0", "false", "no"},
            mcp_transport=transport,
            mcp_host=host,
            mcp_port=port,
            mcp_proxy_mode=proxy_mode,
            mcp_auth_enabled=auth_enabled,
            mcp_public_url=public_url or None,
            oidc_issuer_url=issuer_url or None,
            oidc_jwks_url=jwks_url or None,
            oidc_audience=audience or None,
            mcp_read_scope=read_scope,
            mcp_write_scope=write_scope,
        )
