# P5-03 安装指南

日期：2026-05-23
状态：Implemented
前置：`P4-01 Compose hardening`、`P4-02 Helm chart`、`P4-03 Offline bundle`、`P5-02 SBOM 和许可证包`

## 目标

本步骤固定 Team Cloud GA 安装指南 contract，覆盖 `compose`、`helm`、`offline_bundle` 三条安装路径，给出安装前检查、首次登录 `first_login`、健康检查和常见故障排查入口。该指南把 P1 本地部署、P4 Helm/offline 交付和 P5 发布包串成一条可重复执行的 GA 安装路径。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/install_guide.py` | `build_install_guide_package()` 生成安装指南 JSON contract。 |
| `scripts/team-cloud-install-guide.py` | 写出 install guide JSON artifact。 |
| `teamDoc/GADoc/artifacts/release/team-cloud-install-guide-v0.json` | P5-03 安装指南 artifact。 |
| `tests/team_cloud/test_install_guide.py` | P5-03 contract 测试。 |

## 安装路径

| 路径 | 入口 | 场景 |
| --- | --- | --- |
| `compose` | `deploy/team-cloud/compose.yaml` | 单机、本地验证、开发或客户预检环境。 |
| `helm` | `deploy/team-cloud/helm/hermes-team-cloud/Chart.yaml` | Kubernetes staging/production。 |
| `offline_bundle` | `deploy/team-cloud/offline/install.sh` | 离线或受限网络环境，必须同时携带 manifest、镜像目录和 checksums。 |

### compose

```bash
docker compose -f deploy/team-cloud/compose.yaml up --build
scripts/team-cloud-foundation-smoke.sh
```

`compose` 安装必须先准备 `deploy/team-cloud/secrets/*.txt`，并按 `P1-22` 检查端口、secret file 和健康检查。

### helm

```bash
helm upgrade --install hermes-team-cloud deploy/team-cloud/helm/hermes-team-cloud --atomic --wait
scripts/team-cloud-foundation-smoke.sh
```

`helm` 安装必须先完成 values 审核、secret 注入、Casdoor redirect allowlist 和 ingress/TLS 配置。当前仓库不假定本机安装了 Helm；CI 可继续使用 chart 静态测试和 artifact 校验。

### offline_bundle

```bash
scripts/team-cloud-offline-bundle.sh --manifest deploy/team-cloud/offline/manifest.yaml
deploy/team-cloud/offline/install.sh --manifest deploy/team-cloud/offline/manifest.yaml
```

`offline_bundle` 安装必须包含 `deploy/team-cloud/offline/manifest.yaml`、镜像目录和 `checksums`。导入后先校验 manifest，再执行安装脚本，最后运行 foundation smoke。

## Preflight

安装前必须确认：

- `python_3_11`：本地 Python 版本与测试环境一致。
- `container_runtime`：Docker、Compose 或 Kubernetes runtime 可用。
- `ports_available`：本地 `8780`、`8781`、`18000`、`50051`、`19000`、`19001` 未被占用。
- `secrets_present`：所有 `TEAM_CLOUD_*_FILE` 对应 secret 文件存在。
- `casdoor_redirect_urls`：浏览器访问域名、issuer 和 redirect URL 一致。
- `spicedb_preshared_key`：SpiceDB key 与 Team API secret file 一致。
- `minio_bucket_policy`：bucket、access key、secret key 和 lifecycle 配置已准备。

## first_login

首次登录使用 `Casdoor` 作为身份提供方：

1. `owner_bootstrap`：第一个 Org Owner 通过 Casdoor 登录 Team Web。
2. `create_organization`：创建组织并确认 slug 不可变。
3. `invite_admin`：邀请至少 1 个管理员，避免单点账号风险。
4. `verify_spicedb_relationships`：通过 Permission Explorer 确认 owner/admin/member relationship。
5. `run_foundation_smoke`：运行 `scripts/team-cloud-foundation-smoke.sh` 固定安装证据。

## 健康检查

安装后依次检查：

- `team_api`：`GET /healthz`、`GET /readyz`、`GET /metrics`。
- `casdoor`：OIDC discovery、JWKS、authorize redirect。
- `spicedb`：schema loaded、permission check 正反用例。
- `postgres`：migration plan、pgvector extension、基础 CRUD。
- `minio`：bucket bootstrap、manifest、signed URL。
- `worker`：outbox、backup、embedding/extraction worker。
- `web_shell`：登录壳、成员/团队/角色页、Permission Explorer。

## Troubleshooting

| Key | 症状 | 处理 |
| --- | --- | --- |
| `spicedb_schema_load_failure` | 权限 check 失败或 schema 未加载。 | 检查 `spicedb-migrate`、`spicedb-schema-load`、`TEAM_CLOUD_SPICEDB_PRESHARED_KEY_FILE`，运行 `tests/team_cloud/test_spicedb_schema_ci.py`。 |
| `casdoor_oidc_redirect_failure` | 登录跳转失败或 issuer mismatch。 | 检查 redirect allowlist、`TEAM_CLOUD_JWT_ISSUER` 和 client_id。 |
| `postgres_migration_failure` | `/readyz` migration check 失败。 | 检查 `TEAM_CLOUD_DATABASE_URL_FILE`，运行 `tests/team_cloud/test_postgres_migrations.py`。 |
| `minio_manifest_failure` | 备份 bucket 或 manifest 初始化失败。 | 检查 MinIO endpoint、access key、secret key 和 bucket policy，运行 `tests/team_cloud/test_minio_manifest.py`。 |

## 运行

```bash
scripts/team-cloud-install-guide.py --output teamDoc/GADoc/artifacts/release/team-cloud-install-guide-v0.json
```

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_install_guide.py
scripts/run_tests.sh tests/team_cloud/test_install_guide.py tests/team_cloud/test_deployment_docs.py tests/team_cloud/test_compose_hardening.py tests/team_cloud/test_helm_chart.py tests/team_cloud/test_offline_bundle.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/install_guide.py scripts/team-cloud-install-guide.py tests/team_cloud/test_install_guide.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/install_guide.py scripts/team-cloud-install-guide.py tests/team_cloud/test_install_guide.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/release/team-cloud-install-guide-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
