# Issue 014: Plano do middleware JWT Supabase

## Objetivo

Planejar o middleware de autenticação da FastAPI usando JWT emitido pelo Supabase Auth.

A API não deve implementar login próprio, senha própria, hash de senha ou recuperação de senha.

## Validação do JWT

1. Ler `Authorization: Bearer <token>`.
2. Rejeitar header ausente, malformado ou com esquema diferente de `Bearer`.
3. Validar assinatura do JWT com configuração do Supabase.
4. Validar expiração.
5. Validar issuer e audience conforme configuração do projeto.
6. Não aceitar token sem `sub`.
7. Não logar token, header `Authorization` ou payload completo.

## Extração do sub

1. Após validação criptográfica, extrair `sub`.
2. Tratar `sub` como `auth_user_id`.
3. Não usar email ou metadata como identidade primária.
4. Não usar `user_metadata` para autorização.

## Resolução do usuário interno

1. Buscar `users.auth_user_id = sub`.
2. Bloquear usuário interno inexistente.
3. Bloquear usuário com `status` diferente de `active`.
4. Anexar contexto autenticado ao `request.state` ou dependência equivalente.
5. Resolver papéis/permissões apenas em etapas próprias, não dentro de lógica ampla não testada.

## Erros esperados

1. Token ausente: `401`.
2. Token inválido: `401`.
3. Token expirado: `401`.
4. Usuário interno inexistente: `403` ou `401`, conforme decisão futura.
5. Usuário interno inativo: `403`.
6. Todos os erros devem incluir ou preservar `X-Request-Id`.
7. Payload de erro deve evitar detalhes sensíveis.

## Logs seguros

1. Não logar body da request.
2. Não logar header `Authorization`.
3. Não logar token.
4. Não logar payload completo do JWT.
5. Logar apenas metadados técnicos mínimos, como `request_id`, rota, status e tipo genérico de erro.

## Testes necessários

1. Rejeita request sem bearer token.
2. Rejeita header malformado.
3. Rejeita token inválido.
4. Rejeita token expirado.
5. Rejeita token sem `sub`.
6. Resolve usuário interno por `auth_user_id`.
7. Bloqueia usuário interno inativo.
8. Preserva `request_id` em sucesso e erro.
9. Não registra `Authorization` header nem token em logs.
10. Não implementa login ou senha na API.

## Riscos de segurança

1. Usar `SUPABASE_SERVICE_ROLE_KEY` para validar usuário em rota pública.
2. Confiar em token sem validar assinatura.
3. Ignorar expiração.
4. Confiar em `user_metadata` para autorização.
5. Vazar token em log, exceção ou tracing.
6. Criar bypass para usuário interno inexistente.
7. Confundir autenticação com permissão e organização ativa.

## Arquivos prováveis na implementação futura

1. `apps/api/app/middleware`.
2. `apps/api/app/core/config.py`.
3. `apps/api/app/api_errors.py`.
4. `apps/api/app/main.py`.
5. `apps/api/tests`.

## Fora do escopo deste plano

1. Implementar middleware JWT.
2. Implementar `/auth/me`.
3. Implementar Permission Guard.
4. Implementar middleware de organização.
5. Criar RLS.
