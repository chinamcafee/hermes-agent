#!/usr/bin/env bash
set -euo pipefail

mode="${1:---static-only}"
manifest="team_cloud/deploy/kubernetes/team-cloud-go.yaml"

check_schema() {
  if [[ ! -f "${manifest}" ]]; then
    echo "missing ${manifest}" >&2
    return 1
  fi
  rg -q "definition organization" "${manifest}"
  rg -q "permission write_team" "${manifest}"
  if rg -q "definition team" "${manifest}"; then
    echo "retired team/workgroup SpiceDB resource found in ${manifest}" >&2
    return 1
  fi
}

case "${mode}" in
  --static-only)
    check_schema
    ;;
  --print-zed-command)
    check_schema
    echo "kubectl -n hermes-team-cloud get configmap hermes-team-cloud-go-authz-schema -o jsonpath='{.data.schema\\.json}' | zed validate --schema -"
    ;;
  --run-zed)
    check_schema
    if ! command -v zed >/dev/null 2>&1; then
      echo "zed CLI not found; install authzed/zed or use --static-only" >&2
      exit 127
    fi
    kubectl -n hermes-team-cloud get configmap hermes-team-cloud-go-authz-schema -o jsonpath='{.data.schema\.json}' | zed validate --schema -
    ;;
  *)
    echo "usage: $0 [--static-only|--print-zed-command|--run-zed]" >&2
    exit 2
    ;;
esac
