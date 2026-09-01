---
schema: spec-driven
created: 2026-08-19
---

## Why

当前 RAG 检索链路（`kb-qa-backend/rag_service.py`）是**纯向量召回**：`retrieve_knowledge_context` 将问题向量化后在 ChromaDB 中做 cosine 相似度检索，直接返回 Top-K（默认 4）个片段，没有任何距离阈值、关键词补充或去重。这带来三个召回质量问题：

1. **无距离阈值 → 诱导幻觉**：无论 query 与知识库内容多不相关，系统都硬返回 top_k 个片段。用户问「知识库里没有的内容」时，系统仍把这 4 个几乎不相关的片段拼进 System Prompt，模型可能被诱导编造答案。`ai-service` spec 已规定「片段不足以回答时应告知未找到」，但该分支当前**从不触发**——因为检索永远返回 top_k 条。

2. **纯向量召回对精确术语弱**：向量对语义转述有效，但对精确术语、编号、专有名词（如型号、工号、API 名）的召回能力弱，容易漏掉「关键词精确匹配但语义向量距离不近」的片段。

3. **片段重复/高度重叠**：`split_text` 用 overlap=80 字符滑动窗口切分，相邻 chunk 高度重叠，导致 top_k 里可能都是同一段内容的碎片，挤占其他有效片段。

本 change 针对上述三个问题，在 `rag-service` 内补齐召回质量短板，且**所有新特性默认关闭**，不改变现有调用方的默认行为。

## What Changes

- **距离阈值过滤**（P0）：`retrieve_knowledge_context` 按 cosine distance 阈值过滤召回片段，超过阈值的片段丢弃；全部超阈值时返回空 `chunks` / 空 `context`，触发 `ai-service` 既有的「未找到相关信息」分支。新增 `RAG_DISTANCE_THRESHOLD` 环境变量，**默认空（关闭，保持现状）**
- **关键词 + 向量混合召回**（P1）：引入 SQLite FTS5 BM25 关键词召回，与 ChromaDB 向量召回做 RRF 融合，补充精确术语召回。新增 `RAG_HYBRID_ENABLED` 环境变量，**默认 false（关闭）**
- **检索片段去重**（P2）：对召回片段做内容重叠去重，避免同一段内容的碎片重复占据 top_k

## Capabilities

### New Capabilities

（无——本次全部在既有 `rag-service` 能力内增强）

### Modified Capabilities

- `rag-service`: 向量相似度检索补充距离阈值过滤；新增关键词混合召回与片段去重

## Impact

- **核心改动**：`kb-qa-backend/rag_service.py`（阈值过滤、关键词召回、RRF 融合、去重）
- **索引侧改动**：`kb-qa-backend/rag_service.py` 在 `index_knowledge_base` 时同步写入 SQLite FTS5 全文索引
- **配置**：`.env.example` 新增 `RAG_DISTANCE_THRESHOLD`、`RAG_HYBRID_ENABLED` 两个可选配置
- **无 API 契约变更**：`retrieve_knowledge_context` 签名与返回结构保持不变（新增字段向后兼容）
- **无 BREAKING 变更**：所有新特性默认关闭，现有调用方（`app.py` 非流式/流式问答）行为不变
