# Conectar o Claude ao GLPI-MCP remoto

Este guia explica como conectar um cliente Claude a uma instância GLPI-MCP hospedada em uma VPS. Antes de configurar o Claude, conclua o [guia de implantação em VPS](deployment.md).

## 1. O que precisa estar pronto

- GLPI-MCP em execução na VPS.
- Endpoint público com certificado HTTPS válido, por exemplo `https://mcp.exemplo.com/mcp`.
- Provedor OAuth/OIDC configurado e acessível por HTTPS.
- Access tokens JWT com issuer, audience, expiração e escopos compatíveis.
- Provedor configurado para o fluxo OAuth esperado pelo cliente Claude, incluindo descoberta/registro de cliente quando aplicável.
- Usuário autorizado no provedor para obter os escopos necessários.

O GLPI-MCP não realiza o login do usuário, não emite tokens e não armazena contas individuais do Claude. O login ocorre no provedor de identidade. O GLPI-MCP recebe e valida o access token apresentado pelo cliente.

## 2. Entender o fluxo de autenticação

1. O usuário adiciona o endpoint remoto no Claude.
2. O Claude inicia o fluxo OAuth com o servidor de autorização configurado.
3. O usuário autentica-se no provedor e autoriza o acesso solicitado.
4. O provedor emite um access token JWT.
5. O Claude envia solicitações MCP com esse token para o endpoint HTTPS.
6. O GLPI-MCP valida assinatura, issuer, audience, expiração e escopos.
7. Se o token for válido e tiver o escopo exigido, a ferramenta é executada usando a conta técnica GLPI configurada na VPS.

Não confunda access token com ID token. O GLPI-MCP espera um **access token JWT** destinado à audiência configurada em `OIDC_AUDIENCE`.

## 3. Escopos disponíveis

| Escopo | Ferramentas | Permissão |
|---|---|---|
| `glpi:read` | `glpi_search`, `glpi_get_item` | Pesquisa e consulta. |
| `glpi:write` | `glpi_create_ticket`, `glpi_update_ticket` | Criação e atualização; também exige `glpi:read`. |

Conceda somente os escopos necessários. Além dos escopos, a conta técnica GLPI precisa ter as permissões correspondentes.

## 4. Cadastrar o conector remoto no Claude

Os nomes e a disponibilidade das opções variam conforme o produto Claude, o plano e as políticas do workspace. Em termos gerais:

1. Abra as configurações de conectores ou integrações personalizadas do Claude.
2. Escolha adicionar um conector MCP remoto.
3. Informe o endpoint HTTPS completo, incluindo `/mcp`.
4. Selecione ou conclua a autenticação OAuth quando solicitada.
5. Faça login no provedor de identidade.
6. Autorize somente os escopos necessários.
7. Salve a conexão.
8. Abra uma conversa e confirme se as ferramentas GLPI aparecem disponíveis.

Endpoint de exemplo:

```text
https://mcp.exemplo.com/mcp
```

Não use o endereço HTTP sem TLS nem a porta interna 8000.

## 5. Validar com segurança

Comece com uma operação de leitura, por exemplo pesquisar um chamado conhecido. Verifique:

- O conector aparece como conectado.
- As quatro ferramentas são apresentadas pelo cliente.
- Uma consulta com `glpi:read` funciona.
- Uma operação de escrita só é permitida quando o token possui `glpi:write` e a conta GLPI tem a permissão necessária.

Teste criação e atualização em ambiente controlado, nunca em chamados de produção sem autorização.

## 6. Problemas comuns

| Sintoma | Causa provável / ação |
|---|---|
| Claude não conclui OAuth | Verifique descoberta de metadados, registro de cliente, redirect URI e compatibilidade do provedor com o fluxo esperado pelo Claude. |
| Endpoint inacessível | Verifique DNS, certificado, TCP 443, Caddy e o caminho `/mcp`. |
| HTTP 401 | Token ausente, expirado, assinatura inválida, issuer/audience incorretos ou token não é access token. |
| Ferramentas de leitura funcionam, escrita falha | O token não tem `glpi:write` ou a conta técnica não tem permissão no GLPI. |
| Ferramentas não aparecem | Confira endpoint, transporte Streamable HTTP, logs do GLPI-MCP e compatibilidade do cliente. |

Logs na VPS:

```bash
docker compose logs --tail 100 glpi-mcp caddy
```

## 7. Limites e compatibilidade

O GLPI-MCP implementa validação de bearer access tokens JWT via JWKS e autorização por escopos. Isso não significa que ele implemente um servidor de autorização completo. Login, consentimento, emissão de tokens, cadastro de usuários e registro do cliente são responsabilidades do provedor OAuth/OIDC e do cliente MCP.

A configuração correta de `OIDC_ISSUER_URL`, `OIDC_JWKS_URL` e `OIDC_AUDIENCE` é necessária, mas não garante por si só que o Claude consiga completar a negociação OAuth. Valide o fluxo ponta a ponta com o provedor e a versão do Claude que serão usados antes de colocar o serviço em produção.

## 8. Claude Desktop local

Se o Claude Desktop e o GLPI-MCP estiverem na mesma máquina, a alternativa mais simples é executar localmente por `stdio`. Nesse caso:

- Não é necessário publicar domínio nem configurar Caddy.
- Não é necessário abrir portas de entrada.
- O Claude inicia o processo GLPI-MCP localmente.
- As credenciais GLPI ficam na máquina que executa o servidor.

Consulte a seção de configuração local do [README](../README.md).
