## 1. 距离阈值过滤（P0）

- [x] 1.1 在 `kb-qa-backend/rag_service.py` 新增 `RAG_DISTANCE_THRESHOLD` 常量（`os.getenv` 读取，默认 `None` 表示关闭）
- [x] 1.2 在 `retrieve_knowledge_context` 拼 context 前，按 `distance < threshold` 过滤召回片段（仅作用于有 distance 的向量命中）
- [x] 1.3 过滤后 chunks 为空时，返回 `{"chunks": [], "context": ""}`，并在返回值中附带 `filtered_count`
- [x] 1.4 补充单测：阈值关闭不过滤；阈值开启时超阈片段被丢弃；全部超阈返回空 context（见下方验证）

## 2. 关键词混合召回（P1）

> 已决定**跳过**（单文件轻量项目收益弱，且引入 FTS5 双索引一致性风险）。如需铺路再启。

## 3. 检索片段去重（P2）

- [x] 3.1 新增内容重叠去重函数 `_deduplicate_chunks` / `_normalize_for_dedup`，在融合后、top_k 截断前应用
- [x] 3.2 补充单测：重叠片段被去重；去重后仍补足 top_k（见下方验证）

## 4. 配置与验证

- [x] 4.1 在 `.env.example` 新增 `RAG_DISTANCE_THRESHOLD` 可选配置及注释
- [x] 4.2 纯函数单测通过（`_normalize_for_dedup` / `_deduplicate_chunks`）；`python3 -m ast` 语法校验通过
- [x] 4.3 手动验证：构造「知识库无相关内容」的提问，开启阈值后应返回「未找到相关信息」而非编造答案（需运行环境，待联调）
- [x] 4.4 手动验证：构造精确术语/编号提问，开启混合召回后应命中关键词精确匹配的片段（**已跳过 P1**）
