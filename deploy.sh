#!/usr/bin/env bash
set -euo pipefail

TAG="v$(date +%Y.%m.%d-%H%M%S)"
RAG_MODE="${RAG_MODE:-ingest}" # ingest | restore
RAG_SOURCE_PATH="${RAG_SOURCE_PATH:-backend/app/modules/ai/rag/chroma_db}"
REMOTE_RAG_TAR="/tmp/chroma_${TAG}.tgz"
DB_SOURCE_PATH="${DB_SOURCE_PATH:-data/database.db}"
REMOTE_DB_DIR="/home/lucky/projects/naramkova-moda-modular/data"
REMOTE_DB_PATH="${REMOTE_DB_DIR}/database.db"
DB_SYNC_MODE="${DB_SYNC_MODE:-skip}" # skip | replace
REMOTE_COMPOSE_TMP="/tmp/docker-compose.prod.yml"
REMOTE_COMPOSE_PATH="/home/lucky/projects/naramkova-moda-modular/docker-compose.prod.yml"
LOCAL_ENV_FILE="${LOCAL_ENV_FILE:-.env.production}"
REMOTE_ENV_FILE="${REMOTE_ENV_FILE:-/home/lucky/.env.production}"

git tag "$TAG"
git push origin "$TAG"

docker build -f docker/backend.Dockerfile -t lakyn80/naramkova-backend:"$TAG" .
docker build -f docker/frontend.client.prod.Dockerfile -t lakyn80/naramkova-frontend-client:"$TAG" .
docker build -f docker/frontend.admin.prod.Dockerfile -t lakyn80/naramkova-frontend-admin:"$TAG" .

docker push lakyn80/naramkova-backend:"$TAG"
docker push lakyn80/naramkova-frontend-client:"$TAG"
docker push lakyn80/naramkova-frontend-admin:"$TAG"

if [ "$RAG_MODE" = "restore" ]; then
  tar -czf "$REMOTE_RAG_TAR" -C "$RAG_SOURCE_PATH" .
  scp "$REMOTE_RAG_TAR" lucky@89.221.214.140:"$REMOTE_RAG_TAR"
fi

if [ "$DB_SYNC_MODE" != "skip" ] && [ "$DB_SYNC_MODE" != "replace" ]; then
  echo "Invalid DB_SYNC_MODE: $DB_SYNC_MODE (expected: skip|replace)"
  exit 1
fi

if [ ! -f "$LOCAL_ENV_FILE" ]; then
  echo "Environment file not found: $LOCAL_ENV_FILE"
  exit 1
fi

if [ "$DB_SYNC_MODE" = "replace" ]; then
  if [ ! -f "$DB_SOURCE_PATH" ]; then
    echo "Database file not found: $DB_SOURCE_PATH"
    exit 1
  fi
  ssh lucky@89.221.214.140 "mkdir -p \"$REMOTE_DB_DIR\" && if [ -f \"$REMOTE_DB_PATH\" ]; then cp \"$REMOTE_DB_PATH\" \"${REMOTE_DB_PATH}.${TAG}.bak\"; fi"
  scp "$DB_SOURCE_PATH" lucky@89.221.214.140:"$REMOTE_DB_PATH"
  echo "DB sync mode: replace (remote database.db overwritten with backup)"
else
  echo "DB sync mode: skip (remote database.db untouched)"
fi

scp docker-compose.prod.yml lucky@89.221.214.140:"$REMOTE_COMPOSE_TMP"
scp "$LOCAL_ENV_FILE" lucky@89.221.214.140:"$REMOTE_ENV_FILE"

ssh lucky@89.221.214.140 <<SSH
set -euo pipefail

export TAG="${TAG}"
export RAG_MODE="${RAG_MODE}"
export REMOTE_RAG_TAR="${REMOTE_RAG_TAR}"
export REMOTE_ENV_FILE="${REMOTE_ENV_FILE}"
cd /home/lucky/projects/naramkova-moda-modular
git fetch origin
git checkout main
git pull origin main

cp "$REMOTE_COMPOSE_TMP" "$REMOTE_COMPOSE_PATH"

docker compose -f docker-compose.prod.yml --env-file "$REMOTE_ENV_FILE" down
docker compose -f docker-compose.prod.yml --env-file "$REMOTE_ENV_FILE" up -d

if [ "\$RAG_MODE" = "ingest" ]; then
  curl -fsS -X POST http://127.0.0.1:9050/api/ai/rag/seed-templates
elif [ "\$RAG_MODE" = "restore" ]; then
  docker run --rm -v chroma_data:/data -v /tmp:/backup alpine sh -c "cd /data && tar -czf /backup/chroma_prev_${TAG}.tgz ."
  docker run --rm -v chroma_data:/data -v /tmp:/backup alpine sh -c "rm -rf /data/* && tar -xzf /backup/$(basename "$REMOTE_RAG_TAR") -C /data"
fi
SSH

echo "Deployed $TAG"
