# 01. GA Work Package Register

本表是后续追踪和排期的主索引。所有任务都围绕指定 GA 技术栈：Casdoor、SpiceDB、PostgreSQL/pgvector、MinIO、Team Cloud、Hermes runtime。

## P0：架构冻结

| ID | 工作包 | 主要产出 | 前置 | 估算 |
| --- | --- | --- | --- | ---: |
| P0-01 | GA 范围冻结 | GA/non-GA 清单、裁剪规则 | 无 | 1 |
| P0-02 | 代码边界审计 | Hermes core/plugin/Gateway/API 需改动清单 | P0-01 | 1 |
| P0-03 | ADR 套件 | Casdoor、SpiceDB、pgvector、MinIO、Hermes 集成 ADR | P0-01 | 1.5 |
| P0-04 | 第三方组件版本和许可证冻结 | 版本、镜像、源码 tag、许可证报告初稿 | P0-03 | 1 |
| P0-05 | 本地拓扑设计 | compose 拓扑、端口、secret、网络、volume 约定 | P0-03 | 1 |
| P0-06 | Casdoor OIDC 验证 | 登录回调、JWT 样例、JWKS 验证记录 | P0-05 | 1 |
| P0-07 | SpiceDB schema v0 | schema.zed、权限矩阵、正反样例 | P0-03 | 1.5 |
| P0-08 | PostgreSQL/pgvector schema v0 | migration 草案、索引草案、查询样例 | P0-03 | 1 |
| P0-09 | MinIO 备份模型 v0 | bucket、key、manifest、加密策略草案 | P0-03 | 1 |
| P0-10 | GA 验收矩阵 | 安全、性能、备份恢复、发布出口标准 | P0-03 | 1 |
| P0-11 | 风险登记册 | Top risks、owner、缓解策略 | P0-10 | 0.5 |
| P0-12 | 交付基线计划 | 阶段里程碑、团队配置、issue 模板 | P0-01 | 0.5 |

小计：`12 人周`。

## P1：平台基础

| ID | 工作包 | 主要产出 | 前置 | 估算 |
| --- | --- | --- | --- | ---: |
| P1-01 | Team Cloud repo/package 骨架 | `team_cloud/`、API、worker、web 目录 | P0 | 2 |
| P1-02 | 配置和 secret 管理 | config loader、env schema、secret 分层 | P1-01 | 1.5 |
| P1-03 | 本地 compose 栈 | Casdoor、SpiceDB、PostgreSQL+pgvector、MinIO | P0-05 | 3 |
| P1-04 | PostgreSQL 基础迁移 | org/user/member/team/project/audit/outbox 基表 | P1-01 | 2 |
| P1-05 | Casdoor OIDC 接入 | authorize/callback/token/JWKS 校验 | P1-03 | 2.5 |
| P1-06 | JWT 中间件 | issuer/audience/expiry/nonce/status 校验 | P1-05 | 2 |
| P1-07 | Casdoor 同步 worker | user/org/group lazy upsert、reconcile、禁用传播 | P1-06 | 3 |
| P1-08 | PAT 和 service account | token hash、scope、过期、撤销、审计 | P1-04 | 2.5 |
| P1-09 | SpiceDB client | check、batch check、lookup、write relationships | P1-03 | 2.5 |
| P1-10 | SpiceDB schema CI | schema 校验、fixture、正反测试 | P0-07 | 2 |
| P1-11 | Relationship outbox | outbox 表、worker、幂等、dead letter | P1-09 | 3 |
| P1-12 | AuthZ middleware | API permission gate、fail closed、cache key | P1-09 | 2 |
| P1-13 | 组织/团队/成员 API | CRUD、邀请、禁用、membership 同步 | P1-12 | 3 |
| P1-14 | Audit 基础能力 | audit_events 表、中间件、查询 API | P1-04 | 2 |
| P1-15 | MinIO client 和 manifest | bucket bootstrap、signed URL、object manifest | P1-03 | 2 |
| P1-16 | Web 登录壳 | Casdoor login callback、session、org switcher | P1-05 | 2.5 |
| P1-17 | Web 成员/团队/角色页 | 列表、创建、禁用、角色展示、错误态 | P1-13 | 3.5 |
| P1-18 | 权限解释最小页 | actor/resource/permission check UI | P1-09 | 2 |
| P1-19 | 平台基础测试 | API、auth、outbox、MinIO manifest 集成测试 | P1-13 | 3 |
| P1-20 | 平台安全负测 | 伪造 token、禁用用户、跨 org 管理拒绝 | P1-19 | 2 |
| P1-21 | 观测基线 | metrics、structured logs、health checks | P1-01 | 2 |
| P1-22 | 基础部署文档 | local setup、config、troubleshooting | P1-03 | 1.5 |

小计：`47 人周`。

## P2：记忆与 Hermes 集成

