# GLPI MCP Server

Servidor MCP em Python que conecta ao GLPI pela API REST legada (`apirest.php`).
As ferramentas disponíveis permitem pesquisar itens, consultar um registro,
criar chamados e atualizar chamados. O acesso respeita os perfis e permissões
da conta configurada no GLPI.

## Configuração

Instale as dependências e configure as variáveis de ambiente:

```powershell
python -m pip install -r requirements.txt
$env:GLPI_URL = "https://glpi.example.com"
$env:GLPI_APP_TOKEN = "..."
$env:GLPI_USER_TOKEN = "..."
python -m server
```

Como alternativa ao `GLPI_USER_TOKEN`, configure `GLPI_USERNAME` e
`GLPI_PASSWORD`. `GLPI_APP_TOKEN` depende da configuração da API no GLPI.
Veja `.env.example` para as opções. A verificação TLS fica habilitada por
padrão; desabilite-a somente em ambientes de desenvolvimento controlados.

## Docker

Copie `.env.example` para `.env`, preencha as credenciais e construa a imagem:

```powershell
Copy-Item .env.example .env
docker compose build
```

O `docker compose` inicia o servidor em Streamable HTTP na porta interna 8000,
pronto para receber conexões por um proxy reverso na rede Docker. Essa porta
não é publicada diretamente no host. Para uso local com um cliente que inicia
um processo, mantenha `MCP_TRANSPORT=stdio` e execute:

```powershell
docker compose run --rm -T glpi-mcp
```

Configure o cliente MCP local para iniciar `docker run --rm -i --env-file
<caminho-para-.env> glpi-mcp:local`. O `.env` é excluído do contexto da imagem
e não é incorporado no build. Não publique credenciais no arquivo de imagem.

Para um cliente remoto, use o endpoint `/mcp` via HTTPS. Não exponha o MCP
publicamente sem autenticação: TLS criptografa o tráfego, mas não controla
quem pode chamar as ferramentas.

## Ferramentas

- `glpi_search(itemtype, criteria, limit)`: usa a API Search legada. `criteria`
  aceita parâmetros de busca no formato GLPI, e `limit` é limitado a 100.
- `glpi_get_item(itemtype, item_id)`: consulta por tipo e ID.
- `glpi_create_ticket(name, content, urgency, ...)`: cria um chamado.
- `glpi_update_ticket(ticket_id, fields)`: atualiza campos de um chamado.

Cada chamada abre uma sessão GLPI e a encerra ao terminar. Configure a API
REST e conceda à conta apenas as permissões necessárias. A API REST v2 de
instalações GLPI recentes usa OAuth2; esta implementação mira a API legada
`apirest.php`, que continua disponível em muitas instalações. Consulte a
documentação da API da sua versão antes de definir `GLPI_API_PATH`.
