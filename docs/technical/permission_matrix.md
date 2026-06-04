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
