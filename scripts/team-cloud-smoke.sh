#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"

if [[ ! -d team_cloud ]]; then
  echo "Missing Go Team Cloud service directory: team_cloud" >&2
  exit 2
fi

(
  cd team_cloud
  go test ./...
  go vet ./...
  go build -o /tmp/hermes-team-cloud-server ./cmd/team-cloud-server
)

if [[ -d team_cloud/dashboard ]]; then
  (
    cd team_cloud/dashboard
    npm test -- --run
    npm run type-check
    npm run build
  )
fi

scripts/team-cloud-spicedb-schema-ci.sh --static-only

echo "Team Cloud Go smoke checks passed"
