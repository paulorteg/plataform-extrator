# PRD 08: Modelo de Dados

## Entidades centrais

1. organizations
2. users
3. user_organizations
4. roles
5. permissions
6. plans
7. packages
8. subscriptions
9. usage_events
10. documents
11. document_pages
12. processing_jobs
13. occurrences
14. extracted_fields
15. evidences
16. validation_issues
17. review_versions
18. generated_reports
19. audit_logs
20. model_calls

## Regras

1. Toda entidade operacional tem organization_id.
2. Índices devem considerar organization_id.
3. canonical_data pode ser JSONB validado por schema.
4. extracted_fields devem facilitar lista, busca e revisão.
5. Audit Log é somente aditivo.

## Critérios de aceite

1. Migrations criadas.
2. Seeds idempotentes.
3. Isolamento por organização testado.
4. Campos sensíveis não são expostos indevidamente.
