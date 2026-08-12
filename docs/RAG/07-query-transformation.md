# Query Transformation — Arquitectura y Plan

Este documento describe el diseño de la fase opcional de _query transformation_ en el pipeline RAG: una etapa que transforma la consulta del usuario (reescritura, expansión o descomposición) antes de la recuperación, con trazabilidad completa de las queries generadas y los chunks recuperados por cada una.

---

## Principios de diseño

- **Transparencia total.** El usuario configura explícitamente el LLM de transformación (sin fallback implícito) y ve cualquier error de salida del modelo.
- **Separación en capas.** El transformer es un componente puro de dominio (factory sin DB/FS); la persistencia del prompt y del LLM vive en `SetupService`.
- **Patrón probado.** El transformer referencia su prompt vía `component_field(parent="QueryTransformationPrompt")` (misma mecánica que el dense retriever referencia `DenseEmbedding`), resuelto por `fill_objects`.
- **Extensibilidad.** Estrategias como subclases de `BaseQueryTransformer` registradas en el `ComponentRegistry`, igual que la jerarquía `RetrieverModel`/`CompositeRetriever`.
- **Retrocompatibilidad.** Las claves de parámetros requeridas (`RAG_PARAM_KEYS`, `RAG_MODEL_KEYS`) no cambian; las nuevas son opcionales. Los outputs legacy (formato plano de chunks) siguen siendo reconocidos por el frontend.

---

## Alcance de la primera iteración

- **Estrategias implementadas:**
  1. **Reescritura / compresión** (`QueryRewritingTransformer`) — recibe la consulta + historial opcional y produce una única query reescrita.
  2. **Expansión multi-query** (`QueryExpansionTransformer`) — genera exactamente `n_queries` consultas; el LLM responde en JSON `{"queries": [...]}`.
  3. **Descomposición** (`QueryDecompositionTransformer`) — sin `n_queries` fijo; el LLM decide cuántas sub-queries descomponer.
- **LLM de transformación separado y obligatorio** (`query_transformation_llm`). Si la fase está activa, el LLM debe estar configurado explícitamente; si falta → error claro en validación (400) y defensa en `RAGPipelineConfig`. Sin fallback al LLM de generación.
- **Uso de la consulta transformada.** Alimenta solo la recuperación; el prompt de generación usa el mensaje original del usuario.
- **Trazabilidad persistente.** Las queries generadas y los chunks recuperados por cada una se guardan en la DB (`ProcessData`) y se muestran en la conversación.

---

## 1. Backend

### 1.1 Nuevas clases de Prompt

Subpaquete `DashAI/back/models/RAG/prompts/query_transformation/`:

```
prompts/query_transformation/
├── __init__.py
├── query_transformation_prompt.py       # QueryTransformationPrompt(Prompt) — base
├── default_query_rewriting_prompt.py    # DefaultQueryRewritingPrompt
├── default_query_expansion_prompt.py    # DefaultQueryExpansionPrompt
├── default_query_decomposition_prompt.py# DefaultQueryDecompositionPrompt
└── custom_query_transformation_prompt.py# CustomQueryTransformationPrompt
```

#### Jerarquía

```
Prompt
 └── QueryTransformationPrompt           required_placeholders = ["{input}"]
       ├── DefaultQueryRewritingPrompt   + {history}
       ├── DefaultQueryExpansionPrompt   + {n_queries}
       ├── DefaultQueryDecompositionPrompt + {history}
       └── CustomQueryTransformationPrompt  (template libre)
```

Cada implementación define:

- `SCHEMA` — `language` (enum en|es|pt), `template`.
- `metadata` — con `required_placeholders`, `placeholder_descriptions`, `templates` multidioma (misma estructura que los prompts de generación).
- `format(input, history=None, n_queries=None) -> str` — renderiza reemplazando placeholders.

`format` con `history=None` omite la sección de historial en el template. `PromptFactory`, `PromptService.validate_template` y el frontend (`PlaceholdersList`, `NewPromptModal`) funcionan sin cambios porque reutilizan la maquinaria `Prompt` existente.

