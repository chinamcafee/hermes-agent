# P3-14 Break-glass

日期：2026-05-22
状态：Implemented
前置：`P1-18 权限解释最小页`、`P3-04 Tool audit`

## 目标

本步骤实现敏感个人数据读取的 break-glass workflow contract：Owner 和 Security Admin 必须双人参与，请求包含原因、工单、时间窗口和资源范围，审批后生成短期 `approved_break_glass_reader` relationship，访问写 audit，并在未延迟通知时通知被访问成员。当前实现使用 in-memory workflow 和 relationship outbox，后续可替换为 PostgreSQL request 表、通知系统和真实 SpiceDB writer。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/break_glass.py` | `BreakGlassService`，请求、审批、访问、到期撤销和通知记录。 |
| `tests/team_cloud/test_break_glass.py` | 覆盖双人审批、短期授权、访问审计、延迟通知和撤销。 |
| `teamDoc/GALog/2026-05-22-p3-14-break-glass.md` | TDD 红绿记录和回归证据。 |
| `teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json` | Foundation smoke 新增 `break_glass` domain。 |

## Workflow Contract

支持两种发起/审批组合：

```text
Owner -> Security Admin approval
Security Admin -> Owner approval
```

请求必须包含：

```text
reason
ticket_id
starts_at
expires_at
resource_type = memory | backup
resource_id
permission
target_member_id
```

审批后生成 relationship：

```text
{resource_type}:{resource_id}#approved_break_glass_reader@user:{requester_member_id}
```

到期撤销写入同一 relationship 的 delete outbox item。

## Audit And Notification

workflow 写入以下 audit action：

```text
break_glass.requested
break_glass.approved
break_glass.accessed
break_glass.expired
```

`record_access()` 只允许 requester 在有效时间窗口内调用。默认写入 `break_glass_accessed` 通知，收件人为 `target_member_id`；当 `delayed_notification=true` 时不立即写通知，保留 audit 作为追踪证据。

## 非目标

- 不新增 PostgreSQL `break_glass_requests` 表。
- 不实现 Web Console 审批 UI。
- 不实现真实通知发送通道。
- 不直接调用 SpiceDB；只写 relationship outbox。
- 不实现法律保全策略解释和延迟通知审批。

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_break_glass.py
scripts/run_tests.sh tests/team_cloud/test_break_glass.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/break_glass.py tests/team_cloud/test_break_glass.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/break_glass.py tests/team_cloud/test_break_glass.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
