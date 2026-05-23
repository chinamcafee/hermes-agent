# P1-22 基础部署文档

日期：2026-05-22
状态：Implemented
前置：`P1-03 本地 compose 栈`、`P1-19 平台基础测试`、`P1-21 观测基线`

## 目标

本文档给出 P1 Team Cloud 本地部署、配置、secret、健康检查、smoke 测试和 Troubleshooting 路径。P1 部署目标是让新开发者可以用同一套 compose 栈启动 Casdoor、SpiceDB、PostgreSQL、MinIO、Team API、worker 和 web shell。

## 本地启动

从仓库根目录运行：

```bash
docker compose -f deploy/team-cloud/compose.yaml up --build
```

常用验证：

```bash
curl -fsS http://localhost:8780/healthz
curl -fsS http://localhost:8780/readyz
curl -fsS http://localhost:8780/metrics
scripts/team-cloud-foundation-smoke.sh
```

停止并保留 volume：

```bash
docker compose -f deploy/team-cloud/compose.yaml down
```

重置本地数据：

```bash
docker compose -f deploy/team-cloud/compose.yaml down -v
```

## 本地端口

| 组件 | 端口 | 用途 |
| --- | --- | --- |
| Team API | `8780` | `/healthz`、`/readyz`、`/metrics`、Team API。 |
| Team Web | `8781` | 静态 web shell。 |
| Casdoor | `18000` | OIDC 登录和管理控制台。 |
| Mailpit UI | `18025` | 本地邮件 UI。 |
| Mailpit SMTP | `11025` | 本地 SMTP。 |
| PostgreSQL | `54329` | pgvector/PostgreSQL 开发连接。 |
| SpiceDB gRPC | `50051` | SpiceDB 权限服务。 |
| SpiceDB metrics/http | `9091` | SpiceDB metrics/http。 |
| MinIO S3 | `19000` | MinIO object API。 |
| MinIO Console | `19001` | MinIO console。 |

## 配置和 secret

compose 通过 Docker secrets 注入敏感值，Team API 使用 `_FILE` 变量读取 secret file：

| 环境变量 | Secret file |
| --- | --- |
| `TEAM_CLOUD_DATABASE_URL_FILE` | `deploy/team-cloud/secrets/team_cloud_database_url.txt` |
| `TEAM_CLOUD_CASDOOR_CLIENT_SECRET_FILE` | `deploy/team-cloud/secrets/team_cloud_casdoor_client_secret.txt` |
| `TEAM_CLOUD_SPICEDB_PRESHARED_KEY_FILE` | `deploy/team-cloud/secrets/team_cloud_spicedb_preshared_key.txt` |
| `TEAM_CLOUD_MINIO_SECRET_KEY_FILE` | `deploy/team-cloud/secrets/team_cloud_minio_secret_key.txt` |
| `TEAM_CLOUD_ENCRYPTION_KEY_FILE` | `deploy/team-cloud/secrets/team_cloud_encryption_key.txt` |

非敏感本地配置由 compose environment 设置：

- `TEAM_CLOUD_ENVIRONMENT=local`
- `TEAM_CLOUD_BIND_HOST=0.0.0.0`
- `TEAM_CLOUD_API_PORT=8780`
- `TEAM_CLOUD_JWT_ISSUER=http://localhost:18000`
- `TEAM_CLOUD_CASDOOR_BASE_URL=http://casdoor:8000`
- `TEAM_CLOUD_CASDOOR_CLIENT_ID=hermes-team-api`
- `TEAM_CLOUD_SPICEDB_ENDPOINT=spicedb:50051`
- `TEAM_CLOUD_MINIO_ENDPOINT=http://minio:9000`

不要把 secret 文件内容提交到仓库。

## 健康检查

Team API：

- `GET /healthz`：进程基础健康。
- `GET /readyz`：配置和 migration plan ready checks。
- `GET /metrics`：Prometheus 文本格式请求计数。

compose 健康检查：

- PostgreSQL 使用 `pg_isready`。
- Casdoor 使用 `/api/health` 或 TCP fallback。
- SpiceDB 使用 gRPC 端口探测。
- MinIO 使用 `/minio/health/ready`。
- Team API 使用 `/healthz`。

## Smoke 测试

P1 foundation smoke：

```bash
scripts/team-cloud-foundation-smoke.sh
```

覆盖：

- API：组织、团队、成员、permission explain。
- Auth：Casdoor OIDC、JWT middleware、PAT/service account、Casdoor sync worker。
- AuthZ：SpiceDB client、schema CI、AuthZ middleware。
- Outbox：relationship outbox 和成员禁用 relationship delete intent。
- MinIO：bucket、manifest、signed URL。
- Web：登录壳、members/teams/roles、permission panel。
- Security：伪造 token、禁用用户、跨 org 管理拒绝。
- Observability：`/metrics`、structured request events、`/readyz` shape。

## Troubleshooting

### Casdoor

- 症状：OIDC authorize 不能跳转。
- 检查：`http://localhost:18000` 是否可访问，compose 中 `casdoor` service 是否已 started。
- 检查：`TEAM_CLOUD_JWT_ISSUER` 与浏览器访问 issuer 是否一致。
- 处理：重启 `casdoor-init` 后再启动 `casdoor`，必要时 `docker compose -f deploy/team-cloud/compose.yaml down -v` 重建本地数据。

### SpiceDB

- 症状：权限 check 或 schema load 失败。
- 检查：`spicedb-migrate` 是否 completed，`spicedb-schema-load` 是否 completed。
- 检查：`TEAM_CLOUD_SPICEDB_PRESHARED_KEY_FILE` 对应 secret file 是否存在。
- 处理：运行 `scripts/team-cloud-foundation-smoke.sh` 先确认 client、schema CI 和 AuthZ middleware 单元行为。

### PostgreSQL

- 症状：migration 或 API 启动失败。
- 检查：`postgres-init`、`team-migrate` 是否 completed。
- 检查：`TEAM_CLOUD_DATABASE_URL_FILE` 是否指向有效 secret file。
- 处理：如果 schema 不一致，使用 `docker compose -f deploy/team-cloud/compose.yaml down -v` 清理 volume 后重启。

### MinIO

- 症状：bucket bootstrap 或 manifest 写入失败。
- 检查：`minio-init` 是否 completed，`TEAM_CLOUD_MINIO_SECRET_KEY_FILE` 是否存在。
- 检查：`http://localhost:19001` console 是否可访问。
- 处理：先运行 `scripts/run_tests.sh tests/team_cloud/test_minio_manifest.py` 缩小到 manifest 行为，再检查 compose 服务状态。

### Team API

- 症状：`/readyz` 返回 `not_ready`。
- 检查：`checks.config` 和 `checks.migrations`。
- 检查：`TEAM_CLOUD_*_FILE` secret 是否挂载到容器。
- 处理：查看 `team-api` 容器日志，并用 `/metrics` 确认请求是否到达服务。

## 非目标

- 不覆盖生产 TLS、域名、OIDC redirect 白名单自动化。
- 不覆盖 Helm、offline bundle 或升级回滚。
- 不替代 P4/P5 的部署 smoke、备份恢复演练和最终安全评审。
