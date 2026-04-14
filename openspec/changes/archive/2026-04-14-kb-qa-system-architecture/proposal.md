## Why

本项目是一个基于 Vue 3 + Flask + ChromaDB + 智谱 AI 的知识库问答系统，当前已完成核心功能开发，但缺乏系统性的规格文档。为了支持后续功能迭代、团队协作和代码维护，需要对现有系统的架构、接口、数据结构和模块依赖进行完整的规格化描述。

## What Changes

- **新增规格文档**：为系统所有核心模块创建 OpenSpec 规格文件，覆盖职责、接口、数据结构和依赖关系
- **模块拆分**：按功能边界拆分为独立规格：用户认证、知识库管理、RAG 检索、AI 问答、会话管理、前端交互
- **接口契约化**：将现有 REST API 接口以规格形式固化，作为前后端协作的契约
- **数据模型文档化**：将 SQLite 数据模型和 ChromaDB 向量存储结构纳入规格

## Capabilities

### New Capabilities

- `user-auth`: 用户认证能力——JWT 登录、鉴权守卫、Token 管理
- `knowledge-base`: 知识库管理能力——文件上传、解析、删除、向量索引管理
- `rag-service`: RAG 检索增强生成能力——文本切分、向量化、ChromaDB 存储与检索
- `ai-service`: AI 问答能力——Prompt 构建、多轮上下文、智谱 GLM 调用
- `chat-session`: 会话管理能力——会话创建、历史恢复、多会话隔离
- `frontend-interaction`: 前端交互能力——路由守卫、状态管理、API 封装、页面视图

### Modified Capabilities

（当前为首次规格化，无已有规格需变更）

## Impact

- `openspec/specs/` 目录下新增 6 个模块规格文件
- 不涉及任何现有代码改动
- 为后续功能迭代（如用户注册、Rerank、多路召回）提供规格基础
