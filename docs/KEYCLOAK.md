# Configuração do Keycloak

Este guia descreve uma implantação de Keycloak e a configuração OIDC usada para autenticar clientes MCP remotos no GLPI-MCP. O Keycloak emite tokens; o GLPI-MCP valida esses tokens e aplica autorização por escopos.

> Personalize domínios, usuários e credenciais para sua infraestrutura. Não compartilhe tokens, senhas ou client secrets.

## 1. Requisitos

- VPS Linux com Docker Engine e Docker Compose.
- Domínio de autenticação, por exemplo `auth.exemplo.com.br`.
- Proxy HTTPS (Caddy ou outro proxy reverso).
- Acesso administrativo ao Keycloak.

## 2. Implantar Keycloak com PostgreSQL

Crie um diretório para o stack de identidade, separado da aplicação:

```bash
mkdir -p ~/keycloak
cd ~/keycloak
```

Crie um arquivo `compose.yaml` com um banco PostgreSQL e Keycloak. Use versões fixadas e atualize-as de forma controlada:

```yaml
services:
  keycloak-db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: keycloak
      POSTGRES_USER: keycloak
      POSTGRES_PASSWORD: ${KC_DB_PASSWORD}
    volumes:
      - keycloak_db:/var/lib/postgresql/data
    networks:
      - keycloak-internal
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U keycloak -d keycloak"]
      interval: 10s
      timeout: 5s
      retries: 5

  keycloak:
    image: quay.io/keycloak/keycloak:26.4.2
    restart: unless-stopped
    command: start
    environment:
      KC_DB: postgres
      KC_DB_URL: jdbc:postgresql://keycloak-db:5432/keycloak
      KC_DB_USERNAME: keycloak
      KC_DB_PASSWORD: ${KC_DB_PASSWORD}
      KC_BOOTSTRAP_ADMIN_USERNAME: ${KC_ADMIN_USERNAME}
      KC_BOOTSTRAP_ADMIN_PASSWORD: ${KC_ADMIN_PASSWORD}
      KC_HTTP_ENABLED: "true"
      KC_HOSTNAME: https://auth.exemplo.com.br
      KC_PROXY_HEADERS: xforwarded
    depends_on:
      keycloak-db:
        condition: service_healthy
    networks:
      - keycloak-internal
      - proxy-network
    expose:
      - "8080"

volumes:
  keycloak_db:

networks:
  keycloak-internal:
    internal: true
  proxy-network:
    external: true
    name: REDE_DOCKER_COMPARTILHADA_COM_CADDY
```

Crie um arquivo `.env` nesse diretório para as variáveis administrativas e de banco:

```dotenv
KC_DB_PASSWORD=SUBSTITUA_POR_SENHA_FORTE
KC_ADMIN_USERNAME=SUBSTITUA_USUARIO_ADMIN
KC_ADMIN_PASSWORD=SUBSTITUA_POR_SENHA_FORTE
```

Proteja o arquivo:

```bash
chmod 600 .env
```

**Rede Docker:** o nome `REDE_DOCKER_COMPARTILHADA_COM_CADDY` é um placeholder. O Keycloak e o Caddy precisam compartilhar uma rede Docker para que o proxy consiga encaminhar ao upstream `keycloak:8080`. Crie ou conecte ambos à rede apropriada. Não publique a porta 8080 do Keycloak no host. A rede interna do banco não deve ser acessível pelo proxy.

Suba os serviços:

```bash
docker compose up -d
docker compose ps
docker compose logs -f keycloak
```

## 3. Configurar Caddy para o domínio de identidade

No Caddyfile do proxy que compartilha rede com o serviço Keycloak, adicione um site para `auth.exemplo.com.br`:

```caddy
auth.exemplo.com.br {
    encode zstd gzip
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        Referrer-Policy "no-referrer"
        -Server
    }
    reverse_proxy keycloak:8080
}
```

Confirme que o DNS `auth` aponta para o IP público da VPS e que TCP 80/443 estão liberados. Valide os logs do Caddy e o certificado TLS. Não exponha o console do Keycloak por uma porta adicional do host.

O hostname público deve coincidir com `KC_HOSTNAME`. O Keycloak deve reconhecer os cabeçalhos de proxy encaminhados pelo Caddy. Não configure proxy headers sem que o proxy confiável esteja corretamente configurado.

## 4. Criar um realm

1. Entre no console administrativo do Keycloak.
2. Abra o seletor de realms e selecione **Create realm**.
3. Defina o nome como `glpi-mcp`.
4. Salve e selecione o realm criado.

