"""Tests for GLPI credential validation."""

import unittest

from core.auth import validate_glpi_settings
from core.errors import ConfigurationError
from tests.helpers import make_settings


class AuthenticationValidationTests(unittest.TestCase):
    def test_accepts_user_token(self):
        validate_glpi_settings(make_settings(glpi_user_token="token", glpi_username=None, glpi_password=None))

    def test_accepts_username_and_password(self):
        validate_glpi_settings(make_settings(glpi_user_token=None, glpi_username="user", glpi_password="pass"))

    def test_requires_glpi_url(self):
        with self.assertRaisesRegex(ConfigurationError, "GLPI_URL"):
            validate_glpi_settings(make_settings(glpi_url=""))

    def test_requires_complete_authentication_pair(self):
        with self.assertRaisesRegex(ConfigurationError, "GLPI_USER_TOKEN"):
            validate_glpi_settings(make_settings(glpi_user_token=None, glpi_username="user", glpi_password=None))


if __name__ == "__main__":
    unittest.main()
