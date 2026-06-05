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

Build de produção:

```bash
npm run build
```

Validação leve:

```bash
npm test
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
