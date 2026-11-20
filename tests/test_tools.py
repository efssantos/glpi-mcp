"""Tests for MCP tool registration and behavior."""

import unittest
from unittest.mock import MagicMock, patch

from core.errors import ConfigurationError, IntegrationError
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
    def test_primary_operation_error_is_not_masked_by_close_error(self, client_class):
        client = client_class.return_value
        client.search.side_effect = IntegrationError("search failed")
        client.close.side_effect = IntegrationError("close failed")
        with self.assertRaisesRegex(IntegrationError, "search failed"):
            self.mcp.tools["glpi_search"]("Ticket")
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

    def test_update_ticket_rejects_unapproved_fields_and_invalid_values(self):
        update = self.mcp.tools["glpi_update_ticket"]
        with self.assertRaisesRegex(ValueError, "Unsupported ticket field"):
            update(12, {"is_deleted": 1})
        with self.assertRaisesRegex(ValueError, "urgency must be an integer"):
            update(12, {"urgency": 9})
        with self.assertRaisesRegex(ValueError, "positive integer"):
            update(0, {"name": "Changed"})

    @patch("integrations.glpi.tools.GLPIClient")
    def test_create_ticket_rejects_invalid_urgency(self, client_class):
        with self.assertRaisesRegex(ValueError, "urgency must be an integer"):
            self.mcp.tools["glpi_create_ticket"]("Title", "Description", urgency=0)
        client_class.assert_not_called()

    def test_ticket_fields_validate_ranges_text_lengths_and_reference_ids(self):
        invalid_updates = (
            {"impact": 0},
            {"impact": 6},
            {"priority": 0},
            {"priority": 7},
            {"status": 0},
            {"status": 7},
            {"locations_id": 0},
            {"requesttypes_id": -1},
            {"entities_id": True},
            {"name": ""},
            {"name": "x" * 256},
            {"content": " "},
            {"content": "x" * 10001},
        )
        with patch("integrations.glpi.tools.GLPIClient") as client_class:
            update = self.mcp.tools["glpi_update_ticket"]
            for fields in invalid_updates:
                with self.subTest(fields=list(fields)), self.assertRaises(ValueError):
                    update(2, fields)
            client_class.assert_not_called()

    def test_create_ticket_rejects_invalid_text_and_reference_ids(self):
        invalid_inputs = (
            ("", "Description", 3, None),
            ("Title", " ", 3, None),
            ("x" * 256, "Description", 3, None),
            ("Title", "x" * 10001, 3, None),
            ("Title", "Description", 3, 0),
            ("Title", "Description", 3, True),
        )
        with patch("integrations.glpi.tools.GLPIClient") as client_class:
            create = self.mcp.tools["glpi_create_ticket"]
            for name, content, urgency, category in invalid_inputs:
                with self.subTest(name=name[:15]), self.assertRaises(ValueError):
                    create(name, content, urgency=urgency, itilcategories_id=category)
            client_class.assert_not_called()

    def test_tools_validate_settings_before_creating_client(self):
        invalid_mcp = FakeMCP()
        register_glpi_tools(invalid_mcp, make_settings(glpi_user_token=None, glpi_username=None, glpi_password=None))
        with patch("integrations.glpi.tools.GLPIClient") as client_class:
            with self.assertRaises(ConfigurationError):
                invalid_mcp.tools["glpi_search"]("Ticket")
            client_class.assert_not_called()

    def test_http_read_tools_reject_write_only_scope(self):
        settings = make_settings(mcp_auth_enabled=True)
        mcp = FakeMCP()
        register_glpi_tools(mcp, settings)
        token = MagicMock(scopes=["glpi:write"])
        with patch("integrations.glpi.tools.GLPIClient") as client_class, \
             patch("core.authorization.get_access_token", return_value=token):
            for name, args in (("glpi_search", ("Ticket",)), ("glpi_get_item", ("Ticket", 1))):
                with self.subTest(tool=name), self.assertRaisesRegex(PermissionError, "glpi:read"):
                    mcp.tools[name](*args)
            client_class.assert_not_called()

    def test_http_write_tools_reject_read_only_scope(self):
        settings = make_settings(mcp_auth_enabled=True)
        mcp = FakeMCP()
        register_glpi_tools(mcp, settings)
        token = MagicMock(scopes=["glpi:read"])
        with patch("integrations.glpi.tools.GLPIClient") as client_class, \
             patch("core.authorization.get_access_token", return_value=token):
            with self.assertRaisesRegex(PermissionError, "glpi:write"):
                mcp.tools["glpi_create_ticket"]("Title", "Description")
            with self.assertRaisesRegex(PermissionError, "glpi:write"):
                mcp.tools["glpi_update_ticket"](1, {"name": "Changed"})
            client_class.assert_not_called()

    def test_http_tools_reject_missing_token_before_glpi_calls(self):
        settings = make_settings(mcp_auth_enabled=True)
        mcp = FakeMCP()
        register_glpi_tools(mcp, settings)
        with patch("integrations.glpi.tools.GLPIClient") as client_class, \
             patch("core.authorization.get_access_token", return_value=None):
            calls = (
                ("glpi_search", ("Ticket",)),
                ("glpi_get_item", ("Ticket", 1)),
                ("glpi_create_ticket", ("Title", "Description")),
                ("glpi_update_ticket", (1, {"name": "Changed"})),
            )
            for name, args in calls:
                with self.subTest(tool=name), self.assertRaisesRegex(PermissionError, "authenticated"):
                    mcp.tools[name](*args)
            client_class.assert_not_called()


if __name__ == "__main__":
    unittest.main()
