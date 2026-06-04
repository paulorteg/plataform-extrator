# Issue 013: Plano do endpoint /auth/me

## Objetivo

Planejar o endpoint `/auth/me` adaptado para Supabase First.

O endpoint deve retornar o contexto interno do usuário autenticado: usuário interno, organizações vinculadas, papéis e permissões por organização.

## Resolução do usuário interno

1. O middleware JWT futuro validará o token Supabase.
2. O `sub` validado do token será tratado como `auth_user_id`.
3. A API buscará `users.auth_user_id = sub`.
4. Usuário interno inexistente deve receber erro controlado.
5. Usuário interno com `status` diferente de `active` deve ser bloqueado.

## Organizações do usuário

1. A API buscará vínculos em `user_organizations`.
2. Apenas vínculos ativos devem ser retornados.
3. Cada vínculo deve incluir `organization_id`.
4. Dados da organização devem vir de `organizations`.
5. Organização inativa não deve aparecer como selecionável.

## Papéis e permissões

1. Cada vínculo ativo pode apontar para `role_id`.
2. O papel deve vir de `roles`.
3. Permissões devem vir de `role_permissions` e `permissions`.
4. Permissões devem ser retornadas por organização, não como acesso global implícito.
5. Nenhuma permissão deve ser inferida sem registro em `permissions`.

## Dados que não podem ser retornados

1. Token JWT.
2. Refresh token.
3. `SUPABASE_SERVICE_ROLE_KEY`.
4. `SUPABASE_JWT_SECRET`.
5. Senha, hash de senha ou qualquer credencial.
6. Dados sensíveis de documentos, OCR, BO ou URLs temporárias.
7. Permissões de organização sem vínculo ativo.

## Testes necessários

1. Retorna usuário interno ativo a partir de `auth_user_id`.
2. Bloqueia usuário interno inexistente.
3. Bloqueia usuário interno inativo.
4. Retorna apenas organizações ativas e vínculos ativos.
5. Retorna papéis e permissões por organização.
6. Não retorna tokens, segredos ou dados sensíveis.
7. Preserva `request_id` em erros.
8. Não loga `Authorization` header.

## Dependências

1. Middleware JWT da Issue 014 adaptada.
2. Modelos de usuários e organizações da Issue 009.
3. Modelos e seeds de papéis e permissões da Issue 010.
4. Permission Guard da Issue 016 para ações protegidas posteriores.
5. Middleware de organização da Issue 015 para rotas operacionais posteriores.

## Fora do escopo deste plano

1. Implementar `/auth/me`.
2. Implementar JWT middleware.
3. Implementar Permission Guard.
4. Criar RLS.
5. Criar endpoint de login.
