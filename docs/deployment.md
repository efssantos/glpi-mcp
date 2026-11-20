# Guia de instalação do GLPI-MCP em uma VPS

Este documento apresenta, passo a passo, como instalar e manter uma instância própria do GLPI-MCP em uma VPS Linux e conectá-la à sua instalação do GLPI para uso por clientes MCP remotos.

O resultado esperado é um endereço de acesso HTTPS público, protegido por OAuth/OIDC, sem expor a porta interna do servidor MCP.

## 1. Conhecer os componentes

A instalação utiliza quatro componentes:

| Componente | Responsabilidade |
|---|---|
| Cliente MCP (Claude ou outro) | Envia solicitações MCP e apresenta os resultados ao usuário. |
| Caddy | Recebe conexões públicas, gerencia certificados TLS automaticamente e encaminha o tráfego ao MCP. |
| GLPI-MCP | Implementa as ferramentas, valida tokens de acesso e chama a API REST do GLPI. |
| Provedor OAuth/OIDC | Autentica usuários e emite tokens de acesso JWT. Não faz parte do GLPI-MCP e deve ser configurado separadamente. |

Fluxo de uma consulta:

1. O usuário solicita uma ação no cliente MCP.
2. O cliente conecta-se a `https://SEU-DOMINIO/mcp`.
3. Caddy recebe a conexão HTTPS e encaminha a requisição pela rede privada Docker.
4. O GLPI-MCP valida o token de acesso: assinatura, emissor (`iss`), audiência (`aud`) e expiração (`exp`).
5. A ferramenta verifica os escopos exigidos.
6. O GLPI-MCP chama a API REST com a conta técnica configurada.
7. O GLPI aplica as permissões dessa conta e retorna os dados.
8. O resultado volta ao cliente MCP pelo mesmo caminho.

O GLPI-MCP não hospeda uma página de login, não cadastra usuários e não emite tokens. Ele é o servidor de recursos OAuth (servidor de recursos). O servidor de autorização/IdP é uma dependência externa.

## 2. Requisitos para começar

Você precisa de:

- VPS Linux com acesso administrativo (sudo).
- mecanismo Docker e Docker Compose v2.
- Domínio ou subdomínio sob seu controle, por exemplo `mcp.exemplo.com`.
- Acesso ao painel DNS do domínio.
- Instância GLPI acessível pela Internet ou pela rede privada da VPS.
- App-Token e User Token (ou usuário/senha) de uma conta técnica GLPI.
- Provedor OAuth/OIDC acessível por HTTPS, capaz de emitir JWT tokens de acesso assinados e publicar JWKS.
- Cliente MCP compatível com o transporte HTTP com transmissão contínua e com o fluxo OAuth esperado.

Use uma conta GLPI exclusiva para integração. Não utilize a conta pessoal de um administrador.

## 3. Preparar a VPS e o DNS

### 3.1 Instalar Docker

Instale mecanismo Docker e o plugin Docker Compose v2 seguindo a documentação oficial da distribuição ou do Docker. Confirme:

```bash
docker --version
docker compose version
```

O comando `docker compose version` deve funcionar sem hífen entre docker e compose.

### 3.2 Configurar DNS

No painel DNS do domínio, crie:

- Registro `A`: nome `mcp` apontando para o IPv4 público da VPS.
- Registro `AAAA`: somente se a VPS tiver IPv6 funcional e o firewall IPv6 estiver configurado corretamente.

Exemplo: `mcp.exemplo.com` → `203.0.113.10`.

Aguarde a propagação e confira:

```bash
dig +short mcp.exemplo.com A
dig +short mcp.exemplo.com AAAA
```

O endereço retornado deve corresponder à VPS. Se não usar IPv6, remova um registro AAAA incorreto; um AAAA apontando para outro servidor pode impedir a validação TLS.

### 3.3 Configurar firewall

Libere entrada TCP 80 e TCP 443 no firewall do sistema e no firewall/regras de rede do provedor da VPS.

