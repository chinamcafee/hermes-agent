# P1-03 本地 Compose 栈

日期：2026-05-22
状态：Implemented
前置：`P1-02 配置和 secret 管理`

## 目标

本步骤把 `P0-05 本地拓扑设计` 落成可检查的本地 compose 工件。范围包含服务编排、端口、网络、volume、file secret 注入、初始化 job 和 smoke test 入口，不包含完整 OIDC callback、JWT middleware、AuthZ middleware 或 P1-04 之后的数据库迁移实现。

## 工件

| 工件 | 用途 |
| --- | --- |
| `deploy/team-cloud/compose.yaml` | 本地 Team Cloud 全栈 compose 文件。 |
| `deploy/team-cloud/.env.example` | 非敏感默认值、端口和 image tag。 |
| `deploy/team-cloud/team-cloud.Dockerfile` | Team API、worker、runtime placeholder 的本地镜像。 |
| `deploy/team-cloud/init/postgres-init.sh` | 幂等创建 PostgreSQL role/database 并启用 pgvector。 |
| `deploy/team-cloud/casdoor/app.conf.template` | Casdoor PostgreSQL 配置模板。 |
| `deploy/team-cloud/web-shell/index.html` | P1 web shell，占位到 P1-16 Web 登录壳。 |
| `scripts/team-cloud-secrets.sh` | 生成本地 file secrets。 |
| `scripts/team-cloud-smoke.sh` | 本地 smoke test 入口。 |

## 服务

| Service | 说明 |
| --- | --- |
| `postgres` | 使用 `pgvector/pgvector:0.8.2-pg18-trixie`，host port `54329`。 |
| `postgres-init` | 创建 `hermes_team`、`casdoor`、`spicedb` 三个数据库和对应 role。 |
| `casdoor` | 使用 `casbin/casdoor:3.60.1`，host port `18000`。 |
| `spicedb` | 使用 `authzed/spicedb:v1.53.0`，gRPC `50051`，metrics `9091`。 |
| `spicedb-schema-load` | 使用 P0-07 `schema-v0.zed` 写入本地 SpiceDB。 |
| `minio` | 使用 P0-04 冻结 tag，S3 API `19000`，console `19001`。 |
| `minio-init` | 创建 P0-09 定义的五个 buckets。 |
| `team-api` | 运行 `team_cloud.api:create_app`，host port `8780`。 |
| `team-worker` | 运行 P1 worker heartbeat loop。 |
| `team-web` | P1 web shell，host port `8781`。 |
| `hermes-runtime` | P2 runtime bridge 前的占位服务，仅依赖 Team API。 |

## Secret 规则

- `.env.example` 不包含 secret 明文。
- `scripts/team-cloud-secrets.sh` 生成 `deploy/team-cloud/secrets/*.txt`。
- Compose 的 Team API 和 worker 只读取 `TEAM_CLOUD_*_FILE`。
- `deploy/team-cloud/.gitignore` 忽略生成的 secret 和 generated 内容。

## 验证

静态验证：

```bash
scripts/run_tests.sh tests/team_cloud/test_local_compose_stack.py
docker compose -f deploy/team-cloud/compose.yaml --env-file deploy/team-cloud/.env.example config
```

本地 smoke：

```bash
scripts/team-cloud-smoke.sh
```

Smoke 顺序与 P0-05 一致：生成 secrets、校验 compose、启动栈、检查 Team API health/readiness、检查 MinIO ready、查询 pgvector extension、运行 MinIO bucket init 和 SpiceDB schema load。
