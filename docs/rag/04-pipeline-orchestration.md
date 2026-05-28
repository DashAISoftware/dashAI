# 04 — Pipeline Orchestration

## RAGPipeline (`RAGPipeline.py`)

`RAGPipeline` extends `BaseGenerativeModel`. It is the entry point for RAG session execution. Its `__init__` is pure orchestration — no direct DB queries.

### Configuration System

Raw kwargs are parsed once into a typed `RAGPipelineConfig` dataclass:

```python
@dataclass(frozen=True)
class ModelRef:
    component: str
    params: Dict[str, Any]

@dataclass(frozen=True)
class RAGPipelineConfig:
    session_id: int
    db: Session
    component_registry: ComponentRegistry
    env_rag_path: str
    documents: List[int]
    prompt_id: int
    chunking_model: ModelRef
    retriever_model: ModelRef
    generation_model: ModelRef

    @classmethod
    def from_kwargs(cls, **kwargs) -> RAGPipelineConfig: ...
    @classmethod
    def validate_model_refs(cls, params) -> None: ...
```

- `from_kwargs(**kwargs)` — full validation including infra keys, raises `RAGPipelineConfigError` on missing/unknown keys
- `validate_model_refs(params)` — lightweight validation for early checking (used in `rag_job.py`)
- Magic strings eliminated: `config.chunking_model.component` instead of `kwargs["chunking_model"]["component"]`
- Unknown keys are rejected (no silent ignoring)

### Initialization Flow (step-by-step)

```
RAGPipeline.__init__(**kwargs)
│
├─ 1. RAGPipelineConfig.from_kwargs(**kwargs)
│   Parses + validates → typed fields
│
├─ 2. PipelineRepository.ensure_row(session_id)
│   → Finds or creates rag_pipeline row → self.pipeline_id
│
├─ 3. DocumentLoader.load(document_ids)
│   → Hydrates in-memory BaseDocument instances from DB rows
│   → Returns Dict[int, BaseDocument]
│
├─ 4. PromptFactory.get_prompt(prompt_id)
│   → Loads Prompt instance by DB ID
│
├─ 5. validate_params(kwargs)
│   → Ensures chunking_model, retriever_model, generation_model exist
│   → Ensures each has 'component' and 'params' sub-keys
│
├─ 6. get_or_create_chunk_set(db, doc_ids, pipeline_config)
│   → SHA-256 signature → finds existing or creates new RAGChunkSet
│
├─ 7. ChunkingModelsFactory.init_component_by_name(name, params)
│   → Instantiates chunking model (CharacterChunkModel or TokenChunkModel)
│   → Reuses existing chunks if chunk_set already has them
│   → update_db_models() persists new chunks
│   → Returns (chunking_model_id, chunking_model)
│
├─ 8. RetrieverModelsFactory.init_component_by_name(name, params)
│   → Orchestrates: repo lookup → persistence → constructor injection
│   → Recursively builds composite children
│   → Returns (_, retriever)
│
├─ 9. LLMFactory.create(component_name, params)
│   → ComponentRegistry lookup + instantiation
│   → Returns TextToTextGenerationTaskModel
│
└─ 10. PipelineRepository.update_row(...)
    → Updates rag_pipeline row with chunking_model_id, prompt_id, gen_model_id
```

### Runtime Methods

```python
def single_interaction(query, history=None) -> List[Chunk]:
    """Delegates to self.retriever.retrieve(query)"""

def _build_chunk_references(chunks) -> Tuple[str, Dict]:
    """Format chunks to text for prompt + build reference metadata dict."""

def generate(input_data: Tuple[str, List[Dict]]) -> Tuple[str, Dict]:
    """
    1. Parse input_data → query + history
    2. self.single_interaction(query) → chunks
    3. self._build_chunk_references(chunks) → prompt_text, chunk_dict
    4. self.prompt_model.format(input, prompt_text) → prompt
    5. self.llm_model.generate(history + prompt) → output
    6. Returns (output_text, chunk_reference_dict)
    """
```

### Error Hierarchy

```
RAGPipelineError (base)
├── RAGPipelineParametersError   ← backward-compat alias for ConfigError
├── RAGPipelineConfigError       ← invalid/missing config keys or unknown kwargs
├── RAGPipelineInitializationError
├── RAGPipelineRuntimeError
└── RAGDatabaseError
```

## Supporting Classes

### `PipelineRepository` (`pipeline_repository.py`)

```python
class PipelineRepository:
    def __init__(self, db: Session)
    def ensure_row(self, session_id: int) -> RAGPipeline:
        """Find or create rag_pipeline row for session. Returns the row."""
    def update_row(self, session_id: int, **kwargs) -> None:
        """Update chunking_model_id, prompt_id, generation_model_id on the pipeline row."""
```

### `DocumentLoader` (`document_loader.py`)

```python
class DocumentLoader:
    def __init__(self, db: Session)
    def load(self, document_ids: List[int]) -> Dict[int, BaseDocument]:
        """
        Query document rows from DB.
        Hydrate into BaseDocument subclasses (PDFDocument, TxtDocument) by file_type.
        Raise RAGDatabaseError if any ID not found.
        Returns Dict[doc_id, BaseDocument] for O(1) lookup.
        """
```

### `LLMFactory` (`llm_factory.py`)

```python
class LLMFactory:
    def __init__(self, component_registry: ComponentRegistry)
    def create(self, component_name: str, params: dict) -> TextToTextGenerationTaskModel:
        """Look up component in registry, instantiate with params."""
```

### `ModelsFactory` (`models_factory.py`)

Abstract base class for all RAG sub-factories:

```python
class ModelsFactory:
    def __init__(self, db: Session)
    def init_component_by_name(component_name: str, model_params: dict) -> Tuple[int, Any]:
        """Abstract: instantiate component from name + params, return (db_id, instance)"""
```

Extended by:
- `ChunkingModelsFactory` — instantiate chunking models, persist chunks to DB
- `RetrieverModelsFactory` — orchestrate retriever creation via `RetrieverRepository`

### `ChunkingModelsFactory` (`chunking_models/chunking_models_factory.py`)

```python
class ChunkingModelsFactory(ModelsFactory):
    def __init__(self, db: Session, documents: Dict[int, BaseDocument], chunk_set_id: int)
    def init_component_by_name(name, params) -> Tuple[int, BaseChunkingModel]:
        """Look up existing chunks for chunk_set. If none, chunk documents. Persist to DB."""
    def update_db_models(chunking_model) -> None:
        """Persist new chunks to DB (hash-based dedup)."""
```

## Extra Args System

`extra_args_enum.py` defines 3 string constants used as dictionary keys when passing infrastructure between factories and models:

```python
CHUNKS = "chunks"                    # Dict[int, Dict[int, Chunk]]
COMPONENT_REGISTRY = "component_registry"  # ComponentRegistry instance
ENV_RAG_PATH = "env_rag_path"        # str — environment RAG storage path
```

Reduced from 12 to 3 during refactoring. The removed constants were replaced by:
- `Persistence` dataclasses (replaced raw DB model references)
- Factory-orchestrated DB lookups (replaced passing DB session directly)

## Chunk Set Identity

`chunk_set_utils.py` provides `get_or_create_chunk_set(db, document_ids, pipeline_config)`:

1. Computes signature: `SHA-256(sorted(doc_ids) + sorted_config)`
2. Queries for existing `RAGChunkSet` with that signature
3. If found: returns it (chunks already exist — no re-chunking needed)
4. If not: creates new `RAGChunkSet` row + `RAGChunkSetDocument` rows for each doc

This ensures deterministic reuse: two sessions with same documents + same chunking config share chunks.
