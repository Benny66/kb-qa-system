"""
AI 问答服务 
- 读取知识库 TXT 文件内容
- 构建 Prompt，调用智谱 AI 大模型（zhipuai SDK）
- 默认模型：glm-4-flash（免费，速度快）
"""

import os
from zhipuai import ZhipuAI
from dotenv import load_dotenv

load_dotenv()

# ── 初始化智谱 AI 客户端 ──────────────────────────────────────────────────────
_client = ZhipuAI(
    api_key=os.getenv("ZHIPUAI_API_KEY", ""),
)
_model = os.getenv("ZHIPUAI_MODEL", "glm-4-flash")

# 知识库内容最大字符数（防止超出上下文窗口）
MAX_CONTEXT_CHARS = 12000


def load_knowledge_base(file_path: str) -> str:
    """读取知识库 TXT 文件，返回文本内容（超长则截断）"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        # 尝试 GBK 编码（兼容部分中文 TXT）
        with open(file_path, "r", encoding="gbk", errors="replace") as f:
            content = f.read()

    if len(content) > MAX_CONTEXT_CHARS:
        content = content[:MAX_CONTEXT_CHARS] + "\n\n[...内容过长，已截断...]"

    return content


def build_system_prompt(kb_content: str) -> str:
    """构建系统 Prompt，将知识库内容注入"""
    return f"""你是一个专业的知识库问答助手。
请严格根据以下知识库内容回答用户的问题。

规则：
1. 只根据知识库内容作答，不要编造知识库中没有的信息。
2. 如果知识库中没有相关内容，请明确告知用户"知识库中未找到相关信息"。
3. 回答要简洁、准确、有条理。
4. 使用中文回答。

========== 知识库内容 ==========
{kb_content}
================================
"""


def ask_question(file_path: str, question: str) -> dict:
    """
    向大模型提问，返回回答结果。

    Args:
        file_path: 知识库 TXT 文件路径
        question:  用户问题

    Returns:
        {
            "answer": str,       # AI 回答
            "tokens_used": int,  # 消耗 token 数
            "success": bool,
            "error": str | None
        }
    """
    try:
        kb_content = load_knowledge_base(file_path)

        response = _client.chat.completions.create(
            model=_model,
            messages=[
                {"role": "system", "content": build_system_prompt(kb_content)},
                {"role": "user", "content": question},
            ],
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
