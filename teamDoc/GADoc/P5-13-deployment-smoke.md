# P5-13 Deployment smoke

日期：2026-05-23
状态：Implemented
前置：`GTC-30..GTC-86`

## 目标

本步骤固定当前 Team Cloud GA deployment smoke contract，覆盖 Go 服务端构建、Kubernetes manifest、Dashboard static build 和 Offline bundle。旧 Python compose/Helm/offline 资产已经退役。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/deploy/kubernetes/team-cloud-go.yaml` | 当前 Kubernetes manifest。 |
| `scripts/team-cloud-smoke.sh` | 当前 Go 服务端、Dashboard 和静态 schema smoke。 |
| `teamDoc/GADoc/artifacts/release/team-cloud-deployment-smoke-v0.json` | P5-13 deployment smoke artifact。 |
| `scripts/team-cloud-offline-bundle.sh` | 当前离线资料包生成脚本。 |

## Gates

| Gate | Target | Command |
| --- | --- | --- |
| `go_service_smoke` | Team Cloud Go | `cd team_cloud && go test ./... && go vet ./... && go build -o /tmp/hermes-team-cloud-server ./cmd/team-cloud-server` |
| `dashboard_smoke` | Dashboard | `cd team_cloud/dashboard && npm test -- --run && npm run type-check && npm run build` |
| `manifest_static_smoke` | Kubernetes | `scripts/team-cloud-spicedb-schema-ci.sh --static-only` |
| `offline_bundle_smoke` | Offline bundle | `scripts/team-cloud-offline-bundle.sh` |

## GA matrix

P5-13 覆盖：

- `GA-REL-001`：Go Team Cloud service builds and passes unit/integration tests。
- `GA-REL-002`：Dashboard static build passes typecheck and tests。
- `GA-REL-003`：Kubernetes manifest is the active deployment entry。
- `GA-REL-004`：offline bundle contains current Go service assets and checksums。

## Fresh environment smoke

`fresh_ga_environment` 是新环境部署 smoke 契约。当前 Go 版主路径验证记录：

- `scripts/team-cloud-smoke.sh` 覆盖 Go test/vet/build、Dashboard test/typecheck/build 和 schema static check。
- `scripts/team-cloud-foundation-smoke.sh` 覆盖 Hermes Agent CLI/runtime 与 Team Cloud provider 集成。
- `scripts/team-cloud-isolation-smoke.sh` 覆盖身份、隔离和团队上下文边界。
- `scripts/team-cloud-offline-bundle.sh` 生成 `team_cloud/offline/dist/hermes-team-cloud-offline` 并写入 `SHA256SUMS`。

完整新环境执行命令：

```bash
scripts/team-cloud-smoke.sh
scripts/team-cloud-foundation-smoke.sh
scripts/team-cloud-isolation-smoke.sh
scripts/team-cloud-offline-bundle.sh
```

offline bundle 在本地 GA smoke 中以 checksum 完整性验证关闭；air-gapped 安装环境继续使用：

```bash
scripts/team-cloud-offline-bundle.sh
```

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
