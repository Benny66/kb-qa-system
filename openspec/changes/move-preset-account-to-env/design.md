## Context

预置账号当前硬编码在 `kb-qa-backend/app.py` 的 `init_db()`：

```python
preset_users = {
    "admin": "admin123",
    "demo": "demo123",
}
for username, password in preset_users.items():
    if not User.query.filter_by(username=username).first():
        # 只创建，不更新
        ...
```

前端 `LoginView.vue` 在页面上展示同样的明文账号，并提供点击填充。启动日志（`app.py` 的 `print`）和 README 也明文写死账号密码。

技术栈：Flask + SQLite（SQLAlchemy）+ `python-dotenv`。`.env` 已被 `.gitignore` 忽略且未纳入 git 追踪；后端已用 `load_dotenv()` 读取配置；docker-compose 通过 `env_file` 注入 `.env`。因此「后端配置文件」= `.env`（配 `.env.example` 作为模板），落点是现成的。

## Goals / Non-Goals

**Goals:**
- 登录页不再展示任何账号密码
- 账号密码从 `.env` 读取，代码中无明文密码
- 改 `.env` 密码后，已存在的账号密码随之更新（upsert）
- 清理启动日志、README 中的明文痕迹
- 账号收敛为单一 admin

**Non-Goals:**
- 不实现用户注册功能
- 不删除老库中已存在的 demo 账号（删用户数据不可逆，交给部署方手动处理）
- 不做多账号管理、不改数据库 User 表结构
- 不改 `/api/auth/login` 的接口契约

## Decisions

### 决策 1：账号收敛为单一 admin，用两个环境变量配置

**选择**：`PRESET_ADMIN_USERNAME`（默认 `admin`）+ `PRESET_ADMIN_PASSWORD`（必填）。

**理由**：
- 需求口径偏「账号密码」（单数），单一管理员账号语义最清晰
- 两个独立变量比逗号分隔的 `PRESET_USERS` 更易解析，避免密码含 `:` / `,` 时的转义歧义
- 用户名不是秘密，可给默认值；密码是秘密，必须显式配置

**备选方案**：多账号 `PRESET_USERS=admin:xxx,demo:yyy`。不采用——当前无多账号需求，逗号/冒号分隔在密码含特殊字符时易出问题。

### 决策 2：密码必填，无明文 fallback

**选择**：`PRESET_ADMIN_PASSWORD` 未配置时，`init_db()` 不创建账号并报错（已有账号则跳过 + 警告），不回落任何内置密码。

**理由**：
- 「账号密码入配置」要真正成立，密码的唯一来源必须是 `.env`，代码里不该再留 `admin123` 兜底
- 项目本就必须先配 `.env`（`ZHIPUAI_API_KEY` 不填问答功能不可用），密码入 `.env` 不增加部署门槛
- 兜底明文密码会让「移除明文」的目标形同虚设

### 决策 3：upsert 语义——已存在账号用配置密码覆盖

**选择**：启动时若用户名已存在且配置了密码，则更新 `password_hash`；密码未配置则跳过该账号并打警告。

**理由**：现状是「只创建、不更新」，导致改 `.env` 密码对老库无效。upsert 让「改配置即生效」，符合「账号密码入配置文件」的初衷。

**权衡**：每次启动都会做一次 password_hash 覆盖（几乎无开销）。若将来支持「用户在应用内改密码」，需重新评估——但当前系统不支持应用内改密，upsert 无冲突。

**边界**：老库中已存在的 demo 账号不自动删除；README 说明「如需清理可手动删除」。不静默删用户数据。

### 决策 4：一并清理所有明文痕迹

**选择**：
- `app.py` 启动日志：`print("...admin123...")` 改为「预置账号已按 .env 配置初始化」
- 前端 `LoginView.vue`：删除 `login-hint` 块与 `fillAccount()`，副标题改「请使用管理员账号登录」
- README「默认账号」章节：改为指向 `.env` 的 `PRESET_ADMIN_USERNAME` / `PRESET_ADMIN_PASSWORD`

**理由**：登录页、日志、README 的明文暴露与「代码硬编码」是同源的安全诉求，只改代码不动这些会留下旁路暴露。

## Risks / Trade-offs

- **忘记配 `PRESET_ADMIN_PASSWORD` → 无法登录**：全新库若未配密码，`init_db()` 报错。缓解：`.env.example` 明确注释；报错信息清晰指向配置。这是「移除明文」的必要代价。
- **改 `.env` 密码覆盖老密码**：若部署方手工改过库内密码，会被覆盖。缓解：当前无应用内改密功能，覆盖即预期；README 说明密码以 `.env` 为准。
- **老库 demo 账号残留**：不会自动删除，仍可用 demo 登录。缓解：README 提示手动清理。
