# Backend Architecture

## Pipeline

`RAGPipeline` (`DashAI/back/models/RAG/RAG_pipeline.py`) is the central orchestrator. It receives:

- `RAGPipelineConfig` — user-defined parameters (chunking, retriever, prompt, LLM configs)
- `RAGModelsFactory` — facade that resolves/looks up model instances
- `PipelineRepository` — persistence layer for processes and outputs
- `DocumentLoader` — loads documents from the document repository

The `generate()` method runs: load documents → get or create chunk set → chunk → retrieve → build prompt → LLM generate.

## Factories (Lookup-or-Create Pattern)

`RAGModelsFactory` (`rag_models_factory.py`) is a facade that delegates to four sub-factories:

- `PromptFactory`
- `ChunkingModelFactory`
- `RetrieverFactory`
- `LLMFactory`

Each sub-factory follows the same pattern:
1. Sort the parameters dictionary by keys.
2. Query the database for an existing record matching `(class_name, sorted_parameters)`.
3. If found, return the existing record. If not, create, persist, and return.

**Critical:** The `sorted_params` dict used for the DB lookup and the DB save must be identical. Retrievers additionally inject infrastructure keys (`env_rag_path`, `chunks`, `persistence`) into the params dict after computing `sorted_params`, so these infra keys do not affect the lookup hash.

## Retriever Architecture (Composite Pattern)

`RetrieverModel` (`DashAI/back/models/RAG/retrievers/`) is the abstract base registered as a DashAI Component.

- **Leaf nodes:** `UnitRetriever` subclasses — `TFIDFRetriever`, `BM25Retriever`, `DenseEmbeddingRetriever`
- **Composite nodes:** `CompositeRetriever` subclasses — `SequentialRetriever`, `ParallelRetriever`, `MMRRerankerRetriever`

All retriever SQL is isolated in `RetrieverRepository` (`retriever_repository.py`).

### Dense Retriever Architecture (Two-Layer Abstraction)

The dense retriever uses two layers:

1. **Embedding layer:** `DenseEmbedding` subclasses (`SentenceTransformerEmbedding`, `BERTEmbedding`, etc.) handle model loading, tokenization, and pooling. These are DashAI Components registered in the registry.
2. **Retriever layer:** A single `DenseEmbeddingRetriever` class accepts any `DenseEmbedding` via a `component_field` schema parameter. The embedding family is selected at configuration time.

This means all dense retrievers share one class; the embedding model is injected as a sub-component.

## Key Conventions

- ML code never imports SQLAlchemy directly. The factory layer returns persistence dataclasses (`ChunkPersistence`, `RetrieverPersistence`, etc.).
- The `metadata` column on the `Chunk` model is renamed to `chunk_metadata` to avoid conflict with SQLAlchemy's `MetaData`.
- Chunk IDs are `None` until flush, at which point a synthetic key `{document_id}_{chunk_position}` is assigned.
- Retrievers inject infra keys (`env_rag_path`, `chunks`, `persistence`) into their params after computing `sorted_params`, ensuring the lookup hash remains clean.

## Key Files Reference

| File | Purpose |
|------|---------|
| `DashAI/back/models/RAG/RAG_pipeline.py` | Pipeline orchestrator |
| `DashAI/back/models/RAG/rag_models_factory.py` | Abstract Factory (Facade) |
| `DashAI/back/models/RAG/retrievers/retriever_repository.py` | All retriever SQL |
| `DashAI/back/models/RAG/chunk_set_utils.py` | Chunk-set caching (SHA-256) |
| `DashAI/back/job/rag_job.py` | Background job runner |
| `DashAI/back/tasks/RAG_task.py` | Task definition (history folding, I/O) |
