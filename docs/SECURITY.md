# Segurança

Este documento reúne controles recomendados para implantação e operação segura do GLPI-MCP.

## Princípios

- Privilégio mínimo para contas GLPI e identidade.
- Segredos fora do controle de versão.
- HTTPS em toda comunicação remota.
- Autenticação obrigatória no endpoint remoto.
- Scopes separados de leitura e escrita.
- Containers e redes com exposição mínima.
- Atualizações, monitoramento, backups e rotação de credenciais.

## Credenciais GLPI

- Utilize conta de integração dedicada e com permissões mínimas.
- Prefira User Token quando adequado.
- Proteja App-Token e User Token.
- Mantenha validação TLS habilitada.
- Rotacione credenciais conforme processo controlado.

## Segredos

- Não versionar `.env`, tokens, senhas, client secrets, chaves privadas ou dumps.
- Versionar somente exemplos com placeholders.
- Use secrets manager quando disponível.
- Restrinja permissões do arquivo de ambiente no host.

O `.env` contém também as credenciais bootstrap do Keycloak e senha do banco. Utilize valores fortes e únicos, proteja o arquivo e não o compartilhe.

## OIDC/JWT

- Configure issuer, JWKS e audience com endpoints HTTPS confiáveis.
- Use access tokens para chamadas MCP.
- Valide assinatura, issuer, audience, expiração e scopes.
- Não desabilite validações para contornar falhas.
- Scopes OAuth não substituem permissões GLPI.

## Rede e proxy

- Publique somente o proxy HTTPS.
- Não exponha diretamente as portas 8000, 8080 ou 5432.
- Restrinja SSH.
- PostgreSQL fica em rede interna Docker, sem acesso do proxy.
- Keycloak participa da rede interna do banco e da rede do proxy; o proxy encaminha ao serviço na porta 8080.
- GLPI-MCP não recebe porta publicada no host.
- Mantenha DNS, TLS e proxy corretamente configurados.

O hostname público de identidade encaminha para o Keycloak e inclui o console administrativo, que exige autenticação. Se a política da instalação exigir restrição adicional ao console, aplique controles de acesso no proxy ou na rede administrativa, validando que endpoints OIDC públicos necessários continuem acessíveis.

## Containers e hardening

O Compose fornece controles para GLPI-MCP:

- Filesystem read-only e `tmpfs` para temporários.
- Capabilities removidas e `no-new-privileges`.
- Healthcheck TCP (não é verificação completa do protocolo MCP).
- Limites de CPU e memória de referência.
- Rotação de logs Docker.

Keycloak e PostgreSQL têm limites de recursos e logs rotacionados. O banco usa rede Docker interna e volume persistente. Avalie limites de recursos conforme a carga e o tamanho da VPS.

## Dados e logs

- Não registre tokens, senhas ou client secrets.
- Evite registrar conteúdo de chamados e dados pessoais.
- Restrinja acesso e retenção de logs.
- Redija dados sensíveis antes de compartilhar logs.

## Verificações pós-deploy

1. Requisição sem token é recusada.
2. Token inválido/expirado é recusado.
3. Issuer e audience incorretos são recusados.
4. Scope ausente bloqueia ferramenta.
5. Scopes válidos permitem somente ações autorizadas.
6. Porta 8000 não está acessível externamente.
7. Portas 8080 e 5432 não estão publicadas.
8. TLS válido nos hostnames MCP e identidade.
9. Backups de PostgreSQL e volumes Caddy estão configurados e restauração testada.

## Incidentes e rotação

Credencial exposta deve ser considerada comprometida. Revogue/rotacione, atualize serviços, investigue uso, remova segredos do histórico quando aplicável e verifique acessos. Não reutilize credenciais comprometidas.