#### Ejemplo: DefaultQueryExpansionPrompt

```
Eres un asistente de búsqueda. Genera {n_queries} consultas alternativas
para buscar información sobre la pregunta del usuario.

Pregunta: {input}

Responde en JSON exacto:
{"queries": ["consulta_1", "consulta_2", ..., "consulta_n"]}
```

### 1.2 Query Transformers (componentes del registry)

Subpaquete `DashAI/back/models/RAG/query_transformers/`:

```
query_transformers/
├── __init__.py
├── base_query_transformer.py            # BaseQueryTransformer(BaseModel, ABC)
├── query_rewriting_transformer.py       # QueryRewritingTransformer
├── query_expansion_transformer.py       # QueryExpansionTransformer
├── query_decomposition_transformer.py   # QueryDecompositionTransformer
├── query_transformer_factory.py         # QueryTransformerFactory  (puro)
└── query_parsing.py                     # parseo robusto + validación
```

#### BaseQueryTransformer

```
BaseQueryTransformer(BaseModel, ABC)
    ├── inject_llm(llm)                  # patrón inject_infra
    └── transform(query: str,
                  history: list[dict] | None = None) -> list[str]
```

Cada subclase define su `SCHEMA` con `component_field(parent="QueryTransformationPrompt")` para el prompt.

| Estrategia                      | Schema params                          | Contrato de salida                         |
| ------------------------------- | -------------------------------------- | ------------------------------------------ |
| `QueryRewritingTransformer`     | `prompt`, `use_history: bool`          | `list[str]` con exactamente 1 query        |
| `QueryExpansionTransformer`     | `prompt`, `n_queries: int_field(gt=0)` | `list[str]` con exactamente `n_queries`    |
| `QueryDecompositionTransformer` | `prompt`, `use_history: bool`          | `list[str]` con ≥1 (el LLM decide cuántas) |

#### QueryTransformerFactory

```
QueryTransformerFactory(registry, llm)
    └── create(component, params) -> QueryTransformerFactoryResult
```

Flujo puro (sin DB, sin FS):

1. `model_class.SCHEMA.model_validate(params)`
2. `fill_objects(validated, registry)` — resuelve el prompt anidado a instancia
3. `model = model_class(**resolved)`
4. `model.inject_llm(llm)`

Espejo exacto de `RetrieverFactory` (que resuelve `DenseEmbedding` anidado).

#### Parseo de salida del LLM (`query_parsing.py`)

- `json.loads` del output → extraer `"queries"`.
- Fallback: split por líneas, strip, filtro de vacías.
- **Nunca silencia errores**: si el LLM devuelve formato inválido, cantidad equivocada (expansión), o 0 queries (descomposición) → `RAGQueryTransformerOutputError` con el output crudo incluido. El error se propaga al job y se muestra en el chat de error.

### 1.3 Excepciones

`exceptions/query_transformation.py` (bajo `RAGWorkflowError`):

```
RAGQueryTransformationError          # base
 ├── RAGQueryTransformerOutputError  # parseo / cantidad inválida
 └── RAGQueryTransformationConfigError # fase activa sin LLM
```

Actualizar `exceptions/__init__.py`.

### 1.4 Constantes (`RAG_constants.py`)

```python
# Nuevas claves de parámetro (opcionales)
RAG_PARAM_QUERY_TRANSFORMATION_MODEL = "query_transformation_model"
RAG_PARAM_QUERY_TRANSFORMATION_LLM   = "query_transformation_llm"

# Claves de modelo opcionales ({component, params})
RAG_OPTIONAL_MODEL_KEYS = frozenset({
    RAG_PARAM_QUERY_TRANSFORMATION_MODEL,
    RAG_PARAM_QUERY_TRANSFORMATION_LLM,
})

# Todas las claves de sesión (requeridas + opcionales) — para whitelist del job
RAG_SESSION_PARAM_KEYS = RAG_PARAM_KEYS | RAG_OPTIONAL_MODEL_KEYS

# RAG_PARAM_KEYS      — NO cambia (documents + 4 modelos requeridos)
# RAG_MODEL_KEYS      — NO cambia (required component refs)
# RAG_PARAM_KEYS_ALL  — = RAG_INFRA_KEYS | RAG_SESSION_PARAM_KEYS
```

