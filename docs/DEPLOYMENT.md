# Implantação do GLPI-MCP em VPS

Este guia implanta GLPI-MCP, Keycloak, PostgreSQL e Caddy em uma única stack Docker Compose. Os domínios e segredos de exemplo são fictícios; substitua-os pelos valores da sua infraestrutura.

## 1. Arquitetura

- `mcp.example.com`: endpoint MCP.
- `auth.example.com`: provedor de identidade Keycloak.
- GLPI: sistema externo, acessado pela API REST legada.

O Caddy termina TLS e encaminha o domínio MCP para GLPI-MCP e o domínio de identidade para Keycloak. PostgreSQL fica em uma rede Docker interna e não possui portas publicadas.

## 2. Pré-requisitos

- VPS Linux atualizada.
- Docker Engine e Docker Compose v2.
- Domínios e acesso ao DNS.
- Firewall do host e provedor.
- GLPI com API REST legada habilitada.
- Credenciais de conta técnica GLPI com privilégio mínimo.

## 3. DNS e firewall

Crie registros DNS apontando para o IP público da VPS:

| Tipo | Host | Destino |
|---|---|---|
| A | `mcp` | IP público da VPS |
| A | `auth` | IP público da VPS |

Libere as portas necessárias:

| Porta | Protocolo | Uso |
|---|---|---|
| 22 | TCP | SSH (restrinja por IP) |
| 80 | TCP | HTTP e emissão de certificados |
| 443 | TCP | HTTPS |
| 443 | UDP | HTTP/3, opcional |

Não publique as portas 8000, 8080 ou 5432. Não crie regras públicas para MCP, Keycloak ou PostgreSQL. Se utilizar IPv6, configure firewall e registros AAAA adequadamente.

## 4. Instalar Docker

Instale Docker Engine e o plugin Compose conforme o guia oficial da sua distribuição. Verifique:

```bash
docker --version
docker compose version
```

## 5. Clonar e configurar o projeto

```bash
git clone https://github.com/efssantos/glpi-mcp.git
cd glpi-mcp
cp .env.example .env
```

Edite o `.env` e configure os dados do GLPI, domínios e credenciais. Exemplo:

```dotenv
GLPI_URL=https://glpi.example.com
GLPI_API_PATH=/apirest.php
GLPI_APP_TOKEN=SUBSTITUA_PELO_APP_TOKEN
GLPI_USER_TOKEN=SUBSTITUA_PELO_USER_TOKEN
GLPI_TIMEOUT=30
GLPI_VERIFY_TLS=true

MCP_TRANSPORT=streamable-http
MCP_HOST=0.0.0.0
MCP_PROXY_MODE=true
MCP_PORT=8000
MCP_AUTH_ENABLED=true

MCP_DOMAIN=mcp.example.com
KC_DOMAIN=auth.example.com
MCP_PUBLIC_URL=https://mcp.example.com/mcp
OIDC_ISSUER_URL=https://auth.example.com/realms/glpi-mcp
OIDC_JWKS_URL=https://auth.example.com/realms/glpi-mcp/protocol/openid-connect/certs
OIDC_AUDIENCE=glpi-mcp
MCP_READ_SCOPE=glpi:read
MCP_WRITE_SCOPE=glpi:write

KC_DB_PASSWORD=DEFINA_UMA_SENHA_FORTE
KC_ADMIN_USERNAME=DEFINA_USUARIO_ADMIN
KC_ADMIN_PASSWORD=DEFINA_SENHA_FORTE

LOG_LEVEL=INFO
```

Use senhas fortes, únicas e diferentes entre banco e administrador. Preencha os tokens GLPI. Proteja o arquivo e confirme que não será versionado:

```bash
chmod 600 .env
git status --short
```

Não use os valores de exemplo em produção.

## 6. Iniciar a stack

Todos os serviços são definidos no `compose.yaml`. Suba a stack:

```bash
docker compose config
docker compose up -d --build
docker compose ps
```

O Compose inicia PostgreSQL, aguarda seu healthcheck, inicia Keycloak, GLPI-MCP e Caddy. O Keycloak e o PostgreSQL usam volumes persistentes. O Caddy atende os dois domínios HTTPS.

Acompanhe os logs:

```bash
docker compose logs -f keycloak keycloak-db glpi-mcp caddy
```

## 7. Configurar Keycloak

Acesse o console administrativo em `https://auth.example.com` e entre usando o administrador bootstrap definido no `.env`. Configure realm, client, scopes e audience conforme [KEYCLOAK.md](KEYCLOAK.md).

O Keycloak já é provisionado pelo Compose. Não crie uma segunda stack nem outro container de Keycloak.

## 8. Validar DNS e HTTPS

Confirme DNS e certificados para ambos os hostnames:

- `https://mcp.example.com/mcp`
- `https://auth.example.com`

O Caddy emite e renova os certificados automaticamente quando DNS e conectividade nas portas 80/443 estão corretos. Confira os logs se algum certificado não for emitido.

## 9. Validar autenticação e ferramentas MCP

Use um cliente MCP compatível com Streamable HTTP e OAuth/OIDC. Valide:

- Sem token: requisição protegida é recusada.
- Token inválido, expirado, issuer ou audience incorretos: recusado.
- Token sem scope exigido: ferramenta não autorizada.
- Token válido com `glpi:read`: operações de consulta permitidas.
- Token válido com `glpi:read` e `glpi:write`: operações de escrita permitidas, respeitando as permissões GLPI.

Não compartilhe access tokens ou secrets em logs ou capturas de tela.

## 10. Operação, atualização e backup

Ver status e logs:

```bash
docker compose ps
docker compose logs --tail 100 keycloak
docker compose logs --tail 100 glpi-mcp
docker compose logs --tail 100 caddy
```

Faça backups regulares do volume `keycloak_db` e dos dados de configuração do Caddy (`caddy_data`). Guarde cópias em local seguro e teste a restauração. Backup do banco é essencial para preservar realms, clients, usuários e configurações.

Para atualizar, siga a branch ou release validada do projeto. Faça backup antes de atualizações e acompanhe a compatibilidade das imagens.

## 11. Checklist de implantação

- [ ] DNS MCP e auth apontam para a VPS.
- [ ] Firewall libera somente portas necessárias.
- [ ] Docker Engine e Compose instalados.
- [ ] `.env` preenchido e protegido.
- [ ] Tokens GLPI configurados e com privilégio mínimo.
- [ ] `docker compose config` válido.
- [ ] PostgreSQL saudável e sem porta publicada.
- [ ] Keycloak e GLPI-MCP em execução.
- [ ] Caddy em execução e certificados válidos para ambos os domínios.
- [ ] Porta 8000 e 8080 não publicadas.
- [ ] Realm, client, scopes e audience configurados.
- [ ] Testes de token e scopes realizados.
- [ ] Backup e restauração do banco planejados.

## Referências

- [README](../README.md)
- [Arquitetura](ARCHITECTURE.md)
- [Configuração do Keycloak](KEYCLOAK.md)
- [Segurança](SECURITY.md)
