# RAG Module — ID & Reference System Status

## Completed

### Critical bugs fixed
| Bug | Fix |
|-----|-----|
| Cleanup: chunking model deleted BEFORE retriever → retriever rows silently skipped | Reordered: retriever cleanup runs first, then chunking |
| `save_dense_retriever_model_to_db`: `class_name=DenseRetriever.__name__` hardcoded | Changed to `instance.__class__.__name__` |
| `save_sparse_retriever_model_to_db`: same hardcoded `SparseRetriever.__name__` | Changed to `instance.__class__.__name__` |
| `save_sparse_retriever_model_to_db`: `storage_folder=""` committed before update → crash window | Generate folder via `uuid4()` before first commit; single transaction |
| `RAGGenerationModel` never cleaned up | Added cleanup in `_cleanup_orphaned_rag_resources` |

### DB uniqueness constraints added
| Table | Constraint |
|-------|-----------|
| `chunk` | `(document_id, chunk_index, chunking_model_id)` (replaced useless `(id, document_id)`) |
| `rag_prompt` | `(class_name, parameters)` |
| `rag_generation_model` | `(class_name, parameters)` |
| `rag_chunking_model` | `(class_name, parameters)` |
| `rag_embedding_model` | `(class_name, parameters)` |
| `rag_sparse_retriever` | `(class_name, parameters, documents_ids, chunking_model_id)` |
| `rag_dense_retriever` | `(class_name, parameters, document_ids, chunking_model_id, embedding_model_id)` |
| `rag_embedding_matrix` | Already had `(document_id, chunking_model_id, embedding_model_id)` — correct |

### Reuse now works at DB level
- Chunks: same `(doc, index, chunking_model)` → unique, reused across sessions
- Embeddings: same `(doc, chunking_model, embedding_model)` → unique, reused
- Chunking models: same `(class, params)` → unique, reused
- Prompts, generation models, embedding models: same `(class, params)` → unique

### Per-session retriever instances
- Each session gets its own `RAGSparseRetriever` / `RAGDenseRetriever` / `RAGRetriever` row
- The unique constraints prevent DUPLICATE IDs for the same config, but allow MULTIPLE rows with different configs (different params, different documents)

### Traceability
- Session → `RAGPipeline` → `RAGRetriever` → sparse/dense child
- `RAGSparseRetriever.storage_folder` traced via FK chain
- Cleanup recursively deletes storage folders and DB rows

---

## Pending

### 1. `pipeline_id` on retriever models
- Neither `RAGSparseRetriever`, `RAGDenseRetriever`, nor `RAGRetriever` have a `pipeline_id` column
- The link is only through `RAGPipeline.retriever_model_id` → `RAGRetriever.id`
- Adding a reverse FK would allow direct traceability: "which retriever belongs to which pipeline?"
- **Impact**: Low. Current FK chain already provides traceability.

### 2. `_load_composite_from_db` filtering
- `retriever_models_factory.py:_load_composite_from_db` queries by `class_name` only
- In a multi-pipeline setup with same composite class, wrong row could be returned
- **Mitigation**: in practice, each session has its own pipeline and composite
- **Fix needed**: join through `RAGPipeline` to filter by `pipeline_id`

### 3. Chunk cleanup on document removal
- `chunking_models_factory.py:update_db_models` creates new chunks but never deletes old ones
- If documents are removed from a session, chunks for removed documents remain orphaned
- **Impact**: disk space waste, no correctness issue
- **Fix**: add deletion of chunks whose `document_id` is no longer in the session's document list

### 4. Prompt cleanup heuristic
- Prompts are cleaned up only if name contains `" - session {id}"`
- If a prompt was created without this naming convention, it's never cleaned
- **Fix**: session-scoped prompts should have an FK to GenerativeSession
