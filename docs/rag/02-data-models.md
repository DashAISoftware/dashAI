# 02 — Data Models

All RAG-related SQLAlchemy models live in `DashAI/back/dependencies/database/models.py`.

## Entity-Relationship Summary

```
Document ──< Chunk >── RAGChunkSet ──< RAGChunkSetDocument >── Document
                    >── RAGEmbeddingMatrix >── RAGEmbeddingModel
                    >── RAGRetrieverChunkSet >── RAGRetriever >── RAGRetrieverChild
                                                                 >── RAGSparseRetriever
                                                                 >── RAGDenseRetriever >── RAGEmbeddingModel

RAGPrompt ──< RAGPipeline >── GenerativeSession
RAGGenerationModel ──< RAGPipeline
RAGChunkingModel ──< RAGPipeline

RAGDocumentPipelineSessionLink: Document <-> GenerativeSession <-> RAGPipeline
```

## Model Catalog (16 tables)

### 1. `Document` → `document`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer PK | autoincrement |
| `file_name` | String | NOT NULL |
| `file_type` | String | NOT NULL |
| `file_path` | String | NOT NULL |
| `file_hash` | String | NOT NULL, UNIQUE |
| `optional_metadata` | JSON | nullable |
| `created` | DateTime | default=now |
| `last_modified` | DateTime | default=now, onupdate=now |

Relationships: `chunks` → `Chunk`, `embedding_matrices` → `RAGEmbeddingMatrix`, `pipeline_links` → `RAGDocumentPipelineSessionLink`

### 2. `Chunk` → `chunk`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer PK | autoincrement |
| `chunk_set_id` | FK → `rag_chunk_set.id` | ON DELETE CASCADE, NOT NULL |
| `document_id` | FK → `document.id` | ON DELETE CASCADE, NOT NULL |
| `chunk_index` | Integer | NOT NULL |
| `text` | Text | NOT NULL |
| `metadata` | JSON | nullable |

**Unique constraint**: `("chunk_set_id", "document_id", "chunk_index")` as `uix_chunk_set_doc_index`

The `metadata` column stores format-specific region tracking: `{"page": 3, "bbox": [...]}` for PDF, `{"row": 10, "column": "name"}` for CSV. Format-agnostic.

### 3. `RAGChunkSet` → `rag_chunk_set`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer PK | autoincrement |
| `signature` | String | NOT NULL, UNIQUE |
| `parameters` | JSON | nullable |

Signature = `SHA-256(sorted(document_ids) + serialized_pipeline_config)`. When documents or pipeline config change, the signature changes → new chunk_set row. This enables deterministic reuse: two sessions with the same docs + config share the same chunk_set.

Relationships: `chunks`, `documents` (via RAGChunkSetDocument), `embedding_matrices`, `retriever_links`

### 4. `RAGChunkSetDocument` → `rag_chunk_set_document`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer PK | autoincrement |
| `chunk_set_id` | FK → `rag_chunk_set.id` | ON DELETE CASCADE, NOT NULL |
| `document_id` | FK → `document.id` | ON DELETE CASCADE, NOT NULL |

**Unique constraint**: `("chunk_set_id", "document_id")` as `uix_chunk_set_document`

### 5. `RAGRetrieverChunkSet` → `rag_retriever_chunk_set`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer PK | autoincrement |
| `retriever_id` | FK → `rag_retriever.id` | ON DELETE CASCADE, NOT NULL |
| `chunk_set_id` | FK → `rag_chunk_set.id` | ON DELETE CASCADE, NOT NULL |

**Unique constraint**: `("retriever_id", "chunk_set_id")` as `uix_retriever_chunk_set`

### 6. `RAGPrompt` → `rag_prompt`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer PK | autoincrement |
| `class_name` | String | NOT NULL |
| `name` | String | nullable |
| `parameters` | JSON | nullable |
| `created` | DateTime | default=now |
| `last_modified` | DateTime | default=now, onupdate=now |

**Unique constraint**: `("class_name", "parameters")` as `uix_rag_prompt_class_params`

### 7. `RAGGenerationModel` → `rag_generation_model`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer PK | autoincrement |
| `class_name` | String | NOT NULL |
| `parameters` | JSON | nullable |

**Unique constraint**: `("class_name", "parameters")` as `uix_rag_gen_model_class_params`

### 8. `RAGPipeline` → `rag_pipeline`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer PK | autoincrement |
| `session_id` | FK → `generative_session.id` | ON DELETE CASCADE, NOT NULL |
| `name` | String | NOT NULL |
| `description` | String | nullable |
| `parameters` | JSON | nullable |
| `chunking_model_id` | FK → `rag_chunking_model.id` | ON DELETE CASCADE, NOT NULL |
| `prompt_id` | FK → `rag_prompt.id` | ON DELETE CASCADE, NOT NULL |
| `generation_model_id` | FK → `rag_generation_model.id` | ON DELETE CASCADE, NOT NULL |

FK direction: retrievers reference pipeline, not the reverse. `RAGRetriever.pipeline_id` → `RAGPipeline.id`.

### 9. `RAGChunkingModel` → `rag_chunking_model`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer PK | autoincrement |
| `class_name` | String | NOT NULL |
| `parameters` | JSON | nullable |

**Unique constraint**: `("class_name", "parameters")` as `uix_rag_chunking_model_class_params`

### 10. `RAGRetriever` → `rag_retriever`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer PK | autoincrement |
| `class_name` | String | NOT NULL |
| `pipeline_id` | FK → `rag_pipeline.id` | ON DELETE CASCADE, NOT NULL |

This is the canonical identity row for every retriever — unit (sparse/dense) or composite. It acts as a bridge: `RAGSparseRetriever.bridge_id` and `RAGDenseRetriever.bridge_id` point here.

