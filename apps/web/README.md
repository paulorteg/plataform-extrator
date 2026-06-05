# Web app

Aplicação web executável do MercadoIA BO Platform.

O MVP usa Vite + React em `apps/web` para manter o preview local simples e rápido.

## Rodar localmente

```bash
npm install
npm run dev
```

URL local padrão:

```bash
http://localhost:5173
```

### Configurar preview local

Sem `apps/web/.env.local`, a UI deve abrir em `http://localhost:5173` exibindo
`Ambiente web pendente`. Esse e o estado esperado para confirmar que a aplicacao
nao fica em tela branca quando as variaveis publicas estao ausentes.

Para ver login, shell autenticado e upload, copie o exemplo local:

```bash
cp .env.local.example .env.local
```

Preencha apenas valores publicos:

```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_SUPABASE_URL=<project-url-do-supabase>
VITE_SUPABASE_ANON_KEY=<anon-public-key-do-supabase>
```

Nunca coloque em `.env.local`:

1. `SUPABASE_SERVICE_ROLE_KEY`
2. `SUPABASE_DB_URL`
3. `SUPABASE_JWT_SECRET`
4. Senha, refresh token ou qualquer segredo real.

Depois inicie o frontend:

```bash
npm run dev
```

Checklist visual:

1. Sem `.env.local`: tela `Ambiente web pendente`.
2. Com `.env.local` publico e sem sessao: tela de login.
3. Apos login Supabase e `/auth/me` valido: shell autenticado.
4. No shell autenticado, acesse `#/upload` para ver a tela de upload.
5. Apos um upload, acesse `#/processing?job_id=<job_id>&document_id=<document_id>`
   para acompanhar o status do processamento.
6. Acesse `#/occurrences` para listar ocorrencias extraidas da organizacao ativa.
7. A partir da lista, abra `#/review?occurrence_id=<occurrence_id>` para revisar
   campos, evidencias e validation issues.
8. Na tela de revisao, aprove a ocorrencia e gere o template quando os endpoints
   de backend estiverem disponiveis.

Se a API local nao estiver rodando, o login pode criar sessao Supabase mas falhar
ao carregar o usuario interno em `/auth/me`.

Build de produção:

```bash
npm run build
```

Validação leve:

```bash
npm test
```

Validação HTTP quando o servidor Vite estiver rodando:

```bash
curl -I http://localhost:5173
```

## Supabase Auth

O frontend usa Supabase Auth para login, sessão, recuperação de senha e logout.

Variáveis públicas necessárias:

```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
```

Regras:

1. Envie senha apenas para o Supabase Auth pelo SDK.
2. Não envie senha para a FastAPI.
3. Não use `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_DB_URL` ou `SUPABASE_JWT_SECRET` no frontend.
4. Não persista manualmente o access token em `localStorage`; deixe o SDK Supabase gerenciar a sessão.
5. Para carregar o usuário interno, obtenha a sessão Supabase e chame `/auth/me` com `Authorization: Bearer <access_token>`.

Helpers iniciais:

1. `src/lib/auth/session.js`: login, logout, sessão e carregamento do usuário atual.
2. `src/lib/api/auth-me.js`: chamada autenticada para a API.

### Usuario de teste Supabase

Para testar login localmente:

1. Crie ou convide um usuario no Supabase Auth pelo Dashboard do projeto.
2. Use o email e senha desse usuario na tela de login.
3. Garanta que a API tenha um registro interno em `users.auth_user_id` igual ao
   `sub` do usuario Supabase.
4. Garanta que exista vinculo ativo em `user_organizations` para a organizacao
   de teste.
5. Garanta que a role vinculada tenha permissoes para as telas que voce quer
   validar, incluindo `document_upload` para upload.

Quando o seed de MVP estiver disponivel no ambiente escolhido, ele pode preparar
os dados internos minimos a partir do `auth_user_id` do usuario Supabase.

## Shell autenticado

O shell base da aplicação valida configuração pública e tenta carregar a sessão Supabase antes de exibir a área autenticada.

Estados previstos:

1. Configuração pendente: variáveis `VITE_` ausentes.
2. Carregando: sessão Supabase em validação.
3. Login: usuário sem sessão autentica com email e senha via Supabase Auth.
4. Shell autenticado: navegação principal e área de conteúdo para páginas futuras.

O formulário envia senha apenas ao Supabase Auth via SDK. Após autenticar, o frontend carrega o usuário interno chamando `/auth/me` com o access token da sessão Supabase.

O shell não implementa upload, revisão ou chamadas reais de documentos.

## Upload de BO

A rota `#/upload` permite enviar um BO ou documento sintetico/anonimizado para a API.

Regras do upload:

1. O arquivo e enviado para `POST /documents/upload` usando `VITE_API_BASE_URL`.
2. A requisicao envia `Authorization: Bearer <access_token>` obtido da sessao Supabase.
3. A requisicao envia `X-Organization-Id` com a organizacao ativa selecionada.
4. O frontend valida apenas tipo e tamanho antes do envio.
5. O frontend nao le conteudo textual do BO e nao processa OCR, extracao ou classificacao.
6. O frontend nao faz upload direto para Supabase Storage.

