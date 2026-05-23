#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

MANIFEST="deploy/team-cloud/offline/manifest.yaml"
CHART_DIR="deploy/team-cloud/helm/hermes-team-cloud"
OUT_DIR="${OUT_DIR:-deploy/team-cloud/offline/dist/hermes-team-cloud-offline}"

if [[ ! -f "$MANIFEST" ]]; then
  echo "Missing offline manifest: $MANIFEST" >&2
  exit 2
fi

if ! command -v helm >/dev/null 2>&1; then
  echo "helm is required to package the offline chart" >&2
  exit 2
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required to save offline images" >&2
  exit 2
fi

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR/charts" "$OUT_DIR/images"

cp "$MANIFEST" "$OUT_DIR/manifest.yaml"
cp deploy/team-cloud/offline/install.sh "$OUT_DIR/install.sh"
cp "$CHART_DIR/values.yaml" "$OUT_DIR/values.yaml"

helm package "$CHART_DIR" --destination "$OUT_DIR/charts"

python - "$MANIFEST" "$OUT_DIR/images.txt" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path

import yaml

manifest_path = Path(sys.argv[1])
images_path = Path(sys.argv[2])
manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
images_path.write_text(
    "\n".join(image["ref"] for image in manifest["images"]) + "\n",
    encoding="utf-8",
)
PY

while IFS= read -r image_ref; do
  archive_name="$(echo "$image_ref" | tr '/:' '--').tar"
  docker save "$image_ref" -o "$OUT_DIR/images/$archive_name"
done < "$OUT_DIR/images.txt"

(
  cd "$OUT_DIR"
  sha256sum manifest.yaml install.sh values.yaml images.txt charts/*.tgz images/*.tar > SHA256SUMS
)

echo "Offline bundle written to $OUT_DIR"
