# GLPI MCP Server

Servidor [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) desenvolvido em Python para conectar clientes de IA à API REST legada do GLPI (\`apirest.php\`). Permite pesquisar registros, consultar itens e criar ou atualizar chamados usando as permissões da conta de integração configurada no GLPI.

O projeto oferece três formas de execução:

- **Local (\`stdio\`)**: o cliente MCP inicia o processo na própria máquina.
- **HTTP local**: o servidor fica disponível em \`http://127.0.0.1:8000/mcp\`, para desenvolvimento e clientes na mesma máquina.
- **HTTPS remoto**: implantação em VPS com Docker Compose, Caddy e autenticação OIDC.

> O projeto integra-se à API REST legada do GLPI. A API REST v2 não é o alvo desta implementação.

## Índice

- [Arquitetura e funcionamento](#arquitetura-e-funcionamento)
- [Pré-requisitos e preparação do GLPI](#pré-requisitos-e-preparação-do-glpi)
- [Configuração](#configuração)
- [Instalação local passo a passo](#instalação-local-passo-a-passo)
- [Executar em HTTP local](#executar-em-http-local)
- [Implantar em HTTPS na VPS](#implantar-em-https-na-vps)
- [Conectar clientes MCP](#conectar-clientes-mcp)
- [Ferramentas disponíveis](#ferramentas-disponíveis)
- [Desenvolvimento e contribuição](#desenvolvimento-e-contribuição)
- [Segurança](#segurança)
- [Solução de problemas](#solução-de-problemas)
- [Licença](#licença)

## Arquitetura e funcionamento

O GLPI-MCP atua como uma ponte: recebe chamadas de ferramentas pelo protocolo MCP, executa a operação correspondente na API do GLPI e devolve o resultado ao cliente.

\`\`\`text
Cliente MCP (Claude, etc.)
        |
        | stdio ou Streamable HTTP
        v
    GLPI-MCP
        |
        | API REST legada
        v
       GLPI
\`\`\`

No modo remoto, a arquitetura recomendada adiciona um proxy HTTPS e um provedor de identidade externo:

\`\`\`text
Cliente MCP
    |
 HTTPS :443
    |
  Caddy
    |
 rede Docker privada
    |
 GLPI-MCP ---- OIDC/JWKS
    |
 GLPI API
\`\`\`

### Estrutura do projeto

\`\`\`text
.
├── core/
│   ├── auth.py             # Validação da configuração de acesso ao GLPI
│   ├── authorization.py    # Autorização por escopos OAuth
│   ├── config.py           # Leitura e validação das variáveis de ambiente
│   ├── errors.py           # Exceções da aplicação e integração
│   ├── http.py             # Camada HTTP compartilhada
│   ├── oauth.py            # Validação de access tokens OIDC/JWT
│   └── registry.py         # Criação e configuração do servidor FastMCP
├── integrations/
│   └── glpi/
│       ├── client.py       # Cliente da API REST do GLPI
│       └── tools.py        # Ferramentas MCP expostas pelo GLPI
├── tests/                  # Testes automatizados com unittest e mocks
├── server.py               # Ponto de entrada da aplicação
├── compose.yaml            # Implantação remota com Caddy e HTTPS
├── Caddyfile               # Proxy reverso e TLS automático
├── Dockerfile
├── requirements.txt
└── .env.example
\`\`\`

### Fluxo de uma chamada

1. O cliente MCP invoca uma ferramenta registrada pelo servidor.
2. A ferramenta valida os parâmetros e, no modo remoto, verifica os escopos necessários.
3. O cliente GLPI inicia uma sessão na API usando o App-Token e o token ou as credenciais da conta técnica.
4. A operação é executada na API REST do GLPI.
5. A sessão da API é encerrada e o resultado é devolvido ao cliente MCP.

## Pré-requisitos e preparação do GLPI

Você precisará de:

- Python 3.11 ou superior para execução e desenvolvimento local.
- Docker Engine e Docker Compose v2 para implantação em contêiner/VPS.
- Acesso de rede à instância GLPI.
- API REST legada habilitada na instalação GLPI.
- App-Token, quando exigido pela configuração da API.
- User Token ou usuário e senha de uma conta técnica.

No GLPI:

1. Habilite a API REST legada nas configurações da sua instalação.
2. Gere o App-Token, se a configuração exigir esse token.
3. Gere um User Token para uma conta de integração ou prepare usuário e senha dedicados.
4. Conceda à conta apenas as permissões necessárias para consultar e gerenciar chamados.

Use a URL base do GLPI, por exemplo \`https://glpi.exemplo.com\`. Não acrescente \`/apirest.php\` em \`GLPI_URL\`; o caminho é definido por \`GLPI_API_PATH\`.

## Configuração

Clone o repositório:

\`\`\`bash
git clone https://github.com/efssantos/glpi-mcp.git
cd glpi-mcp
\`\`\`

Crie o arquivo de ambiente a partir do exemplo:

\`\`\`bash
cp .env.example .env
\`\`\`

Preencha os dados de acesso ao GLPI. Exemplo mínimo:

\`\`\`dotenv
GLPI_URL=https://glpi.exemplo.com
GLPI_API_PATH=/apirest.php
GLPI_APP_TOKEN=seu-app-token
GLPI_USER_TOKEN=seu-user-token
GLPI_TIMEOUT=30
GLPI_VERIFY_TLS=true
\`\`\`

Você pode usar \`GLPI_USER_TOKEN\` ou, alternativamente, definir \`GLPI_USERNAME\` e \`GLPI_PASSWORD\`. Não configure as duas formas sem necessidade.

### Variáveis principais

| Variável | Finalidade | Padrão |
|---|---|---|
| \`GLPI_URL\` | URL base da instância GLPI | Obrigatória |
| \`GLPI_API_PATH\` | Caminho da API REST | \`/apirest.php\` |
| \`GLPI_APP_TOKEN\` | Token da aplicação, se exigido pelo GLPI | — |
| \`GLPI_USER_TOKEN\` | Token do usuário de integração | — |
| \`GLPI_USERNAME\` / \`GLPI_PASSWORD\` | Autenticação alternativa à User Token | — |
| \`GLPI_TIMEOUT\` | Timeout das requisições, em segundos | \`30\` |
| \`GLPI_VERIFY_TLS\` | Validar certificado TLS do GLPI | \`true\` |
| \`MCP_TRANSPORT\` | Transporte: \`stdio\` ou \`streamable-http\` | \`stdio\` |
| \`MCP_HOST\` | Interface de escuta HTTP | \`127.0.0.1\` |
| \`MCP_PORT\` | Porta HTTP | \`8000\` |
| \`MCP_PROXY_MODE\` | Indica execução atrás de proxy privado | \`false\` |
| \`MCP_AUTH_ENABLED\` | Habilita autenticação OIDC no HTTP | \`false\` |
| \`MCP_PUBLIC_URL\` | URL pública do recurso MCP | — |
| \`OIDC_ISSUER_URL\` | Emissor OIDC confiável | — |
| \`OIDC_JWKS_URL\` | Endpoint JWKS para validar assinaturas | — |
| \`OIDC_AUDIENCE\` | Audiência esperada no access token | — |
| \`MCP_READ_SCOPE\` / \`MCP_WRITE_SCOPE\` | Escopos de leitura e escrita | \`glpi:read\` / \`glpi:write\` |

O arquivo \`.env\` contém segredos e não deve ser enviado ao Git. O \`.gitignore\` já exclui esse arquivo; mantenha apenas o \`.env.example\` versionado.

## Instalação local passo a passo

Esta é a opção indicada para quem quer usar o GLPI-MCP no próprio computador com um cliente que inicia processos MCP por \`stdio\`.

### 1. Criar o ambiente Python

**Windows (PowerShell):**

\`\`\`powershell
py -3.12 -m venv .venv
..\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
\`\`\`

**Linux ou macOS:**

\`\`\`bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
\`\`\`

### 2. Configurar as credenciais

Defina as variáveis de ambiente na sessão do terminal. Exemplo em PowerShell:

\`\`\`powershell
$env:GLPI_URL = "https://glpi.exemplo.com"
$env:GLPI_APP_TOKEN = "seu-app-token"
$env:GLPI_USER_TOKEN = "seu-user-token"
$env:MCP_TRANSPORT = "stdio"
\`\`\`

Exemplo em Linux/macOS:

\`\`\`bash
export GLPI_URL="https://glpi.exemplo.com"
export GLPI_APP_TOKEN="seu-app-token"
export GLPI_USER_TOKEN="seu-user-token"
export MCP_TRANSPORT="stdio"
\`\`\`

O programa lê variáveis de ambiente do processo. Ele não carrega automaticamente o arquivo \`.env\`; para uso pelo cliente MCP, informe as variáveis na configuração do cliente ou utilize um script de inicialização que as carregue.

### 3. Testar a inicialização

Com o ambiente virtual ativo e as variáveis configuradas:

\`\`\`bash
python -m server
\`\`\`

No modo \`stdio\`, o processo aguarda mensagens do cliente MCP. Por isso, a forma recomendada de uso é iniciá-lo pelo cliente, e não manter um terminal separado esperando uma interface visual.

### 4. Conectar ao Claude Desktop

No arquivo de configuração do Claude Desktop, inclua o servidor em \`mcpServers\`. Ajuste os caminhos e as credenciais:

\`\`\`json
{
  "mcpServers": {
    "glpi": {
      "command": "C:\\caminho\\glpi-mcp\\.venv\\Scripts\\python.exe",
      "args": ["-m", "server"],
      "cwd": "C:\\caminho\\glpi-mcp",
      "env": {
        "GLPI_URL": "https://glpi.exemplo.com",
        "GLPI_APP_TOKEN": "seu-app-token",
        "GLPI_USER_TOKEN": "seu-user-token",
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
\`\`\`

No Linux/macOS, substitua \`command\` e \`cwd\` pelos caminhos correspondentes. Reinicie o Claude Desktop e confira se as ferramentas do GLPI aparecem.

## Executar em HTTP local

Use HTTP quando quiser executar o servidor como processo independente e conectar um cliente MCP por URL. Esta configuração é apropriada para desenvolvimento ou acesso na própria máquina; não publique esse endpoint diretamente na Internet.

### 1. Configurar o transporte

Mantenha as variáveis de acesso ao GLPI configuradas e defina:

**PowerShell:**

\`\`\`powershell
$env:MCP_TRANSPORT = "streamable-http"
$env:MCP_HOST = "127.0.0.1"
$env:MCP_PORT = "8000"
$env:MCP_PROXY_MODE = "false"
$env:MCP_AUTH_ENABLED = "false"
\`\`\`

**Linux/macOS:**

\`\`\`bash
export MCP_TRANSPORT="streamable-http"
export MCP_HOST="127.0.0.1"
export MCP_PORT="8000"
export MCP_PROXY_MODE="false"
export MCP_AUTH_ENABLED="false"
\`\`\`

### 2. Iniciar o servidor

\`\`\`bash
python -m server
\`\`\`

O endpoint local será:

\`\`\`text
http://127.0.0.1:8000/mcp
\`\`\`

Mantenha o processo em execução enquanto o cliente estiver conectado. Para encerrar, use \`Ctrl+C\`.

### 3. Conectar um cliente

Configure o cliente MCP para utilizar o transporte HTTP e a URL \`http://127.0.0.1:8000/mcp\`. A forma de cadastro depende do cliente utilizado.

> **Atenção:** este modo não habilita autenticação OIDC. Ele fica limitado ao loopback da máquina. Não altere o host para \`0.0.0.0\` nem exponha a porta 8000 em uma rede pública. Para acesso remoto, utilize a implantação HTTPS a seguir.

## Implantar em HTTPS na VPS

Para disponibilizar o GLPI-MCP pela Internet, utilize o Docker Compose incluído no projeto. O Caddy publica HTTPS com certificado automático; o contêiner MCP permanece em rede privada e exige autenticação OIDC.

### Arquitetura e requisitos

- VPS Linux com Docker Engine e Docker Compose v2.
- Domínio/subdomínio apontando para o IP público da VPS.
- Portas TCP 80 e 443 liberadas no firewall. UDP 443 é opcional.
- Provedor OIDC externo acessível por HTTPS (por exemplo, Keycloak).
- Conta técnica do GLPI com permissões mínimas.

### 1. Configurar o provedor OIDC

O GLPI-MCP é um *resource server*: valida access tokens emitidos pelo provedor externo, mas não oferece tela de login nem emite tokens.

Configure o provedor para:

1. Publicar a URL HTTPS do emissor (*issuer*) e o endpoint JWKS.
2. Emitir access tokens JWT assinados com RS256 ou ES256.
3. Incluir as claims \`iss\`, \`aud\`, \`exp\` e \`scope\` (ou \`scp\`).
4. Definir uma audiência para o GLPI-MCP, por exemplo \`glpi-mcp\`.
5. Conceder \`glpi:read\` para pesquisa/consulta e \`glpi:write\` para criação/atualização de chamados.
6. Suportar o fluxo e os mecanismos de descoberta/registro de cliente exigidos pelo cliente MCP remoto.

Use access tokens como bearer tokens, nunca ID tokens. O provedor deve emitir a audiência configurada no GLPI-MCP.

### 2. Preparar a VPS

Na VPS:

\`\`\`bash
git clone https://github.com/efssantos/glpi-mcp.git
cd glpi-mcp
cp .env.example .env
\`\`\`

Edite o \`.env\` com os dados reais:

\`\`\`dotenv
GLPI_URL=https://glpi.exemplo.com
GLPI_APP_TOKEN=seu-app-token
GLPI_USER_TOKEN=seu-user-token

MCP_DOMAIN=mcp.exemplo.com
MCP_PUBLIC_URL=https://mcp.exemplo.com/mcp
OIDC_ISSUER_URL=https://identidade.exemplo.com/realms/glpi
OIDC_JWKS_URL=https://identidade.exemplo.com/realms/glpi/protocol/openid-connect/certs
OIDC_AUDIENCE=glpi-mcp
MCP_READ_SCOPE=glpi:read
MCP_WRITE_SCOPE=glpi:write
\`\`\`

Substitua os endereços de exemplo pelos valores publicados pelo seu provedor. A audiência do access token deve ser igual a \`OIDC_AUDIENCE\`. Proteja o arquivo \`.env\` e não o versione.

### 3. Iniciar a aplicação

Com o DNS apontado para a VPS e as portas liberadas:

\`\`\`bash
docker compose up -d --build
docker compose ps
docker compose logs -f caddy glpi-mcp
\`\`\`

O Caddy solicitará e renovará os certificados TLS automaticamente. O endpoint público será:

\`\`\`text
https://mcp.exemplo.com/mcp
\`\`\`

### 4. Verificar a implantação

\`\`\`bash
docker compose ps
docker compose logs --tail 100 glpi-mcp
docker compose logs --tail 100 caddy
\`\`\`

Confirme que os dois serviços estão ativos, que o domínio apresenta certificado válido e que o GLPI-MCP consegue alcançar os endpoints OIDC/JWKS e a API do GLPI. Uma chamada sem token válido deve ser recusada; uma chamada autenticada precisa conter os escopos exigidos.

### Como a rede fica protegida

- Somente o Caddy publica as portas 80 e 443 no host.
- A porta 8000 do GLPI-MCP não é publicada no host.
- Caddy e GLPI-MCP comunicam-se por rede Docker privada.
- O GLPI-MCP possui uma rede de saída para acessar o GLPI.
- Não abra a porta 8000 no firewall da VPS.

Para atualizar a aplicação após novas versões:

\`\`\`bash
git pull
docker compose up -d --build
\`\`\`

## Conectar clientes MCP

O endpoint para clientes remotos é \`https://SEU-DOMINIO/mcp\`. O cliente precisa suportar MCP por Streamable HTTP e o fluxo de autenticação OAuth/OIDC configurado no provedor.

No Claude, adicione um conector MCP remoto nas configurações de conectores da conta ou workspace, informe o endpoint HTTPS e conclua a autenticação OAuth. Os nomes e a disponibilidade das opções variam conforme o produto, plano e política do workspace. O provedor de identidade precisa oferecer os metadados e o mecanismo de registro de cliente esperados pelo conector.

### Escopos de acesso

| Escopo | Permissão |
|---|---|
| \`glpi:read\` | \`glpi_search\` e \`glpi_get_item\` |
| \`glpi:write\` | \`glpi_create_ticket\` e \`glpi_update_ticket\`; também exige \`glpi:read\` |

A autorização OAuth não substitui as permissões da conta técnica dentro do GLPI. Para uso local com Claude Desktop, prefira a conexão \`stdio\` descrita na seção [Instalação local](#instalação-local-passo-a-passo).

## Ferramentas disponíveis

| Ferramenta | Descrição |
|---|---|
| \`glpi_search(itemtype, criteria, limit)\` | Pesquisa registros por tipo e critérios. Limite entre 1 e 100 resultados. |
| \`glpi_get_item(itemtype, item_id)\` | Consulta um registro pelo tipo e identificador. |
| \`glpi_create_ticket(name, content, urgency, ...)\` | Cria um chamado, com categoria e entidade opcionais. |
| \`glpi_update_ticket(ticket_id, fields)\` | Atualiza campos permitidos de um chamado existente. |

A pesquisa recebe \`criteria\` como uma query string URL-encoded com parâmetros de pesquisa aceitos pela API do GLPI, por exemplo \`criteria[0][field]\`, \`criteria[0][searchtype]\` e \`criteria[0][value]\`. Os campos de atualização são validados por lista de permissões no código.

## Desenvolvimento e contribuição

### Preparar o ambiente

Faça fork/clone do repositório, crie um ambiente virtual e instale as dependências:

\`\`\`bash
git clone https://github.com/efssantos/glpi-mcp.git
cd glpi-mcp
python -m venv .venv
\`\`\`

Ative o ambiente virtual e instale:

\`\`\`bash
# Linux/macOS
source .venv/bin/activate

# Windows PowerShell
# ..\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt
\`\`\`

Configure as variáveis GLPI necessárias para testar manualmente a integração. Os testes automatizados utilizam mocks e não exigem instância GLPI nem credenciais reais.

### Executar os testes

\`\`\`bash
python -m unittest discover -s tests -v
\`\`\`

Ao contribuir:

1. Crie uma branch a partir de \`main\` com nome descritivo e em letras minúsculas, usando prefixos como \`feat/\`, \`fix/\`, \`docs/\`, \`test/\` ou \`security/\`.
2. Mantenha a implementação modular: lógica compartilhada em \`core/\` e integração com o GLPI em \`integrations/glpi/\`.
3. Adicione ou atualize testes para novos comportamentos e correções.
4. Não inclua credenciais, tokens ou arquivos \`.env\` nos commits.
5. Abra uma Pull Request descrevendo a motivação, as alterações e como foram testadas.

Padrão de mensagem de commit: \`type: action and description\`, em letras minúsculas e com verbo de ação no imperativo. Exemplos:

\`\`\`text
feat: add asset search tool
fix: validate ticket update fields
test: cover oidc token verification
docs: clarify local http setup
\`\`\`

### Diretrizes técnicas

- Preserve a compatibilidade com Python 3.11 e 3.12.
- Utilize \`unittest\` e mocks para testes unitários; não dependa de um GLPI real na suíte automatizada.
- Valide entradas e configuração antes de executar chamadas externas.
- Preserve mensagens de erro seguras, sem expor tokens ou respostas sensíveis da API.
- Mantenha os modos \`stdio\` e \`streamable-http\` funcionais.
- Em mudanças de autenticação, cubra validação JWT, emissor, audiência, expiração e escopos.

## Segurança

- Utilize uma conta técnica exclusiva no GLPI e aplique o menor privilégio.
- Mantenha \`GLPI_VERIFY_TLS=true\` em produção.
- Nunca publique o arquivo \`.env\` nem inclua credenciais em logs ou commits.
- O modo HTTP sem autenticação é destinado apenas ao loopback local.
- Para acesso remoto, utilize HTTPS, OIDC e escopos; não exponha diretamente a porta 8000.
- Faça rotação dos tokens GLPI e proteja os volumes e arquivos de configuração da VPS.
- Revogue e substitua imediatamente qualquer credencial que tenha sido exposta.

## Solução de problemas

| Sintoma | Verificações |
|---|---|
| Falha ao conectar ao GLPI | Confira \`GLPI_URL\`, DNS, firewall e disponibilidade da API legada. |
| HTTP 401/403 do GLPI | Confira App-Token, User Token ou credenciais e permissões da conta técnica. |
| Erro de certificado | Verifique a cadeia de certificados. Não desabilite a validação TLS em produção. |
| Servidor HTTP não inicia | Confira \`MCP_TRANSPORT\`, \`MCP_HOST\`, \`MCP_PORT\` e as regras de segurança de bind em \`core/config.py\`. |
| Token remoto rejeitado | Confira assinatura, algoritmo, emissor, audiência, expiração, JWKS e escopos. |
| Cliente não lista ferramentas | Confira o endpoint \`/mcp\`, o transporte suportado pelo cliente e os logs do servidor. |
| HTTPS não emite certificado | Confira DNS público, portas TCP 80/443 e logs do Caddy. |

## Licença

Este projeto é distribuído sob a licença MIT. Consulte [LICENSE](LICENSE) para os termos completos.
