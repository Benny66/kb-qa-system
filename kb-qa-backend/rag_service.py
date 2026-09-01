"""
RAG 服务： 
- 读取知识库文本
- 文本切分
- 调用智谱 Embedding 生成向量
- 使用 ChromaDB 持久化存储向量
- 基于相似度检索相关片段
"""

import os
import re
from difflib import SequenceMatcher
from typing import Any

import chromadb
from dotenv import load_dotenv
from zhipuai import ZhipuAI
from openai import OpenAI

from document_loader import extract_document_text
from ai_service import get_llm_config

load_dotenv()

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_CHROMA_PERSIST_DIR = os.path.join(
    _BASE_DIR,
    os.getenv("CHROMA_PERSIST_DIR", "chroma_db"),
)
os.makedirs(_CHROMA_PERSIST_DIR, exist_ok=True)

_collection_name = os.getenv("CHROMA_COLLECTION_NAME", "kb_qa_chunks")

CHUNK_SIZE = max(int(os.getenv("RAG_CHUNK_SIZE", "500")), 100)
CHUNK_OVERLAP = max(int(os.getenv("RAG_CHUNK_OVERLAP", "80")), 0)
TOP_K = max(int(os.getenv("RAG_TOP_K", "4")), 1)
EMBEDDING_BATCH_SIZE = max(int(os.getenv("RAG_EMBED_BATCH_SIZE", "32")), 1)

# 距离阈值（cosine distance，越小越相关）。默认 None 表示不过滤。
# 开启后仅保留 distance < 阈值的片段；全部超阈值时返回空 context，
# 触发 ai-service 的「未找到相关信息」分支，避免诱导模型编造答案。
_RAG_DISTANCE_THRESHOLD = os.getenv("RAG_DISTANCE_THRESHOLD")
RAG_DISTANCE_THRESHOLD: float | None = None
if _RAG_DISTANCE_THRESHOLD not in (None, ""):
    try:
        RAG_DISTANCE_THRESHOLD = float(_RAG_DISTANCE_THRESHOLD)
    except ValueError:
        RAG_DISTANCE_THRESHOLD = None

# 去重相似度阈值：两片段内容相似度（difflib.SequenceMatcher.ratio）达到该值视为重复。
# ratio 取值 0~1，越大越相似。默认 0.6，仅去除高度重叠的片段。
DEDUP_OVERLAP_RATIO = 0.6

_chroma_client = chromadb.PersistentClient(path=_CHROMA_PERSIST_DIR)
_collection = _chroma_client.get_or_create_collection(
    name=_collection_name,
    metadata={"hnsw:space": "cosine"},
)


def get_embedding_client(config_id: int | None = None) -> tuple[Any, str]:
    """根据当前配置获取向量模型客户端和模型名称。"""
    config = get_llm_config(config_id)
    if not config:
        raise ValueError("未配置大模型，无法生成向量。请前往“模型配置”页面设置。")

    provider = config.get("provider", "zhipuai").lower()
    api_key = config.get("api_key")
    # 优先使用专门配置的向量模型，若无则使用聊天模型名（某些兼容接口可能共用）
    model = config.get("embedding_model_name") or config.get("model_name")
    base_url = config.get("base_url")

    if provider == "zhipuai":
        return ZhipuAI(api_key=api_key), model
    else:
        # 豆包、通义、OpenAI 兼容等
        return OpenAI(api_key=api_key, base_url=base_url), model


