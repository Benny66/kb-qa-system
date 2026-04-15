## Context

The current `ai_service.py` is hardcoded to use ZhipuAI and `.env` settings. We need a flexible architecture to manage multiple LLM configurations via a database and switch them dynamically.

## Goals / Non-Goals

**Goals:**
- **Database-backed LLM Configurations**: Store provider settings in a new `LLMConfig` table.
- **Dynamic Provider Switching**: Support passing a `config_id` to chat APIs to use a specific LLM setup.
- **Management UI**: Provide a frontend page to add, edit, and delete LLM configurations.
- **Abstraction Layer**: Maintain a clean `LLMProvider` interface to support multiple backend adapters (OpenAI-compatible, ErnieBot, etc.).

**Non-Goals:**
- **Advanced Encryption**: While keys will be stored in the DB, we won't implement enterprise-grade encryption for now (simple base64 or plain text).
- **Multi-tenant isolation**: All users share the same pool of LLM configurations for now.

## Decisions

### 1. Database Schema

Add a new `LLMConfig` model in `models.py`:
- `id`: Integer Primary Key
- `name`: String (Human-readable name for the config, e.g., "Fast Model", "Expensive Pro")
- `provider`: String (e.g., "zhipuai", "doubao", "qianwen", "minimax", "erniebot")
- `api_key`: String
- `base_url`: String (optional, for OpenAI-compatible providers)
- `model_name`: String (e.g., "glm-4-flash", "doubao-pro")
- `is_default`: Boolean (flag to indicate the system-wide default)
- `created_at` / `updated_at`: Timestamps

### 2. API Design

**Management API:**
- `GET /api/llm-configs`: List all saved LLM configurations.
- `POST /api/llm-configs`: Create a new LLM configuration.
- `PUT /api/llm-configs/<id>`: Update an existing configuration.
- `DELETE /api/llm-configs/<id>`: Delete a configuration.
- `POST /api/llm-configs/<id>/set-default`: Set a configuration as the system default.

**Chat API Update:**
- `POST /api/chat` and `POST /api/chat/stream`: Accept an optional `config_id` in the request body.

### 3. Provider Resolution Logic

The `ai_service.py` will follow this resolution order:
1.  Use `config_id` passed in the request.
2.  If `config_id` is missing, fetch the `is_default=True` configuration from the DB.
3.  If no default exists in the DB, fallback to existing `.env` settings (for backward compatibility).

### 4. Frontend Interaction

- **Configuration Page**: A dedicated "LLM Settings" view reachable from the sidebar/navbar.
- **Chat View**: A dropdown/selector above the chat input to pick from the list of available configurations.

## Risks / Trade-offs

- [Risk] Exposing API keys in the DB. -> Mitigation: Mask keys in the frontend (e.g., "sk-••••••••").
- [Risk] Complexity in managing multiple providers. -> Mitigation: Use a factory pattern with adapters to keep logic clean.
- [Risk] Database performance. -> Mitigation: SQLite is sufficient for this volume of configurations; we can cache the default config if needed.

## Migration Plan

1.  **Phase 1**: Update `models.py` and run migrations (via `init_db`).
2.  **Phase 2**: Implement `ai_service.py` abstraction and adapters.
3.  **Phase 3**: Implement CRUD APIs for `LLMConfig`.
4.  **Phase 4**: Build the frontend configuration UI and integrate model selection in the chat.
