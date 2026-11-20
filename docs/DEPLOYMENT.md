# Implantação do GLPI-MCP em VPS

Este guia descreve uma implantação remota do GLPI-MCP com Docker Compose, HTTPS via Caddy e autenticação OIDC usando Keycloak. Os exemplos são genéricos; substitua os domínios, endereços e credenciais pelos seus valores.

## 1. Arquitetura de referência

- `mcp.exemplo.com.br`: endpoint MCP.
- `auth.exemplo.com.br`: serviço de identidade Keycloak.
- `glpi.exemplo.com.br`: GLPI, se o seu sistema utilizar esse hostname.

Caddy termina TLS e encaminha o tráfego ao serviço MCP. O Keycloak é o provedor OIDC e precisa estar acessível por HTTPS tanto para clientes quanto para GLPI-MCP. Consulte [KEYCLOAK.md](KEYCLOAK.md) para configurar realm, client, scopes e audience.

## 2. Requisitos

- VPS Linux suportada e atualizada.
- Docker Engine e Docker Compose plugin.
- Domínio e acesso ao DNS.
- Acesso administrativo à VPS e ao firewall do provedor.
- GLPI acessível por HTTPS e API REST legada habilitada.
- Keycloak acessível por HTTPS.
- Tokens/credenciais de uma conta técnica do GLPI com privilégios mínimos.

## 3. DNS

Crie registros DNS para apontar os nomes de serviço ao IP público da VPS. Exemplo de registro:

| Tipo | Nome | Destino |
|---|---|---|
| A | `mcp` | `IP_PUBLICO_DA_VPS` |
| A | `auth` | `IP_PUBLICO_DA_VPS` |

Se usar IPv6, publique registros AAAA apenas quando a VPS e o firewall estiverem corretamente configurados para IPv6. Aguarde a propagação e valide a resolução antes de iniciar o proxy.

## 4. Firewall e portas

Libere no firewall da VPS e no firewall de rede do provedor somente as portas necessárias:

| Porta | Protocolo | Uso |
|---|---|---|
| 22 | TCP | SSH (recomendado restringir por IP) |
| 80 | TCP | HTTP e desafio de emissão de certificado |
| 443 | TCP | HTTPS |
| 443 | UDP | HTTP/3, opcional |

Não publique a porta 8000 do GLPI-MCP. Não exponha portas de administração do Keycloak ou do banco de dados na Internet. Restrinja o SSH e mantenha o sistema atualizado.

## 5. Instalar Docker

Instale Docker Engine e o plugin Docker Compose conforme o guia oficial para a distribuição Linux da VPS. Depois valide:

```bash
docker --version
docker compose version
```

Configure o usuário de deploy com os privilégios necessários para administrar containers. Não execute containers com permissões ou volumes mais amplos do que o necessário.

## 6. Clonar o projeto e preparar ambiente

```bash
git clone https://github.com/efssantos/glpi-mcp.git
cd glpi-mcp
cp .env.example .env
```

Edite `.env`. Exemplo de valores para uma instalação remota:

```dotenv
GLPI_URL=https://glpi.exemplo.com.br
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

MCP_DOMAIN=mcp.exemplo.com.br
MCP_PUBLIC_URL=https://mcp.exemplo.com.br/mcp
OIDC_ISSUER_URL=https://auth.exemplo.com.br/realms/glpi-mcp
OIDC_JWKS_URL=https://auth.exemplo.com.br/realms/glpi-mcp/protocol/openid-connect/certs
OIDC_AUDIENCE=glpi-mcp
MCP_READ_SCOPE=glpi:read
MCP_WRITE_SCOPE=glpi:write
LOG_LEVEL=INFO
```

Não copie literalmente os placeholders. Use os valores do GLPI, Keycloak e domínio que você configurou. `GLPI_USER_TOKEN` pode ser substituído por `GLPI_USERNAME` e `GLPI_PASSWORD`, conforme suportado pelo arquivo de exemplo.

Proteja o arquivo de ambiente:

```bash
chmod 600 .env
```

Confirme que `.env` não está sendo rastreado pelo Git antes de continuar.

## 7. Keycloak

Siga [KEYCLOAK.md](KEYCLOAK.md) para:

