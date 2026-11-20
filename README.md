# GLPI-MCP

Servidor **Model Context Protocol (MCP)** em Python que integra clientes de IA à API REST legada do GLPI (`apirest.php`). Permite pesquisar registros, consultar itens e criar/atualizar chamados usando uma conta técnica configurada no GLPI.

O GLPI-MCP suporta execução local via `stdio` e acesso remoto via Streamable HTTP. Para uso remoto, a stack Docker Compose inclui Caddy (HTTPS), Keycloak (OIDC), PostgreSQL para persistência de identidade e o GLPI-MCP, com autorização por scopes.

> Esta implementação utiliza a API REST legada do GLPI. Não é uma integração com a API REST v2.

## Documentação

| Guia | Descrição |
|---|---|
| [Arquitetura](docs/ARCHITECTURE.md) | Componentes, fluxos, autenticação e redes. |
| [Implantação em VPS](docs/DEPLOYMENT.md) | Tutorial de instalação remota, DNS, firewall, Compose, HTTPS e validação. |
| [Configuração do Keycloak](docs/KEYCLOAK.md) | Realm, client, scopes, audience e usuário de teste. |
| [Segurança](docs/SECURITY.md) | Credenciais, OIDC, scopes, rede, containers e verificações de segurança. |

Todos os domínios e credenciais dos exemplos são fictícios. Substitua-os por valores de sua infraestrutura.

## Recursos

- Integração com API REST legada do GLPI.
- Ferramentas MCP de pesquisa, consulta e gerenciamento de chamados.
- Transporte local `stdio`.
- Transporte HTTP Streamable.
- Autenticação remota com validação de access token OIDC/JWT.
- Autorização por scopes de leitura e escrita.
- Stack Compose integrada com GLPI-MCP, Keycloak, PostgreSQL e Caddy.
- HTTPS para os endpoints MCP e de identidade.
- Controles de hardening do container MCP.

## Arquitetura resumida

```text
Cliente MCP
   | HTTPS/Streamable HTTP
   v
Caddy (hosts MCP e identidade)
   |                  |
   v                  v
GLPI-MCP          Keycloak
   |                  |
   v                  v
GLPI API          PostgreSQL
```

Na implantação remota, o Compose provisiona todos os serviços. Caddy atua como proxy HTTPS; as portas do GLPI-MCP, Keycloak e PostgreSQL não são publicadas diretamente no host. Consulte [Arquitetura](docs/ARCHITECTURE.md) para detalhes.

## Pré-requisitos

### Uso local

- Python 3.11 ou superior.
- Acesso a um GLPI com API REST legada habilitada.
- App-Token, quando exigido pelo GLPI.
- User Token ou credenciais de conta técnica.

### Implantação remota

- VPS Linux.
- Docker Engine e Docker Compose v2.
- Domínios e registros DNS para MCP e autenticação apontando para a VPS.
- Portas 80 e 443 liberadas.
- Acesso ao GLPI com API REST habilitada.

## Início rápido — execução local

### 1. Clonar e instalar

```bash
git clone https://github.com/efssantos/glpi-mcp.git
cd glpi-mcp
python -m venv .venv
```

Ative o ambiente virtual:

**Windows PowerShell**
```powershell
.\.venv\Scripts\Activate.ps1
```

**Linux/macOS**
```bash
source .venenv/bin/activate
```

Instale as dependências:
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Configurar o acesso ao GLPI

Configure as variáveis de ambiente na sessão do terminal. Exemplo PowerShell:

```powershell
$env:GLPI_URL = "https://glpi.example.com"
$env:GLPI_API_PATH = "/apirest.php"
$env:GLPI_APP_TOKEN = "SEU_APP_TOKEN"
$env:GLPI_USER_TOKEN = "SEU_USER_TOKEN"
$env:MCP_TRANSPORT = "stdio"
```

No Linux/macOS:

```bash
export GLPI_URL="https://glpi.example.com"
export GLPI_API_PATH="/apirest.php"
export GLPI_APP_TOKEN="SEU_APP_TOKEN"
export GLPI_USER_TOKEN="SEU_USER_TOKEN"
export MCP_TRANSPORT="stdio"
```

Você pode usar `GLPI_USER_TOKEN` ou, alternativamente, `GLPI_USERNAME` e `GLPI_PASSWORD`. Consulte [.env.example](.env.example) para todas as variáveis. O processo local não carrega automaticamente o arquivo `.env`; configure as variáveis no cliente MCP ou no shell.

### 3. Configurar um cliente MCP local

