#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/deploy/team-cloud/compose.yaml"

cd "$ROOT_DIR"

if [[ ! -f deploy/team-cloud/secrets/team_cloud_database_url.txt ]]; then
  scripts/team-cloud-secrets.sh
fi

docker compose -f "$COMPOSE_FILE" --env-file deploy/team-cloud/.env.example config >/dev/null
docker compose -f "$COMPOSE_FILE" --env-file deploy/team-cloud/.env.example up -d --wait

curl -fsS http://localhost:8780/healthz >/dev/null
curl -fsS http://localhost:8780/readyz >/dev/null
curl -fsS http://localhost:19000/minio/health/ready >/dev/null

docker compose -f "$COMPOSE_FILE" --env-file deploy/team-cloud/.env.example exec -T postgres \
  psql -U hermes_superuser -d hermes_team -tAc "select extversion from pg_extension where extname = 'vector'" | grep -q '0.8.2'

docker compose -f "$COMPOSE_FILE" --env-file deploy/team-cloud/.env.example run --rm minio-init
docker compose -f "$COMPOSE_FILE" --env-file deploy/team-cloud/.env.example run --rm spicedb-schema-load

echo "Team Cloud local compose smoke checks passed"
