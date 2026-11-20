# Segurança

Este documento reúne controles recomendados para instalar, configurar e operar o GLPI-MCP com segurança.

## Princípios

- Privilégio mínimo para a conta técnica do GLPI e para usuários do provedor de identidade.
- Segredos fora do controle de versão.
- HTTPS em toda comunicação remota.
- Autenticação obrigatória no endpoint remoto.
- Autorização por scopes, além das permissões internas do GLPI.
- Containers e redes com exposição mínima.
- Atualizações, monitoramento e rotação de credenciais.

## Credenciais do GLPI

- Utilize uma conta de integração dedicada.
- Conceda apenas as permissões necessárias às ferramentas MCP.
- Prefira User Token em vez de senha, quando disponível e adequado.
- Mantenha App-Token e User Token protegidos.
- Habilite validação TLS (`GLPI_VERIFY_TLS=true`) em produção.
- Rotacione tokens seguindo processo controlado e atualize os serviços dependentes.

## Segredos e repositório

- Não versionar `.env`, tokens, senhas, client secrets, chaves privadas ou dumps de dados.
- Versionar apenas arquivos de exemplo com placeholders, como `.env.example`.
- Não inserir segredos em documentação, screenshots, logs, issues ou PRs.
- Use armazenamento de segredos da plataforma/infraestrutura quando disponível.
- Limite permissões de leitura do arquivo de ambiente no host.

## OIDC, JWT e scopes

Na implantação remota:

- Configure issuer, JWKS e audience usando endpoints HTTPS confiáveis.
- Use access tokens, não ID tokens, para chamadas ao recurso MCP.
- O servidor valida a assinatura do JWT, issuer, audience, expiração e scopes.
- Use scopes de leitura e escrita separados.
- Operações de escrita exigem scopes apropriados e não devem ser liberadas apenas por autenticação.
- A autorização OAuth não substitui a autorização dentro do GLPI.

Não aceite tokens de emissores não confiáveis ou tokens com audience diferente do recurso. Não desabilite verificações para contornar erros de configuração.

## Rede e proxy

- Publique somente o proxy HTTPS.
- Não exponha diretamente a porta MCP 8000.
- Restrinja SSH ao conjunto de IPs de administração sempre que possível.
- Não exponha o banco de dados ou interfaces administrativas do Keycloak à Internet.
- Use redes Docker separadas e comunicação interna entre serviços.
- Configure o proxy para encaminhar apenas aos upstreams necessários.
- Mantenha TLS e certificados válidos.

## Containers

A configuração de Compose do projeto usa controles de hardening para o serviço MCP, como filesystem read-only, tmpfs para temporários, remoção de capabilities e `no-new-privileges`. Não remova essas opções sem avaliar a necessidade.

Evite montar diretórios do host com acesso amplo no container. Utilize imagens atualizadas e versões confiáveis.

## Logs e informações sensíveis

- Não registre bearer tokens, senhas ou client secrets.
- Evite logs de conteúdo de chamados que possa conter dados pessoais ou confidenciais.
- Restrinja acesso aos logs e defina retenção adequada.
- Ao compartilhar logs para diagnóstico, remova tokens, URLs privadas e dados identificáveis.

## Testes de segurança básicos

Após implantação:

1. Requisição sem token deve ser rejeitada.
2. Token inválido deve ser rejeitado.
3. Token expirado deve ser rejeitado.
4. Token com issuer incorreto deve ser rejeitado.
5. Token com audience incorreta deve ser rejeitado.
6. Usuário sem scope de leitura não deve executar consultas.
7. Usuário sem scope de escrita não deve executar operações de alteração.
8. Token com scopes válidos deve permitir somente as ações autorizadas.
9. Confirme que a porta MCP não está diretamente acessível externamente.
10. Confirme que certificados HTTPS estão válidos.

## Incidentes e rotação

Se uma credencial for exposta, considere-a comprometida: revogue ou rotacione imediatamente, atualize o serviço, investigue o uso, remova o segredo do histórico quando aplicável e verifique acessos. Não reutilize credenciais comprometidas.
