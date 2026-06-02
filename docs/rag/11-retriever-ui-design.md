# Retriever Configuration UI — Technical Design Document

> **Target audience**: AI coding agents working on this codebase.
> **Scope**: The retriever configuration interface in the simplified RAG flow — component states, design decisions, bugs fixed, constraints, backend-frontend contract, and data flow.

> **Source**: Originally located at `DashAI/front/src/pages/generative/simplified-RAG/RETRIEVER_UI_DESIGN.md`. Moved here on 2026-06-01 as part of documentation consolidation.

---

## 1. File Map

| File | Purpose |
|------|---------|
| `sections/RetrieverSection.jsx` | **Simplified view**. Renders 3 preset cards (Keyword, Embedding, Hybrid), Top-K slider, "Advanced" button, `AdvancedConfigCard` when `isAdvanced`, and the amber "Advanced Top K" chip. |
| `advanced/RetrieverAdvancedModal.jsx` | Modal wrapper. Holds `RetrieverConfigurationStep` behind a `FormSchemaProvider`. Has Save/Cancel buttons which call `retrieverStepRef.saveFormValues()`. |
| `advanced/RetrieverConfigurationStep.jsx` | Autocomplete for retriever model selection. Dispatches to `AutoSaveFormSchema` (unit retrievers) or `CompositeRetrieverBuilder` (composite retrievers). Owns `savedParamsRef`. |
| `advanced/RetrieverNodeConfig.jsx` | Dialog for configuring a child node inside `CompositeRetrieverBuilder`. Model autocomplete + auto-saving `FormSchema`. |
| `advanced/CompositeRetrieverBuilder.jsx` | Tree builder for `SequentialRetriever` / `ParallelRetriever`. Renders `TreeNodeView` for each node, opens `RetrieverNodeConfig` for editing. Serializes tree to `{component, params, children}` on every emit. |
| `components/ragFormDefaults.js` | `buildDefaultValuesFromSchemaProperties`, `normalizeParamsForSchema`, `getInitialModelParameters`. Bridge between raw schema `properties` and form initial values. |
| `components/PresetCard.jsx` | Reusable card. Amber border+background when selected, clickable. |
| `components/AdvancedConfigCard.jsx` | Thin wrapper: renders `PresetCard` with "Advanced config applied" label and model name as description. |
| `utils/schema.js` | `formattedModel` (resolves `ComponentField` sub-forms via API), `generateYupSchema` (Yup + initial values), `formattedSubform`, `getParamsFromSubform`. |
| `api/rag.ts` | `getRetrieverComponents(parentName)`, `getRetrievalParadigm()` — fetches component metadata from backend. |
| `api/component.ts` | `getComponents({ model })` — fetches schema for a single component by name. |

### Backend (Python)

| File | Purpose |
|------|---------|
| `retrievers/retriever_model.py` | Base class. `Component` in Composite (GoF). `validate_and_transform`, `fill_objects`. |
| `retrievers/unit_retriever.py` | Base for leaf retrievers (sparse/dense). |
| `retrievers/composite/composite_retriever.py` | `CompositeRetriever` — holds `_children: List[RetrieverModel]`. |
| `retrievers/composite/sequential_retriever.py` | Cascade-only. No `strategy` field. Schema: `children` only. |
| `retrievers/composite/parallel_retriever.py` | `ROUND_ROBIN` / `INTERLEAVE`. `MergeStrategy` enum. |
| `retrievers/sparse/tfidf_retriever.py` | `TFIDFRetriever` + `TFIDFVectorizerModel`. Vectorizer is a `ComponentField` in the schema. |
| `retrievers/sparse/bm25_retriever.py` | `BM25Retriever` + `BM25VectorizerModel`. |
| `retrievers/dense/dense_retriever.py` | `DenseRetriever(UnitRetriever)`. Accepts `_embedding_model` kwarg. Cleans `self.params`, stores `encoding_model`. |
| `retrievers/dense/huggingface_dense_retriever.py` | Schema: flat encoding params. `_ENCODING_CLASS`, `_ENCODING_PARAM_KEYS`. `__init__` builds `HuggingFaceEmbedding`. |
| `retrievers/dense/fasttext_dense_retriever.py` | Same pattern as HuggingFace. |
| `retrievers/retriever_factory.py` | Full lifecycle: DB lookup-or-create, encoding injection, persistence wiring, child recursion. |
| `retrievers/enums.py` | `MergeStrategy` (only; `RetrievalStrategy` removed). |
| `core/schema_fields/` | Type system: `BaseSchema`, `schema_field`, `component_field`, `enum_field`, etc. |

