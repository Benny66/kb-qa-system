## ADDED Requirements

### Requirement: 流式问答接口
系统 SHALL 提供 SSE 流式问答接口 POST /api/chat/stream，以 text/event-stream 格式逐块推送模型输出，并在流结束后持久化完整回答。

#### Scenario: 流式接口正常推送
- **WHEN** 客户端请求 POST /api/chat/stream，传入合法的 kb_id、question 和可选 session_id
- **THEN** 服务端返回 Content-Type: text/event-stream 响应，逐块推送 data: {"type":"delta","content":"..."} 格式的 SSE 事件，最终推送 data: {"type":"done","session_id":...,"tokens_used":...} 结束帧

#### Scenario: 流结束后写入历史记录
- **WHEN** 模型流式输出完成，所有 delta 块已推送完毕
- **THEN** 系统将完整拼接的回答、question、references_json、tokens_used 一次性写入 ChatHistory，并更新 ChatSession.updated_at

#### Scenario: 流式接口发生错误时推送错误帧
- **WHEN** RAG 检索失败、AI 服务异常或参数校验不通过
- **THEN** 服务端推送 data: {"type":"error","error":"..."} 事件后关闭流，不写入历史记录

#### Scenario: 流式接口复用非流式接口的前置逻辑
- **WHEN** 处理流式问答请求
- **THEN** 系统执行与非流式接口相同的参数校验、知识库权限校验、ensure_knowledge_base_index 和 retrieve_knowledge_context 步骤，仅 AI 调用和响应方式不同

#### Scenario: 流式接口支持自动创建和复用会话
- **WHEN** 流式问答请求未传入 session_id
- **THEN** 系统自动创建新会话，并在结束帧中返回 session_id；若传入已有 session_id 则复用该会话
