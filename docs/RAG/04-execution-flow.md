# End-to-End Execution Flow

## Step-by-Step

### 1. Session Configuration

The user fills the `RAGSessionSetup` form:
- Selects documents from the repository.
- Configures the chunking model (type, chunk size, overlap).
- Chooses a retriever (preset or custom composite).
- Selects a prompt template (language, optional custom template).
- Picks an LLM (model name, parameters like temperature, context window).

### 2. Session Creation

Frontend calls `POST /api/v1/generative-session/` with the full parameter
payload. The endpoint performs these validation steps before persisting:

1. **Model & task validation** — checks `model_name` and `task_name` exist in
   the component registry.
2. **Document validation** — ensures documents list is non-empty and all IDs
   exist in the database.
3. **Parameter normalization** — `normalize_payload()` transforms frontend-style
   property wrappers.
4. **Prompt resolution** — if `prompt_id` is provided, it is resolved to a
   `{component, params}` ref (validates prompt exists + template placeholders).
5. **Schema validation** — `RAGPipeline.SCHEMA.model_validate()` validates
   the full parameter structure.
6. **Component validation** — `validate_component_refs()` recursively checks
   that all `{component, params}` references exist in the registry.
7. **Prompt template validation** — if an explicit template is given, validates
   that it contains the required placeholders (`{input}`, `{chunks}`).

On success, a `GenerativeSession` record is persisted with:
- `task_name` — Set to `"RAGTask"` for RAG sessions.
- `model_name` — Set to `"RAGPipeline"`.
- `parameters` — The validated configuration dict.

### 3. Process Creation

When the user sends a message, the frontend calls
`POST /api/v1/generative-process/` with the input text. This creates a
