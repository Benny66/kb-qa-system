# 📚 知识库问答系统

基于 **Vue3 + Flask + 智谱 AI** 的简化版知识库问答系统。上传 TXT 文件作为知识库，通过大模型实现精准问答，并保留完整的问答历史记录。

---

## ✨ 功能特性

- 🔐 **用户登录** — 预置账号，JWT 鉴权，无需注册
- 📂 **知识库管理** — 上传 / 删除 TXT 知识库文件，展示字符数、文件大小
- 💬 **AI 问答** — 选择知识库后与大模型对话，回答严格基于知识库内容
- 📋 **问答历史** — 分页查看、按知识库筛选、支持删除单条记录

---

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 · Vite · Pinia · Vue Router · Axios |
| 后端 | Python 3.11 · Flask · Flask-JWT-Extended · Flask-SQLAlchemy |
| 数据库 | SQLite |
| AI | 智谱 AI（GLM-4-Flash / GLM-4-Air / GLM-4） |

---

## 📁 项目结构

```
.
├── README.md
├── kb-qa-backend/               # Flask 后端
│   ├── app.py                   # 主应用 & 所有接口
│   ├── models.py                # 数据库模型（User / KnowledgeBase / ChatHistory）
│   ├── ai_service.py            # 智谱 AI 问答服务
│   ├── requirements.txt         # Python 依赖
│   ├── .env.example             # 环境变量模板
│   └── uploads/                 # TXT 文件存储目录（自动创建）
│
└── kb-qa-frontend/              # Vue3 前端
    ├── index.html
    ├── vite.config.js
    ├── package.json
    └── src/
        ├── main.js
        ├── App.vue
        ├── style.css            # 全局样式
        ├── api/                 # Axios 接口封装
        │   ├── request.js       # 实例配置（JWT 注入 / 错误处理）
        │   ├── auth.js
        │   ├── kb.js
        │   └── chat.js
        ├── stores/              # Pinia 状态管理
        │   ├── auth.js          # 用户登录态
        │   └── toast.js         # 全局提示
        ├── router/
        │   └── index.js         # 路由 & 登录守卫
        └── views/
            ├── LoginView.vue    # 登录页
            ├── LayoutView.vue   # 侧边栏布局
            ├── KbView.vue       # 知识库管理
            ├── ChatView.vue     # AI 问答
            └── HistoryView.vue  # 问答历史
```

---

## 🚀 快速开始

### 前置条件

- Python >= 3.11
- Node.js >= 18
- 智谱 AI API Key（[免费申请](https://open.bigmodel.cn/usercenter/apikeys)）

---

### 1. 后端启动

```bash
# 进入后端目录
cd kb-qa-backend

# 创建并激活虚拟环境
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 ZHIPUAI_API_KEY
```

编辑 `.env`：

```env
JWT_SECRET_KEY=your-secret-key
ZHIPUAI_API_KEY=your-api-key-here   # ← 必填
ZHIPUAI_MODEL=glm-4-flash           # 免费模型，推荐
UPLOAD_FOLDER=uploads
```

```bash
# 启动后端（自动初始化数据库）
python app.py
# ✅ 后端运行在 http://localhost:5001
```

---

### 2. 前端启动

```bash
# 进入前端目录
cd kb-qa-frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
# ✅ 前端运行在 http://localhost:5173
```

打开浏览器访问 [http://localhost:5173](http://localhost:5173)

---

### 3. 登录

系统预置了两个账号，无需注册：

| 用户名 | 密码 |
|--------|------|
| admin | admin123 |
| demo | demo123 |

---

## 📡 接口文档

所有接口以 `/api` 为前缀，需要认证的接口请在请求头携带：

```
Authorization: Bearer <token>
```

### 认证

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|:----:|
| POST | `/api/auth/login` | 用户登录，返回 JWT Token | ❌ |
| GET | `/api/auth/me` | 获取当前用户信息 | ✅ |

**登录示例：**

```bash
curl -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

### 知识库

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|:----:|
| GET | `/api/kb` | 获取知识库列表 | ✅ |
| POST | `/api/kb/upload` | 上传 TXT 文件（form-data，字段名 `file`） | ✅ |
| DELETE | `/api/kb/:id` | 删除知识库（同时删除关联历史） | ✅ |

### 问答

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|:----:|
| POST | `/api/chat` | AI 问答，Body: `{ kb_id, question }` | ✅ |
| GET | `/api/chat/history` | 获取历史，Query: `?kb_id=&page=&per_page=` | ✅ |
| DELETE | `/api/chat/history/:id` | 删除单条历史 | ✅ |

### 其他

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |

---

## 🤖 AI 模型说明

本项目使用 [智谱 AI](https://open.bigmodel.cn/) 的大模型接口，支持以下模型（在 `.env` 中配置 `ZHIPUAI_MODEL`）：

| 模型 | 特点 | 费用 |
|------|------|------|
| `glm-4-flash` | 速度最快，适合开发测试 | **免费** |
| `glm-4-air` | 性价比高，效果均衡 | 按量计费 |
| `glm-4` | 效果最强 | 按量计费 |

> 知识库内容超过 12,000 字符时会自动截断，以适配模型上下文窗口。

---

## ⚙️ 生产部署建议

```bash
# 后端使用 gunicorn 部署
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5001 app:app

# 前端构建静态文件
cd kb-qa-frontend
npm run build
# 将 dist/ 目录部署到 Nginx 或 CDN
```

Nginx 反向代理参考配置：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /path/to/kb-qa-frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 📝 注意事项

- `.env` 文件包含 API Key 等敏感信息，**已加入 `.gitignore`，请勿提交**
- `uploads/` 目录存储用户上传的文件，**已加入 `.gitignore`**，部署时需手动创建
- SQLite 数据库文件 `kb_qa.db` **已加入 `.gitignore`**，生产环境建议换用 PostgreSQL / MySQL
- 默认 Token 永不过期，生产环境建议在 `app.py` 中设置合理的过期时间

---

## 📄 License

MIT
