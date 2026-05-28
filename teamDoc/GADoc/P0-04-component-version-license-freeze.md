# P0-04 第三方组件版本和许可证冻结

日期：2026-05-22
状态：Accepted for P0 execution
前置：`P0-03 ADR 套件`

## 冻结原则

1. P0-04 只冻结版本、许可证、源码 tag/commit 和镜像来源，不在本步骤引入生产代码依赖。
2. 运行时镜像在 `P1-03 本地 compose 栈` 必须继续 pin 到 digest；本文先冻结可复现的 tag 和已查到的 linux/amd64、linux/arm64 digest。
3. Python 依赖沿用本仓库 exact pin 风格；新增 Team Cloud 依赖进入 `pyproject.toml` 时必须同时更新 `uv.lock`。
4. 组件必须满足 `teamDoc/11-source-accessible-component-policy.md` 的源码可访问要求。
5. MinIO 因 AGPL-3.0 和公开镜像停更节奏，必须作为 `P0-11 风险登记册` 的显式风险项继续跟踪。

## 核心服务冻结

| 组件 | 冻结版本 | 运行镜像 / 制品 | 源码定位 | 许可证 | GA 处理 |
| --- | --- | --- | --- | --- | --- |
| Casdoor | `v3.60.1` | `casbin/casdoor:3.60.1` | `casdoor/casdoor@88fb414c3304e9dbf37ff752c64d51acb5bced74` | Apache-2.0 | 默认 AuthN/OIDC；P1 compose 用该 tag，再 pin digest。 |
| SpiceDB | `v1.53.0` | `authzed/spicedb:v1.53.0` | `authzed/spicedb@b15effc560eb7e8078a6a7e0347e2d460266ca6d` | Apache-2.0 | 默认 AuthZ/ReBAC；schema CI 和 relationship outbox 基于该版本。 |
| PostgreSQL | `18.4` | `postgres:18.4-trixie` | PostgreSQL 18.4 release | PostgreSQL License | canonical data store；P1 优先自建 Team Postgres 镜像以固定 pgvector。 |
| pgvector | `v0.8.2` | 从 `pgvector/pgvector:v0.8.2` 源码装入 Team Postgres 镜像 | `pgvector/pgvector@cab9da72c04353f143bb06b42ab70a403daac64a` | PostgreSQL License | 与 PostgreSQL 18.4 组合构建；不依赖滚动 `pg18` tag 作为 GA 真相。 |
| MinIO | `RELEASE.2025-09-07T16-13-09Z` | `minio/minio:RELEASE.2025-09-07T16-13-09Z` | `minio/minio@07c3a429bfed433e49018cb0f78a52145d4bedeb` | AGPL-3.0 | 默认对象存储的临时冻结；进入 Beta 前必须完成许可证和供应链审查。 |

## 镜像 digest 记录

| 镜像 tag | linux/amd64 digest | linux/arm64 digest | 备注 |
| --- | --- | --- | --- |
| `casbin/casdoor:3.60.1` | `sha256:75a00a3d1df3aae26bf1ad1afc81b354a950b9f24238dc02e2cc500dda759ea5` | `sha256:9f9665f11e7e32a093b938ee9eef6d7c63818c87155bd4589e1e33a5bec85172` | Docker Hub tag updated 2026-05-19。 |
| `authzed/spicedb:v1.53.0` | `sha256:3b330c2978c093a4c5060169cc3975df601e9bbd856c4b9772493d144949942c` | `sha256:698b1982f6a516dddcb97adb2042659ce5ad3cc2014bdbd90e900af5fdcae918` | Docker Hub tag updated 2026-05-13。 |
| `postgres:18.4-trixie` | `sha256:41da01536bc3ae26308cefb0c57235e7488001360bdb15191eb0b7955b570299` | `sha256:f6902dfddea256a7bf788aefabbf10e5305ea348693caa4c741795559044001a` | Base image for custom Postgres + pgvector build。 |
| `pgvector/pgvector:0.8.2-pg18-trixie` | `sha256:77f3220c156665b2b198f3bcb859bdd6c12f6dd614e0a835f36826e21eaeb475` | `sha256:490964491a68a5e3801ea45ed9321dc9d5107bfcf80199476a2f8d8a24947220` | 仅作 dev fallback；GA 以自建 PostgreSQL 18.4 + pgvector 0.8.2 为准。 |
| `minio/minio:RELEASE.2025-09-07T16-13-09Z` | `sha256:a1a8bd4ac40ad7881a245bab97323e18f971e4d4cba2c2007ec1bedd21cbaba2` | `sha256:9966a92a734f9411e32f4f41d7d9d826fcdc0f68c4e20b70295bd4e7c11f8a2f` | 公开 Docker Hub 最新稳定 tag 截至本次核查。 |

## Go 服务端依赖冻结

