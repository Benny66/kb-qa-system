## Context

当前 `POST /api/chat` 接口为阻塞式：后端等待智谱 GLM 生成完整回答后，一次性以 JSON 返回。对于长回答（500+ 字），用户需等待 3~8 秒才能看到任何内容。

智谱 AI SDK（zhipuai >= 2.1.5）已原生支持 `stream=True` 参数，可逐块迭代模型输出。Flask 通过 `Response` + `stream_with_context` 支持 SSE 推送。前端通过 `fetch` + `ReadableStream` 可消费 SSE，无需引入 WebSocket 或额外库。

本次变更在现有架构上新增一条流式路径，原有非流式接口保持不变。

## Goals / Non-Goals

**Goals:**
- 新增 `POST /api/chat/stream` SSE 接口，逐 token 推送模型输出
- 新增 `ask_question_stream()` 生成器函数，封装流式 SDK 调用
- 前端新增流式渲染逻辑：逐字追加、打字光标、中止控制
- 流结束后一次性写入 ChatHistory，保证历史记录完整性
- 原有 `POST /api/chat` 接口不受影响

**Non-Goals:**
- 不改造现有非流式接口
- 不引入 WebSocket（SSE 已满足单向推送需求）
- 不实现断点续传（用户中止后不恢复）
- 不对历史页面做流式改造（历史页只展示已完成的回答）

## Decisions

### 决策 1：使用 SSE（Server-Sent Events）而非 WebSocket

**选择**：SSE（`text/event-stream`）

**备选方案**：WebSocket、长轮询

**理由**：
- 问答场景为单向推送（服务端 → 客户端），SSE 语义更匹配
- SSE 基于 HTTP，无需握手协议，Flask 原生支持，前端用 `fetch` 即可消费
- WebSocket 需要额外的连接管理和心跳机制，复杂度更高
- 长轮询延迟高，不适合逐 token 推送

---

### 决策 2：前端使用 fetch + ReadableStream 而非 EventSource

**选择**：`fetch` + `ReadableStream` 手动解析 SSE

**备选方案**：浏览器原生 `EventSource` API

**理由**：
- `EventSource` 不支持 POST 请求，也不支持自定义请求头（无法注入 JWT Token）
- `fetch` 支持完整的请求控制（headers、body、AbortController）
- 手动解析 SSE 行格式（`data: {...}\n\n`）实现简单，无需额外库

---

### 决策 3：流结束后一次性写入历史，而非逐块写入

**选择**：在生成器耗尽（type="done"）后，将完整拼接的回答一次性写入 ChatHistory

**备选方案**：每收到一个 delta 块就更新数据库

**理由**：
- 逐块写入会产生大量数据库写操作，性能差
- 历史记录只需保存完整回答，中间状态无意义
- 若用户中止流，已接收的部分内容不写入历史（保持历史记录的完整性语义）

---

### 决策 4：流式接口与非流式接口共享前置逻辑

**选择**：`/api/chat/stream` 复用参数校验、权限校验、`ensure_knowledge_base_index`、`retrieve_knowledge_context` 等逻辑，仅 AI 调用和响应方式不同

**备选方案**：完全独立实现流式接口

**理由**：
- 避免重复代码，降低维护成本
- 可将公共前置逻辑提取为内部函数，两个接口共同调用

---

### 决策 5：SSE 数据帧格式

```
# delta 帧（每个 token 块）
data: {"type": "delta", "content": "..."}

# 结束帧
data: {"type": "done", "session_id": 1, "history_id": 42, "tokens_used": 256}

# 错误帧
data: {"type": "error", "error": "..."}
```

**理由**：
- 统一 JSON 格式，前端解析简单
- type 字段区分帧类型，扩展性好
- 结束帧携带 session_id，前端可在首次问答后保存会话 ID

---

### 决策 6：AbortController 中止流

**选择**：前端通过 `AbortController` 中止 `fetch` 请求，消息气泡保留已接收内容

**理由**：
- 用户中止后已生成的内容仍有价值，不应丢弃
- `AbortController` 是标准 Web API，无需额外依赖
- 中止后不写入历史，避免保存不完整回答

## Risks / Trade-offs

| 风险 | 缓解措施 |
|---|---|
| Flask 开发服务器（Werkzeug）对 SSE 支持有限，可能缓冲响应 | 开发时设置 `response.headers['X-Accel-Buffering'] = 'no'`，生产使用 Gunicorn + gevent/eventlet worker |
| 用户中止流后，后端生成器可能继续运行消耗 API 配额 | 前端中止 fetch 后，Flask 的 `stream_with_context` 会在下次 yield 时检测到连接断开并停止迭代 |
| 流式接口无法在 Axios 中直接使用（Axios 不支持流式响应） | 流式接口使用原生 `fetch`，非流式接口继续使用 Axios，两者并存 |
| 长时间流式连接占用 Flask 线程 | 开发阶段可接受；生产环境使用异步 worker（gevent）避免线程耗尽 |

## Migration Plan

1. 后端新增 `ask_question_stream()` 函数和 `/api/chat/stream` 路由，不修改现有代码
2. 前端新增 `sendChatStream()` 函数和 `ChatView.vue` 流式渲染逻辑
3. 前端默认切换为流式接口；若浏览器不支持 `ReadableStream`，降级为非流式接口
4. 无数据库 schema 变更，无需迁移

**回滚策略**：前端切回调用 `sendChat()`（非流式），后端流式接口可保留不影响功能。

## Open Questions

- 是否需要在流式接口中也返回 `references`（检索参考片段）？当前设计在结束帧中返回，前端可在流结束后展示。
- 生产环境是否需要配置 Nginx 的 `proxy_buffering off` 以确保 SSE 实时推送？
- 是否需要对流式接口单独设置更长的超时时间（当前 Axios 超时 60s，fetch 无默认超时）？