### 1.5 RAGPipelineConfig y RAGPipelineSchema

**RAGPipelineConfig** (dataclass tipada):

- `query_transformation_model: ModelRef | None = None`
- `query_transformation_llm: ModelRef | None = None`
- `from_kwargs`: si `query_transformation_model` presente pero `query_transformation_llm` ausente → `RAGPipelineConfigError` (defensa en profundidad; sin fallback).
- Parseo opcional: valida estructura `{component, params}` solo si la clave está presente.

**RAGPipelineSchema** (validación pydantic):

```python
query_transformation_model: schema_field(
    component_field(parent="BaseQueryTransformer"),
    placeholder=None,
    description=...,
) = None  # opcional con default None

query_transformation_llm: schema_field(
    component_field(parent="TextToTextGenerationTaskModel"),
    placeholder=None,
    description=...,
) = None
```

### 1.6 RAGPipeline — Orquestación y salida tipada

#### Dataclasses

```python
@dataclass(frozen=True)
class QueryRetrieval:
    """Una query de búsqueda y los chunks que recuperó."""
    query: str                         # texto de la query usada
    is_transformed: bool               # False si es la original sin transformación
    chunks: Dict[str, ChunkReference]  # {key: ChunkReference}

@dataclass(frozen=True)
class RAGGenerationOutput:
    message: str                       # respuesta generada
    chunks: Dict[str, ChunkReference]  # chunks fusionados/dedupeados (compat)
    queries: List[QueryRetrieval]      # NUEVO: trazabilidad query→chunks
```

#### Flujo `generate()`

```
input_data
  │
  ├── 1. Extraer input_message + history
  │
  ├── 2. Transformación (si fase activa)
  │      search_queries = transformer.transform(input_message, history)
  │      └── El error de transformación se propaga sin tragar
  │
  ├── 3. Recuperación multi-query (_retrieve_multi)
  │      Por cada query:
  │         chunks_q = single_interaction(query)
  │         QueryRetrieval(query, is_transformed, build_refs(chunks_q))
  │      Merge: deduplicar por (document_id, document_position)
  │             preservando orden inter-query, acotar a retrieval_top_k
  │             → chunks plano para compat
  │
  ├── 4. Prompt de generación
  │      prompt_model.format(input=input_message, chunks=chunks_text)
  │      │
  │      │  └── usa input_message ORIGINAL, nunca la transformada
  │
  └── 5. LLM generation → RAGGenerationOutput
```

`single_interaction(query)` se mantiene intacto.

### 1.7 RAGModelsFactory y SetupService

**RAGModelsFactory:**

```python
def create_query_transformer(
    self, component: str, params: dict, llm: TextToTextGenerationTaskModel
) -> QueryTransformerFactoryResult:
    return QueryTransformerFactory(self._registry, llm).create(component, params)
```

**SetupService.build_pipeline():**

```
si config.query_transformation_model:
    ├── Validar que config.query_transformation_llm existe
    │      └── si no → error (no se usa nunca el LLM de generación)
    ├── llm_result = self._llm.get_or_create(
    │       config.query_transformation_llm.component,
    │       config.query_transformation_llm.params
    │   )
    ├── transformer = models_factory.create_query_transformer(
    │       config.query_transformation_model.component,
    │       config.query_transformation_model.params,
    │       llm_result.model   # ← exclusivamente este LLM
    │   )
    ├── Persistir prompt anidado vía self._prompts.get_or_create(...)
    │      (para auditoría/reuso; opcional, sin nueva FK en la DB)
    └── Pasar transformer a _assemble_pipeline_instance
```

### 1.8 Validación (SessionValidationService)

