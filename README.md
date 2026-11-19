# GLPI MCP Server

Servidor MCP em Python que conecta clientes e assistentes de IA à API REST legada do GLPI (`apirest.php`). O projeto permite pesquisar registros, consultar itens e criar ou atualizar chamados usando as permissões de uma conta técnica configurada no GLPI.

O GLPI-MCP pode ser executado localmente, iniciado pelo cliente MCP via `stdio`, ou hospedado em uma VPS e disponibilizado remotamente por HTTPS.

## Índice

- [Visão geral e funcionamento](#visão-geral-e-funcionamento)
- [Ferramentas disponíveis](#ferramentas-disponíveis)
- [Escolher o modo de execução](#escolher-o-modo-de-execução)
- [Requisitos](#requisitos)
- [Preparar o GLPI](#preparar-o-glpi)
- [Executar localmente](#executar-localmente)
- [Implantar em uma VPS com HTTPS](#implantar-em-uma-vps-com-https)
- [Portas e conectividade](#portas-e-conectividade)
- [Conectar o Claude](#conectar-o-claude)
- [Testes e manutenção](#testes-e-manutenção)
- [Solução de problemas](#solução-de-problemas)
- [Segurança](#segurança)

## Visão geral e funcionamento

O GLPI-MCP é uma camada intermediária entre um cliente compatível com MCP e o GLPI. O assistente não acessa diretamente o banco de dados nem recebe as credenciais administrativas do GLPI: ele solicita uma ferramenta ao servidor MCP, e o servidor executa a operação pela API REST.

### Fluxo de uma operação

1. O usuário pede algo ao assistente, por exemplo: consultar um chamado.
2. O cliente MCP identifica que deve chamar uma ferramenta do GLPI-MCP.
3. O GLPI-MCP recebe a chamada pelo transporte configurado (`stdio` ou `Streamable HTTP`).
4. No modo remoto, o servidor valida o access token JWT e os escopos OAuth exigidos.
5. O servidor valida os parâmetros e verifica se a operação é permitida.
6. O cliente interno chama a API REST do GLPI usando os tokens da conta técnica configurada no servidor.
7. O GLPI aplica as permissões dessa conta e devolve o resultado.
8. O GLPI-MCP retorna o resultado ao cliente MCP, que o apresenta ao usuário.

### Arquitetura local

```text
Claude Desktop ou outro cliente MCP
              |
          stdio local
              |
          GLPI-MCP
              |
       API REST do GLPI
```

Nesse modo, o cliente inicia o processo GLPI-MCP na própria máquina. Não existe endpoint público, proxy ou porta de entrada para o MCP.

### Arquitetura remota em VPS

```text
Claude / cliente MCP
        |
        | HTTPS (TCP 443) + access token
        v
   Internet / DNS
        |
        v
   Caddy na VPS
   TLS automático
        |
        | rede Docker privada
        v
   GLPI-MCP (porta 8000 interna)
        |
        | HTTPS de saída
        v
   API REST do GLPI

GLPI-MCP também consulta o provedor OIDC/JWKS
para validar os access tokens recebidos.
```

- **Caddy** recebe o tráfego público, termina o TLS e encaminha as requisições.
- **GLPI-MCP** processa o protocolo MCP, valida tokens e executa as ferramentas.
- **Provedor OAuth/OIDC externo** autentica os usuários e emite access tokens. Pode ser um serviço gerenciado ou uma instalação própria, por exemplo Keycloak.
- **GLPI** continua sendo a fonte de dados e a camada final de permissões.

> **Atenção:** HTTPS protege o tráfego, mas não autentica o usuário. O GLPI-MCP atua como *resource server*: valida tokens emitidos pelo provedor externo, mas não hospeda login, não emite tokens e não substitui o provedor de identidade.

## Ferramentas disponíveis

| Ferramenta | O que faz | Acesso remoto |
|---|---|---|
| `glpi_search` | Pesquisa registros por tipo de item, critérios e limite de resultados (máximo 100). | `glpi:read` |
| `glpi_get_item` | Consulta um registro pelo tipo e ID. | `glpi:read` |
| `glpi_create_ticket` | Cria um chamado com título, conteúdo, urgência e referências opcionais. | `glpi:read` e `glpi:write` |
| `glpi_update_ticket` | Atualiza campos permitidos de um chamado existente. | `glpi:read` e `glpi:write` |

A conta técnica do GLPI também precisa ter permissão para executar a operação. Os escopos OAuth não concedem permissões dentro do GLPI.

## Escolher o modo de execução

| Cenário | Modo | Quando usar |
|---|---|---|
| Claude Desktop na mesma máquina do servidor | `stdio` | Uso individual e local, sem publicar serviço na Internet. |
| Desenvolvimento | `stdio` | Execução simples pelo terminal ou cliente MCP. |
| VPS para acesso remoto | `streamable-http` + HTTPS | Quando o cliente está em outro computador ou rede. |
| Instalação central para vários usuários | `streamable-http` + HTTPS + OIDC | Quando a organização precisa centralizar a operação e controlar acessos. |

Os dois modos disponibilizam as mesmas ferramentas. A diferença é o transporte e a forma de autenticação.

## Requisitos

### Execução local
- Python 3.11 ou superior, ou Docker.
- Acesso de rede à instância GLPI.
- API REST legada habilitada no GLPI.

### Execução em VPS
- VPS Linux com Docker Engine e Docker Compose v2.
- Domínio ou subdomínio apontando para o IP público da VPS.
- Portas TCP 80 e 443 liberadas para entrada.
- Instância GLPI acessível pela VPS.
- Provedor OAuth/OIDC que emita access tokens JWT assinados e publique as chaves JWKS.
- Cliente MCP que suporte o fluxo de autenticação remota exigido pelo servidor de autorização.

## Preparar o GLPI

1. Acesse o GLPI com uma conta administradora.
2. Habilite a API REST legada nas configurações da instalação.
3. Gere um App-Token, quando exigido pela configuração da API.
4. Gere um User Token para uma conta técnica dedicada ou configure usuário e senha exclusivos para a integração.
5. Conceda à conta técnica somente as permissões necessárias para pesquisar, consultar e gerenciar chamados.
6. Confirme que a VPS ou máquina local consegue acessar a URL do GLPI.

Use a URL base, por exemplo `https://glpi.suaempresa.com`, sem acrescentar `/apirest.php` em `GLPI_URL`. O caminho da API é configurado separadamente.

## Executar localmente

### 1. Baixar o projeto

```bash
git clone https://github.com/efssantos/glpi-mcp.git
cd glpi-mcp
```

### 2. Criar o ambiente Python

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configurar as credenciais

Crie o arquivo `.env` com os dados da sua instância:

```dotenv
GLPI_URL=https://glpi.suaempresa.com
GLPI_API_PATH=/apirest.php
GLPI_APP_TOKEN=SEU_APP_TOKEN
GLPI_USER_TOKEN=SEU_USER_TOKEN
GLPI_TIMEOUT=30
GLPI_VERIFY_TLS=true
MCP_TRANSPORT=stdio
MCP_HOST=127.0.0.1
MCP_PROXY_MODE=false
MCP_AUTH_ENABLED=false
MCP_PORT=8000
LOG_LEVEL=INFO
```

Também é possível usar `GLPI_USERNAME` e `GLPI_PASSWORD` no lugar de `GLPI_USER_TOKEN`. Não configure simultaneamente métodos desnecessários.

### 4. Iniciar e conectar o cliente

Para validar manualmente:

```bash
python -m server
```

Em produção local, normalmente o próprio Claude Desktop inicia o processo. Configure o cliente com o executável Python do ambiente virtual, o argumento `-m server`, o diretório do repositório e as variáveis de ambiente acima. Exemplo de configuração está disponível na seção [Conectar o Claude](#conectar-o-claude).

## Implantar em uma VPS com HTTPS

O passo a passo completo, incluindo preparação do provedor OIDC, DNS, firewall, configuração do `.env`, inicialização, validação e manutenção, está em **[Guia de implantação em VPS](docs/deployment.md)**.

Resumo do processo:

1. Preparar a VPS Linux e instalar Docker Engine + Compose v2.
2. Apontar um domínio para o IP da VPS.
3. Configurar um provedor OAuth/OIDC para autenticar os usuários e emitir access tokens.
4. Clonar o projeto e preencher o `.env` com dados do GLPI, domínio e OIDC.
5. Liberar TCP 80/443 e iniciar `docker compose up -d --build`.
6. Validar o certificado HTTPS, a autenticação e a listagem de ferramentas MCP.
7. Cadastrar o endpoint `https://SEU-DOMINIO/mcp` no cliente MCP.

A imagem isolada do GLPI-MCP não fornece HTTPS. Na implantação remota, o Compose executa Caddy e GLPI-MCP juntos; somente Caddy publica portas no host.

## Portas e conectividade

| Porta | Direção | Uso |
|---|---|---|
| TCP 80 | Entrada pública na VPS | Validação de domínio/certificado Let's Encrypt e redirecionamento para HTTPS. |
| TCP 443 | Entrada pública na VPS | Endpoint MCP HTTPS. |
| UDP 443 | Entrada pública, opcional | HTTP/3 no Caddy. |
| TCP 8000 | Apenas rede Docker interna | Comunicação Caddy → GLPI-MCP. Não publicar no host nem liberar no firewall. |
| TCP 443 | Saída da VPS | Acesso HTTPS à API GLPI e ao provedor OIDC/JWKS, se esses serviços usarem HTTPS. |
| UDP/TCP 53 | Saída da VPS | Resolução DNS, normalmente já permitida pelo provedor. |

No modo local `stdio`, nenhuma porta de entrada precisa ser aberta. Na VPS, exponha somente TCP 80 e 443 (UDP 443 é opcional). A porta 8000 permanece privada.

## Conectar o Claude

### Claude Desktop local (stdio)

Configure o cliente para iniciar o processo Python local. Exemplo ilustrativo para Windows:

```json
{
  "mcpServers": {
    "glpi": {
      "command": "C:\\CAMINHO\\glpi-mcp\\.venv\\Scripts\\python.exe",
      "args": ["-m", "server"],
      "cwd": "C:\\CAMINHO\\glpi-mcp",
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

Use caminhos absolutos e não suponha que o cliente carregará automaticamente o arquivo `.env`.

### Claude remoto

Depois de concluir a implantação da VPS, cadastre um conector MCP remoto usando o endpoint HTTPS e conclua a autenticação OAuth oferecida pelo provedor de identidade. O procedimento detalhado e os requisitos de compatibilidade estão em [Integração com Claude remoto](docs/claude-integration.md).

A disponibilidade e os nomes dos menus do Claude podem variar por produto, plano e política do workspace. O suporte ao fluxo OAuth deve ser validado com o provedor escolhido antes de considerar a instalação pronta para produção.

## Testes e manutenção

Executar os testes automatizados:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Os testes usam mocks e não exigem uma instância GLPI real.

Com Docker Compose:

```bash
docker compose ps
docker compose logs --tail 100 glpi-mcp caddy
docker compose restart
docker compose pull
docker compose up -d
```

Faça backup dos volumes `caddy_data` e `caddy_config`, mantenha o sistema atualizado e planeje a rotação dos tokens GLPI e das chaves do provedor de identidade.

## Solução de problemas

| Sintoma | Verificações |
|---|---|
| GLPI retorna 401/403 | App-Token, User Token/credenciais, API habilitada e permissões da conta técnica. |
| VPS não obtém certificado | DNS A/AAAA, TCP 80/443 liberadas no firewall da VPS e do provedor, logs do Caddy. |
| Endpoint não responde | `docker compose ps`, logs de Caddy e GLPI-MCP, domínio e `MCP_DOMAIN`. |
| Token remoto rejeitado | Access token (não ID token), assinatura RS256/ES256, issuer, audience, expiração e URL JWKS. |
| Leitura funciona, escrita não | Escopos `glpi:write` e `glpi:read`, além das permissões da conta GLPI. |
| Cliente não lista ferramentas | Endpoint terminado em `/mcp`, compatibilidade do cliente com Streamable HTTP/OAuth e logs do servidor. |
| Erro de conexão com GLPI | DNS, rota de saída, firewall, URL base e disponibilidade de `/apirest.php`. |

## Segurança

- Use uma conta técnica GLPI dedicada e com menor privilégio.
- Nunca versione o arquivo `.env` ou compartilhe tokens e senhas.
- Mantenha `GLPI_VERIFY_TLS=true` em produção.
- Não publique a porta 8000 nem exponha diretamente o contêiner MCP.
- Na VPS, mantenha Caddy e GLPI-MCP em redes Docker privadas conforme o Compose.
- Habilite autenticação OIDC no modo remoto e conceda somente os escopos necessários.
- Proteja e faça backup dos volumes persistentes do Caddy.
- HTTPS cifra a conexão; OAuth autentica o cliente; escopos limitam ferramentas; as permissões GLPI continuam limitando as operações sobre os dados.

## Licença

Distribuído sob a licença MIT. Consulte [LICENSE](LICENSE).
