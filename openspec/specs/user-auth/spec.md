# user-auth Specification

## Purpose
TBD - created by archiving change kb-qa-system-architecture. Update Purpose after archive.
## Requirements
### Requirement: 用户登录
系统 SHALL 支持预置账号通过用户名和密码进行登录，登录成功后返回 JWT Token。

#### Scenario: 正确凭据登录成功
- **WHEN** 用户提交合法的用户名和密码（如 admin/admin123）
- **THEN** 系统返回 JWT Token 和用户信息，HTTP 状态码 200

#### Scenario: 错误凭据登录失败
- **WHEN** 用户提交不存在的用户名或错误密码
- **THEN** 系统返回 401 错误，提示"用户名或密码错误"

#### Scenario: 请求体为空时拒绝登录
- **WHEN** 用户提交空请求体或缺少用户名/密码字段
- **THEN** 系统返回 400 错误，提示字段不能为空

### Requirement: JWT 鉴权守卫
系统 SHALL 对所有非公开接口（除 /api/auth/login 和 /api/health 外）强制校验 JWT Token。

#### Scenario: 携带有效 Token 访问受保护接口
- **WHEN** 请求头包含合法的 `Authorization: Bearer <token>`
- **THEN** 系统正常处理请求并返回数据

#### Scenario: 未携带 Token 访问受保护接口
- **WHEN** 请求头不包含 Authorization 字段
- **THEN** 系统返回 401 Unauthorized

#### Scenario: 携带无效 Token 访问受保护接口
- **WHEN** 请求头包含格式错误或伪造的 Token
- **THEN** 系统返回 401 Unauthorized

### Requirement: 获取当前用户信息
系统 SHALL 提供接口让已登录用户获取自身账号信息。

#### Scenario: 已登录用户查询自身信息
- **WHEN** 已登录用户请求 GET /api/auth/me
- **THEN** 系统返回该用户的 id、username、created_at 字段

#### Scenario: 用户不存在时返回 404
- **WHEN** JWT 中的 user_id 在数据库中不存在
- **THEN** 系统返回 404 错误，提示"用户不存在"

### Requirement: 前端 Token 持久化与自动注入
前端 SHALL 将 Token 存储于 localStorage，并在每次 HTTP 请求中自动注入 Authorization 头。

#### Scenario: 登录后 Token 持久化
- **WHEN** 用户登录成功
- **THEN** Token 和用户信息写入 localStorage，页面刷新后仍保持登录态

#### Scenario: 请求返回 401 时自动登出
- **WHEN** 任意接口响应 HTTP 401
- **THEN** 前端清除 localStorage 中的 token 和 user，并跳转至 /login 页面

### Requirement: 路由守卫
前端路由 SHALL 对未登录用户拦截受保护页面，并对已登录用户拦截登录页。

#### Scenario: 未登录访问受保护路由
- **WHEN** 未登录用户访问 /kb、/chat、/history 等页面
- **THEN** 路由守卫将其重定向至 /login

#### Scenario: 已登录用户访问登录页
- **WHEN** 已登录用户访问 /login
- **THEN** 路由守卫将其重定向至 /（首页）

### Requirement: 预置账号初始化
系统 SHALL 在首次启动时自动创建预置账号，无需手动注册。

#### Scenario: 首次启动自动创建账号
- **WHEN** 数据库中不存在 admin 或 demo 账号时启动服务
- **THEN** 系统自动创建 admin/admin123 和 demo/demo123 两个账号

#### Scenario: 重复启动不重复创建
- **WHEN** 数据库中已存在预置账号时再次启动服务
- **THEN** 系统跳过创建，不产生重复记录

