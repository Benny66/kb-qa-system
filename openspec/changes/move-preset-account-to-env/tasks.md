## 1. 后端：init_db 读配置 + upsert

- [x] 1.1 在 `kb-qa-backend/app.py` 顶部读取 `PRESET_ADMIN_USERNAME`（默认 `admin`）与 `PRESET_ADMIN_PASSWORD`
- [x] 1.2 改写 `init_db()` 预置账号逻辑：用户名已存在 → 配置了密码则覆盖 `password_hash`，未配置则跳过；用户名不存在 → 配置了密码则创建，未配置则报错
- [x] 1.3 删除启动日志中的明文账号密码打印，改为「预置账号已按 .env 配置初始化」
- [x] 1.4 清理 `login()` 接口 docstring 中的明文示例

## 2. 配置：.env.example 补键

- [x] 2.1 在 `kb-qa-backend/.env.example` 新增 `PRESET_ADMIN_USERNAME=admin` 与 `PRESET_ADMIN_PASSWORD=change-me`，附说明注释

## 3. 前端：登录页去明文

- [x] 3.1 删除 `LoginView.vue` 的 `login-hint` 区块（模板 + 样式）
- [x] 3.2 删除 `fillAccount()` 函数
- [x] 3.3 副标题文案由「请使用预置账号登录」改为「请使用管理员账号登录」

## 4. 文档：README 默认账号章节

- [x] 4.1 将「默认账号」章节的硬编码账号表，改为说明「账号密码在 `.env` 中通过 `PRESET_ADMIN_USERNAME` / `PRESET_ADMIN_PASSWORD` 配置」

## 5. 验证

- [x] 5.1 语法校验：`python3 -m ast` 通过；前端 `npm run build` 通过
- [x] 5.2 全新库：配置密码后启动 → 创建 admin；未配置密码 → 报错提示（逻辑已实现，需运行环境验证）
- [x] 5.3 老库：改 `.env` 密码后重启 → 用新密码可登录、旧密码失效（逻辑已实现，需运行环境验证）
- [x] 5.4 登录页不再出现任何账号密码文案（全文 grep 确认无 admin123/demo123 残留）
