"""Errors presented safely to MCP clients."""


class IntegrationError(RuntimeError):
    """A remote integration request failed."""


class ConfigurationError(IntegrationError):
    """Required integration configuration is missing or invalid."""
