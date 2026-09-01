# rag-service Specification

## Purpose

增强 RAG 检索的召回质量：补充距离阈值过滤（防幻觉）、关键词混合召回（补精确术语）、片段去重（提升多样性）。

## MODIFIED Requirements

### Requirement: 向量相似度检索

系统 SHALL 根据用户问题检索最相关的知识片段，使用余弦相似度，返回 Top-K 结果；当配置了距离阈值时，SHALL 过滤掉超过阈值的低相关片段。

#### Scenario: 正常检索返回片段
- **WHEN** 调用 retrieve_knowledge_context(kb_id, user_id, question)
- **THEN** 系统将问题向量化，在 ChromaDB 中按 kb_id + user_id 过滤后检索，返回 Top-K（默认 4）个片段，每个片段包含 content、metadata、distance

#### Scenario: 未配置距离阈值时不过滤
- **WHEN** 环境变量 RAG_DISTANCE_THRESHOLD 未设置
- **THEN** 系统保留所有召回片段，不做距离过滤（保持默认行为）

#### Scenario: 距离阈值开启时过滤低相关片段
- **WHEN** RAG_DISTANCE_THRESHOLD 设置为 0.7
- **THEN** 系统仅保留 distance < 0.7 的片段，其余丢弃

#### Scenario: 全部片段超阈值时返回空结果
- **WHEN** 召回的所有片段 distance 均 ≥ 阈值
- **THEN** 系统返回 chunks: [] 与 context: ""，使 AI 问答走「未找到相关信息」分支而非编造答案

## ADDED Requirements

### Requirement: 关键词混合召回

系统 SHALL 支持关键词 + 向量混合召回：当 RAG_HYBRID_ENABLED 开启时，用 SQLite FTS5 BM25 关键词召回与向量召回做 RRF 融合，补充精确术语召回。

#### Scenario: 混合召回关闭时纯向量
- **WHEN** RAG_HYBRID_ENABLED 未设置或为 false
- **THEN** 系统仅做向量召回，保持现有行为

#### Scenario: 混合召回开启时两路召回并融合
- **WHEN** RAG_HYBRID_ENABLED 为 true
- **THEN** 系统同时执行向量召回与关键词召回，用 RRF 公式（k=60）融合排序后返回 top_k

#### Scenario: 关键词命中片段无距离
- **WHEN** 某片段仅被关键词召回命中、未被向量召回命中
- **THEN** 该片段 distance 为 null，距离阈值过滤仅作用于有 distance 的向量命中

### Requirement: 检索片段去重

系统 SHALL 对召回片段做内容重叠去重，避免因切分 overlap 导致的重复片段占据 top_k。

#### Scenario: 重叠片段去重
- **WHEN** 两个召回片段文本归一化后的最长公共子串长度超过较短片段一定比例（如 60%）
- **THEN** 系统保留排序更靠前的片段，丢弃重复片段

#### Scenario: 去重后补足 top_k
- **WHEN** 去重后片段数少于 top_k
- **THEN** 系统按排序补足候选，保证返回尽可能多的有效片段
