"""GLPI MCP server entry point."""

from core.config import Settings
from core.registry import create_server
from integrations.glpi import register_glpi_tools


def main() -> None:
    settings = Settings.from_env()
    server = create_server()
    register_glpi_tools(server, settings)
    if settings.mcp_transport == "stdio":
        server.run()
    elif settings.mcp_transport == "streamable-http":
        server.run(transport="streamable-http", host=settings.mcp_host, port=settings.mcp_port)
    else:
        raise ValueError("MCP_TRANSPORT must be 'stdio' or 'streamable-http'.")


if __name__ == "__main__":
    main()
