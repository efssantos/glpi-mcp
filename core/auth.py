"""Common environment validation."""

from .config import Settings
from .errors import ConfigurationError


def validate_glpi_settings(settings: Settings) -> None:
    if not settings.glpi_url:
        raise ConfigurationError("Set GLPI_URL to the GLPI server URL.")
    if not (settings.glpi_user_token or (settings.glpi_username and settings.glpi_password)):
        raise ConfigurationError("Set GLPI_USER_TOKEN or both GLPI_USERNAME and GLPI_PASSWORD.")
