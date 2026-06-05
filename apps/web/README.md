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
3. Acesso restrito: usuário sem sessão, aguardando tela de login futura.
4. Shell autenticado: navegação principal e área de conteúdo para páginas futuras.

O shell não implementa login completo, upload, revisão ou chamadas reais de documentos.

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
