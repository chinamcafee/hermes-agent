# P4-02 Helm chart

日期：2026-05-23
状态：Implemented
前置：`P4-01 Compose hardening`

## 目标

本步骤提供 Team Cloud Beta/GA 部署的 Helm chart 基线。Chart 覆盖 `values.yaml`、secret 管理、ingress TLS、backup persistence 和安装/升级 jobs，供 P4-03 offline bundle、P4-09 upgrade/rollback 和 P5 安装指南复用。

## 工件

| 工件 | 用途 |
| --- | --- |
| `deploy/team-cloud/helm/hermes-team-cloud/Chart.yaml` | Chart 元数据。 |
| `deploy/team-cloud/helm/hermes-team-cloud/values.yaml` | 镜像、config、secret、ingress、persistence 和 jobs 默认值。 |
| `deploy/team-cloud/helm/hermes-team-cloud/templates/secret.yaml` | 可创建 chart 内 secret，或通过 `secrets.existingSecret` 复用外部 secret。 |
| `deploy/team-cloud/helm/hermes-team-cloud/templates/pvc.yaml` | backup persistence PVC。 |
| `deploy/team-cloud/helm/hermes-team-cloud/templates/deployment-*.yaml` | API、worker、web workloads。 |
| `deploy/team-cloud/helm/hermes-team-cloud/templates/ingress.yaml` | `networking.k8s.io/v1` ingress 和 TLS。 |
| `deploy/team-cloud/helm/hermes-team-cloud/templates/job-*.yaml` | migration、SpiceDB schema、MinIO bucket 初始化 jobs。 |
| `tests/team_cloud/test_helm_chart.py` | 静态 contract 测试，固定 P4-02 要求。 |

## Values Contract

- `images.*.repository/tag/pullPolicy` 必须显式配置，默认 tag 不使用 `latest`。
- `secrets.create=true` 时 chart 创建 Opaque Secret；`secrets.existingSecret` 非空时 workload 复用外部 Secret。
- `ingress.enabled=false` 默认关闭外部入口，但 `ingress.tls.enabled=true` 保留生产 TLS contract。
- `persistence.enabled=true`，backup PVC 默认挂载到 `/backups`。
- `jobs.migrations`、`jobs.spicedbSchema`、`jobs.minioBuckets` 默认启用并设置 `ttlSecondsAfterFinished`。

## 非目标

- 不打包离线镜像和 chart archive；P4-03 处理。
- 不执行真实 Kubernetes 部署；P5-13 处理新环境 deployment smoke。
- 不替代外部 PostgreSQL/SpiceDB/MinIO/Casdoor 的生产安装规范；本 chart 固定 Team Cloud workload 和初始化 contract。

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_helm_chart.py
scripts/run_tests.sh tests/team_cloud/test_helm_chart.py tests/team_cloud/test_compose_hardening.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check tests/team_cloud/test_helm_chart.py tests/team_cloud/test_compose_hardening.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile tests/team_cloud/test_helm_chart.py tests/team_cloud/test_compose_hardening.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