---

## 2. Data Model (Frontend)

### 2.1 `retrieverModel`

The single source of truth for the current retriever configuration. Shape:

```ts
{
  component: string;                          // e.g. "ParallelRetriever", "TFIDFRetriever"
  params: Record<string, any>;                // varies by component
}
```

#### Unit retriever example (TFIDF):
```json
{
  "component": "TFIDFRetriever",
  "params": {
    "TFIDFVectorizer": {
      "properties": {
        "component": "TFIDFVectorizerModel",
        "params": {
          "comp": {
            "component": "TFIDFVectorizerModel",
            "params": {
              "ngram_range": [1, 1],
              "max_df": 1.0,
              "lowercase": true
            }
          }
        }
      }
    },
    "similarity_function": "cosine",
    "top_k": 5
  }
}
```

#### Hybrid example (ParallelRetriever):
```json
{
  "component": "ParallelRetriever",
  "params": {
    "strategy": "round_robin",
    "children": [
      {
        "component": "TFIDFRetriever",
        "params": {
          "TFIDFVectorizer": { "...": "..." },
          "similarity_function": "cosine",
          "top_k": 5
        }
      },
      {
        "component": "HuggingFaceDenseRetriever",
        "params": {
          "model_name": "sentence-transformers/all-MiniLM-L6-v2",
          "pooling_strategy": "mean",
          "similarity_metric": "cosine",
          "top_k": 5
        }
      }
    ]
  }
}
```

#### Sequential example:
```json
{
  "component": "SequentialRetriever",
  "params": {
    "children": [
      { "component": "TFIDFRetriever", "params": { "top_k": 20 } },
      { "component": "HuggingFaceDenseRetriever", "params": { "top_k": 5 } }
    ]
  }
}
```

### 2.2 `groups`

```ts
Array<{key: "keyword" | "embedding" | "hybrid", members: ComponentInfo[]}>
```

- `keyword`: children of `SparseRetriever` (TFIDF, BM25)
- `embedding`: children of `DenseRetriever` (FastText, HuggingFace)
- `hybrid`: empty members, hardwired to `ParallelRetriever`

Fetched via `getRetrieverComponents(parentName)` which queries component registry by base class name.

### 2.3 `selectedGroup`

One of `"keyword"`, `"embedding"`, `"hybrid"`, or `null` (nothing selected). Determines which `PresetCard` shows as selected.

### 2.4 `isAdvanced` (computed)

`true` when the current `retrieverModel` deviates from the paradigm defaults. Computed via `useMemo` with dependencies `[retrieverModel, selectedGroup, groups, hybridDefaults]`.

**Algorithm**:

1. If `retrieverModel` or `selectedGroup` is missing → `true`
2. If `top_k` is not in `[3, 5, 10, 15, 20]` → `true` (topK was customized)
3. For `"hybrid"`:
   - Component must be `"ParallelRetriever"` → else `true`
   - Build fresh default model via `buildHybridModel(tk, hybridDefaults)`
   - Compare `retrieverModel.params` vs fresh via `deepEqual` → `true` if different
4. For `"keyword"` / `"embedding"`:
   - Match component against group members
   - Build defaults via `buildDefaultValuesFromSchemaProperties(schema.properties)`
   - Strip `top_k` from both sides with `filterTopK`
   - Compare via `deepEqual`

**CRITICAL**: `isAdvanced` does NOT depend on `topK` state or `selectedModel`. It uses the current `retrieverModel` as ground truth and compares it against dynamically-resolved defaults.

### 2.5 `topK` (slider state)

Local state initialized from `retrieverModel`. Synced from model via `useEffect([retrieverModel])`. Default = 10. Changes only through slider clicks (not from model changes except initial sync).

---

## 3. Data Flow

### 3.1 Initial Load