Formatos aceitos pelo backend:

1. PDF
2. JPEG
3. PNG
4. TIFF

Tamanho maximo:

1. 25 MB por arquivo.

## Status do processamento

A rota `#/processing` consulta o status dos jobs documentais pelo backend.

Consultas suportadas:

1. `GET /processing-jobs/{job_id}` para consultar um job especifico.
2. `GET /documents/{document_id}/processing-jobs` para listar jobs de um documento.

Regras:

1. A requisicao usa `VITE_API_BASE_URL`.
2. A requisicao envia `Authorization: Bearer <access_token>` obtido da sessao Supabase.
3. A requisicao envia `X-Organization-Id` com a organizacao ativa selecionada.
4. A UI exibe apenas status, identificadores, tentativas e datas retornadas pela API.
5. A UI nao exibe metadata sensivel, conteudo bruto do documento, OCR completo,
   narrativa completa, prompt ou payload interno de erro.
6. A UI nao gera signed URL e nao acessa Supabase Storage diretamente para processar documento.

## Lista de ocorrencias

A rota `#/occurrences` lista ocorrencias extraidas usando `GET /occurrences`.

Regras:

1. A requisicao usa `VITE_API_BASE_URL`.
2. A requisicao envia `Authorization: Bearer <access_token>` obtido da sessao Supabase.
3. A requisicao envia `X-Organization-Id` com a organizacao ativa selecionada.
4. A tela permite filtrar por status, buscar por dados operacionais e paginar resultados.
5. A tela mostra apenas dados principais nao sensiveis, como numero do BO, tipo,
   cidade, UF, status, confianca e pendencias.
6. A tela nao exibe CPF, CNPJ, placa, narrativa completa, OCR completo, metadata
   sensivel, prompt ou conteudo bruto.
7. A acao `Abrir detalhe` prepara a navegacao para a proxima tela, sem implementar
   revisao ou detalhe completo nesta issue.

## Detalhe e revisao da ocorrencia

A rota `#/review?occurrence_id=<occurrence_id>` revisa uma ocorrencia usando os
endpoints existentes:

1. `GET /occurrences/{occurrence_id}` para resumo seguro e checklist.
2. `GET /occurrences/{occurrence_id}/fields` para campos extraidos, evidencias e
   validation issues.
3. `PATCH /occurrences/{occurrence_id}/fields/{field_id}` para editar campo.
4. `POST /occurrences/{occurrence_id}/fields/{field_id}/approve` para aprovar campo.
5. `POST /occurrences/{occurrence_id}/approve` para aprovar a ocorrencia.
6. `POST /occurrences/{occurrence_id}/templates/generate` para solicitar a geracao
   do template no backend.
7. `GET /occurrences/{occurrence_id}/templates/{report_id}/download-url` para obter
   uma URL temporaria de download quando a API retornar essa opcao.

Regras:

1. Todas as requisicoes usam `VITE_API_BASE_URL`.
2. Todas as requisicoes enviam `Authorization: Bearer <access_token>`.
3. Todas as requisicoes operacionais enviam `X-Organization-Id`.
4. A tela nao exibe `metadata`, narrativa completa, OCR completo, prompt, conteudo
   bruto ou URL permanente.
5. Valores de campos sensiveis, como CPF, CNPJ e placa, ficam ocultos no frontend.
6. Evidencias sao exibidas apenas como trecho resumido com mascaramento basico.
7. Aprovacao da ocorrencia inteira usa apenas endpoint existente do backend.
8. Geracao de template usa apenas endpoint existente do backend; o frontend nao
   monta arquivo, nao acessa storage privado diretamente e nao cria signed URL.
9. A URL temporaria de download so aparece se a API devolver `signed_url`; ela nao
   deve ser persistida em `localStorage`, `sessionStorage` ou logs.
10. A tela nao exibe bucket, path privado de storage ou payload interno de template.

## Deploy na Vercel

Configure o projeto na Vercel com:

1. Root Directory: `apps/web`
2. Framework Preset: `Vite`
3. Install Command: `npm install`
4. Build Command: `npm run build`
5. Output Directory: `dist`

Variáveis por ambiente:

1. Preview:
   - `VITE_API_BASE_URL`: URL da API de preview ou ambiente de teste.
   - `VITE_SUPABASE_URL`: Project URL do Supabase de teste.
   - `VITE_SUPABASE_ANON_KEY`: anon/public key do Supabase de teste.
2. Production:
   - `VITE_API_BASE_URL`: URL da API de produção.
   - `VITE_SUPABASE_URL`: Project URL do Supabase de produção.
   - `VITE_SUPABASE_ANON_KEY`: anon/public key do Supabase de produção.

Nunca configure no frontend:

1. `SUPABASE_SERVICE_ROLE_KEY`
2. `SUPABASE_DB_URL`
3. `SUPABASE_JWT_SECRET`

Não faça deploy de produção sem aprovação humana.
