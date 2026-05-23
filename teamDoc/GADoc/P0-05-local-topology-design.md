# P0-05 本地拓扑设计

日期：2026-05-22
状态：Accepted for P0 execution
前置：`P0-04 第三方组件版本和许可证冻结`

## 目标

本地拓扑必须让新开发者在 P1 通过一条文档路径启动企业版最小全栈，并能验证 Casdoor 登录、SpiceDB 授权、PostgreSQL/pgvector 记忆库、MinIO 备份对象和 Hermes runtime bridge。P0-05 只冻结拓扑设计，实际 compose 文件在 `P1-03 本地 compose 栈` 落地。

## 服务拓扑

```text
host browser / CLI
  -> team-web:8781
  -> team-api:8780
  -> casdoor:18000
  -> minio-console:19001

team-web
  -> team-api
  -> casdoor authorize endpoint

team-api
  -> casdoor JWKS / OIDC metadata
  -> spicedb gRPC
  -> postgres hermes_team database
  -> minio object API
  -> hermes-runtime worker queue

team-worker
  -> postgres hermes_team database
  -> spicedb relationship write
  -> minio backup/export upload

hermes-runtime
  -> team-api Memory API
  -> team-api Tool Policy API
  -> existing Hermes tools and gateways

postgres
  -> hermes_team database
  -> casdoor database
  -> spicedb database
```

本地 compose 使用一个 PostgreSQL service 承载三个数据库，降低开发者启动成本；每个数据库使用独立 role、密码和 migration/seed 流程。生产和 Helm 部署允许将三者拆分成独立实例。

## 端口规划

| Service | Host port | Container port | 暴露范围 | 用途 |
| --- | ---: | ---: | --- | --- |
| `team-web` | `8781` | `3000` | host | Admin Console / chat shell。 |
| `team-api` | `8780` | `8780` | host + internal | Team API、OIDC callback、health。 |
| `casdoor` | `18000` | `8000` | host + internal | OIDC/AuthN 管理台和 authorize endpoint。 |
| `spicedb` | `50051` | `50051` | host optional + internal | gRPC AuthZ；host 暴露仅用于本地调试。 |
| `spicedb-metrics` | `9091` | `9090` | host optional | metrics/debug；P4 再接入 dashboards。 |
| `postgres` | `54329` | `5432` | host optional + internal | 本地 psql 调试；应用使用 internal DNS。 |
| `minio` | `19000` | `9000` | host + internal | S3 API。 |
| `minio-console` | `19001` | `9001` | host | 本地对象检查。 |
| `mailpit` | `18025` | `8025` | host | Casdoor 本地邮件预览。 |
| `mailpit-smtp` | `11025` | `1025` | internal + host optional | Casdoor SMTP。 |

端口避开 Hermes 现有 CLI/API 常见端口和系统默认 `5432`、`9000`，减少本机冲突。

## 网络

| Network | Members | 规则 |
| --- | --- | --- |
| `team-edge` | `team-web`, `team-api`, `casdoor`, `minio`, `mailpit` | 仅承接 host 入口和浏览器回调。 |
| `team-control` | `team-api`, `team-worker`, `hermes-runtime`, `casdoor`, `spicedb` | 身份、授权和 runtime 控制面。 |
| `team-data` | `team-api`, `team-worker`, `postgres`, `minio`, `spicedb` | 数据面；除调试端口外不暴露到 host。 |

`postgres` 不加入 `team-edge`。`hermes-runtime` 不直接访问 `spicedb`，工具权限和记忆权限统一通过 `team-api` policy/memory endpoint。

## Volumes

| Volume | Service | 内容 | 备份策略 |
| --- | --- | --- | --- |
| `team_postgres_data` | `postgres` | `hermes_team`、`casdoor`、`spicedb` 数据库 | P3 纳入 PostgreSQL base backup/WAL 策略。 |
| `team_minio_data` | `minio` | 个人备份、组织导出、附件、文档原文、restore staging | P3 纳入对象生命周期和复制策略。 |
| `team_casdoor_conf` | `casdoor` | 本地生成的 Casdoor app config | 由 seed job 可重建，不作为 canonical data。 |
| `team_spicedb_cache` | `spicedb` | 本地 cache / dispatch metadata | 可重建，不备份。 |
| `team_runtime_home` | `hermes-runtime` | 本地 Hermes profile、tool cache、临时日志 | 不承载 canonical memory；可清理重建。 |

P1 compose 默认不把 secrets 放入 volume；所有 secret 通过 file secret 注入。

## 初始化数据

启动顺序：

1. `postgres-init`：创建 role/database：
   - `hermes_team` / `hermes_team_user`
   - `casdoor` / `casdoor_user`
   - `spicedb` / `spicedb_user`
   - 在 `hermes_team` 中启用 `vector` extension。