def normalize_text(text: str) -> str:
    """基础文本清洗，减少无意义空白。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\t", " ")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \u3000]{2,}", " ", text)
    return text.strip()


def _find_better_split_position(text: str, start: int, end: int) -> int:
    """尽量在句号、换行等位置切分，减少语义截断。"""
    if end >= len(text):
        return len(text)

    window_start = max(start, end - 80)
    candidate = text[window_start:end]
    separators = ["\n\n", "\n", "。", "！", "？", "；", ". ", "! ", "? ", "; ", "，", ", ", " "]

    best = -1
    for sep in separators:
        idx = candidate.rfind(sep)
        if idx > best:
            best = idx + len(sep)

    if best <= 0:
        return end
    return window_start + best


def split_text(text: str, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP) -> list[str]:
    """按字符窗口切分文本，并尽量在语义边界处断开。"""
    text = normalize_text(text)
    if not text:
        return []

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        end = _find_better_split_position(text, start, end)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        next_start = max(end - chunk_overlap, start + 1)
        if next_start <= start:
            next_start = end
        start = next_start

    return chunks


def _extract_embeddings(response: Any) -> list[list[float]]:
    data = getattr(response, "data", None) or []
    return [item.embedding for item in data if getattr(item, "embedding", None)]


def embed_texts(texts: list[str], config_id: int | None = None) -> list[list[float]]:
    """批量生成文本向量。"""
    if not texts:
        return []

    client, model = get_embedding_client(config_id)
    vectors: list[list[float]] = []
    for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[i:i + EMBEDDING_BATCH_SIZE]
        response = client.embeddings.create(
            model=model,
            input=batch,
        )
        batch_vectors = _extract_embeddings(response)
        if len(batch_vectors) != len(batch):
            raise RuntimeError("Embedding 返回数量与输入数量不一致")
        vectors.extend(batch_vectors)
    return vectors


def embed_query(text: str, config_id: int | None = None) -> list[float]:
    """生成查询向量。"""
    client, model = get_embedding_client(config_id)
    response = client.embeddings.create(
        model=model,
        input=text,
    )
    vectors = _extract_embeddings(response)
    if not vectors:
        raise RuntimeError("查询向量生成失败")
    return vectors[0]


def _build_where(kb_id: int, user_id: int) -> dict:
    """构造 Chroma 过滤条件。多条件时需显式使用 $and。"""
    return {
        "$and": [
            {"kb_id": str(kb_id)},
            {"user_id": str(user_id)},
        ]
    }


def get_kb_index_count(kb_id: int, user_id: int) -> int:
    """获取指定知识库在向量库中的分片数量。"""
    result = _collection.get(where=_build_where(kb_id, user_id))
    return len(result.get("ids", []))


def delete_knowledge_base_index(kb_id: int, user_id: int) -> None:
    """删除指定知识库的全部向量索引。"""
    _collection.delete(where=_build_where(kb_id, user_id))


def index_knowledge_base(
    kb_id: int,
    user_id: int,
    file_path: str,
    kb_name: str = "",
    original_filename: str | None = None,
    config_id: int | None = None,
) -> dict:
    """为知识库创建向量索引。"""
    text = extract_document_text(file_path, original_filename or os.path.basename(file_path))
    chunks = split_text(text)
    if not chunks:
        raise RuntimeError("知识库内容为空，无法建立向量索引")

    delete_knowledge_base_index(kb_id, user_id)

    for start in range(0, len(chunks), EMBEDDING_BATCH_SIZE):
        batch_chunks = chunks[start:start + EMBEDDING_BATCH_SIZE]
        batch_vectors = embed_texts(batch_chunks, config_id=config_id)
        batch_ids = [f"kb_{kb_id}_chunk_{start + idx}" for idx in range(len(batch_chunks))]
        batch_metadatas = [
            {
                "kb_id": str(kb_id),
                "user_id": str(user_id),
                "kb_name": kb_name or "",
                "chunk_index": start + idx,
                "source": os.path.basename(file_path),
            }
            for idx in range(len(batch_chunks))
        ]
        _collection.add(
            ids=batch_ids,
            documents=batch_chunks,
            embeddings=batch_vectors,
            metadatas=batch_metadatas,
        )

    return {
        "chunk_count": len(chunks),
    }


def ensure_knowledge_base_index(
    kb_id: int,
    user_id: int,
    file_path: str,
    kb_name: str = "",
    original_filename: str | None = None,
    config_id: int | None = None,
) -> dict:
    """如果知识库还未建立索引，则自动建立。"""
    chunk_count = get_kb_index_count(kb_id, user_id)
    if chunk_count > 0:
        return {
            "indexed": True,
            "chunk_count": chunk_count,
            "created": False,
        }

    result = index_knowledge_base(kb_id, user_id, file_path, kb_name, original_filename, config_id=config_id)
    return {
        "indexed": True,
        "chunk_count": result["chunk_count"],
        "created": True,
    }


def _normalize_for_dedup(text: str) -> str:
    """归一化文本用于重叠去重：去除所有空白，仅保留可比较的字符序列。"""
    return re.sub(r"\s+", "", text or "")


def _deduplicate_chunks(chunks: list[dict], ratio: float = DEDUP_OVERLAP_RATIO) -> list[dict]:
    """按内容重叠去重，保留排序靠前的片段（chunks 已按相关度降序）。

    相似度用 difflib.SequenceMatcher.ratio，达到 DEDUP_OVERLAP_RATIO 视为重复。
    对切分 overlap 产生的高度重叠片段有效；不引入 embedding 二次计算。
    """
    if not chunks:
        return chunks

    kept: list[dict] = []
    for chunk in chunks:
        norm = _normalize_for_dedup(chunk.get("content"))
        duplicate = False
        for existing in kept:
            existing_norm = _normalize_for_dedup(existing.get("content"))
            if not norm or not existing_norm:
                continue
            if SequenceMatcher(None, norm, existing_norm).ratio() >= ratio:
                duplicate = True
                break
        if not duplicate:
            kept.append(chunk)
    return kept


def retrieve_knowledge_context(kb_id: int, user_id: int, question: str, top_k: int = TOP_K, config_id: int | None = None) -> dict:
    """检索与问题最相关的知识片段。

    流程：向量召回（多取候选）→ 距离阈值过滤 → 内容重叠去重 → 截断 top_k。
    新特性默认关闭（RAG_DISTANCE_THRESHOLD 为空时不过滤），向后兼容。
    """
    if not question.strip():
        return {
            "chunks": [],
            "context": "",
        }

    query_vector = embed_query(question, config_id)
    # 多取候选（top_k * 2），供阈值过滤 + 去重后仍能补足 top_k
    fetch_k = max(top_k * 2, top_k)
    result = _collection.query(
        query_embeddings=[query_vector],
        n_results=fetch_k,
        where=_build_where(kb_id, user_id),
        include=["documents", "metadatas", "distances"],
    )

    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]

    chunks = []
    for idx, doc in enumerate(documents):
        if not doc:
            continue
        metadata = metadatas[idx] if idx < len(metadatas) else {}
        distance = distances[idx] if idx < len(distances) else None
        chunks.append(
            {
                "content": doc,
                "metadata": metadata or {},
                "distance": distance,
            }
        )

    # 距离阈值过滤（默认关闭）。cosine distance 越小越相关，故保留 distance < 阈值。
    filtered_count = 0
    if RAG_DISTANCE_THRESHOLD is not None:
        before = len(chunks)
        chunks = [c for c in chunks if c.get("distance") is not None and c["distance"] < RAG_DISTANCE_THRESHOLD]
        filtered_count = before - len(chunks)

    # 内容重叠去重
    chunks = _deduplicate_chunks(chunks)

    # 截断到 top_k
    chunks = chunks[:top_k]

    context = "\n\n".join(
        f"[片段{index + 1}]\n{item['content']}"
        for index, item in enumerate(chunks)
    )

    return {
        "chunks": chunks,
        "context": context,
        "filtered_count": filtered_count,
    }
