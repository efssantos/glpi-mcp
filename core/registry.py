"""MCP tool registration."""

from mcp.server.fastmcp import FastMCP


def create_server() -> FastMCP:
    return FastMCP("glpi-mcp")