Relationships: `pipeline`, `children` (→ RAGRetrieverChild), `sparse_detail`, `dense_detail`

### 11. `RAGRetrieverChild` → `rag_retriever_child`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer PK | autoincrement |
| `parent_id` | FK → `rag_retriever.id` | ON DELETE CASCADE, NOT NULL |
| `child_id` | FK → `rag_retriever.id` | ON DELETE CASCADE, NOT NULL |
| `child_order` | Integer | NOT NULL |

**Unique constraint**: `("parent_id", "child_order")` as `uix_retriever_child_order`

### 12. `RAGSparseRetriever` → `rag_sparse_retriever`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer PK | autoincrement |
| `bridge_id` | FK → `rag_retriever.id` | ON DELETE CASCADE, NOT NULL |
| `chunk_set_id` | FK → `rag_chunk_set.id` | ON DELETE CASCADE, NOT NULL |
| `class_name` | String | NOT NULL |
| `parameters` | JSON | nullable |
| `storage_folder` | String | NOT NULL |

**Unique constraint**: `("class_name", "parameters", "chunk_set_id")` as `uix_rag_sparse_retriever`

### 13. `RAGDenseRetriever` → `rag_dense_retriever`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer PK | autoincrement |
| `bridge_id` | FK → `rag_retriever.id` | ON DELETE CASCADE, NOT NULL |
| `chunk_set_id` | FK → `rag_chunk_set.id` | ON DELETE CASCADE, NOT NULL |
| `class_name` | String | NOT NULL |
| `parameters` | JSON | nullable |
| `embedding_model_id` | FK → `rag_embedding_model.id` | ON DELETE CASCADE, NOT NULL |

**Unique constraint**: `("class_name", "parameters", "chunk_set_id", "embedding_model_id")` as `uix_rag_dense_retriever`

### 14. `RAGEmbeddingModel` → `rag_embedding_model`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer PK | autoincrement |
| `class_name` | String | NOT NULL |
| `parameters` | JSON | nullable |

**Unique constraint**: `("class_name", "parameters")` as `uix_rag_embedding_model_class_params`

### 15. `RAGEmbeddingMatrix` → `rag_embedding_matrix`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer PK | autoincrement |
| `document_id` | FK → `document.id` | ON DELETE CASCADE, NOT NULL |
| `chunk_set_id` | FK → `rag_chunk_set.id` | ON DELETE CASCADE, NOT NULL |
| `embedding_model_id` | FK → `rag_embedding_model.id` | ON DELETE CASCADE, NOT NULL |
| `storage_folder` | String | NOT NULL |
| `matrix_shape` | JSON | NOT NULL |
| `created` | DateTime | default=now |
| `last_modified` | DateTime | default=now, onupdate=now |

**Unique constraint**: `("document_id", "chunk_set_id", "embedding_model_id")` as `uix_document_chunk_set_embedding`

Properties: `num_chunks` (matrix_shape[0]), `embedding_dimension` (matrix_shape[1])

### 16. `RAGDocumentPipelineSessionLink` → `rag_document_pipeline_session_link`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer PK | autoincrement |
| `document_id` | FK → `document.id` | ON DELETE CASCADE, NOT NULL |
| `session_id` | FK → `generative_session.id` | ON DELETE CASCADE, NOT NULL |
| `pipeline_id` | FK → `rag_pipeline.id` | ON DELETE CASCADE, NOT NULL |

**Unique constraints**: `("document_id", "session_id")`, `("session_id", "pipeline_id")`, `("document_id", "pipeline_id")`

Uses legacy `Column()` syntax — the only RAG model not yet migrated to `mapped_column()`.

## Chunk Set Architecture

The chunk_set system provides deterministic, content-addressable identity for chunking results.

**Why**: Multiple sessions with identical documents and chunking config should share chunks rather than re-chunking. When documents or config change, the signature changes → new chunk_set → re-chunk.

**Signature formula**:
```
SHA-256(
    json.dumps({
        "doc_ids": sorted(document_ids),
        "config": dict(sorted(pipeline_config.items())),
    }, sort_keys=True)
)
```

**Tables involved**:
- `RAGChunkSet` — one row per unique signature
- `RAGChunkSetDocument` — which documents belong to a chunk_set
- `Chunk.chunk_set_id` — FK to RAGChunkSet
- `RAGRetrieverChunkSet` — which retriever uses which chunk_set

**Flow**:
1. `get_or_create_chunk_set(db, doc_ids, config)` → computes signature → finds or creates row
2. `ChunkingModelsFactory.init_component_by_name()` receives `chunk_set_id`
3. Chunks are persisted with `chunk_set_id` FK
4. Retrievers are linked to the same `chunk_set_id`

## Uniqueness Constraints — Reuse by Design

All component-configuration tables have uniqueness on `(class_name, parameters)`, enabling automatic row reuse:

| Table | Unique Constraint | Effect |
|-------|------------------|--------|
| `rag_prompt` | `(class_name, parameters)` | Same prompt config reused |
| `rag_generation_model` | `(class_name, parameters)` | Same LLM config reused |
| `rag_chunking_model` | `(class_name, parameters)` | Same chunking config reused |
| `rag_embedding_model` | `(class_name, parameters)` | Same embedding config reused |
| `rag_sparse_retriever` | `(class_name, parameters, chunk_set_id)` | Same retriever + chunk_set reused |
| `rag_dense_retriever` | `(class_name, parameters, chunk_set_id, embedding_model_id)` | Same retriever + chunk_set + embedding reused |
| `rag_embedding_matrix` | `(document_id, chunk_set_id, embedding_model_id)` | Same doc+chunk_set+embedding reused |
| `chunk` | `(chunk_set_id, document_id, chunk_index)` | Same chunk position reused |
