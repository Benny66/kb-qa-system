# rag-service Specification

## Purpose
TBD - created by archiving change kb-qa-system-architecture. Update Purpose after archive.
## Requirements
### Requirement: 文本切分
系统 SHALL 将知识库原始文本按字符窗口切分为语义片段，并尽量在自然语义边界处断开。

#### Scenario: 正常文本切分
- **WHEN** 输入长度超过 CHUNK_SIZE（默认 500）的文本
- **THEN** 系统按 CHUNK_SIZE 切分，相邻片段重叠 CHUNK_OVERLAP（默认 80）个字符，返回片段列表

#### Scenario: 在语义边界处优先断开
- **WHEN** 切分位置附近存在段落换行、句号、问号等分隔符
- **THEN** 系统在最近的分隔符处断开，而非硬截断

#### Scenario: 空文本返回空列表
- **WHEN** 输入文本为空字符串或仅含空白字符
- **THEN** 系统返回空列表 []

#### Scenario: 文本清洗
- **WHEN** 文本包含多余空行（3行以上）、制表符、全角空格
- **THEN** 系统在切分前统一清洗：压缩多余空行为双换行，制表符替换为空格

### Requirement: 文本向量化
系统 SHALL 调用智谱 Embedding API 将文本片段批量转换为向量，支持分批处理。

#### Scenario: 批量向量化成功
- **WHEN** 输入 N 个文本片段
- **THEN** 系统按 EMBEDDING_BATCH_SIZE（默认 32）分批调用 API，返回与输入等长的向量列表

#### Scenario: 向量数量不一致时抛出异常
- **WHEN** API 返回的向量数量与输入文本数量不一致
- **THEN** 系统抛出 RuntimeError，提示"Embedding 返回数量与输入数量不一致"

#### Scenario: 查询向量化
- **WHEN** 输入单条查询文本
- **THEN** 系统调用 API 返回单个向量，若结果为空则抛出 RuntimeError

### Requirement: 向量索引写入
系统 SHALL 将文本片段及其向量写入 ChromaDB，并附加 kb_id、user_id 元数据用于隔离。

#### Scenario: 建立知识库索引
- **WHEN** 调用 index_knowledge_base(kb_id, user_id, file_path, ...)
- **THEN** 系统先删除该知识库的旧索引，再分批写入新的文本片段、向量和元数据

#### Scenario: 知识库内容为空时拒绝索引
- **WHEN** 文件解析后文本为空，切分结果为空列表
- **THEN** 系统抛出 RuntimeError，提示"知识库内容为空，无法建立向量索引"

#### Scenario: 懒加载索引
- **WHEN** 调用 ensure_knowledge_base_index 且 ChromaDB 中已有该知识库的片段
- **THEN** 系统跳过重建，直接返回 indexed: true, created: false

#### Scenario: 懒加载触发重建
- **WHEN** 调用 ensure_knowledge_base_index 且 ChromaDB 中无该知识库的片段
- **THEN** 系统自动调用 index_knowledge_base 完成索引建立，返回 created: true

### Requirement: 向量相似度检索
系统 SHALL 根据用户问题检索最相关的知识片段，使用余弦相似度，返回 Top-K 结果。

#### Scenario: 正常检索返回片段
- **WHEN** 调用 retrieve_knowledge_context(kb_id, user_id, question)
- **THEN** 系统将问题向量化，在 ChromaDB 中按 kb_id + user_id 过滤后检索，返回 Top-K（默认 4）个片段，每个片段包含 content、metadata、distance

#### Scenario: 问题为空时返回空结果
- **WHEN** 传入空字符串问题
- **THEN** 系统不调用 API，直接返回 chunks: [], context: ""

#### Scenario: 多用户数据隔离
- **WHEN** 用户 A 和用户 B 各自上传了知识库
- **THEN** 用户 A 的检索结果 SHALL 只包含用户 A 的知识片段，不返回用户 B 的数据

### Requirement: 向量索引删除
系统 SHALL 支持按 kb_id + user_id 删除 ChromaDB 中的全部相关片段。

#### Scenario: 删除知识库向量索引
- **WHEN** 调用 delete_knowledge_base_index(kb_id, user_id)
- **THEN** 系统从 ChromaDB 中删除所有 kb_id 和 user_id 均匹配的文档片段

### Requirement: ChromaDB 多条件过滤
系统 SHALL 在所有 ChromaDB 查询和删除操作中使用 $and 操作符同时过滤 kb_id 和 user_id。

#### Scenario: 构造多条件过滤器
- **WHEN** 需要过滤特定用户的特定知识库
- **THEN** 系统构造 {"$and": [{"kb_id": str(kb_id)}, {"user_id": str(user_id)}]} 作为 where 条件

