# Configuração do Keycloak

Keycloak é implantado junto à stack principal pelo Docker Compose. Este documento cobre apenas a configuração do provedor OIDC para GLPI-MCP.

## 1. Pré-requisitos

- Stack iniciada com `docker compose up -d`.
- Domínio `auth` apontando para a VPS e HTTPS válido.
- Acesso ao console administrativo do Keycloak.

Não crie uma stack Docker separada para Keycloak ou PostgreSQL. Os serviços, redes e volumes já estão declarados no `compose.yaml`.

## 2. Console administrativo

Acesse `https://auth.example.com` e autentique com o usuário e senha bootstrap configurados por `KC_ADMIN_USERNAME` e `KC_ADMIN_PASSWORD` no arquivo `.env`.

Mantenha as credenciais bootstrap protegidas. Após a implantação inicial, siga o procedimento de administração do Keycloak para proteger, rotacionar ou substituir as credenciais administrativas.

## 3. Criar um realm

1. Abra o seletor de realms e escolha **Create realm**.
2. Defina o nome como `glpi-mcp`.
3. Salve e selecione o realm.

Issuer esperado:

`https://auth.example.com/realms/glpi-mcp`

## 4. Criar o client

1. Acesse **Clients** e clique em **Create client**.
2. Selecione **OpenID Connect**.
3. Defina Client ID como `glpi-mcp`.
4. Configure Client authentication conforme o fluxo de autenticação do cliente MCP.
5. Habilite **Standard flow** se o cliente usar Authorization Code Flow.
6. Mantenha **Direct access grants** e **Implicit flow** desabilitados, salvo necessidade documentada e análise de segurança.
7. Salve.

Configure redirect URIs e web origins conforme o cliente que utilizará o MCP. Evite wildcards.

## 5. Criar scopes

Crie client scopes OpenID Connect:

- `glpi:read`
- `glpi:write`

Associe-os ao client conforme o fluxo de emissão de tokens. A aplicação requer leitura para operações MCP e leitura mais escrita para operações de alteração.

## 6. Configurar audience

O GLPI-MCP valida a audiência do access token. Configure um mapper para adicionar a audience `glpi-mcp`:

1. Em **Client scopes**, crie um scope dedicado, como `glpi-mcp-dedicated`.
2. Abra **Mappers** e crie um mapper do tipo **Audience**.
3. Defina **Included Client Audience** como `glpi-mcp`.
4. Habilite **Add to access token**.
5. Desabilite **Add to ID token**.
6. Salve e associe o scope dedicado ao client como Default client scope, se esse for o comportamento esperado.

Confirme que o access token inclui a audience esperada.

## 7. Usuário de integração/teste

1. Abra **Users** no realm.
2. Crie um usuário exclusivo para testes, por exemplo `mcp-client`.
3. Configure uma senha forte e única.
4. Atribua apenas as permissões necessárias ao fluxo escolhido.

Não reutilize credenciais pessoais nem registre senhas, tokens ou client secrets.

## 8. Endpoints OIDC

Exemplo de configuração correspondente ao domínio de exemplo:

| Variável | Valor |
|---|---|
| `OIDC_ISSUER_URL` | `https://auth.example.com/realms/glpi-mcp` |
| `OIDC_JWKS_URL` | `https://auth.example.com/realms/glpi-mcp/protocol/openid-connect/certs` |
| `OIDC_AUDIENCE` | `glpi-mcp` |

Esses valores devem corresponder ao realm, hostname e audience configurados no Keycloak e ao `.env` do GLPI-MCP.

## 9. Checklist

- [ ] Keycloak iniciado pelo Compose principal.
- [ ] PostgreSQL saudável e privado.
- [ ] HTTPS válido no hostname de identidade.
- [ ] Realm criado.
- [ ] Client configurado para o fluxo do cliente MCP.
- [ ] Redirect URIs sem wildcard.
- [ ] Scopes de leitura e escrita criados e associados.
- [ ] Audience mapper configurado para access token.
- [ ] Issuer e JWKS acessíveis.
- [ ] Token validado pelo GLPI-MCP.

Consulte [DEPLOYMENT.md](DEPLOYMENT.md) para implantação e operação da stack.
