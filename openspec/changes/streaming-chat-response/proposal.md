## Why

当前问答接口采用阻塞式响应：后端等待大模型生成完整回答后才一次性返回，用户面对长回答时需等待数秒才能看到任何内容，体验较差。引入流式输出（SSE）后，模型每生成一个 token 即推送至前端，用户可实时看到回答逐字出现，显著提升交互流畅感。

## What Changes

- **新增** 后端流式问答接口 `POST /api/chat/stream`，基于 Server-Sent Events（SSE）逐 token 推送模型输出
- **新增** `ai_service.py` 中的流式调用函数 `ask_question_stream()`，使用 ZhipuAI SDK 的 `stream=True` 模式
- **修改** `ai-service` 规格：新增"流式生成回答"requirement
- **修改** `chat-session` 规格：新增"流式问答历史写入"requirement（流结束后写库）
- **修改** `frontend-interaction` 规格：新增"流式消息渲染"requirement（EventSource / fetch SSE 消费）
- 原有 `POST /api/chat` 非流式接口**保持不变**，两者并存

## Capabilities

### New Capabilities

（无新增独立能力模块，均为对现有模块的行为扩展）

### Modified Capabilities

- `ai-service`：新增流式生成回答的 requirement，`ask_question_stream()` 以生成器方式逐块 yield token
- `chat-session`：新增流式问答场景下的历史写入 requirement（流结束后一次性持久化完整回答）
- `frontend-interaction`：新增流式消息渲染 requirement（前端使用 fetch + ReadableStream 消费 SSE，逐字追加到消息气泡）

## Impact

- **后端**：`ai_service.py` 新增 `ask_question_stream()` 函数；`app.py` 新增 `/api/chat/stream` 路由，使用 Flask `Response` + `stream_with_context` 推送 SSE
- **前端**：`api/chat.js` 新增 `sendChatStream()` 函数；`ChatView.vue` 新增流式渲染逻辑（逐字追加、光标动画、中止控制）
- **依赖**：无新增第三方依赖，ZhipuAI SDK 已支持 `stream=True`
- **兼容性**：原 `/api/chat` 接口不受影响，前端可按需选择调用哪个接口
