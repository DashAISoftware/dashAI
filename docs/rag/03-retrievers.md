# 03 — Retrievers

## Class Hierarchy (Composite Pattern)

```
RetrieverModel                      ← Component (abstract)
├── UnitRetriever                   ← Leaf (abstract)
│   ├── SparseRetriever             ← Abstract: TF-IDF/BM25 base
│   │   ├── TFIDFRetriever
│   │   └── BM25Retriever
│   └── DenseRetriever              ← Abstract: embedding-based
│       ├── FastTextDenseRetriever
│       └── HuggingFaceDenseRetriever (abstract, FLAGS=["abstract","huggingface"])
│           ├── SentenceTransformerDenseRetriever
│           ├── BERTDenseRetriever
│           ├── DistilBERTDenseRetriever
│           ├── RoBERTaDenseRetriever
│           ├── E5DenseRetriever
│           ├── GemmaDenseRetriever
│           ├── InstructorDenseRetriever
│           └── LaBSEDenseRetriever
└── CompositeRetriever              ← Composite (abstract)
    ├── SequentialRetriever
    └── ParallelRetriever
```

## Core Interface

Every retriever declares two methods (defined on `RetrieverModel`):

```python
def retrieve(self, query: str) -> List[Chunk]:
    """Return top-k chunks for query."""

def score_chunks(self, candidate_chunks: List[Chunk], query: str) -> List[Tuple[int, float]]:
    """Re-rank candidate_chunks by relevance to query."""
```

- `retrieve()` searches the full index and returns top-k.
- `score_chunks()` scores a pre-selected subset — used by cascade composite strategy for re-ranking.

## Two-Level Embedding Architecture

Dense retrievers are built on a two-level abstraction:

1. **Embedding layer** (`embeddings/dense/`): Internal, non-registered classes that encapsulate loading, tokenization, pooling, and overflow handling. Each implements `_pool()` with family-specific logic.

2. **Retriever layer** (`retrievers/dense/`): Registered Component classes with `SCHEMA`, `DISPLAY_NAME`, `get_metadata()`. Each wraps a specific embedding via `_create_embedding()`.

### Embedding hierarchy (internal)
```
DenseEmbedding (BaseModel, abstract)
 └── HuggingFaceEmbedding (abstract, FLAGS=["abstract","huggingface"])
      ├── OverfloatHandler (abstract — adds overflow strategy + _batch_encode_impl)
      │    ├── _SentenceTransformerEmbedding  (mean pool + L2 norm)
      │    ├── _BERTEmbedding                 (CLS / mean / max / concat layers)
      │    └── _E5Embedding                   (avg pool + query/passage prefix + L2 norm)
      ├── _GemmaEmbedding                     (SentenceTransformer API)
      └── _InstructorEmbedding                (InstructorEmbedding API, instruction-tuned)
```

### Dense retriever families (registered components)

| Family | Models | Pooling | Schema fields |
|--------|--------|---------|---------------|
| `SentenceTransformerDenseRetriever` | 21 (all-MiniLM, all-mpnet, multi-qa-*, msmarco-*, specter, etc.) | mean + L2 norm (fixed) | model_name, overflow_strategy, normalize, device, similarity_metric, top_k |
| `BERTDenseRetriever` | 6 (bert-base/large-*, multilingual) | CLS / mean / max / concat_2/3/4 | model_name, overflow_strategy, pooling_strategy, device, similarity_metric, top_k |
| `DistilBERTDenseRetriever` | 4 (distilbert-base-*, multilingual) | CLS / mean / max / concat_2/3/4 | model_name, overflow_strategy, pooling_strategy, device, similarity_metric, top_k |
| `RoBERTaDenseRetriever` | 4 (roberta-*, xlm-roberta-*) | mean / max (no CLS) | model_name, overflow_strategy, pooling_strategy, device, similarity_metric, top_k |
| `E5DenseRetriever` | 5 (e5-*, multilingual-e5-*) | avg pool + prefix + L2 norm (fixed) | model_name, overflow_strategy, device, similarity_metric, top_k |
| `GemmaDenseRetriever` | 1 (embeddinggemma-300m) | SentenceTransformer API (fixed) | model_name, task_type, overflow_strategy, device, similarity_metric, top_k |
| `InstructorDenseRetriever` | 3 (instructor-base/large/xl) | Instruction-tuned API (fixed) | model_name, instruction, device, similarity_metric, top_k |
| `LaBSEDenseRetriever` | 1 (LaBSE) | mean + L2 norm (fixed) | model_name, overflow_strategy, device, similarity_metric, top_k |

