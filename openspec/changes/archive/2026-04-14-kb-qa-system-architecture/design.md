## Context

本项目是一个轻量级知识库问答系统，采用前后端分离架构。后端基于 Flask + SQLAlchemy + ChromaDB，前端基于 Vue 3 + Vite + Pinia。核心能力是 RAG（检索增强生成）：将用户上传的文档切分为语义片段，向量化后存入 ChromaDB，问答时先检索相关片段再交给智谱 GLM 生成回答。

当前系统已完成核心功能开发，本文档对现有架构的关键技术决策进行梳理和记录，作为后续迭代的设计基线。

## Goals / Non-Goals

**Goals:**
- 记录系统整体分层架构和模块边界
- 说明 RAG 核心流程的技术选型与实现决策
- 记录数据模型设计和多用户隔离策略
- 记录前端状态管理和路由守卫的设计决策
- 识别现有架构的风险和可改进点

**Non-Goals:**
- 不涉及任何代码改动
- 不讨论生产部署方案（Nginx/Gunicorn 等）
- 不涉及用户注册、权限管理等未实现功能

## Decisions

### 决策 1：采用 RAG 而非全文注入

**选择**：将知识库文本切分为片段，向量化后存入 ChromaDB，问答时检索 Top-K 片段注入 Prompt。

**备选方案**：将整篇文档直接注入 System Prompt。

**理由**：
- 全文注入受模型上下文窗口限制，超长文档无法处理
- RAG 只注入相关片段，减少无关内容干扰，降低幻觉风险
- ChromaDB 支持本地持久化，无需额外服务，适合轻量项目

---

### 决策 2：ChromaDB 单 Collection + 元数据过滤实现多用户隔离

**选择**：所有用户的知识库片段存入同一个 ChromaDB Collection，通过 `kb_id + user_id` 的 `$and` 过滤条件实现隔离。

**备选方案**：每个用户或每个知识库创建独立 Collection。

**理由**：
- 单 Collection 管理简单，无需动态创建/删除 Collection
- ChromaDB 的 where 过滤支持 `$and` 多条件，隔离效果等价
- 轻量项目用户量小，单 Collection 性能足够

**风险**：用户量或知识库数量极大时，单 Collection 检索性能会下降。

---

### 决策 3：SQLite 作为关系型数据库

**选择**：使用 SQLite 存储用户、知识库、会话、历史等结构化数据。

**备选方案**：MySQL / PostgreSQL。

**理由**：
- 零配置，适合开发和轻量项目
- Flask-SQLAlchemy 支持无缝切换，后续可迁移至 MySQL/PostgreSQL

**风险**：不支持高并发写入，生产环境需替换。

---

### 决策 4：会话历史从服务端读取，客户端传入作为兜底

**选择**：问答时优先从数据库读取最近 5 轮会话历史，客户端传入的 `history` 字段仅在数据库历史为空时使用。

**备选方案**：完全依赖客户端传入历史。

**理由**：
- 服务端历史保证刷新页面后仍可继续追问
- 避免客户端历史被篡改或丢失导致上下文断裂

---

### 决策 5：JWT Token 不设过期时间

**选择**：`JWT_ACCESS_TOKEN_EXPIRES = False`，Token 永不过期。

**备选方案**：设置固定过期时间 + Refresh Token 机制。

**理由**：
- 简化开发和演示流程，无需处理 Token 刷新
- 当前为预置账号系统，无注册功能，安全风险可控

**风险**：Token 泄露后无法失效，生产环境必须改造。

---

### 决策 6：文本切分策略——字符窗口 + 语义边界优化

**选择**：按 CHUNK_SIZE（默认 500 字符）切分，CHUNK_OVERLAP（默认 80 字符）重叠，并在切分点附近寻找最近的语义分隔符（段落、句号等）。

**备选方案**：固定字符硬截断；按段落切分。

**理由**：
- 固定硬截断会破坏语义，影响检索质量
- 语义边界优化在不引入复杂 NLP 依赖的前提下改善切分质量
- 重叠设计减少跨片段语义丢失

---

### 决策 7：前端路由守卫 + localStorage 持久化登录态

**选择**：Vue Router 全局 beforeEach 守卫检查 auth store 的 isLoggedIn，Token 存储于 localStorage。

**备选方案**：Cookie + Session 方案。

**理由**：
- JWT + localStorage 与前后端分离架构天然契合
- Pinia store 从 localStorage 初始化，刷新后自动恢复登录态
- 401 响应拦截器统一处理 Token 失效，无需各页面单独处理

---

### 决策 8：懒加载向量索引（ensure_knowledge_base_index）

**选择**：每次问答前调用 `ensure_knowledge_base_index`，若 ChromaDB 中无该知识库的片段则自动重建。

**备选方案**：仅在上传时建立索引，不做运行时检查。

**理由**：
- ChromaDB 数据目录被误删或迁移后，系统可自动恢复，不会直接报错
- 增加了一次 ChromaDB count 查询的开销，但对轻量项目可接受

## Risks / Trade-offs

| 风险 | 缓解措施 |
|---|---|
| SQLite 不支持高并发 | 生产环境替换为 MySQL/PostgreSQL，Flask-SQLAlchemy 支持无缝切换 |
| JWT 不过期导致安全风险 | 生产环境设置 `JWT_ACCESS_TOKEN_EXPIRES`，增加 Refresh Token 机制 |
| ChromaDB 单 Collection 大数据量性能下降 | 可按用户分 Collection，或迁移至 FAISS/Milvus |
| Embedding API 调用失败导致上传失败 | 当前已做事务回滚，后续可增加重试机制 |
| 知识库文件存储在本地 uploads/ 目录 | 生产环境建议迁移至对象存储（OSS/S3） |
| 检索 Top-K 固定为 4，可能召回不足 | 可根据问题类型动态调整 Top-K，或引入 Rerank |

## Open Questions

- 是否需要支持用户注册和多租户权限管理？
- 是否需要引入 Rerank 模型提升检索精度？
- ChromaDB 是否需要迁移至独立向量数据库服务（如 Milvus）以支持更大规模？
- 会话标题是否需要支持 AI 自动生成（而非截取首条问题）？
- 是否需要支持流式输出（SSE/WebSocket）以改善长回答的用户体验？
