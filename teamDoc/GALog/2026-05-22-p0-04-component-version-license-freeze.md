# GALog 2026-05-22 P0-04 第三方组件版本和许可证冻结

## 工作粒度

- 工作包：`P0-04 第三方组件版本和许可证冻结`
- 类型：项目统筹 / 供应链基线
- 执行日期：2026-05-22
- 执行者：Codex

## 输入依据

- `teamDoc/GAStep/02-phase-0-1-foundation-steps.md`
- `teamDoc/02-technical-selection.md`
- `teamDoc/11-source-accessible-component-policy.md`
- `teamDoc/GADoc/P0-03-adr-suite.md`
- `pyproject.toml`
- `uv.lock`

## 产出

- 新增：`teamDoc/GADoc/P0-04-component-version-license-freeze.md`

## 执行记录

1. 核对 `P0-04` 要求：冻结 Casdoor、SpiceDB、PostgreSQL、pgvector、MinIO、FastAPI、客户端 SDK 版本。
2. 读取当前 Hermes 依赖锁定状态，保留 `fastapi==0.133.1`、`uvicorn[standard]==0.41.0`、`pydantic==2.13.4`、`httpx[socks]==0.28.1`、`PyJWT[crypto]==2.12.1`。
3. 通过 PyPI 元数据核查 SQLAlchemy、Alembic、asyncpg、authzed、casdoor、minio、pgvector helper 的最新版本和许可证。
4. 通过 GitHub tag / Docker Hub tag 核查核心服务的源码定位、镜像 tag 和 linux/amd64、linux/arm64 digest。
5. 发现 MinIO 公开 Docker Hub 镜像最新稳定 tag 停在 `RELEASE.2025-09-07T16-13-09Z`，而源码仓库有更新 tag；已在冻结文档中将其登记为 P0-11 必须跟踪的供应链/许可证风险。

## 决策摘要

1. Casdoor 冻结到 `v3.60.1`，运行镜像使用 `casbin/casdoor:3.60.1`。
2. SpiceDB 冻结到 `v1.53.0`，运行镜像使用 `authzed/spicedb:v1.53.0`。
3. PostgreSQL 冻结到 `18.4`，pgvector 冻结到 `v0.8.2`；GA 路线优先构建自有 Postgres+pgvector 镜像，避免浮动 `pg18` tag。
4. MinIO 临时冻结到 `RELEASE.2025-09-07T16-13-09Z`，AGPL-3.0 和镜像发布节奏进入风险登记。
5. Python 依赖冻结为 exact pins；`psycopg` 因 LGPL-3.0-only 不作为默认依赖。

## 验证计划

- 检查冻结文档包含核心服务、镜像 digest、Python 依赖、许可证风险、后续执行约束。
- 检查冻结文档覆盖 `P0-04` 点名的全部组件。
- 验证后更新 `progress-tracker.md` 中 `P0-04` 为 `Done`。

## 后续

- 进入 `P0-05 本地拓扑设计`。
- 在 `P0-11 风险登记册` 中登记 MinIO AGPL、MinIO 镜像发布节奏、psycopg LGPL、pgvector 自建镜像可复现性。
