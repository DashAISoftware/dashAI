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
payload. The endpoint validates parameters against `RAGPipeline.SCHEMA` and
persists a `GenerativeSession` record in the database. The session stores:
- `task_name` — Set to `"RAGTask"` for RAG sessions.
- `model_name` — Set to `"RAGPipeline"`.
- `parameters` — The full configuration dict (documents, chunking, retriever,
  prompt, generation model).

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
Query session → check task_name → if issubclass(RAGTask):
    delegate to RAGJob.run()
    return
```

If the task is **not** a RAG task, `GenerativeJob` proceeds with the standard
generation flow.

### 6. Pipeline Construction (in RAGJob)

```
RAGJob.run():
  │
  ├── 1. Query GenerativeProcess + GenerativeSession from DB
  │
  ├── 2. Build RAGPipelineConfig.from_kwargs()
  │       Uses session parameters + injected DB + registry + env path
  │
  ├── 3. Create RAGModelsFactory(db, registry, rag_path)
  │
  ├── 4. Create PipelineRepository(db)
  │
  ├── 5. Create DocumentLoader(db)
  │
  └── 6. Assemble RAGPipeline(config, models, repo, doc_loader)
```

### 7. Pipeline Initialisation

During `RAGPipeline.__init__()`:

```
  │
  ├── a. PipelineRepository.ensure_db_record(session_id)
  │       Creates or finds the rag_pipeline table row.
  │
  ├── b. DocumentLoader.load(document_ids)
  │       Fetches documents from DB, hydrates BaseDocument objects.
  │
  ├── c. get_or_create_chunk_set(db, doc_ids, chunking_config)
  │       SHA-256 signature → reuse or create new chunk set.
  │
  ├── d. ModelsFactory.create_prompt(component, params)
  │       Lookup-or-create prompt record in rag_prompt table.
  │
  ├── e. ModelsFactory.create_chunking_model(docs, chunk_set, component, params)
  │       Creates chunker → chunks docs → persists chunks → returns model.
  │
  ├── f. ModelsFactory.create_retriever(pipeline_id, chunks, chunk_set, component, params)
  │       Creates retriever → computes/trains → persists → returns model.
  │
  ├── g. ModelsFactory.create_llm(component, params)
  │       Lookup-or-create LLM record in rag_generation_model table.
  │
  └── h. PipelineRepository.update_db_record(...)
        Patches the pipeline record with real component FK IDs.
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
  │
  ├── b. retriever.retrieve(query)
  │       Returns top-k Chunk objects relevant to the query.
  │
  ├── c. _build_chunk_references(chunks)
  │       Formats chunks into text block + ChunkReference dict.
  │
  ├── d. prompt_model.format(input=query, chunks=chunk_text)
  │       Renders the prompt template with query + chunk context.
  │
  ├── e. llm_model.generate(history + prompt)
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
