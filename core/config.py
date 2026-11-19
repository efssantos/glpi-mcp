"""Environment based configuration for the MCP server."""

from dataclasses import dataclass
import os


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
        if timeout <= 0:
            raise ValueError("GLPI_TIMEOUT must be greater than zero.")
        if not 1 <= port <= 65535:
            raise ValueError("MCP_PORT must be between 1 and 65535.")
        if transport not in {"stdio", "streamable-http"}:
            raise ValueError("MCP_TRANSPORT must be 'stdio' or 'streamable-http'.")
        if not host:
            raise ValueError("MCP_HOST must not be empty.")
        proxy_mode = os.getenv("MCP_PROXY_MODE", "false").strip().lower() in {"1", "true", "yes"}
        if transport == "streamable-http" and host not in {"127.0.0.1", "localhost", "::1"} and not proxy_mode:
            raise ValueError(
                "Non-loopback HTTP binding requires MCP_PROXY_MODE=true and a private network behind an authenticated reverse proxy."
            )

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
        )
