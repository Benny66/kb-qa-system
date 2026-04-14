## ADDED Requirements

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
