# README_TECNICO.md

## Visão geral

Guia técnico para configurar, rodar e evoluir a plataforma.

## Requisitos locais

1. Node.js LTS
2. Python 3.11 ou superior
3. Docker
4. Docker Compose
5. Git
6. pnpm ou npm

## Subir infraestrutura local

```bash
docker compose up -d postgres redis minio
```

## Criar bucket local

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
pnpm install
pnpm dev
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
pnpm test
```

## Regras de desenvolvimento

1. Nunca commitar `.env`.
2. Nunca commitar BO real não anonimizado.
3. Toda alteração de banco exige migration.
4. Toda feature crítica exige teste.
5. Toda rota operacional exige `organization_id`.
6. Toda ação crítica exige Audit Log.
7. O backend é a fonte final de autorização.
