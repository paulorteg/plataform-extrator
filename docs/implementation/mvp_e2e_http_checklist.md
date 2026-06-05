# Checklist HTTP do MVP end to end

## Objetivo

Validar manualmente o fluxo tecnico do MVP, desde um usuario autenticado pelo Supabase Auth ate a geracao de template e verificacoes de auditoria e usage.

Este roteiro nao cria usuario no Supabase, nao usa senha, nao inclui token real e nao deve ser executado com Boletim de Ocorrencia real nao anonimizado.

## Pre-requisitos

1. API rodando localmente em `http://localhost:8000`.
2. Migrations aplicadas no banco de teste.
3. Buckets privados do Supabase Storage configurados.
4. Usuario existente no Supabase Auth.
5. Registro interno em `users` com `auth_user_id` igual ao `sub` do usuario Supabase.
6. Vinculo ativo em `user_organizations` para a organizacao de teste.
7. Role com permissoes para upload, ocorrencias, revisao, template, audit e usage.
8. Plano, pacote, assinatura ou quota minima configurados quando usage estiver habilitado.
9. Documento sintetico e anonimizado para upload.

Se a Issue 050C estiver disponivel no branch usado, o seed local pode preparar os dados internos minimos:

```bash
cd apps/api
SUPABASE_DB_URL="<connection-string-do-supabase-ou-postgres-local>" alembic upgrade head
export MERCADOIA_MVP_AUTH_USER_ID="<uuid-do-usuario-supabase-auth>"
python scripts/seed_mvp_test_environment.py
```

## Placeholders

Substitua todos os placeholders antes de executar:

1. `<API_BASE_URL>`: URL da API, por exemplo `http://localhost:8000/api/v1`.
2. `<SUPABASE_ACCESS_TOKEN>`: access token atual do Supabase Auth.
3. `<ORGANIZATION_ID>`: organizacao ativa do usuario interno.
4. `<REQUEST_ID>`: identificador tecnico sem dado sensivel, por exemplo `mvp-e2e-001`.
5. `<DOCUMENT_PATH>`: caminho local para um PDF ou imagem sintetica.
6. `<DOCUMENT_ID>`: id retornado no upload.
7. `<JOB_ID>`: id retornado no upload.
8. `<OCCURRENCE_ID>`: id retornado na listagem de ocorrencias.
9. `<FIELD_ID>`: id de campo retornado em `/occurrences/{occurrence_id}/fields`.
10. `<REPORT_ID>`: id retornado na geracao de template.

Nunca cole `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`, refresh token, senha ou dado pessoal real no roteiro.

## Headers obrigatorios

Rotas privadas:

```http
Authorization: Bearer <SUPABASE_ACCESS_TOKEN>
X-Request-Id: <REQUEST_ID>
```

Rotas operacionais:

```http
Authorization: Bearer <SUPABASE_ACCESS_TOKEN>
X-Organization-Id: <ORGANIZATION_ID>
X-Request-Id: <REQUEST_ID>
```

## Sequencia de validacao

### 1. Health check

Execute `GET /health` sem autenticacao.

Resultado esperado:

1. HTTP 200.
2. Corpo `{"status":"ok"}`.

### 2. Identidade e organizacoes

Execute `GET /auth/me`.

Resultado esperado:

1. HTTP 200.
2. Usuario interno retornado.
3. Organizacao de teste presente em `organizations`.
4. Role e permissoes incluem pelo menos `document_upload`, `occurrence_list`, `occurrence_view`, `review_field_edit`, `review_field_approve`, `review_approve_occurrence`, `template_generate`, `template_download`, `audit_view` e `usage_view`.
5. Resposta nao contem senha, token, service role key ou segredo.

### 3. Upload do documento

Execute `POST /documents/upload` com arquivo sintetico e header `X-Organization-Id`.

Resultado esperado:

1. HTTP 201.
2. Resposta contem `document_id`, `job_id`, `organization_id`, `status`, `storage_uri`, `sha256_hash` e `size_bytes`.
3. `organization_id` bate com `<ORGANIZATION_ID>`.
4. O arquivo fica no bucket privado de documentos.
5. A resposta nao contem conteudo do arquivo, URL publica permanente ou signed URL.