```
RetrieverSection mount
  → load()
    → getRetrieverComponents("SparseRetriever") → groups.keyword
    → getRetrieverComponents("DenseRetriever")  → groups.embedding
    → push { key: "hybrid", members: [] }
    → resolveDefaults("TFIDFRetriever")         → tfidfDefaults
    → resolveDefaults("HuggingFaceDenseRetriever") → hfDefaults
    → setHybridDefaults({ tfidf, huggingface })

    → Auto-repair check (see §5.2)

    → If retrieverModel has a component:
        → Find matching group → setSelectedGroup
        → Find matching model  → setSelectedModel
    → setLoading(false)
```

### 3.2 `resolveDefaults(modelName)`

```
getComponents({ model: modelName })
  → backend returns { schema: JSON Schema }
  → formattedModel(schema)
      → For each ComponentField property:
          → getComponents({ model: placeholder.component })
          → formattedModel(subform.schema)  // recursive
          → Returns { properties: { component, params: { comp: { component, params } } } }
  → generateYupSchema(formatted)
      → generateInitialValues() recursively resolves placeholders
  → Returns initialValues
```

**Why not `buildDefaultValuesFromSchemaProperties` alone**: It only reads `placeholder` from the schema `properties`. For `ComponentField`s, the placeholder is `{component, params: {}}`. It cannot resolve nested sub-component defaults. `formattedModel` + `generateYupSchema` is the only path that recursively fetches and resolves ComponentField schemas.

### 3.3 `selectGroup(groupKey)` — Clicking a PresetCard

1. If `alreadySelected` (`!isAdvanced && selectedGroup === groupKey`):
   - **DOES NOT rebuild the model** (preserves user customizations)
   - Opens advanced modal: `setShowAdvanced(true)`
   - Returns

2. If NOT already selected:
   - Clears advanced: `setShowAdvanced(false)`
   - Sets `selectedGroup`
   - If `"hybrid"`: `setRetrieverModel(buildHybridModel(topK, hybridDefaults))`
   - If keyword/embedding: picks first member, builds defaults via `buildDefaultValuesFromSchemaProperties`
   - `topK` slider state is preserved (not reset)

### 3.4 `buildHybridModel(effectiveK, defaults)`

Constructs a `ParallelRetriever` model with two children:

```js
{
  component: "ParallelRetriever",
  params: {
    strategy: "round_robin",
    children: [
      {
        component: "TFIDFRetriever",
        params: { ...tfidfDefaults, top_k: Math.max(1, Math.ceil(effectiveK / 2)) }
      },
      {
        component: "HuggingFaceDenseRetriever",
        params: { ...hfDefaults, top_k: Math.max(1, Math.floor(effectiveK / 2)) }
      }
    ]
  }
}
```

Top-K is **split evenly** between the two children (ceil for TFIDF, floor for HuggingFace). Minimum = 1 per child.

### 3.5 Top-K Slider

- Only visible when `!isAdvanced` and `selectedGroup` is set.
- Shows 5 values: `[3, 5, 10, 15, 20]`.
- Calls `handleTopKChange(value)`:
  - For hybrid: rebuilds model via `buildHybridModel(value, hybridDefaults)`
  - For unit: updates `params.top_k` via spread
- **Disabled when `isAdvanced`** (returns early, no-op).

### 3.6 AdvancedConfigCard + Amber Chip

When `isAdvanced`:
- The corresponding `PresetCard` is NOT selected (deselected).
- `AdvancedConfigCard` renders in its place: shows component name + "Advanced config applied" label with amber styling.
- An amber chip shows `"Advanced Top K: {effectiveTopK}"` aligned beside/under the card.
- Both cards + chip are clickable → opens advanced modal.

### 3.7 Advanced Modal → Save

```
User clicks "Done"
  → RetrieverAdvancedModal.handleSave()
    → retrieverStepRef.current.saveFormValues()
      → Calls saveCurrentFormValues() in RetrieverConfigurationStep
        → Reads savedParamsRef.current (last auto-saved form values)
        → setRetrieverModel({ component, params })
    → onClose() → setShowAdvanced(false)
```

---

## 4. Form Save Mechanism (RetrieverConfigurationStep)

### 4.1 The Problem with `enableReinitialize`

`FormSchema` (which auto-saves) re-initializes when `initialValues` changes. If `initialValues` depends on `retrieverModel.params`, every auto-save → `retrieverModel` updates → `initialValues` changes → form re-initializes → user's changes are lost.

