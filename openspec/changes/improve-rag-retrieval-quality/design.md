## Context

当前检索链路（`kb-qa-backend/rag_service.py`）：

```
question
  → embed_query(question)                 # 智谱/OpenAI 兼容 embedding
  → _collection.query(cosine, top_k=4)    # ChromaDB 向量检索
  → 拼接 context（[片段N]\ncontent）      # 无阈值、无重排、无去重
  → build_system_prompt(context)          # 注入 LLM
```

技术栈：Flask + SQLite（SQLAlchemy）+ ChromaDB（`hnsw:space: cosine`）+ 智谱/OpenAI 兼容 embedding。向量检索返回的 `distance` 为 cosine distance（`1 - cosine_similarity`，范围 `[0,2]`，**越小越相关**）。

## Goals / Non-Goals

**Goals:**
- 召回片段按 distance 阈值过滤，过滤后为空时返回空上下文，触发「未找到」分支
- 引入关键词召回（SQLite FTS5 BM25）与向量召回融合，补充精确术语召回
- 对召回片段去重，提升 top_k 内多样性

**Non-Goals:**
- 不引入 rerank 模型（交叉编码器），对轻量项目过重
- 不做查询改写 / 查询扩展（需额外 LLM 调用）
- 不做结构化分块（标题/表格感知），属独立 change
- 不改变单文件知识库的产品形态
- 不改变 `retrieve_knowledge_context` 的调用签名与返回结构（仅新增可选字段）

## Decisions

### 决策 1：距离阈值默认关闭，用环境变量开启

**选择**：新增 `RAG_DISTANCE_THRESHOLD` 环境变量（float，可选）。未设置时**不过滤**（保持现状）；设置后，`distance < threshold` 的片段保留，其余丢弃；过滤后为空则返回 `chunks: []` / `context: ""`。

**备选方案**：默认设一个保守阈值（如 1.0）强制开启过滤。不采用——会改变现有行为，且 cosine distance 的合理阈值与 embedding 模型、知识库内容强相关，无法一刀切；默认关闭更安全。

**理由**：距离阈值是「防幻觉」的关键，但阈值本身依赖模型与数据分布，应由部署方按需配置。默认关闭避免破坏性，部署方（尤其是内部工具）可按文档开启。

**过滤语义**：cosine distance 越小越相关，故 `distance < threshold` 保留。`threshold` 取值建议 0.5~0.8（对应 cosine similarity 约 0.5~0.2），需结合 embedding 模型校准。

### 决策 2：关键词召回用 SQLite FTS5 BM25，而非内存倒排

**选择**：用 SQLite FTS5 全文索引存 chunk，`bm25()` 排序做关键词召回。`index_knowledge_base` 时同步写入 FTS5 表；检索时对 query 做 FTS5 查询取 top_k 命中。

**备选方案**：
- 内存倒排索引 + TF-IDF：进程重启即失，且要维护额外内存结构，不如 FTS5 持久且免维护
- 不引入关键词召回，只做查询扩展：改动小但收益有限，无法真正解决精确术语召回

**理由**：SQLite 已是项目在用存储（`kb_qa.db`），FTS5 是 SQLite 内置模块，无需新增依赖；BM25 是标准关键词排序算法，与 ChromaDB 向量召回天然互补。

**FTS5 表设计**：外置 content 表 `rag_chunk_fts(kb_id, user_id, chunk_index, content)`，用 `DELETE/INSERT` 与 `index_knowledge_base` 的删除+重建语义对齐；`chunk_index` 用于召回后回溯到原始 chunk。

### 决策 3：两路融合用 RRF（Reciprocal Rank Fusion）

**选择**：向量召回与关键词召回各取 top_k 候选，用 RRF 公式融合排序：`rrf_score(d) = Σ 1/(k + rank_i(d))`，`k=60`，按 rrf_score 降序取最终 top_k。

**理由**：向量分数（cosine distance）与关键词分数（BM25）量级不同，直接加权不可比；RRF 只依赖排名，天然规避尺度差异，是标准的多路召回融合方案，实现简单。

**融合后距离字段**：仅向量召回的片段携带 `distance`；关键词命中片段 `distance` 为 `None`。最终结果按 rrf_score 排序，`distance` 阈值过滤仍仅作用于有 distance 的片段（见决策 1）。

### 决策 4：去重用「内容重叠判定」，在融合后、top_k 截断前应用

**选择**：对召回片段两两比较，若两片段文本归一化后的最长公共子串长度超过较短片段长度的一定比例（如 60%），判为重复，保留排序更靠前的片段。

**理由**：`split_text` 的 overlap 会导致相邻 chunk 大量重叠，简单重叠判定即可识别，无需引入 embedding 相似度计算。

**位置**：在 RRF 融合后、最终 top_k 截断前，保证去重后能补足 top_k（去重前候选数 > top_k）。

### 决策 5：所有新特性默认关闭，`retrieve_knowledge_context` 签名兼容

**选择**：`RAG_HYBRID_ENABLED` 默认 `false`（纯向量，现状）；`RAG_DISTANCE_THRESHOLD` 默认空（不过滤，现状）。`retrieve_knowledge_context` 返回 dict 新增可选字段（如 `filtered_count`、`keyword_hits`），不删除、不改动既有字段。

**理由**：无破坏性，现有 `app.py` 两处调用（非流式/流式问答）无需改动即可继续工作，新特性按需开启。

## Risks / Trade-offs

- **FTS5 引入双索引一致性风险**：ChromaDB 与 FTS5 需在 `index_knowledge_base` 内同步写入/删除，若一处失败可能不一致。缓解：`index_knowledge_base` 已「先删后建」，FTS5 复用同一事务/顺序，失败时整库重建。
- **距离阈值未经校准**：0.5~0.8 是经验值，实际最优依赖 embedding 模型（embedding-3 等），需部署方按真实数据校准；默认关闭规避了未校准时的破坏性。
- **RRF k=60 为经验默认**：未针对本项目数据调优，作为起点。
- **改动集中在 `rag_service.py`**：检索关键路径，需配套单测覆盖阈值过滤、混合召回、去重三个分支。
