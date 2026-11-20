# Conectar o GLPI-MCP ao Claude

Este guia configura um conector MCP remoto no Claude usando o Keycloak já implantado com o GLPI-MCP.

## Por que usar um cliente OAuth pré-registrado?

O GLPI-MCP valida tokens emitidos pelo Keycloak, mas não é responsável por registrar clientes OAuth. O registro automático depende do endpoint e das políticas de registro do servidor de autorização; ele pode falhar quando o Keycloak exige autorização para registrar novos clientes.

Para uma conexão Claude com um client OAuth pré-registrado, não habilite registro anônimo de clientes no Keycloak apenas para evitar essa configuração. O cliente Claude será criado manualmente no realm e suas credenciais serão informadas no conector.

## 1. Criar um cliente OAuth no Keycloak

1. Acesse o console administrativo do Keycloak.
2. Selecione o realm `glpi-mcp`.
3. Abra **Clients** e clique **Create client**.
4. Selecione **OpenID Connect** e avance.
5. Defina o Client ID como `claude-glpi-mcp`.
6. Habilite **Client authentication** (cliente confidencial) e **Standard flow**.
7. Salve o cliente.

## 2. Configurar o redirect URI

Em **Clients > claude-glpi-mcp > Settings**, configure o URI de redirecionamento permitido:

```
https://claude.ai/api/mcp/auth_callback
```

Adicione apenas o URI de callback necessário para o cliente Claude que está sendo usado. Não use wildcard (`*`) nos redirect URIs. Se outro produto/superfície Claude fornecer um callback diferente, registre o URI oficial indicado para essa superfície.

## 3. Configurar scopes

O GLPI-MCP usa scopes separados para operações:

- `glpi:read`: pesquisa e consulta.
- `glpi:write`: criação e atualização de chamados.

No realm, crie ou confirme os client scopes OpenID Connect com esses nomes e associe-os ao cliente `claude-glpi-mcp` conforme o fluxo de autorização. Garanta que o access token emitido contenha os scopes solicitados no claim `scope` (ou `scp`, se estiver usando formato de array).

Para o primeiro teste, conceda somente `glpi:read`. Adicione `glpi:write` somente se o conector precisar criar ou atualizar chamados.

Mantenha o Audience Mapper já documentado neste guia: o access token deve incluir a audience `glpi-mcp`.

## 4. Obter as credenciais

Em **Clients > claude-glpi-mcp > Credentials**, copie:

- **Client ID**: `claude-glpi-mcp`.
- **Client Secret**: o secret gerado para o cliente.

Guarde o secret com segurança. Não o inclua no repositório, em arquivos versionados ou em capturas de tela.

## 5. Adicionar o conector no Claude

1. Abra **Customize > Connectors** (ou a seção Conectores da sua versão).
2. Clique em **Add custom connector**.
3. Nome: `GLPI-MCP`.
4. URL do servidor: `https://mcp.example.com/mcp` — substitua pelo hostname MCP da sua implantação.
5. Avance e mantenha autenticação OAuth habilitada.
6. Em **OAuth client**, selecione **Use your own OAuth client** / **Usar seu próprio cliente OAuth**.
7. Informe o Client ID `claude-glpi-mcp` e o Client Secret copiado do Keycloak.
8. Não preencha Request headers.
9. Adicione o conector.

Não selecione **Register automatically** quando estiver usando o cliente pré-registrado. Não selecione **No login**, pois o GLPI-MCP exige autenticação OAuth.

## 6. Conectar e validar

1. Na lista de conectores, clique em **Connect**.
2. Autentique no Keycloak.
3. Revise e autorize as permissões solicitadas.
4. Retorne ao Claude e habilite o conector na conversa.
5. Solicite a listagem de ferramentas e teste uma consulta de leitura, por exemplo: `Liste os 5 chamados mais recentes`.

Confirme também que a conta técnica configurada no GLPI possui apenas as permissões necessárias. O OAuth do Keycloak e os scopes do GLPI-MCP não substituem as permissões da conta técnica GLPI.

## Solução de problemas

- **Falha ao registrar o cliente:** confirme que o conector está usando **Use your own OAuth client**, e não **Register automatically**.
- **Redirect URI inválido:** compare o callback informado pelo Claude com a lista de redirect URIs permitidos no Keycloak; a correspondência deve ser exata.
- **Login funciona, mas o token é recusado:** confira issuer, JWKS URL, audience `glpi-mcp`, validade do token e scopes.
- **Ferramentas de leitura recusadas:** confirme que o access token contém `glpi:read`.
- **Ferramentas de escrita recusadas:** confirme que o token contém `glpi:write` e que a conta técnica GLPI tem permissões para a operação.

## Referências

- [Configuração do Keycloak](KEYCLOAK.md)
- [Implantação em VPS](DEPLOYMENT.md)
- [README](../README.md)
- [Documentação oficial do Claude: conectores MCP remotos](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp)
