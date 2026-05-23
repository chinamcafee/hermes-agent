# P5-13 Deployment smoke

日期：2026-05-23
状态：Implemented
前置：`P4-01..P4-03`

## 目标

本步骤固定 Team Cloud GA deployment smoke contract，覆盖 Docker Compose、Helm 和 Offline bundle 三种交付形态。GA 补审后，本地已完成 `helm lint` 与 Helm upgrade/rollback 验证；fresh compose smoke 记录 `compose_up_wait`、`foundation_smoke` 和 offline manifest 检查的最终运行结果。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/deployment_smoke.py` | `build_deployment_smoke_package()` 生成 deployment smoke JSON contract。 |
| `scripts/team-cloud-deployment-smoke.py` | 写出 deployment smoke JSON artifact。 |
| `teamDoc/GADoc/artifacts/release/team-cloud-deployment-smoke-v0.json` | P5-13 deployment smoke artifact。 |
| `tests/team_cloud/test_deployment_smoke.py` | P5-13 contract 测试。 |

## Gates

| Gate | Target | Command |
| --- | --- | --- |
| `compose_smoke` | Docker Compose | `scripts/run_tests.sh tests/team_cloud/test_local_compose_stack.py tests/team_cloud/test_compose_hardening.py` |
| `helm_static_smoke` | Helm | `scripts/run_tests.sh tests/team_cloud/test_helm_chart.py`、`helm lint deploy/team-cloud/helm/hermes-team-cloud`、Helm upgrade/rollback |
| `offline_bundle_smoke` | Offline bundle | `scripts/run_tests.sh tests/team_cloud/test_offline_bundle.py` |
| `fresh_environment_smoke` | fresh_ga_environment | `docker compose -f deploy/team-cloud/compose.yaml config`、`docker compose -f deploy/team-cloud/compose.yaml up --build`、`scripts/team-cloud-foundation-smoke.sh`、`deploy/team-cloud/offline/install.sh --manifest deploy/team-cloud/offline/manifest.yaml` |

## GA matrix

P5-13 覆盖：

- `GA-REL-001`：Docker Compose deployment starts full stack with health checks。
- `GA-REL-002`：Helm chart deploys and rolls back cleanly。
- `GA-REL-003`：offline image bundle installs without internet access。

## Fresh environment smoke

`fresh_ga_environment` 是新环境部署 smoke 契约。当前本机验证记录：

- Docker：`Docker version 29.1.2`
- Docker Compose：`Docker Compose version v2.40.3`
- `docker compose -f deploy/team-cloud/compose.yaml config`：passed
- `compose_up_wait`：passed；首次执行发现 `minio/mc:RELEASE.2025-09-07T16-13-09Z` 不存在，已将 mc client image 修正为 `minio/mc:RELEASE.2025-08-13T08-35-41Z`，并为 registry-limited 环境增加镜像覆盖变量。
- `foundation_smoke`：passed
- `helm lint`：passed
- `helm upgrade/rollback`：passed；本地 kind smoke 覆盖首次 install、二次 upgrade（`config.logLevel=DEBUG`）和 rollback。
- `offline_install_manifest_check`：passed

完整新环境执行命令：

```bash
docker compose -f deploy/team-cloud/compose.yaml config
HERMES_TEAM_PLATFORM=linux/amd64 \
TEAM_CLOUD_PYTHON_BASE_IMAGE=mirror.gcr.io/library/python:3.13-slim-bookworm \
ALPINE_IMAGE=mirror.gcr.io/library/alpine:3.22.2 \
MINIO_IMAGE=quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z \
MINIO_MC_IMAGE=quay.io/minio/mc:RELEASE.2025-08-13T08-35-41Z \
MAILPIT_IMAGE=ghcr.io/axllent/mailpit:v1.29.5 \
TEAM_WEB_IMAGE=mirror.gcr.io/library/nginx:1.29.3-alpine \
docker compose -p hermes-team-cloud-ga-smoke -f deploy/team-cloud/compose.yaml up --build --wait --wait-timeout 300
scripts/team-cloud-foundation-smoke.sh
helm lint deploy/team-cloud/helm/hermes-team-cloud
helm upgrade --install hermes-team-cloud-ga-smoke deploy/team-cloud/helm/hermes-team-cloud \
  --namespace hermes-ga-smoke --create-namespace --atomic --wait --timeout 120s \
  --set replicaCount.api=0 --set replicaCount.worker=0 --set replicaCount.web=0 \
  --set jobs.migrations.enabled=false --set jobs.spicedbSchema.enabled=false \
  --set jobs.minioBuckets.enabled=false --set persistence.enabled=false
helm upgrade hermes-team-cloud-ga-smoke deploy/team-cloud/helm/hermes-team-cloud \
  --namespace hermes-ga-smoke --atomic --wait --timeout 120s \
  --set replicaCount.api=0 --set replicaCount.worker=0 --set replicaCount.web=0 \
  --set jobs.migrations.enabled=false --set jobs.spicedbSchema.enabled=false \
  --set jobs.minioBuckets.enabled=false --set persistence.enabled=false \
  --set config.logLevel=DEBUG
helm rollback hermes-team-cloud-ga-smoke 1 --namespace hermes-ga-smoke --wait --timeout 120s
```

offline bundle 在本地 GA smoke 中以 manifest 完整性验证关闭；air-gapped 安装环境继续使用：

```bash
deploy/team-cloud/offline/install.sh --manifest deploy/team-cloud/offline/manifest.yaml
```

## Helm lint

`helm lint` 已在本地补跑并通过。P5-13 artifact 将该状态记录为 `helm_lint_status == passed`，同时通过 `tests/team_cloud/test_helm_chart.py` 覆盖 chart 结构、values 和模板静态契约。

## Acceptance thresholds

- `failed_tests == 0`
- `missing_deployment_artifacts == 0`
- `unreviewed_helm_lint_gap == 0`

## 运行

```bash
scripts/team-cloud-deployment-smoke.py --output teamDoc/GADoc/artifacts/release/team-cloud-deployment-smoke-v0.json
```

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_deployment_smoke.py
scripts/run_tests.sh tests/team_cloud/test_deployment_smoke.py tests/team_cloud/test_local_compose_stack.py tests/team_cloud/test_compose_hardening.py tests/team_cloud/test_helm_chart.py tests/team_cloud/test_offline_bundle.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/deployment_smoke.py scripts/team-cloud-deployment-smoke.py tests/team_cloud/test_deployment_smoke.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/deployment_smoke.py scripts/team-cloud-deployment-smoke.py tests/team_cloud/test_deployment_smoke.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/release/team-cloud-deployment-smoke-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
