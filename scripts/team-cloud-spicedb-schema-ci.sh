#!/usr/bin/env bash
set -euo pipefail

mode="${1:---static-only}"
if [[ -n "${PYTHON:-}" ]]; then
  python_bin="${PYTHON}"
elif [[ -x ".venv/bin/python" ]]; then
  python_bin=".venv/bin/python"
elif [[ -x "venv/bin/python" ]]; then
  python_bin="venv/bin/python"
else
  python_bin="python"
fi

case "${mode}" in
  --static-only)
    "${python_bin}" -m team_cloud.authz.schema_ci --check
    ;;
  --print-zed-command)
    "${python_bin}" -m team_cloud.authz.schema_ci --check --print-zed-command
    ;;
  --run-zed)
    "${python_bin}" -m team_cloud.authz.schema_ci --run-zed
    ;;
  *)
    echo "usage: $0 [--static-only|--print-zed-command|--run-zed]" >&2
    exit 2
    ;;
esac
