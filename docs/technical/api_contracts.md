# api_contracts.md

## Base

`/api/v1`

## Grupos

Auth, Organizations, Users, Plans, Packages, Usage, Documents, Processing Jobs, Occurrences, Review, Templates, Audit, Monitoring e Settings.

## Contratos centrais

POST `/auth/login`.
GET `/auth/me`.
POST `/documents/upload`.
GET `/occurrences`.
GET `/occurrences/{occurrence_id}`.
GET `/occurrences/{occurrence_id}/fields`.
PATCH `/occurrences/{occurrence_id}/fields/{field_id}`.
POST `/occurrences/{occurrence_id}/approve`.
POST `/occurrences/{occurrence_id}/templates/generate`.
GET `/audit-logs`.

## Regras

1. Endpoints privados exigem bearer token.
2. Endpoints operacionais exigem `X-Organization-Id`.
3. Respostas de erro têm `code`, `message`, `details` e `request_id`.
4. Listas são paginadas.
5. Dados sensíveis vêm mascarados conforme permissão.