- Criar o realm `glpi-mcp`.
- Criar/configurar o client `glpi-mcp`.
- Configurar o fluxo de autenticação adequado ao cliente MCP.
- Criar scopes `glpi:read` e `glpi:write`.
- Configurar o audience mapper `glpi-mcp`.
- Criar um usuário de integração para testes.
- Conferir issuer e JWKS.

Antes de subir o MCP, verifique se o issuer e JWKS estão acessíveis via HTTPS. Se o Keycloak estiver em outra rede/stack Docker, valide conectividade a partir do host e do container MCP. Não use endereços de rede internos que não sejam resolvíveis pelo serviço.

## 8. Caddy e HTTPS

O Caddyfile incluído na versão atual configura o host definido por `MCP_DOMAIN` e encaminha para `glpi-mcp:8000`. O DNS precisa apontar para a VPS e as portas 80/443 precisam estar liberadas para que o Caddy consiga emitir e renovar certificados.

Se o Keycloak estiver no mesmo Caddy, configure um site adicional para `auth.exemplo.com.br` e um upstream de Keycloak acessível pela rede Docker. Não adicione o upstream até confirmar o nome de serviço, a porta e a conectividade de rede da instalação do Keycloak. Evite publicar o console administrativo desnecessariamente.

## 9. Iniciar o GLPI-MCP

```bash
docker compose up -d --build
docker compose ps
```

Acompanhe os logs:

```bash
docker compose logs -f glpi-mcp caddy
```

Verifique se os serviços estão em execução e se o Caddy emitiu o certificado TLS. Endpoint esperado:

```
https://mcp.exemplo.com.br/mcp
```

## 10. Validar o endpoint e a autenticação

Primeiro, confira a resolução DNS e o certificado HTTPS. Depois teste o endpoint usando o cliente MCP compatível. O endpoint remoto deve exigir um access token válido.

Resultados esperados:
- Sem token: requisição protegida recusada.
- Token inválido, expirado ou com issuer/audience incorretos: recusado.
- Token válido sem scope necessário: ferramenta não autorizada.
- Token válido com `glpi:read`: consultas autorizadas.
- Token com `glpi:read` e `glpi:write`: operações de escrita autorizadas, sujeitas às permissões da conta GLPI.

Não compartilhe tokens em logs, capturas de tela ou comandos copiados para tickets.

## 11. Conectar o cliente MCP

Configure o cliente com o endpoint HTTPS `https://mcp.exemplo.com.br/mcp`. O cliente precisa suportar Streamable HTTP e o método de autenticação OAuth/OIDC esperado pelo provedor. Siga o fluxo de autenticação do cliente e confirme que as ferramentas são listadas.

As opções e os fluxos de OAuth variam entre clientes. Redirect URIs e registro de cliente devem seguir os requisitos do cliente que você está conectando; não use redirect URI aberto ou wildcard.

## 12. Operação e atualização

Atualizar código pela branch/release apropriada:

```bash
git pull
docker compose up -d --build
docker compose ps
```

Ver logs recentes:

```bash
docker compose logs --tail 100 glpi-mcp
docker compose logs --tail 100 caddy
```

Mantenha backups dos dados e configurações relevantes, tokens de integração protegidos, sistema operacional e imagens atualizados, e acompanhe alertas de expiração de certificados.

## 13. Checklist final

- [ ] DNS dos hosts MCP e identidade aponta para o destino correto.
- [ ] Firewall permite somente as portas necessárias.
- [ ] Docker e Compose estão instalados.
- [ ] `.env` foi preenchido e protegido.
- [ ] API REST legada do GLPI habilitada.
- [ ] Conta técnica possui privilégios mínimos.
- [ ] Realm, client, scopes e audience configurados no Keycloak.
- [ ] Issuer e JWKS URLs acessíveis.
- [ ] Container MCP e Caddy em execução.
- [ ] HTTPS válido para o host MCP.
- [ ] Porta 8000 não está publicada na Internet.
- [ ] Requisições sem token ou com token inválido são recusadas.
- [ ] Cliente MCP autentica e lista ferramentas.
- [ ] Operações de leitura e escrita testadas com permissões apropriadas.

## Referências

- [README](../README.md)
- [Arquitetura](ARCHITECTURE.md)
- [Keycloak](KEYCLOAK.md)
- [Segurança](SECURITY.md)