### 4.2 The Solution: `savedParamsRef` + Stable `initialValues`

**`savedParamsRef`**: A `useRef` that stores the last auto-saved form values. Updated in:
- `handleParametersSave` (unit retrievers, from `FormSchema` auto-save)
- `handleCompositeChange` (composite retrievers, from `CompositeRetrieverBuilder`)

**`initialValues` in `AutoSaveFormSchema`**: Depends ONLY on `[selectedRetriever]`. Uses `getInitialModelParameters` to resolve defaults based on the selected model's schema. It does NOT depend on `retrieverModel`, so it never re-initializes from auto-saves.

```jsx
const initialValues = useMemo(() => {
  return getInitialModelParameters({
    selectedModel: selectedRetriever,
    currentModelName: retrieverModel?.component,
    currentParams: retrieverModel?.params,
  });
}, [selectedRetriever]);  // ← ONLY selectedRetriever
```

On first open: `currentModelName` may match → preserves existing params.
On model change (autocomplete): `currentModelName` is null → fresh defaults.
On subsequent auto-saves: `selectedRetriever` hasn't changed → same `initialValues` → no re-initialization.

### 4.3 Cleanup on Unmount

```jsx
useEffect(() => {
  return () => {
    saveCurrentFormValues();  // preserves last params when navigating away
  };
}, [saveCurrentFormValues]);
```

---

## 5. Auto-Repair on Load

### 5.1 Problem

Old sessions saved before the refactor have `TFIDFRetriever` children with empty vectorizer sub-params:

```json
{
  "TFIDFVectorizer": {
    "properties": { "component": "TFIDFVectorizerModel", "params": { "comp": { "component": "TFIDFVectorizerModel", "params": {} } } }
  }
}
```

The innermost `params: {}` means the vectorizer has no configuration — the backend will fail or use wrong defaults.

### 5.2 Detection & Repair Algorithm

```js
const fresh = buildHybridModel(getEffectiveTopK(retrieverModel), { tfidf: tfidfDefaults, huggingface: hfDefaults });

if (!deepEqual(retrieverModel.params, fresh.params)) {
  // Model differs from fresh defaults → could be either:
  // (a) Old session with empty sub-params, or
  // (b) User-customized model

  // Check for empty ComponentField sub-params:
  const hasEmptySubform = retrieverModel.params?.children?.some((child) =>
    Object.values(child.params || {}).some((v) => {
      const inner = v?.properties?.params?.comp?.params;
      return inner && typeof inner === "object" && Object.keys(inner).length === 0;
    }),
  );

  if (hasEmptySubform) {
    // Case (a): Repair
    setRetrieverModel(fresh);
  }
  // Case (b): User customization — preserve as-is
}
```

**Design decisions**:
- No hardcoded component names (no `c.component === "TFIDFRetriever"`)
- Generic pattern match: `v.properties.params.comp.params` with 0 keys → empty ComponentField
- Only repairs when BOTH `deepEqual` fails AND empty subform exists
- Customized models have non-empty sub-params → correctly preserved

---

## 6. Helper Functions

### 6.1 `deepEqual(a, b)`

Order-independent recursive object comparison. Handles:
- `null`
- Non-object types (primitives)
- Arrays vs objects
- Different key lengths

**NOT** `JSON.stringify` because:
- Key order can differ between fresh defaults (sorted alphabetically by Python) and stored models (insertion order).
- `JSON.stringify({a:1,b:2}) !== JSON.stringify({b:2,a:1})` → false positive for "advanced".

### 6.2 `getEffectiveTopK(model)`

Extracts the logical top-K from a retriever model:

- **Unit retriever**: `model.params.top_k`
- **ParallelRetriever**: `sum(children[i].params.top_k)` — total documents retrieved across all children
- **SequentialRetriever**: `children[last].params.top_k` — final cascade output count

Returns `null` if model is incomplete.

### 6.3 `filterTopK(obj)`

```js
Object.fromEntries(Object.entries(obj || {}).filter(([k]) => k !== "top_k"))
```

Used inside `isAdvanced` to compare params excluding top_k, because top_k is a slider-controlled value that shouldn't trigger "advanced" state.

### 6.4 `buildDefaultValuesFromSchemaProperties(properties)`

