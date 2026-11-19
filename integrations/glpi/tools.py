"""GLPI MCP tools."""

from typing import Any

from core.config import Settings
from core.errors import ConfigurationError
from core.auth import validate_glpi_settings
from .client import GLPIClient


def register_glpi_tools(mcp: Any, settings: Settings) -> None:
    """Register read and ticket mutation tools on a FastMCP-compatible server."""

    @mcp.tool()
    def glpi_search(itemtype: str, criteria: str = "", limit: int = 50) -> object:
        """Search GLPI items by item type (for example Ticket, Computer, User).

        criteria is an optional legacy Search API parameter string, such as
        criteria[0][field]=1&criteria[0][searchtype]=contains&criteria[0][value]=printer.
        Results are capped at 100 items.
        """
        validate_glpi_settings(settings)
        client = GLPIClient(settings)
        try:
            return client.search(itemtype, criteria=criteria, limit=limit)
        finally:
            client.close()

    @mcp.tool()
    def glpi_get_item(itemtype: str, item_id: int) -> object:
        """Get a GLPI item by type and numeric ID."""
        validate_glpi_settings(settings)
        client = GLPIClient(settings)
        try:
            return client.get(itemtype, item_id)
        finally:
            client.close()

    @mcp.tool()
    def glpi_create_ticket(name: str, content: str, *, urgency: int = 3,
                           itilcategories_id: int | None = None,
                           entities_id: int | None = None) -> object:
        """Create a GLPI ticket. Uses the connected GLPI account's permissions."""
        validate_glpi_settings(settings)
        fields: dict[str, Any] = {"name": name, "content": content, "urgency": urgency}
        if itilcategories_id is not None:
            fields["itilcategories_id"] = itilcategories_id
        if entities_id is not None:
            fields["entities_id"] = entities_id
        client = GLPIClient(settings)
        try:
            return client.create("Ticket", fields)
        finally:
            client.close()

    @mcp.tool()
    def glpi_update_ticket(ticket_id: int, fields: dict[str, Any]) -> object:
        """Update fields on an existing GLPI ticket by ID."""
        validate_glpi_settings(settings)
        if not fields:
            raise ValueError("Provide at least one ticket field to update.")
        if "id" in fields:
            raise ValueError("The ticket ID is supplied separately; omit id from fields.")
        client = GLPIClient(settings)
        try:
            return client.update("Ticket", ticket_id, fields)
        finally:
            client.close()
