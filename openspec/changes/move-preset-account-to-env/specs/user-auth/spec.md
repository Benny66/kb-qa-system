# user-auth Specification

## Purpose

预置账号的配置与初始化语义：账号密码从 `.env` 配置读取，单一 admin 账号，upsert 维护，登录页不再展示明文账号密码。

## MODIFIED Requirements

### Requirement: 预置账号初始化

系统 SHALL 在启动时从后端配置文件（`.env`）读取预置账号的用户名与密码，按 upsert 语义维护单一管理员账号，而非硬编码多个账号。

#### Scenario: 首次启动从配置创建账号
- **WHEN** 数据库中不存在管理员账号，且 `.env` 已配置 PRESET_ADMIN_PASSWORD
- **THEN** 系统 SHALL 使用 PRESET_ADMIN_USERNAME（默认 admin）与 PRESET_ADMIN_PASSWORD 创建账号

#### Scenario: 密码未配置时拒绝创建
- **WHEN** 数据库中不存在管理员账号，且 `.env` 未配置 PRESET_ADMIN_PASSWORD
- **THEN** 系统 SHALL 不创建账号，并给出明确错误提示

#### Scenario: 已存在账号时按配置覆盖密码
- **WHEN** 数据库中已存在管理员账号，且 `.env` 配置了 PRESET_ADMIN_PASSWORD
- **THEN** 系统 SHALL 用配置密码更新该账号的 password_hash（改配置即生效）

#### Scenario: 已存在账号且密码未配置时跳过
- **WHEN** 数据库中已存在管理员账号，且 `.env` 未配置 PRESET_ADMIN_PASSWORD
- **THEN** 系统 SHALL 跳过该账号的密码更新，并给出警告提示

#### Scenario: 不再预置 demo 账号
- **WHEN** 系统启动初始化
- **THEN** 系统 SHALL NOT 自动创建 demo 账号

### Requirement: 登录页不展示明文账号密码

前端登录页 SHALL NOT 展示任何预置账号的用户名或密码。

#### Scenario: 登录页无明文账号提示
- **WHEN** 用户访问登录页
- **THEN** 页面 SHALL NOT 出现预置账号的用户名或密码文案，也不提供账号密码自动填充
