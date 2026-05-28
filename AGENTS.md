# AGENTS.md

This file provides guidance to AI coding agents when working with code in this repository.

## What is DashAI

DashAI is a desktop/web graphical toolbox for training, evaluating, and deploying ML models. FastAPI backend + React frontend, optionally wrapped in PyWebView for a native desktop window. Python >= 3.10.

## Commands

### Backend

```bash
pip install -e . -r requirements-dev.txt
pre-commit install

# Run dev server
python -m DashAI --no-browser --logging-level DEBUG

# Lint / format (must pass both before committing)
ruff check --fix
ruff format

# Run all tests (in-memory SQLite — no setup needed)
pytest tests/

# Run a single test
pytest tests/back/api/test_components_api.py -v
pytest tests/back/api/test_components_api.py::test_function_name -v

# Database migrations (auto-runs on startup)
alembic upgrade head
```

### Frontend

```bash
cd DashAI/front

yarn install        # requires Node LTS + Yarn 3.5.0 (enforced by packageManager)
yarn start          # dev server on http://localhost:3000 (eslint disabled)
yarn build          # eslint disabled
yarn test           # eslint disabled
yarn test FileName.test.tsx
yarn lint           # runs eslint explicitly (uses eslint.config.js)
```

**Important:** `start`, `build`, and `test` scripts all set `DISABLE_ESLINT_PLUGIN=true`. ESLint only runs via the dedicated `yarn lint` command. Prettier is configured in `DashAI/front/.prettierrc` and runs via pre-commit.

## Architecture

```
Browser / PyWebView
  → React (port 3000 dev / port 8000 prod)
  → FastAPI (/api/v1/...)
  → Service layer → SQLite (SQLAlchemy + Alembic)
  → Huey job queue (async: training, conversion, exploration)
```

The frontend polls `/api/v1/jobs/{job_id}` for long-running task status.

## Key files

| Path | Purpose |
|------|---------|
| `DashAI/__main__.py` | CLI entry point (typer). Starts uvicorn + Huey consumer subprocess |
| `DashAI/back/app.py` | FastAPI `create_app` factory |
| `DashAI/back/container.py` | DI container (`kink`) — config, DB engine, ComponentRegistry, job queue |
| `DashAI/back/initial_components.py` | **Registers all components on startup.** Add new ML components here in `get_initial_components()` |
| `DashAI/back/dependencies/config_builder.py` | Builds config dict (paths, logging, calls `get_initial_components()`) |
| `DashAI/back/dependencies/registry/component_registry.py` | `ComponentRegistry` — resolves components by name string |
| `DashAI/back/api/api_v1/endpoints/` | REST endpoints — each file is a FastAPI router |
| `DashAI/back/api/api_v1/api.py` | Mounts all endpoint routers on `api_router_v1` |
| `DashAI/back/core/schema_fields/` | Type system driving dynamic frontend forms |
| `DashAI/back/pipeline/` | DAG pipeline nodes |
| `DashAI/back/plugins/` | Plugin system (PyPI packages with `dashai.plugins` entry point) |
| `DashAI/front/src/components/configurableObject/` | Auto-generates forms from backend component schemas |

## Key patterns

**ComponentRegistry** — all ML components (models, metrics, converters, dataloaders, explorers, explainers, tasks, optimizers, jobs, pipeline nodes) are registered at startup and resolved by name string. To add a new component: subclass the relevant base, define its schema, and add it to `get_initial_components()` in `DashAI/back/initial_components.py`.

**Schema / type system** — every component declares parameters using `BaseSchema` + field classes (`IntField`, `FloatField`, `ComponentField`, `UnionType`, etc.) with `MultilingualString` labels. The frontend uses these schemas to auto-generate configuration forms.

**Dependency injection (`kink`)** — singletons (config, DB engine, ComponentRegistry, job queue) live in the `di` container. Use `@inject` to receive them. Config is accessed as `di["config"]` and includes `INITIAL_COMPONENTS`.

**Huey job queue** — in dev mode the Huey consumer runs as a subprocess spawned from `__main__.py`; in PyInstaller bundles it runs as a daemon thread due to limitations with frozen executables.

## RAG Module Architecture

The RAG (Retrieval-Augmented Generation) module is a 4-stage pipeline: Document Loading → Chunking → Retrieval → Generation. It lives under `DashAI/back/models/RAG/`.

### Key RAG files

| Path | Purpose |
|------|---------|
| `DashAI/back/models/RAG/RAG_pipeline.py` | Pipeline orchestrator. Receives dependencies injected via `RAGPipelineConfig` + `RAGModelsFactory` + `PipelineRepository` + `DocumentLoader` |
| `DashAI/back/models/RAG/rag_models_factory.py` | Abstract Factory (GoF). Creates prompts, chunking models, retrievers, and LLMs via sub-factories |
| `DashAI/back/models/RAG/prompts/prompt_factory.py` | Creates prompt instances with DB lookup-or-create semantics |
| `DashAI/back/models/RAG/chunking_models/chunking_model_factory.py` | Creates chunking models, persists chunks to DB |
| `DashAI/back/models/RAG/retrievers/retriever_factory.py` | Creates retrievers with full persistence lifecycle (sparse/dense/composite) |
| `DashAI/back/models/RAG/retrievers/retriever_repository.py` | All DB operations for retriever records (bridge, sparse, dense, composite, embeddings) |
| `DashAI/back/models/RAG/llm_factory.py` | Creates LLM instances with DB lookup-or-create |
| `DashAI/back/models/RAG/pipeline_repository.py` | Manages the `rag_pipeline` DB record |
| `DashAI/back/models/RAG/document_loader.py` | Loads Document rows from DB, hydrates `BaseDocument` instances (supports txt, pdf, md, rst, tex, csv) |
| `DashAI/back/models/RAG/chunk_set_utils.py` | Chunk-set caching via SHA-256 signature. Same docs + same config = same chunk set (avoid re-chunking) |
| `DashAI/back/job/rag_job.py` | **RAGJob** — background job that constructs and runs the full RAG pipeline |
| `DashAI/back/job/generative_job.py` | **GenerativeJob** — generic generative job. Auto-dispatches to RAGJob when the session task is `RAGTask` |
| `DashAI/back/tasks/RAG_task.py` | Task definition for RAG. Handles history folding, input/output processing |

