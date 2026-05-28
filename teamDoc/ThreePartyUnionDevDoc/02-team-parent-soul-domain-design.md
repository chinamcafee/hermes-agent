# 02. 团队父人格领域设计

日期：2026-05-24

## 领域对象

### Team Parent Soul

团队父人格是团队级系统人格基线，适用于该团队所有成员的 team mode 会话。

建议字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | string | 稳定 ID，例如 `soul_<slug>`。 |
| `org_id` | string | 当前单团队模型下等同团队空间 ID。 |
| `team_id` | string | 第一版可等同 `org_id`，保留扩展。 |
| `status` | string | `active`、`archived`。 |
| `content` | text | Markdown 格式人格内容。 |
| `version` | int | 每次编辑递增。 |
| `checksum_sha256` | string | 内容校验和，用于缓存和同步。 |
| `updated_by_member_id` | string | 最近编辑者。 |
| `created_at` / `updated_at` | timestamp | 审计字段。 |

### Effective Soul

有效人格不是数据库主对象，而是 Hermes Agent 在本地合成的结果。Team 模式下优先使用 Hermes 当前 profile 配置的大模型供应商进行语义合并；本地模式不调用大模型合并。

LLM 合并产物必须保存在本地缓存，不写回 Team Cloud Go 的团队父人格，也不覆盖本地 `SOUL.md`：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `mode` | string | `local` 或 `team`。 |
| `merge_status` | string | `not_required`、`merged`、`failed`。 |
| `team_parent_version` | int | 合并所用团队父人格版本。 |
| `team_parent_checksum` | string | 合并所用团队父人格 checksum。 |
| `local_checksum` | string | 合并所用本地 `SOUL.md` checksum。 |
| `provider` / `model` | string | 执行合并的大模型供应商和模型。 |
| `effective_content` | text | 合并后人格结果。 |
| `error_code` / `error_message` | string | 合并失败时给 CLI/Desktop 展示的结构化错误。 |

大模型不可用时，Hermes Agent 可以生成一个安全降级组合，保证 Team Parent Soul 仍在本地人格之前：

```text
## Team Parent Soul (Authoritative)
<team parent soul content>

## Persona Precedence
When Team Parent Soul conflicts with Local Soul, follow Team Parent Soul.
Local Soul may only add preferences that do not weaken or contradict team rules.

## Local Soul (Member Preference)
<local SOUL.md content>
```

## 合并规则

1. 非 team mode：`effective_soul = local_soul`。
2. team mode 且团队父人格存在：本地人格保存、恢复或重置后，Hermes Agent 立即调用当前 profile 配置的大模型供应商，生成 `effective_soul`。
3. team mode 但父人格暂不可用：
   - 默认 fail open：继续使用本地人格，但 CLI/Desktop 显示 `team_parent_soul_unavailable`。
   - 高安全团队后续可配置 fail closed：阻断 team mode 会话。
4. 本地人格为空：合并结果只包含团队父人格和冲突规则。
5. 团队父人格为空或未配置：合并结果回退本地人格，但状态标记 `team_parent_soul_missing`。
6. 大模型供应商未配置、鉴权失败、超时或调用异常时：
   - 本地 `SOUL.md` 保存仍然成功，不回滚用户编辑。
   - `merge_status=failed`，CLI/Desktop 显示优雅失败提示和 `error_code`。
   - 运行时使用安全降级组合，仍确保团队父人格优先于本地人格。
   - 用户重新配置模型供应商后，可以通过 `/soul merge` 或再次保存本地人格重新触发合并。

2026-05-25 修订：`team mode` 的判定不再依赖团队父人格是否已经配置正文。只要当前 profile 同时具备 Team Cloud URL、有效成员 session token、默认 org/member context 且熔断器允许访问，Hermes Agent 的 `resolve_soul_state()` 就必须返回 `mode=team`，并向 CLI/Desktop 返回三段结构：

- `team_parent_soul`：未配置时仍返回空 content 和版本元数据，而不是 `null`。
- `local_soul`：当前 profile 的 `SOUL.md`。
- `effective_soul`：父人格未配置时等于本地人格，`merge_status=team_parent_missing`。

这样 Desktop 在团队已登录但管理员尚未配置父人格时，仍能展示“团队父人格 / 本地人格 / 合并后人格”三段 UI，并明确提示团队父人格缺失，而不是退回单一本地人格页面。

## 本地人格保存触发合并

CLI 和 Desktop 本地都没有权限保存团队父人格，但在 team mode 下保存本地人格时必须主动触发“团队父人格 + 本地人格”的合并。

触发源：

- CLI 保存或重置当前 profile 的 `SOUL.md`。
- Desktop local/ssh 模式保存或重置 `SOUL.md`。
- `/cloud-backup soul restore <object-key>` 恢复本地人格。

不触发源：

- 非 team mode 的本地人格保存。
- Team Cloud Dashboard 编辑团队父人格；该操作只更新云端版本，成员本地在下一次同步或显式 `/soul merge` 时合并。
- 只读查看 `/soul show team|local|effective`。

合并调用必须使用 Hermes 当前 profile 已配置的大模型供应商和模型，不新增 Team Cloud Go 服务端模型配置，也不把本地人格内容上传给 Team Cloud Go 代为合并。

## 权限

| 角色 | 查看 | 编辑 | 备份 | 恢复 |
| --- | --- | --- | --- | --- |
| `super_admin` | 是 | 是 | 是 | 是 |
| `admin` | 是 | 是 | 是 | 是 |
| `user` | 是 | 否 | 否 | 否 |

普通成员可通过 CLI/Desktop 查看团队父人格和合并结果，但不能修改。

## 同步语义

Hermes Agent 在创建 `AIAgent(team_context=...)` 前执行：

1. 读取本地 `SOUL.md`。
2. 如果当前 profile 为 team mode，调用 Team Cloud Go 获取 active team parent soul。
3. 以 `checksum_sha256` 和 `version` 缓存在 profile 本地，例如 `.cache/team_cloud/team_parent_soul.json`。
4. 如果缓存中的 team parent checksum、local checksum 和 provider/model 仍匹配，则复用缓存的 merged effective soul。
5. 如果缓存缺失或已过期，优先尝试 LLM 合并；失败时生成安全降级组合，并把 `merge_status=failed` 返回给 CLI/Desktop。
6. 将 effective soul 注入 system prompt 的 identity slot。

缓存只用于 Team Cloud Go 临时不可用时展示和短期恢复，不改变权威源。

## 审计

Team Cloud Go 必须记录：

- `team_soul.read`
- `team_soul.update`
- `team_soul.backup.run`
- `team_soul.restore.preview`
- `team_soul.restore.execute`

Hermes Agent 本地日志只记录版本、checksum、状态，不记录完整人格内容，避免日志泄漏团队规则。
