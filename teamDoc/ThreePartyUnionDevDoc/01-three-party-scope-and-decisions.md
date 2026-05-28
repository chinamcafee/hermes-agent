# 01. 三方范围和关键决策

日期：2026-05-24

## 背景

当前 Hermes 已经具备本地 `SOUL.md` 人格、`/personality` 预设人格、Team Cloud Go 团队记忆、Hermes CLI Team Bridge、Desktop Soul 页面和本地个人记忆备份。新需求要求把“人格”提升为团队模式的一等治理对象，并把本地个人资源备份从单一 memory 扩展为 memory + soul。

## 三方职责

| 组件 | 新增职责 | 不负责 |
| --- | --- | --- |
| Team Cloud Go | 管理团队父人格、团队父人格版本、团队父人格备份、恢复、审计和 Dashboard UI。 | 不管理成员本地 `SOUL.md`，不直接读写 Desktop 文件系统。 |
| Hermes Agent CLI/API Server | 同步团队父人格、合成本地人格和父人格、注入 effective soul、提供 `/soul` 与 `/cloud-backup` CLI/JSON 契约。 | 不在本地管理团队父人格的最终版本；团队父人格权威源只在 Team Cloud Go。 |
| Hermes Desktop | 通过 Hermes Agent Bridge 展示团队父人格、本地人格、合并人格和云备份操作。 | 不直连 Team Cloud Go 业务 API，不直接编辑团队父人格；编辑入口跳转 Dashboard 或调用未来 Bridge。 |

## 关键决策

### 决策 1：团队父人格是本地人格的父级约束

team mode 下最终人格由三段组成：

1. 团队父人格：Team Cloud Go 权威内容。
2. 冲突规则：任何冲突均以团队父人格为准。
3. 本地人格：当前 profile 的 `SOUL.md`，仅在不冲突时补充个人偏好。

这种方式不做不可验证的“语义冲突自动改写”。合并结果是可展示、可缓存、可审计的有效系统提示词。

### 决策 2：Team Cloud Go 只管理团队父人格，不管理本地人格

本地人格与个人记忆一样属于成员本地 profile 数据。无论是否加入团队，本地人格都可以通过 `/cloud-backup soul ...` 备份到用户配置的 MinIO/S3-compatible 对象存储。

### 决策 3：备份入口统一为 `/cloud-backup`

旧 `/memory-backup` 只覆盖个人记忆，无法承载本地人格。由于项目尚未上线部署，旧入口不保留兼容层，直接删除并替换为：

```bash
/cloud-backup config ...
/cloud-backup memory schedule|backup|history|restore ...
/cloud-backup soul schedule|backup|history|restore ...
```

MinIO/S3 配置共用；具体对象按 resource type 分路径保存，不能混在同一个 prefix 下。

### 决策 4：Desktop 只消费 Hermes Agent Bridge

Desktop 的 Soul 页面和 Cloud Backup 页面只调用 Hermes Agent Bridge。Desktop 不直接调用 Team Cloud Go 的 team soul、backup、auth 或 member API。

## 非目标

- 不要求 Team Cloud Go 管理每个成员的本地人格。
- 不要求第一版自动理解并删除本地人格中的冲突句子。
- 不要求 Desktop 复制 Team Cloud Dashboard 的团队父人格编辑器。
- 不要求提供 `/memory-backup` 兼容别名；后续实现必须直接删除旧入口。

## 成功标准

- team mode 下 Hermes Agent prompt 中包含团队父人格，并明确高于本地人格。
- CLI 和 Desktop 能展示团队父人格、本地人格、合并人格三个维度。
- local mode 下仍只展示本地人格，不拉取 Team Cloud Go。
- Team Cloud Go Dashboard 能查看、编辑、备份、恢复团队父人格。
- `/cloud-backup memory ...` 和 `/cloud-backup soul ...` 对象路径分离。
