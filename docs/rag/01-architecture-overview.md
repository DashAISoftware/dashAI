# 01 — Architecture Overview

## Design Philosophy

The RAG module is built on three principles:

1. **Separation of ML from persistence.** Retriever instances (ML layer) never import SQLAlchemy. They receive `Persistence` dataclasses (paths only) and `Chunk` objects. All DB operations live in `RetrieverRepository` and factory orchestration methods.

2. **Composite pattern for retrievers.** `RetrieverModel` is the Component. `UnitRetriever` (leaf) encapsulates TF-IDF, BM25, or Dense logic. `CompositeRetriever` delegates to children. `SequentialRetriever` supports accumulate/cascade strategies. `ParallelRetriever` supports round_robin/interleave merge.

3. **Factories orchestrate, repositories persist.** `RetrieverModelsFactory` coordinates repository lookups, persistence planning, constructor injection, and composite recursion. It does NOT write SQL — `RetrieverRepository` does.

4. **Two-level abstraction for dense retrievers.** Dense retrievers are split into an **embedding layer** (internal — loads models, implements family-specific pooling/overflow) and a **retriever layer** (registered components — schemas, metadata, frontend exposure). This enables adding new embedding families without rewriting retriever logic.

## Component Hierarchy

```
BaseModel (DashAI core)
 └── RetrieverModel                    Component (abstract)
      ├── UnitRetriever                Leaf (abstract)
      │    ├── SparseRetriever         (abstract)
      │    │    ├── TFIDFRetriever
      │    │    └── BM25Retriever
      │    └── DenseRetriever          (abstract)
      │         ├── FastTextDenseRetriever
      │         └── HuggingFaceDenseRetriever (abstract)
      │              ├── SentenceTransformerDenseRetriever
      │              ├── BERTDenseRetriever
      │              ├── DistilBERTDenseRetriever
      │              ├── RoBERTaDenseRetriever
      │              ├── E5DenseRetriever
      │              ├── GemmaDenseRetriever
      │              ├── InstructorDenseRetriever
      │              └── LaBSEDenseRetriever
      └── CompositeRetriever           Composite (abstract)
           ├── SequentialRetriever
           └── ParallelRetriever
```

### Component responsibilities

| Class | Role | DB identity |
|-------|------|-------------|
| `RetrieverModel` | Declares `retrieve()` and `score_chunks()` interface. Stores `_db_id` for DB row reference. | `rag_retriever` row (via factory) |
| `UnitRetriever` | Extracts common infra kwargs (`env_rag_path`, `chunks`, `persistence`). Forbids composite constructor injection. | `rag_sparse_retriever` or `rag_dense_retriever` sub-row |
| `SparseRetriever` | Base for TF-IDF/BM25. Owns `SparsePersistence` with `model_dir`. | `rag_sparse_retriever` via `bridge_id` |
| `DenseRetriever` | Base for embedding-based. Owns `DensePersistence` with per-document matrix dirs. `init_model()` delegates to `_create_embedding()`. | `rag_dense_retriever` via `bridge_id` |
| `HuggingFaceDenseRetriever` | Abstract bridge between `DenseRetriever` and all HuggingFace-based families. Add `_create_embedding()` abstract method. | Same as DenseRetriever |
| Concrete dense families | Each family owns a `MODELS` dict (model names → languages, max_seq_length). `get_metadata()` returns language summaries. `_create_embedding()` instantiates the family-specific embedding. | Same as DenseRetriever |
| `CompositeRetriever` | Manages child list via `add()`/`remove()`/`get_children()`. | `rag_retriever_child` link table |
| `SequentialRetriever` | Applies children in order. ACCUMULATE: gather until top-k. CASCADE: first retrieves broad, subsequent refine via `score_chunks()`. | Same as Composite |
| `ParallelRetriever` | Runs all children concurrently, merges by ROUND_ROBIN or INTERLEAVE. | Same as Composite |

### Embedding hierarchy (internal, non-registered)

```
DenseEmbedding (BaseModel, abstract)
 └── HuggingFaceEmbedding (abstract)
      ├── OverfloatHandler         (abstract — overflow strategy)
      │    ├── _SentenceTransformerEmbedding
      │    ├── _BERTEmbedding      (reused by BERT, DistilBERT, RoBERTa)
      │    └── _E5Embedding
      ├── _GemmaEmbedding          (SentenceTransformer library)
      └── _InstructorEmbedding     (InstructorEmbedding library)
```

