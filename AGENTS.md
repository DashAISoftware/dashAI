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
| `DashAI/front/src/pages/generative/SessionRouter.jsx` | Routes `/app/generative/sessions/:id` to RAG or non-RAG view based on session `task_name` |
| `DashAI/front/src/pages/generative/simplified-RAG/` | RAG session setup wizard (SimplifiedSessionSetup) + collapsible section components per pipeline stage |
| `DashAI/front/src/pages/generative/simplified-RAG/sections/` | Per-stage components: ChunkingSection, RetrieverSection, GeneratorSection, PromptSection |
| `DashAI/front/src/pages/generative/simplified-RAG/advanced/` | Advanced configuration modals: CompositeRetrieverBuilder, ChunkingConfigurationStep, RetrieverConfigurationStep, etc. |
| `DashAI/front/src/pages/generative/simplified-RAG/components/` | Reusable bodies: GeneratorBody, PromptBody, PresetCard, AdvancedConfigCard |

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
    ├── BaseChunkingModel (CharacterChunkModel | TokenChunkModel | RecursiveCharacterChunkModel)
    ├── RetrieverModel
    │   ├── UnitRetriever (Leaf)
    │   │   ├── SparseRetriever → TFIDFRetriever | BM25Retriever
    │   │   └── DenseRetriever (abstract)
    │   │        └── DenseEmbeddingRetriever (UNIFIED — accepts any DenseEmbedding)
    │   │             ├── SentenceTransformerEmbedding → 27 models (ST + Qwen3 + Harrier)
    │   │             ├── BERTEmbedding
    │   │             ├── DistilBERTEmbedding
    │   │             ├── RoBERTaEmbedding
    │   │             ├── E5Embedding
    │   │             ├── GemmaEmbedding
    │   │             ├── InstructorEmbedding
    │   │             ├── LaBSEmbedding
    │   │             ├── FastTextEmbedding
    │   │             └── OpenAIEmbedding (API)
    │   └── CompositeRetriever (Composite, GoF)
    │       ├── SequentialRetriever
    │       ├── ParallelRetriever (ROUND_ROBIN | INTERLEAVE)
    │       └── MMRRerankerRetriever
    ├── Prompt (GenerationPrompt | AugmentationPrompt)
    └── TextToTextGenerationTaskModel (LLM)