### 4. Processamento do job

No estado atual da API nao existe endpoint HTTP publico para executar ou consultar `processing_jobs`.

Validacao operacional recomendada:

1. Execute o worker ou comando interno de processamento usado no ambiente de teste.
2. Confirme no banco que `<JOB_ID>` saiu de `pending` para `completed`.
3. Confirme que o documento saiu de `uploaded` para um status processado.
4. Confirme que o processamento criou ao menos uma linha em `occurrences`.

Consulta de apoio, apenas em banco local/de teste:

```sql
select id, job_type, status, error_code
from processing_jobs
where id = '<JOB_ID>'
  and organization_id = '<ORGANIZATION_ID>';
```

Se a Issue 050B ainda nao estiver aplicada no branch testado, o processamento end to end com arquivo real salvo no Supabase Storage pode nao estar disponivel. Nesse caso, registre a limitacao e valide somente o upload, a criacao do job e os fluxos ja cobertos por dados sinteticos.

### 5. Listagem de ocorrencias

Execute `GET /occurrences?page=1&page_size=20`.

Resultado esperado:

1. HTTP 200.
2. Lista contem pelo menos uma ocorrencia do documento processado.
3. Cada item contem `id`, `document_id`, `status`, `pending_required` e `blocking_issues`.
4. Campos sensiveis nao aparecem completos em lista quando mascaramento for aplicavel.

### 6. Detalhe da ocorrencia

Execute `GET /occurrences/<OCCURRENCE_ID>`.

Resultado esperado:

1. HTTP 200.
2. `organization_id` bate com `<ORGANIZATION_ID>`.
3. `checklist` indica pendencias ou possibilidade de aprovacao.
4. `text_excerpt` nao deve ser usado como narrativa integral em logs ou evidencias externas.

### 7. Campos da ocorrencia

Execute `GET /occurrences/<OCCURRENCE_ID>/fields`.

Resultado esperado:

1. HTTP 200.
2. Lista de campos extraidos.
3. Cada campo contem `field_key`, `value`, `status`, `confidence`, `extraction_method`, `evidence` e `validation_issues`.
4. Valores sensiveis devem estar mascarados quando a permissao nao permitir visualizacao completa.

### 8. Edicao de campo

Execute `PATCH /occurrences/<OCCURRENCE_ID>/fields/<FIELD_ID>` com valor sintetico.

Resultado esperado:

1. HTTP 200.
2. Campo passa para `manual` quando `value` for alterado.
3. Audit log de `review.field_updated` e criado.
4. A justificativa nao contem dado sensivel real.

### 9. Aprovacao de campo

Execute `POST /occurrences/<OCCURRENCE_ID>/fields/<FIELD_ID>/approve`.

Resultado esperado:

1. HTTP 200.
2. Campo passa para `aprovado`.
3. Issues de validacao relacionadas ao campo ficam resolvidas quando aplicavel.
4. Audit log de `review.field_approved` e criado.

Repita para os campos obrigatorios ate o checklist permitir aprovacao da ocorrencia.

### 10. Aprovacao da ocorrencia

Execute `POST /occurrences/<OCCURRENCE_ID>/approve`.

Resultado esperado:

1. HTTP 200.
2. Status da ocorrencia passa para `aprovado`.
3. Resposta contem `snapshot_version`.
4. `review_versions` recebe snapshot aprovado.
5. Audit log de `review.occurrence_approved` e criado.

### 11. Preview de template

Execute `POST /occurrences/<OCCURRENCE_ID>/templates/preview`.

Resultado esperado:

1. HTTP 200.
2. Resposta contem `template_version`, `fields` e `content_preview`.
3. Campos pendentes aparecem como `requires_review` quando aplicavel.
4. Audit log de `template.previewed` e criado.

### 12. Geracao de template

Execute `POST /occurrences/<OCCURRENCE_ID>/templates/generate`.

Resultado esperado:

