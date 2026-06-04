#!/usr/bin/env bash
set -euo pipefail

# Local-only MinIO helper. Supabase Storage is the MVP storage target.
BUCKET="mercadoia-local"
MINIO_CONTAINER="${MINIO_CONTAINER:-mercadoia_bo_platform_package-minio-1}"
MINIO_ALIAS="${MINIO_ALIAS:-local}"
MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://localhost:9000}"
MINIO_ROOT_USER="${MINIO_ROOT_USER:-minio}"
MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD:-minio_password}"

if ! command -v docker >/dev/null 2>&1; then
  echo "Erro: docker nao encontrado no PATH." >&2
  exit 1
fi

if ! docker container inspect "$MINIO_CONTAINER" >/dev/null 2>&1; then
  echo "Erro: container MinIO '$MINIO_CONTAINER' nao encontrado." >&2
  echo "Suba a infraestrutura local com: docker compose up -d minio" >&2
  exit 1
fi

if [ "$(docker inspect -f '{{.State.Running}}' "$MINIO_CONTAINER")" != "true" ]; then
  echo "Erro: container MinIO '$MINIO_CONTAINER' nao esta rodando." >&2
  echo "Suba a infraestrutura local com: docker compose up -d minio" >&2
  exit 1
fi

docker exec "$MINIO_CONTAINER" mc alias set "$MINIO_ALIAS" "$MINIO_ENDPOINT" "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null
docker exec "$MINIO_CONTAINER" mc mb --ignore-existing "$MINIO_ALIAS/$BUCKET"

echo "Bucket local pronto: $BUCKET"
