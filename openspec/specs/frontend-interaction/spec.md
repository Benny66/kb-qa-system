# frontend-interaction Specification

## Purpose
TBD - created by archiving change kb-qa-system-architecture. Update Purpose after archive.
## Requirements
### Requirement: Axios 请求封装
前端 SHALL 使用统一的 Axios 实例处理所有 HTTP 请求，自动注入 Token 并统一处理错误。

#### Scenario: 自动注入 Authorization 头
- **WHEN** 发起任意 HTTP 请求
- **THEN** 请求拦截器从 localStorage 读取 token，注入 Authorization: Bearer <token> 头

#### Scenario: 统一错误提示
- **WHEN** 请求失败（非 401）
- **THEN** 响应拦截器提取 error.response.data.msg 或 error.message 作为错误信息，以 Promise.reject 返回

#### Scenario: 超时配置
- **WHEN** 请求超过 60 秒未响应
- **THEN** 请求超时，触发错误处理流程（AI 接口响应较慢，超时设为 60s）

### Requirement: 认证状态管理
前端 SHALL 使用 Pinia store 管理登录态，支持持久化和响应式访问。

#### Scenario: 登录后持久化状态
- **WHEN** 用户登录成功
- **THEN** auth store 将 token 和 user 写入 localStorage，isLoggedIn 计算属性返回 true

#### Scenario: 登出清除状态
- **WHEN** 用户主动登出或 Token 失效
- **THEN** auth store 清空 token 和 user，清除 localStorage，isLoggedIn 返回 false

#### Scenario: 页面刷新后恢复登录态
- **WHEN** 用户刷新页面
- **THEN** auth store 从 localStorage 初始化 token 和 user，保持登录态

### Requirement: 知识库管理页面
前端 SHALL 提供知识库管理页面，支持上传、查看和删除知识库。

#### Scenario: 展示知识库列表
- **WHEN** 用户进入知识库管理页面
- **THEN** 页面展示当前用户的全部知识库，包含文件名、文件大小、字符数、上传时间、索引状态

#### Scenario: 上传知识库文件
- **WHEN** 用户选择文件并点击上传
- **THEN** 前端以 multipart/form-data 格式提交文件，展示上传进度，成功后刷新列表

#### Scenario: 删除知识库
- **WHEN** 用户点击删除并确认
- **THEN** 前端调用 DELETE /api/kb/<id>，成功后从列表中移除该知识库

### Requirement: AI 问答页面
前端 SHALL 提供会话式问答界面，支持选择知识库、多轮追问、新建会话和历史会话恢复。

#### Scenario: 选择知识库后开始问答
- **WHEN** 用户选择知识库并发送第一条消息
- **THEN** 前端调用 POST /api/chat（不传 session_id），后端自动创建会话，前端保存返回的 session_id 用于后续追问

#### Scenario: 多轮追问
- **WHEN** 用户在已有会话中继续发送消息
- **THEN** 前端携带 session_id 调用 POST /api/chat，实现上下文连续

#### Scenario: 新建会话
- **WHEN** 用户点击"新建会话"按钮
- **THEN** 前端清空当前消息列表，重置 session_id，下次发送消息时创建新会话

#### Scenario: 恢复历史会话
- **WHEN** 用户点击左侧会话列表中的历史会话
- **THEN** 前端调用 GET /api/chat/sessions/<session_id> 获取消息列表并渲染，后续追问携带该 session_id

#### Scenario: 展示检索参考片段
- **WHEN** AI 回答返回 references 字段
- **THEN** 前端在回答下方展示参考片段来源信息

### Requirement: 问答历史页面
前端 SHALL 提供历史会话浏览页面，支持按知识库筛选和一键继续聊天。

#### Scenario: 展示历史会话列表
- **WHEN** 用户进入历史页面
- **THEN** 页面按会话维度展示历史，每个会话显示标题、知识库名称、消息数量、最后更新时间

#### Scenario: 按知识库筛选历史
- **WHEN** 用户选择特定知识库进行筛选
- **THEN** 页面只展示该知识库下的会话列表

#### Scenario: 继续聊天
- **WHEN** 用户点击某个历史会话的"继续聊天"按钮
- **THEN** 前端跳转至 AI 问答页面，并恢复该会话的上下文

#### Scenario: 删除历史会话
- **WHEN** 用户点击删除某个会话
- **THEN** 前端调用 DELETE /api/chat/sessions/<session_id>，成功后从列表移除

### Requirement: 全局布局与导航
前端 SHALL 提供统一的布局容器，包含顶部导航栏和侧边栏，所有主页面在其内部渲染。

#### Scenario: 导航栏展示当前用户
- **WHEN** 用户已登录并进入主界面
- **THEN** 布局组件展示当前用户名，并提供登出入口

#### Scenario: 路由切换保持布局
- **WHEN** 用户在知识库管理、AI 问答、历史页面之间切换
- **THEN** 布局容器保持不变，仅 router-view 区域内容切换

### Requirement: 全局消息提示
前端 SHALL 提供全局 Toast 消息提示，用于展示操作成功或失败的反馈。

#### Scenario: 操作成功提示
- **WHEN** 上传知识库、删除知识库等操作成功
- **THEN** 页面顶部或角落展示绿色成功提示，自动消失

#### Scenario: 操作失败提示
- **WHEN** 任意 API 请求失败
- **THEN** 页面展示红色错误提示，包含具体错误信息

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

