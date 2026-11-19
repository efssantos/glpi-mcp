"""GLPI MCP tools."""

from typing import Any

from core.config import Settings
from core.auth import validate_glpi_settings
from .client import GLPIClient


UPDATEABLE_TICKET_FIELDS = {
    "name", "content", "urgency", "impact", "priority", "status",
    "itilcategories_id", "entities_id", "requesttypes_id", "locations_id",
}
FIELD_RANGES = {
    "urgency": (1, 5),
    "impact": (1, 5),
    "priority": (1, 6),
    "status": (1, 6),
}
REFERENCE_FIELDS = {"itilcategories_id", "entities_id", "requesttypes_id", "locations_id"}


def _positive_id(value: int | None, field_name: str) -> None:
    if value is not None and (
        not isinstance(value, int) or isinstance(value, bool) or value < 1
    ):
        raise ValueError(f"{field_name} must be a positive integer.")


def _validate_ticket_fields(fields: dict[str, Any], *, allow_partial: bool) -> None:
    if not isinstance(fields, dict) or not fields:
        raise ValueError("Provide at least one ticket field.")
    unknown = set(fields) - UPDATEABLE_TICKET_FIELDS
    if unknown:
        raise ValueError(f"Unsupported ticket field(s): {', '.join(sorted(unknown))}")

    for field_name in ("name", "content"):
        if field_name in fields:
            value = fields[field_name]
            maximum = 255 if field_name == "name" else 10000
            if not isinstance(value, str) or not value.strip() or len(value) > maximum:
                raise ValueError(f"{field_name} must be non-empty text with at most {maximum} characters.")

    for field_name, (minimum, maximum) in FIELD_RANGES.items():
        if field_name in fields:
            value = fields[field_name]
            if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
                raise ValueError(f"{field_name} must be an integer between {minimum} and {maximum}.")

    for field_name in REFERENCE_FIELDS:
        if field_name in fields:
            _positive_id(fields[field_name], field_name)


def register_glpi_tools(mcp: Any, settings: Settings) -> None:
    """Register read and ticket mutation tools on a FastMCP-compatible server."""

    @mcp.tool()
    def glpi_search(itemtype: str, criteria: str = "", limit: int = 50) -> object:
        """Search GLPI items using indexed criteria fields; results are limited to 100."""
        validate_glpi_settings(settings)
        if not isinstance(itemtype, str) or not itemtype.strip() or len(itemtype) > 100:
            raise ValueError("itemtype must be non-empty text with at most 100 characters.")
        client = GLPIClient(settings)
        try:
            return client.search(itemtype, criteria=criteria, limit=limit)
        finally:
            client.close()

    @mcp.tool()
    def glpi_get_item(itemtype: str, item_id: int) -> object:
        """Get a GLPI item by type and numeric ID."""
        validate_glpi_settings(settings)
        if not isinstance(itemtype, str) or not itemtype.strip() or len(itemtype) > 100:
            raise ValueError("itemtype must be non-empty text with at most 100 characters.")
        _positive_id(item_id, "item_id")
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
        _validate_ticket_fields(fields, allow_partial=False)
        client = GLPIClient(settings)
        try:
            return client.create("Ticket", fields)
        finally:
            client.close()

    @mcp.tool()
    def glpi_update_ticket(ticket_id: int, fields: dict[str, Any]) -> object:
        """Update an allowlisted set of fields on an existing GLPI ticket."""
        validate_glpi_settings(settings)
        _positive_id(ticket_id, "ticket_id")
        if "id" in fields:
            raise ValueError("The ticket ID is supplied separately; omit id from fields.")
        _validate_ticket_fields(fields, allow_partial=True)
        client = GLPIClient(settings)
        try:
            return client.update("Ticket", ticket_id, fields)
        finally:
            client.close()