Internal embedding classes are NOT registered as components. They handle loading, tokenization, and family-specific pooling. The families with OverflowHandler support `truncate` and `aggregate` overflow strategies for chunks exceeding the model's max sequence length.

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
│   ├── retriever_models_factory.py    # Factory: lookup → persistence → inject → save
│   ├── retriever_repository.py        # All SQL operations
│   ├── persistence.py                 # SparsePersistence, DensePersistence
│   ├── enums.py                       # RetrievalStrategy, MergeStrategy
│   ├── exceptions.py                  # RetrieverError hierarchy
│   ├── sparse/                        # TFIDFRetriever, BM25Retriever (+ encodings)
│   ├── dense/                         # Dense retriever families
│   │   ├── dense_retriever.py         # Abstract DenseRetriever base
│   │   ├── huggingface_dense_retriever.py  # Abstract HuggingFace bridge
│   │   ├── sentence_transformer_dense_retriever.py
│   │   ├── bert_dense_retriever.py
│   │   ├── distilbert_dense_retriever.py
│   │   ├── roberta_dense_retriever.py
│   │   ├── e5_dense_retriever.py
│   │   ├── gemma_dense_retriever.py
│   │   ├── instructor_dense_retriever.py
│   │   ├── labse_dense_retriever.py
│   │   ├── fasttext_dense_retriever.py
│   │   ├── _hf_language_utils.py      # Language metadata (ISO codes → display labels)
│   │   └── _hf_metadata_utils.py      # build_retriever_metadata()
│   └── composite/                     # SequentialRetriever, ParallelRetriever
│
├── embeddings/                        # Dense/sparse encoding models
│   ├── dense_embedding.py             # Abstract DenseEmbedding base
│   ├── dense/
│   │   ├── huggingface_embedding.py   # Abstract HuggingFaceEmbedding base
│   │   ├── _overflow_handler.py       # OverfloatHandler (truncate/aggregate)
│   │   ├── _sentence_transformer_embedding.py
│   │   ├── _bert_embedding.py
│   │   ├── _e5_embedding.py
│   │   ├── _gemma_embedding.py
│   │   ├── _instructor_embedding.py
│   │   └── fasttext_embedding.py
│   └── sparse/
│
├── chunking_models/                   # CharacterChunkModel, TokenChunkModel
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
┌────────────────────────────────────────┐
│ Embedding layer (internal, no DB refs) │
│                                        │
│ HuggingFaceEmbedding (abstract)        │
│ ├── OverfloatHandler (truncate/agg)    │
│ │   ├── _SentenceTransformerEmbedding  │
│ │   ├── _BERTEmbedding                 │
│ │   └── _E5Embedding                   │
│ ├── _GemmaEmbedding                    │
│ └── _InstructorEmbedding               │
│                                        │
│ → Loads HF models, implements pooling  │
│ → Receives model_max_length from MODELS│
│ → Encapsulates family-specific logic   │
└────────────────────────────────────────┘
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

## Language Metadata

Each dense retriever declares per-model language info in its `MODELS` dict. `_hf_language_utils.py` maps 44 ISO 639-1 codes to 3-letter display labels. `compute_language_summary()` truncates at 3 with overflow. `get_metadata()` returns:

- `language_summary`: Aggregated family string (e.g. `"Eng, Esp, Multi +6"`)
- `model_languages`: Per-model summary strings + labels + counts

The frontend reads this to display language tags in the retriever selector without any hardcoded logic.

## FK Direction (critical design choice)

The FK for pipeline→retriever was **inverted** from the original design:

- **Old**: `RAGPipeline.retriever_model_id` → `RAGRetriever.id` (pipeline owns the FK)
- **New**: `RAGRetriever.pipeline_id` → `RAGPipeline.id` (retriever references its pipeline)

This inversion allows retrievers to exist independently and be referenced by their bridge sub-tables. The bridge pattern:

- `RAGSparseRetriever.bridge_id` → `RAGRetriever.id`
- `RAGDenseRetriever.bridge_id` → `RAGRetriever.id`

Composite children are linked via `rag_retriever_child` (parent_id, child_id, child_order), both referencing `rag_retriever.id`.
