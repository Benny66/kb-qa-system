## Why

Currently, the system is tightly coupled with ZhipuAI (智谱 AI) and relies on `.env` files for configuration. This makes it difficult for non-technical users to switch providers or models without access to the server's filesystem. We need a more flexible approach that allows users to:
1.  **Configure multiple LLM providers** (Doubao, Qianwen, Ernie Bot, Minimax, etc.) via a user-friendly management interface.
2.  **Switch models dynamically** during a chat session to optimize for cost or performance.
3.  **Store configurations in a database** rather than hardcoding them in environment variables, enabling multi-user or multi-tenant settings in the future.

## What Changes

- **Backend Abstraction**: Create an `LLMProvider` abstraction layer in `ai_service.py` to support multiple adapters.
- **Database Schema**: Add a `LLMConfig` table to store API keys, base URLs, model names, and provider types.
- **Management API**: Implement CRUD endpoints for `LLMConfig`.
- **Chat API Update**: Update `/api/chat` and `/api/chat/stream` to accept an optional `config_id` to use a specific LLM configuration.
- **Frontend Configuration Page**: Create a new "LLM Settings" page in the frontend to manage these configurations.
- **Dynamic Model Selector**: Add a dropdown in the chat interface to allow users to select an active model from the saved configurations.
- **Default Config**: Use a designated "default" configuration if no specific `config_id` is provided.

## Capabilities

### New Capabilities
- `multi-llm-provider`: LLM provider abstraction and adapter implementations for multiple domestic models.
- `llm-config-management`: Database-backed management system for LLM configurations with a dedicated UI.

### Modified Capabilities
- `ai-service`: Updated to fetch LLM settings from the database and support dynamic provider switching.

## Impact

- **Database**: New `LLMConfig` table in the SQLite database.
- **API**: New endpoints for managing LLM configurations.
- **Frontend**: New configuration UI and model selection logic in the chat view.
- **Security**: API keys will be stored in the database. We should consider basic encryption or masking in the UI.
