# PRD 10: Testes Automatizados

## Objetivo

Garantir segurança, qualidade, precisão, regressão documental e estabilidade do pipeline.

## Camadas de teste

1. Unitários
2. Integração
3. Contrato de API
4. Segurança e permissões
5. Pipeline documental
6. Regressão de fixtures
7. Frontend
8. End to end

## Testes obrigatórios

1. Autenticação
2. Organization_id
3. Permissões
4. Upload
5. Storage
6. Jobs
7. OCR Provider
8. LLM Gateway
9. Validadores
10. Mapping
11. Revisão
12. Consumo idempotente
13. Auditoria
14. Mascaramento
15. Template apenas aprovado

## Critérios de aceite

1. Testes críticos rodam em CI.
2. Regressão rápida roda em PR.
3. Regressão completa roda antes de deploy.
4. Campo inventado é falha crítica.
