# 03 — Retrievers

## Class Hierarchy (Composite Pattern)

```
RetrieverModel                      ← Component (abstract)
├── UnitRetriever                   ← Leaf (abstract)
│   ├── SparseRetriever             ← Abstract: TF-IDF/BM25 base
│   │   ├── TFIDFRetriever
│   │   └── BM25Retriever
│   └── DenseRetriever
└── CompositeRetriever              ← Composite (abstract)
    ├── SequentialRetriever
    └── ParallelRetriever
```

## Core Interface

Every retriever declares two methods (defined on `RetrieverModel`):

```python
def retrieve(self, query: str) -> List[Chunk]:
    """Return top-k chunks for query."""

def score_chunks(self, candidate_chunks: List[Chunk], query: str) -> List[Chunk]:
    """Re-rank candidate_chunks by relevance to query."""
```

- `retrieve()` searches the full index and returns top-k.
- `score_chunks()` scores a pre-selected subset — used by cascade composite strategy for re-ranking.

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

### UnitRetriever signature
```python
def __init__(self, **kwargs):
    # Pops infrastructure kwargs:
    self._env_rag_path = kwargs.pop("env_rag_path")
    self._chunks = kwargs.pop("chunks")
    self._persistence = kwargs.pop("persistence")
    # Validates required extra kwargs (set by subclass):
    self._validate_extra_kwargs(kwargs)
    # Calls parent with remaining kwargs
    super().__init__(**kwargs)
```

### REQUIRED_EXTRA_KWARGS
Each class declares a `REQUIRED_EXTRA_KWARGS` list. `UnitRetriever` validates the **common subset** `{env_rag_path, chunks, persistence}`. Concrete classes append type-specific keys:

- `TFIDFRetriever.REQUIRED_EXTRA_KWARGS`: common + `{vectorizer_model,...}`
- `DenseRetriever.REQUIRED_EXTRA_KWARGS`: common + `{embedding_model,...}`

If any required key is missing from kwargs, `ExtraKwargsMissingError` is raised immediately — no silent defaults.

### Composite constructor
```python
def __init__(self, **kwargs):
    # children are NOT in kwargs — factory manages them separately
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