Calls `normalizeParamsForSchema({}, properties)`. Reads `placeholder` from each schema property. For non-ComponentField types (string, number, enum), the placeholder is the default value. For ComponentField types, the placeholder is `{component, params: {}}` — hence why this function alone is insufficient for hybrid defaults.

### 6.5 `getInitialModelParameters({ selectedModel, currentModelName, currentParams })`

Priority:
1. If `currentModelName === selectedModel.name` and `currentParams` non-empty → use `currentParams` (preserve existing)
2. Else if `selectedModel.parameters` non-empty → use stored parameters
3. Else → `buildDefaultValuesFromSchemaProperties(selectedModel.schema.properties)`

Then always runs `normalizeParamsForSchema` to ensure ComponentField values have the `{properties: {component, params: {comp: {component, params}}}}` shape.

---

## 7. Backend-Frontend Contract

### 7.1 ComponentField Format

The backend schema system uses `component_field(parent="ModelType")` which generates:

```json
{
  "type": "object",
  "parent": "TFIDFVectorizerModel",
  "placeholder": {
    "component": "TFIDFVectorizerModel",
    "params": {}
  },
  "properties": {
    "component": { "type": "string" },
    "params": { "type": "object" }
  }
}
```

The frontend normalizes this to:

```json
{
  "properties": {
    "component": "TFIDFVectorizerModel",
    "params": {
      "comp": {
        "component": "TFIDFVectorizerModel",
        "params": { /* vectorizer params */ }
      }
    }
  }
}
```

### 7.2 `formattedModel` Resolution

`formattedModel(schema)`:
1. Iterates schema `properties`
2. For each property with `type: "object"` AND `parent`:
   - Calls `getComponents({ model: placeholder.component })` to fetch the sub-component schema
   - Recursively calls `formattedModel(subform.schema)`
   - Returns the resolved structure

### 7.3 Dense Retriever Encoding Contract

**Schema** (flat, no ComponentField for encoding):

```python
class HuggingFaceDenseRetrieverSchema(BaseSchema):
    model_name: schema_field(enum_field(HF_MODELS), ...)
    max_length: schema_field(int_field(ge=1), placeholder=512, ...)
    batch_size: schema_field(int_field(ge=1), placeholder=32, ...)
    device: schema_field(enum_field(["cpu", "cuda"]), ...)
    pooling_strategy: schema_field(enum_field(["mean", "cls", "max"]), ...)
    similarity_metric: schema_field(enum_field(METRICS), ...)
    top_k: schema_field(int_field(gt=0), placeholder=5, ...)
```

**`__init__` pattern**:
```python
def __init__(self, **kwargs):
    # Pop encoding params from kwargs
    model_name = kwargs.pop("model_name", "default")
    ...
    # Build embedding instance
    embedding = HuggingFaceEmbedding(model_name=model_name, ...)
    # Inject into kwargs
    kwargs["_embedding_model"] = embedding
    super().__init__(**kwargs)
```

**`DenseRetriever.__init__`**:
```python
def __init__(self, **kwargs):
    self.embedding_model = kwargs.pop("_embedding_model")
    super().__init__(**kwargs)
    # Clean self.params: keep only similarity_metric and top_k
    for key in list(self.params.keys()):
        if key not in ("similarity_metric", "top_k"):
            self.params.pop(key, None)
    # Store encoding info
    self.params["encoding_model"] = {
        "class_name": encoding_class.__name__,
        "parameters": dict(sorted(self.embedding_model.params.items())),
    }
```

**Factory contract** (`_ENCODING_CLASS`, `_ENCODING_PARAM_KEYS`):
```python
class HuggingFaceDenseRetriever(DenseRetriever):
    _ENCODING_CLASS = "HuggingFaceEmbedding"
    _ENCODING_PARAM_KEYS = ["model_name", "max_length", "batch_size", "device", "pooling_strategy"]
```

`RetrieverFactory._inject_encoding()` reads these class attributes:
- Constructs `encoding_model` dict from the specified param keys
- Injects it into `sorted_params` for DB lookup/save
- `_load_dense()` pops `encoding_model` from params before constructing model

---

## 8. Bug History & Fixes

### 8.1 Bug: `onFormSubmit={() => {}}` in `RetrieverNodeConfig`