- **Estructura de claves opcionales**: iterar `RAG_OPTIONAL_MODEL_KEYS`; si presentes → validar `{component, params}` (misma lógica que `_validate_model_keys` pero no requeridas).
- **Regla cruzada**: si `query_transformation_model` está presente y `query_transformation_llm` ausente → `ValueError("query_transformation_llm is required when query transformation is enabled.")`.
- **Prompt anidado**: validar template del prompt dentro de `query_transformation_model.params.prompt` con `PromptService.validate_component_ref`.
- `validate_component_refs` ya cubre los refs anidados recursivamente (sin cambios).

### 1.9 RAGJob whitelist

Cambiar `RAG_PARAM_KEYS` por `RAG_SESSION_PARAM_KEYS` en la línea de whitelist para no filtrar las claves opcionales.

### 1.10 Persistencia en DB (RAGTask.process_output)

Un único output `"Dict"` (metadata `outputs` intacta), con estructura versionada:

```json
{
  "version": 2,
  "chunks": {
    "12_3": {
      "document_id": 12,
      "document_name": "informe.pdf",
      "document_position": 3,
      "text": "contenido del chunk..."
    }
  },
  "queries": [
    {
      "query": "¿cuál es la política de privacidad según el informe 2023?",
      "is_transformed": true,
      "chunks": {
        "12_3": {...},
        "12_5": {...}
      }
    },
    {
      "query": "política de privacidad informe anual 2023",
      "is_transformed": true,
      "chunks": {
        "12_3": {...}
      }
    }
  ]
}
```

- `chunks` es el conjunto fusionado/dedupeado (compatible con el formato legacy).
- `queries` siempre presente (≥1 entrada). Sin transformación: `[{"query": mensaje_original, "is_transformed": false, "chunks": {...}}]`.
- Sesiones legacy → formato plano (sin `version` ni `queries`). El frontend detecta y cae en modo compatibilidad.

Outputs de `process_output`:

```
(message, "str")
(json_dumps(dict), "Dict")
```

### 1.11 Registro en `initial_components.py`

Añadir en `get_initial_components()`:

```python
from DashAI.back.models.RAG.prompts.query_transformation import (
    DefaultQueryRewritingPrompt,
    CustomQueryTransformationPrompt,
    DefaultQueryExpansionPrompt,
    DefaultQueryDecompositionPrompt,
)
from DashAI.back.models.RAG.query_transformers import (
    QueryRewritingTransformer,
    QueryExpansionTransformer,
    QueryDecompositionTransformer,
)
```

---

## 2. Frontend

### 2.1 Helpers en `api/rag.ts`

- `getPromptKind(className)` → `"generation" | "augmentation" | "query_transformation"` (basado en prefijos/clases explícitas). Reemplaza `isGenerationPromptClass`.
- `getDefaultPrompts(parent)` parametrizable (por defecto `"RAGGenerationPrompt"`).
- `getQueryTransformationPrompts()` → children de `QueryTransformationPrompt`.
- `getQueryTransformerComponents()` → children de `BaseQueryTransformer`.
- `getCustomPrompts` añade `"QueryTransformationPrompt"` al array de parents.

### 2.2 RAGSessionSetup

- `defaultSessionData.parameters` extendido con `query_transformation_model: {component: "", params: {}}` y `query_transformation_llm: {component: "", params: {}}`.
- Nueva `RAGCard` "Query Transformation" con toggle de habilitado.
- **No bloquea guardar** si la fase está deshabilitada.
- Las claves se incluyen en el payload solo cuando el toggle está activo.

### 2.3 QueryTransformationSection (nuevo)

Componente en `sections/QueryTransformationSection.jsx`:

- **Toggle** "Enable query transformation".
- **Selector de estrategia**: Autocomplete con children de `BaseQueryTransformer`.
- **Modal de configuración avanzada** (patrón `AdvancedConfigCard` + `FormSchema` como `RetrieverConfigurationStep`):
  - Prompt: selector filtrado a `QueryTransformationPrompt` (reutilizando lógica de `PromptSection` parametrizada).
  - `n_queries` (int, solo visible si la estrategia es `QueryExpansionTransformer`).
  - `use_history` (bool, solo visible si la estrategia es reescritura o descomposición).
