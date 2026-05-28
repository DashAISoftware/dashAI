# Frontend Changes Required — RAG Factory Refactoring (May 2026)

This document describes the frontend changes needed to align with the
backend factory refactoring. The core change is: **prompts are now
components (like chunking, retriever, and LLM)**, not a simple ID reference.

## TL;DR

| What changed | Before | After |
|-------------|--------|-------|
| Prompt in session params | `"prompt_id": 5` | `"prompt": {"component": "DefaultGenerationPrompt", "params": {...}}` |
| Schema field | `prompt_id: int_field(gt=0)` | `prompt: component_field(parent="Prompt")` |
| API request body | `{"prompt_id": 5, ...}` | `{"prompt": {"component": "...", "params": {...}}, ...}` |

## 1. Session Creation Payload

### Before
```json
{
  "task_name": "RAGTask",
  "model_name": "RAGPipeline",
  "parameters": {
    "documents": [1, 2],
    "chunking_model": {
      "component": "CharacterChunkModel",
      "params": {"chunk_size": 500, "chunk_overlap": 50}
    },
    "retriever_model": {
      "component": "TFIDFRetriever",
      "params": {"top_k": 5, "similarity_function": "cosine"}
    },
    "generation_model": {
      "component": "OpenAITextToTextGenerationModel",
      "params": {"model": "gpt-4"}
    },
    "prompt_id": 5
  }
}
```

### After
```json
{
  "task_name": "RAGTask",
  "model_name": "RAGPipeline",
  "parameters": {
    "documents": [1, 2],
    "chunking_model": { ... },
    "retriever_model": { ... },
    "generation_model": { ... },
    "prompt": {
      "component": "DefaultGenerationPrompt",
      "params": {
        "name": "Default Prompt",
        "template": "Answer using these chunks:\n{chunks}\n\nUser: {input}"
      }
    }
  }
}
```

## 2. Files That Need Changes

### 2.1 `SimplifiedSessionSetup.jsx` (creation form)

**Current**: sends `prompt_id: int` in the session creation payload.
**New**: must construct `prompt: {component, params}`.

The `PromptBody` component currently stores a `prompt_id` in the form state.
Change to store the full component ref:

```jsx
// Before:
onSavedParams({ prompt_id: selectedPromptId })

// After:
onSavedParams({
  prompt: {
    component: selectedPromptComponent,  // e.g., "DefaultGenerationPrompt"
    params: promptParams,                 // e.g., { template: "...", name: "..." }
  }
})
```

### 2.2 `api/rag.ts` (API calls)

The TypeScript interface for session creation parameters must change:

```typescript
// Before
interface RAGSessionParams {
  documents: number[];
  chunking_model: { component: string; params: Record<string, any> };
  retriever_model: { component: string; params: Record<string, any> };
  generation_model: { component: string; params: Record<string, any> };
  prompt_id: number;
}

// After
interface RAGSessionParams {
  documents: number[];
  chunking_model: { component: string; params: Record<string, any> };
  retriever_model: { component: string; params: Record<string, any> };
  generation_model: { component: string; params: Record<string, any> };
  prompt: { component: string; params: Record<string, any> };
}
```

### 2.3 `RAGParamsPanel.jsx` (edit prompt in existing session)

Currently loads and saves prompts by ID. Must change to:
- Load: receive the full `prompt: {component, params}` from the session config
- Save: send the full `prompt: {component, params}` back

### 2.4 `PromptBody.jsx` (shared prompt selector)

Currently works with `prompt_id` internally. Must change to use the `ModelRef` format. The recommended approach:

```jsx
// Store as structured object, not just ID
const [promptModelRef, setPromptModelRef] = useState({
  component: null,
  params: {},
});

// When selecting a prompt from the dropdown:
const handlePromptSelect = (promptDbRow) => {
  setPromptModelRef({
    component: promptDbRow.class_name,       // "DefaultGenerationPrompt"
    params: promptDbRow.parameters,           // { template: "...", name: "..." }
  });
};
```

### 2.5 `RAGSessionSummary.jsx` (session overview)

Currently displays `session.parameters.prompt_id`. Must change to display `session.parameters.prompt.component` and `session.parameters.prompt.params`.

### 2.6 `ragFormDefaults.js` (default values)

The schema-driven form defaults must handle the new `component_field(parent="Prompt")` field.

### 2.7 `RAGPromptsPage.jsx` (prompt management page)

The prompt management page (`/app/generative/rag/prompts`) is mostly unaffected — it still displays `RAGPrompt` DB rows. However, if it returns a `prompt_id` to `SimplifiedSessionSetup`, that must change to return a `ModelRef`.

## 3. Backward Compatibility

The old `prompt_id` field no longer exists in `RAGPipelineSchema`:

```python
# REMOVED:
prompt_id: schema_field(int_field(gt=0), ...)

# ADDED:
prompt: schema_field(component_field(parent="Prompt"), ...)
```

The `POST /api/v1/generative_session/` endpoint validates against `RAGPipeline.SCHEMA`. Sending `prompt_id` will fail validation.

## 4. Migration Path for Existing Sessions

Existing sessions in the database have `RAGPipeline.prompt_id` FK values. These are still valid in the DB. The migration affects only NEW session creation and session parameter editing.

If you need to load an OLD session (created with `prompt_id`), the `RAGPipelineConfig.from_kwargs()` expects the new format. The API endpoint `generative_session.py` should handle backward compatibility if needed (add a transform that converts old `prompt_id` to new `prompt: {component, params}` by looking up the prompt DB record).

## 5. Testing Checklist

- [ ] Create a new RAG session with prompt as component (not ID)
- [ ] Edit prompt in an existing session (RAGParamsPanel)
- [ ] Verify the session parameters stored in DB include `prompt: {component, params}`
- [ ] Verify schema validation rejects old `prompt_id` format
- [ ] Verify prompt selection in PromptBody sends correct format
- [ ] Verify RAGPromptsPage still works for browsing/creating prompts

## 6. Key Constants

```typescript
// Registered prompt component names (match backend ComponentRegistry)
const PROMPT_COMPONENTS = [
  "DefaultGenerationPrompt",
  "CustomGenerationPrompt",
  "DefaultQnAGenerationPrompt",
  "DefaultAugmentationPrompt",
  "CustomAugmentationPrompt",
] as const;

// ModelRef shape (same for all component fields)
interface ModelRef {
  component: string;
  params: Record<string, any>;
}
```
