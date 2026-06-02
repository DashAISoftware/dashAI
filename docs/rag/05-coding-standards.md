# 05 — Coding Standards

Mandatory conventions for all RAG module code. These apply to the entire `DashAI/back/models/RAG/` subtree.

## 1. Zero Silent Defaults

**Never** use:
- `kwargs.pop("key", default_value)` — if `key` is required, let it raise KeyError
- `x or default` — if `x` could legitimately be `None`/`0`/`""`, handle it explicitly
- `getattr(obj, "attr", default)` — raise AttributeError if missing

If a parameter is required, the absence must produce a typed exception:

```python
# CORRECT
if "chunks" not in kwargs:
    raise ExtraKwargsMissingError({"chunks"}, self.__class__.__name__)
self._chunks = kwargs.pop("chunks")

# WRONG
self._chunks = kwargs.pop("chunks", {})
```

## 2. Zero Magic Strings

Use the following pattern everywhere:

### Enums (for logical choices)
```python
class RetrievalStrategy(Enum):
    ACCUMULATE = "accumulate"
    CASCADE = "cascade"

class MergeStrategy(Enum):
    ROUND_ROBIN = "round_robin"
    INTERLEAVE = "interleave"
```

### Constants (for dictionary keys)
```python
CHUNKS = "chunks"
COMPONENT_REGISTRY = "component_registry"
ENV_RAG_PATH = "env_rag_path"
COMPOSITE_RETRIEVER_NAMES = frozenset({"SequentialRetriever", "ParallelRetriever"})
```

Never write `"accumulate"` or `"chunks"` as string literals in function bodies.

## 3. Typed Generics Everywhere

```python
# CORRECT
from typing import Dict, List, Optional, Tuple
def load(self, ids: List[int]) -> Dict[int, BaseDocument]: ...

# WRONG
def load(self, ids): ...  # bare annotation
def load(self, ids: list) -> dict: ...  # untyped generics
```

## 4. MultilingualString + `# type: ignore` on Schemas

Every `schema_field` description must use `MultilingualString(en=..., es=...)`. Every `schema_field` assignment must have `# type: ignore`:

```python
chunk_size: schema_field(
    int_field(gt=0),
    description=MultilingualString(
        en="Size of each chunk in characters.",
        es="Tamaño de cada fragmento en caracteres.",
    ),
    placeholder=500,
)  # type: ignore
```

## 5. No Comments in Code

Do not add comments to source files unless explicitly requested. This includes:
- No docstrings beyond what already exists
- No inline comments explaining logic
- No `# TODO`, `# FIXME`, `# HACK`, `# NOTE`

Existing comments may be preserved; do not add new ones.

## 6. ML/DB Separation

**ML layer** (`retrievers/`, `embeddings/`, `chunking_models/`):
- Must NOT import `sqlalchemy` or any `DashAI.back.dependencies.database.models`
- Receives `Chunk` objects and `Persistence` dataclasses (paths only)
- Performs file I/O (`np.load`/`np.save`, `pickle`)

**DB layer** (`retriever_repository.py`, `pipeline_repository.py`, `document_loader.py`):
- Pure SQLAlchemy operations
- Creates/updates DB model instances
- Never instantiates ML models

**Factory layer** (`retriever_models_factory.py`, `chunking_models_factory.py`):
- Orchestrates both layers
- Calls repository for DB lookups, builds Persistence objects, injects into ML constructors
- Calls repository again for saves

## 7. Exception Handling

- All RAG-specific exceptions extend `RAGWorkflowError` or `RetrieverError`
- Every constructor validates required kwargs before proceeding
- No bare `except:` or `except Exception:` without re-raising typed exceptions
- `raise from` for exception chaining when appropriate

## 8. Component Registry Usage

When factories need to resolve a component name to a class:

```python
component_class = self.component_registry[component_name]
instance = component_class(**params)
```

The `extra_args_enum.COMPONENT_REGISTRY` constant is used only for passing the registry through kwargs dictionaries. Direct access uses `self.component_registry`.

## 9. Factory Constructor Convention

All factory constructors follow this signature pattern:

```python
class SomeFactory(ModelsFactory):
    def __init__(self, db: Session, ...other deps...):
        super().__init__(db=db)
        # Store additional dependencies
```

The base class receives `db`. Sub-factories add their specific dependencies.

## 10. Schema Definition Convention

Every Component subclass must define:
- `COMPATIBLE_COMPONENTS` (list of task names)
- `SCHEMA` (Pydantic model class)
- Optional: `DESCRIPTION` and `DISPLAY_NAME` as `MultilingualString`

Parameters are never optional in schemas unless they genuinely have a sensible default.

## 11. Imports

- Aggregate imports in `__init__.py` files for public API
- Internal files import from sibling modules directly
- No circular imports — if needed, defer imports inside functions
- Use absolute imports from `DashAI.back.*`

## 12. `normalize_payload` — frontend properties wrapper normalisation

The frontend auto-generated forms (``generateInitialValues`` in
``utils/schema.js``) produce a ``properties`` wrapper for nested component
fields:

.. code::

    {"properties": {"component": "X", "params": {"comp": {"component": "X", "params": {...}}}}}

This wrapper must be converted to the canonical ``{component, params}`` form
before ``model_validate``. The conversion function is
``DashAI.back.core.schema_fields.utils.normalize_payload`` and its logic is
**identical** to the unwrapping step in ``model_factory._process_param``
(approximately line 162). It is called in two places:

- ``RetrieverFactory.create()`` — called with the params passed to
  ``create(component_name, params)``.
- ``generative_session.py`` (the ``upload_generative_session`` endpoint) —
  called with ``params.parameters`` before ``model_validate``.

**Do not** add a ``model_validator`` to any schema class as an alternative
way to normalise the wrapper. The normalisation belongs in the payload
preparation layer, not in the schema definition.

## 13. Infrastructure injection pattern

Schema fields should never contain runtime infrastructure such as
``env_rag_path``, ``chunks``, or ``persistence``. These are injected AFTER
schema validation via ``inject_infra()`` on ``RetrieverModel``:

1. ``model_class.SCHEMA.model_validate(params)`` — validates only the
   fields declared in the schema (``BaseSchema`` has ``extra="forbid"``).
2. ``fill_objects(validated, registry)`` — resolves ``{component, params}``
   sub-fields into instantiated objects (core DashAI).
3. ``model_class(**resolved)`` — constructs the model with clean params.
4. ``factory._inject_infra(model, persistence)`` — calls
   ``model.inject_infra(env_rag_path, chunks, persistence)`` which sets the
   runtime attributes.
5. ``model._check_infra()`` — called at the start of ``retrieve()`` and
   ``score_chunks()`` to ensure infrastructure was injected.

This guarantees that:

- Schema fields and runtime infrastructure are never mixed.
- ``model_validate`` catches missing/wrong schema parameters.
- ``_check_infra`` catches missing infrastructure.

## 14. File Naming

- Python files: `snake_case.py`
- Classes: `PascalCase`
- Test files: `test_*.py`
- Documentation: `NN-*kebab-case*.md`