```

### Dense retriever architecture (unified)

Dense retrievers use a **two-layer abstraction** with a **single unified retriever class**:

1. **Embedding layer** (`embeddings/dense/`): Registered `DenseEmbedding` Component classes (`SentenceTransformerEmbedding`, `BERTEmbedding`, `OpenAIEmbedding`, etc.) that handle model loading, tokenization, pooling, and overflow strategies. Each embedding class declares its own `SCHEMA`, `MODELS` dict, and `DISPLAY_NAME`.

2. **Retriever layer** (`retrievers/dense/`): **One class:** `DenseEmbeddingRetriever` — accepts any `DenseEmbedding` via `component_field(parent="DenseEmbedding")` in its schema. The `RetrieverFactory` resolves the `component_field` into an actual embedding instance via `fill_objects()`, then calls `embedding.load()` and `_init_embedding()`.

The old per-family dense retriever classes (`SentenceTransformerDenseRetriever`, `BERTDenseRetriever`, etc. — ~10 classes) were deleted. They added unnecessary indirection: the embedding family was tied to the retriever class, forcing one retriever class per embedding type.

### Pooling strategies

`SentenceTransformerEmbedding` supports two pooling strategies, selected automatically per model via the `ST_MODELS` metadata dict:

- **`"mean"`** — traditional mean pooling (used by all SentenceTransformer and Qwen3 models)
- **`"last_token"`** — last-token pooling for decoder-only architectures (used by Harrier OSS v1)

The strategy is not exposed in the schema; it is set per-model in `ST_MODELS[model_name]["pooling"]` and passed to `_SentenceTransformerEmbedding.__init__`.

### Default embedding models

The SentenceTransformerEmbedding family includes 30 models across 3 sub-families:

| Sub-family | Models | Default |
|-----------|--------|---------|
| **Harrier OSS v1** (Microsoft) | `270m`, `0.6b`, `27b` | ⭐ `microsoft/harrier-oss-v1-0.6b` |
| **Qwen3 Embedding** (Alibaba) | `0.6B`, `4B`, `8B` | — |
| **SentenceTransformers** | 22 standard models | — |

All models support 32K+ max sequence length. Harrier and Qwen3 are multilingual; SentenceTransformers models have per-model language metadata.

### How to add a new embedding family

1. Subclass `DenseEmbedding` with family-specific `SCHEMA`, `MODELS` dict, and `DISPLAY_NAME`
2. Implement `__init__`, `load()`, `encode()`, `batch_encode()`
3. Register in `initial_components.py` under `DenseEmbedding`

Internal helper classes (prefixed with `_`, e.g. `_SentenceTransformerEmbedding`, `_BERTEmbedding`) are NOT registered as components — they are implementation details of the public embedding component.

### DenseEmbeddingRetriever.init_model() — must call embedding.load()

**Critical:** `DenseEmbeddingRetriever.init_model()` must call `self._embedding_instance.load()` **before** `_init_embedding()`. The embedding instance is created by `fill_objects()` during factory construction but its heavy resources (tokenizer, model weights) are only acquired on explicit `load()`. Missing this call causes `TypeError: 'NoneType' object is not callable` when `batch_encode` tries to use the uninitialized tokenizer.

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
- Old concrete `HuggingFaceDenseRetriever` (single class with flat `HF_MODELS` list) — split into 8 families
- Old `HuggingFaceEmbedding` (single class with 28-model enum) — split into abstract base + 6 internal subclasses
- **Old per-family dense retrievers:** `SentenceTransformerDenseRetriever`, `BERTDenseRetriever`, `DistilBERTDenseRetriever`, `E5DenseRetriever`, `FastTextDenseRetriever`, `GemmaDenseRetriever`, `InstructorDenseRetriever`, `LaBSEDenseRetriever`, `OpenAIDenseRetriever`, `RoBERTaDenseRetriever` — all replaced by the unified `DenseEmbeddingRetriever` + separate `DenseEmbedding` components

### Query transformation and augmentation (pending development)

- `DefaultAugmentationPrompt` is commented out in `initial_components.py:523` — this will be enabled when query expansion/transformation is implemented.
- The augmentation prompt pipeline step (pre-retrieval query expansion) is not yet integrated into the RAG pipeline. The components exist (`AugmentationPrompt`, `CustomAugmentationPrompt`) but are not wired into `RAGPipeline.generate()`.
- Future work: integrate query transformation (paraphrasing, expansion) before the retrieval step, and expose augmentation prompts in the frontend wizard.

## RAG Design Decisions & Gotchas

This section captures every non-obvious design decision and recurring pitfall encountered during the RAG module refactor. **Read this before touching any RAG code.**

### Critical: Parameter format mismatch in factory lookup-or-create

**Problem:** `RetrieverFactory._create_unit()` computed `sorted_params` from raw frontend params (`{component, params}` format for nested ComponentFields), then passed them to `_load_unit_from_db()` for the DB lookup. However, `_save_sparse()` / `_save_dense()` stored `model.params` — which is the post-`validate_and_transform` / `fill_objects` format (deeply nested with `{properties: {params: {comp: ...}}}` structure).

Result: the DB lookup (raw format) never found records saved in post-transform format → `IntegrityError: UNIQUE constraint failed` on the second message in the same session.

**Fix:** Both `_save_sparse()` and `_save_dense()` receive the raw `sorted_params` (computed before `_inject_infra()` and `model_class(**params)`) and store that raw format in the DB. Lookup and save now use the same parameter representation.

**Rule:** In any factory with lookup-or-create semantics, the parameters used for DB lookup and DB save **must be the exact same dict** (same keys, same structure, same sort order). Never save `model.params` (post-transform) while looking up with raw params.

### Prompt type system

- `RAGGenerationPrompt` is the base class for all RAG generation prompts. Custom user prompts inherit directly from it.
- `DefaultRAGGenerationPrompt` and `DefaultQnARAGGenerationPrompt` are built-in defaults with **multilingual templates** (`en`, `es`, `pt`). They are registered in `get_initial_components()`.
- Default prompts include a `Language` schema parameter; user-created custom prompts do NOT have `Language` — the frontend autocomplete reads from the component registry and the DB, deduplicating by `component` name.
- Prompt is sent from frontend as `{component: "RAGGenerationPrompt", params: {...}}` (unified `{component, params}` format). Backend resolves `component` string via `ComponentRegistry`, validates `params` against its schema. No `prompt_id` integer field anywhere — the old `prompt_id` column was removed from `GenerativeSession`.

### ComponentField is resolved by ComponentRegistry, not by recursive inheritance

The `getChildComponents("RetrieverModel", recursive=false)` call in the frontend returns **only classes that inherit directly from `RetrieverModel`** — none of which are concrete retrievers. All concrete retrievers inherit via intermediate abstract classes (`SparseRetriever`, `DenseRetriever`, `CompositeRetriever`). Always use `recursive=true` when querying the component tree for concrete subclasses.

### Chunk IDs are None until SQLAlchemy flush

When building chunk references in `_build_chunk_references()`, `chunk.id` is `None` because SQLAlchemy doesn't assign IDs until the session is flushed. The fix uses a **synthetic key** `f"{document_id}_{chunk_position}"` as the chunk reference sent to the LLM, then maps it back to the database row after flush.

### `metadata` column name conflicts with SQLAlchemy `Base.metadata`

`Chunk` model had a column named `metadata` which shadows SQLAlchemy's `Base.metadata` class attribute, breaking introspection. The attribute was renamed to `chunk_metadata` while keeping the DB column name as `"metadata"` via `Column("metadata", ...)`. **Never name an ORM column `metadata`.**

### Never `kwargs.pop()` a required parameter before `super().__init__()`

Several retriever subclasses used `kwargs.pop("persistence")` — but `persistence` is a **required** parameter of the parent `_Dense`/`_Sparse` constructors. Popping it caused `TypeError: __init__() missing required argument`. Required parameters must use `kwargs["persistence"]` or be passed explicitly.

### Retrievers inject infra keys into their params dict

`RetrieverFactory._inject_infra()` adds `env_rag_path`, `chunks`, and `persistence` into the params dict **before** instantiating the model. These are runtime dependencies, not part of the schema — they must be excluded from `sorted_params` (the lookup/save key) by computing `sorted_params` **before** calling `_inject_infra()`.

### Validation of RAG session params is opt-in, not default

`GenerativeSession.create()` does NOT validate that session `parameters` conform to `RAGPipeline.SCHEMA` for all tasks — only when the session's task is `RAGTask`. Non-RAG sessions pass through without schema validation. Adding generic schema validation for all tasks would break existing generative sessions.

### Link Table pattern: prefer `Table()` over ORM models for association tables

Composite retriever children are tracked via `rag_retriever_child` — a `Table()` (not an ORM model class). This avoids the pitfalls of instrumented ORM instances for pure many-to-many links. The `RetrieverRepository` manages these directly via core SQLAlchemy operations.

### `RAGTask.process_output` serializes chunks as JSON

Chunk source references sent to the LLM are Python objects; `RAGTask.process_output()` calls `json.dumps(chunks, ensure_ascii=False, default=str)` to serialize them before storing in the process `output` column. Without this, `str(chunks)` produces unparseable Python repr strings.

### Template design for LLM responses

RAG generation prompts include explicit instructions:
- Use only the provided document excerpts (never hallucinate)
- Cite sources by document name, page, and section when available
- Answer "I don't know" if the information is not in the retrieved chunks

Language-specific templates exist in `DEFAULT_RAG_GENERATION_TEMPLATE` and `DEFAULT_QNA_RAG_GENERATION_TEMPLATE` (en/es/pt). Adding a new language requires updating both default prompt files.

### DB and RAG cache cleanup

After schema changes to RAG models (renamed columns, removed tables), you must:
1. Delete `sqlite.db` to force full schema rebuild (Alembic migrations cover only production scenarios)
2. Delete `~/.DashAI/rag/` directory to clear stale embeddings, indices, and sparse retriever files
The dev server automatically rebuilds the DB on startup with the current ORM models.

### SentenceTransformer embedding model metadata

Each model in `ST_MODELS` requires three metadata keys:
1. `languages`: list of ISO 639-1 codes or `["multi"]`
2. `max_seq_length`: integer, injected into the tokenizer
3. `pooling`: `"mean"` (encoder models) or `"last_token"` (decoder-only models like Harrier)

`model_max_length` is never in the schema — it's read from `ST_MODELS[model_name]` and injected into the embedding. `batch_size` is intentionally absent (was a no-op in retrieval).

### RetrieverSection: 3-preset card architecture

The retriever section shows **3 preset cards** instead of 4 groups:

| Card | Retriever class | Embedding | Top-K split |
|------|----------------|-----------|-------------|
| **Keyword** | `BM25Retriever` | — | `top_k` |
| **Semantic** | `DenseEmbeddingRetriever` | Harrier OSS v1 0.6B (default) | `top_k` |
| **Hybrid** | `ParallelRetriever` | BM25 + Harrier 0.6B | `ceil(k/2)` BM25, `floor(k/2)` Dense |

`isAdvanced` detection compares the current model (minus `top_k`) against the 3 preset models built from resolved defaults. If none match, the configuration is "advanced" and shows an `AdvancedConfigCard` instead of a highlighted preset card.

The top-level retriever selector in `RetrieverConfigurationStep` groups options by family:
- **Keyword:** BM25, TFIDF
- **Dense:** embedding families (SentenceTransformer, BERT, OpenAI, FastText, etc.) — selecting one builds a `DenseEmbeddingRetriever` with that embedding pre-filled
- **Composite:** Parallel, Sequential, MMRReranker

All dense options use `DenseEmbeddingRetriever` as the retriever class; the `component_field(parent="DenseEmbedding")` in its schema handles the embedding selection via `FormSchema`.

## Frontend RAG fixes

This section documents all fixes and improvements applied to the RAG frontend.

### Session routing: unified `/app/generative/sessions/:id`

**Before:** Non-RAG sessions navigated to `/app/generative/sessions/:id` (handled by `GenerativeContent`), while RAG sessions stayed at `/app/generative/rag` and passed session IDs via `location.state`.

**After:** All sessions (RAG and non-RAG) navigate to `/app/generative/sessions/:id`. A new `SessionRouter` component at `DashAI/front/src/pages/generative/SessionRouter.jsx` fetches the session, detects `task_name === "RAGTask"`, and renders either `SimplifiedRAGPage` (wrapped in `GenerativeProvider`) or `Generative`. Uses `useRef` to persist the previous view during loading so no spinner flash occurs between same-type session switches. Stale `location.state`-based session selection was removed from `SimplifiedRAGPage`; it now reads the session ID from `useParams()`.

**Files:** `SessionRouter.jsx` (new), `App.jsx`, `SimplifiedRAGPage.jsx`, `SessionBar.jsx`

### `setPromptModel` is NOT a React state setter — never pass a functional updater

**Problem:** `PromptBody` used `setPromptModel((prev) => ({...}))` with a functional updater, but `setPromptModel` is `updatePrompt` — a plain function passed from `SimplifiedSessionSetup`, not a `useState` setter. React passed the updater function itself as the value, causing `sessionData.parameters.prompt` to become a function (instead of `{component, params}`). This broke `isPromptValid` (functions have no `.component` property) and silenced the save button.

**Fix:** Changed `setPromptModel((prev) => ({...}))` to `setPromptModel({...})` (plain object). Also added an `isInitializedRef` guard to avoid overwriting the parent's prompt params on initialization, and persist existing params when updating only template/language.

**Rule:** Only use functional updaters with React `useState` setters. Pass plain values to regular callback props.

### Retrievers: de-hardcode defaults, fetch from backend

**Problem:** `buildHybridModel` in `RetrieverSection.jsx` hardcoded `model_name: "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"` and `merge_strategy: "round_robin"`, ignoring the defaults from `resolveDefaults()`. Also, `getRetrieverComponents()` used `recursive=false`, which failed to find concrete dense retriever families (SentenceTransformer, BERT, DistilBERT, etc.) because they inherit via `HuggingFaceDenseRetriever` (intermediate abstract class).

**Fix:**
- `getRetrieverComponents` in `api/rag.ts` now uses `recursive=true`
- `RetrieverSection` filters out components with `flags: ["abstract"]` so intermediate abstract classes don't appear in the UI
- `buildHybridModel` reads `model_name` from `embeddingDefaults` (fetched via `resolveDefaults`) and `merge_strategy` from `ParallelRetriever` defaults
- Embedding card description shows the default model name (e.g., `sentence-transformers/all-MiniLM-L6-v2`) instead of "N options"
- Sparse default changed from TFIDF → BM25; hybrid now uses BM25 + SentenceTransformerDenseRetriever

**Files:** `api/rag.ts`, `sections/RetrieverSection.jsx`

**Note:** The 4-group preset architecture described above has been replaced by a simpler 3-preset card system (Keyword, Semantic, Hybrid). See "RetrieverSection: 3-preset card architecture" above for the current design.

### AdvancedConfigCard not showing after saving from modal

**Problem:** When saving a retriever configuration from the `RetrieverAdvancedModal` without first selecting a preset group, `selectedGroup` remained `null`. The `isAdvanced` check returned `false` immediately on `!selectedGroup`, so the `AdvancedConfigCard` never rendered.

**Fix:** Added a `useEffect` that auto-detects the group when `retrieverModel` changes but no group is selected. Introduced `"__custom__"` as a sentinel group value for configurations that don't match any preset (e.g., `SequentialRetriever` or custom-parametrized retrievers). `isAdvanced` now handles all three cases: preset match, hybrid, and `__custom__`.

**File:** `sections/RetrieverSection.jsx`

**Note:** With the 3-preset card redesign, `__custom__` is no longer used. `isAdvanced` is now a simple `useMemo` that compares the current `retrieverModel` (minus `top_k`) against the 3 preset models. If it doesn't match any, it's advanced.

### Generator: save button disabled without LLM + API key warning

**Problem:** `GeneratorBody.contextStats` returned `{isValid: true}` even when no generator was selected, enabling the save button prematurely. Additionally, remote models (OpenAI, DeepSeek) showed no warning when `API_key` was empty.

**Fix:**
- `contextStats` returns `{isValid: false}` when `!generatorModel.component` or `!selectedGenerator`
- `isConfigurationComplete` in `SimplifiedSessionSetup` checks `Boolean(sessionData.parameters.generator_model?.component)` explicitly
- `GeneratorBody` detects remote models (`OpenAITextToTextGenerationModel`, `DeepSeekTextToTextGenerationModel`) via `isRemoteModel` and shows an `Alert` warning when `API_key` is empty via `isApiKeyMissing`
- `overallIsValid = contextStats.isValid && !isApiKeyMissing` controls `setIsValid`
- `context_window` and `max_tokens` use `??` instead of `||` to correctly handle `0` values

**Files:** `components/GeneratorBody.jsx`, `SimplifiedSessionSetup.jsx`

### Generator: display_name in Autocomplete

**Problem:** The LLM selector showed class names like `"QwenModel"` instead of human-readable display names like `"Qwen Model"`.

**Fix:** `getOptionLabel` in `GeneratorBody` now uses `getDescription(option.display_name, i18n)` (resolves `MultilingualString` with i18n language), falling back to `option.name`.

**File:** `components/GeneratorBody.jsx`

### Race condition in GeneratorBody.handleGeneratorChange

**Problem:** `handleGeneratorChange` called `setSelectedGenerator(newValue)` **before** the `await resolveDefaults()`, then `setGeneratorModel(...)` after. Between the two, the sync effect detected `!generatorModel?.component` and forcibly set `selectedGenerator` to `null`, breaking the validation chain.

**Fix:** Moved `setSelectedGenerator(newValue)` to **after** the `await`, alongside `setGeneratorModel(...)`. Removed the aggressive `setSelectedGenerator(null)` from the sync effect when `generatorModel.component` is empty — it now just returns without touching the selection.

**File:** `components/GeneratorBody.jsx`

### Prompt: language selector visible when collapsed

**Problem:** The prompt language selector was hidden behind `showDetails &&`, so when the RAG Parameters card was collapsed, users couldn't see or change the selected language.

**Fix:** Removed `showDetails` guard from the language selector in `PromptBody`. Only the template preview remains behind `showDetails`.

**File:** `components/PromptBody.jsx`

### Prompt: default language from platform

**Problem:** `PromptBody` always defaulted to `"en"` when auto-selecting a prompt, regardless of the platform's current language.

**Fix:** Computes `platformLang` from `i18n.language` (supports `en`, `es`, `pt`). Uses it for initial `selectedLanguage` state, auto-selection fallback, and when switching between default prompts.

**File:** `components/PromptBody.jsx`

### CompositeRetrieverBuilder: static flow indicator

**Problem:** The composite retriever tree had no visual indication of the input-to-output flow direction.

**Fix:** Added a static column to the left of the tree showing: "All chunks" at the top, triple downward arrows in the middle, "Selected chunks" at the bottom. Uses theme `divider` color. Text is translatable via `allChunks` / `selectedChunks` keys.

**File:** `advanced/CompositeRetrieverBuilder.jsx`

### RetrieverConfigurationStep: descriptions and instructions

Added two translatable texts to the advanced retriever configuration modal:
- `retrieverDescription` — explains the three retriever families (keyword, embedding, composite) under the selector
- `compositeInstructions` — explains how to add child retrievers (+ button) and edit cards (click), shown only when a composite retriever is selected

**File:** `advanced/RetrieverConfigurationStep.jsx`

### Default chunker name fix

**Problem:** `ChunkingSection` referenced a non-existent chunker `"SimpleChunker"` as the default fallback.

**Fix:** Changed to `"CharacterChunkModel"` (the actual class name).

**File:** `sections/ChunkingSection.jsx`

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
