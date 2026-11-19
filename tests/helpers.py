"""Shared fixtures for the test suite."""

from core.config import Settings


def make_settings(**overrides):
    values = {
        "glpi_url": "https://glpi.example.test",
        "glpi_app_token": "app-token",
        "glpi_user_token": "user-token",
        "glpi_api_path": "/apirest.php",
        "request_timeout": 12.5,
        "verify_tls": True,
        "mcp_transport": "stdio",
        "mcp_host": "127.0.0.1",
        "mcp_port": 8000,
    }
    values.update(overrides)
    return Settings(**values)
