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
`GenerativeProcess` record linked to the session, with `status="PENDING"`.

### 4. Job Dispatch

The frontend calls `POST /api/v1/job/` with `job_type="GenerativeJob"` and the
`generative_process_id`. The job is enqueued in the Huey async task queue.

### 5. Job Execution

`GenerativeJob.run()` performs an initial DB lookup:
```
Query session → check task_name → if task is RAGTask:
    delegate to RAGJob.run()
    return
```

If the task is **not** a RAG task, `GenerativeJob` proceeds with the standard
generation flow. `RAGJob` itself is a standalone `BaseJob` subclass (not a
subclass of `GenerativeJob`), instantiated and executed independently.

### 6. Pipeline Construction (in RAGJob)

```
RAGJob.run():
  │
  ├── 1. Query GenerativeProcess + GenerativeSession from DB
  │
  ├── 2. Build RAGPipelineConfig.from_kwargs()
  │       Uses session parameters + injected DB + registry + env path
  │
  └── 3. RAGSetupService.build_pipeline(config)
         DocumentService → ChunkingService → RetrieverSetupService
         → LLMService → PromptService → RAGPipeline
```

### 7. RAGSetupService.build_pipeline()

```
  │
  ├── a. _ensure_db_record(session_id)
  │       Creates or finds the rag_pipeline table row.
  │
  ├── b. DocumentService.load(documents)
  │       Fetches documents from DB, hydrates BaseDocument objects.
  │
  ├── c. ChunkingService.get_or_create_chunk_set(doc_ids, config)
  │       SHA-256 signature → reuse or create new chunk set.
  │
  ├── d. ChunkingService.create(docs, chunk_set, component, params)
  │       Creates chunker → chunks docs → persists chunks.
  │
  ├── e. RetrieverSetupService.setup(component, params)
  │       Lookup-or-create retriever → compute embeddings → persist.
  │
  ├── f. LLMService.get_or_create(component, params)
  │       Lookup-or-create LLM record.
  │
  ├── g. PromptService.create(class_name, name, params)
  │       Persists prompt record.
  │
  ├── h. _update_db_record(...)
  │       Patches the pipeline record with real component FK IDs.
  │
  └── i. Assemble and return RAGPipeline(config, documents, chunks, ...)
```

### 8. History Preparation

The job queries all previous `GenerativeProcess` records for the session with
`status="FINISHED"` and builds a list of `(input, output)` tuples. The
`RAGTask.prepare_for_task()` method folds this history into a message list:

```
[
  {"role": "user", "content": "Previous input"},
  {"role": "assistant", "content": "Previous output"},
  {"role": "user", "content": "Current input"}
]
```

### 9. Generation

`RAGPipeline.generate(input_data)`:

```
  │
  ├── a. Extract input message + history from input_data
  │       (reads the last entry as the current query)
  │
  ├── b. single_interaction(query) → retriever.retrieve(query)
  │       Returns top-k Chunk objects relevant to the query.
  │
  ├── c. _build_chunk_references(chunks)
  │       Formats chunks into text block + ChunkReference dict.
  │
  ├── d. prompt_model.format(input=query, chunks=chunk_text)
  │       Renders the prompt template with query + chunk context.
  │
  ├── e. llm_model.generate(list(history) + [{"role": "user", "content": prompt}])
  │       LLM generates a response text.
  │
  └── f. Return RAGGenerationOutput(message, chunks)
```

### 10. Output Processing

`RAGTask.process_output(output)`:

1. Unpacks `output.message` (LLM response text) and `output.chunks` (dict of
   `ChunkReference` objects with document metadata).
2. Returns a list of `(data, type)` tuples:
   - `(response_text, "str")`
   - `(json_chunk_references, "Dict")`

### 11. Persistence

`RAGJob` creates `ProcessData` records for each output tuple, links them to the
`GenerativeProcess`, and sets the process status to `"FINISHED"`.

### 12. Frontend Polling

The frontend polls `GET /api/v1/jobs/{job_id}` for job status. When the job
completes, it reads the process output and renders the chat response with
cited chunk references.