### RAG component hierarchy

```
RAGPipeline (BaseGenerativeModel)
├── receives: RAGPipelineConfig + RAGModelsFactory + PipelineRepository + DocumentLoader
├── orchestrates: load docs → chunk-set → chunking → retrieval → prompt → LLM
└── owns:
    ├── BaseChunkingModel (CharacterChunkModel | TokenChunkModel)
    ├── RetrieverModel
    │   ├── UnitRetriever (Leaf)
    │   │   ├── SparseRetriever → TFIDFRetriever | BM25Retriever
    │   │   └── DenseRetriever (requires DenseEmbedding)
    │   └── CompositeRetriever (Composite, GoF)
    │       ├── SequentialRetriever (ACCUMULATE | CASCADE)
    │       └── ParallelRetriever (ROUND_ROBIN | INTERLEAVE)
    ├── Prompt (GenerationPrompt | AugmentationPrompt)
    └── TextToTextGenerationTaskModel (LLM)
```

### RAG flow (backend)

1. **Session creation** (`POST /api/v1/generative_session/`): validates `RAGPipeline.SCHEMA` for RAG tasks, stores session with parameters
2. **Process creation** (`POST /api/v1/generative_process/`): creates `GenerativeProcess`, stores input text
3. **Job enqueue** (`POST /api/v1/job/` with `job_type="GenerativeJob"`): `GenerativeJob.run()` detects RAG sessions and delegates to `RAGJob`
4. **RAGJob.run()**: constructs `RAGPipelineConfig` → `RAGModelsFactory` → `PipelineRepository` → `DocumentLoader` → `RAGPipeline`. Calls `pipeline.generate()` → processes output → saves to DB
5. **Frontend polls** `/api/v1/jobs/{job_id}` for status, then reads process output

### Factory pattern (lookup-or-create)

All 4 sub-factories (`PromptFactory`, `ChunkingModelFactory`, `RetrieverFactory`, `LLMFactory`) follow the same pattern:
1. Check DB for existing record matching `(class_name, sorted_parameters)`
2. If found → return existing instance
3. If not → create DB record, instantiate component, return both

`RAGModelsFactory` is the Facade that delegates `create_prompt()`, `create_chunking_model()`, `create_retriever()`, `create_llm()` to the respective sub-factories.

### Retriever persistence

Every retriever gets a **bridge record** in `rag_retriever` (canonical identity for both unit and composite retrievers). Sub-table detail records (`RAGDenseRetriever`, `RAGSparseRetriever`) link back via `bridge_id`. Composite retrievers store ordered children via `rag_retriever_child`.

`RetrieverRepository` encapsulates ALL SQL for retrievers — factories never touch SQLAlchemy directly.

### Known constraints (documented in code as `# NOTE:`)

- Chunk similarity matrices loaded entirely in RAM (fine for tens to low hundreds of documents)
- No streaming output from LLMs — user waits for full response
- `pairwise_distances` O(n×dim) per query, no FAISS/HNSW indexing
- Embedding matrices loaded via `np.load()` into RAM
- `get_or_create_chunk_set` does SELECT-then-INSERT without lock (safe for single-user)
- DB session held open during entire job lifecycle including LLM inference (risk of connection timeout)

### What was removed during refactor

- `text_splitter.py`, `text_preprocessor.py` — legacy, never used
- `chunk_embedding.py` — dead `ChunkEmbedding` class
- `embeddings/sparse/bm25_encoding.py`, `tfidf_encoding.py` — old interface incompatible with factory pattern
- `embeddings/trainable_encoding.py` — incomplete intermediate hierarchy, unused
- RAG-specific code in `GenerativeJob` — now in `RAGJob`

## Testing

- Backend tests use in-memory SQLite — no setup needed.
- Key fixtures in `tests/back/conftest.py`: `test_path`, `test_datasets_path`, `test_job_queue`.
- Job queue tests: `test_job_queue.set_test_mode(immediate=True)` runs tasks synchronously.
- API tests use FastAPI `TestClient` defined in `tests/back/api/conftest.py` (module-scoped).
- Frontend test command passes `--passWithNoTests` in CI.

## Adding new things

**New ML model or converter:** subclass `BaseModel` / `BaseConverter`, define schema, register in `DashAI/back/initial_components.py::get_initial_components()`.

**New API endpoint:** add file in `DashAI/back/api/api_v1/endpoints/`, include its router in `DashAI/back/api/api_v1/api.py`.

**New async job:** subclass `BaseJob`, dispatch via `job_queue.enqueue(...)`, track status through jobs API.

## Data at runtime

Default `~/.DashAI/` (overridable via `DASHAI_LOCAL_PATH` env var):
`datasets/`, `runs/`, `explanations/`, `notebooks/`, `images/`, `documents/`, `rag/`, `sqlite.db`

## CI

Only a `publish.yml` workflow exists (on push to `production` branch). It builds the frontend, publishes to PyPI, and builds Windows/macOS installers. No CI test workflow is defined.