1. HTTP 200.
2. Resposta contem `report_id`, `storage_bucket`, `storage_path` e `template_version`.
3. Template e salvo em bucket privado.
4. Audit log de `template.generated` e criado.

### 13. Signed URL do template

Execute `GET /occurrences/<OCCURRENCE_ID>/templates/<REPORT_ID>/download-url`.

Resultado esperado:

1. HTTP 200.
2. Resposta contem `signed_url` e `expires_in`.
3. URL e temporaria.
4. Audit log de `template.download_url_created` e criado.
5. Signed URL nao deve ser copiada para logs, tickets ou documentos.

### 14. Audit logs

Execute `GET /audit-logs?page=1&page_size=50`.

Resultado esperado:

1. HTTP 200.
2. Eventos criticos aparecem para a organizacao ativa.
3. Metadados nao contem Authorization, token, corpo completo de request, OCR integral, narrativa integral, prompt completo, signed URL ou conteudo do arquivo.

Filtros uteis:

1. `GET /audit-logs?target_type=document`
2. `GET /audit-logs?target_type=occurrence`
3. `GET /audit-logs?target_type=generated_report`
4. `GET /audit-logs?request_id=<REQUEST_ID>`

### 15. Usage

Execute `GET /usage/balance`, `GET /usage/events` e `GET /usage/availability?amount=1`.

Resultado esperado:

1. Balance mostra quota total, uso e disponibilidade.
2. Eventos de usage existem quando o processamento registrou consumo.
3. Availability retorna se ainda ha quota para consumir.

## Falhas comuns

### 401 `missing_token` ou `invalid_token`

Verifique se:

1. `Authorization` esta no formato `Bearer <SUPABASE_ACCESS_TOKEN>`.
2. O token nao expirou.
3. `SUPABASE_JWT_SECRET` da API corresponde ao projeto Supabase usado.

### 403 `organization_required`, `organization_not_found` ou `permission_denied`

Verifique se:

1. `X-Organization-Id` foi enviado em rotas operacionais.
2. O usuario interno existe e esta ativo.
3. `user_organizations` tem vinculo ativo para a organizacao.
4. A role do vinculo possui a permissao da rota.

### 400 `unsupported_file_type`

Use um arquivo com content type permitido: `application/pdf`, `image/jpeg`, `image/png` ou `image/tiff`.

### Job fica `pending`

Verifique se:

1. O worker/processador foi iniciado.
2. O job tem `job_type = document_processing`.
3. A Issue 050A esta no branch testado.
4. A Issue 050B esta no branch testado quando o teste depender de arquivo real no Supabase Storage.

### Job fica `failed`

Verifique `error_code`, sem copiar OCR, narrativa ou arquivo para logs externos. Causas comuns:

1. Documento ausente ou organizacao divergente.
2. Storage indisponivel.
3. Quota insuficiente.
4. Conteudo de teste sem sinais minimos para segmentacao.

### Ocorrencia nao aprova

Verifique `GET /occurrences/<OCCURRENCE_ID>` e `GET /occurrences/<OCCURRENCE_ID>/fields`.

1. Campos obrigatorios precisam estar preenchidos.
2. Issues bloqueantes precisam estar resolvidas.
3. Campos pendentes devem ser editados ou aprovados conforme regra de revisao.

## Checklist final

- [ ] Health check retornou 200.
- [ ] `/auth/me` retornou usuario, organizacao, role e permissoes.
- [ ] Upload retornou `document_id` e `job_id`.
- [ ] Job `document_processing` concluiu ou limitacao foi registrada.
- [ ] Ocorrencia foi listada.
- [ ] Detalhe da ocorrencia foi aberto.
- [ ] Campos foram revisados.
- [ ] Campos obrigatorios foram aprovados.
- [ ] Ocorrencia foi aprovada.
- [ ] Preview de template foi gerado.
- [ ] Template foi gerado.
- [ ] Signed URL temporaria foi criada quando aplicavel.
- [ ] Audit logs foram consultados.
- [ ] Usage foi consultado.
- [ ] Nenhum segredo real foi registrado no roteiro, logs, Jira ou commit.
- [ ] Nenhum BO real nao anonimizado foi usado.
