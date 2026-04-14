## 1. 规格文档归档至 openspec/specs/

- [ ] 1.1 将 specs/user-auth/spec.md 归档至 openspec/specs/user-auth/spec.md
- [ ] 1.2 将 specs/knowledge-base/spec.md 归档至 openspec/specs/knowledge-base/spec.md
- [ ] 1.3 将 specs/rag-service/spec.md 归档至 openspec/specs/rag-service/spec.md
- [ ] 1.4 将 specs/ai-service/spec.md 归档至 openspec/specs/ai-service/spec.md
- [ ] 1.5 将 specs/chat-session/spec.md 归档至 openspec/specs/chat-session/spec.md
- [ ] 1.6 将 specs/frontend-interaction/spec.md 归档至 openspec/specs/frontend-interaction/spec.md

## 2. 验证规格文件格式

- [ ] 2.1 运行 openspec validate 检查所有规格文件格式是否合法
- [ ] 2.2 确认每个规格文件的 Requirement 均包含至少一个 Scenario
- [ ] 2.3 确认所有 Scenario 使用 #### 四级标题（非三级）

## 3. 规格与代码一致性核查

- [ ] 3.1 核查 user-auth 规格与 app.py 认证接口实现是否一致
- [ ] 3.2 核查 knowledge-base 规格与 app.py 知识库接口、document_loader.py 实现是否一致
- [ ] 3.3 核查 rag-service 规格与 rag_service.py 实现是否一致（切分参数、ChromaDB 过滤条件）
- [ ] 3.4 核查 ai-service 规格与 ai_service.py 实现是否一致（Prompt 结构、错误处理）
- [ ] 3.5 核查 chat-session 规格与 app.py 会话/历史接口实现是否一致
- [ ] 3.6 核查 frontend-interaction 规格与前端 src/ 各模块实现是否一致

## 4. 归档变更

- [ ] 4.1 运行 openspec archive kb-qa-system-architecture 完成变更归档
- [ ] 4.2 确认 openspec/specs/ 下 6 个模块规格文件已正确生成
