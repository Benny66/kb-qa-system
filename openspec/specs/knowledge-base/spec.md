# knowledge-base Specification

## Purpose
TBD - created by archiving change kb-qa-system-architecture. Update Purpose after archive.
## Requirements
### Requirement: 上传知识库文件
系统 SHALL 支持用户上传 .txt、.md、.markdown、.pdf、.docx 格式的文件作为知识库，并自动完成解析和向量索引。

#### Scenario: 上传合法格式文件成功
- **WHEN** 用户上传一个 .pdf 或 .docx 或 .txt 或 .md 文件（≤10MB）
- **THEN** 系统解析文件内容，写入 KnowledgeBase 记录，建立 ChromaDB 向量索引，返回 chunk_count 和知识库元信息，HTTP 201

#### Scenario: 上传不支持格式被拒绝
- **WHEN** 用户上传 .xlsx、.pptx 等不支持格式的文件
- **THEN** 系统返回 400 错误，提示支持的格式列表

#### Scenario: 文件解析失败时回滚
- **WHEN** 上传的文件内容损坏或无法解析
- **THEN** 系统删除已保存的物理文件，不写入数据库记录，返回 400 错误

#### Scenario: 向量化失败时回滚
- **WHEN** 文件解析成功但调用 Embedding API 失败
- **THEN** 系统删除已保存的物理文件和数据库记录，返回 500 错误

#### Scenario: 文件名冲突处理
- **WHEN** 用户上传与已有文件同名的文件
- **THEN** 系统使用 uuid4 前缀生成唯一存储文件名，原始文件名保存在 original_filename 字段

### Requirement: 获取知识库列表
系统 SHALL 返回当前用户的全部知识库，并附带向量索引状态信息。

#### Scenario: 查询知识库列表
- **WHEN** 已登录用户请求 GET /api/kb
- **THEN** 系统返回该用户的知识库列表，每条记录包含 id、name、file_size、char_count、chunk_count、indexed、created_at

#### Scenario: 向量索引查询失败时降级
- **WHEN** 查询 ChromaDB 中某知识库的 chunk_count 时发生异常
- **THEN** 该知识库的 chunk_count 返回 0，indexed 返回 false，不影响其他知识库的返回

### Requirement: 删除知识库
系统 SHALL 支持用户删除知识库，并联动删除物理文件、向量索引、关联会话和问答历史。

#### Scenario: 删除知识库成功
- **WHEN** 用户请求 DELETE /api/kb/<id>，且该知识库属于当前用户
- **THEN** 系统依次删除 ChromaDB 向量索引、物理文件、关联 ChatSession、关联 ChatHistory、KnowledgeBase 记录，返回成功

#### Scenario: 删除不属于自己的知识库
- **WHEN** 用户请求删除不存在或属于其他用户的知识库
- **THEN** 系统返回 404 错误，提示"知识库不存在或无权限"

#### Scenario: 向量索引删除失败时继续
- **WHEN** 删除 ChromaDB 索引时发生异常
- **THEN** 系统忽略该异常，继续执行后续删除步骤

### Requirement: 重建向量索引
系统 SHALL 支持对已有知识库手动触发向量索引重建。

#### Scenario: 重建索引成功
- **WHEN** 用户请求 POST /api/kb/<id>/reindex，且知识库文件存在
- **THEN** 系统重新读取文件、切分、向量化并写入 ChromaDB，返回新的 chunk_count

#### Scenario: 知识库文件丢失时拒绝重建
- **WHEN** 知识库记录存在但物理文件已被删除
- **THEN** 系统返回 500 错误，提示"知识库文件丢失，请重新上传"

### Requirement: 多格式文档解析
系统 SHALL 根据文件扩展名自动选择解析策略，提取纯文本内容。

#### Scenario: 解析 TXT / Markdown 文件
- **WHEN** 上传 .txt、.md、.markdown 文件
- **THEN** 系统优先以 UTF-8 编码读取，失败时降级为 GBK 编码

#### Scenario: 解析 PDF 文件
- **WHEN** 上传 .pdf 文件
- **THEN** 系统逐页提取文本，跳过无法解析的页面，合并为完整文本

#### Scenario: 解析 DOCX 文件
- **WHEN** 上传 .docx 文件
- **THEN** 系统提取所有段落文本和表格内容（表格以 " | " 分隔列），合并为完整文本

#### Scenario: 不支持的扩展名抛出异常
- **WHEN** 传入不支持格式的文件路径
- **THEN** 系统抛出 ValueError，提示不支持的文件格式

