# 08 — Migrations

All Alembic migrations live in `DashAI/alembic/versions/`. Four migrations were created during the RAG refactoring (May 2026).

## Migration Summary

| # | File | Purpose |
|---|------|---------|
| 1 | (first) | Composite retriever support: `RAGRetrieverChild` table, `RAGRetriever` bridge expansions |
| 2 | (second) | DB uniqueness constraints on 7 tables |
| 3 | (third) | FK direction inversion: `RAGSparseRetriever.bridge_id`, `RAGDenseRetriever.bridge_id` → `RAGRetriever`; removed `RAGPipeline.retriever_model_id` |
| 4 | (fourth) | `chunk_set` architecture: `RAGChunkSet`, `RAGChunkSetDocument`, `RAGRetrieverChunkSet`; `Chunk.metadata` JSON column; `Chunk.chunk_set_id` FK |

## Migration 1 — Composite Retriever Support

**New tables**:
- `rag_retriever_child` — parent/child composite links with `child_order`

**Schema changes**:
- Expanded `RAGRetriever` to act as canonical identity row for all retriever types
- Added `pipeline_id` FK to `RAGRetriever`

## Migration 2 — DB Uniqueness Constraints

Added `UniqueConstraint` on 7 tables to enable automatic row reuse:

| Table | Constraint Columns |
|-------|-------------------|
| `chunk` | `(document_id, chunk_index, chunking_model_id)` |
| `rag_prompt` | `(class_name, parameters)` |
| `rag_generation_model` | `(class_name, parameters)` |
| `rag_chunking_model` | `(class_name, parameters)` |
| `rag_embedding_model` | `(class_name, parameters)` |
| `rag_sparse_retriever` | `(class_name, parameters, documents_ids, chunking_model_id)` |
| `rag_dense_retriever` | `(class_name, parameters, document_ids, chunking_model_id, embedding_model_id)` |

Replaced useless constraint `(id, document_id)` on `chunk`.

## Migration 3 — FK Direction Inversion

**Removed**:
- `RAGPipeline.retriever_model_id` FK → `RAGRetriever.id`

**Added**:
- `RAGSparseRetriever.bridge_id` FK → `RAGRetriever.id`
- `RAGDenseRetriever.bridge_id` FK → `RAGRetriever.id`
- `RAGRetriever.pipeline_id` FK → `RAGPipeline.id` (retriever references pipeline, not reverse)

**Effect**: Retrievers can exist independently and be referenced by sub-tables. Pipeline → retriever traceability maintained via reverse FK. Composite children reference `rag_retriever.id` symmetrically (both parent and child are retriever rows).

## Migration 4 — Chunk Set Architecture

**New tables**:
- `rag_chunk_set` — canonical identity (signature, parameters)
- `rag_chunk_set_document` — documents in a chunk_set
- `rag_retriever_chunk_set` — retriever ↔ chunk_set link

**Schema changes to `chunk`**:
- Replaced `chunking_model_id` FK with `chunk_set_id` FK → `rag_chunk_set.id`
- Added `metadata` JSON column (nullable) for format-specific region tracking
- Updated unique constraint: `(chunk_set_id, document_id, chunk_index)`

**Impact on sub-retriever tables**:
- `RAGSparseRetriever`: FK columns updated to reference `chunk_set_id` instead of individual doc IDs
- `RAGDenseRetriever`: Same update
- `RAGEmbeddingMatrix`: `chunk_set_id` column replaces previous `chunking_model_id`

## Running Migrations

```bash
# Auto-runs on startup, but manual trigger:
alembic upgrade head

# Create new migration:
alembic revision --autogenerate -m "description"
```
