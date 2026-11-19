# GLPI MCP Server

Servidor MCP desenvolvido em Python que integra assistentes de IA ao GLPI por meio da API REST legada (`apirest.php`). Com ele, um cliente compatível com o Model Context Protocol (MCP) pode pesquisar registros, consultar itens e gerenciar chamados, respeitando as permissões da conta configurada no GLPI.

## Índice

- [Como funciona](#como-funciona)
- [Pré-requisitos](#pré-requisitos)
- [Preparar o GLPI](#preparar-o-glpi)
- [Configuração](#configuração)
- [Executar localmente com Python](#executar-localmente-com-python)
- [Executar com Docker](#executar-com-docker)
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
MCP_HOST=127.0.0.1
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

Certifique-se de que o arquivo `.env` esteja preenchido. Construa a imagem na raiz do repositório:

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

Para executar o servidor como serviço HTTP, configure `MCP_TRANSPORT=streamable-http` e faça o processo escutar em `0.0.0.0) dentro do contêiner. Exemplo:

```bash
docker run -d \
  --name glpi-mcp \
  --restart unless-stopped \
  --env-file .env \
  -e MCP_TRANSPORT=streamable-http \
  -e MCP_HOST=0.0.0.0 \
  -p 127.0.0.1:8000:8000 \
  glpi-mcp:local
```

O mapeamento acima disponibiliza a porta somente no loopback do host. Para acesso remoto, coloque um proxy reverso na frente do serviço, configure HTTPS e autenticação/autorização no proxy. O endpoint MCP é:

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
| Contêiner HTTP inicia, mas não aceita conexões | Confirme `MCP_TRANSPORT=streamable-http`, `MCP_HOST=0.0.0.0), o mapeamento da porta e os logs do contêiner. |
| Ferramentas não aparecem | Consulte os logs do processo MCP e confirme que o cliente suporta o transporte configurado. |

## Segurança

- Use uma conta técnica dedicada no GLPI e aplique o princípio do menor privilégio.
- Nunca versione `.env`, tokens, senhas ou arquivos com credenciais.
- Mantenha a validação TLS habilitada em produção.
- Não exponha o endpoint MCP diretamente à Internet sem uma camada de autenticação e autorização.
- HTTPS protege o tráfego, mas, por si só, não identifica nem autoriza quem pode invocar as ferramentas.
- Revogue e gere novamente qualquer token que tenha sido exposto.

## Licença

Este projeto é distribuído sob a licença MIT. Consulte o arquivo [LICENSE](LICENSE) para ver os termos completos.
