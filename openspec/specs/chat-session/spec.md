# chat-session Specification

## Purpose
TBD - created by archiving change kb-qa-system-architecture. Update Purpose after archive.
## Requirements
### Requirement: 创建会话
系统 SHALL 支持用户在指定知识库下创建独立的聊天会话，每个会话拥有独立的上下文。

#### Scenario: 手动创建会话
- **WHEN** 用户请求 POST /api/chat/sessions，传入 kb_id 和可选 title
- **THEN** 系统创建 ChatSession 记录，title 默认为"新对话"，返回会话信息，HTTP 201

#### Scenario: 知识库不存在时拒绝创建
- **WHEN** 传入的 kb_id 不存在或不属于当前用户
- **THEN** 系统返回 404 错误，提示"知识库不存在或无权限"

#### Scenario: 问答时自动创建会话
- **WHEN** 用户发起问答请求但未传入 session_id
- **THEN** 系统自动创建新会话，title 取问题前 30 个字符，超出部分追加"..."

### Requirement: 获取会话列表
系统 SHALL 支持按知识库筛选会话列表，并支持分页。

#### Scenario: 获取全部会话
- **WHEN** 用户请求 GET /api/chat/sessions（不传 kb_id）
- **THEN** 系统返回该用户的全部会话，按 updated_at 降序排列，支持分页（默认每页 20 条，最大 100 条）

#### Scenario: 按知识库筛选会话
- **WHEN** 用户请求 GET /api/chat/sessions?kb_id=1
- **THEN** 系统只返回属于该知识库的会话列表

#### Scenario: 会话列表包含摘要信息
- **WHEN** 返回会话列表
- **THEN** 每条会话包含 id、kb_id、kb_name、title、message_count、last_question、created_at、updated_at

### Requirement: 获取会话详情
系统 SHALL 支持获取单个会话的完整消息列表。

#### Scenario: 获取会话详情成功
- **WHEN** 用户请求 GET /api/chat/sessions/<session_id>，且会话属于当前用户
- **THEN** 系统返回会话基本信息及按时间升序排列的全部消息列表

#### Scenario: 访问他人会话被拒绝
- **WHEN** 用户请求访问不属于自己的会话
- **THEN** 系统返回 404 错误，提示"会话不存在或无权限"

### Requirement: 删除会话
系统 SHALL 支持删除整个会话及其全部消息记录。

#### Scenario: 删除会话成功
- **WHEN** 用户请求 DELETE /api/chat/sessions/<session_id>，且会话属于当前用户
- **THEN** 系统通过 cascade delete 联动删除该会话下的全部 ChatHistory 记录，返回成功

#### Scenario: 删除不存在的会话
- **WHEN** 用户请求删除不存在或不属于自己的会话
- **THEN** 系统返回 404 错误

### Requirement: 多轮问答与会话历史恢复
系统 SHALL 在每次问答时从数据库读取会话历史，支持刷新页面后继续追问。

#### Scenario: 携带 session_id 继续追问
- **WHEN** 用户发起问答请求并传入已有 session_id
- **THEN** 系统从数据库读取该会话最近 5 轮历史消息，作为多轮上下文传给 AI 服务

#### Scenario: 服务端历史优先于客户端历史
- **WHEN** 请求同时包含 session_id 和 history 字段
- **THEN** 系统优先使用数据库中的会话历史，仅当数据库历史为空时才使用客户端传入的 history

#### Scenario: 会话与知识库不匹配时拒绝
- **WHEN** 传入的 session_id 对应的会话所属知识库与请求中的 kb_id 不一致
- **THEN** 系统返回 400 错误，提示"会话与知识库不匹配"

### Requirement: 问答历史记录
系统 SHALL 将每轮问答结果持久化，包含问题、回答、检索参考片段和 Token 消耗。

#### Scenario: 问答成功后写入历史
- **WHEN** AI 服务成功返回回答
- **THEN** 系统将 question、answer、references_json（检索片段序列化 JSON）、tokens_used 写入 ChatHistory

#### Scenario: AI 服务失败时回滚
- **WHEN** AI 服务返回 success: false
- **THEN** 系统回滚数据库事务，不写入任何历史记录，返回 500 错误

### Requirement: 获取问答历史
系统 SHALL 支持按知识库或会话筛选问答历史，并支持分页。

#### Scenario: 获取全部历史
- **WHEN** 用户请求 GET /api/chat/history（不传筛选参数）
- **THEN** 系统返回该用户的全部问答历史，按 created_at 降序排列

#### Scenario: 按知识库和会话筛选历史
- **WHEN** 用户请求 GET /api/chat/history?kb_id=1&session_id=2
- **THEN** 系统返回同时满足 kb_id 和 session_id 条件的历史记录

### Requirement: 删除单条问答历史
系统 SHALL 支持删除单条问答记录，并在会话无消息时自动清理空会话。

#### Scenario: 删除单条历史成功
- **WHEN** 用户请求 DELETE /api/chat/history/<id>，且记录属于当前用户
- **THEN** 系统删除该条记录，返回成功

#### Scenario: 删除最后一条消息时清理空会话
- **WHEN** 删除某条历史后，其所属会话已无任何消息
- **THEN** 系统同时删除该空会话

### Requirement: 会话标题自动更新
系统 SHALL 在会话标题为"新对话"时，根据首条问题自动更新标题。

#### Scenario: 首次问答后更新会话标题
- **WHEN** 问答成功且当前会话 title 为"新对话"
- **THEN** 系统将 title 更新为问题前 30 个字符（超出追加"..."）

#### Scenario: 已有自定义标题时不覆盖
- **WHEN** 会话已有非"新对话"的标题
- **THEN** 系统不修改标题

