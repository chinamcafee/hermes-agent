#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

NAMESPACE="${NAMESPACE:-hermes-team-cloud}"
RELEASE="${RELEASE:-hermes-team-cloud}"
VALUES_FILE="${VALUES_FILE:-values.yaml}"
CHART_ARCHIVE="charts/hermes-team-cloud-0.1.0.tgz"

if [[ ! -f SHA256SUMS ]]; then
  echo "Missing SHA256SUMS" >&2
  exit 2
fi

sha256sum -c SHA256SUMS

for image_archive in images/*.tar; do
  docker load -i "$image_archive"
done

helm upgrade --install "$RELEASE" "$CHART_ARCHIVE" \
  --namespace "$NAMESPACE" \
  --create-namespace \
  --values "$VALUES_FILE"

