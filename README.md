# MercadoIA BO Platform

Plataforma empresarial para leitura, processamento, extração, revisão e geração de templates padronizados a partir de Boletins de Ocorrência e documentos relacionados a sinistros.

## Objetivo

Transformar documentos heterogêneos em dados estruturados, revisáveis, auditáveis e exportáveis, respeitando LGPD, controle de acesso, evidência por campo e baixo custo de uso de LLM.

## Estrutura do monorepo

```text
apps/
  api/       Backend FastAPI.
  web/       Frontend Next.js.
  worker/    Processamento assíncrono.
docs/
  prd/       Documentação de produto e arquitetura.
  technical/ Contratos, matrizes, decisões e backlog técnico.
infra/
  scripts/   Scripts de apoio para infraestrutura local.
packages/
  mappings/  Mapeamentos declarativos.
  schemas/   Schemas compartilhados.
```

## Stack base

Frontend: Next.js, React, TypeScript, Tailwind CSS e shadcn ui.

Backend: Python, FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis e workers assíncronos.

Processamento: OCR por provider interface, LLM por gateway interno, storage privado compatível com S3.

## Regras fundamentais

1. Toda rota privada exige autenticação.
2. Toda rota operacional exige organização ativa.
3. Toda consulta operacional filtra por `organization_id`.
4. Toda ação protegida valida permissão no backend.
5. Toda ação crítica gera Audit Log.
6. Todo arquivo original fica em storage privado.
7. Toda URL de arquivo é temporária.
8. Todo campo automático precisa de evidência.
9. Nenhuma chamada de LLM pode ocorrer fora do LLM Gateway.
10. Nenhum OCR pode ocorrer fora da OCR Provider Interface.
11. Campo ausente não deve ser inventado.
12. Campo manual aprovado prevalece sobre automático.
13. Template final só pode ser gerado a partir de versão aprovada.
14. Logs técnicos não podem expor dados sensíveis.

## Como evoluir este projeto

Leia primeiro:

1. `AGENTS.md`
2. `README_TECNICO.md`
3. `docs/prd/00_indice_geral.md`
4. `docs/technical/issues_iniciais.md`

Implemente uma issue por vez, seguindo a ordem documentada em `docs/technical/issues_iniciais.md`. Não avance para issues posteriores sem confirmação explícita.

## Documentação principal

- `AGENTS.md`: regras obrigatórias para agentes de código.
- `README_TECNICO.md`: setup local, comandos e regras técnicas.
- `docs/technical/architecture_decisions.md`: decisões arquiteturais aprovadas.
- `docs/technical/security_matrix.md`: classificação, máscaras, storage, logs e LLM.
- `docs/technical/permission_matrix.md`: papéis, permissões e regras de autorização.
- `docs/technical/api_contracts.md`: grupos e contratos centrais da API.

## Segurança

Este projeto processa dados pessoais, documentos oficiais e narrativas sensíveis. Não use BOs reais não anonimizados em repositório, fixtures ou ambiente de desenvolvimento compartilhado.
