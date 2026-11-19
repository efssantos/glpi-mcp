# GLPI MCP Server

Servidor MCP desenvolvido em Python que integra assistentes de IA ao GLPI por meio da API REST legada (`apirest.php`). Com ele, um cliente compatível com o Model Context Protocol (MCP) pode pesquisar registros, consultar itens e gerenciar chamados, respeitando as permissões da conta configurada no GLPI.

## Índice

- [Como funciona](#como-funciona)
- [Pré-requisitos](#pré-requisitos)
- [Preparar o GLPI](#preparar-o-glpi)
- [Configuração](#configuração)
- [Executar localmente com Python](#executar-localmente-com-python)
- [Executar com Docker](#executar-com-docker)
- [Implantação remota em VPS](#implantação-remota-em-vps)
- [Conectar a um cliente MCP](#conectar-a-um-cliente-mcp)
- [Ferramentas disponíveis](#ferramentas-disponíveis)
- [Testes automatizados](#testes-automatizados)
- [Solução de problemas](#solução-de-problemas)
- [Segurança](#segurança)

## Como funciona

O GLPI MCP Server funciona como uma ponte entre o cliente MCP (por exemplo, Claude Desktop) e a API REST do GLPI:

```text
Assistente/cliente MCP  <-->  GLPI MCP Server  <-->  API REST do GLPI
```

O servidor oferece dois modos de transporte:

- **stdio**: recomendado quando o cliente MCP inicia o servidor como um processo local.
- **Streamable HTTP**: recomendado para execução como serviço, acessível por um cliente remoto ou por um proxy reverso.

### Qual modo devo escolher?

A escolha depende de onde o servidor será executado e de quem precisa acessá-lo:

| Cenário | Transporte recomendado | Motivo |
|---|---|---|
| Uso individual no computador, por exemplo com Claude Desktop | **stdio (local)** | O próprio cliente inicia o processo. Não precisa abrir porta nem publicar um serviço de rede. |
| Desenvolvimento e testes na máquina do desenvolvedor | **stdio (local)** | Configuração simples e comunicação direta entre o cliente e o processo. |
| GLPI MCP hospedado em uma VM ou servidor | **Streamable HTTP** | O MCP fica em execução como serviço e pode ser acessado por clientes remotos. |
| Vários usuários ou clientes precisam acessar uma instalação central | **Streamable HTTP** | Centraliza a execução e a manutenção do servidor. Cada cliente precisa ser autenticado e autorizado conforme a arquitetura adotada. |
| Ambiente com proxy reverso e domínio HTTPS | **Streamable HTTP** | Permite publicar o endpoint por meio de um proxy, com TLS e controles de acesso. |
| Ambiente sem necessidade de acesso remoto | **stdio (local)** | Evita manter uma porta HTTP aberta. |

**Regra prática:** use stdio quando o assistente e o processo MCP estiverem na mesma máquina e o cliente puder iniciar o processo. Use Streamable HTTP quando o MCP precisar ficar hospedado e ser acessado pela rede. Os dois modos oferecem as mesmas ferramentas; o que muda é a forma de comunicação.

## Pré-requisitos

Para execução local:

- Python 3.11 ou superior.
- Acesso de rede à instância GLPI.
- API REST legada habilitada no GLPI.
- Token de aplicação e credenciais/token de usuário com as permissões necessárias.

Para execução em contêiner:

- Docker Engine e o comando `docker`.
- Docker Compose não é necessário: os exemplos abaixo usam diretamente `docker build` e `docker run`.

> **Compatibilidade:** este projeto utiliza a API REST legada do GLPI (`apirest.php`). Verifique se ela está habilitada e disponível na sua instalação. A API REST v2 de versões recentes pode ter fluxo de autenticação diferente e não é o alvo desta implementação.

## Preparar o GLPI

1. Entre no GLPI com uma conta administradora.
2. Habilite e configure a API REST legada nas configurações de API da sua instalação.
3. Gere um **App-Token** (token da aplicação).
4. Gere um **User Token** para a conta de integração ou prepare um usuário e senha dedicados.
5. Conceda à conta somente as permissões necessárias para as operações que pretende executar.

Os nomes dos menus podem variar conforme a versão e o idioma do GLPI. Consulte a documentação correspondente à sua versão para habilitar a API e gerar os tokens.

Você precisará da URL base do GLPI, por exemplo `https://glpi.suaempresa.com`. Não inclua `/apirest.php` no valor de `GLPI_URL`; o caminho da API é configurado separadamente.

## Configuração

Clone o repositório e entre na pasta:

```bash
git clone https://github.com/efssantos/glpi-mcp.git
cd glpi-mcp
```

Crie um arquivo `.env` na raiz do projeto usando `.env.example` como referência. Exemplo:

```dotenv
GLPI_URL=https://glpi.suaempresa.com
GLPI_API_PATH=/apirest.php
GLPI_APP_TOKEN=COLOQUE_SEU_APP_TOKEN

# Use GLPI_USER_TOKEN ou, alternativamente, GLPI_USERNAME + GLPI_PASSWORD.
GLPI_USER_TOKEN=COLOQUE_SEU_USER_TOKEN
# GLPI_USERNAME=usuario-integracao
# GLPI_PASSWORD=sua-senha

GLPI_TIMEOUT=30
GLPI_VERIFY_TLS=true

# Para cliente local iniciado como processo:
MCP_TRANSPORT=stdio
MCP_HOST=127.0.0.1\nMCP_PROXY_MODE=false
MCP_PORT=8000
LOG_LEVEL=INFO
```

Ajuste os valores de acordo com seu ambiente:

| Variável | Obrigatória | Descrição |
|---|---:|---|
| `GLPI_URL` | Sim | URL base da instalação GLPI, sem o caminho da API. |
| `GLPI_API_PATH` | Não | Caminho da API. Padrão: `/apirest.php`. |
| `GLPI_APP_TOKEN` | Conforme GLPI | Token da aplicação, quando exigido pela configuração da API. |
| `GLPI_USER_TOKEN` | Uma forma de autenticação | Token do usuário. Alternativamente, use usuário e senha. |
| `GLPI_USERNAME` | Uma forma de autenticação | Usuário da conta de integração. |
| `GLPI_PASSWORD` | Uma forma de autenticação | Senha da conta de integração. |
| `GLPI_TIMEOUT` | Não | Tempo limite das requisições em segundos. Padrão: `30`. |
| `GLPI_VERIFY_TLS` | Não | Valida o certificado TLS. Padrão: `true`. |
| `MCP_TRANSPORT` | Não | `stdio` ou `streamable-http`. Padrão: `stdio`. |
| `MCP_HOST` | Não | Interface de escuta HTTP. Padrão: `127.0.0.1`. |
| `MCP_PORT` | Não | Porta HTTP. Padrão: `8000`. |

Não compartilhe o arquivo `.env`, tokens ou senhas. O arquivo já deve permanecer fora do Git por meio do `.gitignore`.

## Executar localmente com Python

### Windows (PowerShell)

Crie e ative um ambiente virtual:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Se o PowerShell bloquear a ativação do ambiente virtual, consulte as políticas de execução da sua organização ou execute os comandos usando o Python do ambiente virtual diretamente.

Configure as variáveis de ambiente a partir do arquivo `.env` ou defina-as na sessão do PowerShell. Para definir manualmente:

```powershell
$env:GLPI_URL = "https://glpi.suaempresa.com"
$env:GLPI_API_PATH = "/apirest.php"
$env:GLPI_APP_TOKEN = "COLOQUE_SEU_APP_TOKEN"
$env:GLPI_USER_TOKEN = "COLOQUE_SEU_USER_TOKEN"
$env:MCP_TRANSPORT = "stdio"
python -m server
```

### Linux e macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Defina as variáveis de ambiente (ou carregue-as com uma ferramenta local apropriada) e inicie:

```bash
export GLPI_URL="https://glpi.suaempresa.com"
export GLPI_API_PATH="/apirest.php"
export GLPI_APP_TOKEN="COLOQUE_SEU_APP_TOKEN"
export GLPI_USER_TOKEN="COLOQUE_SEU_USER_TOKEN"
export MCP_TRANSPORT="stdio"
python -m server
```

Quando o servidor estiver no modo `stdio`, ele é iniciado pelo cliente MCP. Não é necessário abrir uma porta de rede nem manter um terminal separado executando o processo.

## Executar com Docker

### Usar imagem publicada (GHCR)

A imagem é publicada no GitHub Container Registry:

```bash
docker pull ghcr.io/efssantos/glpi-mcp:latest
```

Para usar uma versão específica, substitua `latest` pela tag correspondente, por exemplo `1.0.0`.

Com o arquivo `.env` preenchido, inicie o contêiner em modo stdio:

```bash
docker run --rm -i --env-file .env ghcr.io/efssantos/glpi-mcp:latest
```

Para executar em modo Streamable HTTP, configure `MCP_TRANSPORT=streamable-http` no arquivo `.env` e publique a porta:

```bash
docker run -d \\
  --name glpi-mcp \\
  --restart unless-stopped \\
  --env-file .env \\
  -e MCP_HOST=0.0.0.0 \\
  -e MCP_PROXY_MODE=true \\
  -e MCP_AUTH_ENABLED=true \\
  -p 127.0.0.1:8000:8000 \\
  ghcr.io/efssantos/glpi-mcp:latest
```

### Construir a imagem localmente

Se preferir construir a imagem a partir do código-fonte:

```bash
docker build -t glpi-mcp:local .
```

### Modo stdio (cliente local)

O cliente MCP deve iniciar o contêiner e manter a entrada padrão aberta:

```bash
docker run --rm -i --env-file .env glpi-mcp:local
```

Esse comando é apropriado para ser usado como processo iniciado pelo cliente MCP. Não acrescente `-t` nessa configuração.

### Modo Streamable HTTP (serviço)

Para executar o servidor como serviço HTTP, configure `MCP_TRANSPORT=streamable-http` e faça o processo escutar em `0.0.0.0` dentro do contêiner. Exemplo:

```bash
docker run -d \
  --name glpi-mcp \
  --restart unless-stopped \
  --env-file .env \
  -e MCP_TRANSPORT=streamable-http \
  -e MCP_HOST=0.0.0.0 \
  -e MCP_PROXY_MODE=true \
  -p 127.0.0.1:8000:8000 \
  glpi-mcp:local
```

O mapeamento acima disponibiliza a porta somente no loopback do host. O processo escuta em todas as interfaces **dentro do contêiner**, por isso `MCP_PROXY_MODE=true` só deve ser usado quando a porta estiver isolada e acessível exclusivamente pelo proxy reverso (por exemplo, por uma rede Docker privada, sem publicar a porta no host). Para acesso remoto, configure HTTPS, autenticação e autorização no proxy. Não exponha a porta do contêiner diretamente à Internet. O endpoint MCP é:

```text
https://SEU-DOMINIO/mcp
```

Consulte os logs e pare o contêiner com:

```bash
docker logs -f glpi-mcp
docker stop glpi-mcp
```

Se alterar o código ou as dependências, reconstrua a imagem e recrie o contêiner.

## Conectar a um cliente MCP

### Claude Desktop — execução local com Python

No arquivo de configuração do Claude Desktop, adicione uma entrada em `mcpServers`. Ajuste o caminho absoluto do repositório e o caminho do arquivo `.env`:

```json
{
  "mcpServers": {
    "glpi": {
      "command": "C:\\CAMINHO\\PARA\\glpi-mcp\\.venv\\Scripts\\python.exe",
      "args": ["-m", "server"],
      "cwd": "C:\\CAMINHO\\PARA\\glpi-mcp",
      "env": {
        "GLPI_URL": "https://glpi.suaempresa.com",
        "GLPI_API_PATH": "/apirest.php",
        "GLPI_APP_TOKEN": "SEU_APP_TOKEN",
        "GLPI_USER_TOKEN": "SEU_USER_TOKEN",
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

Substitua os caminhos e credenciais pelos valores do seu ambiente. Alternativamente, use um pequeno script de inicialização que carregue o arquivo `.env` e inicie `python -m server`; não presuma que o cliente MCP carregará automaticamente o arquivo `.env`.

### Claude Desktop — execução local com Docker

Se a imagem já foi construída e o arquivo `.env` está em um caminho conhecido, a configuração pode iniciar o contêiner:

```json
{
  "mcpServers": {
    "glpi": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "--env-file", "C:\\CAMINHO\\PARA\\glpi-mcp\\.env",
        "glpi-mcp:local"
      ]
    }
  }
}
```

### Cliente remoto via Streamable HTTP

Quando o servidor estiver publicado com HTTPS e protegido por autenticação, configure o cliente MCP para usar o endpoint remoto `https://SEU-DOMINIO/mcp`. A forma exata de cadastrar um servidor HTTP varia conforme o cliente. Não use HTTP sem TLS em redes não confiáveis.

Após conectar, confirme no cliente se as ferramentas do GLPI foram carregadas. Reinicie o cliente após alterar sua configuração.

## Validar a instalação Streamable HTTP

Depois de iniciar o contêiner, faça os testes abaixo na própria máquina em que o serviço está hospedado. Os exemplos consideram a porta local `127.0.0.1:8000` e o endpoint `/mcp`.

### 1. Verificar se o contêiner está em execução

```bash
docker ps --filter name=glpi-mcp
docker logs --tail 50 glpi-mcp
```

Confirme que o contêiner está ativo e que os logs não mostram erros de inicialização.

### 2. Inicializar uma sessão MCP

Envie uma requisição JSON-RPC de inicialização:

```bash
curl -i \
  -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2025-03-26",
      "capabilities": {},
      "clientInfo": {
        "name": "glpi-mcp-test",
        "version": "1.0.0"
      }
    }
  }'
```

A resposta esperada é `HTTP/1.1 200 OK`, com `content-type: text/event-stream`, um cabeçalho `mcp-session-id` e um evento `message` contendo os dados de inicialização. Anote o valor de `mcp-session-id` retornado: ele será usado nas próximas requisições.

### 3. Informar que o cliente concluiu a inicialização

Substitua `SEU_SESSION_ID` pelo identificador recebido no passo anterior:

```bash
curl -i \
  -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "MCP-Session-Id: SEU_SESSION_ID" \
  -H "MCP-Protocol-Version: 2025-03-26" \
  -d '{
    "jsonrpc": "2.0",
    "method": "notifications/initialized"
  }'
```

Essa notificação não possui `id`, pois não espera uma resposta JSON-RPC com resultado.

### 4. Listar as ferramentas disponíveis

Use o mesmo identificador de sessão:

```bash
curl -i \
  -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "MCP-Session-Id: SEU_SESSION_ID" \
  -H "MCP-Protocol-Version: 2025-03-26" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {}
  }'
```

A resposta esperada é `HTTP 200` e um evento contendo `result.tools`. Confira se a lista inclui as ferramentas esperadas, como `glpi_search`, `glpi_get_item`, `glpi_create_ticket` e `glpi_update_ticket`.

### 5. Fazer uma consulta real ao GLPI

Depois de confirmar que as ferramentas aparecem em `tools/list`, conecte um cliente MCP (por exemplo, Claude Desktop) e execute uma consulta de leitura, como uma pesquisa de registros. O resultado depende da conectividade com o GLPI, das credenciais configuradas e das permissões da conta de integração.

> **Importante:** um `GET /mcp` simples não realiza a inicialização do protocolo. Se ele retornar `406 Not Acceptable` com a mensagem `Client must accept text/event-stream`, isso indica que o cabeçalho `Accept: text/event-stream` não foi enviado. Use o fluxo de inicialização por `POST` mostrado acima. Se a sessão expirar ou o servidor for reiniciado, inicialize uma nova sessão e use o novo identificador.

## Ferramentas disponíveis

| Ferramenta | Finalidade |
|---|---|
| `glpi_search(itemtype, criteria, limit)` | Pesquisa registros por tipo de item, critérios e limite de resultados. O limite máximo é 100. |
| `glpi_get_item(itemtype, item_id)` | Consulta um registro pelo tipo e ID. |
| `glpi_create_ticket(name, content, urgency, ...)` | Cria um chamado no GLPI. |
| `glpi_update_ticket(ticket_id, fields)` | Atualiza campos de um chamado existente. |

Os tipos de item, critérios de pesquisa e campos aceitos seguem as regras da API GLPI e as permissões da conta utilizada.

## Testes automatizados

Os testes usam `unittest` e mocks para isolar as chamadas HTTP. Não é necessário ter uma instância GLPI nem fornecer credenciais reais.

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

O GitHub Actions executa a suíte em Python 3.11 e 3.12 nos eventos configurados no workflow do repositório.

## Solução de problemas

| Sintoma | O que verificar |
|---|---|
| Erro de conexão com o GLPI | Confirme `GLPI_URL`, DNS, conectividade, firewall e se a API está acessível. |
| HTTP 401 ou 403 | Confira App-Token, token/credenciais do usuário, configuração da API e permissões da conta no GLPI. |
| Erro de certificado TLS | Instale/configure a cadeia de certificados confiável. Use `GLPI_VERIFY_TLS=false` somente em ambiente de desenvolvimento controlado. |
| Cliente não encontra o servidor | Em stdio, valide comando, argumentos, diretório de trabalho e caminhos absolutos. Reinicie o cliente depois de editar a configuração. |
| Contêiner HTTP inicia, mas não aceita conexões | Confirme `MCP_TRANSPORT=streamable-http`, `MCP_HOST=0.0.0.0`, o mapeamento da porta e os logs do contêiner. |
| Ferramentas não aparecem | Consulte os logs do processo MCP e confirme que o cliente suporta o transporte configurado. |

## Segurança

- Use uma conta técnica dedicada no GLPI e aplique o princípio do menor privilégio.
- Nunca versione `.env`, tokens, senhas ou arquivos com credenciais.
- Mantenha a validação TLS habilitada em produção.
- Não exponha o endpoint MCP diretamente à Internet nem publique a porta do contêiner em interfaces de rede públicas.
- Em `streamable-http`, prefira `MCP_HOST=127.0.0.1` quando o proxy estiver no mesmo host. Se o proxy estiver em outro contêiner, use `MCP_HOST=0.0.0.0` somente com `MCP_PROXY_MODE=true`, em uma rede privada compartilhada e sem publicar a porta MCP diretamente no host.
- Configure o proxy com HTTPS obrigatório, autenticação de cada cliente, autorização por usuário/grupo, limites de requisição e logs de auditoria.
- Restrinja por firewall/rede o acesso à porta local do MCP para que somente o proxy possa alcançá-la. Não confie apenas em um cabeçalho de identidade enviado pelo cliente.
- HTTPS protege o tráfego, mas, por si só, não identifica nem autoriza quem pode invocar as ferramentas.
- O servidor MCP não implementa autenticação HTTP própria nesta versão; a implantação em rede depende dos controles do proxy. O modo `stdio` continua sendo apropriado para execução local.
- Revogue e gere novamente qualquer token que tenha sido exposto.

## Licença

Este projeto é distribuído sob a licença MIT. Consulte o arquivo [LICENSE](LICENSE) para ver os termos completos.


## Implantação remota em VPS

Para publicar o GLPI-MCP com HTTPS automático, Caddy e autenticação OAuth/OIDC, siga o [guia de implantação remota](docs/deployment.md). A configuração usa Docker Compose, mantém a porta MCP fora da interface pública e preserva o transporte local `stdio`.
