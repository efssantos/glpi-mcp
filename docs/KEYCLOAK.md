# Configuração do Keycloak

Este guia configura o Keycloak como provedor de identidade (OIDC) para autenticar clientes MCP remotos no GLPI-MCP. O Keycloak emite tokens; o GLPI-MCP valida esses tokens e aplica autorização por escopos.

> Personalize domínios, usuários e credenciais para sua infraestrutura. Não compartilhe tokens, senhas ou client secrets.

## 1. Pré-requisitos

- Keycloak instalado e acessível por HTTPS.
- Um domínio dedicado para autenticação.
- Acesso administrativo ao Keycloak.
- GLPI-MCP configurado para autenticação OIDC.

URL de exemplo: `https://auth.exemplo.com.br`.

## 2. Criar um realm

1. Entre no console administrativo do Keycloak.
2. Abra o seletor de realms e selecione **Create realm**.
3. Defina o nome como `glpi-mcp`.
4. Salve e selecione o realm criado.

O issuer esperado será:

`https://auth.exemplo.com.br/realms/glpi-mcp`

## 3. Criar o client

1. No realm `glpi-mcp`, acesse **Clients** e clique em **Create client**.
2. Selecione **OpenID Connect**.
3. Defina o **Client ID** como `glpi-mcp`.
4. Configure o client como confidencial (Client authentication habilitada), quando aplicável ao fluxo utilizado.
5. Habilite **Standard flow** conforme o cliente MCP que será utilizado.
6. Mantenha **Direct access grants** e **Implicit flow** desabilitados, salvo se houver uma necessidade documentada e uma análise de segurança.
7. Salve as configurações.

Configure redirect URIs e web origins conforme o cliente MCP utilizado. Não use curingas em produção.

## 4. Criar scopes de autorização

Crie dois client scopes do tipo OpenID Connect:

- `glpi:read`
- `glpi:write`

Para cada scope:

1. Abra **Client scopes**.
2. Clique em **Create client scope**.
3. Defina o nome do scope.
4. Selecione o protocolo OpenID Connect.
5. Salve.

Associe os scopes ao client `glpi-mcp` conforme o fluxo de emissão de tokens e a necessidade de permissões. O servidor exige leitura para operações MCP e exige também escrita para operações de alteração.

## 5. Configurar a audience (aud)

O GLPI-MCP valida a audiência do access token. Configure um mapper para adicionar a audience `glpi-mcp`:

1. Em **Client scopes**, crie um scope dedicado, por exemplo `glpi-mcp-dedicated`.
2. Abra o scope e acesse **Mappers**.
3. Crie um mapper do tipo **Audience**.
4. Defina **Included Client Audience** como `glpi-mcp`.
5. Habilite **Add to access token**.
6. Desabilite **Add to ID token**.
7. Salve.
8. Associe o scope `glpi-mcp-dedicated` ao client `glpi-mcp` como Default client scope.

Confira se o access token inclui a audience `glpi-mcp`, que deve corresponder à variável `OIDC_AUDIENCE` do servidor.

## 6. Criar usuário de integração

1. Acesse **Users** no realm `glpi-mcp`.
2. Crie um usuário exclusivo para integração/testes.
3. Use um nome de exemplo como `mcp-client`.
4. Configure as credenciais em **Credentials**.
5. Use uma senha forte, única e armazenada com segurança.

Não reutilize credenciais pessoais e não inclua credenciais em commits, logs ou documentação.

## 7. URLs OIDC para o GLPI-MCP

Usando o domínio de exemplo `auth.exemplo.com.br`:

| Configuração | Valor de exemplo |
|---|---|
| Issuer | `https://auth.exemplo.com.br/realms/glpi-mcp` |
| JWKS | `https://auth.exemplo.com.br/realms/glpi-mcp/protocol/openid-connect/certs` |
| Audience | `glpi-mcp` |

O servidor consulta o endpoint JWKS para obter as chaves públicas e validar assinatura dos tokens. Também verifica issuer, audience e expiração.

## 8. Scopes esperados

| Scope | Permissão |
|---|---|
| `glpi:read` | Consultas e leitura de registros |
| `glpi:write` | Operações de escrita; também requer leitura |

Os scopes devem estar presentes no access token, na claim `scope` (string) ou `scp` (lista), conforme o token emitido.

## 9. Checklist de validação

- [ ] Realm `glpi-mcp` criado.
- [ ] Client `glpi-mcp` configurado.
- [ ] Fluxos habilitados/desabilitados conforme a configuração recomendada.
- [ ] Redirect URI configurado para o cliente MCP utilizado.
- [ ] Scopes `glpi:read` e `glpi:write` criados.
- [ ] Scopes associados ao client conforme fluxo de token.
- [ ] Mapper de audience adiciona `glpi-mcp` ao access token.
- [ ] Scope dedicado de audience associado.
- [ ] Usuário de integração criado.
- [ ] Issuer e JWKS URLs conferidos.
- [ ] Access token validado com audience e scopes esperados.

## 10. Próximo passo

Configure as variáveis OIDC no GLPI-MCP e o proxy HTTPS seguindo [Deployment](DEPLOYMENT.md).