## Language Metadata

Each dense retriever declares per-model language support via `MODELS: Dict[str, dict]`. Example:

```python
MODELS = {
    "sentence-transformers/all-MiniLM-L6-v2": {
        "languages": ["en"],
        "max_seq_length": 512,
    },
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2": {
        "languages": ["en", "es", "fr", "de", ..., "multi"],
        "max_seq_length": 512,
    },
}
```

`get_metadata()` computes and returns:

- `family`: Family display name (e.g. "SentenceTransformers")
- `language_summary`: Aggregated family display string (e.g. "Eng, Esp, Multi +6")
- `language_count`: Total unique languages across all family models
- `model_count`: Number of models in the family
- `model_languages`: Per-model summary dicts with labels, summary, count

The `_hf_language_utils.py` module maps 44 ISO 639-1 codes to display labels (e.g. `"en" → "Eng"`). `compute_language_summary()` truncates at 3 languages with overflow (e.g. `"Eng, Esp, Fra +47"`).

## Overflow Strategy

All dense retrievers (except INSTRUCTOR) expose `overflow_strategy` in their schema:

| Strategy | Behavior |
|----------|----------|
| `truncate` | Truncate each chunk to `model_max_length` tokens. Default and current behavior. |
| `aggregate` | Split chunk into `model_max_length`-sized segments, encode each separately, mean-pool the resulting embeddings. |

`model_max_length` is NOT visible in the schema. It is defined per-model in the `MODELS` dict (e.g., 512 for most models, 8192 for Gemma) and injected automatically by `_create_embedding()`.

The `OverfloatHandler` abstract class implements `_batch_encode_impl()` with both strategies, using HuggingFace tokenizer's `return_overflowing_tokens` for the `aggregate` path.

## Task Prompts (Gemma)

The `GemmaDenseRetriever` supports task-specific prompts that optimize embeddings for a given use case. The user selects a `task_type` from a predefined enum (no free-form prompt engineering).

| Task Type | Query Prompt Format | Use Case |
|-----------|---------------------|----------|
| `search_result` | `task: search result \| query: {text}` | Document retrieval (default for RAG) |
| `question_answering` | `task: question answering \| query: {text}` | Q&A retrieval |
| `fact_checking` | `task: fact checking \| query: {text}` | Evidence retrieval for fact verification |
| `classification` | `task: classification \| query: {text}` | Text classification |
| `clustering` | `task: clustering \| query: {text}` | Text clustering |
| `sentence_similarity` | `task: sentence similarity \| query: {text}` | Semantic similarity (non-retrieval) |
| `code_retrieval` | `task: code retrieval \| query: {text}` | Code search |

During batch encoding (document indexing), a fixed document prompt is used: `title: none | text: {text}`. During query encoding (retrieval), the selected task prompt is prepended.

*INSTRUCTOR uses a different mechanism: free-form text instruction passed as `[[instruction, text]]` pairs via the `InstructorEmbedding` library — see its schema for the `instruction` field.*

## Composite Strategies

### Sequential Retriever

Applies children one after another. Two strategies via `RetrievalStrategy` enum:

| Strategy | Behavior |
|----------|----------|
| `ACCUMULATE` | Each child retrieves independently. Results are accumulated until top-k is reached. Order: child 1 returns N, then child 2 returns M, and so on. |
| `CASCADE` | First child retrieves broadly, subsequent children refine via `score_chunks()`. Child 1 returns candidates, child 2 re-ranks and trims to top-k. Requires `UnitRetriever` children only (composites don't implement `score_chunks`). If a composite is added to a cascade, `UnitRetrieverChildError` is raised. |

### Parallel Retriever

All children run concurrently. Two merge strategies via `MergeStrategy` enum:

| Strategy | Behavior |
|----------|----------|
| `ROUND_ROBIN` | Takes 1 chunk from each child in order, cycling. |
| `INTERLEAVE` | Takes chunks proportionally from each child based on their result count. |

## Persistence Layer

### SparsePersistence
```python
@dataclass
class SparsePersistence:
    model_dir: str | None  # Absolute path to directory with .pkl files
```
- If `None`: no previous dump exists → retriever trains from scratch.
- Factory sets `model_dir` **before** calling `save()`.
- `save()` on TFIDF/BM25 is parameterless — reads `self._persistence.model_dir`.

### DensePersistence
```python
@dataclass
class DensePersistence:
    matrix_dirs: dict[int, str]  # document_id → absolute path to dir with embeddings.npy
    embedding_model_id: int      # identifies which embedding model produced the vectors
```
- Matrix dirs are per-document (each document has its own `.npy` file).
- `DenseRetriever.compute_missing_embeddings()` only does `np.save()` — factory creates the `RAGEmbeddingMatrix` DB rows afterwards.

### Note on mutability
Both dataclasses are `frozen=False` (mutable). This is intentional: the factory constructs the retriever instance first, then sets `persistence.model_dir` (for sparse) or `persistence.matrix_dirs` (for dense) via path resolution, **before** calling `save()`.

## Constructor Contract

### DenseRetriever + init_model pattern

All dense retrievers extend `HuggingFaceDenseRetriever` (abstract, FLAGS=["abstract","huggingface"]) which adds:

```python
class HuggingFaceDenseRetriever(DenseRetriever):
    @abstractmethod
    def _create_embedding(self) -> HuggingFaceEmbedding:
        raise NotImplementedError

    def init_model(self) -> None:
        embedding = self._create_embedding()
        embedding.load()
        self._init_embedding(embedding)
```

Concrete families implement `_create_embedding()` which:
1. Pops schema params from `self.params` (model_name, device, etc.)
2. Looks up `model_max_length` from `MODELS[model_name]`
3. Returns the family-specific embedding instance with all params

### UnitRetriever signature
```python
def __init__(self, **kwargs):
    self._env_rag_path = kwargs.pop("env_rag_path")
    self._chunks = kwargs.pop("chunks")
    self._persistence = kwargs.pop("persistence")
    self._validate_extra_kwargs(kwargs)
    super().__init__(**kwargs)
```

### Composite constructor
```python
def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self._children: List[RetrieverModel] = []
```
`children` is **completely removed** from pydantic schema. The frontend sees composite as a retriever with strategy params only. Factory recursively creates children from `rag_retriever_child` rows.

## Retrieval DB Schema

```
RAGRetriever (canonical identity for every retriever)
├── class_name: str
├── pipeline_id: FK → RAGPipeline.id
│
├── RAGSparseRetriever (via bridge_id)
│   ├── class_name, parameters, chunk_set_id
│   └── storage_folder: str
│
├── RAGDenseRetriever (via bridge_id)
│   ├── class_name, parameters, chunk_set_id
│   ├── embedding_model_id: FK → RAGEmbeddingModel.id
│   └── (no storage_folder — matrix dirs are per-document)
│
└── RAGRetrieverChild (composite parents, via parent_id)
    ├── parent_id: FK → RAGRetriever.id
    ├── child_id: FK → RAGRetriever.id
    └── child_order: int
```

## ID Management

`RetrieverModel._db_id` is the unified identity slot. All retrievers (sparse, dense, composite) get their DB ID set via:

```python
def set_id(self, db_id: int) -> None:
    self._db_id = db_id

def get_id(self) -> int:
    return self._db_id
```

No overrides in subclasses — a single slot for the `rag_retriever.id` value. The factory calls `set_id()` after creating the bridge row.

## Exception Hierarchy

```
RetrieverError (base)
├── MissingParameterError         ← required parameter missing from kwargs
├── ExtraKwargsMissingError       ← required infrastructure kwargs missing
├── CompositeValidationError      ← invalid composite config
└── UnitRetrieverChildError       ← composite child is not a UnitRetriever
```

All exception classes accept typed parameters and generate descriptive messages. No bare `Exception` is raised anywhere in the retriever subsystem.

## Roadmap: Cross-Encoder Retrievers

A future phase will add cross-encoder (re-ranking) dense retrievers. Unlike bi-encoders, cross-encoders process query+document pairs jointly and output a relevance score. They would:

- Implement `score_chunks()` by calling the cross-encoder model
- Raise `NotImplementedError` on `retrieve()` (not designed for full-index search)
- Be used inside `SequentialRetriever` with `CASCADE` strategy for retrieve → re-rank pipelines

Models to support: `cross-encoder/ms-marco-MiniLM-L-6-v2`, `cross-encoder/stsb-roberta-base`, etc.
