## ADDED Requirements

### Requirement: 流式消息渲染
前端 SHALL 使用 fetch + ReadableStream 消费 SSE 流式接口，将模型输出逐字追加到消息气泡，提供实时打字机效果。

#### Scenario: 流式内容逐字追加
- **WHEN** 后端推送 type="delta" 的 SSE 事件
- **THEN** 前端将 content 字段追加到当前 AI 消息气泡的文本末尾，用户可实时看到回答逐字出现

#### Scenario: 流结束后更新会话状态
- **WHEN** 后端推送 type="done" 的结束帧
- **THEN** 前端从结束帧中提取 session_id 并保存，移除打字光标动画，将消息标记为完成状态

#### Scenario: 流式输出期间禁用发送按钮
- **WHEN** 流式输出正在进行中
- **THEN** 前端禁用消息输入框和发送按钮，防止用户重复提交

#### Scenario: 流式输出期间展示中止按钮
- **WHEN** 流式输出正在进行中
- **THEN** 前端展示"停止生成"按钮，用户点击后调用 AbortController.abort() 中止 fetch 请求，消息气泡保留已接收内容

#### Scenario: 流式接口发生错误时展示错误提示
- **WHEN** 后端推送 type="error" 事件，或 fetch 请求本身抛出异常
- **THEN** 前端在消息气泡中展示错误提示文字，并恢复输入框可用状态

### Requirement: 流式问答 API 封装
前端 SHALL 在 api/chat.js 中封装 sendChatStream() 函数，使用 fetch 发起流式请求并以回调方式暴露 delta、done、error 事件。

#### Scenario: 封装流式请求函数
- **WHEN** 调用 sendChatStream(kbId, question, options)
- **THEN** 函数使用 fetch 向 POST /api/chat/stream 发起请求，自动注入 Authorization 头，返回可用于中止的 AbortController 实例

#### Scenario: 逐行解析 SSE 数据
- **WHEN** 从 ReadableStream 读取到以 "data: " 开头的行
- **THEN** 函数解析 JSON 内容，根据 type 字段分别调用 onDelta、onDone、onError 回调
