# 09. 调研引用

## 本地 Hermes 代码与文档

- `agent/memory_provider.py` - MemoryProvider 生命周期和扩展 hook。
- `agent/memory_manager.py` - 内置记忆 + 单个外部 provider 的调度规则、context fencing。
- `agent/agent_init.py` - memory provider 初始化时透传 `user_id/chat_id/thread_id/gateway_session_key`。
- `gateway/session.py` - `SessionSource`、`build_session_key()`、shared multi-user session。
- `gateway/run.py` - Gateway 创建 `AIAgent` 时透传平台身份。
- `gateway/slash_access.py` - slash command access control，可作为 Gateway 命令权限迁移参考。
- `gateway/platforms/api_server.py` - OpenAI-compatible API Server、Bearer auth、`X-Hermes-Session-Key`。
- `hermes_cli/web_server.py` - 本地 Dashboard、ephemeral session token、dashboard plugin API；不适合作为团队云认证基础。
- `plugins/memory/honcho/` - 现有 memory provider 参考。
- `plugins/memory/mem0/` - 现有 memory provider 参考。
- `plugins/memory/supermemory/` - context strip 和 container 思路参考。
- `plugins/memory/retaindb/` - write-behind queue 参考。
- `website/docs/guides/team-telegram-assistant.md` - 现有团队 Telegram 助手教程。
- `website/docs/user-guide/features/memory-providers.md` - 记忆 provider 总览。
- `website/docs/user-guide/features/web-dashboard.md` - Dashboard 能力和安全边界。
- `website/docs/user-guide/features/api-server.md` - API Server 能力。
- `website/docs/developer-guide/memory-provider-plugin.md` - Memory provider 插件编写指南。

## 指定 GA 技术栈

- Casdoor repository: https://github.com/casdoor/casdoor
- Casdoor documentation: https://casdoor.org/docs/
- Casdoor SCIM documentation: https://casdoor.org/docs/category/scim/
- SpiceDB repository: https://github.com/authzed/spicedb
- SpiceDB documentation: https://authzed.com/docs/spicedb
- SpiceDB schema concepts: https://authzed.com/docs/spicedb/concepts/schema
- PostgreSQL documentation: https://www.postgresql.org/docs/
- pgvector repository: https://github.com/pgvector/pgvector
- pgvector PostgreSQL news: https://www.postgresql.org/about/news/pgvector-080-released-2952/
- MinIO repository: https://github.com/minio/minio
- MinIO documentation: https://min.io/docs/minio/container/index.html

## AnySearch 核验摘要

本轮通过 `$anysearch` 检索确认：

- Casdoor GitHub 描述支持 OAuth/OIDC/SAML/CAS/LDAP/SCIM/WebAuthn/TOTP/MFA，许可证为 Apache-2.0。
- SpiceDB 是 Google Zanzibar-inspired 的开源细粒度授权数据库，通过 schema、relationships 和 permission checks 表达资源权限，许可证为 Apache-2.0。
- pgvector 是 PostgreSQL 向量相似度搜索扩展，支持 HNSW/IVFFlat 等索引能力，许可证为 PostgreSQL License。
- MinIO 是 S3-compatible object storage，源码可访问，许可证为 AGPL-3.0，商业化/私有化部署需要许可证审查。
