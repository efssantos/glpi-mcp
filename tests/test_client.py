"""Tests for the GLPI REST client."""

import base64
import unittest
from unittest.mock import patch

from core.errors import ConfigurationError, IntegrationError
from integrations.glpi.client import GLPIClient
from tests.helpers import make_settings


class GLPIClientTests(unittest.TestCase):
    def setUp(self):
        self.settings = make_settings()
        self.client = GLPIClient(self.settings)

    def test_requires_glpi_url(self):
        with self.assertRaises(ConfigurationError):
            GLPIClient(make_settings(glpi_url=""))

    def test_builds_user_token_headers(self):
        self.assertEqual(self.client._headers()["Authorization"], "user_token user-token")
        self.assertEqual(self.client._headers()["App-Token"], "app-token")

    def test_builds_basic_auth_headers(self):
        client = GLPIClient(make_settings(glpi_user_token=None, glpi_username="alice", glpi_password="secret"))
        expected = base64.b64encode(b"alice:secret").decode("ascii")
        self.assertEqual(client._headers()["Authorization"], f"Basic {expected}")

    @patch("integrations.glpi.client.request_json")
    def test_starts_session_once_and_reuses_session_token(self, request_json):
        request_json.side_effect = [{"session_token": "session-123"}, {"id": 7}, {"id": 8}]
        self.assertEqual(self.client.request("Ticket/7"), {"id": 7})
        self.assertEqual(self.client.request("Ticket/8"), {"id": 8})
        self.assertEqual(request_json.call_count, 3)
        first_call = request_json.call_args_list[0]
        second_call = request_json.call_args_list[1]
        self.assertEqual(first_call.args[0], "https://glpi.example.test/apirest.php/initSession")
        self.assertNotIn("Session-Token", first_call.kwargs["headers"])
        self.assertEqual(second_call.kwargs["headers"]["Session-Token"], "session-123")

    @patch("integrations.glpi.client.request_json")
    def test_rejects_missing_session_token(self, request_json):
        request_json.return_value = {"error": "invalid credentials"}
        with self.assertRaisesRegex(IntegrationError, "session token"):
            self.client.start_session()

    @patch("integrations.glpi.client.request_json")
    def test_close_kills_session_and_clears_token(self, request_json):
        self.client._session_token = "session-123"
        self.client.close()
        request_json.assert_called_once()
        self.assertEqual(request_json.call_args.args[0], "https://glpi.example.test/apirest.php/killSession")
        self.assertIsNone(self.client._session_token)

    @patch("integrations.glpi.client.request_json")
    def test_close_clears_token_even_when_kill_session_fails(self, request_json):
        self.client._session_token = "session-123"
        request_json.side_effect = IntegrationError("network error")
        with self.assertRaises(IntegrationError):
            self.client.close()
        self.assertIsNone(self.client._session_token)

    @patch("integrations.glpi.client.request_json")
    def test_search_caps_limit_and_encodes_item_type(self, request_json):
        request_json.side_effect = [{"session_token": "s"}, []]
        self.client.search("IT Asset", limit=500, criteria="?is_deleted=0")
        call = request_json.call_args_list[1]
        self.assertEqual(call.args[0], "https://glpi.example.test/apirest.php/search/IT%20Asset?range=0-99&is_deleted=0")

    @patch("integrations.glpi.client.request_json")
    def test_create_and_update_wrap_fields_in_input(self, request_json):
        request_json.side_effect = [{"session_token": "s"}, {"id": 9}, {"id": 9}]
        self.client.create("Ticket", {"name": "Test"})
        self.client.update("Ticket", 9, {"name": "Updated"})
        create_call, update_call = request_json.call_args_list[1:]
        self.assertEqual(create_call.kwargs["body"], {"input": {"name": "Test"}})
        self.assertEqual(update_call.kwargs["body"], {"input": {"id": 9, "name": "Updated"}})
        self.assertEqual(update_call.kwargs["method"], "PUT")


if __name__ == "__main__":
    unittest.main()
