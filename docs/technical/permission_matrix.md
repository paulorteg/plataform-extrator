# permission_matrix.md

## Papéis

platform_owner, platform_admin, organization_admin, manager, analyst, auditor e viewer.

## Permissões principais

auth_login, organization_view, user_invite, user_role_change, plan_manage, package_assign, usage_view, document_upload, document_view, document_download, occurrence_list, occurrence_view, review_field_edit, review_field_approve, review_approve_occurrence, template_generate, template_download, sensitive_data_view, sensitive_data_copy, audit_view, audit_export.

## Regras

1. Backend valida tudo.
2. Frontend apenas oculta ações.
3. Admin global não acessa BO sensível por padrão.
4. Dados sensíveis têm permissão própria.
5. Permissão não substitui entitlement de plano.
6. Entitlement de plano não substitui permissão.

## Supabase Auth e autorização interna

No MVP, Supabase Auth autentica o usuário, mas não decide sozinho permissões de negócio.

1. Supabase Auth confirma identidade e emite JWT.
2. FastAPI valida o JWT em rotas privadas.
3. FastAPI resolve organização ativa, papel, permissões e entitlements internos.
4. Toda ação protegida continua validando permissão no backend.
5. A API não recebe senha de usuário no MVP.

## RLS e multiempresa

RLS no Supabase é camada adicional de segurança para isolamento por organização.

1. RLS não substitui `X-Organization-Id` em rotas operacionais.
2. RLS não substitui filtros por `organization_id` nas consultas da FastAPI.
3. RLS não substitui Permission Guard.
4. Políticas RLS devem reforçar isolamento, especialmente em tabelas multiempresa.
5. Service role deve ser usada somente no backend e nunca no frontend.

A estratégia inicial de RLS está documentada em `docs/technical/rls_strategy.md`.
