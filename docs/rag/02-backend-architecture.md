# Backend Architecture

## Overview

The RAG backend follows a **layered architecture** with clear separation of
concerns:

```
RAGJob (orchestration)
  │
  ├── RAGPipelineConfig     (validated parameter object)
  ├── RAGModelsFactory      (component creation)
  │     ├── PromptFactory
  │     ├── ChunkingModelFactory
  │     ├── RetrieverFactory
  │     └── LLMFactory
  ├── PipelineRepository    (DB persistence)
  └── DocumentLoader        (document hydration)
       │
       ▼
  RAGPipeline (orchestrator)
       │
       ├── single_interaction()  → retrieve chunks
       ├── _build_chunk_references() → ChunkReference[]
       └── generate()            → RAGGenerationOutput
```

## RAGPipeline (`RAG_pipeline.py`)

Central orchestrator that ties together all sub-systems. Receives its
dependencies injected as constructor arguments — it does not construct
factories, repositories, or loaders itself.

### Initialisation Flow

1. **`PipelineRepository.ensure_db_record()`** — Creates or finds the
   `rag_pipeline` DB record for the session.
2. **`DocumentLoader.load()`** — Hydrates `BaseDocument` objects from the
   document table.
3. **`get_or_create_chunk_set()`** — Computes a SHA-256 hash of
   `(document_ids + chunking_config)`. If a chunk set with this hash exists,
   reuses it; otherwise creates a new one.
4. **`RAGModelsFactory`** — Facade that delegates to four sub-factories:
   - `PromptFactory` — Creates or looks up the prompt component.
   - `ChunkingModelFactory` — Creates the chunking model, chunks documents,
     persists chunks to the DB.
   - `RetrieverFactory` — Creates the retriever (sparse/dense/composite),
     computes embeddings if needed, persists.
   - `LLMFactory` — Creates or looks up the text generation model.
5. **`PipelineRepository.update_db_record()`** — Patches the pipeline record
   with the real component IDs.

### Generation Flow

`generate(input_data)`:

1. Extracts the current message from `input_data[-1]` and history from
   `input_data[:-1]`.
2. Calls `single_interaction(query)` → `retriever.retrieve(query)` returns
   top-k `Chunk` objects.
3. Calls `_build_chunk_references(chunks)` → formats chunks into text +
   `Dict[str, ChunkReference]` metadata.
4. Formats the prompt using `prompt_model.format(input, chunks)`.
5. Calls `llm_model.generate()` with the full prompt + history.
6. Returns a typed `RAGGenerationOutput(message, chunks)`.

## RAGPipelineConfig

Dataclass that parses and validates the raw kwargs dict once, providing typed
field access throughout the pipeline. Eliminates magic strings in `__init__`.

- Validates that all required keys exist (`session_id`, `db`,
  `component_registry`, `env_rag_path`, `documents`, plus four `ModelRef`
  entries).
- Validates that each model reference is a `dict` with `component` and `params`
  keys.
- Rejects unknown keys via set subtraction.

## RAGModelsFactory (`rag_models_factory.py`)

Abstract Factory (GoF) with four `create_*` methods, each delegating to a
specialised sub-factory. Shared dependencies (`db`, `registry`, `env_rag_path`)
are injected once into the factory.

### Sub-Factory Pattern (Lookup-or-Create)

All four sub-factories follow the same pattern:

1. Sort the parameters dictionary by keys.
2. Query the database for an existing record matching
   `(class_name, sorted_parameters)`.
3. If found → re-instantiate the model from the stored parameters.
4. If not found → create a new DB record, persist it, instantiate the model.
5. Return a typed `*FactoryResult` dataclass with `db_record_id` and `model`.

**Critical:** The `sorted_params` dict used for DB lookup and save must be
identical. Factory methods that need to add infrastructure keys do so *after*
computing `sorted_params`.

### ChunkingModelFactory

Wraps the full chunking lifecycle:
1. Resolves or creates the DB record.
2. Instantiates the chunking model (injects `documents` kwarg).
3. Runs `model.chunk_documents()` — splits text into chunks.
4. Persists new chunks to the `Chunk` DB table (avoids duplicates via
   `_persist_chunks`).
5. Updates in-memory chunk IDs from the persisted records.

### RetrieverFactory

Handles three retriever categories:

- **Sparse** (TF-IDF, BM25) — Creates or loads from `rag_sparse_retriever`
  table, manages on-disk persistence via `SparsePersistence`.
- **Dense** (`DenseEmbeddingRetriever`) — Creates or loads from
  `rag_dense_retriever` table, manages embedding computation and similarity
  matrix persistence via `DensePersistence`.