2. `casdoor-init`：生成本地 organization、admin user、Team Web app、Team API app、OIDC redirect URI。
3. `spicedb-migrate`：初始化 datastore schema。
4. `spicedb-schema-load`：写入 P0-07 `schema.zed` 和 permission fixtures。
5. `minio-init`：创建 buckets：
   - `hermes-personal-backups`
   - `hermes-org-exports`
   - `hermes-attachments`
   - `hermes-document-sources`
   - `hermes-restore-staging`
6. `team-migrate`：执行 P0-08/P1-04 Alembic migrations。
7. `team-seed`：创建本地 `org_local`、`team_default`、`project_default`、`member_admin`，并写入 SpiceDB relationships。
8. `hermes-runtime-init`：生成本地 Hermes profile，配置 TeamMemoryProvider endpoint 和 TeamToolPolicyHook endpoint。

所有 seed 必须幂等；重复执行不能产生重复组织、用户、bucket 或 relationship。

## Secret 注入

目录规划：

```text
deploy/team-cloud/
  compose.yaml
  .env.example
  secrets/
    .gitkeep
  generated/
    casdoor/
    postgres/
    spicedb/
    minio/
```

规则：

- `.env.example` 只放非敏感默认值、端口和 image tag。
- `secrets/*.txt` 由 `scripts/team-cloud-secrets.sh` 生成，默认 `.gitignore`。
- Compose services 使用 `*_FILE` 或 Docker compose `secrets:` 读取密码。
- Team API 只通过 file secret 读取：
  - `TEAM_CLOUD_JWT_ISSUER`
  - `TEAM_CLOUD_CASDOOR_CLIENT_SECRET_FILE`
  - `TEAM_CLOUD_SPICEDB_PRESHARED_KEY_FILE`
  - `TEAM_CLOUD_DATABASE_URL_FILE`
  - `TEAM_CLOUD_MINIO_SECRET_KEY_FILE`
  - `TEAM_CLOUD_ENCRYPTION_KEY_FILE`
- 禁止在 compose、日志、health output 中打印 secret 值。

## 健康检查

| Service | Health check | Ready 条件 |
| --- | --- | --- |
| `postgres` | `pg_isready -U hermes_team_user -d hermes_team` | 三个数据库可连接，`vector` extension 可查询。 |
| `casdoor` | HTTP `GET /api/health`，失败时 fallback TCP `:8000` | OIDC discovery 和 JWKS 可访问。 |
| `spicedb` | gRPC health probe `:50051` | datastore migrations 完成，schema revision 可读。 |
| `minio` | HTTP `GET /minio/health/ready` | 五个 buckets 存在且 service account 可写。 |
| `team-api` | HTTP `GET /healthz` and `GET /readyz` | DB、Casdoor metadata、SpiceDB check、MinIO put/list 全部通过。 |
| `team-worker` | internal heartbeat row + `/healthz` | outbox scan loop、backup scheduler、relationship writer active。 |
| `team-web` | HTTP `GET /` | 静态资源加载，OIDC config endpoint 可读。 |
| `hermes-runtime` | `GET /healthz` or worker heartbeat | 能拉取 Team API config，能写 runtime event heartbeat。 |
| `mailpit` | HTTP `GET /` | SMTP endpoint 可连接。 |

`depends_on` 只能表达启动顺序，不能替代 readiness；P1 必须实现 `wait-for-ready` job 或 health-gated migrations。

## 本地验收路径

P1 compose 完成后，本拓扑的 smoke test 顺序固定为：

1. `docker compose -f deploy/team-cloud/compose.yaml up -d --wait`
2. 登录 Casdoor，本地 admin 能进入 Team Web。
3. Team API 验证 id_token 的 issuer/audience/signature/exp。
4. Team API 对 `org_local` 执行 SpiceDB `check member read` 成功，对未授权 user 失败。
5. PostgreSQL 执行 `select extversion from pg_extension where extname = 'vector'` 返回 `0.8.2`。
6. MinIO 写入并读取 `hermes-personal-backups/.../smoke.jsonl.enc`。
7. Hermes runtime 使用 TeamMemoryProvider 返回 `Personal Memory` 和 `Team Shared Memory` 两段空结果。
8. 关闭成员后，Team API、Gateway identity resolver 和 runtime run 均 fail closed。

## 后续执行约束

- `P0-06` 必须基于本拓扑跑通 Casdoor OIDC token 验证。
- `P0-07` schema 必须覆盖本拓扑 seed 的 organization/team/project/session/memory/document/tool/backup。
- `P0-08` PostgreSQL schema 必须支持本拓扑所有初始化数据和 health checks。
- `P0-09` MinIO key/manifest 规范必须覆盖本拓扑五个 bucket。
- `P1-03` compose 文件不得新增未在本文登记的核心服务；如必须新增，先更新本文件和进度追踪。