- **Selector de LLM de transformación** (obligatorio cuando la fase está activa): autocomplete reutilizando `getGeneratorComponents`. Si falta → `isConfigurationComplete` y `validateConfiguration` bloquean con mensaje claro.

### 2.4 NewPromptModal

Dropdown de tipo de prompt con opciones: `CustomRAGGenerationPrompt` y `CustomQueryTransformationPrompt`, en lugar del valor hardcodeado actual.

### 2.5 PromptSection

Excluir prompts `query_transformation` del selector de generación usando `getPromptKind`.

### 2.6 Chat — Visualización de queries y chunks

#### Parsing en `GenerativeChat.jsx`

Al recibir la respuesta (output `"Dict"`):

```
parsedData = JSON.parse(data)
si parsedData.queries && Array.isArray(parsedData.queries)
    → formato nuevo (v2)
si no
    → formato legacy (SourcesDisplay existente)
```

#### RetrievalDisplay (nuevo componente)

Reemplaza `SourcesDisplay` en el renderizado del chat:

```
RetrievalDisplay
 ├── Si legacy (objeto plano) → SourcesDisplay (sin cambios)
 └── Si v2 → lista de queries:
      Por cada QueryRetrieval:
       ├── Header:
       │      "Query N" + texto de la query
       │      Badge: "transformed" / "original"
       └── SourcesDisplay por query:
              Agrupa chunks por documento
              Botón "View chunks" → DocumentReferencesModal
```

Se extrae el renderizado interno de `SourcesDisplay` (lista de documentos con sus chunks) a un sub-componente `DocumentChunkList` reutilizable tanto en modo legacy como dentro de `RetrievalDisplay`.

#### Visualización siempre presente

Incluso sin transformación activa, `RetrievalDisplay` muestra la query original + sus chunks. La estructura `queries` siempre tiene ≥1 entrada (la o las queries usadas para recuperar), con `is_transformed: false` para la original.

### 2.7 i18n

Nuevas claves en `generative.json` (en, es, pt, de, zh):

- `rag.queryTransformation.title`, `.description`, `.enableToggle`, `.strategyLabel`, `.promptLabel`, `.llmLabel`, `.llmRequired`, `.nQueries`, `.useHistory`, `.advancedConfig`
- `rag.retrieval.queryLabel`, `.originalQuery`, `.transformedQuery`, `.queriesTitle`, `.chunksPerQuery`

---

## 3. Tests

### Backend (`tests/back/RAG/`)

| Área                        | Verificaciones                                                                                                                                                                                                 |
| --------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Prompts                     | Formato, placeholders requeridos, `history=None` omite sección, validación de template                                                                                                                         |
| Transformers (LLM mockeado) | Rewriting: strip comillas, vacío → error; Expansion: n exacto; mismatch/parseo → error con raw output; Decomposition: n libre ≥1, 0 → error; parseo fallback por líneas                                        |
| Factory                     | Resolución prompt anidado, inyección LLM, error si componente no registrado                                                                                                                                    |
| RAGPipelineConfig           | Fase activa sin LLM → `RAGPipelineConfigError`; sin fase → OK; estructura opcional inválida → error                                                                                                            |
| Pipeline                    | Sin transformer → output `queries=[original]`, chunks plano idéntico al actual; Multi-query → `QueryRetrieval` por query, merge dedupe acotado a top_k; Errores de transformación se propagan (no silenciados) |
| RAGTask                     | `process_output` produce estructura v2; formato legacy sigue parseable                                                                                                                                         |
| Validación POST/PUT         | Cross-field: transformer sin LLM → 400; prompt anidado validado; claves opcionales ausentes OK                                                                                                                 |
| Regresión                   | `pytest tests/` completo                                                                                                                                                                                       |

### Frontend

- `getPromptKind` clasifica correctamente generation / augmentation / query_transformation.
- Parser del chat: detecta v2 vs legacy sin errores.
- Sección opcional no bloquea guardado; fase activa sin LLM sí bloquea.

