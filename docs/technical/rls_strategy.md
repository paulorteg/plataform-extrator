# rls_strategy.md

## Objetivo

Definir a estratégia inicial de Row Level Security (RLS) no Supabase para isolamento por organização no MVP.

RLS é camada adicional de defesa. A FastAPI continua sendo a fonte principal de autorização, validação de organização ativa, permissões, entitlements, auditoria e regras de negócio.

## Princípios

1. Supabase Auth autentica usuários e emite JWT.
2. FastAPI valida autenticação, organização ativa, permissão e entitlement antes de ações operacionais.
3. RLS reforça o isolamento por organização no banco e reduz impacto de falhas.
4. Toda tabela operacional deve ter `organization_id`.
5. O frontend não deve consultar dados sensíveis diretamente no MVP.
6. Service role deve ser usada apenas no backend e com validações explícitas.
7. Nenhuma policy SQL real é criada nesta issue.

## Modelo de identidade

Supabase Auth mantém a identidade primária em `auth.users`.

A aplicação mantém usuários internos para regras de negócio:

```text
auth.users
  id

users
  id
  auth_user_id
  email
  status

user_organizations
  id
  user_id
  auth_user_id
  organization_id
  role_id
  status
```

Regras:

1. `users.auth_user_id` referencia logicamente `auth.users.id`.
2. `user_organizations` representa vínculo do usuário com uma ou mais organizações.
3. Usuário só acessa organização com vínculo ativo.
4. FastAPI resolve o usuário interno a partir do `sub` do JWT Supabase.
5. Policies RLS podem usar `auth.uid()` para reforçar o vínculo com `user_organizations`.

## Tabelas com organization_id

Toda entidade operacional deve ter `organization_id`, incluindo:

1. `usage_events`
2. `documents`
3. `document_pages`
4. `processing_jobs`
5. `occurrences`
6. `extracted_fields`
7. `evidences`
8. `validation_issues`
9. `review_versions`
10. `generated_reports`
11. `audit_logs`
12. `model_calls`
13. `subscriptions`
14. `packages`, quando atribuídos por organização
15. `roles`, quando customizados por organização
16. `permissions`, quando customizadas por organização

Tabelas globais, como catálogo global de permissões ou planos, podem não ter `organization_id`, mas devem ter acesso restrito.

## Acesso direto pelo frontend

No MVP, o frontend não deve consultar diretamente tabelas sensíveis ou operacionais.

Devem passar pela FastAPI:

1. documentos e páginas
2. ocorrências
3. campos extraídos
4. evidências
5. issues de validação
6. versões de revisão
7. relatórios gerados
8. jobs de processamento
9. usage
10. auditoria
11. chamadas de modelo
12. dados pessoais ou altamente restritos

Acesso direto pelo frontend só poderá ser autorizado em issue futura, com RLS testada, dados mascarados quando aplicável e escopo explícito.

## Policies mínimas futuras

Quando as tabelas existirem, as policies devem seguir este desenho:

1. Habilitar RLS em toda tabela operacional.
2. Bloquear `anon` por padrão.
3. Permitir `authenticated` apenas com vínculo ativo em `user_organizations`.
4. Restringir por `organization_id`.
5. Separar policies de `SELECT`, `INSERT`, `UPDATE` e `DELETE`.
6. Evitar `DELETE` em entidades auditáveis.
7. Nunca usar `user_metadata` para autorização.
8. Não criar policy ampla com `TO authenticated USING (true)`.

Condição conceitual:

```sql
organization_id in (
  select organization_id
  from user_organizations
  where auth_user_id = auth.uid()
    and status = 'active'
)
```

## Storage

Buckets privados do MVP:

1. `mercadoia-documents`
2. `mercadoia-templates`
3. `mercadoia-artifacts`

Regras futuras:

1. Policies em `storage.objects` devem respeitar prefixo de organização.
2. Acesso a arquivos sensíveis deve ocorrer por signed URLs temporárias geradas pelo backend.
3. Paths devem começar por `organizations/{organization_id}/`.
4. Download de documento ou template sensível deve gerar Audit Log.
5. OCR integral e payloads sensíveis não podem aparecer em logs.

## Service role key

`SUPABASE_SERVICE_ROLE_KEY` pode bypassar RLS. Ela deve ser tratada como segredo crítico.

Riscos:

1. Vazamento no frontend remove isolamento efetivo.
2. Uso indiscriminado no backend pode contornar RLS sem validação de negócio.
3. Logs, tracing, exceptions e dumps de ambiente podem expor o segredo.
4. Rotas com service role sem Permission Guard podem virar bypass de autorização.

Mitigações:

1. Nunca usar `SUPABASE_SERVICE_ROLE_KEY` em `NEXT_PUBLIC_*`.
2. Nunca enviar a service role para o browser.
3. Nunca logar variáveis de ambiente, headers, tokens ou signed URLs.
4. Isolar uso da service role em serviços internos.
5. Validar JWT, `organization_id`, permissão e entitlement antes de qualquer ação sensível.
6. Preferir queries com escopo explícito por `organization_id`.

## Fora do escopo desta issue

Esta issue não cria:

1. migrations
2. tabelas
3. policies SQL
4. policies de Storage
5. middleware JWT
6. middleware de organização
7. Permission Guard
8. testes de RLS

Esses itens ficam para issues futuras.
