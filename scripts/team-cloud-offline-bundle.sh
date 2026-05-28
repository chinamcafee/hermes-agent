#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${OUT_DIR:-$ROOT_DIR/team_cloud/offline/dist/hermes-team-cloud-offline}"

cd "$ROOT_DIR"

if [[ ! -d team_cloud ]]; then
  echo "Missing Go Team Cloud service directory: team_cloud" >&2
  exit 2
fi

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"/{service,kubernetes,docs,images}

cp team_cloud/Dockerfile "$OUT_DIR/service/Dockerfile"
cp team_cloud/README.md "$OUT_DIR/service/README.md"
cp team_cloud/deploy/kubernetes/team-cloud-go.yaml "$OUT_DIR/kubernetes/team-cloud-go.yaml"
cp teamDoc/releaseManual/team-cloud-go-minikube-dashboard-manual.md "$OUT_DIR/docs/minikube-dashboard-manual.md"
cp teamDoc/releaseManual/team-cloud-ga-release-manual.md "$OUT_DIR/docs/team-cloud-ga-release-manual.md"

cat > "$OUT_DIR/README.md" <<'EOF'
# Hermes Team Cloud Offline Bundle

This bundle targets the Team Cloud service in `team_cloud/`.

Included:

- `service/Dockerfile`
- `service/README.md`
- `kubernetes/team-cloud-go.yaml`
- `docs/minikube-dashboard-manual.md`
- `docs/team-cloud-ga-release-manual.md`

Set `OFFLINE_IMAGES` to a whitespace-separated list of image refs if you also
want this script to export container image archives under `images/`.
EOF

if [[ -n "${OFFLINE_IMAGES:-}" ]]; then
  if ! command -v docker >/dev/null 2>&1; then
    echo "docker is required when OFFLINE_IMAGES is set" >&2
    exit 2
  fi
  while IFS= read -r image_ref; do
    [[ -z "$image_ref" ]] && continue
    archive_name="$(echo "$image_ref" | tr '/:' '--').tar"
    docker save "$image_ref" -o "$OUT_DIR/images/$archive_name"
  done <<< "$OFFLINE_IMAGES"
fi

(
  cd "$OUT_DIR"
  find . -maxdepth 3 -type f -print0 | sort -z | xargs -0 shasum -a 256 > SHA256SUMS
)

echo "Team Cloud Go offline bundle written to $OUT_DIR"