**Symptom**: Editing child node parameters in CompositeRetrieverBuilder had no effect. Clicking "Save" on the node config dialog appeared to work but the parameters were not persisted.

**Root cause**: `RetrieverNodeConfig.jsx:161` had `onFormSubmit={() => {}}` — the auto-saving `FormSchema` was calling this no-op handler instead of updating `params` state. The save handler (`handleSave`) read `params` which was only initialized from `nodeData` and never updated by form changes.

**Fix**: Changed to `onFormSubmit={(values) => setParams(values)}`.

### 8.2 Bug: `enableReinitialize` + `initialValues` dependent on `retrieverModel`

**Symptom**: User edits a field in the advanced modal's form. Auto-save updates `retrieverModel.params`. This causes `initialValues` to change (because it had `retrieverModel.params` as a dependency). FormSchema re-initializes with the new (auto-saved) values, but the form's current values may differ from initialValues → loss of unsaved changes.

**Root cause**: `useMemo` dependency `[selectedRetriever, retrieverModel?.component, retrieverModel?.params]` — the form re-initialized on every auto-save.

**Fix**: `savedParamsRef` pattern. `initialValues` depends only on `[selectedRetriever]`. `savedParamsRef` is the single source of truth for the last saved state. On unmount, `saveCurrentFormValues()` reads `savedParamsRef.current` and updates `retrieverModel`.

### 8.3 Bug: `getComponents({ model })` destructured as array

**Symptom**: `resolveDefaults` returned `undefined` for all component defaults. Hybrid models were built with empty defaults → `isAdvanced` always true.

**Root cause**: `ResolvedSubformMenu.jsx` destructured the result of `getComponents({ model })` as `const [result]`, treating the return value as an array. But `getComponents({ model })` returns a single object `{ success, schema, ... }` when called with `model` parameter.

**Fix**: `const result = await getComponents({ model: modelName })` — no destructuring.

### 8.4 Bug: `buildHybridModel` with empty sub-defaults

**Symptom**: Hybrid models had children with `TFIDFVectorizer: { properties: { params: { comp: { params: {} } } } }` — empty innermost params.

**Root cause**: `buildDefaultValuesFromSchemaProperties` was used to build defaults but only reads `placeholder` from schema `properties`. For ComponentFields, the placeholder is `{component: "X", params: {}}` — always empty.

**Fix**: `resolveDefaults` uses `formattedModel` + `generateYupSchema` which recursively fetches sub-component schemas and resolves all nested defaults.

### 8.5 Bug: `alreadySelected` rebuilt model with fresh defaults

**Symptom**: User customized a hybrid model. Clicked the same preset card again. The model was rebuilt with fresh defaults, overwriting customizations.

**Root cause**: `selectGroup` had special-case logic for `alreadySelected` that called `buildHybridModel(topK, hybridDefaults)` → `setRetrieverModel(...)` before opening the modal.

**Fix**: Removed the rebuild logic from `alreadySelected` path. Now just opens the modal:

```js
if (alreadySelected) {
  setShowAdvanced(true);
  return;
}
```

### 8.6 Bug: Hardcoded component name in auto-repair

**Symptom**: Auto-repair only checked for `c.component === "TFIDFRetriever"`. Would fail for other component types or future additions.

**Fix**: Generic pattern check — walks all children, checks any value that has `v.properties.params.comp.params` with 0 keys.

---

## 9. Constraints & Known Limitations

1. **No streaming output** from LLMs — user waits for full response.
2. **Chunk similarity matrices in RAM** — fine for tens to low hundreds of documents, bottleneck for very large collections.
3. **`pairwise_distances` O(n×dim)** per query, no FAISS/HNSW indexing.
4. **Embedding matrices loaded via `np.load()`** into RAM.
5. **DB session held open** during entire job lifecycle including LLM inference (risk of connection timeout).
6. **`get_or_create_chunk_set`** does SELECT-then-INSERT without lock (safe for single-user).
7. **Hybrid model is hardwired** to TFIDF + HuggingFaceDense in `buildHybridModel`. Extending to support other combinations would require changing this function and the `API_GROUPS` resolution logic.
8. **Top-K splitting is always ceil/floor** for two children. No support for proportional or user-defined splits.
9. **`SequentialRetriever` must have strictly decreasing top_k** — enforced by backend validation. Frontend does not enforce this (user must configure manually).
10. **`getEffectiveTopK` for hybrid = sum of children's top_k**. Frontend slider uses this effective total, but backend children each have individual top_k — there's no single "top_k" field on ParallelRetriever itself.

