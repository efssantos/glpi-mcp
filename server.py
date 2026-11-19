"""GLPI MCP server entry point."""

from core.config import Settings
from core.oauth import build_authentication
from core.registry import create_server
from integrations.glpi import register_glpi_tools


def main() -> None:
    settings = Settings.from_env()
    auth, token_verifier = build_authentication(settings)

    server = create_server(
        host=settings.mcp_host,
        port=settings.mcp_port,
        auth=auth,
        token_verifier=token_verifier,
    )

    register_glpi_tools(server, settings)

    if settings.mcp_transport == "stdio":
        server.run()
    elif settings.mcp_transport == "streamable-http":
        server.run(transport="streamable-http")
    else:
        raise ValueError("MCP_TRANSPORT must be 'stdio' or 'streamable-http'.")


if __name__ == "__main__":
    main()
