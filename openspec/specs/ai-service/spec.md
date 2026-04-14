# ai-service Specification

## Purpose
TBD - created by archiving change kb-qa-system-architecture. Update Purpose after archive.
## Requirements
### Requirement: 构建系统 Prompt
系统 SHALL 将 RAG 检索出的知识片段注入 System Prompt，约束模型仅基于知识片段回答。

#### Scenario: 正常注入知识片段
- **WHEN** 传入非空的检索上下文文本
- **THEN** 系统将其嵌入 System Prompt 的"检索出的知识片段"区域，并附加回答规则

#### Scenario: 检索上下文超长时截断
- **WHEN** 检索上下文字符数超过 MAX_CONTEXT_CHARS（默认 6000）
- **THEN** 系统截断至 6000 字符并追加"[...检索内容过长，已截断...]"提示

#### Scenario: 检索上下文为空时提示
- **WHEN** 传入空字符串上下文
- **THEN** System Prompt 中显示"[未检索到相关片段]"，模型应告知用户知识库中未找到相关信息

### Requirement: 多轮对话消息构建
系统 SHALL 将历史对话消息与当前问题组合为符合 OpenAI 格式的 messages 列表。

#### Scenario: 携带历史消息构建对话
- **WHEN** 传入包含 user/assistant 角色的历史消息列表
- **THEN** 系统在 System Prompt 之后、当前问题之前插入历史消息，顺序为 system → history → user

#### Scenario: 历史消息超出限制时截断
- **WHEN** 历史消息条数超过 MAX_HISTORY_MESSAGES（默认 10）
- **THEN** 系统保留最近 10 条消息，丢弃更早的历史

#### Scenario: 过滤非法历史消息
- **WHEN** 历史消息中包含非 user/assistant 角色或内容为空的条目
- **THEN** 系统过滤掉这些条目，不将其加入 messages

### Requirement: 调用大模型生成回答
系统 SHALL 调用智谱 GLM 模型（默认 glm-4-flash）生成回答，并返回结构化结果。

#### Scenario: 正常生成回答
- **WHEN** 传入有效的检索上下文、问题和历史消息
- **THEN** 系统调用 ZhipuAI chat.completions.create，返回 answer、tokens_used、success: true

#### Scenario: API 调用失败时返回错误结构
- **WHEN** 调用智谱 AI API 时发生任何异常
- **THEN** 系统返回 success: false，answer 为空字符串，error 字段包含友好化的错误描述

#### Scenario: API Key 无效时友好提示
- **WHEN** 异常信息包含 "api_key"、"authentication" 或 "invalid" 关键词
- **THEN** error 字段返回"API Key 无效或未配置，请检查 .env 文件中的 ZHIPUAI_API_KEY"

#### Scenario: 网络超时时友好提示
- **WHEN** 异常信息包含 "connection" 或 "timeout" 关键词
- **THEN** error 字段返回"连接智谱 AI 超时，请检查网络连接"

#### Scenario: 模型不存在时友好提示
- **WHEN** 异常信息包含 "model" 和 "not found" 关键词
- **THEN** error 字段返回包含当前模型名称的提示，引导用户检查 ZHIPUAI_MODEL 配置

### Requirement: 模型参数配置
系统 SHALL 支持通过环境变量配置模型名称，并使用固定的低温度参数保证回答准确性。

#### Scenario: 使用环境变量指定模型
- **WHEN** .env 中设置了 ZHIPUAI_MODEL
- **THEN** 系统使用该值作为模型名称，默认值为 glm-4-flash

#### Scenario: 低温度参数保证准确性
- **WHEN** 调用模型生成回答
- **THEN** temperature 固定为 0.3，max_tokens 为 2048

### Requirement: 流式生成回答
系统 SHALL 提供流式问答函数，以生成器方式逐块 yield 模型输出的 token，支持调用方实时消费。

#### Scenario: 正常流式输出
- **WHEN** 调用 ask_question_stream(context, question, history)，且 API 调用成功
- **THEN** 函数以生成器方式逐块 yield 包含 type="delta" 和 content 字段的字典，最终 yield 一条 type="done" 且包含 tokens_used 的结束帧

#### Scenario: 流式输出过程中 API 异常
- **WHEN** 在流式迭代过程中发生网络中断或 API 错误
- **THEN** 函数 yield 一条 type="error" 且包含友好化 error 字段的字典，随后终止生成器

#### Scenario: 流式调用使用 stream=True 参数
- **WHEN** 调用智谱 AI SDK 生成回答
- **THEN** 系统传入 stream=True，逐块迭代 response 中的 choices[0].delta.content，跳过 content 为空的块

