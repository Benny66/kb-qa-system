"""
AI 问答服务 
- 接收 RAG 检索出的知识片段作为上下文
- 支持多种国内大模型提供商（智谱、OpenAI 兼容接口等）
- 支持从数据库加载 LLM 配置或从环境变量 fallback
- 支持携带最近几轮对话上下文，实现连续追问
"""

import os
import json
from abc import ABC, abstractmethod
from typing import Iterable, Generator, Dict, Any, List, Optional, Type
from dataclasses import dataclass
from zhipuai import ZhipuAI
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# 检索上下文最大字符数（防止超出上下文窗口）
MAX_CONTEXT_CHARS = 6000
# 最多携带的历史消息条数（不含当前问题）
MAX_HISTORY_MESSAGES = 10

@dataclass
class LLMResponse:
    content: str
    tokens_used: int
    success: bool = True
    error: Optional[str] = None

class LLMProvider(ABC):
    @abstractmethod
    def chat_completions_create(self, messages: List[Dict[str, str]]) -> LLMResponse:
        pass

    @abstractmethod
    def chat_completions_stream(self, messages: List[Dict[str, str]]) -> Generator[Dict[str, Any], None, None]:
        pass

    def _friendly_error(self, error_msg: str, model_name: str) -> str:
        error_msg = str(error_msg).lower()
        if "api_key" in error_msg or "authentication" in error_msg or "invalid" in error_msg:
            return "API Key 无效或未配置，请检查配置"
        if "connection" in error_msg or "timeout" in error_msg:
            return "连接大模型服务超时，请检查网络连接"
        if "model" in error_msg and "not found" in error_msg:
            return f"模型 {model_name} 不存在，请检查配置"
        return str(error_msg)

class ZhipuAIAdapter(LLMProvider):
    def __init__(self, api_key: str, model_name: str):
        self.client = ZhipuAI(api_key=api_key)
        self.model_name = model_name

    def chat_completions_create(self, messages: List[Dict[str, str]]) -> LLMResponse:
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.3,
                max_tokens=2048,
            )
            content = response.choices[0].message.content or ""
            tokens_used = response.usage.total_tokens if response.usage else 0
            return LLMResponse(content=content, tokens_used=tokens_used)
        except Exception as e:
            return LLMResponse(content="", tokens_used=0, success=False, error=self._friendly_error(str(e), self.model_name))

    def chat_completions_stream(self, messages: List[Dict[str, str]]) -> Generator[Dict[str, Any], None, None]:
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.3,
                max_tokens=2048,
                stream=True,
            )
            tokens_used = 0
            for chunk in response:
                delta_content = ""
                if chunk.choices and chunk.choices[0].delta:
                    delta_content = chunk.choices[0].delta.content or ""
                if delta_content:
                    yield {"type": "delta", "content": delta_content}
                if hasattr(chunk, "usage") and chunk.usage:
                    tokens_used = chunk.usage.total_tokens or tokens_used
            yield {"type": "done", "tokens_used": tokens_used}
        except Exception as e:
            yield {"type": "error", "error": self._friendly_error(str(e), self.model_name)}

class OpenAICompatibleAdapter(LLMProvider):
    def __init__(self, api_key: str, model_name: str, base_url: Optional[str] = None):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model_name = model_name

    def chat_completions_create(self, messages: List[Dict[str, str]]) -> LLMResponse:
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.3,
                max_tokens=2048,
            )
            content = response.choices[0].message.content or ""
            tokens_used = response.usage.total_tokens if response.usage else 0
            return LLMResponse(content=content, tokens_used=tokens_used)
        except Exception as e:
            return LLMResponse(content="", tokens_used=0, success=False, error=self._friendly_error(str(e), self.model_name))

    def chat_completions_stream(self, messages: List[Dict[str, str]]) -> Generator[Dict[str, Any], None, None]:
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.3,
                max_tokens=2048,
                stream=True,
            )
            tokens_used = 0
            for chunk in response:
                delta_content = ""
                if chunk.choices and chunk.choices[0].delta:
                    delta_content = chunk.choices[0].delta.content or ""
                if delta_content:
                    yield {"type": "delta", "content": delta_content}
                if hasattr(chunk, "usage") and chunk.usage:
                    tokens_used = chunk.usage.total_tokens or tokens_used
            yield {"type": "done", "tokens_used": tokens_used}
        except Exception as e:
            yield {"type": "error", "error": self._friendly_error(str(e), self.model_name)}

