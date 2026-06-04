# PRD 07: Arquitetura Técnica

## Decisão base

Monólito modular no MVP com frontend Next.js, backend FastAPI, PostgreSQL, Redis, workers e storage S3 compatível.

## Componentes

1. Web app
2. API
3. Worker
4. PostgreSQL
5. Redis
6. Storage privado
7. OCR Provider Interface
8. LLM Gateway
9. Audit Log Service
10. Usage Service

## Princípios

1. API REST versionada.
2. Workers para tarefas pesadas.
3. OCR desacoplado por interface.
4. LLM centralizado por gateway.
5. Modelo Canônico antes do template.
6. Mapping declarativo.
7. Observabilidade desde o MVP.

## Critérios de aceite

1. Infra local sobe com Docker Compose.
2. API tem health check.
3. Worker processa job básico.
4. Banco tem migrations.
5. Storage privado funcionando.
