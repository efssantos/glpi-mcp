"""Tests for MCP tool registration and behavior."""

import unittest
from unittest.mock import MagicMock, patch

from core.errors import ConfigurationError
from integrations.glpi.tools import register_glpi_tools
from tests.helpers import make_settings


class FakeMCP:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(function):
            self.tools[function.__name__] = function
            return function
        return decorator


class GLPIToolTests(unittest.TestCase):
    def setUp(self):
        self.mcp = FakeMCP()
        self.settings = make_settings()
        register_glpi_tools(self.mcp, self.settings)

    def test_registers_all_expected_tools(self):
        self.assertEqual(set(self.mcp.tools), {
            "glpi_search", "glpi_get_item", "glpi_create_ticket", "glpi_update_ticket"
        })

    @patch("integrations.glpi.tools.GLPIClient")
    def test_search_calls_client_and_closes_session(self, client_class):
        client = client_class.return_value
        client.search.return_value = [{"id": 1}]
        result = self.mcp.tools["glpi_search"]("Ticket", "", 10)
        self.assertEqual(result, [{"id": 1}])
        client.search.assert_called_once_with("Ticket", criteria="", limit=10)
        client.close.assert_called_once()

    @patch("integrations.glpi.tools.GLPIClient")
    def test_get_item_calls_client(self, client_class):
        client = client_class.return_value
        client.get.return_value = {"id": 4}
        self.assertEqual(self.mcp.tools["glpi_get_item"]("Ticket", 4), {"id": 4})
        client.get.assert_called_once_with("Ticket", 4)
        client.close.assert_called_once()

    @patch("integrations.glpi.tools.GLPIClient")
    def test_create_ticket_includes_optional_fields_only_when_provided(self, client_class):
        client = client_class.return_value
        self.mcp.tools["glpi_create_ticket"]("Title", "Description", urgency=2, entities_id=3)
        client.create.assert_called_once_with("Ticket", {
            "name": "Title", "content": "Description", "urgency": 2, "entities_id": 3
        })
        client.close.assert_called_once()

    @patch("integrations.glpi.tools.GLPIClient")
    def test_update_ticket_calls_client(self, client_class):
        client = client_class.return_value
        self.mcp.tools["glpi_update_ticket"](12, {"name": "Changed"})
        client.update.assert_called_once_with("Ticket", 12, {"name": "Changed"})
        client.close.assert_called_once()

    def test_update_ticket_rejects_empty_fields_and_id_override(self):
        update = self.mcp.tools["glpi_update_ticket"]
        with self.assertRaisesRegex(ValueError, "at least one"):
            update(12, {})
        with self.assertRaisesRegex(ValueError, "omit id"):
            update(12, {"id": 99})

    def test_tools_validate_settings_before_creating_client(self):
        invalid_mcp = FakeMCP()
        register_glpi_tools(invalid_mcp, make_settings(glpi_user_token=None, glpi_username=None, glpi_password=None))
        with patch("integrations.glpi.tools.GLPIClient") as client_class:
            with self.assertRaises(ConfigurationError):
                invalid_mcp.tools["glpi_search"]("Ticket")
            client_class.assert_not_called()


if __name__ == "__main__":
    unittest.main()
