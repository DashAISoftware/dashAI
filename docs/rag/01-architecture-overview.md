# 01 — Architecture Overview

## Design Philosophy

The RAG module is built on three principles:

1. **Separation of ML from persistence.** Retriever instances (ML layer) never import SQLAlchemy. They receive `Persistence` dataclasses (paths only) and `Chunk` objects. All DB operations live in `RetrieverRepository` and factory orchestration methods.

2. **Composite pattern for retrievers.** `RetrieverModel` is the Component. `UnitRetriever` (leaf) encapsulates TF-IDF, BM25, or Dense logic. `CompositeRetriever` delegates to children. `SequentialRetriever` supports accumulate/cascade strategies. `ParallelRetriever` supports round_robin/interleave merge.

3. **Factories orchestrate, repositories persist.** `RetrieverModelsFactory` coordinates repository lookups, persistence planning, constructor injection, and composite recursion. It does NOT write SQL — `RetrieverRepository` does.

## Component Hierarchy

```
BaseModel (DashAI core)
 └── RetrieverModel              Component (abstract)
      ├── UnitRetriever          Leaf (abstract)
      │    ├── SparseRetriever   (abstract)
      │    │    ├── TFIDFRetriever
      │    │    └── BM25Retriever
      │    └── DenseRetriever
      └── CompositeRetriever     Composite (abstract)
           ├── SequentialRetriever
           └── ParallelRetriever
```

### Component responsibilities

| Class | Role | DB identity |
|-------|------|-------------|
| `RetrieverModel` | Declares `retrieve()` and `score_chunks()` interface. Stores `_db_id` for DB row reference. | `rag_retriever` row (via factory) |
| `UnitRetriever` | Extracts common infra kwargs (`env_rag_path`, `chunks`, `persistence`). Forbids composite constructor injection. | `rag_sparse_retriever` or `rag_dense_retriever` sub-row |
| `SparseRetriever` | Base for TF-IDF/BM25. Owns `SparsePersistence` with `model_dir`. | `rag_sparse_retriever` via `bridge_id` |
| `DenseRetriever` | Wraps a `DenseEmbedding` model. Owns `DensePersistence` with per-document matrix dirs. | `rag_dense_retriever` via `bridge_id` |
| `CompositeRetriever` | Manages child list via `add()`/`remove()`/`get_children()`. | `rag_retriever_child` link table |
| `SequentialRetriever` | Applies children in order. ACCUMULATE: gather until top-k. CASCADE: first retrieves broad, subsequent refine via `score_chunks()`. | Same as Composite |
| `ParallelRetriever` | Runs all children concurrently, merges by ROUND_ROBIN or INTERLEAVE. | Same as Composite |

## Package Layout

```
DashAI/back/models/RAG/
├── RAG_pipeline.py                    # Top-level orchestrator (extends BaseGenerativeModel)
├── chunk_set_utils.py                 # Deterministic chunk_set identity via SHA-256
├── document_loader.py                 # DB-row → in-memory BaseDocument hydration
├── pipeline_repository.py             # RAGPipeline row ensure/update
├── llm_factory.py                     # ComponentRegistry → LLM instance
├── models_factory.py                  # Abstract base for ChunkingModelsFactory, RetrieverModelsFactory
├── persistence.py                     # SparsePersistence, DensePersistence dataclasses
├── extra_args_enum.py                 # String constants for kwargs dictionary keys
├── exceptions.py                      # RAGWorkflowError
│
├── retrievers/                        # Retriever subsystem
│   ├── retriever_model.py             # Base (Component pattern)
│   ├── unit_retriever.py              # Leaf retriever base
│   ├── retriever_models_factory.py    # Orchestration (lookup → persistence → inject → save)
│   ├── retriever_repository.py        # All SQL operations
│   ├── persistence.py                 # SparsePersistence, DensePersistence
│   ├── enums.py                       # RetrievalStrategy, MergeStrategy
│   ├── exceptions.py                  # RetrieverError hierarchy
│   ├── sparse/                        # TFIDFRetriever, BM25Retriever (+ encodings)
│   ├── dense/                         # DenseRetriever
│   └── composite/                     # SequentialRetriever, ParallelRetriever
│
├── chunking_models/                   # CharacterChunkModel, TokenChunkModel
├── embeddings/                        # Dense/sparse encoding models
├── prompts/                           # Prompt templates + factory
└── documents/                         # BaseDocument, PDFDocument, Chunk
```

## Separation of Concerns

```
┌──────────────────────────────────────────────────┐
│ RAGPipeline (orchestration only)                 │
│                                                  │
│ PipelineRepository  DocumentLoader  PromptFactory│
│ ChunkingModelsFactory  RetrieverModelsFactory    │
│ LLMFactory                                       │
│                                                  │
│ → No direct self.db.query(), no DB model imports │
└──────────────────────────────────────────────────┘
         │                    │
         ▼                    ▼
┌─────────────────┐  ┌────────────────────────────┐
│ RetrieverModels │  │ RetrieverRepository         │
│ Factory         │  │ (pure SQL)                  │
│                 │  │                             │
│ _prepare_*()    │  │ find_sparse/dense/composite │
│ _save_*()       │  │ save_sparse/dense/composite │
│ _load_*()       │  │ find_or_create_embedding    │
│                 │  │ find/save_embedding_matrix  │
│ → Orchestrates  │  │ create_bridge               │
│   repo calls    │  │ find_bridge_for_sub_table   │
└─────────────────┘  └────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ Persistence (dataclasses)   │
│                             │
│ SparsePersistence(model_dir)│
│ DensePersistence(           │
│   matrix_dirs,              │
│   embedding_model_id        │
│ )                           │
│                             │
│ → Paths only, zero DB refs │
└─────────────────────────────┘
```

## FK Direction (critical design choice)

The FK for pipeline→retriever was **inverted** from the original design:

- **Old**: `RAGPipeline.retriever_model_id` → `RAGRetriever.id` (pipeline owns the FK)
- **New**: `RAGRetriever.pipeline_id` → `RAGPipeline.id` (retriever references its pipeline)

This inversion allows retrievers to exist independently and be referenced by their bridge sub-tables. The bridge pattern:

- `RAGSparseRetriever.bridge_id` → `RAGRetriever.id`
- `RAGDenseRetriever.bridge_id` → `RAGRetriever.id`

Composite children are linked via `rag_retriever_child` (parent_id, child_id, child_order), both referencing `rag_retriever.id`.
