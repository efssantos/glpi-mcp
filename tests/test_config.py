"""Tests for environment-based settings."""

import unittest
from unittest.mock import patch

from core.config import Settings


class SettingsTests(unittest.TestCase):
    def test_reads_environment_and_normalizes_values(self):
        env = {
            "GLPI_URL": " https://glpi.example.test/ ",
            "GLPI_API_PATH": "/custom/api/",
            "GLPI_APP_TOKEN": "app",
            "GLPI_USER_TOKEN": "user",
            "GLPI_TIMEOUT": "15.5",
            "GLPI_VERIFY_TLS": "false",
            "MCP_TRANSPORT": "STREAMABLE-HTTP",
            "MCP_HOST": "127.0.0.1",
            "MCP_PORT": "9000",
        }
        with patch.dict("os.environ", env, clear=True):
            settings = Settings.from_env()
        self.assertEqual(settings.glpi_url, "https://glpi.example.test")
        self.assertEqual(settings.glpi_api_path, "/custom/api")
        self.assertEqual(settings.request_timeout, 15.5)
        self.assertFalse(settings.verify_tls)
        self.assertEqual(settings.mcp_transport, "streamable-http")
        self.assertEqual(settings.mcp_host, "127.0.0.1")
        self.assertEqual(settings.mcp_port, 9000)

    def test_uses_safe_defaults_when_optional_values_are_missing(self):
        with patch.dict("os.environ", {}, clear=True):
            settings = Settings.from_env()
        self.assertEqual(settings.glpi_url, "")
        self.assertEqual(settings.request_timeout, 30.0)
        self.assertTrue(settings.verify_tls)
        self.assertEqual(settings.mcp_transport, "stdio")
        self.assertEqual(settings.mcp_host, "127.0.0.1")
        self.assertEqual(settings.mcp_port, 8000)
        self.assertFalse(settings.mcp_auth_enabled)

    def test_requires_proxy_mode_for_non_loopback_http_binding(self):
        env = {"MCP_TRANSPORT": "streamable-http", "MCP_HOST": "0.0.0.0"}
        with patch.dict("os.environ", env, clear=True):
            with self.assertRaisesRegex(ValueError, "MCP_PROXY_MODE=true"):
                Settings.from_env()
        env.update({
            "MCP_PROXY_MODE": "true",
            "MCP_AUTH_ENABLED": "true",
            "MCP_PUBLIC_URL": "https://mcp.example.test/mcp",
            "OIDC_ISSUER_URL": "https://identity.example.test/realms/glpi",
            "OIDC_JWKS_URL": "https://identity.example.test/realms/glpi/certs",
            "OIDC_AUDIENCE": "glpi-mcp",
        })
        with patch.dict("os.environ", env, clear=True):
            settings = Settings.from_env()
        self.assertTrue(settings.mcp_proxy_mode)
        self.assertTrue(settings.mcp_auth_enabled)

    def test_rejects_non_loopback_http_without_authentication(self):
        env = {"MCP_TRANSPORT": "streamable-http", "MCP_HOST": "0.0.0.0", "MCP_PROXY_MODE": "true"}
        with patch.dict("os.environ", env, clear=True):
            with self.assertRaisesRegex(ValueError, "MCP_AUTH_ENABLED=true"):
                Settings.from_env()

    def test_requires_complete_oidc_configuration(self):
        env = {"MCP_TRANSPORT": "streamable-http", "MCP_AUTH_ENABLED": "true"}
        with patch.dict("os.environ", env, clear=True):
            with self.assertRaisesRegex(ValueError, "OIDC_ISSUER_URL"):
                Settings.from_env()

    def test_rejects_non_https_oidc_endpoints(self):
        env = {
            "MCP_TRANSPORT": "streamable-http",
            "MCP_AUTH_ENABLED": "true",
            "MCP_PUBLIC_URL": "https://mcp.example.test/mcp",
            "OIDC_ISSUER_URL": "http://identity.example.test",
            "OIDC_JWKS_URL": "https://identity.example.test/certs",
            "OIDC_AUDIENCE": "glpi-mcp",
        }
        with patch.dict("os.environ", env, clear=True):
            with self.assertRaisesRegex(ValueError, "HTTPS"):
                Settings.from_env()

    def test_rejects_invalid_timeout_and_port_ranges(self):
        for env in ({"GLPI_TIMEOUT": "0"}, {"MCP_PORT": "70000"}):
            with patch.dict("os.environ", env, clear=True):
                with self.assertRaises(ValueError):
                    Settings.from_env()

    def test_invalid_numeric_environment_values_raise_value_error(self):
        with patch.dict("os.environ", {"GLPI_TIMEOUT": "invalid"}, clear=True):
            with self.assertRaises(ValueError):
                Settings.from_env()

    def test_rejects_invalid_tls_boolean_values(self):
        with patch.dict("os.environ", {"GLPI_VERIFY_TLS": "maybe"}, clear=True):
            with self.assertRaisesRegex(ValueError, "GLPI_VERIFY_TLS must be a boolean"):
                Settings.from_env()

    def test_rejects_invalid_boolean_values(self):
        with patch.dict("os.environ", {"MCP_AUTH_ENABLED": "sometimes"}, clear=True):
            with self.assertRaisesRegex(ValueError, "boolean"):
                Settings.from_env()


if __name__ == "__main__":
    unittest.main()
