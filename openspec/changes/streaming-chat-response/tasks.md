## 1. 后端：ai_service.py 新增流式调用

- [x] 1.1 在 `ai_service.py` 中新增 `ask_question_stream(retrieved_context, question, history)` 生成器函数
- [x] 1.2 使用 ZhipuAI SDK `stream=True` 参数发起流式请求，逐块迭代 `choices[0].delta.content`
- [x] 1.3 每个非空 content 块 yield `{"type": "delta", "content": chunk}` 字典
- [x] 1.4 流正常结束时 yield `{"type": "done", "tokens_used": N}` 结束帧
- [x] 1.5 捕获迭代过程中的异常，yield `{"type": "error", "error": "友好化错误信息"}` 后终止生成器
- [x] 1.6 复用现有 `build_chat_messages()` 和 `trim_context()` 函数构建消息列表

## 2. 后端：app.py 新增流式问答路由

- [x] 2.1 在 `app.py` 中新增 `POST /api/chat/stream` 路由，添加 `@jwt_required()` 装饰器
- [x] 2.2 提取公共前置逻辑函数（参数校验、kb 权限校验、session 处理、RAG 检索），供流式和非流式接口共用
- [x] 2.3 实现 SSE 生成器函数：调用 `ask_question_stream()`，将每个 yield 帧序列化为 `data: {...}\n\n` 格式字符串
- [x] 2.4 在 SSE 生成器中拼接完整回答，流结束（type="done"）后写入 ChatHistory 和更新 ChatSession
- [x] 2.5 在结束帧中附加 `session_id`、`history_id`、`tokens_used`、`references` 字段
- [x] 2.6 使用 `flask.Response(stream_with_context(generator), mimetype='text/event-stream')` 返回流式响应
- [x] 2.7 设置响应头 `Cache-Control: no-cache`、`X-Accel-Buffering: no` 防止代理缓冲

## 3. 前端：api/chat.js 新增流式请求封装

- [x] 3.1 在 `api/chat.js` 中新增 `sendChatStream(kbId, question, options, callbacks)` 函数
- [x] 3.2 使用原生 `fetch` 向 `POST /api/chat/stream` 发起请求，从 `localStorage` 读取 token 注入 Authorization 头
- [x] 3.3 创建 `AbortController`，将其 `signal` 传入 fetch，函数返回 controller 实例供调用方中止
- [x] 3.4 使用 `response.body.getReader()` 读取 `ReadableStream`，按行解析 `data: {...}` 格式的 SSE 数据
- [x] 3.5 根据解析出的 `type` 字段分别调用 `callbacks.onDelta(content)`、`callbacks.onDone(data)`、`callbacks.onError(error)`

## 4. 前端：ChatView.vue 流式渲染逻辑

- [x] 4.1 在 `ChatView.vue` 中新增 `isStreaming` 响应式状态，控制输入框和发送按钮的禁用状态
- [x] 4.2 发送消息时预先在消息列表中插入一条空的 AI 消息气泡（content 为空字符串，状态为 streaming）
- [x] 4.3 在 `onDelta` 回调中将 content 追加到该气泡的文本，触发 Vue 响应式更新实现逐字渲染
- [x] 4.4 在消息气泡末尾展示闪烁光标动画（CSS `::after` 伪元素），流结束后移除
- [x] 4.5 在 `onDone` 回调中：保存 `session_id`、移除光标动画、恢复输入框可用状态、更新会话列表
- [x] 4.6 在 `onError` 回调中：在气泡中展示错误提示文字，恢复输入框可用状态
- [x] 4.7 展示"停止生成"按钮（流式输出期间可见），点击后调用 `AbortController.abort()` 中止请求
- [x] 4.8 用户中止后将气泡状态标记为 aborted，保留已接收内容，不触发历史写入

## 5. 验证与联调

- [ ] 5.1 启动后端，使用 curl 或 Postman 验证 `/api/chat/stream` 接口能正确推送 SSE 事件流
- [ ] 5.2 验证流结束后 ChatHistory 记录已正确写入数据库（完整回答、references_json、tokens_used）
- [ ] 5.3 在前端验证逐字渲染效果，确认光标动画正常显示和消失
- [ ] 5.4 验证"停止生成"功能：中止后气泡保留已接收内容，数据库无不完整记录写入
- [ ] 5.5 验证多轮追问：流式问答后 session_id 正确保存，下一条消息携带该 session_id
- [ ] 5.6 验证原有非流式接口 `POST /api/chat` 功能不受影响

**注**：详见 IMPLEMENTATION_REPORT.md 中的验证方法说明
