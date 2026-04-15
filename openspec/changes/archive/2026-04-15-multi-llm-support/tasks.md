## 1. Database & Models

- [x] 1.1 Add `LLMConfig` model in `models.py`
- [x] 1.2 Update `init_db()` in `app.py` to create the new table
- [x] 1.3 Add helper methods to `models.py` for fetching LLM configurations

## 2. Core Abstraction & Adapters

- [x] 2.1 Define `LLMResponse` and `LLMProvider` interface in `ai_service.py`
- [x] 2.2 Implement `ZhipuAIAdapter`
- [x] 2.3 Implement `OpenAICompatibleAdapter` (for Doubao, Qianwen, etc.)
- [x] 2.4 Implement a registry and factory for providers

## 3. Backend Management API

- [x] 3.1 Implement `GET /api/llm-configs` (with API key masking)
- [x] 3.2 Implement `POST /api/llm-configs`
- [x] 3.3 Implement `PUT /api/llm-configs/<id>`
- [x] 3.4 Implement `DELETE /api/llm-configs/<id>`
- [x] 3.5 Implement `POST /api/llm-configs/<id>/set-default`

## 4. Integration with Chat API

- [x] 4.1 Update `/api/chat` to accept `config_id` and load provider accordingly
- [x] 4.2 Update `/api/chat/stream` to accept `config_id` and load provider accordingly
- [x] 4.3 Ensure fallback to `.env` if no configurations exist in the database

## 5. Frontend Development

- [x] 5.1 Create a new `SettingsView.vue` for LLM configuration management
- [x] 5.2 Add API service methods for managing LLM configurations
- [x] 5.3 Implement model selection dropdown in `ChatView.vue`
- [x] 5.4 Update navigation (sidebar/navbar) to include a link to the LLM settings page

## 6. Testing & Verification

- [x] 6.1 Verify adding and editing LLM configurations in the UI
- [x] 6.2 Test dynamic model switching during chat
- [x] 6.3 Verify that API keys are never exposed in the UI as plain text
