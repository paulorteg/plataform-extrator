# security_matrix.md

## Classificação

1. Operacional interno
2. Operacional restrito
3. Pessoal
4. Altamente restrito
5. Segredo

## Máscaras

CPF: `000*****00`.
CNPJ: `00.***.***/****00`.
Telefone: DDD e últimos dígitos.
Email: parcial.
Endereço: cidade e UF.
Narrativa: não exibir em lista.
Documento original: acessar apenas com permissão.

## Storage

Storage privado, URL temporária, separação por ambiente e organização, criptografia em repouso, audit log em download e retenção configurável.

No MVP, o storage principal é Supabase Storage privado.

1. Documentos originais, templates e artefatos de processamento ficam em buckets privados.
2. Acesso a arquivos ocorre por signed URLs ou URLs temporárias.
3. Buckets devem separar ambientes e preservar isolamento por organização.
4. Download de documento ou template sensível deve gerar Audit Log.
5. MinIO local pode ser usado em desenvolvimento, mas não substitui Supabase Storage no MVP.

## Banco e RLS

Supabase Postgres é o banco principal do MVP.

RLS deve ser usada como camada adicional de isolamento por organização, mas não substitui validação no backend.

1. Toda rota operacional continua exigindo organização ativa.
2. Toda consulta operacional na FastAPI continua filtrando por `organization_id`.
3. Toda ação protegida continua validando permissão no backend.
4. Políticas RLS devem reforçar isolamento e reduzir impacto de falhas.
5. Service role keys nunca devem ser expostas ao frontend ou logs.

A estratégia inicial de RLS está documentada em `docs/technical/rls_strategy.md`.

## Autenticação

Supabase Auth é a autenticação principal do MVP.

1. A API valida JWT do Supabase em rotas privadas.
2. A API não recebe senha de usuário no MVP.
3. Tokens não podem aparecer em logs técnicos.
4. Dados internos de organização, papel e permissões são resolvidos pela API.

## Logs

Logs técnicos não podem conter dados sensíveis completos, narrativa, OCR integral, tokens, senhas ou URLs temporárias.

## LLM

Usar mínimo contexto, schema obrigatório, evidência obrigatória, rejeição sem evidência e registro de custo.
