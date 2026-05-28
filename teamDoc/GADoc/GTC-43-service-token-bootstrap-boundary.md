# Team Cloud Bootstrap Token 边界说明（已更新）

日期：2026-05-24

## 结论

Team Cloud Go Dashboard 已取消部署级 Service token bootstrap。首次初始化不需要填写 token；`POST /v1/bootstrap/super-admin` 只在系统未初始化时开放，初始化完成后返回 `409 already_initialized`。

## 新边界

- PostgreSQL、Redis、MinIO/S3 连接信息由 Kubernetes Secret / env 注入。
- Dashboard 初始化页只创建单团队空间和唯一超级管理员，不再创建默认工作组。
- 超级管理员或管理员登录 `POST /v1/auth/login` 后，服务端签发 `hcs_...` opaque session token。
- session token 的摘要和 principal 存储在 Redis；后续 Dashboard API 使用 Bearer token 鉴权。

## 安全要求

- 不再生成、填写或轮换 `TEAM_CLOUD_SERVICE_TOKEN`。
- 初始化接口只能在未初始化状态调用；已存在超级管理员后必须拒绝重复初始化。
- 普通成员和 CLI 后续应使用成员级 token、OIDC/JWT 或 PAT，不设计 service token 模式。
