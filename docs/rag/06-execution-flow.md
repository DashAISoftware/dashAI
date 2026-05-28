# 06 — Execution Flow

## Lifecycle of a RAG Query

```
User types in GenerativeChat
         │
         ▼
POST /api/v1/generative_process/
  { session_id, input_text }
         │
         ▼
API creates GenerativeProcess (PENDING)
  + ProcessData (input text)
  + Enqueues RAGJob
         │
         ▼
Huey Worker picks up RAGJob:
         │
    ┌────┴────────────────────────────────────────┐
    │ 1. Reconstruct RAGPipeline from session params │
    │    (stored in GenerativeSession)             │
    │                                               │
    │ 2. Parse conversation history                 │
    │    (previous messages in session)             │
    │                                               │
    │ 3. pipeline.generate(input_data)              │
    │    ├─ retriever.retrieve(query) → chunks      │
    │    ├─ prompt.format(input, chunks) → prompt   │
    │    └─ llm_model.generate(history + prompt)    │
    │                                               │
    │ 4. Save response to ProcessData               │
    │    + chunk reference metadata as second item  │
    │                                               │
    │ 5. Update process status → FINISHED           │
    └──────────────────────────────────────────────┘
         │
         ▼
Frontend polls GET /api/v1/jobs/{job_id}
  → Detects FINISHED
  → Parses response text + source references
         │
         ▼
GenerativeChat renders:
  - LLM response text
  - "References" section → DocumentReferencesModal
    (shows which chunks were used)
```

## Pipeline Generate Detail

```python
def generate(self, input_data: Tuple[str, List[Dict[str, str]]]) -> Tuple[str, Dict[str, Any]]:
    # input_data format: tuple of (history_message_1, history_message_2, ..., last_message)
    # last_message = {"role": "user", "content": actual_query}
    input_dict = input_data[-1]
    input_message = input_dict['content']
    history = input_data[:-1]

    # 1. RETRIEVAL
    chunks = self.single_interaction(input_message)
    # → List[Chunk]

    # 2. PROMPT FORMATTING
    chunks_texts = []
    chunk_dict = {}
    for chunk in chunks:
        doc = self.documents[chunk.document_id]
        chunks_texts.append(
            f"Document {doc.file_name}, chunk n {chunk.document_position}, "
            f"text:\n {chunk.text}"
        )
        chunk_dict[chunk.id] = {
            "document_id": chunk.document_id,
            "document_name": doc.file_name,
            "document_position": chunk.document_position,
            "text": chunk.text
        }
    prompt = self.prompt_model.format(input=input_message, chunks="\n\n".join(chunks_texts))

    # 3. GENERATION
    model_input = history + [{"role": "user", "content": prompt}]
    output = self.llm_model.generate(model_input)

    # 4. RETURN
    return [output[0], chunk_dict]
    # chunk_dict is stored as ProcessData (type: Dict)
    # Frontend uses it to render the References section
```

## Session Creation Lifecycle

### Frontend → Backend
1. **Parameter Collection**: `SimplifiedSessionSetup` gathers documents, chunking strategy, retriever, prompt, generator
2. **Pre-validation**: Cross-component validation (chunk_size * top_k ≤ LLM context window)
3. **API Call**: `POST /api/v1/generative_session/` with `task_name="RAGTask"`, `model_name="RAGPipeline"`

### Backend Processing
1. **Component Verification**: RAGPipeline + RAGTask registered in ComponentRegistry
2. **Document Validation**: All document IDs exist in DB
3. **Schema Validation**: `RAGPipeline.SCHEMA.model_validate(params)`
4. **Persistence**:
   - Create `GenerativeSession` row
   - Create `GenerativeSessionParameterHistory` entry
   - Pipeline model row created lazily (first time `RAGPipeline.__init__` runs)
5. **Return**: session ID + metadata to frontend

## Cleanup Flow

When a session is deleted:
1. **Retriever cleanup runs FIRST** (before chunking models)
   - Delete `RAGRetriever` rows (cascade deletes `RAGSparseRetriever`, `RAGDenseRetriever`, `RAGRetrieverChild`)
   - Delete on-disk storage folders
2. **Then chunking models**: `RAGChunkingModel` rows (cascade via FK)
3. **Orphaned resources**: `_cleanup_orphaned_rag_resources()` removes `RAGGenerationModel`, `RAGPrompt` entries no longer referenced
4. **Chunk cleanup**: `chunk_set` cascade covers `Chunk` rows
