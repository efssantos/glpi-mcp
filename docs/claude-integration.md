# Connect Claude to a remote GLPI-MCP server

This guide connects Claude to a GLPI-MCP instance deployed on a VPS. The server must already be reachable through a valid HTTPS certificate and configured with an OIDC authorization server. See [VPS deployment](deployment.md) first.

## Before connecting

Have the following information ready:

- Public MCP endpoint, for example `https://mcp.example.com/mcp`.
- OIDC issuer URL configured in `OIDC_ISSUER_URL`.
- A client registration in the identity provider, or an authorization server that supports the registration flow required by the Claude connector.
- Access-token audience matching `OIDC_AUDIENCE`.
- The scopes the user should receive: `glpi:read` for read-only access and `glpi:write` for ticket changes.

The access token must be a signed JWT access token (not an ID token) containing the configured issuer, audience, expiry, and scope claims. The MCP service verifies its signature using the configured JWKS endpoint.

## Add the remote connector

1. Open Claude's connector/custom integration settings for the account or workspace.
2. Add a remote MCP connector using the HTTPS endpoint shown above.
3. Select the OAuth authentication flow when prompted.
4. Complete the identity-provider sign-in and consent flow.
5. Grant only the scopes required for the user's tasks.
6. Save the connector and verify that the GLPI tools are listed in the conversation.

The exact labels and availability of connector settings depend on the Claude product, plan, and workspace policy. If the connector cannot complete OAuth discovery or registration, verify that the configured authorization server publishes standard OAuth metadata and supports the client-registration method expected by Claude.

## Scope model

| Scope | Permitted tools |
|---|---|
| `glpi:read` | `glpi_search`, `glpi_get_item` |
| `glpi:write` | `glpi_create_ticket`, `glpi_update_ticket` (also requires `glpi:read`) |

The MCP resource server requires `glpi:read` on every authenticated token. Write operations additionally require `glpi:write`. GLPI's own account permissions remain in force, so OAuth scopes do not grant permissions that the configured GLPI account does not have.

## Troubleshooting

- **OAuth discovery fails:** verify that the issuer URL is correct and that its authorization-server metadata is publicly reachable over HTTPS.
- **Token rejected:** check the JWT signature algorithm, issuer, audience, expiration, and JWKS URL. Confirm that the client obtained an access token rather than an ID token.
- **Read tools work but ticket changes fail:** request the `glpi:write` scope and confirm that the GLPI integration account can create or update tickets.
- **TLS error:** check DNS, firewall rules for ports 80/443, and Caddy logs.
- **Tools are unavailable:** check `docker compose logs glpi-mcp caddy` and confirm the connector uses the exact `/mcp` endpoint.

## Local Claude Desktop

For a Claude Desktop process running on the same computer as GLPI-MCP, keep using the local `stdio` configuration in the main README. The remote OAuth deployment is intended for clients that connect over HTTPS; it does not replace or disable `stdio`.
