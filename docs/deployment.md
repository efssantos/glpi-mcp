# Remote deployment on a VPS

This deployment publishes the MCP endpoint through Caddy with automatic HTTPS. The MCP container is not published directly to the host: only Caddy exposes ports 80 and 443.

## Requirements

- A Linux VPS with Docker Engine and Docker Compose v2.
- A DNS name such as `mcp.example.com` pointing to the VPS public IP.
- TCP ports 80 and 443 reachable from the internet (UDP 443 is optional and enables HTTP/3).
- A reachable OIDC/OAuth authorization server that issues signed JWT access tokens.
- A GLPI account dedicated to the integration, with least-privilege permissions.

## Configure the identity provider

The GLPI-MCP service acts as an OAuth 2.1 resource server. It does not host a login page or issue user tokens. Configure an external OIDC provider (for example, a self-hosted Keycloak realm) to:

1. Publish an HTTPS issuer URL and a JWKS endpoint.
2. Issue signed access tokens using RS256 or ES256.
3. Include `iss`, `aud`, `exp`, and a `scope` (or `scp`) claim.
4. Issue the audience configured for this MCP resource: `glpi-mcp` in the example.
5. Grant `glpi:read` for search and item lookup; grant `glpi:write` as well for ticket creation and updates.
6. Support the authorization-code flow with PKCE and the client-registration/discovery capabilities required by the MCP client.

Do not use ID tokens as bearer access tokens. Configure the MCP client and identity provider to obtain an access token whose audience is the GLPI-MCP resource.

## Configure the VPS

Clone the repository and create the environment file:

```bash
git clone https://github.com/efssantos/glpi-mcp.git
cd glpi-mcp
cp .env.example .env
```

Edit `.env` and configure at least:

```dotenv
GLPI_URL=https://glpi.example.com
GLPI_APP_TOKEN=your-glpi-app-token
GLPI_USER_TOKEN=your-glpi-user-token

MCP_DOMAIN=mcp.example.com
MCP_PUBLIC_URL=https://mcp.example.com/mcp
OIDC_ISSUER_URL=https://identity.example.com/realms/glpi
OIDC_JWKS_URL=https://identity.example.com/realms/glpi/protocol/openid-connect/certs
OIDC_AUDIENCE=glpi-mcp
MCP_READ_SCOPE=glpi:read
MCP_WRITE_SCOPE=glpi:write
```

Use the exact issuer and JWKS URLs published by your identity provider. Configure its access-token audience to match `OIDC_AUDIENCE`. Keep `.env` private and never commit it.

## Start the services

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f caddy glpi-mcp
```

Caddy obtains and renews the TLS certificate automatically after DNS and firewall prerequisites are met. Persistent Docker volumes retain Caddy's certificate and configuration data.

The public MCP endpoint is:

```text
https://mcp.example.com/mcp
```

The protected-resource metadata is published by the MCP SDK and points clients to the configured authorization-server issuer. Unauthenticated MCP requests are rejected with HTTP 401.

## Network model

- Caddy is the only service publishing host ports (80 and 443).
- The MCP service has no published host port.
- Caddy and MCP communicate over the private `backend` Docker network.
- MCP has a separate egress network to reach the GLPI API.
- The VPS firewall should allow inbound TCP 80/443 only (and UDP 443 if HTTP/3 is desired). Do not open port 8000.

## Operational checks

```bash
docker compose ps
docker compose logs --tail 100 glpi-mcp
docker compose logs --tail 100 caddy
docker compose restart
```

Verify that the endpoint presents a valid certificate and that the OIDC discovery/JWKS endpoints are reachable from the MCP container. Test both an unauthenticated request (must be rejected) and an authenticated request with the appropriate scope.

## Security notes

- Use a dedicated GLPI integration account and restrict its permissions.
- Rotate GLPI tokens and OIDC signing keys according to your organization's policy.
- Restrict write scopes to trusted users or clients.
- Back up the `caddy_data` volume and protect the `.env` file.
- Keep Docker, Caddy, the MCP image, and the identity provider updated.
- HTTPS encrypts traffic; OAuth token validation and per-tool scopes provide identity and authorization. Neither replaces least-privilege permissions in GLPI.