Exemplo com UFW:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw status
```

UDP 443 é opcional para HTTP/3. O Compose atual publica essa porta; se não quiser HTTP/3, remova a linha `443:443/udp` de `compose.yaml`.

**Não libere a porta 8000.** Ela é usada somente entre Caddy e GLPI-MCP na rede Docker.

## 4. Configurar o provedor de identidade OAuth/OIDC

Esta etapa é obrigatória para o acesso remoto. O GLPI-MCP não substitui um provedor de identidade. Você pode usar um serviço de identidade gerenciado ou hospedar uma solução como Keycloak, desde que ela atenda aos requisitos abaixo.

Ajuste o provedor para:

1. Publicar metadados de autorização OAuth/OIDC por HTTPS.
2. Publicar um endereço de acesso JWKS HTTPS com as chaves públicas de assinatura.
3. Emitir **tokens de acesso JWT** assinados com RS256 ou ES256.
4. Incluir os declarações `iss`, `aud` e `exp`.
5. Incluir os escopos em `escopo` (texto separado por espaços) ou `scp` (lista de textos).
6. Incluir nos tokens a audiência destinada ao GLPI-MCP, igual ao valor configurado em `OIDC_AUDIENCE`.
7. Permitir que o cliente MCP obtenha um token de acesso para esse recurso. O fluxo de autorização, PKCE, descoberta de metadados e registro de cliente deve ser compatível com o cliente utilizado.

Escopos recomendados:

- `glpi:read`: pesquisa e consulta.
- `glpi:write`: criação e atualização de chamados. As ferramentas de escrita também exigem `glpi:read`.

O token precisa conter os dois escopos para executar operações de escrita. Não use um token de identificação como portador token. token de identificação identifica uma sessão/autenticação para o cliente; o GLPI-MCP espera um token de acesso destinado ao recurso.

### Valores que você precisa obter no provedor

Guarde estes valores para configurar o GLPI-MCP:

- URL exata do emissor (`iss`).
- URL HTTPS do endereço de acesso JWKS.
- Audiência que será incluída nos tokens de acesso.
- Mapeamento de escopos para usuários/clientes.
- Configuração de cliente/registro e URI de redirecionamento exigida pelo cliente MCP.

O GLPI-MCP valida tokens e escopos, mas não administra o cadastro de usuários ou a concessão de escopos. Faça essas tarefas no provedor de identidade.

> **Compatibilidade:** nem todo provedor OIDC ou cliente MCP implementa os mesmos mecanismos de descoberta e registro dinâmico. Antes de disponibilizar o serviço a usuários, valide o fluxo completo entre o cliente escolhido e seu provedor. A configuração de emissor/JWKS, isoladamente, não comprova que o login remoto funcionará.

## 5. Baixar e configurar o GLPI-MCP

Conecte-se à VPS por SSH e execute:

```bash
git clone https://github.com/efssantos/glpi-mcp.git
cd glpi-mcp
cp .env.example .env
```

Edite o arquivo:

```bash
nano .env
```

Preencha os valores. Exemplo:

```dotenv
# Instância GLPI e conta técnica
GLPI_URL=https://glpi.exemplo.com
GLPI_API_PATH=/apirest.php
GLPI_APP_TOKEN=COLOQUE_SEU_APP_TOKEN
GLPI_USER_TOKEN=COLOQUE_SEU_USER_TOKEN
GLPI_TIMEOUT=30
GLPI_VERIFY_TLS=true

# Domínio público do MCP
MCP_DOMAIN=mcp.exemplo.com
MCP_PUBLIC_URL=https://mcp.exemplo.com/mcp

# Provedor OAuth/OIDC
OIDC_ISSUER_URL=https://identity.exemplo.com/realms/glpi
OIDC_JWKS_URL=https://identity.exemplo.com/realms/glpi/protocol/openid-connect/certs
OIDC_AUDIENCE=glpi-mcp

# Escopos exigidos pelo servidor
MCP_READ_SCOPE=glpi:read
MCP_WRITE_SCOPE=glpi:write

