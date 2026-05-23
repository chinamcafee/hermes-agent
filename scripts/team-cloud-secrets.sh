#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SECRETS_DIR="$ROOT_DIR/deploy/team-cloud/secrets"
FORCE=0

if [[ "${1:-}" == "--force" ]]; then
  FORCE=1
fi

mkdir -p "$SECRETS_DIR"

rand() {
  python - <<'PY'
import secrets
print(secrets.token_urlsafe(36))
PY
}

write_secret() {
  local name="$1"
  local value="$2"
  local path="$SECRETS_DIR/$name"
  if [[ -e "$path" && "$FORCE" != "1" ]]; then
    return
  fi
  umask 077
  printf '%s\n' "$value" > "$path"
}

team_db_password="$(rand)"
write_secret "team_cloud_postgres_password.txt" "$(rand)"
write_secret "team_cloud_database_url.txt" "postgresql://hermes_team_user:${team_db_password}@postgres:5432/hermes_team?sslmode=disable"
write_secret "team_cloud_casdoor_db_password.txt" "$(rand)"
write_secret "team_cloud_spicedb_db_password.txt" "$(rand)"
write_secret "team_cloud_casdoor_client_secret.txt" "$(rand)"
write_secret "team_cloud_spicedb_preshared_key.txt" "$(rand)"
write_secret "team_cloud_minio_secret_key.txt" "$(rand)"
write_secret "team_cloud_encryption_key.txt" "$(rand)"
write_secret "team_cloud_minio_root_password.txt" "$(rand)"

echo "Team Cloud secrets are ready in deploy/team-cloud/secrets"
