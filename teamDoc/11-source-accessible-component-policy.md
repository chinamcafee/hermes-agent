# 11. 源码可访问组件准入策略

本文件是所有实施文档的硬约束：团队版 Hermes Agent 的新增核心组件必须源码可访问。本轮 GA 方案限定为 Casdoor、SpiceDB、PostgreSQL/pgvector、MinIO 和自研 Team Cloud。

## 1. 准入规则

必需组件必须满足：

- 源码地址可访问，能对应到运行镜像或发布版本。
- 许可证明确，并通过商业化/私有化部署审查。
- 支持自托管。
- 数据可完整导出。
- 安全边界可审计。

禁止作为核心依赖：

- 仅闭源托管身份服务。
- 仅闭源托管授权服务。
- 不提供服务端源码的 memory provider。
- 不可导出数据的向量库、对象存储或审计服务。
- 许可证不允许目标交付模式的组件。

## 2. 默认组件清单

| 组件 | 用途 | 默认决策 | 源码/许可证状态 | 备注 |
| --- | --- | --- | --- | --- |
| Casdoor | 身份认证、SSO、OIDC/SAML/SCIM、MFA | 默认 AuthN | GitHub 可访问，Apache-2.0 | Team Cloud 不保存密码 |
| SpiceDB | 资源级授权、ReBAC、权限解释 | 默认 AuthZ | GitHub 可访问，Apache-2.0 | 所有业务资源权限边界 |
| PostgreSQL | 结构化 canonical data | 默认数据库 | 源码可访问，PostgreSQL License | 所有业务表带 `org_id` |
| pgvector | 向量相似度搜索 | 默认记忆向量索引 | GitHub 可访问，PostgreSQL License | HNSW/IVFFlat，canonical memory 仍在 PostgreSQL |
| MinIO | 对象存储、个人记忆备份、导出包 | 默认对象存储 | GitHub 可访问，AGPL-3.0 | AGPL 影响需法务确认 |
| Go 标准库 `net/http` | Team API | 首次上线服务框架 | Go 源码可访问，BSD-style | `team_cloud_go/` 单二进制，适合 Kubernetes 部署 |

## 3. 不进入默认路线

| 组件 | 原因 |
| --- | --- |
| Keycloak/ZITADEL/Ory | 身份方案已限定为 Casdoor |
| OpenFGA/Cerbos/Casbin | 资源授权方案已限定为 SpiceDB |
| 独立向量库 | 默认限定为 PostgreSQL/pgvector |
| 第三方 memory SaaS | 不作为 canonical memory 或权限边界 |
| 闭源商业服务 | 不符合源码可访问核心约束 |

## 4. MinIO 许可证注意

MinIO 使用 AGPL-3.0。进入 GA 前必须确认：

- 是否修改 MinIO 源码。
- 是否以网络服务形式提供给客户。
- 私有化部署包是否需要附带源码和许可证声明。
- 企业客户是否接受 AGPL 义务。
- 是否需要购买商业支持或准备替代方案。

## 5. 实施检查点

Phase 0：

- 输出 `third_party_components.md`。
- 固定组件版本、镜像来源、源码 commit/tag。
- 生成许可证报告。
- 本地 compose 可启动全栈。

Beta 前：

- 完成 SBOM。
- 完成镜像漏洞扫描。
- 完成源码和许可证归档。
- 完成备份恢复演练。

GA 前：

- 所有核心组件有升级策略。
- 所有核心组件有备份恢复策略。
- 所有核心组件有安全配置基线。
- 所有核心组件有故障降级 Runbook。