# Provider 注册表
_providers: Dict[str, Type[LLMProvider]] = {
    "zhipuai": ZhipuAIAdapter,
    "doubao": OpenAICompatibleAdapter,
    "qianwen": OpenAICompatibleAdapter,
    "minimax": OpenAICompatibleAdapter,
    "openai-compatible": OpenAICompatibleAdapter,
}

def get_provider(config: Dict[str, Any]) -> LLMProvider:
    if not config:
        raise ValueError("未配置大模型。请前往“模型配置”页面添加并设置默认模型。")

    provider_type = config.get("provider", "zhipuai").lower()
    adapter_cls = _providers.get(provider_type)
    if not adapter_cls:
        raise ValueError(f"不支持的 LLM Provider: {provider_type}")
    
    if adapter_cls == OpenAICompatibleAdapter:
        return adapter_cls(api_key=config["api_key"], model_name=config["model_name"], base_url=config.get("base_url"))
    else:
        return adapter_cls(api_key=config["api_key"], model_name=config["model_name"])

def get_llm_config(config_id: Optional[int] = None) -> Dict[str, Any]:
    """从数据库获取 LLM 配置，或者从环境变量 fallback。"""
    from models import LLMConfig
    from app import app
    
    with app.app_context():
        config_obj = None
        if config_id:
            config_obj = LLMConfig.query.get(config_id)
        else:
            config_obj = LLMConfig.query.filter_by(is_default=True).first()
        
        if config_obj:
            return {
                "provider": config_obj.provider,
                "api_key": config_obj.api_key,
                "model_name": config_obj.model_name,
                "embedding_model_name": config_obj.embedding_model_name,
                "base_url": config_obj.base_url,
            }
    
    # Fallback to .env if needed (backward compatibility)
    provider = os.getenv("LLM_PROVIDER", "zhipuai")
    api_key = os.getenv("ZHIPUAI_API_KEY")
    
    if not api_key:
        return {} # No config available

    return {
        "provider": provider,
        "api_key": api_key,
        "model_name": os.getenv("ZHIPUAI_MODEL", "glm-4-flash"),
        "embedding_model_name": os.getenv("ZHIPUAI_EMBEDDING_MODEL", "embedding-3"),
        "base_url": os.getenv("ZHIPUAI_BASE_URL"),
    }

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

def ask_question_stream(
    retrieved_context: str,
    question: str,
    history: list[dict] | None = None,
    config_id: Optional[int] = None,
) -> Generator[dict, None, None]:
    """流式问答生成器。"""
    try:
        messages = build_chat_messages(retrieved_context, question, history)
        config = get_llm_config(config_id)
        provider = get_provider(config)
        yield from provider.chat_completions_stream(messages)
    except Exception as e:
        yield {"type": "error", "error": str(e)}

def ask_question(
    retrieved_context: str,
    question: str,
    history: list[dict] | None = None,
    config_id: Optional[int] = None,
) -> dict:
    """向大模型提问，返回回答结果。"""
    try:
        messages = build_chat_messages(retrieved_context, question, history)
        config = get_llm_config(config_id)
        provider = get_provider(config)
        resp = provider.chat_completions_create(messages)
        return {
            "answer": resp.content,
            "tokens_used": resp.tokens_used,
            "success": resp.success,
            "error": resp.error,
        }
    except Exception as e:
        return {
            "answer": "",
            "tokens_used": 0,
            "success": False,
            "error": str(e),
        }
