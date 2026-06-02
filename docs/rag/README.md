# DashAI RAG — Documentation Index

This directory contains the complete technical documentation for the Retrieval-Augmented Generation (RAG) module of DashAI. It consolidates knowledge from multiple development sessions and the current codebase state.

All RAG-related documentation has been consolidated here from scattered locations (repository root and frontend directory). See each file's header for its origin source.

## Index

| File | Scope |
|------|-------|
| [`01-architecture-overview.md`](./01-architecture-overview.md) | Design philosophy, component hierarchy, package layout, separation of concerns |
| [`02-data-models.md`](./02-data-models.md) | All 16 DB models, FK chains, uniqueness constraints, chunk_set architecture |
| [`03-retrievers.md`](./03-retrievers.md) | Composite pattern (Leaf/Composite/Sequential/Parallel), retriever class hierarchy, `score_chunks` cascade re-ranking |
| [`04-pipeline-orchestration.md`](./04-pipeline-orchestration.md) | `RAGPipeline`, `RAGModelsFactory`, sub-factories, DI pattern |
| [`05-coding-standards.md`](./05-coding-standards.md) | Zero-silent-defaults, no-magic-strings, typed generics, MultilingualString, ML-vs-DB separation |
| [`06-execution-flow.md`](./06-execution-flow.md) | End-to-end query lifecycle: API → Huey worker → retrieval → generation → response |
| [`07-frontend.md`](./07-frontend.md) | Simplified view, dual-card system, component dependency graph, routes |
| [`08-migrations.md`](./08-migrations.md) | Alembic migration history (composite support, uniqueness, FK inversion, chunk_set) |
| [`09-pending-tasks.md`](./09-pending-tasks.md) | Known issues, cleanup TODOs, architectural debt, next steps |
| [`10-frontend-changes.md`](./10-frontend-changes.md) | Frontend changes needed: prompt_id → prompt ModelRef |
| [`11-retriever-ui-design.md`](./11-retriever-ui-design.md) | Retriever configuration UI: data model, data flow, form save mechanism, auto-repair, backend-frontend contract, bug history |
| [`12-testing-guide.md`](./12-testing-guide.md) | Simplified RAG interface testing guide (Spanish): usage flow, data flow, testing checklist |
| [`13-technical-guide.md`](./13-technical-guide.md) | Comprehensive RAG technical guide: backend architecture, frontend architecture, execution flow, session lifecycle, migration summary |
| [`14-frontend-architecture.md`](./14-frontend-architecture.md) | Frontend file tree, dependency graph, shared utilities, component responsibilities, architectural decisions |
| [`15-notes.md`](./15-notes.md) | Design notes about document version tracking (Spanish) |

## Quick Reference

### Key file map (backend)

```
DashAI/back/
├── dependencies/database/models.py          ← All 16 DB model classes
├── models/RAG/
│   ├── RAG_pipeline.py                       ← Orchestrator (286 lines)
│   ├── chunk_set_utils.py                    ← get_or_create_chunk_set()
│   ├── document_loader.py                    ← DocumentLoader (DB → BaseDocument)
│   ├── pipeline_repository.py                ← RAGPipeline row CRUD
│   ├── llm_factory.py                        ← LLM instantiation from registry
│   ├── models_factory.py                     ← Abstract base factory
│   ├── extra_args_enum.py                    ← CHUNKS, COMPONENT_REGISTRY, ENV_RAG_PATH
│   ├── persistence.py                        ← SparsePersistence, DensePersistence
│   ├── retrievers/
│   │   ├── retriever_model.py                ← Component base (RetrieverModel)
│   │   ├── unit_retriever.py                 ← Leaf node base (UnitRetriever)
│   │   ├── retriever_models_factory.py       ← Orchestration factory (333 lines)
│   │   ├── retriever_repository.py           ← All SQL queries (313 lines)
│   │   ├── persistence.py                    ← SparsePersistence, DensePersistence
│   │   ├── enums.py                          ← RetrievalStrategy, MergeStrategy
│   │   ├── exceptions.py                     ← Typed error hierarchy
│   │   ├── sparse/                           ← TFIDFRetriever, BM25Retriever
│   │   ├── dense/                            ← DenseRetriever
│   │   └── composite/                        ← SequentialRetriever, ParallelRetriever
│   ├── chunking_models/                      ← CharacterChunkModel, TokenChunkModel
│   ├── embeddings/                           ← TFIDF/BF25 encodings, DenseEmbedding
│   ├── prompts/                              ← Prompt templates + factory
│   └── documents/                            ← BaseDocument, PDFDocument, Chunk
└── alembic/versions/                         ← 4 RAG migrations
```

### Key file map (frontend)

```
DashAI/front/src/
├── pages/generative/simplified-RAG/          ← SimplifiedView (20+ files)
├── components/generative/RAG/                ← Side panels, cards, shared UI
├── api/rag.ts                                ← All RAG API calls
└── utils/urlUtils.js                         ← normalizeUrl() for document preview
```