---

## 10. State Transition Diagram

```
                    ┌─────────────────────────────────┐
                    │         Initial Load             │
                    │  fetch groups, resolve defaults  │
                    │  auto-repair if needed            │
                    │  sync selectedGroup from model   │
                    └────────────┬────────────────────┘
                                 │
                    ┌────────────▼────────────────────┐
                    │       isAdvanced = false         │
                    │  selectedGroup = "keyword"       │
                    │  PresetCard selected (amber)     │
                    │  Top-K slider visible            │
                    └───┬──────────────────┬──────────┘
                        │                  │
           Click another card        Click "Advanced" button
                        │                  │
             ┌──────────▼──────┐   ┌──────▼────────────────┐
             │ selectGroup()   │   │ setShowAdvanced(true) │
             │ rebuild model   │   │ → opens modal          │
             │ isAdvanced recalc│   └──────┬────────────────┘
             └──────────┬──────┘          │
                        │         User configures in modal
                        │         Click "Done" → saveFormValues()
                        │                  │
                        │         ┌────────▼──────────────┐
                        │         │ isAdvanced = true      │
                        │         │ PresetCards deselected  │
                        │         │ AdvancedConfigCard shown│
                        │         │ Top-K slider hidden     │
                        │         │ Amber chip: Top K: {n}  │
                        │         └────────┬──────────────┘
                        │                  │
                        │         Click another preset card
                        │         (isAdvanced → alreadySelected=false)
                        │                  │
                        └──────────────────┘
                                 │
                    ┌────────────▼────────────────────┐
                    │  Model rebuilt with defaults     │
                    │  isAdvanced recalculated          │
                    │  Top-K slider reappears          │
                    └─────────────────────────────────┘
```

---

## 11. Key Design Decisions Summary

| Decision | Rationale |
|----------|-----------|
| `deepEqual` recursive, not `JSON.stringify` | Order-independence for comparison. Key order differs between Python (sorted) and JS (insertion). |
| `filterTopK` in `isAdvanced` | Top-K is slider-controlled; custom top-K values should not trigger "advanced" state. Only non-topK parameter differences matter. |
| `savedParamsRef` instead of `FormSchemaInterceptor` | Cleaner separation: form auto-saves to ref, ref flushes to model on explicit save/close. No form re-initialization from auto-save. |
| `initialValues` dep only on `[selectedRetriever]` | Prevents form re-initialization on auto-save. The selected retriever is the trigger for fresh defaults. |
| `resolveDefaults` = `formattedModel` + `generateYupSchema` | Only mechanism that recursively resolves ComponentField sub-defaults. `buildDefaultValuesFromSchemaProperties` produces `{}` for nested fields. |
| Auto-repair uses generic pattern, not hardcoded names | Future-proof: works with any retriever that has ComponentField children with empty sub-params. |
| `alreadySelected` does NOT rebuild model | Preserves user customizations. The modal reads current state from `retrieverModel` via `RetrieverConfigurationStep`. |
| Flat encoding schema on dense retrievers | Encoding params are top-level fields, not nested `{encoding_model: {component, params}}`. Factory injects encoding info internally. |
| `_ENCODING_CLASS` + `_ENCODING_PARAM_KEYS` as class attrs | Declarative. Factory reads these generically — no `if isinstance` chains. |
| `SequentialRetriever` no `strategy` field | Only cascade mode. Eliminates invalid `accumulate` usage. Simplifies schema and validation. |
| `MergeStrategy.ROUND_ROBIN.value` in parallel descriptions | Avoids displaying `'MergeStrategy.ROUND_ROBIN'` (enum member repr) in frontend. Shows `'round_robin'` (the value). |
| Top-K default = 10 | Middle of `[3, 5, 10, 15, 20]` range. Good default for most RAG use cases. |
| Hybrid always `ParallelRetriever` with `round_robin` | `round_robin` interleaves results naturally. `interleave` preserves order but can bias toward a single retriever. |
