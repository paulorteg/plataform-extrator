# Supabase First Backlog Update

## Decisão

Adotar Supabase First no MVP:

1. Supabase Postgres como banco principal
2. Supabase Auth para autenticação
3. Supabase Storage privado para documentos, templates e artefatos de processamento
4. FastAPI mantida para regras de negócio, auditoria, usage, extração e APIs
5. Worker Python mantido para processamento documental
6. Redis opcional, adiado até a necessidade real de fila robusta
7. Docker mantido para desenvolvimento local, API e worker
8. RLS como camada adicional de isolamento por organização

## Novas issues recomendadas

1. Issue 004A: Revisar arquitetura para Supabase First
2. Issue 004B: Criar projeto Supabase e configurar variáveis de ambiente
3. Issue 004C: Configurar Supabase Postgres como banco principal
4. Issue 004D: Configurar Supabase Auth para autenticação do MVP
5. Issue 004E: Configurar Supabase Storage privado para documentos
6. Issue 004F: Definir RLS inicial para isolamento por organização
7. Issue 004G: Atualizar backlog e documentação para Supabase First

## Documentos atualizados

1. `docs/technical/architecture_decisions.md`
2. `docs/technical/security_matrix.md`
3. `docs/technical/permission_matrix.md`
4. `docs/technical/rls_strategy.md`
5. `docs/technical/issues_iniciais.md`
6. `README_TECNICO.md`

## Issues existentes que mudam de escopo

### Issue 007: Configurar SQLAlchemy e Alembic

Manter, mas conectar ao Supabase Postgres via `SUPABASE_DB_URL`. PostgreSQL local em Docker vira opcional.

### Issue 011: Implementar hash de senha

Não implementar no MVP. Substituir por documentação de uso do Supabase Auth. Pode virar issue arquivada ou cancelada.

### Issue 012: Criar endpoint de login

Alterar para: configurar fluxo de login no frontend usando Supabase Auth. A API não deve receber senha no MVP.

### Issue 013: Criar endpoint /auth/me

Manter, mas a API deve ler o usuário a partir do JWT do Supabase e complementar com dados internos de organização, papel e permissões.

### Issue 014: Criar middleware de autenticação

Alterar para: validar JWT do Supabase na FastAPI.

### Issue 024: Criar Storage Service

Alterar para: Storage Service usando Supabase Storage no MVP, com buckets privados e signed URLs.

### Issue 026: Criar endpoint de upload de documentos

Manter, mas upload deve salvar no Supabase Storage privado.

### Issue 027: Criar processing_jobs e fila básica

Manter processing_jobs em Postgres. Redis pode ser opcional. O MVP pode começar com worker polling controlado em processing_jobs antes de introduzir fila robusta.

## Prompt recomendado para Codex

```text
Vamos adaptar o projeto para Supabase First antes de continuar as issues.

Leia AGENTS.md, README_TECNICO.md, docs/technical/architecture_decisions.md, docs/technical/security_matrix.md, docs/technical/permission_matrix.md e docs/technical/issues_iniciais.md.

Não implemente código ainda.

Atualize a documentação para refletir:
1. Supabase Postgres como banco principal
2. Supabase Auth no lugar de autenticação própria no MVP
3. Supabase Storage privado para documentos, templates e artefatos de processamento
4. FastAPI mantendo regras de negócio, pipeline documental, auditoria e usage
5. Worker Python mantendo processamento documental
6. Redis opcional em fase posterior
7. RLS como camada adicional de isolamento por organização

Depois liste os arquivos que você pretende alterar e aguarde minha aprovação.
```

## Sequência recomendada agora

1. Revisar e aceitar as issues 004A a 004G.
2. Commitar a adaptação Supabase First.
3. Retomar a sequência normal com escopos adaptados.
4. Priorizar Issue 006, Issue 007 adaptada ou Issue 009 conforme decisão do produto.