- **Composite** (Sequential, Parallel, MMR) — Recursively creates child
  retrievers, manages the bridge record in `rag_retriever` and child links in
  `rag_retriever_child`.

### LLMFactory

Creates or looks up `TextToTextGenerationTaskModel` instances. Persists
records in `rag_generation_model` table.

## Document Loader (`document_loader.py`)

Resolves document IDs to hydrated `BaseDocument` subclass instances.
Supported file types and their document classes:

| Extension | Class       |
|-----------|-------------|
| `.txt`    | `TxtDocument` |
| `.pdf`    | `PDFDocument` |
| `.md`     | `TxtDocument` |
| `.rst`    | `TxtDocument` |
| `.tex`    | `TxtDocument` |
| `.csv`    | `TxtDocument` |

## Retriever Architecture

### Class Hierarchy

```
RetrieverModel (ABC, DashAI Component)
  ├── UnitRetriever (ABC, leaf node)
  │     ├── SparseRetriever (ABC)
  │     │     ├── TFIDFRetriever
  │     │     └── BM25Retriever
  │     └── DenseRetriever (ABC)
  │           └── DenseEmbeddingRetriever
  │                 └── HuggingFaceDenseRetriever
  └── CompositeRetriever (ABC, composite node)
        ├── SequentialRetriever
        ├── ParallelRetriever
        └── MMRRerankerRetriever
```

- **Unit retrievers** are leaf nodes — they perform actual retrieval against
  their index.
- **Composite retrievers** wrap one or more child retrievers and combine their
  results via a strategy (sequential cascade, parallel merge, MMR re-ranking).

### Dense Retriever Two-Layer Design

The dense retriever separates concerns into two layers:

1. **Embedding layer** (`DenseEmbedding` subclasses) — Handle model loading,
   tokenization, pooling, and vector generation. These are DashAI Components
   registered in the component registry. Available: `BERTEmbedding`,
   `DistilBERTEmbedding`, `E5Embedding`, `GemmaEmbedding`,
   `HuggingFaceEmbedding`, `InstructorEmbedding`, `LaBSEmbedding`,
   `OpenAIEmbedding`, `RoBERTaEmbedding`, `SentenceTransformerEmbedding`.
2. **Retriever layer** (shared `DenseEmbeddingRetriever` class) — Accepts any
   `DenseEmbedding` via a `component_field` schema parameter. The embedding
   family is selected at configuration time.

### Retriever Persistence

All retriever SQL is isolated in `RetrieverRepository`
(`retriever_repository.py`). It owns every query, INSERT, and DB-model
construction related to retrievers.

The `rag_retriever` table acts as a **bridge** — every retriever (unit,
composite, dense, sparse) gets one canonical identity record here. Sub-tables
(`rag_sparse_retriever`, `rag_dense_retriever`) hold type-specific details.
Composite child links are stored in `rag_retriever_child`.

## Chunk Set Caching (`chunk_set_utils.py`)

`get_or_create_chunk_set()` computes a deterministic SHA-256 hash of:
- Sorted document IDs
- Sorted chunking configuration (e.g., chunking model component + params)

If a chunk set with this signature exists, it is reused. This avoids
re-chunking the same documents with the same parameters.

**Note:** Uses SELECT-then-INSERT without a lock. Safe for single-user
operation but could create duplicate chunk sets under concurrent requests.

## Job Layer (`rag_job.py`, `generative_job.py`)

- **`GenerativeJob`** is the generic job for text generation. At runtime, it
  detects whether the session uses `RAGTask` and delegates to `RAGJob`.
- **`RAGJob`** builds the `RAGPipeline` with all dependencies and runs
  generate/save/output in a background Huey task. RAGJob duplicates some
  status-update methods from GenerativeJob by design — see
  [known limitations](./05-known-limitations.md#code-duplication) for the
  rationale.

## Task Layer (`RAG_task.py`)

`RAGTask` extends `BaseGenerativeTask` and:
- Prepares input by folding chat history into the message list.
- Processes output by serializing the response and chunk references into
  DB-suitable format.
- Declares `USE_HISTORY = True` to enable history folding in the job layer.

## Typed Return Values

The pipeline uses typed dataclasses instead of raw dicts or lists:

| Dataclass              | Purpose                                      |
|------------------------|----------------------------------------------|
| `RAGPipelineConfig`    | Validated pipeline parameters                |
| `ChunkReference`       | A single retrieved chunk with document info  |
| `RAGGenerationOutput`  | Typed pipeline output (message + chunks)     |
| `*FactoryResult`       | Each factory returns a typed result          |
| `SparsePersistence`    | On-disk reference for sparse retrievers      |
| `DensePersistence`     | Embedding matrix references for dense retrievers |
