# README_TECNICO.md

## Visão geral

Guia técnico para configurar, rodar e evoluir a plataforma.

## Arquitetura MVP

O MVP segue uma abordagem Supabase First:

1. Supabase Postgres como banco principal.
2. Supabase Auth como autenticação principal.
3. Supabase Storage privado para documentos e templates.
4. FastAPI para regras de negócio, pipeline documental, auditoria, usage, extração e APIs.
5. Worker Python para processamento documental.
6. Redis opcional em fase posterior, quando houver necessidade real de fila robusta.

O backend continua sendo a fonte final de autorização. RLS no Supabase é uma camada adicional de segurança e não substitui validação de `organization_id`, permissões e entitlements na FastAPI.

A estratégia inicial de RLS está em `docs/technical/rls_strategy.md`.

## Requisitos locais

1. Node.js LTS
2. Python 3.11 ou superior
3. Docker
4. Docker Compose
5. Git
6. npm

## Gerenciador de pacotes do frontend

O frontend usa npm no MVP. O lockfile esperado é `apps/web/package-lock.json`.

## Variáveis de ambiente

Configure as variáveis reais em `.env` local, sem commitar o arquivo.

Copie `.env.example` para `.env` e preencha com os valores do seu projeto Supabase.

### Frontend público

Estas variáveis podem ser usadas no frontend. Elas não devem conter segredos administrativos.

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
```

Onde encontrar:

1. `NEXT_PUBLIC_SUPABASE_URL`: Supabase Dashboard > Project Settings > API > Project URL.
2. `NEXT_PUBLIC_SUPABASE_ANON_KEY`: Supabase Dashboard > Project Settings > API > Project API keys > anon/public key.

### Backend sensível

Estas variáveis são exclusivas da API/worker. Nunca exponha no frontend.

```bash
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_DB_URL=
SUPABASE_JWT_SECRET=
SUPABASE_STORAGE_BUCKET_DOCUMENTS=
SUPABASE_STORAGE_BUCKET_TEMPLATES=
SUPABASE_STORAGE_BUCKET_ARTIFACTS=
SUPABASE_SIGNED_URL_TTL_SECONDS=
```

Onde encontrar:

1. `SUPABASE_URL`: Supabase Dashboard > Project Settings > API > Project URL.
2. `SUPABASE_ANON_KEY`: Supabase Dashboard > Project Settings > API > Project API keys > anon/public key.
3. `SUPABASE_SERVICE_ROLE_KEY`: Supabase Dashboard > Project Settings > API > Project API keys > service_role key.
4. `SUPABASE_DB_URL`: Supabase Dashboard > Project Settings > Database > Connection string.
5. `SUPABASE_JWT_SECRET`: Supabase Dashboard > Project Settings > API > JWT Settings > JWT Secret.
6. `SUPABASE_STORAGE_BUCKET_DOCUMENTS`: nome do bucket privado criado em Storage para documentos.
7. `SUPABASE_STORAGE_BUCKET_TEMPLATES`: nome do bucket privado criado em Storage para templates.
8. `SUPABASE_STORAGE_BUCKET_ARTIFACTS`: nome do bucket privado criado em Storage para artefatos de processamento.
9. `SUPABASE_SIGNED_URL_TTL_SECONDS`: tempo de validade das signed URLs geradas pelo backend.

Regras:

1. `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_DB_URL` e `SUPABASE_JWT_SECRET` nunca podem ir para o frontend.
2. `NEXT_PUBLIC_SUPABASE_ANON_KEY` pode ser usada no frontend.
3. `.env.example` deve conter apenas placeholders.
4. `.env` real nunca deve ser commitado.

## Supabase Auth no MVP

Supabase Auth é a autenticação principal do MVP.

1. O frontend usa `NEXT_PUBLIC_SUPABASE_URL` e `NEXT_PUBLIC_SUPABASE_ANON_KEY` para criar o cliente Supabase.
2. A API usa `SUPABASE_URL`, `SUPABASE_ANON_KEY` e `SUPABASE_JWT_SECRET` para configuração backend.
3. A API não recebe senha de usuário no MVP.
4. `SUPABASE_SERVICE_ROLE_KEY` nunca deve ser usada no frontend.
5. Fluxo de login, `/auth/me` e middleware de validação JWT serão tratados nas issues específicas.

## Supabase Storage no MVP

Supabase Storage privado é o storage principal para documentos, templates e artefatos de processamento.

Crie os buckets no Supabase Dashboard em Storage > Buckets:

1. `mercadoia-documents`, privado, para documentos originais.
2. `mercadoia-templates`, privado, para templates gerados.
3. `mercadoia-artifacts`, privado, para páginas renderizadas, payloads OCR e arquivos auxiliares do pipeline.

Regras:

1. Buckets devem permanecer privados.
2. Acesso de usuário a arquivos deve ocorrer por signed URLs temporárias geradas pelo backend.
3. Caminhos de objetos devem incluir `organization_id` para preservar isolamento multiempresa.
4. `SUPABASE_SERVICE_ROLE_KEY` pode ser usada apenas pela API/worker.
5. Download de documento ou template sensível deve gerar Audit Log quando o fluxo for implementado.
6. Artefatos de processamento não devem expor OCR integral ou payloads sensíveis em logs.
7. Upload e download não são implementados nesta issue.

Paths planejados:

1. Documentos originais: `organizations/{organization_id}/documents/{document_id}/original`.
2. Templates gerados: `organizations/{organization_id}/occurrences/{occurrence_id}/templates/{template_id}`.
3. Artefatos de processamento: `organizations/{organization_id}/documents/{document_id}/artifacts/{artifact_type}/{artifact_id}`.

## Infraestrutura local opcional

Docker local é mantido para desenvolvimento, API, worker e serviços auxiliares. PostgreSQL local, Redis e MinIO podem apoiar testes locais, mas Supabase Postgres e Supabase Storage são os alvos principais do MVP.

```bash
docker compose up -d postgres redis minio
```

## Criar bucket local opcional

```bash
./infra/scripts/create_local_bucket.sh
```

## Rodar API

```bash
cd apps/api
uvicorn app.main:app --reload --port 8000
```

## Rodar frontend

```bash
cd apps/web
npm install
npm run dev
```

## Rodar worker

```bash
cd apps/worker
python worker.py
```

## Rodar testes

```bash
cd apps/api
pytest
```

```bash
cd apps/web
npm test
```

## Regras de desenvolvimento

1. Nunca commitar `.env`.
2. Nunca commitar BO real não anonimizado.
3. Toda alteração de banco exige migration.
4. Toda feature crítica exige teste.
5. Toda rota operacional exige `organization_id`.
6. Toda ação crítica exige Audit Log.
7. O backend é a fonte final de autorização.
8. A API valida JWT do Supabase em rotas privadas.
9. A API não recebe senha de usuário no MVP.
10. Supabase Storage deve usar buckets privados e URLs temporárias.
11. RLS reforça isolamento por organização, mas não substitui validação no backend.
