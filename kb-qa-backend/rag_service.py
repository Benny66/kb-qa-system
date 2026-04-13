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
from typing import Any

import chromadb
from dotenv import load_dotenv
from zhipuai import ZhipuAI

from document_loader import extract_document_text

load_dotenv()

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_CHROMA_PERSIST_DIR = os.path.join(
    _BASE_DIR,
    os.getenv("CHROMA_PERSIST_DIR", "chroma_db"),
)
os.makedirs(_CHROMA_PERSIST_DIR, exist_ok=True)

_client = ZhipuAI(api_key=os.getenv("ZHIPUAI_API_KEY", ""))
_embedding_model = os.getenv("ZHIPUAI_EMBEDDING_MODEL", "embedding-3")
_collection_name = os.getenv("CHROMA_COLLECTION_NAME", "kb_qa_chunks")

CHUNK_SIZE = max(int(os.getenv("RAG_CHUNK_SIZE", "500")), 100)
CHUNK_OVERLAP = max(int(os.getenv("RAG_CHUNK_OVERLAP", "80")), 0)
TOP_K = max(int(os.getenv("RAG_TOP_K", "4")), 1)
EMBEDDING_BATCH_SIZE = max(int(os.getenv("RAG_EMBED_BATCH_SIZE", "32")), 1)

_chroma_client = chromadb.PersistentClient(path=_CHROMA_PERSIST_DIR)
_collection = _chroma_client.get_or_create_collection(
    name=_collection_name,
    metadata={"hnsw:space": "cosine"},
)


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


def embed_texts(texts: list[str]) -> list[list[float]]:
    """批量生成文本向量。"""
    if not texts:
        return []

    vectors: list[list[float]] = []
    for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[i:i + EMBEDDING_BATCH_SIZE]
        response = _client.embeddings.create(
            model=_embedding_model,
            input=batch,
        )
        batch_vectors = _extract_embeddings(response)
        if len(batch_vectors) != len(batch):
            raise RuntimeError("Embedding 返回数量与输入数量不一致")
        vectors.extend(batch_vectors)
    return vectors


def embed_query(text: str) -> list[float]:
    """生成查询向量。"""
    response = _client.embeddings.create(
        model=_embedding_model,
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
) -> dict:
    """为知识库创建向量索引。"""
    text = extract_document_text(file_path, original_filename or os.path.basename(file_path))
    chunks = split_text(text)
    if not chunks:
        raise RuntimeError("知识库内容为空，无法建立向量索引")

    delete_knowledge_base_index(kb_id, user_id)

    for start in range(0, len(chunks), EMBEDDING_BATCH_SIZE):
        batch_chunks = chunks[start:start + EMBEDDING_BATCH_SIZE]
        batch_vectors = embed_texts(batch_chunks)
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
) -> dict:
    """如果知识库还未建立索引，则自动建立。"""
    chunk_count = get_kb_index_count(kb_id, user_id)
    if chunk_count > 0:
        return {
            "indexed": True,
            "chunk_count": chunk_count,
            "created": False,
        }

    result = index_knowledge_base(kb_id, user_id, file_path, kb_name, original_filename)
    return {
        "indexed": True,
        "chunk_count": result["chunk_count"],
        "created": True,
    }


def retrieve_knowledge_context(kb_id: int, user_id: int, question: str, top_k: int = TOP_K) -> dict:
    """检索与问题最相关的知识片段。"""
    if not question.strip():
        return {
            "chunks": [],
            "context": "",
        }

    query_vector = embed_query(question)
    result = _collection.query(
        query_embeddings=[query_vector],
        n_results=top_k,
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

    context = "\n\n".join(
        f"[片段{index + 1}]\n{item['content']}"
        for index, item in enumerate(chunks)
    )

    return {
        "chunks": chunks,
        "context": context,
    }
