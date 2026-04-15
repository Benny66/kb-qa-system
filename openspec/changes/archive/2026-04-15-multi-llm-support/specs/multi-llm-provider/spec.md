# multi-llm-provider Specification

## Purpose
抽象 LLM provider 接口，并通过数据库管理多套大模型配置，支持在聊天过程中动态切换不同的模型配置。

## ADDED Requirements

### Requirement: LLMConfig 数据库存储
系统 SHALL 提供 `LLMConfig` 数据模型，用于持久化存储大模型配置。

#### Scenario: 存储新配置
- **WHEN** 提供名称、Provider、API Key、模型名称等信息
- **THEN** 系统将其保存到数据库，并分配唯一 ID

### Requirement: LLM 配置管理 API
系统 SHALL 提供 CRUD 接口来管理大模型配置。

#### Scenario: 获取配置列表
- **WHEN** 调用 `GET /api/llm-configs`
- **THEN** 返回所有已保存的配置列表，但应对 API Key 进行脱敏处理（如显示为 "sk-••••"）

#### Scenario: 设置默认配置
- **WHEN** 调用 `POST /api/llm-configs/<id>/set-default`
- **THEN** 指定配置被设为默认，系统中原有的默认配置标志被清除

### Requirement: 聊天时动态选择模型配置
系统 SHALL 在发起对话请求时，允许通过 `config_id` 参数指定使用哪套大模型配置。

#### Scenario: 指定配置 ID 提问
- **WHEN** `POST /api/chat` 请求体中包含 `config_id=5`
- **THEN** 后端加载 ID 为 5 的配置，并使用该配置对应的 Provider 和模型生成回答

#### Scenario: 未指定配置时使用默认
- **WHEN** 请求体中未包含 `config_id`
- **THEN** 后端优先加载数据库中标记为 `is_default=True` 的配置；若无，则 fallback 到 `.env` 配置

### Requirement: 前端配置界面
系统 SHALL 提供一个专门的配置页面，允许用户管理 LLM 设置。

#### Scenario: 在前端添加配置
- **WHEN** 用户在配置页填写表单并点击保存
- **THEN** 调用后端 API 保存配置，并刷新配置列表

#### Scenario: 在聊天界面切换模型
- **WHEN** 用户在聊天窗口的模型选择器中更改选项
- **THEN** 后续的发送请求都将携带新选中的 `config_id`

## MODIFIED Requirements

### Requirement: 调用大模型生成回答
系统 SHALL 通过抽象 provider 调用大模型生成回答，并返回结构化结果。Provider 和模型信息优先从数据库加载。

#### Scenario: 正常生成回答
- **WHEN** 传入有效的检索上下文、问题和历史消息，且提供了 `config_id`
- **THEN** 系统根据 `config_id` 加载对应的适配器，发起请求并返回结果

#### Scenario: API 调用失败时返回错误结构
- **WHEN** 调用 LLM API 时发生异常
- **THEN** 系统返回 success: false，并包含友好化的错误描述

### Requirement: 模型参数配置
系统 SHALL 支持通过数据库配置模型名称、API Key 和 Provider，并在调用时应用。

#### Scenario: 使用数据库中的参数
- **WHEN** 加载某套配置
- **THEN** 系统使用该配置定义的 `model_name`、`api_key` 和 `base_url` 发起请求
