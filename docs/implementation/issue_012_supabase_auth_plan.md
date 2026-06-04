# Issue 012: Plano de login com Supabase Auth

## Objetivo

Planejar a adaptação da Issue 012 para Supabase First.

Esta issue futura não deve criar login próprio na FastAPI. Supabase Auth será responsável por login, senha, recuperação de senha, sessão e emissão de tokens.

## Fluxo frontend futuro

1. O frontend usará `NEXT_PUBLIC_SUPABASE_URL` e `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
2. O login será feito com o cliente Supabase no browser.
3. Recuperação de senha e sessão também serão geridas pelo Supabase Auth.
4. Após login, o frontend manterá a sessão conforme SDK do Supabase.
5. Chamadas para APIs privadas enviarão `Authorization: Bearer <access_token>`.

## Fluxo na API

1. A FastAPI receberá o JWT no header `Authorization`.
2. A API não receberá senha.
3. A API não terá endpoint próprio de autenticação com credenciais.
4. A API validará o JWT em issue futura de middleware.
5. Depois da validação, o `sub` do token será usado como `users.auth_user_id`.

## Mapeamento de usuário

1. Supabase Auth mantém o usuário em `auth.users`.
2. A aplicação mantém o usuário interno em `users`.
3. `users.auth_user_id` deve corresponder ao `sub` do JWT Supabase.
4. Usuário autenticado sem registro interno deve ser bloqueado ou encaminhado a fluxo de provisionamento definido em issue futura.
5. Permissões internas serão resolvidas via `user_organizations`, `roles`, `permissions` e `role_permissions`.

## Riscos

1. Expor `SUPABASE_SERVICE_ROLE_KEY` no frontend.
2. Logar `Authorization` header ou token.
3. Implementar login paralelo na FastAPI por engano.
4. Aceitar token sem validação de assinatura, issuer, audience e expiração.
5. Confiar em `user_metadata` para autorização de negócio.
6. Permitir usuário Supabase sem usuário interno ativo.

## Testes necessários

1. Frontend usa apenas variáveis `NEXT_PUBLIC_*`.
2. Nenhum endpoint backend recebe senha.
3. Chamadas privadas enviam bearer token.
4. Tokens não aparecem em logs.
5. Erros preservam `request_id`.
6. Usuário sem vínculo interno não recebe acesso operacional.

## Arquivos prováveis na implementação futura

1. `apps/web` para cliente Supabase e telas/fluxos de login.
2. `apps/api/app/core/config.py` para leitura segura de configuração JWT, se necessário.
3. `apps/api/app/middleware` para validação futura do token.
4. `apps/api/tests` para cobrir ausência de login próprio e envio de bearer token.

## Fora do escopo deste plano

1. Implementar login.
2. Implementar middleware JWT.
3. Implementar `/auth/me`.
4. Criar RLS.
5. Criar endpoint de senha ou recuperação de senha.