| ID | 工作包 | 主要产出 | 前置 | 估算 |
| --- | --- | --- | --- | ---: |
| P2-01 | 记忆迁移表 | memory_items、embeddings、events、observations、review | P1-04 | 3 |
| P2-02 | pgvector 查询层 | HNSW 索引、personal/team SQL、query explain | P2-01 | 3.5 |
| P2-03 | Memory CRUD API | list/create/update/delete/archive/restore | P2-01 | 3 |
| P2-04 | Prefetch pipeline | query embedding、候选、SpiceDB check、rerank、format | P2-02 | 4 |
| P2-05 | Memory relationships | personal owner、team parent、reviewer relationships | P1-11 | 2 |
| P2-06 | Embedding worker | batch embedding、重试、模型版本、回填 | P2-01 | 3 |
| P2-07 | Memory extraction worker | observation 消费、候选生成、confidence、source trace | P2-01 | 3.5 |
| P2-08 | Review Queue API | approve/reject/edit-before-approve、审计 | P2-07 | 3 |
| P2-09 | 去重和冲突检测 | checksum、semantic duplicate、contradiction review | P2-07 | 2.5 |
| P2-10 | PII/secret detector | 写入拦截、敏感级别、测试样例 | P2-03 | 2.5 |
| P2-11 | TeamMemoryProvider 插件 | initialize/prefetch/sync_turn/tool routing | P2-04 | 4 |
| P2-12 | Memory tools | search/remember/propose/promote/forget/backup_now | P2-11 | 3 |
| P2-13 | sync_turn observation | turn metadata、tool summaries、context fencing | P2-11 | 2 |
| P2-14 | `AIAgent.team_context` | init 参数、memory init 透传、向后兼容测试 | P1-01 | 3 |
| P2-15 | API Server identity headers | 可信 header、校验、agent 创建透传 | P2-14 | 2.5 |
| P2-16 | Gateway identity resolver | external identity resolve、绑定提示、session key prefix | P1-13 | 3.5 |
| P2-17 | Web Chat 入口 | submit、stream、event viewer、错误态 | P2-14 | 3.5 |
| P2-18 | 云会话历史 | cloud_sessions/messages/tool_calls 写入和查询 | P2-17 | 3 |
| P2-19 | Runtime event bridge | tool start/complete、memory read IDs、run events | P2-18 | 2 |
| P2-20 | 隔离测试套件 | Alice/Bob、org A/B、team/project 正反测试 | P2-04 | 4 |
| P2-21 | 记忆性能基线 | prefetch P95、pgvector explain、top-k 调优 | P2-04 | 2 |
| P2-22 | SessionDB 迁移工具 | 本地历史导入、unmapped 身份处理 | P2-18 | 2.5 |
| P2-23 | 记忆和 runtime 文档 | API、provider、迁移、运维说明 | P2-20 | 1.5 |

小计：`66.5 人周`。

## P3：数据治理与权限硬化

| ID | 工作包 | 主要产出 | 前置 | 估算 |
| --- | --- | --- | --- | ---: |
| P3-01 | 工具风险 taxonomy | safe/network/file/terminal/destructive/secret 映射 | P2-14 | 1.5 |
| P3-02 | TeamToolPolicyHook | pre_tool_call、SpiceDB check、fail closed | P3-01 | 3.5 |
| P3-03 | 高危工具审批 | approval 集成、审批超时、审计 | P3-02 | 2.5 |
| P3-04 | Tool audit | cloud_tool_calls、deny/allow/approval events | P3-02 | 2 |
| P3-05 | Personal backup policy | cadence、retention、include options、UI/API | P2-03 | 2.5 |
| P3-06 | 加密 JSONL exporter | manifest、checksum、envelope encryption | P3-05 | 3.5 |
| P3-07 | MinIO upload/lifecycle | upload、signed URL、retention cleanup | P3-06 | 2.5 |
| P3-08 | Restore preview | conflict detection、diff、staging | P3-06 | 3.5 |
| P3-09 | Restore execute | merge/overwrite/archive-old、embedding rebuild | P3-08 | 3 |
| P3-10 | 组织导出 | metadata、sessions、memory、relationships snapshot | P2-18 | 3 |
| P3-11 | 删除请求 | request、approval、scheduled execution、audit | P3-10 | 2.5 |
| P3-12 | Hard delete worker | PostgreSQL/SpiceDB/MinIO 清理和重试 | P3-11 | 3 |
| P3-13 | Retention policies | session/tool/memory/audit retention 策略 | P3-11 | 2 |
| P3-14 | Break-glass | 双人审批、短期授权、通知和审计 | P1-18 | 3 |
| P3-15 | Permission Explorer GA | 关系路径、近期变更、deny reason | P1-18 | 3 |
| P3-16 | Audit 高级能力 | filters、export、sensitive read views | P1-14 | 3 |
| P3-17 | Usage/quotas | token、runs、backup size、org quotas | P2-18 | 2 |
| P3-18 | Backup/restore tests | backup、download、restore、checksum mismatch | P3-09 | 3 |
| P3-19 | AuthZ chaos tests | SpiceDB outage、outbox lag、dead letter fail closed | P3-02 | 2 |
| P3-20 | 数据治理文档 | export/delete/backup/break-glass runbook | P3-18 | 1.5 |
| P3-21 | 通知系统 | backup failure、break-glass、review backlog | P3-05 | 1.5 |
| P3-22 | Admin UX 收尾 | empty/error/permission states、批量操作确认 | P3-16 | 2.5 |

