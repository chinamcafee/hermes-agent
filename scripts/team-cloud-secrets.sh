#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${OUT_DIR:-$ROOT_DIR/team_cloud/.local/secrets}"
OUT_FILE="$OUT_DIR/team_cloud.env"
FORCE=0

if [[ "${1:-}" == "--force" ]]; then
  FORCE=1
fi

if [[ -e "$OUT_FILE" && "$FORCE" != "1" ]]; then
  echo "Team Cloud local env already exists: $OUT_FILE"
  exit 0
fi

rand() {
  python - <<'PY'
import secrets
print(secrets.token_urlsafe(36))
PY
}

mkdir -p "$OUT_DIR"
umask 077
cat > "$OUT_FILE" <<EOF
# Local development env for the Go Team Cloud service.
# For Kubernetes, create Secrets from equivalent values instead of mounting this file.
TEAM_CLOUD_DATABASE_URL=postgres://hermes:$(rand)@127.0.0.1:5432/hermes_team_cloud?sslmode=disable
TEAM_CLOUD_REDIS_ADDR=127.0.0.1:6379
TEAM_CLOUD_REDIS_PASSWORD=$(rand)
TEAM_CLOUD_SESSION_TTL_SECONDS=86400
TEAM_CLOUD_AUTO_MIGRATE=true
TEAM_CLOUD_DASHBOARD_ENABLED=true
TEAM_CLOUD_DASHBOARD_DIR=$ROOT_DIR/team_cloud/dashboard/out
TEAM_CLOUD_CASDOOR_ISSUER=http://127.0.0.1:8000
TEAM_CLOUD_CASDOOR_AUDIENCE=hermes-team-cloud
TEAM_CLOUD_CASDOOR_JWKS_URL=http://127.0.0.1:8000/.well-known/jwks
TEAM_CLOUD_AUTHZ_MODE=local
TEAM_CLOUD_BACKUP_OBJECT_MODE=disabled
EOF

echo "Team Cloud Go local env written to $OUT_FILE"
