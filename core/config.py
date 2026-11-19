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

    @classmethod
    def from_env(cls) -> "Settings":
        url = os.getenv("GLPI_URL", "").strip().rstrip("/")
        return cls(
            glpi_url=url,
            glpi_app_token=os.getenv("GLPI_APP_TOKEN") or None,
            glpi_user_token=os.getenv("GLPI_USER_TOKEN") or None,
            glpi_username=os.getenv("GLPI_USERNAME") or None,
            glpi_password=os.getenv("GLPI_PASSWORD") or None,
            glpi_api_path="/" + os.getenv("GLPI_API_PATH", "apirest.php").strip("/"),
            request_timeout=float(os.getenv("GLPI_TIMEOUT", "30")),
            verify_tls=os.getenv("GLPI_VERIFY_TLS", "true").strip().lower() not in {"0", "false", "no"},
            mcp_transport=os.getenv("MCP_TRANSPORT", "stdio").strip().lower(),
            mcp_host=os.getenv("MCP_HOST", "127.0.0.1").strip(),
            mcp_port=int(os.getenv("MCP_PORT", "8000")),
        )
