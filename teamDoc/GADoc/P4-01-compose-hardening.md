# P4-01 Compose hardening

日期：2026-05-23
状态：Implemented
前置：`P3 数据治理与权限硬化`

## 目标

本步骤把本地 Compose 从 P1/P3 的功能栈提升为 Beta 验证栈。范围包含长期服务 healthcheck、固定 backup mount、dev TLS mount 和 smoke 覆盖，不引入生产级证书签发或 Helm/offline bundle；这些由 P4-02 和 P4-03 承接。

## 工件

| 工件 | 用途 |
| --- | --- |
| `deploy/team-cloud/compose.yaml` | 为长期服务补齐 healthcheck，并固定 `/backups` 与 `/etc/hermes-team-cloud/tls` mount。 |
| `deploy/team-cloud/.env.example` | 暴露 backup mount 与 dev TLS 文件路径的本地默认值。 |
| `deploy/team-cloud/backups/.gitkeep` | 保留本地 backup mount 目录；实际备份文件不入库。 |
| `deploy/team-cloud/certs/dev/.gitkeep` | 保留 dev TLS mount 目录；实际 `*.pem` 不入库。 |
| `tests/team_cloud/test_compose_hardening.py` | 静态 contract 测试，固定 P4-01 hardening 要求。 |

## Healthcheck Contract

长期运行服务必须声明 `healthcheck.test`、`interval`、`timeout` 和 `retries`：

- `postgres`
- `casdoor`
- `mailpit`
- `spicedb`
- `minio`
- `team-api`
- `team-worker`
- `team-web`
- `hermes-runtime`

初始化 job 仍通过 `depends_on.condition: service_completed_successfully` 表达完成状态，不作为长期服务 healthcheck 目标。

## Mount Contract

- `postgres`、`minio` 和 `team-api` 挂载 `./backups:/backups`，为 P4-06 备份恢复演练提供固定路径。
- `team-api`、`team-worker`、`team-web` 和 `hermes-runtime` 挂载 `./certs/dev:/etc/hermes-team-cloud/tls:ro`，为本地 dev TLS 证书注入提供固定路径。
- `.gitignore` 忽略 `backups/**` 和 `certs/dev/*.pem`，只保留 `.gitkeep`。

## 非目标

- 不生成真实证书。
- 不启用生产 TLS ingress。
- 不实现 Helm chart 或 offline bundle。

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_compose_hardening.py
scripts/run_tests.sh tests/team_cloud/test_compose_hardening.py tests/team_cloud/test_local_compose_stack.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check tests/team_cloud/test_compose_hardening.py tests/team_cloud/test_local_compose_stack.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile tests/team_cloud/test_compose_hardening.py tests/team_cloud/test_local_compose_stack.py tests/team_cloud/test_platform_foundation_suite.py
scripts/team-cloud-foundation-smoke.sh
```
