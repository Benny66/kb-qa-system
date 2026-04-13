"""
AI 问答服务 
- 接收 RAG 检索出的知识片段作为上下文
- 构建 Prompt，调用智谱 AI 大模型（zhipuai SDK）
- 默认模型：glm-4-flash（免费，速度快）
- 支持携带最近几轮对话上下文，实现连续追问
"""

import os
from typing import Iterable
from zhipuai import ZhipuAI
from dotenv import load_dotenv

load_dotenv()

# ── 初始化智谱 AI 客户端 ──────────────────────────────────────────────────────
_client = ZhipuAI(
    api_key=os.getenv("ZHIPUAI_API_KEY", ""),
)
_model = os.getenv("ZHIPUAI_MODEL", "glm-4-flash")

# 检索上下文最大字符数（防止超出上下文窗口）
MAX_CONTEXT_CHARS = 6000
# 最多携带的历史消息条数（不含当前问题）
MAX_HISTORY_MESSAGES = 10


def trim_context(context: str) -> str:
    """限制检索上下文长度。"""
    context = (context or "").strip()
    if len(context) > MAX_CONTEXT_CHARS:
        context = context[:MAX_CONTEXT_CHARS] + "\n\n[...检索内容过长，已截断...]"
    return context


def build_system_prompt(retrieved_context: str) -> str:
    """构建系统 Prompt，将检索出的知识片段注入。"""
    retrieved_context = trim_context(retrieved_context)
    return f"""你是一个专业的知识库问答助手。
请严格根据以下“检索出的知识片段”回答用户的问题。

规则：
1. 优先依据给定知识片段回答，不要编造片段中没有的信息。
2. 如果知识片段不足以回答问题，请明确告知用户“知识库中未找到相关信息”或“当前检索内容不足以回答该问题”。
3. 回答要简洁、准确、有条理。
4. 使用中文回答。
5. 如果用户问题与历史对话有关，可以结合历史对话理解代词指代，但答案事实仍应以检索片段为准。

========== 检索出的知识片段 ==========
{retrieved_context or '[未检索到相关片段]'}
=====================================
"""


def build_chat_messages(retrieved_context: str, question: str, history: Iterable[dict] | None = None) -> list[dict]:
    """构建多轮对话消息列表。"""
    messages = [
        {"role": "system", "content": build_system_prompt(retrieved_context)}
    ]

    normalized_history = []
    for item in history or []:
        if not isinstance(item, dict):
            continue

        role = str(item.get("role", "")).strip().lower()
        content = str(item.get("content", "")).strip()

        if role not in {"user", "assistant"}:
            continue
        if not content:
            continue

        normalized_history.append({"role": role, "content": content})

    if len(normalized_history) > MAX_HISTORY_MESSAGES:
        normalized_history = normalized_history[-MAX_HISTORY_MESSAGES:]

    messages.extend(normalized_history)
    messages.append({"role": "user", "content": question})
    return messages


def ask_question(retrieved_context: str, question: str, history: list[dict] | None = None) -> dict:
    """
    向大模型提问，返回回答结果。

    Args:
        retrieved_context: 检索出的知识片段文本
        question: 用户当前问题
        history: 最近几轮历史消息，格式如
                 [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]

    Returns:
        {
            "answer": str,       # AI 回答
            "tokens_used": int,  # 消耗 token 数
            "success": bool,
            "error": str | None
        }
    """
    try:
        messages = build_chat_messages(retrieved_context, question, history)

        response = _client.chat.completions.create(
            model=_model,
            messages=messages,
            temperature=0.3,      # 较低温度，保证回答准确性
            max_tokens=2048,
        )

        answer = response.choices[0].message.content or ""
        tokens_used = response.usage.total_tokens if response.usage else 0

        return {
            "answer": answer,
            "tokens_used": tokens_used,
            "success": True,
            "error": None,
        }

    except Exception as e:
        error_msg = str(e)
        # 友好化常见错误提示
        if "api_key" in error_msg.lower() or "authentication" in error_msg.lower() or "invalid" in error_msg.lower():
            error_msg = "API Key 无效或未配置，请检查 .env 文件中的 ZHIPUAI_API_KEY"
        elif "connection" in error_msg.lower() or "timeout" in error_msg.lower():
            error_msg = "连接智谱 AI 超时，请检查网络连接"
        elif "model" in error_msg.lower() and "not found" in error_msg.lower():
            error_msg = f"模型 {_model} 不存在，请检查 .env 文件中的 ZHIPUAI_MODEL"

        return {
            "answer": "",
            "tokens_used": 0,
            "success": False,
            "error": error_msg,
        }