| 用途 | 组件 | 冻结版本 | 许可证 | 处理方式 |
| --- | --- | --- | --- | --- |
| Team API runtime | Go toolchain | `1.24.5` | BSD-style | `team_cloud/go.mod` 使用 `go 1.24.0` 和 `toolchain go1.24.5`。 |
| PostgreSQL driver | `github.com/jackc/pgx/v5` | `v5.7.6` | MIT | 用于 `team_cloud/internal/store/postgres`，通过 Go module 精确版本锁定。 |

## Python 参考实现依赖冻结

`team_cloud/` 当前为 Go 服务端源码；旧 Python 服务端已经删除，首次上线服务端以该 Go 目录为准。

| 用途 | 包 | 冻结版本 | 许可证 | 处理方式 |
| --- | --- | --- | --- | --- |
| Team API 参考实现 | FastAPI / `fastapi` | `0.133.1` | MIT | 仅用于未上线 Python 参考实现；不作为首次上线服务端。 |
| ASGI server | `uvicorn[standard]` | `0.41.0` | BSD-3-Clause | 与本仓库 `web` extra 当前锁定版本一致。 |
| 数据模型 | `pydantic` | `2.13.4` | MIT | 与本仓库 runtime 当前锁定版本一致。 |
| HTTP/JWKS/OIDC | `httpx[socks]` | `0.28.1` | BSD-3-Clause | 与本仓库 runtime 当前锁定版本一致。 |
| JWT 验签 | `PyJWT[crypto]` | `2.12.1` | MIT | 沿用本仓库 CVE 修复 pin；升级需单独安全评估。 |
| DB ORM/Core | `SQLAlchemy` | `2.0.49` | MIT | P1 新增；用于迁移、query builder 和 async session。 |
| DB migration | `alembic` | `1.18.4` | MIT | P1 新增；所有 schema 通过 migration 管理。 |
| DB async driver | `asyncpg` | `0.31.0` | Apache-2.0 | 默认驱动；已在本仓库 `matrix` extra 中锁定。 |
| DB sync driver | `psycopg` | `3.3.4` | LGPL-3.0-only | 不作为默认依赖；仅在 Alembic/工具链确需 sync driver 时引入并走许可证审查。 |
| SpiceDB SDK | `authzed` | `1.24.4` | Apache-2.0 | P1 新增；封装为 Team Cloud AuthzClient。 |
| Casdoor SDK | `casdoor` | `1.41.0` | Apache-2.0 | P1 新增；只用于管理同步，不参与 JWT trust boundary。 |
| MinIO SDK | `minio` | `7.2.20` | Apache-2.0 | P1 新增；对象上传、manifest 校验和 presigned URL。 |
| pgvector Python helper | `pgvector` | `0.4.2` | MIT | 可选 helper；canonical 查询仍以 SQLAlchemy/SQL 为准。 |

客户端 SDK 冻结范围包括 `authzed==1.24.4`、`casdoor==1.41.0`、`minio==7.2.20` 和可选 `pgvector==0.4.2`。

## 许可证风险

1. `MinIO`：AGPL-3.0 是当前最大合规风险。GA 前必须确认是否修改源码、是否随私有化部署分发、是否触发网络服务源码提供义务、是否需要商业授权或替代 S3 后端。
2. `psycopg`：LGPL-3.0-only 不进入默认依赖。若后续迁移工具必须使用，需要在 `P0-11` 或 `P5-14` 法务包中登记。
3. `pgvector/pgvector`：许可证与 PostgreSQL 兼容，但必须保存源码 tag 和构建脚本，避免 `pg18` 浮动 tag 造成不可复现。
4. 所有 GitHub Actions 后续新增 action 必须按 commit SHA pin，并在注释中标注版本名。

## 后续执行约束

- `P0-05` 本地拓扑必须使用本文服务边界和端口规划，明确 digest pin 策略。
- `P1-01` 新建 Team Cloud package 时，新增依赖不得偏离本文版本；如必须偏离，先更新本文和 `progress-tracker.md` 阻塞项。
- `P1-03` compose 禁止使用 `latest` tag。
- `P1-04` migrations 必须验证 PostgreSQL 18.4 + pgvector 0.8.2 的扩展启用路径。
- `P5-02` SBOM 和许可证包必须包含本文所有组件和源码链接。

## 核查来源

- Casdoor GitHub tags and license: `https://github.com/casdoor/casdoor`
- Casdoor image tags: `https://hub.docker.com/r/casbin/casdoor/tags`
- SpiceDB GitHub releases and license: `https://github.com/authzed/spicedb`
- SpiceDB image tags: `https://hub.docker.com/r/authzed/spicedb/tags`
- PostgreSQL versions RSS: `https://www.postgresql.org/versions.rss`
- PostgreSQL image tags: `https://hub.docker.com/_/postgres/tags`
- pgvector GitHub tags and license: `https://github.com/pgvector/pgvector`
- pgvector image tags: `https://hub.docker.com/r/pgvector/pgvector/tags`
- MinIO GitHub tags and license: `https://github.com/minio/minio`
- MinIO image tags: `https://hub.docker.com/r/minio/minio/tags`
- Python package metadata: `https://pypi.org/`
