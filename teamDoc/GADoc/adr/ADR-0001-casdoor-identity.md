# ADR-0001：使用 Casdoor 作为默认身份认证系统

状态：Accepted
日期：2026-05-22
适用阶段：P1-P5

## 背景

Hermes Team Agent GA 需要支持企业登录、MFA、外部 IdP、组织用户生命周期、禁用传播和 Gateway/API/Web 多入口身份绑定。现有 Hermes 本地 token、平台 allowlist 和 Dashboard session token 无法满足企业 SSO、审计和禁用用户传播要求。

## 决策

使用 Casdoor 作为默认企业身份认证和身份生命周期系统。Team Cloud 只信任 Casdoor OIDC/JWT/JWKS、Casdoor webhook/SCIM/reconcile 结果，以及 Team Cloud Go 登录后签发并存储在 Redis 的 Dashboard session token。Team Cloud Go 第一版 Dashboard 为超级管理员/管理员提供本地管理页登录，密码只保存 bcrypt hash；不把 Casdoor group/role 直接当最终资源授权。

Team Cloud 负责：

- 将 Casdoor subject 映射为 `team_cloud_user` 和 `member`。
- 同步组织、用户、组、角色和禁用状态。
- 生成产品 membership 和 SpiceDB relationship outbox。
- 签发 PAT 和 service account token，并记录审计事件。

## 备选

| 方案 | 结果 |
| --- | --- |
| Keycloak / ZITADEL / Ory | 功能上可行，但本轮方案已明确限定 Casdoor；切换会扩大集成和运维范围 |
| 继续使用本地 Dashboard token | 无法满足 SSO、MFA、企业禁用传播、SCIM 和跨入口身份绑定 |
| Team Cloud 自研登录和密码存储 | 安全成本高，偏离 Agent runtime 和数据治理目标 |

## 后果

- P1 必须提供 Casdoor 本地 compose、OIDC app 配置、JWKS cache、nonce/issuer/audience/exp 校验和禁用用户传播。
- API/Gateway/Web 都必须经过 Team Cloud identity resolver，不能直接信任平台 user_id。
- Casdoor roles/groups 只能作为同步输入，最终授权必须写入 SpiceDB。
- 需要运维 Casdoor 配置备份、JWKS rotation Runbook 和登录失败观测。

## 回滚条件

只有当 Casdoor 在目标私有化环境中无法满足企业 IdP、MFA 或许可证要求，且 P0 架构评审批准替代身份系统时，才允许回滚。回滚方案必须保持 OIDC/JWT/JWKS 抽象不变，不能退回本地 token 作为团队登录。