Issuer esperado:

`https://auth.exemplo.com.br/realms/glpi-mcp`

## 5. Criar o client

1. No realm `glpi-mcp`, acesse **Clients** e clique em **Create client**.
2. Selecione **OpenID Connect**.
3. Defina o **Client ID** como `glpi-mcp`.
4. Configure Client authentication conforme o fluxo adotado pelo cliente MCP.
5. Habilite **Standard flow** se o cliente usar authorization code flow.
6. Mantenha **Direct access grants** e **Implicit flow** desabilitados, salvo necessidade documentada e análise de segurança.
7. Salve as configurações.

Configure redirect URIs e web origins conforme o cliente MCP. Não use curingas em produção. O modo de autenticação do cliente MCP precisa ser compatível com os fluxos configurados no Keycloak.

## 6. Criar scopes de autorização

Crie dois client scopes do tipo OpenID Connect:

- `glpi:read`
- `glpi:write`

Para cada scope:

1. Abra **Client scopes**.
2. Clique em **Create client scope**.
3. Defina o nome do scope.
4. Selecione OpenID Connect.
5. Salve.

Associe os scopes ao client `glpi-mcp` conforme o fluxo de emissão de tokens e a necessidade de permissões. O servidor exige leitura para operações MCP e exige também escrita para operações de alteração.

## 7. Configurar a audience (aud)

O GLPI-MCP valida a audiência do access token. Configure um mapper para adicionar a audience `glpi-mcp`:

1. Em **Client scopes**, crie um scope dedicado, por exemplo `glpi-mcp-dedicated`.
2. Abra o scope e acesse **Mappers**.
3. Crie um mapper do tipo **Audience**.
4. Defina **Included Client Audience** como `glpi-mcp`.
5. Habilite **Add to access token**.
6. Desabilite **Add to ID token**.
7. Salve.
8. Associe o scope `glpi-mcp-dedicated` ao client `glpi-mcp` como Default client scope, se esse for o comportamento esperado do fluxo.

Confira se o access token inclui a audience `glpi-mcp`, que deve corresponder à variável `OIDC_AUDIENCE` do servidor.

## 8. Criar usuário de integração/teste

1. Acesse **Users** no realm `glpi-mcp`.
2. Crie um usuário exclusivo para integração/testes.
3. Use um nome de exemplo como `mcp-client`.
4. Configure credenciais em **Credentials**.
5. Use uma senha forte, única e armazenada com segurança.

Não reutilize credenciais pessoais e não inclua credenciais em commits, logs ou documentação.

## 9. URLs OIDC para o GLPI-MCP

Usando o domínio de exemplo `auth.exemplo.com.br`:

| Configuração | Valor de exemplo |
|---|---|
| Issuer | `https://auth.exemplo.com.br/realms/glpi-mcp` |
| JWKS | `https://auth.exemplo.com.br/realms/glpi-mcp/protocol/openid-connect/certs` |
| Audience | `glpi-mcp` |

O servidor consulta o endpoint JWKS para obter as chaves públicas e validar assinatura dos tokens. Também verifica issuer, audience e expiração.

## 10. Scopes esperados

| Scope | Permissão |
|---|---|
| `glpi:read` | Consultas e leitura de registros |
| `glpi:write` | Operações de escrita; também requer leitura |

Os scopes devem estar presentes no access token, na claim `scope` (string) ou `scp` (lista), conforme o token emitido.

## 11. Checklist

- [ ] PostgreSQL e Keycloak executando.
- [ ] Banco de dados sem porta pública.
- [ ] Keycloak publicado somente por proxy HTTPS.
- [ ] Realm `glpi-mcp` criado.
- [ ] Client `glpi-mcp` configurado.
- [ ] Fluxos configurados conforme cliente MCP.
- [ ] Redirect URI definido sem curingas.
- [ ] Scopes `glpi:read` e `glpi:write` criados.
- [ ] Scopes associados ao client conforme fluxo.
- [ ] Audience mapper adiciona `glpi-mcp` ao access token.
- [ ] Scope dedicado de audience associado.
- [ ] Usuário de integração criado.
- [ ] Issuer e JWKS URLs conferidos.
- [ ] Access token validado com audience e scopes esperados.

## 12. Próximo passo

Configure as variáveis OIDC no GLPI-MCP e o proxy HTTPS seguindo [Deployment](DEPLOYMENT.md).