小计：`49 人周`。

## P4：Beta 验证

| ID | 工作包 | 主要产出 | 前置 | 估算 |
| --- | --- | --- | --- | ---: |
| P4-01 | Compose hardening | healthcheck、volumes、TLS/dev cert、backup mount | P3 | 1.5 |
| P4-02 | Helm chart | values、secrets、ingress、persistence、jobs | P4-01 | 3 |
| P4-03 | Offline bundle | images、charts、checksums、install script | P4-02 | 2 |
| P4-04 | Metrics dashboard | Team API、SpiceDB、pgvector、MinIO、worker | P3 | 2.5 |
| P4-05 | Logs/traces | request_id、run_id、audit correlation | P4-04 | 1.5 |
| P4-06 | 备份恢复演练 | PostgreSQL、SpiceDB、MinIO、Casdoor restore evidence | P3 | 3.5 |
| P4-07 | Load test scripts | chat、prefetch、backup、permission check | P2/P3 | 2.5 |
| P4-08 | Security test suite | token spoofing、prompt injection、tool bypass | P3 | 3 |
| P4-09 | Upgrade/rollback | migrations、image rollback、schema compatibility | P4-02 | 2.5 |
| P4-10 | Pilot onboarding | 试点团队导入、培训、反馈表 | P4-01 | 1.5 |
| P4-11 | Bug triage process | severity、SLA、release blocker rules | P4-10 | 0.5 |
| P4-12 | Cost/quotas tuning | quota defaults、usage dashboard、limit alerts | P3-17 | 1.5 |
| P4-13 | Chaos drills | SpiceDB/MinIO/PostgreSQL partial failure | P4-06 | 2 |
| P4-14 | Beta 文档 | pilot install、known issues、feedback guide | P4-10 | 1.5 |
| P4-15 | i18n/accessibility pass | 中文/英文关键文案、键盘可用性 | P3-22 | 1 |
| P4-16 | 性能调优 | pgvector index、batch check、worker concurrency | P4-07 | 2 |
| P4-17 | Pilot telemetry review | usage、errors、latency、security events 周报 | P4-10 | 1 |
| P4-18 | Beta exit report | blocker list、GA readiness、剩余风险 | P4-17 | 0.5 |

小计：`28 人周`。

## P5：GA 发布

| ID | 工作包 | 主要产出 | 前置 | 估算 |
| --- | --- | --- | --- | ---: |
| P5-01 | 最终安全评审 | threat model、权限矩阵、漏洞复测 | P4 | 2.5 |
| P5-02 | SBOM 和许可证包 | SBOM、license report、MinIO AGPL 说明 | P4 | 1.5 |
| P5-03 | 安装指南 | compose/helm/offline 安装文档 | P4 | 1.5 |
| P5-04 | 管理员和用户手册 | org/member/memory/backup/tool policy 使用说明 | P4 | 2 |
| P5-05 | API 文档 | Team API、memory API、authz API、examples | P4 | 1.5 |
| P5-06 | Runbook 汇总 | backup/restore/outage/upgrade/rollback | P4 | 2 |
| P5-07 | Release notes | breaking changes、upgrade notes、known issues | P5-03 | 0.5 |
| P5-08 | GA sign-off | sign-off 表、owner、证据链接 | P5-01 | 0.5 |
| P5-09 | Support playbook | 首响、诊断命令、日志采集、升级路径 | P5-06 | 1 |
| P5-10 | Migration guide | SessionDB 导入、旧 memory provider 数据迁移 | P2-22 | 1.5 |
| P5-11 | Training material | 管理员培训、成员培训、FAQ | P5-04 | 0.5 |
| P5-12 | Final regression | 全量 e2e、安全、备份恢复、升级回归 | P5-01 | 2 |
| P5-13 | Deployment smoke | 新环境安装、基础聊天、备份、恢复 smoke | P5-03 | 1 |
| P5-14 | Legal/compliance package | 数据处理说明、许可证、审计说明 | P5-02 | 1 |
| P5-15 | Post-GA backlog | deferred items、known risks、下一版本计划 | P5-08 | 0.5 |

小计：`18 人周`。
