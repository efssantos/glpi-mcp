"""MCP server factory."""

from mcp.server.fastmcp import FastMCP


def create_server(host: str = "127.0.0.1", port: int = 8000) -> FastMCP:
    return FastMCP("glpi-mcp", host=host, port=port)
