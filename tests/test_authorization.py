"""Tests for scope-based tool authorization."""

import unittest
from unittest.mock import patch

from core.authorization import require_scope
from tests.helpers import make_settings


class ScopeAuthorizationTests(unittest.TestCase):
    def test_stdio_mode_does_not_require_http_identity(self):
        require_scope(make_settings(), "glpi:read")

    @patch("core.authorization.get_access_token", return_value=None)
    def test_rejects_missing_authenticated_context(self, get_token):
        settings = make_settings(mcp_auth_enabled=True)
        with self.assertRaisesRegex(PermissionError, "authenticated"):
            require_scope(settings, "glpi:read")

    @patch("core.authorization.get_access_token")
    def test_rejects_missing_scope(self, get_token):
        get_token.return_value.scopes = ["glpi:read"]
        settings = make_settings(mcp_auth_enabled=True)
        with self.assertRaisesRegex(PermissionError, "glpi:write"):
            require_scope(settings, "glpi:write")

    @patch("core.authorization.get_access_token")
    def test_accepts_required_scope(self, get_token):
        get_token.return_value.scopes = ["glpi:read", "glpi:write"]
        require_scope(make_settings(mcp_auth_enabled=True), "glpi:write")


if __name__ == "__main__":
    unittest.main()
