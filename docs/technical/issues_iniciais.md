# issues_iniciais.md

## Sprint 0

Issue 001: Criar estrutura inicial do monorepo.
Issue 002: Criar README principal.
Issue 003: Criar AGENTS.md.

## Sprint 1

Issue 004: Criar docker compose local.
Issue 004A: Revisar arquitetura para Supabase First.
Issue 004B: Criar projeto Supabase e configurar variáveis de ambiente.
Issue 004C: Configurar Supabase Postgres como banco principal.
Issue 004D: Configurar Supabase Auth para autenticação do MVP.
Issue 004E: Configurar Supabase Storage privado para documentos e templates.
Issue 004F: Definir RLS inicial para isolamento por organização.
Issue 004G: Atualizar backlog e documentação para Supabase First.
Issue 005: Criar script de bucket local.
Issue 006: Criar app FastAPI mínimo.
Issue 007: Configurar SQLAlchemy e Alembic.
Issue 008: Criar logs estruturados.

## Sprint 2

Issue 009: Criar usuários e organizações.
Issue 010: Criar papéis e permissões.
Issue 011: Substituída por decisão Supabase Auth, sem hash de senha próprio.
Issue 012: Planejar login via Supabase Auth no frontend.
Issue 013: Planejar `/auth/me` com usuário interno, organizações, papéis e permissões.
Issue 014: Planejar middleware de autenticação validando JWT do Supabase.
Issue 015: Middleware de organização.
Issue 016: Permission Guard.
Issue 017: Audit Log service.

## Sprint 3 em diante

Planos, pacotes, consumo, upload, storage, jobs, pipeline documental, Modelo Canônico, Mapping, lista, revisão, aprovação, templates, auditoria e regressão.

## Atualização Supabase First

O MVP adota Supabase First:

1. Supabase Postgres como banco principal.
2. Supabase Auth como autenticação principal.
3. Supabase Storage privado para documentos, templates e artefatos de processamento.
4. FastAPI mantida para regras de negócio, pipeline documental, auditoria, usage, extração e APIs.
5. Worker Python mantido para processamento documental.
6. Redis opcional em fase posterior.
7. RLS como camada adicional de isolamento por organização.

## Documentos técnicos Supabase First

1. `docs/technical/architecture_decisions.md`: ADRs e limites da decisão Supabase First.
2. `docs/technical/security_matrix.md`: regras de segurança, storage privado, RLS e logs.
3. `docs/technical/permission_matrix.md`: relação entre Supabase Auth, backend, permissões e RLS.
4. `docs/technical/rls_strategy.md`: estratégia inicial dedicada de RLS.
5. `README_TECNICO.md`: variáveis, setup e comandos do MVP.

## Status das issues 004A a 004G

Issue 004A: documentação arquitetural revisada para Supabase First.

Issue 004B: variáveis de ambiente Supabase documentadas em `.env.example` e `README_TECNICO.md`.

Issue 004C: configuração inicial de Supabase Postgres preparada via `SUPABASE_DB_URL`.

Issue 004D: configuração inicial de Supabase Auth preparada para frontend e backend, sem fluxo de login próprio.

Issue 004E: Supabase Storage privado documentado com buckets para documentos, templates e artefatos.

Issue 004F: estratégia inicial de RLS documentada em `docs/technical/rls_strategy.md`.

Issue 004G: backlog e documentação consolidados para retomar a sequência normal com escopos adaptados.

## Issues existentes com escopo alterado

Issue 004: Docker Compose local continua útil para desenvolvimento, mas PostgreSQL local, Redis e MinIO não são a infraestrutura principal do MVP.

Issue 005: Script de bucket local continua útil para MinIO em desenvolvimento, mas Supabase Storage privado passa a ser o storage principal do MVP.

Issue 007: Manter SQLAlchemy e Alembic, conectando ao Supabase Postgres via `SUPABASE_DB_URL`. PostgreSQL local em Docker vira opcional.

Issue 011: Não implementar hash de senha próprio no MVP. Substituída por decisão arquitetural: senha, recuperação de senha, sessão e credenciais ficam sob responsabilidade do Supabase Auth. A tabela interna `users` não deve ter `password`, `password_hash`, `senha` ou equivalentes.

Issue 012: Alterar de endpoint próprio de login para fluxo de login no frontend usando Supabase Auth. A API não deve receber senha no MVP.

Issue 013: Manter `/auth/me`, mas a API deve ler o usuário a partir do JWT do Supabase e complementar com organização, papel e permissões internas.

Issue 014: Alterar middleware de autenticação para validar JWT do Supabase na FastAPI.

Issue 015: Manter middleware de organização. RLS é camada adicional e não substitui validação de organização ativa no backend.

Issue 016: Manter Permission Guard no backend.

Issue 017: Manter Audit Log service.

Issue 024: Alterar Storage Service para Supabase Storage no MVP, com buckets privados e signed URLs.

Issue 026: Manter upload de documentos, salvando no Supabase Storage privado.

Issue 027: Manter `processing_jobs` no Postgres. Redis pode ser opcional; o MVP pode começar com worker polling controlado.

## Regra de ouro

Toda issue deve ter teste, organization_id, permissão e auditoria quando aplicável.
