---
schema: spec-driven
created: 2026-08-20
---

## Why

当前登录页（`kb-qa-frontend/src/views/LoginView.vue`）在页面上直接展示预置账号 `admin / admin123` 和 `demo / demo123`，并提供点击自动填充。账号密码作为明文硬编码在后端 `app.py` 的 `init_db()` 中（`preset_users` 字典），启动日志和 README 也明文打印账号密码。

这带来两个问题：

1. **明文暴露**：任何人打开登录页即可看到管理员账号密码，失去登录认证的意义；密码散落在前端、后端代码、启动日志、README 四处，难以维护与安全审计。
2. **配置不可变**：密码写死在代码里，部署方无法在不改代码的情况下更换密码。

本 change 将账号密码从代码/前端移除，统一收敛到后端配置文件 `.env`（该文件已被 `.gitignore` 忽略、不纳入版本控制），并清理所有明文痕迹。

## What Changes

- **登录页去明文**：删除 `LoginView.vue` 的 `login-hint` 区块与 `fillAccount()` 填充逻辑，副标题改为中性文案「请使用管理员账号登录」
- **账号密码入配置**：`init_db()` 从 `.env` 读取 `PRESET_ADMIN_USERNAME`（默认 `admin`）与 `PRESET_ADMIN_PASSWORD`（必填、无明文 fallback），按 upsert 语义维护账号
- **upsert 语义**：已存在账号时用配置密码覆盖 `password_hash`（改配置即生效）；密码未配置时拒绝创建/跳过并给出明确提示
- **清理明文痕迹**：删除 `app.py` 启动日志中的明文账号密码打印；README 默认账号章节改为指向 `.env` 配置
- **账号收敛为单一 admin**：不再预置 `demo` 账号（已存在的 demo 账号不做自动删除，由部署方决定）

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `user-auth`: 预置账号从「硬编码 admin/demo 两个账号」改为「从 `.env` 读取单一 admin 账号，upsert 维护」

## Impact

- **后端**：`kb-qa-backend/app.py`（`init_db` 读配置 + upsert + 删明文打印）
- **前端**：`kb-qa-frontend/src/views/LoginView.vue`（删登录提示块与填充逻辑）
- **配置**：`kb-qa-backend/.env.example` 新增 `PRESET_ADMIN_USERNAME` / `PRESET_ADMIN_PASSWORD`
- **文档**：`README.md` 默认账号章节
- **无 BREAKING API 变更**：`/api/auth/login` 契约不变
- **行为变更**：全新库仅预置单一 admin 账号；老库已有 demo 账号保留但不再受代码管理
