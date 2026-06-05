# architecture_decisions.md

## ADRs aprovadas

1. Monólito modular no MVP.
2. Frontend com Vite e React no MVP.
3. Backend com FastAPI e Python.
4. Supabase Postgres como banco principal do MVP.
5. JSONB para Modelo Canônico.
6. Redis opcional, adiado até necessidade real de fila robusta.
7. Supabase Storage privado para documentos, templates e artefatos de processamento no MVP.
8. OCR via Provider Interface.
9. LLM Gateway obrigatório.
10. Extração determinística antes de LLM.
11. Modelo Canônico antes do template.
12. Mapping declarativo e versionado.
13. Revisão humana no MVP.
14. Evidência por campo.
15. Consumo por ocorrência.
16. Audit Log separado.
17. Segurança e LGPD desde o início.
18. Dados reais apenas anonimizados em testes.
19. Testes de regressão documental.
20. Templates apenas de versão aprovada.
21. Supabase Auth como autenticação principal do MVP.
22. FastAPI mantida para regras de negócio, pipeline documental, auditoria, usage, extração e APIs.
23. Worker Python mantido para processamento documental.
24. RLS no Supabase como camada adicional de isolamento por organização.

## Supabase First no MVP

O MVP adota Supabase First para reduzir escopo operacional inicial sem remover o backend próprio.

1. Supabase Postgres é o banco principal.
2. Supabase Auth é a autenticação principal.
3. Supabase Storage privado armazena documentos originais, templates e artefatos de processamento.
4. FastAPI valida regras de negócio, permissões, organização ativa, auditoria, usage e pipeline documental.
5. Worker Python executa processamento documental.
6. Redis fica opcional para fase posterior, quando houver necessidade real de fila robusta.

## Limites da decisão

1. Supabase Auth não substitui autorização de negócio no backend.
2. RLS não substitui validação de `organization_id`, permissão e entitlement na FastAPI.
3. Supabase Storage deve permanecer privado, com acesso por URLs temporárias ou signed URLs.
4. PostgreSQL local em Docker pode ser usado em desenvolvimento, mas não é o banco principal do MVP.
5. MinIO local pode apoiar desenvolvimento, mas Supabase Storage é o alvo principal do MVP.

## Estratégia de RLS

A estratégia inicial de RLS está documentada em `docs/technical/rls_strategy.md`.

RLS é defesa adicional para isolamento por organização. FastAPI continua sendo a fonte principal de autorização, permissões, entitlements, organização ativa, auditoria e regras de negócio.