LOG_LEVEL=INFO
```

Substitua todos os exemplos pelos endereços e credenciais reais. Os endereços do emissor e do serviço JWKS variam conforme o provedor; copie os valores exatos publicados por ele. O valor de `OIDC_AUDIENCE` deve coincidir com a audiência dos tokens de acesso.

O Compose define o modo remoto, ativa a autenticação e configura a escuta interna do servidor. Não é necessário alterar manualmente `MCP_TRANSPORT`, `MCP_HOST`, `MCP_PROXY_MODE` ou `MCP_AUTH_ENABLED` para essa implantação.

Proteja o arquivo:

```bash
chmod 600 .env
```

Nunca publique o arquivo em repositórios ou envie credenciais em chamados/registros.

## 6. Iniciar a aplicação

Na pasta do repositório:

```bash
docker compose up -d --build
```

Verifique o estado dos serviços:

```bash
docker compose ps
```

Acompanhe os registros:

```bash
docker compose registros -f caddy glpi-mcp
```

O Compose inicia dois contêineres:

- `caddy`: publica TCP 80/443 e gerencia HTTPS.
- `glpi-mcp`: executa o servidor MCP na porta 8000, sem publicar essa porta no host.

Quando DNS e firewall estiverem corretos, Caddy solicita automaticamente o certificado TLS e renova-o. O endereço de acesso público será:

```text
https://mcp.exemplo.com/mcp
```

## 7. Conhecer as portas utilizadas

| Porta | Protocolo | Direção | Finalidade |
|---|---|---|---|
| 80 | TCP | Entrada pública | Validação Let's Encrypt e redirecionamento HTTP para HTTPS. |
| 443 | TCP | Entrada pública | Conexões HTTPS dos clientes MCP. |
| 443 | UDP | Entrada pública, opcional | HTTP/3. |
| 8000 | TCP | Rede Docker privada | Proxy Caddy encaminha chamadas para o GLPI-MCP. Nunca publicar no host. |
| 443 | TCP | Saída | API GLPI e endereço de acessos HTTPS OIDC/JWKS. |
| 53 | UDP/TCP | Saída | Resolução DNS, conforme o resolvedor configurado. |

A VPS também precisa alcançar a instância GLPI e o provedor OIDC. Se algum desses serviços estiver em porta ou rede diferente, permita somente o destino necessário.

No modo local `stdio`, não há portas de entrada. A tabela acima descreve a implantação remota em VPS.

## 8. Verificar a instalação

### 8.1 Verificar os contêineres

```bash
docker compose ps
docker compose registros --tail 100 glpi-mcp
docker compose registros --tail 100 caddy
```

Ambos os serviços devem estar em execução. Corrija erros de configuração antes de seguir.

### 8.2 Verificar HTTPS

De um computador externo à VPS:

```bash
curl -I https://mcp.exemplo.com
```

Confirme que o domínio resolve para a VPS e que o certificado apresentado é válido. A resposta HTTP da raiz pode variar; o objetivo deste teste é verificar conectividade TLS. O endereço de acesso MCP é `/mcp`.

### 8.3 Verificar autenticação

Faça uma requisição ao endereço de acesso sem token. O acesso não autenticado deve ser recusado (HTTP 401 ou desafio de autenticação equivalente).

Depois, use o cliente MCP configurado para autenticar pelo provedor e obter um token de acesso correto. Um teste manual com um token deve usar um token de acesso JWT, com emissor, audiência, expiração e escopos válidos.

### 8.4 Verificar as ferramentas

Conecte o cliente MCP ao endereço:

```text
https://mcp.exemplo.com/mcp
```

Conclua a autenticação. Confirme que as ferramentas `glpi_search`, `glpi_get_item`, `glpi_create_ticket` e `glpi_update_ticket` aparecem. Comece com uma consulta de leitura. Só depois teste criação/atualização em um ambiente controlado.

## 9. Conceder acesso aos usuários

A autorização tem duas camadas independentes:

1. **OAuth/OIDC:** o token de acesso precisa conter os escopos requeridos pelo GLPI-MCP.
2. **GLPI:** a conta técnica configurada no servidor precisa ter permissão para a ação solicitada.

| Operação | Escopos do token | Permissão GLPI |
|---|---|---|
| Pesquisar ou consultar | `glpi:read` | Leitura do tipo de item correspondente. |
| Criar chamado | `glpi:read` + `glpi:write` | Criar chamados. |
| Atualizar chamado | `glpi:read` + `glpi:write` | Atualizar os campos permitidos. |

Como a integração usa uma conta técnica configurada no servidor, as operações dos clientes remotos são executadas com as permissões dessa conta no GLPI. Os escopos distinguem o que cada token pode solicitar, mas não transformam a conta técnica em usuários individuais do GLPI.

## 10. Operação e atualização

Ver status e registros:

```bash
docker compose ps
docker compose registros --tail 100 glpi-mcp caddy
```

Reiniciar:

```bash
docker compose restart
```

Atualizar o código da branch implantada:

```bash
git pull
docker compose up -d --build
```

Antes de atualizar em produção, leia as notas de versão e faça cópia de segurança de configurações e dados persistentes.

### Backups

Os volumes `caddy_data` e `caddy_config` guardam certificados e dados de configuração do Caddy. Faça cópia de segurança seguro desses volumes. Mantenha também uma cópia protegida do `.env`; ela contém credenciais e não deve ficar em cópia de segurança público.

## 11. Segurança da instalação

- Não exponha TCP 8000.
- Não desative a validação TLS do GLPI em produção.
- Restrinja os escopos de escrita aos usuários que realmente precisam deles.
- Proteja o acesso administrativo à VPS e mantenha o sistema atualizado.
- Rotacione tokens GLPI e chaves/segredos do provedor conforme a política adotada.
- Monitore registros e falhas de autenticação.
- Faça cópia de segurança e teste a restauração.
- Se o provedor OIDC ficar indisponível, novas validações de tokens podem falhar; planeje a disponibilidade dessa dependência.

## 12. Desinstalar a aplicação

Na pasta do projeto:

```bash
docker compose down
```

Para remover também os volumes persistentes (incluindo dados/certificados do Caddy):

```bash
docker compose down -v
```

O segundo comando é destrutivo. Execute-o somente se realmente quiser apagar os dados persistidos pelo Compose.