Exemplo para Claude Desktop (ajuste o caminho de instalação e os valores ao seu ambiente):

```json
{
  "mcpServers": {
    "glpi": {
      "command": "C:\\CAMINHO\\glpi-mcp\\.venv\\Scripts\\python.exe",
      "args": ["-m", "server"],
      "cwd": "C:\\CAMINHO\\glpi-mcp",
      "env": {
        "GLPI_URL": "https://glpi.example.com",
        "GLPI_APP_TOKEN": "SEU_APP_TOKEN",
        "GLPI_USER_TOKEN": "SEU_USER_TOKEN",
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

Reinicie o cliente e confirme se as ferramentas MCP estão disponíveis. O processo `stdio` é iniciado e gerenciado pelo cliente.

> Consulte o [tutorial completo](docs/DEPLOYMENT.md) para transporte HTTP local e implantação remota HTTPS integrada.

## Transporte HTTP local

Para desenvolvimento, o servidor pode ser iniciado em loopback com Streamable HTTP. Configure `MCP_TRANSPORT=streamable-http`, `MCP_HOST=127.0.0.1`, `MCP_PORT=8000`, `MCP_AUTH_ENABLED=false` e `MCP_PROXY_MODE=false`, além das variáveis de acesso ao GLPI, e execute:

```bash
python -m server
```

Endpoint local: `http://127.0.0.1:8000/mcp`.

Este modo não utiliza autenticação OIDC e não deve ser exposto à rede pública. Para uso remoto, siga [Implantação em VPS](docs/DEPLOYMENT.md).

## Ferramentas MCP

| Ferramenta | Descrição |
|---|---|
| `glpi_search(itemtype, criteria, limit)` | Pesquisa registros por tipo e critérios. Limite de 1 a 100 resultados. |
| `glpi_get_item(itemtype, item_id)` | Consulta um registro pelo tipo e identificador. |
| `glpi_create_ticket(name, content, urgency, ...)` | Cria chamado; permite campos opcionais conforme a implementação. |
| `glpi_update_ticket(ticket_id, fields)` | Atualiza campos permitidos de um chamado. |

A pesquisa recebe `criteria` no formato de critérios aceito pela API GLPI. Campos de atualização são limitados/validados pela implementação. Consulte o código em `integrations/glpi/tools.py` para parâmetros exatos disponíveis na versão instalada.

Scopes usados na autorização remota:

| Scope | Acesso |
|---|---|
| `glpi:read` | Pesquisa e consulta |
| `glpi:write` | Criação e atualização (também exige leitura) |

A autorização MCP não substitui as permissões da conta técnica configurada no GLPI.

## Testes

Os testes automatizados usam `unittest` e mocks e não exigem uma instância GLPI nem credenciais reais:

```bash
python -m unittest discover -s tests -v
```

## Contribuição

1. Crie uma branch de trabalho a partir de `main`.
2. Use nomes de branch descritivos, como `feat/`, `fix/`, `docs/`, `test/` ou `security/`.
3. Inclua ou atualize testes quando alterar comportamento.
4. Não inclua segredos, tokens, dados reais de chamados ou arquivos `.env`.
5. Abra Pull Request com resumo, motivação e testes realizados.

Exemplos de commits:

```text
feat: add asset search tool
fix: validate ticket update fields
test: cover oidc token verification
docs: improve deployment guide
```

## Segurança

- Use conta técnica GLPI dedicada com privilégio mínimo.
- Mantenha `GLPI_VERIFY_TLS=true`.
- Não versione arquivos de ambiente ou credenciais.
- Não exponha as portas MCP 8000, Keycloak 8080 ou PostgreSQL 5432 na Internet.
- Para implantação remota, use HTTPS e autenticação OIDC.
- Restrinja portas administrativas, atualize imagens/container e rotacione tokens.

Consulte [SECURITY.md](docs/SECURITY.md).

## Solução de problemas

| Sintoma | Verifique |
|---|---|
| API GLPI não conecta | URL base, DNS, API REST legada, firewall e TLS. |
| GLPI retorna 401/403 | App-Token, User Token/credenciais e permissões da conta. |
| Servidor HTTP não inicia | Transporte, host, porta e variáveis MCP. |
| Token remoto recusado | Assinatura, issuer, audience, expiração, JWKS e scopes. |
| Cliente não lista ferramentas | Endpoint `/mcp`, transporte suportado, autenticação e logs. |
| Caddy não emite certificado | DNS dos dois hosts, portas TCP 80/443 e logs do Caddy. |

## Licença

Este projeto está sob a licença MIT. Consulte [LICENSE](LICENSE).