---

## 4. Migración de datos

- **No requiere migración de esquema** (no hay nuevas tablas ni columnas FK).
- Los outputs legacy (formato plano de chunks) son reconocidos por el frontend vía detección de formato (`"queries"` ausente → modo compatibilidad).
- Las nuevas sesiones generan outputs v2 que incluyen `version`, `chunks` (compat) y `queries`.
- La columna `ProcessData.data_type` sigue siendo `"Dict"`. El cambio es solo en la estructura del JSON interno.

---

## 5. Flujo end-to-end

```
┌─ Session Setup ────────────────────────────────────────────────────┐
│ Toggle → Estrategia → Prompt → LLM (obligatorio si activa) → Save  │
└────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─ POST /api/v1/generative-session/ ─────────────────────────────────┐
│ ValidationService:                                                  │
│   · Estructura {component, params} (opcional)                       │
│   · Regla cruzada: transformer → requiere LLM                       │
│   · Template del prompt anidado                                     │
│   · validate_component_refs recursivo                               │
└────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─ POST /api/v1/generative-process/ ──────────────────────────────────┐
│ RAGJob → SetupService.build_pipeline:                               │
│   1. llm_service.get_or_create(transformation_llm)  — sin fallback  │
│   2. models_factory.create_query_transformer(..., llm)               │
│   3. prompts.get_or_create(transformation_prompt)                    │
│   4. RAGPipeline(query_transformer=...)                              │
└────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─ RAGPipeline.generate() ────────────────────────────────────────────┐
│   1. input_message + history                                         │
│   2. transformer.transform(msg, history)  →  [q1, q2, ...]          │
│   3. _retrieve_multi([q1, q2, ...]):                                │
│        q1 → retriever.retrieve → ChunkReference dict                │
│        q2 → retriever.retrieve → ChunkReference dict                │
│        Merge dedupe (document_id, position) → chunks plano           │
│   4. prompt_model.format(input=input_message_original, ...)          │
│   5. llm.generate(...)                                               │
│   6. RAGGenerationOutput(message, chunks, queries)                   │
└────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─ RAGTask.process_output() ──────────────────────────────────────────┐
│   (message, "str")                                                   │
│   ({"version":2, "chunks":{...}, "queries":[...]}, "Dict")         │
└────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─ Chat UI ───────────────────────────────────────────────────────────┐
│ GenerativeChat: parse Dict → detecta queries array                   │
│ RetrievalDisplay:                                                    │
│   Query 1 "reescrita..." [badge: transformed]                        │
│     ├─ informe.pdf (2 chunks)    [View chunks]                       │
│   Query 2 "expansión..." [badge: transformed]                        │
│     └─ informe.pdf (1 chunk)     [View chunks]                       │
└────────────────────────────────────────────────────────────────────┘
```

---

## 6. Fuera de alcance

Implementaciones futuras que la arquitectura soporta sin cambios estructurales:

- **HyDE** (Hypothetical Document Embeddings) — nueva subclase de `BaseQueryTransformer`.
- **Corrective RAG** — re-evaluación de relevancia + re-retrieval.
- **MergeStrategy avanzado** (re-ranking sobre el merge de multi-query) — hoy merge simple con dedupe.
- **Nuevas tablas DB** para persistir la estrategia del transformer (hoy el config vive en el JSON de parámetros de sesión; las queries viven en `ProcessData`).

El contrato `transform(query, history) -> list[str]` y `QueryTransformerFactory` permiten añadir nuevas estrategias registrándolas en el `ComponentRegistry` + `initial_components.py`, sin tocar el pipeline ni el setup.

---

## Referencias

- [02-backend-architecture.md](./02-backend-architecture.md) — arquitectura general del backend RAG
- [04-execution-flow.md](./04-execution-flow.md) — flujo de ejecución paso a paso
- [06-future-work.md](./06-future-work.md) — trabajo futuro (query transformation ya no aparece aquí)
