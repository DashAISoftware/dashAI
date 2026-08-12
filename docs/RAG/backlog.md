# Sesión 1: refactor de validación RAG

## Objetivo

Revisar el proceso de creación de una sesión RAG y eliminar la carga de
validación que residía en el endpoint, aplicando principios SOLID y
manteniendo la mantenibilidad del módulo RAG.

**Problema detectado:** el endpoint `POST /api/v1/generative-session/`
contenía ~60 líneas de validación RAG _inline_ (documentos, resolución de
`prompt_id`, validación de component refs y template de prompt), duplicando
lógica que ya existía en `RAGSetupService.validate_update_payload()` (usado
en el PUT). Cualquier cambio en las reglas de validación requería modificar
dos lugares, y `RAGSetupService` mezclaba dos responsabilidades: validación
y ensamblado de pipeline.

## Archivos modificados

| Archivo                                                  | Acción                                                                                                                                                                                                                        |
| -------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DashAI/back/services/RAG/session_validation_service.py` | **Creado** — nuevo `RAGSessionValidationService` con `prepare_RAG_params()` (POST) y `validate_update_payload()` (PUT). Originalmente `rag_session_validation_service.py`, renombrado por convención de nombres.              |
| `DashAI/back/services/RAG/setup_service.py`              | **Creado** — `SetupService` con única responsabilidad: `build_pipeline()`. Reemplaza a `RAG_setup_service.py`.                                                                                                                |
| `DashAI/back/services/RAG/RAG_setup_service.py`          | **Eliminado** — se renombró a `setup_service.py` y se extrajo la validación.                                                                                                                                                  |
| `DashAI/back/api/api_v1/endpoints/generative_session.py` | **Modificado** — el POST delega la validación RAG a `RAGSessionValidationService.prepare_RAG_params()`; el PUT pasa de `RAGSetupService.validate_update_payload()` a `RAGSessionValidationService.validate_update_payload()`. |
| `DashAI/back/job/RAG_job.py`                             | **Modificado** — import actualizado a `SetupService` desde `setup_service`.                                                                                                                                                   |

## Estado alcanzado

1. **Nuevo `RAGSessionValidationService`** — centraliza toda la validación de
   parámetros de sesión RAG:
   - `prepare_RAG_params()` — para creación (POST). Todas las keys de modelo
     (`prompt`/`prompt_id`, `chunking_model`, `retriever_model`,
     `generation_model`) y `documents` son obligatorias. Resuelve `prompt_id`
     → `prompt` _antes_ de la validación estructural.
   - `validate_update_payload()` — para actualización parcial (PUT). Solo
     valida las keys presentes en el payload.
   - Helpers privados compartidos: `_validate_model_keys(require_all=...)`,
     `_validate_documents()`, `_resolve_prompt()`.

2. **`SetupService`** (antes `RAGSetupService`) — quedó con una única
   responsabilidad: ensamblar el pipeline (`build_pipeline()`). Ya no tiene
   lógica de validación.

3. **Endpoints delgados** — `POST` y `PUT` son delegadores puros hacia el
   service de validación. La lógica de negocio RAG ya no vive en la capa HTTP.

4. **Nombres consistentes** — se eliminó el prefijo `RAG_` del archivo
   `setup_service.py` (era el único en `services/RAG/` con ese prefijo) y toda
   referencia a `rag` en minúscula pasó a `RAG` mayúscula, por instrucción
   explícita del equipo.

## Diagrama final

```
POST /generative-session/            PUT /generative-session/{id}/parameters
         │                                       │
         ▼                                       ▼
RAGSessionValidationService             RAGSessionValidationService
  └─ prepare_RAG_params()                └─ validate_update_payload()
       (validación completa)                 (validación parcial)


RAG_job.run()
  └─ SetupService.build_pipeline()
       (solo assembly, sin validación)
```

## Verificación

- **Imports**: `RAGSessionValidationService`, `SetupService` y el router del
  endpoint cargan correctamente.
- **Tests**: 142/142 pasaron (7 de `tests/back/api/test_session_api.py` +
  135 de `tests/back/RAG/`). Cero regresiones.
- **Nota**: `test_app_front` falla por un problema **pre-existente** de
  migración Alembic (`No such revision or branch 'e7f8a9b0c1d2'`), no
  relacionado con este refactor.

## Decisiones y hallazgos relevantes

- **Bug corregido durante el refactor**: `prepare_RAG_params()` fallaba al
  recibir `prompt_id` (entero) en vez de `prompt` (component ref), porque la
  validación estructural corría antes de la resolución. Se resolvió moviendo
  la conversión `prompt_id → prompt` al inicio del método. El caso estaba
  cubierto por `test_update_generative_session_params_merges_and_logs_history`.
- **Validación de creación vs. actualización**: la única diferencia real es
  la estrictez (`require_all=True` para POST, `False` para PUT y documents
  condicionales). El resto de la lógica es idéntica.
- **Pendiente de decisión**: se propuso unificar los dos métodos públicos vía
  un helper privado `_validate(params, require_all)` para reducir duplicación
  de los pasos comunes (component refs, documents, prompt). No se implementó;
  quedó en discusión.

## Reglas de convención acordadas en esta sesión

- Los módulos en `services/RAG/` no llevan prefijo `RAG_` en el nombre del
  archivo (ej. `setup_service.py`, `session_validation_service.py`,
  `document_service.py`).
- La sigla **RAG** va siempre en mayúscula en nombres de clases, métodos y
  referencias (ej. `prepare_RAG_params`, `RAGSessionValidationService`).

---

# Sesión 2: clasificación de modelos e implementación de cross-encoders (SBERT)

## Objetivo

1. **Documentar la clasificación de modelos** de retrievers y embeddings del
   módulo RAG: revisar cada `model_name` del código y determinar su tipo
   (bi-encoder, cross-encoder u otro), detallando en la documentación una
   tabla con _model name_, _type_ y _reference_ (link a la documentación
   oficial).
2. **Implementar retrievers cross-encoder de SBERT**: crear una clase
   abstracta `CrossEncoderRetriever` y una implementación concreta
   `SentenceTransformerCrossEncoderRetriever` que envuelve los modelos
   `CrossEncoder` de `sentence-transformers`.

**Contexto previo:** DashAI solo tenía retrievers sparse (BM25, TF-IDF),
dense (embeddings bi-encoder) y compuestos (Sequential, Parallel, MMR
Reranker). No existía ningún cross-encoder — los cross-encoders procesan
pares (query, documento) de forma conjunta y devuelven un score de relevancia,
a diferencia de los bi-encoders que codifican cada texto por separado.

## Archivos modificados

| Archivo                                                                                 | Acción                                                                                                                                                                                                                                                                                               |
| --------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `docs/RAG/01-overview.md`                                                               | **Modificado** — se añadió la sección "Model Type Classification" (tabla con 67 entradas clasificadas: 55 bi-encoders, 2 embeddings estáticos FastText, retrievers sparse/composite/dense y luego los 18 cross-encoders); se actualizó el resumen de Component Types y la tabla de Retriever Models. |
| `DashAI/back/models/RAG/retrievers/cross_encoder/cross_encoder_retriever.py`            | **Creado** — clase abstracta `CrossEncoderRetriever(CompositeRetriever, ABC)`. Define la interfaz `_cross_score()` y la lógica de re-ranking sobre un child retriever.                                                                                                                               |
| `DashAI/back/models/RAG/retrievers/cross_encoder/sentence_transformer_cross_encoder.py` | **Creado** — clase concreta `SentenceTransformerCrossEncoderRetriever` + schema. Contiene el catálogo `CROSS_ENCODER_MODELS` (18 modelos) y el uso de `sentence_transformers.CrossEncoder`.                                                                                                          |
| `DashAI/back/models/RAG/retrievers/cross_encoder/__init__.py`                           | **Creado** — re-exports del submódulo (`CrossEncoderRetriever`, `SentenceTransformerCrossEncoderRetriever`).                                                                                                                                                                                         |
| `DashAI/back/models/RAG/retrievers/__init__.py`                                         | **Modificado** — se añadieron los nuevos re-exports de `cross_encoder`.                                                                                                                                                                                                                              |
| `DashAI/back/initial_components.py`                                                     | **Modificado** — se registró `SentenceTransformerCrossEncoderRetriever` en `get_initial_components()`.                                                                                                                                                                                               |

## Estado alcanzado

1. **Tabla de clasificación de modelos** en `docs/RAG/01-overview.md`:
   - Se auditaron los 55 `model_name` de embeddings (BERT, DistilBERT,
     RoBERTa, E5, Gemma, Instructor, LaBSE, OpenAI, SentenceTransformer,
     Harrier, Qwen3) — todos bi-encoders.
   - Se documentaron también los 2 embeddings estáticos FastText (presentes
     en el código pero **no registrados** en el UI), los retrievers
     sparse/composite/dense, y posteriormente los 18 cross-encoders.
   - **Hallazgo:** en la primera revisión no existía ningún cross-encoder en
     DashAI; solo tras la implementación de esta sesión se incorporaron.

2. **`CrossEncoderRetriever`** — clase abstracta que extiende
   `CompositeRetriever` (porque re-ranking requiere un child retriever de
   primera etapa):
   - Params: `retrieval_factor` (multiplicador de candidatos) y `top_k`.
   - `retrieve()` recupera `top_k × retrieval_factor` candidatos del child,
     los re-escora con `_cross_score()` (abstracto) y devuelve los `top_k`
     mejores ordenados por relevancia descendente.
   - `score_chunks()` delega al child retriever (compatibilidad con
     workflows compuestos como MMR).

3. **`SentenceTransformerCrossEncoderRetriever`** — implementación concreta:
   - **18 modelos** cross-encoder de SBERT organizados por dominio: MS MARCO
     passage ranking (MiniLM-L-4/6/12, TinyBERT-L-2, ELECTRA-base), MS MARCO
     multilingual (`mmarco-mMiniLMv2-L12-H384-v1`), STS (roberta-base,
     distilroberta, TinyBERT-L-4, roberta-large), Quora (distilroberta,
     roberta), NLI (distilroberta, roberta, deberta-v3-base/xsmall,
     MiniLM2-L6-H768).
   - `load()` carga el modelo de forma perezosa vía `CrossEncoder(...)`
     (con `max_length` desde el catálogo); `_cross_score()` construye los
     pares `(query, chunk.text)` y llama a `predict()`.
   - El componente fue **registrado** en `initial_components.py`, por lo que
     queda disponible en el UI y vía ComponentRegistry como cualquier otro
     retriever.

## Diagrama final

```
RetrieverModel
└── CompositeRetriever (ABC)
    └── CrossEncoderRetriever (ABC)                        ← NUEVO
        └── SentenceTransformerCrossEncoderRetriever       ← NUEVO (18 modelos SBERT)

Uso (patrón re-ranker):
  config = {
      "model_name": "cross-encoder/ms-marco-MiniLM-L-6-v2",
      "retrieval_factor": 3,
      "top_k": 5,
      "children": [{"component": "BM25Retriever", "params": {...}}],
  }
  → child recupera 15 candidatos → cross-encoder reordena → top 5
```

## Verificación

- **Ruff check**: los archivos nuevos y modificados pasan `ruff check`
  (la única corrección fue `# noqa: N803` para `env_RAG_path` y un import
  largo en `initial_components.py`).
- **Ruff format**: aplicado a los archivos nuevos.
- **Nota**: la importación del módulo requiere `sentence-transformers`
  (ya declarado en `requirements.txt`); no está instalado en el entorno de
  desarrollo local, por lo que la verificación de imports en vivo no fue
  posible.

## Decisiones y hallazgos relevantes

- **`CrossEncoderRetriever` extiende `CompositeRetriever`, no `UnitRetriever`**:
  los cross-encoders son demasiado costosos para escorar todo el corpus, por
  lo que se usan como _re-rankers_ sobre una primera etapa rápida (BM25,
  bi-encoder). Esto es análogo a `MMRRerankerRetriever`.
- **Convención de nombres**: la clase inicialmente se llamó
  `SentenceTransformerCrossEncoder`, pero se renombró a
  `SentenceTransformerCrossEncoderRetriever` por solicitud explícita del
  equipo, para dejar explícito que es un retriever (y distinguirla de la
  familia de embeddings). El schema se renombró en consecuencia
  (`SentenceTransformerCrossEncoderRetrieverSchema`). El nombre del archivo
  se mantuvo (`sentence_transformer_cross_encoder.py`).
- **Sin dependencias nuevas**: `CrossEncoder` forma parte del paquete
  `sentence-transformers`, que ya era dependencia de DashAI.
- **Interfaz `score_chunks`**: devuelve distancias (menor = más relevante,
  convención de bi-encoders). Los cross-encoders devuelven _scores_ (mayor =
  más relevante), por lo que `retrieve()` ordena descendente y `score_chunks`
  delega al child para no romper la convención existente.
- **Pendiente**: no existen tests unitarios dedicados para ningún retriever
  (solo tests de integración que referencian los componentes por nombre).
  Quedó pendiente añadir tests para el `SentenceTransformerCrossEncoderRetriever`.

---

# Sesión 3: funciones faltantes del cross-encoder reranker

## Objetivo

Revisar la implementación del cross-encoder reranker (creada en la Sesión II)
e implementar las funciones que faltaban para hacerlo **intercambiable y
componible** con el resto de retrievers (BM25, dense, MMR, Sequential,
Parallel). El alcance se confirmó con el equipo:

1. `retrieve()` debe aceptar un `top_k` opcional; si no se pasa, se usa el
   `top_k` configurado del `CrossEncoderRetriever` (el K final del re-ranker).
2. `get_chunk_vectors()` — delegando al child, para que un `MMRRerankerRetriever`
   pueda envolver un cross-encoder sin `AttributeError`.
3. `init_model()` → `load()`, consistente con el ciclo de vida del resto de
   retrievers (`init_model() -> retrieve()`).
4. `score_chunks()` debe puntuar de verdad con el modelo cross-encoder (ya no
   delegar al child), devolviendo `(chunk_id, distance)` ordenados ascendente.
5. `save()`/`load()` definidos con `raise NotImplementedError` en la base
   abstracta (contrato explícito, sin romper la carga real del modelo HF).
6. Sin funciones adicionales: basta con que sea intercambiable/componible.

**Contexto:** el código del cross-encoder existía desde la Sesión II (sin
commit, en la rama `RAG`), pero con `score_chunks()` delegando al child y sin
soporte de override de `top_k`, ni `get_chunk_vectors`, ni `init_model()`, ni
tests dedicados.

## Archivos modificados

| Archivo                                                                                 | Acción                                                                                                                                                                                                                                                                                                                                                                                                                            |
| --------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DashAI/back/models/RAG/retrievers/cross_encoder/cross_encoder_retriever.py`            | **Modificado** — `retrieve(query, top_k=None, **kwargs)` con override y guards (`top_k` entero ≥ 1, `retrieval_factor` entero ≥ 1, `children` no vacío); `score_chunks()` real (resuelve IDs en `chunks` inyectado, convierte logits a distancia `[0,1]` con `1 - sigmoid`, ordena ascendente); `get_chunk_vectors()` delegando al child con guard; `init_model()` → `load()`; `save()`/`load()` con `raise NotImplementedError`. |
| `DashAI/back/models/RAG/retrievers/cross_encoder/sentence_transformer_cross_encoder.py` | **Modificado** — `load(filename="")` alineada a la firma base; `activation_fn=nn.Identity()` (logits crudos para todos los modelos); validación de `model_name` contra el catálogo **antes** de descargar de HuggingFace; colapso de salida multiclase NLI a la columna `entailment` (`score_index: 1`); `_cross_score` con manejo de error completo.                                                                             |
| `DashAI/back/models/RAG/RAG_constants.py`                                               | **Modificado** — `COMPOSITE_RETRIEVER_NAMES` ahora incluye `MMRRerankerRetriever` y `SentenceTransformerCrossEncoderRetriever` (necesario para el cleanup en cascada). El set ya existía en el WIP del branch con Sequential/Parallel.                                                                                                                                                                                            |
| `DashAI/back/models/RAG/retrievers/composite/mmr_reranker_retriever.py`                 | **Modificado** — el fallback de vectores ahora captura `(ValueError, RAGRetrieverError)` en lugar de solo `ValueError`.                                                                                                                                                                                                                                                                                                           |
| `DashAI/back/services/RAG/cleanup_service.py`                                           | **Modificado** — fix del filtro SQLAlchemy `.filter(a and b)` (entre ColumnElements descartaba la exclusión de la sesión actual, dejando el cleanup sin correr nunca); `_sort_params` ahora canoniza dicts y listas recursivamente (comparación insensible al orden de claves/lista).                                                                                                                                             |
| `docs/RAG/01-overview.md`                                                               | **Modificado** — corrección del conteo: "18 cross-encoder models" → **17** (conteo real del catálogo `CROSS_ENCODER_MODELS`).                                                                                                                                                                                                                                                                                                     |
| `tests/back/RAG/test_cross_encoder_retriever.py`                                        | **Creado** — 21 tests unitarios (override de `top_k`, `score_chunks`, guards, colapso NLI, MMR fallback, comparación de config en cleanup). Resuelve el pendiente de tests de la Sesión II.                                                                                                                                                                                                                                       |

## Estado alcanzado

1. **`retrieve(query, top_k=None)`** — override opcional; usa el `top_k`
   configurado del `CrossEncoderRetriever` como default. El child recupera
   `top_k × retrieval_factor` candidatos y el re-ranker devuelve los mejores
   `top_k`. Guards en runtime para `top_k`/`retrieval_factor` inválidos y
   `children` vacío.

2. **`score_chunks()` real** — resuelve los `chunk_ids` vía el dict `chunks`
   inyectado (levanta `RAGRetrieverError` si la infraestructura no está
   inyectada), puntúa los pares con el cross-encoder y devuelve
   `(chunk_id, distance)` con distancia `[0,1]` (`1 - sigmoid(logit)`, menor =
   más relevante) ordenados ascendente.

3. **`get_chunk_vectors()`** — delega al child (guard si el child no lo
   soporta), lo que habilita composiciones `MMR → CrossEncoder`.

4. **`init_model()`** — llama a `load()`, alineando el ciclo de vida con el
   resto de retrievers.

5. **Contrato de persistencia explícito** — `save()`/`load()` en la base
   abstracta lanzan `NotImplementedError`; `load()` real en la concreta.

6. **Endurecimiento por QA (ml-tester + flow-tester)**:
   - Logits crudos garantizados (`activation_fn=nn.Identity()`); corrige el
     doble sigmoide que comprimía distancias y distorsionaba MMR/Parallel.
   - Modelos NLI (3 etiquetas) colapsados a la columna `entailment`.
   - `model_name` validado contra el catálogo antes de cualquier descarga HF.
   - MMR cae a top-k cuando el child no provee vectores.
   - Cleanup: comparación de config insensible al orden (protección de
     recursos compartidos entre sesiones).
   - `COMPOSITE_RETRIEVER_NAMES` completo para el routing de cleanup.

## Verificación

- **Ruff**: `ruff check` y `ruff format --check` limpios en todos los archivos
  modificados/creados.
- **Imports**: `CrossEncoderRetriever`, `SentenceTransformerCrossEncoderRetriever`
  y `MMRRerankerRetriever` cargan correctamente.
- **Tests nuevos**: `pytest tests/back/RAG/test_cross_encoder_retriever.py -v`
  → **21 passed** (default/override de `top_k`, guards, `score_chunks` con
  distancias ordenadas, colapso multiclase NLI, guard de `model_name`
  desconocido, fallback de MMR, comparación de configs en cleanup).
- **Suite RAG amplia**: `pytest tests/back/RAG/` → **94 passed** (sin
  regresiones). Además verdes según QA: `test_RAG_session_flow.py` (19),
  prompts (77) y configs de componentes/pipeline (39).

## Decisiones y hallazgos relevantes

- **`activation_fn=nn.Identity()`**: sentence-transformers ≥ 3.0 aplica Sigmoid
  por defecto a modelos de una etiqueta sin activación declarada en su config
  (STS, Quora, `ms-marco-electra-base`), por lo que `predict()` devolvía
  probabilidades y no logits. Con Identity, `predict()` devuelve logits crudos
  para todos los modelos y la conversión `1 - sigmoid(logit)` es correcta.
- **Modelos NLI multiclase**: devuelven `(n, 3)` logits; se colapsan a la
  columna `entailment` vía `"score_index": 1` en el catálogo. Sin esto,
  `score_chunks` crasheaba (`TypeError`) y `retrieve` rankeaba mal en silencio.
- **Validación runtime vs. schema**: la ruta compuesta (`_setup_composite` /
  `_create_composite`) no valida params contra `SCHEMA`, así que los bounds del
  schema (`model_name` enum, `retrieval_factor gt=1`, `top_k`) no se aplican en
  esa ruta. Se añadieron guards en `load()`/`retrieve()` para mitigar lo más
  peligroso (descarga arbitraria de repos HF por typo, `top_k` inválido). El
  fix arquitectónico (validar params compuestos contra SCHEMA) queda pendiente.
- **`COMPOSITE_RETRIEVER_NAMES` por strings**: es frágil; si se registra un
  retriever compuesto nuevo y no se añade al set, el cleanup lo tratará como
  unit y dejará los hijos huérfanos. Alternativa pendiente: derivar el set del
  registry vía `issubclass(model_class, CompositeRetriever)`.
- **Corrección de conteo**: el catálogo tiene **17** modelos (no 18 como decía
  la doc). La tabla de `01-overview.md` se corrigió.
- **Nota de proceso**: un subagente modificó sin autorización `AGENTS.md` y
  `CLAUDE.md` (documentación del endpoint `/api/v1/jobs`); se revirtió para
  mantener el alcance de la sesión.

## Pendientes detectados (fuera de alcance de esta sesión)

- **Validación de esquema en la ruta compuesta** (arquitectónico, afecta a
  todos los compuestos: Sequential, Parallel, MMR, CrossEncoder).
- **Cleanup service** (pre-existente en el WIP):
  - La limpieza de chunking compara JSON crudo en DB, sensible al orden de
    claves (`H1`).
  - La limpieza compuesta no elimina recursos de embedding de hijos densos
    (`RAGEmbeddingMatrix`/`RAGEmbeddingModel`/folders) (`H2`).
  - SQLite sin `PRAGMA foreign_keys=ON` (los `ondelete="CASCADE"` son inertes).
  - Composites anidados solo se limpian un nivel; las filas bridge de los
    hijos quedan huérfanas.
  - `DELETE` de sesión no elimina la fila `RAGPipeline`.
- **Menores del cross-encoder**: sin tope máximo a `expanded_k`, `score_chunks`
  con ids duplicados repite puntuación, `load()` no es thread-safe, `chunk_map`
  se reconstruye por llamada.

---

# Sesión 4: eliminación de `retrieval_factor` en re-rankers (cross-encoders y MMR)

## Objetivo

Corregir un error de diseño en los re-rankers del módulo RAG: el parámetro
`retrieval_factor` multiplicaba el `top_k` del re-ranker para decidir cuántos
candidatos recuperar del child (`top_k × retrieval_factor`). La cantidad de
candidatos que recupera el **ranker** (child retriever de primera etapa) debe
ser configuración propia de ese child (su propio `top_k`); el **reranker**
(cross-encoder) solo debe tener `top_k` (cuántos de los chunks ya recuperados
seleccionar tras el re-rank) y sus propios parámetros de modelo (ej.
`model_name` en el cross-encoder de SentenceTransformer). Por decisión del
equipo, el mismo fix se aplicó también a `MMRRerankerRetriever`.

**Terminología acordada en esta sesión:**

- **ranker** = child retriever que hace la primera recuperación.
- **reranker** = cross-encoder (o MMR) que hace el re-rank.

## Archivos modificados

| Archivo                                                                                 | Acción                                                                                                                                                                                                                                                                                                                                                                                                        |
| --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DashAI/back/models/RAG/retrievers/cross_encoder/cross_encoder_retriever.py`            | **Modificado** — se eliminó el atributo `retrieval_factor` de `__init__` (solo queda `top_k`) y su validación en `retrieve()`; `retrieve()` ahora llama `child.retrieve(query)` **sin override de `top_k`** (el child usa su propio `top_k` configurado). El docstring de la clase documenta la separación de responsabilidades ranker/reranker.                                                              |
| `DashAI/back/models/RAG/retrievers/cross_encoder/sentence_transformer_cross_encoder.py` | **Modificado** — se eliminó el campo schema `retrieval_factor`; se actualizaron el docstring del schema, el ejemplo de config del docstring de la clase (el child define su propio `top_k`, ej. 15 candidatos) y el docstring de `__init__`.                                                                                                                                                                  |
| `DashAI/back/models/RAG/retrievers/composite/mmr_reranker_retriever.py`                 | **Modificado** — mismo fix en MMR: se eliminó el campo schema `retrieval_factor`, el atributo y su uso en `retrieve()` (`candidates = child.retrieve(query)` sin override); docstrings actualizados. Bonus de consistencia: `score_chunks()` ahora tiene type hints y el docstring de `retrieve()` documenta `Raises`.                                                                                        |
| `tests/back/RAG/test_cross_encoder_retriever.py`                                        | **Modificado** — se quitó `retrieval_factor=2` de todos los constructores; aserciones de `child.retrieve_calls` actualizadas a `("query", None)`; se eliminó `test_retrieve_rejects_invalid_retrieval_factor`; `_FakeChildRetriever` ganó un `default_top_k` opcional (el child respeta su propio top-k cuando no hay override); nuevo test que demuestra que el top-k del child acota el conjunto candidato. |
| `tests/back/RAG/test_RAG_component_api_configs.py`                                      | **Modificado** — tests MMR (`test_ranking_mmr_reranker`, `test_topk_mmr_12`) sin `retrieval_factor`; docstrings actualizados.                                                                                                                                                                                                                                                                                 |
| `tests/back/RAG/test_RAG_pipeline_api_configs.py`                                       | **Modificado** — `test_publication_2_ehr_summarization` sin `retrieval_factor` en el MMR.                                                                                                                                                                                                                                                                                                                     |
| `docs/RAG/01-overview.md`                                                               | **Modificado** — se añadió el párrafo "Ranker vs. reranker configuration" en la sección "Model Type Classification".                                                                                                                                                                                                                                                                                          |

## Estado alcanzado

1. **Sin `retrieval_factor`** en schemas, constructores ni lógica de
   `retrieve()` de los tres re-rankers (`CrossEncoderRetriever`,
   `SentenceTransformerCrossEncoderRetriever`, `MMRRerankerRetriever`).

2. **`retrieve()` delega la decisión del candidato set al child**: ambos
   re-rankers llaman `child.retrieve(query)` sin pasar `top_k`. El child usa
   su propio `top_k` configurado; el re-ranker solo selecciona `top_k` de los
   candidatos recibidos (short-circuit cuando los candidatos no superan el
   `top_k` efectivo). La validación de `top_k` del re-ranker (entero ≥ 1) se
   preserva.

3. **Compatibilidad de construcción**: `RetrieverFactory._create_composite`
   pasa los params guardados directamente al constructor del compuesto sin
   validar contra `SCHEMA`; al eliminar el pop de `retrieval_factor` no queda
   ningún código que intente leer el campo ausente, así que la construcción no
   se rompe.

4. **Documentación**: la separación ranker/reranker queda documentada en el
   docstring de `CrossEncoderRetriever` y en `docs/RAG/01-overview.md`. Las
   únicas menciones restantes a `retrieval_factor` en el repo son
   intencionales y dicen que el parámetro ya no existe.

## Diagrama final

```
Antes (incorrecto):
  reranker.top_k × retrieval_factor → child.retrieve(top_k=expanded)
  (el reranker controlaba cuántos candidatos traía el ranker)

Después (correcto):
  child.retrieve()  →  child usa su propio top_k  →  N candidatos
  reranker reordena los N candidatos y devuelve sus top_k
  (config del reranker: top_k + parámetros de modelo, ej. model_name)
```

## Verificación

- **Tests**: `pytest tests/back/RAG/` → **156 passed** (incluye los 21 del
  cross-encoder y los tests de configs de componentes/pipeline). Además
  `pytest tests/back/api/test_components_api.py` → **20 passed** (el registro
  de componentes sigue sano tras el cambio de schema).
- **Ruff**: `ruff check` y `ruff format --check` limpios en todos los archivos
  modificados.
- **Mypy**: `mypy` sobre los archivos del cambio reporta 876 errores en 101
  archivos, todos **pre-existentes** en el repo (patrones repo-wide como
  `schema_field(...)` y asignaciones `MultilingualString`); ninguno fue
  introducido por esta sesión. mypy no es un gate del proyecto (AGENTS.md usa
  ruff; CI solo tiene `publish.yml`).

## Decisiones y hallazgos relevantes

- **Alcance ampliado por el equipo**: la tarea original pedía solo cross-
  encoders, pero se confirmó que el mismo error de diseño existía en
  `MMRRerankerRetriever`; se aplicó el fix también allí.
- **Test que prueba el mecanismo**: el nuevo test usa un child con
  `default_top_k=2` y un reranker con `top_k=5`. Si el reranker expandiera
  candidatos (comportamiento viejo) devolvería 5; con el diseño correcto
  devuelve 2 (short-circuit), demostrando que el top-k del child acota el
  resultado.
- **Semántica del override**: `retrieve(query, top_k=...)` sigue existiendo en
  el cross-encoder, pero el override solo afecta la selección final del
  reranker, nunca la cantidad que recupera el child.
- **Migración de configuraciones existentes**: las sesiones RAG guardadas con
  `retrieval_factor` en sus parámetros ya no aceptarán ese campo; la
  configuración del retriever debe actualizarse definiendo el tamaño del
  candidato set en el `top_k` del child.
- **Nota de estado del repo**: el árbol de trabajo ya contenía cambios sin
  commitear previos a esta sesión (módulo `cross_encoder/` completo, tests, y
  refactor de servicios de la Sesión I). Esta sesión no commiteó nada.

## Pendientes detectados (fuera de alcance de esta sesión)

- **Validación de esquema en la ruta compuesta** (heredado de la Sesión III):
  `_create_composite` no valida params contra `SCHEMA`, por lo que los bounds
  del schema de los compuestos no se aplican en esa ruta.
- **`COMPOSITE_RETRIEVER_NAMES` por strings** (heredado): frágil ante nuevos
  retrievers compuestos; alternativa pendiente es derivarlo del registry vía
  `issubclass(model_class, CompositeRetriever)`.
- **Menores del cross-encoder** (heredados): `score_chunks` con ids duplicados
  repite puntuación, `load()` no es thread-safe, `chunk_map` se reconstruye por
  llamada.

---

# Sesión 5: benchmark RAG — retrievers composite (cross-encoder) y LLMs (< 8B), `--skip-passes` y CSV multi-línea

## Objetivo

Ampliar la suite de benchmarks por componentes (`RAG_benchmark/benchmarks/`)
para cubrir dos familias que no se testeaban:

1. **Retrievers composite**, incluyendo el **SentenceTransformer cross-encoder
   reranker** (`SentenceTransformerCrossEncoderRetriever`), usando solo
   modelos pequeños (< 8B parámetros).
2. **LLMs locales** (categoría `llm` nueva), también solo con modelos < 8B.

Además, por solicitud del equipo, se añadió en la misma sesión:

3. **`--skip-passes`**: flag de CLI que salta la ejecución de un componente si
   su último resultado registrado fue `passed`, para testear solo componentes
   faltantes o que habían fallado.
4. **Fix de CSV multi-línea**: errores con saltos de línea reales producían
   celdas que ocupaban varias líneas en los CSV de resultados; se sanitizaron
   en el código y en todos los CSV existentes.
5. **Fix del embedding de OpenAI**: la API key ahora se lee en tiempo de
   ejecución desde el entorno/`.env` (no en tiempo de importación) y nunca se
   loguea en los CSV/JSONL de resultados.

**Contexto:** la suite tenía 3 categorías de componentes (chunking, retrieval,
embedding). Los retrievers composite solo cubrían MMR; no existía testeo de
cross-encoders ni de LLMs. El `LLM_MAP` y `MULTI_TURN_CONVERSATION` ya estaban
en `benchmark_data.py` pero sin usar.

## Archivos modificados

| Archivo                                                                                 | Acción                                                                                                                                                                                                                                                                                                                            |
| --------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `RAG_benchmark/benchmarks/components/llm.py`                                            | **Creado** — `LLM_CONFIGS` (10 modelos < 8B), `_execute_llm()`, `_resolve_llm_device()` (normaliza `cuda`/`cpu` y resuelve `CUDA` → primera GPU llama.cpp, fallback CPU), `run_all_llm_benchmarks()`.                                                                                                                             |
| `RAG_benchmark/benchmarks/components/retrieval.py`                                      | **Modificado** — `CROSS_ENCODER_RETRIEVER_CONFIGS` (4 configs), helper `_build_child_retriever_with_persistence()` (hijo denso/BM25), `_execute_cross_encoder_retriever()` (con `_prepare_chunks()` único y `try/finally` de limpieza), docstrings en ejecutores, `copy.deepcopy` de configs y soporte `skip_passes`.             |
| `RAG_benchmark/benchmarks/components/runner.py`                                         | **Modificado** — nueva categoría `llm` en defaults; `skip_passes` propagado a las 4 categorías; resumen con `skipped` separado de `failed`.                                                                                                                                                                                       |
| `RAG_benchmark/benchmarks/components/embedding.py`                                      | **Modificado** — `skip_passes`, `copy.deepcopy`, fix de la API key de OpenAI (se inyecta en runtime, no se guarda en params ni se loguea).                                                                                                                                                                                        |
| `RAG_benchmark/benchmarks/components/chunking.py`                                       | **Modificado** — `skip_passes`, `copy.deepcopy`.                                                                                                                                                                                                                                                                                  |
| `RAG_benchmark/benchmarks/benchmark_utils.py`                                           | **Modificado** — `_csv_single_line()` (celdas CSV de una sola línea), `load_last_run_statuses()` (último estado por clave, tolera CSV corruptos y timestamps vacíos), `run_configs(skip_statuses=...)` (loguea `skipped` sin ejecutar).                                                                                           |
| `RAG_benchmark/benchmarks/config.py`                                                    | **Modificado** — campo `skip_passes: bool` + parámetro en `from_env()`.                                                                                                                                                                                                                                                           |
| `RAG_benchmark/benchmarks/cli.py`                                                       | **Modificado** — flag `--skip-passes` en `components`.                                                                                                                                                                                                                                                                            |
| `RAG_benchmark/benchmarks/report.py`                                                    | **Modificado** — `_csv_single_line()` en exports de CSV (componentes y pipelines).                                                                                                                                                                                                                                                |
| `DashAI/back/models/hugging_face/deep_seek_model.py`                                    | **Modificado** — el `from llama_cpp import Llama` a nivel de módulo se movió dentro de `__init__` con `try/except` (igual que el resto de modelos llama.cpp). Elimina la carga eager de `llama_cpp` al importar el paquete `DashAI.back.models`, que rompía el benchmark en máquinas sin `llama-cpp-python` (hallazgo H1 del QA). |
| `DashAI/back/models/RAG/retrievers/cross_encoder/sentence_transformer_cross_encoder.py` | **Modificado** — solo docstring de `inject_infra` (decía que propagaba infra a los hijos, pero solo la guarda y carga el modelo).                                                                                                                                                                                                 |
| `docs/RAG_benchmark/02-component-benchmarks.md`                                         | **Modificado** — nueva familia "Composite: Cross-Encoder Reranker", totales corregidos (14 configs / 42 ejecuciones), nueva categoría `## Category: LLM`, sección de `--skip-passes`, nota de `--device CUDA`.                                                                                                                    |
| `docs/RAG_benchmark/05-configuration-and-output.md`                                     | **Modificado** — filas de CLI/`BenchmarkConfig` para `--skip-passes` y categoría `llm`; lista de `component_type` corregida.                                                                                                                                                                                                      |
| `RAG_benchmark/results/*.csv`                                                           | **Modificado** — los 13 CSV existentes se re-escribieron para eliminar celdas multi-línea (80 celdas en 4 archivos).                                                                                                                                                                                                              |

## Estado alcanzado

1. **Benchmark de retrievers composite con cross-encoder**: 4 configs de
   `SentenceTransformerCrossEncoderRetriever` con modelos < 8B
   (`ms-marco-MiniLM-L-6-v2` sobre hijo denso, `ms-marco-MiniLM-L-12-v2` sobre
   hijo BM25, `stsb-distilroberta-base` y `mmarco-mMiniLMv2-L12-H384-v1` sobre
   hijo denso). Todos pasan (PASS en la ejecución real).

2. **Benchmark de LLMs (< 8B)**: 10 configs — Llama 3.2 1B/3B, Qwen 2.5
   0.5B/1.5B/3B/7B, SmolLM2 360M/1.7B, Phi-4-mini, Mistral-7B. `_execute_llm()`
   mide load (descarga/carga de pesos en `__init__`) y exec (`generate()` con
   prompt de `MULTI_TURN_CONVERSATION`), y valida salida no vacía. En la
   ejecución real los 10 pasaron (1.9–12.9 s).

3. **`--skip-passes`**: `load_last_run_statuses()` escanea todos los
   `benchmark_*.csv` del directorio de resultados y devuelve el **último**
   estado registrado por `(component_type, component_class, model_name,
config_name)`; los configs cuyo último estado es exactamente `passed` se
   loguean como `skipped` y no se ejecutan. Tolerancia: ignora timestamps
   vacíos y CSVs corruptos/interrumpidos (no aborta el escaneo). Nota de
   semántica: una fila `skipped` **sí** se considera "último estado", por lo
   que un componente saltado en una pasada se re-ejecuta en la siguiente a
   menos que un `passed` fresco lo sustituya (ver hallazgo sobre la
   alternancia skip→run).

4. **CSV de una sola línea**: `_csv_single_line()` reemplaza saltos de línea
   reales por espacios en las celdas de error/texto al escribir CSV (JSON/JSONL
   conservan el texto original). Se aplicó en `BenchmarkLogger.log()` y en
   `report.py` (componentes y pipelines). Los CSV históricos de
   `RAG_benchmark/results/` se re-escribieron; verificación repo-wide: **0
   CSV con celdas multi-línea**.

5. **OpenAI embedding con API key desde `.env`**: el config ya no contiene
   `api_key`; `_execute_embedding()` la lee de `os.environ` en tiempo de
   ejecución (el módulo de config carga `RAG_benchmark/.env` con
   `python-dotenv`). La key **no** se escribe en los resultados. Verificado con
   una llamada real a `text-embedding-3-small` (200 OK, dim 1536).

6. **Imports seguros sin `llama_cpp`**: con el fix en `deep_seek_model.py`, la
   cadena `RAG_benchmark → DashAI.back.models → hugging_face → deep_seek_model`
   ya no importa `llama_cpp` de forma eager; verificado simulando un entorno
   sin el paquete (los imports del benchmark funcionan).

## Ejecución real del benchmark

Secuencia pedida por el equipo: `components --skip-passes` con `--iter 1`,
luego `--iter 2`, luego `--iter 10` (los modelos GGUF ya estaban en caché HF;
los 4 cross-encoders se descargaron, ~100 MB).

| Pasada               | Resultado                                                                                                                                                      | Estado   |
| -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| 1 iter (2026-07-31)  | 40 ejecuciones: 14 ok, 24 skipped, 2 failed, 202 s. Cross-encoders (4) y LLMs (10) **PASS**.                                                                   | Completa |
| 2 iter (2026-07-31)  | 80 ejecuciones: 48 ok, 28 skipped, 4 failed (2 embeddings × 2), 193 s. Chunking/retrieval/embedding re-ejecutados (ver hallazgo sobre semántica de `skipped`). | Completa |
| 10 iter (2026-07-31) | Re-lanzada tras el fix de OpenAI; quedó **interrumpida** por el usuario.                                                                                       | Parcial  |

**Fallos persistentes (esperados):**

- `GemmaEmbedding` (`google/embeddinggemma-300m`): 401, repo gated de HF — requiere autenticación (`huggingface_hub` login / token).
- `OpenAIEmbedding`: falló en pasadas 1–2 por falta de key; **corregido** y verificado con la key ahora presente en `.env`.

**Resultados en:** `RAG_benchmark/results/` (`benchmark_*.csv`, `component_results_*.csv`, `benchmark_*.jsonl`, `benchmark_*.json`).

## Verificación

- **Imports**: todos los módulos del benchmark y la CLI cargan correctamente
  (incluido sin `llama_cpp`, simulado).
- **Ruff**: `ruff check` limpio en las líneas tocadas; los hallazgos restantes
  del directorio son **pre-existentes** (imports sin uso, líneas largas en
  `conversation.py`/`pipelines/configs.py`, etc.). `ruff format --check` solo
  señala los 2 archivos no tocados.
- **Smoke tests** (independientes): `load_last_run_statuses` (último estado +
  robustez ante CSV corrupto/blank timestamp), `run_configs` con
  `skip_statuses` (salta `passed`, ejecuta `failed`/missing), CSV single-line
  (2 filas: header + 1 con error saneado; JSONL conserva saltos), configs
  pristinas tras `deepcopy`, `_resolve_llm_device('cpu'/'cuda')`.
- **API key OpenAI**: llamada real a `text-embedding-3-small` correcta.

## Decisiones y hallazgos relevantes

- **Semántica de `--skip-passes` y la alternancia skip→run**: el escáner
  considera el último estado registrado tal cual (incluida la fila `skipped`),
  por lo que un componente saltado en una pasada queda con estado `skipped` y
  **se vuelve a ejecutar en la siguiente pasada** a menos que un `passed`
  fresco lo sustituya. Esto se observó en la pasada 2: chunking/retrieval/
  embedding (saltados en la pasada 1) se re-ejecutaron y registraron `passed`,
  lo que dio 2 iteraciones frescas de dato para esas familias (no dañino, pero
  es el comportamiento actual y debe tenerse en cuenta al interpretar los
  resultados; una alternativa pendiente es ignorar las filas `skipped` en el
  cálculo del último estado).
- **Modelos < 8B verificados por QA (ml-tester)**: los 10 LLM (0.36B–7.6B) y
  los 4 cross-encoders (22M–118M) cumplen la restricción; todos los configs
  pasan su `SCHEMA(**params)` con `device`/`iteration` inyectados
  (`quantization` requerido solo en Llama y Phi-4-mini).
- **`llama_cpp` eager import (H1 del QA)**: era el único obstáculo para correr
  el benchmark sin `llama-cpp-python`. Se arregló en `deep_seek_model.py` (el
  resto de la cadena ya estaba protegido en `llama_utils.py`).
- **Seguridad de la API key**: el diseño original dejaba la key en los params
  del config, que `run_configs` loguea tal cual en CSV/JSONL. Ahora la key se
  inyecta en una copia local de params dentro de `_execute_embedding()` y no
  aparece en ningún resultado.
- **Ruido de llama.cpp**: los constructores de los modelos LLM usan
  `verbose=True`, lo que vuelca chat templates y metadata a stdout en cada
  carga. No afecta resultados, solo legibilidad de la consola.

## Pendientes detectados (fuera de alcance o interrumpido)

- **Pasada 3 del benchmark (10 iteraciones)** quedó **interrumpida**; se debe
  relanzar `python -m RAG_benchmark.benchmarks.cli components --skip-passes --iter 10` para cerrar la secuencia.
- **Benchmark de pipelines (`pipelines` command)** — **no ejecutado** en esta
  sesión (es un run más pesado: sesiones RAG multi-turno vía API con LLMs). Queda pendiente decidir y ejecutar.
- **`GemmaEmbedding`** requiere autenticación HF (repo gated); sin login seguirá fallando con 401.
- **`pipelines/configs.py`** define configs de `LlamaModel` sin `quantization`,
  que el `LlamaSchema` **requiere** (verificado por validación Pydantic). Si se
  corre el benchmark de pipelines, esos configs fallarán la validación hasta
  que se añada `"quantization": "Q4_K_M"`.
- **Ruff pre-existente** en `RAG_benchmark/` (imports sin uso en
  `benchmark_utils.py`/`report.py`, líneas largas en docstrings y prints,
  `conversation.py` y `pipelines/configs.py` no formateados) — quedó sin tocar
  por ser pre-existente y el directorio está en `.gitignore`.

---

# Sesión 6: reorganización del guardado de resultados del benchmark y autocontención de `RAG_benchmark/`

## Objetivo

Dos tareas encargadas por el equipo sobre la suite de benchmarks RAG:

1. **Reorganizar el guardado de resultados**: hasta ahora cada ejecución
   dispersaba muchos archivos directamente en `RAG_benchmark/results/`
   (`benchmark_{ts}.json`, `component_results_{ts}.csv`, más un
   `BenchmarkLogger` por categoría que generaba `benchmark_{ts}.csv`,
   `benchmark_{ts}.jsonl` y `benchmark_{ts}_details.jsonl` con timestamps
   distintos entre sí). Se pidió que **cada ejecución** cree una carpeta con
   el nombre de la fecha/hora de ejecución, que incluya un JSON/YAML con los
   parámetros de la ejecución (iteraciones, modelos testeados, etc.) y que
   los archivos de resultados y logs se organicen de forma comprensible
   (que el nombre del archivo indique qué contiene).
2. **Autocontención de la carpeta de benchmarks**: mover los tests de
   benchmarks a `RAG_benchmark/`, crear dentro una subcarpeta de
   documentación que, además de documentar, indique que **todo lo relativo a
   benchmarks debe residir únicamente en esa carpeta**. Los RAG benchmarks
   **no serán parte de DashAI**, por lo que no deben salir de ahí.

## Archivos modificados

| Archivo                                                                     | Acción                                                                                                                                                                                                                                                                                       |
| --------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `RAG_benchmark/benchmarks/output.py`                                        | **Creado** — `RunDirectory`, `create_run_directory()`, `build_initial_metadata()`/`build_final_metadata()`, `write_run_metadata()` (escritura atómica). Define el layout por ejecución.                                                                                                      |
| `RAG_benchmark/benchmarks/config.py`                                        | **Modificado** — campo `run_dir`, propiedades `output_dir`/`logs_dir`/`details_dir`, método `with_run_dir()`, constantes `LOGS_DIR_NAME`/`DETAILS_DIR_NAME`.                                                                                                                                 |
| `RAG_benchmark/benchmarks/benchmark_utils.py`                               | **Modificado** — `BenchmarkLogger` con `name` y `details_dir` (nombres estables `<name>.csv`/`<name>.jsonl`/`<name>_details.jsonl`); `load_last_run_statuses()` pasa a escaneo recursivo `**/*.csv` y tolera BOM/filas malformadas; las filas `skipped` ya no pisan un estado `passed` real. |
| `RAG_benchmark/benchmarks/report.py`                                        | **Modificado** — nombres estables por defecto (`suite_result.json`, `component_results.csv`, `pipeline_results.csv`); docstrings añadidos.                                                                                                                                                   |
| `RAG_benchmark/benchmarks/cli.py`                                           | **Modificado** — crea la carpeta de ejecución, escribe metadata inicial (crash-safe) y final, exporta a `config.output_dir`, usa `COMPONENT_CATEGORIES`, valida `--iter` ≥ 1.                                                                                                                |
| `RAG_benchmark/benchmarks/components/runner.py`                             | **Modificado** — refactor a `_run_category()` (elimina la duplicación 4×), constante `COMPONENT_CATEGORIES`, loggers en `config.logs_dir` con nombre de categoría, dedupe de categorías repetidas.                                                                                           |
| `RAG_benchmark/benchmarks/components/{chunking,embedding,retrieval,llm}.py` | **Modificados** — parámetro `results_dir` para el escaneo de `--skip-passes`.                                                                                                                                                                                                                |
| `RAG_benchmark/tests/conftest.py`                                           | **Creado** — bootstrap de `sys.path` para importar `RAG_benchmark` desde cualquier cwd.                                                                                                                                                                                                      |
| `RAG_benchmark/tests/test_benchmark_output.py`                              | **Creado** (en `tests/back/RAG/`) y luego **movido** a `RAG_benchmark/tests/`. 11 tests.                                                                                                                                                                                                     |
| `RAG_benchmark/tests/test_benchmark_pipeline_helpers.py`                    | **Movido** de `tests/back/RAG/` a `RAG_benchmark/tests/`. 12 tests.                                                                                                                                                                                                                          |
| `RAG_benchmark/docs/00-scope-and-boundaries.md`                             | **Creado** — regla de oro de autocontención: todo lo relativo a benchmarks vive solo en `RAG_benchmark/`.                                                                                                                                                                                    |
| `RAG_benchmark/docs/README.md`                                              | **Modificado** — nota de alcance ("no parte de DashAI") + índice actualizado.                                                                                                                                                                                                                |
| `RAG_benchmark/docs/{01,02,03,04,05}-*.md`                                  | **Movidos** de `docs/RAG_benchmark/` a `RAG_benchmark/docs/` (con actualizaciones menores).                                                                                                                                                                                                  |
| `docs/RAG_benchmark/`                                                       | **Eliminada** (contenido movido a `RAG_benchmark/docs/`).                                                                                                                                                                                                                                    |
| `run_pipeline_benchmark.py` (raíz del repo)                                 | **Eliminado** — wrapper que violaba la autocontención; el runner real sigue en `RAG_benchmark/run_pipeline_benchmark.py`.                                                                                                                                                                    |

## Estado alcanzado

1. **Carpeta por ejecución** — cada invocación de `components` o `pipelines`
   crea `RAG_benchmark/results/<YYYYMMDD_HHMMSS>/` (con sufijo `_2`, `_3`, ...
   en colisión; creada de forma atómica con `os.mkdir`):

   ```
   RAG_benchmark/results/<YYYYMMDD_HHMMSS>/
     run_metadata.json          ← parámetros (iteraciones, modelos testeados,
     │                            categorías/pipelines, device, APIs, entorno, summary)
     suite_result.json          ← BenchmarkSuiteResult completo
     component_results.csv      ← resultados por componente (runs components)
     pipeline_results.csv       ← resultados por turno/pipeline (runs pipelines)
     logs/<categoria>.csv|.jsonl ← logs crudos por categoría
     details/<categoria>_details.jsonl
   ```

2. **`run_metadata.json`** — se escribe **antes** de ejecutar
   (`completed: false`, `end_time: null`, registro crash-safe) y se
   sobreescribe al terminar (`completed: true`, `models_tested`, `summary`,
   `end_time`). `messages_per_conversation` solo aparece en runs de
   `pipelines`; `models_tested` une componentes y pipelines si ambos existen.
   Escritura atómica (tmp + rename).

3. **Logs por categoría con nombres auto-descriptivos** — `BenchmarkLogger`
   escribe `logs/chunking.csv`, `logs/chunking.jsonl`, etc. Ya no hay
   `benchmark_{ts}.csv` dispersos con timestamps inconsistentes.

4. **`--skip-passes` corregido (H1 del QA)** — el escaneo recursivo ignora
   las filas `skipped` al calcular el último estado, por lo que un componente
   saltado ya no se re-ejecuta en la siguiente pasada (se eliminó la
   alternancia skip→run). Tolerancia a BOM (`utf-8-sig`) y a filas
   malformadas (se saltan por fila, no por archivo).

5. **Tests autocontenidos** — los tests de benchmark viven en
   `RAG_benchmark/tests/` y se ejecutan con
   `python -m pytest RAG_benchmark/tests/`. No forman parte de `testpaths`
   de DashAI.

6. **Documentación autocontenida** — `RAG_benchmark/docs/` con
   `00-scope-and-boundaries.md` que establece la regla: _todo lo relativo a
   benchmarks reside únicamente dentro de `RAG_benchmark/`_ (sin wrappers,
   tests, imports ni docs fuera; sin añadir el módulo al paquete/CI/sitio de
   DashAI).

7. **Wrapper raíz eliminado** — `run_pipeline_benchmark.py` en la raíz del
   repo ya no existe.

## Estructura final de `RAG_benchmark/`

```
RAG_benchmark/
  benchmarks/        # motor (cli, config, modelos, runners)
  tests/             # pytest suite (conftest + 2 test files)
  docs/              # documentación (00-scope-and-boundaries + 01..05 + README)
  papers/            # datos de prueba (PDFs)
  results/           # salidas por ejecución
  .env               # claves API locales
  run_benchmark.py / run_pipeline_benchmark.py
```

## Verificación

- **Tests**: `python -m pytest RAG_benchmark/tests/` → **23 passed** (11 de
  `test_benchmark_output.py` + 12 de `test_benchmark_pipeline_helpers.py`).
- **Ruff**: `ruff check` y `ruff format --check` limpios en todos los
  archivos modificados/creados.
- **CLI**: `python -m RAG_benchmark.benchmarks.cli --help` funciona.
- **Smoke test del flujo**: creación de carpeta, metadata inicial/final,
  exports y escaneo recursivo verificados end-to-end (script temporal).
- **Tests RAG de DashAI intactos**: `tests/back/RAG/test_RAG_prompts.py` →
  13 passed.
- **Sin referencias rotas**: no quedan referencias a `docs/RAG_benchmark/` ni
  a las rutas antiguas de tests (solo cachés, limpiadas).

## Decisiones y hallazgos relevantes

- **QA (ml-tester)**: hallazgos corregidos en la sesión: H1 (alternancia
  skip→run en `--skip-passes`), M1 (CSV con BOM se descartaban), M2
  (categorías duplicadas con `-c`), M3 (filas CSV malformadas podían pisar
  estados reales), M4 (`models_tested` se sobrescribía en suites mixtas),
  L3 (race al crear la carpeta), L4 (`has_openai`/`has_deepseek` con string
  vacío), L6 (escritura no atómica de metadata), L7 (sin validación de
  `--iter`).
- **Nota de transparencia**: durante el movimiento de la documentación, la
  carpeta `docs/RAG_benchmark/` (sin trackear en git) se borró por error
  antes de mover su contenido. Los 6 documentos se reconstruyeron en
  `RAG_benchmark/docs/`; `02-component-benchmarks.md` se reconstruyó a partir
  del código real de los benchmarks (configs de chunking, embedding,
  retrieval y LLM).
- **Las rutas de la Sesión V quedan obsoletas**: los archivos que se
  documentaron como `docs/RAG_benchmark/02-component-benchmarks.md` y
  `docs/RAG_benchmark/05-configuration-and-output.md` ahora viven en
  `RAG_benchmark/docs/`.
- **`RAG_benchmark/` está en `.gitignore`**: los cambios de esta sesión (y de
  la Sesión V) no aparecen en `git status`. El único delta trackeado es la
  eliminación de `run_pipeline_benchmark.py` de la raíz.
- **No se usó git** durante la sesión (por instrucción del equipo: hay muchas
  sesiones sin commitear, previas y posteriores a esta).

## Pendientes detectados (fuera de alcance de esta sesión)

- **M5 del QA**: el `error_message` de pipelines puede reflejar el
  `response.text` de un 422 (que ecoa el payload con `api_key`);
  `_redact_secrets` no cubre los mensajes de error. Baja probabilidad (los
  configs actuales pasan la validación), pero conviene sanear los mensajes de
  error antes de escribirlos.
- **`details/` se crea vacío**: `log_detailed_run()` no tiene llamadores aún;
  el subfolder y el doc de formato existen pero no se escribe nada.
- **`start_time` inicial vs final**: la metadata inicial usa el timestamp del
  CLI y la final el de `result.start_time` (difieren en milisegundos).
- **`_redact_secrets` solo cubre keys exactas** `api_key`/`API_key`; keys con
  otros nombres (`apiKey`, `token`, `secret`) quedarían sin redactar.

---

# Sesión 7: arreglo del benchmark de pipelines RAG (todos fallaban)

## Objetivo

Revisar y hacer funcionar el benchmark de pipelines RAG
(`python -m RAG_benchmark.run_pipeline_benchmark pipelines ...`), que el
usuario intentó ejecutar y **fallaba en TODOS los pipelines** (50/50 en el run
del 2026-08-02: cada `GenerativeProcess` terminaba en estado `ERROR` en menos
de un segundo). El trabajo siguió un flujo **TDD**: primero los agentes QA
(`ml-tester`, `api-tester`, `flow-tester`) caracterizaron los bugs por dominio
(schema/BD, API, state-machine), luego se implementaron los fixes con tests de
regresión que pasan a verde.

## Causas raíz (en orden de aparición en el flujo del job)

1. **Esquema de BD incoherente con el ORM (bloqueante de todo):**
   `sqlite3.IntegrityError: NOT NULL constraint failed:
rag_pipeline.chunking_model_id`. La migración `f06652057903_add_rag_tables`
   creó `rag_pipeline.chunking_model_id`, `prompt_id` y `generation_model_id`
   como **NOT NULL**, pero el ORM (`models.py`, clase `RAGPipeline`) las define
   `nullable=True` y `SetupService._ensure_db_record()` inserta una fila
   _placeholder_ con esas FKs en NULL (se rellenan después en
   `_update_db_record()`; el retriever necesita el `pipeline_id` antes de
   poder crearse, así que el patrón placeholder es estructuralmente
   necesario). Confirmado por los 3 testers con reproducción aislada.
2. **Configs de pipeline incompletos (faltaban campos requeridos de los
   sub-componentes):** la creación de sesión valida solo el shape
   `{component, params}` (top-level `RAGPipelineSchema`), por lo que las
   configs inválidas se aceptaban con 201 y explotaban en runtime dentro de
   `SetupService.build_pipeline()`:
   - `separators` requerido en `RecursiveCharacterChunkModel` (pub1/pub3) →
     `KeyError: 'separators'`.
   - `overflow_strategy` requerido en `SentenceTransformerEmbedding` (pub2) y
     `E5Embedding` (pub4a) → `ValidationError`.
   - 6 campos requeridos de `BM25VectorizerSchema` (pub4b): `strip_accents`,
     `lowercase`, `stop_words`, `max_df`, `min_df`, `max_features`.
   - `quantization` requerido en `LlamaSchema` (todos) → faltaba
     `"quantization": "Q4_K_M"`.
   - `template` requerido por `DefaultRAGGenerationPromptSchema` y por
     `PromptService.create()` (todos) — las configs solo enviaban
     `{"language": "en"}`.
   - `retrieval_factor` en el MMR de pub2: el schema y el constructor lo
     ignoran (el tamaño del candidato set lo define el `top_k` del child), se
     eliminó.
3. **`context_window` insuficiente:** el prompt con `top_k=20` chunks de
   300 tokens (~5787 tokens) excedía el `context_window: 4096` del Llama →
   `Requested tokens (5787) exceed context window of 4096`. Se subió a 8192
   (el GGUF soporta hasta 131072; headroom suficiente).
4. **Bug real de backend en `OpenAIEmbedding.batch_encode()` (pub1/pub3):**
   - La API de OpenAI limita a **2048 inputs por request**; el pipeline
     enviaba 4048 chunks en una sola llamada → 400.
   - La API rechaza **cualquier string vacío** dentro del batch
     (`'$.input' is invalid`) — verificado de forma aislada: 2048 no-vacíos
     OK, con 1 vacío → 400. Los chunks vacíos provienen del parser `textract`
     (default de `PDFDocument`), que colapsa whitespace y produce miles de
     mini-chunks.
   - **Decisión del usuario:** NO cambiar el parser por defecto (debe seguir
     siendo `textract`; "PyPDF2 no funciona tan bien"). El fix fue sanitizar
     en el embedding, no cambiar la extracción.
5. **Inconsistencia de parser (hallazgo Critical del code-review):** el
   benchmark descubría los papers con `parser="PyPDF2"` (`base.py`, `cli.py`)
   pero el runtime rehidrata con el default `textract`. Se alineó el
   descubrimiento a `textract` y se documentó el parser efectivo.

## Archivos modificados

| Archivo                                                                  | Acción                                                                                                                                                                                                                                                                                                                                             |
| ------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DashAI/alembic/versions/e9f8a7b6c5d4_make_rag_pipeline_fks_nullable.py` | **Creado** — migración que hace nullable `chunking_model_id`, `prompt_id` y `generation_model_id` de `rag_pipeline` (down_revision `8d5416cac8f1`, la cabeza). Docstring documenta que el `downgrade` fallará en BD con filas placeholder (re-aplicar NOT NULL es destructivo).                                                                    |
| `DashAI/back/models/RAG/embeddings/dense/openai_embedding.py`            | **Modificado** — `batch_encode()` particiona en slices de ≤ `OPENAI_MAX_INPUTS_PER_REQUEST = 2048` y concatena con `np.vstack`; `encode()` y `batch_encode()` sanitizan strings vacíos/whitespace a `" "` vía helper compartido `_sanitize_input()` (preserva el alineamiento de filas con los chunk indices del retriever).                       |
| `RAG_benchmark/benchmarks/pipelines/configs.py`                          | **Modificado** (gitignored) — campos requeridos añadidos (separators, overflow_strategy, BM25 fields, quantization, template desde `TEMPLATES["en"]`), `context_window` 4096→8192, `retrieval_factor` eliminado, params de `generation_model` expandidos una clave por línea.                                                                      |
| `RAG_benchmark/benchmarks/pipelines/base.py`                             | **Modificado** (gitignored) — `discover_rag_benchmark_papers(parser="textract")` (consistente con el runtime).                                                                                                                                                                                                                                     |
| `RAG_benchmark/benchmarks/cli.py`                                        | **Modificado** (gitignored) — conteo de papers con `parser="textract"`.                                                                                                                                                                                                                                                                            |
| `RAG_benchmark/tests/test_pipeline_configs_schema_valid.py`              | **Creado** (gitignored) — test de regresión parametrizado sobre los 5 configs: recorre recursivamente todos los component refs (incl. `children` de MMR y `BM25Vectorizer` anidado), valida cada uno contra el `SCHEMA` del componente registrado y verifica el set esperado de componentes por pipeline (falla en refs malformados sin `params`). |
| `RAG_benchmark/docs/03-pipeline-benchmarks.md`                           | **Modificado** (gitignored) — nota de extracción de texto: se usa `textract`, el chunking opera sobre texto con whitespace colapsado.                                                                                                                                                                                                              |
| `docs/RAG/backlog.md`                                                    | **Modificado** — esta entrada.                                                                                                                                                                                                                                                                                                                     |

**No modificado** (aunque se evaluó): `DashAI/back/models/RAG/documents/pdf_document.py`
— se probó cambiar el default de `textract` a `PyPDF2` y se **revirtió** por
decisión explícita del usuario.

## Estado alcanzado

1. **Migración `e9f8a7b6c5d4`** — verificada por `ml-tester`: aplica limpio en
   BD fresca y en BD existente pre-fix; produce exactamente las columnas
   nullable que el ORM espera; el INSERT placeholder y el flujo completo de
   `create_app` funcionan. No quedan otros desajustes ORM/BD en las tablas RAG.

2. **Configs de pipeline válidos** — los 5 configs (`pub1`, `pub2`, `pub3`,
   `pub4a`, `pub4b`) validan contra los `SCHEMA` de sus componentes (el test
   de regresión lo garantiza). La lógica de negocio no se tocó; solo se
   completaron los params que el frontend también enviaría.

3. **Benchmark corriendo end-to-end** (verificado con 1 iteración / 1 mensaje
   por pipeline, modelo ya cacheados):
   - `pub1` (OpenAI embeddings + Llama 3B): **successful** (~26–58 s/turn).
   - `pub2` (MMR + MiniLM + Llama 3B): **successful** (~59 s/turn).
   - `pub3` (OpenAI embeddings + Llama 1B): **successful** (~28 s/turn).
   - `pub4b` (BM25 + Llama 3B): **successful** (~61 s/turn).
   - `pub4a` (E5 Mistral 7B + Llama 3B): config válido (el test de regresión
     lo valida) pero **impracticable en esta máquina**: el modelo E5 de 7B
     inicia una descarga de 13+ min y una carga muy pesada en CPU. Limitación
     práctica de recursos, no de código.

4. **Fix de OpenAI** — `batch_encode()` correcto para lotes vacíos `(0,0)`,
   un solo slice y multi-slice; alineamiento de filas preservado (verificado
   por el code-reviewer con mock).

5. **Parser consistente** — el benchmark descubre y ejecuta con `textract`
   (default del runtime), documentado en `03-pipeline-benchmarks.md`.

## Verificación

- **Tests benchmark**: `python -m pytest RAG_benchmark/tests/` → **28 passed**
  (incluye el nuevo `test_pipeline_configs_schema_valid.py`, 5/5).
- **Tests RAG de DashAI**: `python -m pytest tests/back/RAG/` → **156 passed**
  (cero regresiones).
- **Ruff**: `ruff check` limpio en `openai_embedding.py`; la migración está
  excluida del lint (`exclude = ["alembic"]`, consistente con las migraciones
  existentes que usan comillas simples).
- **Smoke real**: runs de `pub1`, `pub2`, `pub3`, `pub4b` con 1 iter / 1 msg
  → `1 runs, 1 successful` cada uno; CSV con `assistant_response`,
  `chunks_retrieved` (p. ej. 20 en pub4b) y sin `error`.

## Decisiones y hallazgos relevantes

- **Proceso QA**: los 3 testers convergieron en C1 (migración), C2 (configs
  incompletos) y C3 (prompt sin template). El `api-tester` confirmó que los
  endpoints (session/process/job) cumplen el contrato que el benchmark
  asume; el fallo era del backend/job, no del API. El `flow-tester` confirmó
  que el patrón placeholder es estructuralmente necesario (el retriever
  necesita `pipeline_id`) y que la migración debe commitearse.
- **Bug de OpenAI aislado con precisión**: 2048 no-vacíos OK; 1 vacío en el
  batch → 400. No es un límite de tamaño de lote, es la presencia de strings
  vacíos. El fix sanitiza a `" "` (embedding neutral, fila preservada).
- **Parser**: la decisión de mantener `textract` es del usuario. Consecuencia
  documentada: `textract` colapsa whitespace, así que
  `RecursiveCharacterChunkModel` (separadores basados en `\n`) cae a separar
  por `.`/espacio → miles de chunks pequeños (~30 chars). El benchmark mide
  esa realidad (no la de PyPDF2). La sanidad del chunking con texto
  colapsado queda como cuestión metodológica abierta.
- **`RAG_benchmark/` está en `.gitignore`**: los cambios de configs, tests y
  docs del benchmark son locales (no trackeados).
- **⚠️ La migración `e9f8a7b6c5d4` es untracked**: hay que commitearla o el
  bug C1 reaparece en cualquier checkout limpio/CI. Por instrucción del
  equipo, **no se usó git** en esta sesión.
- **`context_window` 8192**: válido (`int_field(ge=1, le=131072)`) y
  consistente en los 5 pipelines; incrementa el KV-cache en CPU (manejable
  en Q4_K_M 3B/1B). Resultados previos producidos con 4096 no son
  directamente comparables — convendría registrar el context window en la
  metadata del benchmark.

## Pendientes detectados (fuera de alcance de esta sesión)

- **Commitear la migración `e9f8a7b6c5d4`** (sin commit, el fix de BD no
  sobrevive a un checkout limpio).
- **`pub4a` requiere recursos** (E5 Mistral 7B en CPU impracticable); decidir
  si se mapea a un modelo E5 menor (`intfloat/e5-small-v2`, ya cacheados) o
  se ejecuta en máquina con más RAM/GPU.
- **Errores de RAGJob invisibles (H1 del flow-tester)**: `RAGJob.set_status_as_error()`
  solo cambia el status a ERROR; no persiste `ProcessData` con el detalle del
  error (a diferencia de `GenerativeJob`). El benchmark y el frontend solo ven
  "Process N ended with ERROR status" sin diagnóstico.
- **Cascada de BD inerte (H1)**: SQLite sin `PRAGMA foreign_keys=ON`; borrar
  una sesión deja huérfanas las filas `RAG_pipeline`/`RAG_chunk_set`
  (heredado de Sesiones III/V).
- **`PromptService.create()` rechaza prompts solo con `language`** (sin
  `template`/`templates`): el benchmark ya envía `template` explícito, pero
  es un bug latente para cualquier ruta que dependa del template por defecto
  del componente (el frontend sí envía `template`, por eso no afecta al UI).
- **`build_pipeline` no es idempotente entre turnos (H2 del flow-tester)**:
  cada turno reconstruye el pipeline y crea filas nuevas de prompt/retriever
  compuesto; el `prompt_id` de la fila única de pipeline se re-apunta al más
  reciente. Para el benchmark de 1 turno no afecta; con `--messages > 1`
  acumula filas.
- **El `downgrade` de la migración falla** en BD con filas placeholder
  (documentado en el docstring de la migración).

---

# Sesión 8: fix del crash de `RAG_prompt` en el benchmark de pipelines + revisión multi-turno y outputs por turno

## Objetivo

Arreglar el benchmark de pipelines RAG
(`python -m RAG_benchmark.run_pipeline_benchmark pipelines ...`), que fallaba
con `RAGDatabaseError: Error creating prompt in database.` al insertar en la
tabla `RAG_prompt` (violación de `UniqueConstraint("class_name", "parameters")`).
Además, revisar tres preguntas del usuario sobre el comportamiento del
benchmark:

1. ¿Simula correctamente una conversación multi-turno dado el parámetro de
   turnos (`--messages`)?
2. ¿Cómo se configura el prompt del LLM que simula al usuario (`UserSimulator`)?
3. ¿Se guardan los outputs de cada turno, incluyendo mensaje del usuario,
   respuesta del LLM y chunks del LLM?

## Causa raíz del crash

`SetupService.build_pipeline()` (en `DashAI/back/services/RAG/setup_service.py`)
llamaba `PromptService.create()`, que hace un INSERT incondicional en la tabla
`RAG_prompt`. La tabla tiene `UniqueConstraint("class_name", "parameters",
name="uix_RAG_prompt_class_params")` (models.py). El benchmark crea una sesión
nueva por iteración y **cada turno** re-ejecuta `build_pipeline()` con el mismo
prompt config (misma `class_name` + mismos `parameters`), por lo que la segunda
creación del mismo prompt violaba la constraint → `RAGDatabaseError` →
`JobError("Error during RAG pipeline setup")`.

El resto de componentes del pipeline ya usaban patrón lookup-or-create
(`LLMService.get_or_create`, `ChunkingService.create`,
`RetrieverSetupService.setup`); solo el prompt no lo hacía. Además, cada turno
re-ejecuta `build_pipeline()` completo, así que incluso una sola sesión
multi-turno fallaba en el turno 2.

## Archivos modificados

| Archivo                                                  | Acción                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| -------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DashAI/back/services/RAG/prompt_service.py`             | **Modificado** — nuevo método `PromptService.get_or_create()` (patrón lookup-or-create como `LLMService.get_or_create`): busca por `(class_name, parameters)` probando primero los params crudos y luego los ordenados con `dict(sorted(...))` (la constraint UNIQUE compara el JSON serializado, sensible al orden de claves); si existe, reutiliza el registro; si no, inserta con params ordenados. Maneja `exc.IntegrityError` por concurrencia (rollback + re-lookup). Helper privado `_find_by_class_and_params()`. **`create()` no se modificó** — el endpoint `POST /api/v1/prompt/` sigue devolviendo 409 en duplicados (test `test_create_duplicate_prompt_fails`). |
| `DashAI/back/services/RAG/setup_service.py`              | **Modificado** — `build_pipeline()` usa `self._prompts.get_or_create(...)` en vez de `create(...)`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `DashAI/back/job/RAG_job.py`                             | **Modificado** — la query del historial multi-turno (procesos `FINISHED` de la sesión) añadió `.order_by(GenerativeProcess.id)` para garantizar orden cronológico (antes sin ORDER BY).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `DashAI/back/dependencies/database/models.py`            | **Modificado** — relaciones `input` y `output` de `GenerativeProcess` ahora usan `order_by="ProcessData.id"` para garantizar que `output[0]` sea siempre el mensaje (no el JSON de chunks).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `RAG_benchmark/benchmarks/models.py`                     | **Modificado** (gitignored) — `TurnRecord` añade `retrieved_chunks: Any = Field(default_factory=dict)` con el dict JSON completo de chunks por turno.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `RAG_benchmark/benchmarks/pipelines/base.py`             | **Modificado** (gitignored) — `_parse_process_output()` devuelve tupla de 3: `(output_text, chunks_retrieved, retrieved_chunks)`; `_execute_turn()` guarda `retrieved_chunks` en `TurnRecord` (éxito y fallo con `{}`).                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `RAG_benchmark/benchmarks/report.py`                     | **Modificado** (gitignored) — columna `retrieved_chunks` (JSON, `ensure_ascii=False`) en `pipeline_results.csv`, después de `chunks_retrieved`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `RAG_benchmark/tests/test_benchmark_pipeline_helpers.py` | **Modificado** (gitignored) — tests de `_parse_process_output` a la nueva firma de 3 elementos; nuevos tests: `test_parse_process_output_list_chunks`, `test_export_pipeline_csv_includes_retrieved_chunks`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `tests/back/RAG/test_RAG_prompts.py`                     | **Modificado** — test `test_service_get_or_create_reuses_existing` (reuso con mismos params, fila nueva con params distintos, conteo en DB).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `RAG_benchmark/docs/03-pipeline-benchmarks.md`           | **Modificado** (gitignored) — per-turn execution, nueva sub-sección "Conversation history", result aggregation con `retrieved_chunks`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `RAG_benchmark/docs/04-execution-flow.md`                | **Modificado** (gitignored) — per-pipeline flow y per-turn details con extracción de chunks.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `RAG_benchmark/docs/05-configuration-and-output.md`      | **Modificado** (gitignored) — columna `retrieved_chunks` en tabla CSV, ejemplo JSON, data model `TurnRecord`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |

## Estado alcanzado

1. **Crash eliminado** — `build_pipeline()` reutiliza el registro `RAG_prompt`
   existente cuando la misma clase+params ya fue creada por una sesión/turno
   previo. El benchmark multi-turno ya no falla en la segunda creación del
   prompt. Verificado con 187 tests (backend RAG + benchmark) y 0 regresiones.

2. **Historial multi-turno ordenado** — `RAGJob` arma la conversación desde los
   procesos `FINISHED` de la sesión con `ORDER BY GenerativeProcess.id`, y las
   relaciones `input`/`output` del modelo devuelven los `ProcessData` por `id`,
   garantizando que el mensaje sea siempre `output[0]`.

3. **Chunks completos por turno** — cada `TurnRecord` guarda el dict JSON
   completo de los chunks recuperados (`retrieved_chunks`: document id, name,
   position, text), además del conteo `chunks_retrieved`. Se exporta al CSV
   `pipeline_results.csv` y al `suite_result.json`.

4. **Revisión respondida al usuario**:
   - **Q1 (multi-turno):** el diseño simula correctamente la conversación
     (`--messages` controla `range(messages_per_conversation)`, el
     `UserSimulator` recibe `prev_resp` para preguntas contextuales y el backend
     arma el historial), pero estaba roto por el crash del prompt (ahora
     resuelto) y el historial no estaba ordenado (ahora con ORDER BY).
   - **Q2 (prompt del simulador):** `_DEFAULT_SYSTEM_PROMPT` hardcodeado en
     `RAG_benchmark/benchmarks/conversation.py` (estudiante curioso de RAG);
     config vía `DASHAI_DEEPSEEK_API_KEY`/`DASHAI_DEEPSEEK_MODEL` (default
     `deepseek-chat`), `base_url` fijo `https://api.deepseek.com`,
     `temperature=0.8`, `max_tokens=256`, fallback a preguntas random si la API
     falla. Limitación documentada: el system prompt es genérico de RAG, no se
     personaliza por paper.
   - **Q3 (outputs por turno):** antes se guardaban `user_message` y
     `assistant_response`, pero solo el _count_ de chunks. Ahora se guarda el
     dict completo de chunks por turno.

## Verificación

- **Tests**: `pytest tests/back/RAG/ RAG_benchmark/tests/` → **187 passed**
  (cero regresiones). Además `pytest tests/back/RAG/test_RAG_prompts.py
tests/back/RAG/test_RAG_prompt_updates.py tests/back/RAG/test_RAG_session_flow.py`
  → 36 passed.
- **Ruff**: `ruff check` y `ruff format --check` limpios en todos los archivos
  modificados/creados.
- **Mypy**: reporta errores pre-existentes del repo (1022 en 120 archivos),
  ninguno introducido por esta sesión; mypy no es un gate del proyecto
  (AGENTS.md usa ruff).
- **Code-review**: 0 Critical, 7 Warnings (5 arreglados en la iteración:
  asimetría de orden de claves en la búsqueda, `IntegrityError` por
  concurrencia, tipo `retrieved_chunks`, ordenamiento de relaciones
  input/output, cobertura de tests; 2 de diseño documentados: tamaño del CSV
  con chunks completos y validación ligera de `get_or_create`).

## Decisiones y hallazgos relevantes

- **`get_or_create` no valida template** (a diferencia de `create`): es
  intencional y seguro porque `setup_service.build_pipeline()` construye primero
  `prompt_model = models_factory.create_prompt(...)`, que ya valida el
  componente vía `PromptFactory` antes de llamar a `get_or_create`.
- **Asimetría de orden de claves**: `create()` guarda los params tal cual los
  recibe; la constraint UNIQUE compara el texto JSON serializado (sensible al
  orden de claves). `get_or_create` mitiga buscando primero con los params
  crudos y luego con `sorted(...)`, e insertando siempre ordenado para
  determinismo futuro.
- **`RAG_benchmark/` está en `.gitignore`**: los cambios de benchmark (models,
  base, report, tests, docs) son locales (no trackeados). Los cambios
  trackeados son `prompt_service.py`, `setup_service.py` (untracked),
  `RAG_job.py`, `models.py` y `test_RAG_prompts.py`.
- **No se usó git** durante la sesión (por instrucción del equipo: hay muchas
  sesiones sin commitear, previas y posteriores a esta).
- **El repo tenía cambios previos sin commitear** (refactor de servicios de la
  Sesión I, `RAGSetupService`→`SetupService`, módulo `cross_encoder/`, etc.);
  se respetaron y solo se tocó lo necesario.

## Pendientes detectados (fuera de alcance de esta sesión)

- **System prompt del `UserSimulator` genérico de RAG**: no se personaliza por
  paper (médico, EHR, etc.). Mejora posible: inyectar el título/tema del paper
  al system prompt del simulador.
- **CSV con chunks completos crece**: con `top_k=20` y `chunk_size=1000` cada
  turno emite decenas de KB. Decisión de diseño del usuario (quería chunks
  completos); alternativa: mover chunks a JSONL aparte y dejar referencia en CSV.
- **Validación ligera de `get_or_create`**: no valida `class_name` registrado
  ni `Prompt` subclass (mitigado por `create_prompt` previo). Opcional: validar
  `class_name in registry` y documentar la precondición.

---

# Sesión 9: fix del bug "Similarity matrix not initialized" en el benchmark de pipelines RAG (cache de chunking por chunk set)

## Objetivo

Investigar el error reportado por el usuario al ejecutar el benchmark de
pipelines RAG (`python -m RAG_benchmark.run_pipeline_benchmark pipelines ...`):

```
RAGPipelineRuntimeError: Failed during retrieval: Document retrieval failed:
Similarity matrix not initialized.
```

Determinar si el error era del **benchmark** o del **código RAG**, y corregirlo
con flujo **TDD**: primero agentes de testing (test que falla), luego
implementación del fix, y finalmente code review.

**Diagnóstico:** el error es del **código RAG**, no del benchmark. El benchmark
solo lo expone al aplicar la misma configuración de chunking sobre documentos
distintos dentro de un mismo proceso (escenario legítimo de usuario: dos
sesiones RAG con los mismos parámetros de chunking pero documentos diferentes).

## Causa raíz

`DenseRetriever.retrieve()` lanzaba `ValueError("Similarity matrix not
initialized.")` porque `similarity_matrix` era `None`. La matriz se construye en
`init_similarity_matrix()` a partir de los chunks inyectados; con 0 chunks no se
construye y no hay excepción durante el setup (el error aparece recién en
`retrieve()`).

`ChunkingService.create()` (`DashAI/back/services/RAG/chunking_service.py`)
usaba como clave natural del modelo de chunking **solo `(class_name,
parameters)`**, sin incluir el `chunk_set_id` (que codifica el conjunto de
documentos). La secuencia del bug:

1. El 1er documento crea el registro del modelo de chunking y persiste sus
   chunks bajo `chunk_set_id=A`.
2. Un 2º documento (misma config de chunking) encuentra el modelo existente →
   camino de caché → `_fetch_chunks_from_db(chunk_set_id=B)` devuelve `{}`
   (el chunk set B nunca fue chunked) → devuelve un `ChunkingFactoryResult`
   con `chunks` vacío.
3. El retriever denso recibe 0 chunks → `matrix_dirs` vacío →
   `similarity_matrix = None` → "Similarity matrix not initialized".

Evidencia de la reproducción (DB del repro): `rag_chunking_model` con **1**
registro; `chunk` solo con filas para `chunk_set_id=1` (4048 chunks); los chunk
sets 2 y 3 con **0** chunks.

## Reproducción

`pipelines --pipeline pub1 --iter 3 --messages 1` (OpenAI embeddings reales):

| Iteración | Documento                   | Antes del fix                                  | Después del fix |
| --------- | --------------------------- | ---------------------------------------------- | --------------- |
| 0         | Atlas-Few-Shot-Learning.pdf | OK                                             | OK              |
| 1         | Dense-Passage-Retrieval.pdf | **FAIL** ("Similarity matrix not initialized") | OK              |
| 2         | Faster-And-Lighter-LLMs.pdf | **FAIL**                                       | OK              |

## Archivos modificados

| Archivo                                             | Acción                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DashAI/back/services/RAG/chunking_service.py`      | **Modificado** — fix en `ChunkingService.create()`: cuando el modelo de chunking está cacheado por `(class_name, parameters)` pero el chunk set actual **no tiene chunks persistidos**, ahora se computan y persisten los chunks (antes devolvía `{}`). Se respeta el `UniqueConstraint("class_name", "parameters")` de `RAGChunkingModel` (la rama de caché reutiliza `existing.id`). Refactor DRY en dos helpers privados: `_compute_chunks()` (factory puro) y `_persist_chunks_and_update_ids()` (persistencia + rollback). La rama cache-miss guarda el record del modelo **antes** de persistir chunks (camino de fallo autocurable). |
| `tests/back/RAG/test_chunking_service.py`           | **Creado** — test unitario de regresión: dos documentos con la misma config de chunking; el 2º chunk set debe producir chunks no vacíos.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `tests/back/RAG/test_chunking_cache_integration.py` | **Creado** — test de integración: monta `RetrieverSetupService.setup("DenseEmbeddingRetriever")` para ambos chunk sets (sin LLM) y verifica que el retriever del 2º documento construye `similarity_matrix is not None`.                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `docs/RAG/backlog.md`                               | **Modificado** — esta entrada.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |

No se modificó ningún archivo extra (ni el benchmark, ni parsers, ni embeddings);
el bug se resolvió únicamente en la capa de servicio de chunking.

## Estado alcanzado

1. **Invariante restaurado**: todo chunk set recién creado debe tener sus chunks
   computados y persistidos, aunque el modelo de chunking ya esté cacheado para
   otros documentos.

2. **Flujo TDD completo (RED → GREEN → REVIEW):**
   - **RED — ml-tester**: escribió el test unitario; fallaba con
     `result_b.chunks == {}`.
   - **RED — flow-tester**: escribió el test de integración; fallaba con
     `res_b.model.similarity_matrix is None` (síntoma exacto de producción).
   - **GREEN — agente general**: implementó el fix.
   - **REVIEW — code-reviewer** (3 iteraciones):
     - Iter 1: 2 Critical (tamaño/anidamiento de `create()` + duplicación de
       lógica; Ruff SIM105 en los tests) → corregidos.
     - Iter 2: 2 Warnings (regresión de robustez por reordenación en la rama
       cache-miss — persistía chunks antes que el record del modelo; redacción
       "RED phase" incompleta en un docstring) → corregidos.
     - Iter 3: **APROBADO** (0 Critical, 0 Warnings; 3 suggestions no
       bloqueantes).

3. **Verificación:**
   - `pytest tests/back/RAG/` → **159 passed** (incluye los 2 tests de
     regresión).
   - `ruff check` y `ruff format --check` limpios en los 3 archivos.
   - **Benchmark real**: `pipelines --pipeline pub1 --iter 3 --messages 1` →
     **3/3 successful** (0 fallos) tras el fix; antes 1/3.

## Decisiones y hallazgos relevantes

- **El error era del código RAG, no del benchmark.** El benchmark lo expone al
  reutilizar la misma config de chunking con documentos distintos en un mismo
  proceso. Un usuario normal lo reproduciría creando dos sesiones con los mismos
  parámetros de chunking pero documentos diferentes.
- **`UniqueConstraint("class_name", "parameters")`**: la rama de caché con chunk
  set sin chunks **no** llama a `_save_db_record` (reutiliza `existing.id`);
  guardar el registro duplicado habría violado la constraint.
- **Orden de operaciones en cache-miss**: `_save_db_record` (commit del record)
  antes de `_persist_chunks` — si el record no se puede guardar, el rollback no
  deja chunks huérfanos y un reintento es autocurable; si la persistencia de
  chunks falla tras guardar el record, el siguiente `create()` reutiliza el
  modelo cacheado, detecta chunk set sin chunks y recomputa.
- **`RAG_benchmark/` está en `.gitignore`**: los cambios de la Sesión V–VIII en
  el benchmark no aparecen en `git status`; esta sesión no modificó nada del
  benchmark.
- **Los 2 tests nuevos son untracked**: hay que hacer `git add
tests/back/RAG/test_chunking_service.py
tests/back/RAG/test_chunking_cache_integration.py` al commitear.
- **No se usó git** durante la sesión (por instrucción del equipo: hay muchas
  sesiones sin commitear, previas y posteriores a esta).

## Pendientes detectados (fuera de alcance de esta sesión)

- **Guard todo-o-nada `if not chunks`** (code-reviewer): no distingue "chunk set
  sin chunks persistidos" de "chunk set legítimamente vacío" (documento sin
  texto → recomputa en cada llamada). Tampoco cubre el caso de persistencia
  parcial (crash a mitad de la persistencia de chunks de solo algunos
  documentos). Una alternativa robusta compararía los `document_id` presentes en
  los chunks persistidos contra los documentos del chunk set.
- **Test de integración depende de red en el primer run**: usa
  `SentenceTransformerEmbedding` (`all-MiniLM-L6-v2`); en CI offline fallaría
  hasta que el modelo esté cacheado (patrón pre-existente en el repo).
- **Menores (suggestions del code-reviewer)**: docstring de `create()` sin
  secciones `Args:`/`Raises:`; `_save_db_record(model)` sin type hint en
  `model`; `_update_chunk_ids` hace N+1 queries por chunk.

---

# Sesión 10: reorganización del guardado de resultados del benchmark (formato incremental por carpetas, mapeo por `id`) + doc tras el rename `benchmarks/` → `app/`

## Objetivo

Dos tareas encargadas por el equipo, en la misma sesión:

1. **Arreglar el formato de guardado de los resultados del benchmark.** El
   formato de la Sesión VI producía demasiadas subcarpetas (`logs/`,
   `details/`) y, sobre todo, los resultados consolidados
   (`suite_result.json`, `component_results.csv`, `pipeline_results.csv`)
   solo se exportaban **al final del run completo** — si el proceso moría a
   mitad, se perdía todo lo ya ejecutado (solo los `logs/*.jsonl` crudos eran
   incrementales). Se pidió:
   - Una carpeta de run `results/[fecha-hora]/` con un `config.json` en la
     raíz (fecha, hora, plataforma, configuración del benchmark, etc.).
   - Subcarpetas `components/<tipo>/` y `pipelines/<N - nombre>/`.
   - Cada subcarpeta con: un CSV de resultados, un JSON con cada configuración
     utilizada (config **completamente detallada**, incluidos parámetros
     recursivos) y otro JSON que declare cada input y output.
   - **Mapeo por `id`** entre los JSONs y el CSV.
   - **Escritura incremental**: escribir a cada iteración, a cada turno,
     apenas se producen los resultados, sin esperar al final — para no perder
     datos si el proceso muere.
2. **Actualizar la documentación** tras el rename del paquete
   `RAG_benchmark/benchmarks/` → `RAG_benchmark/app/` (renombrado por el
   usuario; el código ya importaba `RAG_benchmark.app.*`).

## Archivos modificados

**Parte A — nuevo formato de resultados.** Las rutas se listan con la
ubicación final tras el rename (`app/`; antes `benchmarks/`).

| Archivo                                                                     | Acción                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| --------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `RAG_benchmark/app/store.py`                                                | **Creado** — `JsonStore` (persistencia atómica temp+rename de un dict keyed por id, `set()`/`load()` con `log.warning` ante JSON corrupto), `atomic_write_json()` (con `flush`+`fsync`), `csv_single_line()`, `append_csv_row()`. Constantes compartidas `RESULTS_CSV_FILENAME`/`CONFIGS_JSON_FILENAME`/`IO_JSON_FILENAME`.                                                                                                                                                               |
| `RAG_benchmark/app/pipelines/writer.py`                                     | **Creado** — `PipelineResultsWriter`: por carpeta de pipeline escribe `results.csv` (una fila por turno con `id,run_id,...`), `configs.json` (`{iter{n}: config redactada}`) e `io.json` (`{iter{n}-turn{m}: {inputs, outputs}}`).                                                                                                                                                                                                                                                        |
| `RAG_benchmark/app/config.py`                                               | **Modificado** — `LOGS_DIR_NAME`/`DETAILS_DIR_NAME` → `COMPONENTS_DIR_NAME="components"`, `PIPELINES_DIR_NAME="pipelines"`, `CONFIG_FILENAME="config.json"`; propiedades `logs_dir`/`details_dir` → `components_dir`/`pipelines_dir`.                                                                                                                                                                                                                                                     |
| `RAG_benchmark/app/output.py`                                               | **Modificado** — `RunDirectory` (root, components_dir, pipelines_dir, run_id, config_path); `create_run_directory` crea `components/`+`pipelines/`; `write_run_config()` (config.json con `completed:false`, `end_time:null`, environment, extra) y `update_run_config()` (no-op si falta el archivo, regenera payload si está corrupto); eliminados `build_initial_metadata`/`build_final_metadata`/`write_run_metadata`.                                                                |
| `RAG_benchmark/app/benchmark_utils.py`                                      | **Modificado** — `BenchmarkLogger(output_dir)` reescrito: escribe `results.csv` (columnas con `id`) + `configs.json` + `io.json`; `log(result, config, inputs, outputs)` asigna id contador `0001...`, persiste JSONs antes que CSV y devuelve el id. `run_configs()` registra config/inputs/outputs en cada ejecución (incluida la rama `skipped`). Eliminados `log_detailed_run`/`details_path`/`read_benchmark_csv`. `load_last_run_statuses()` intacta (sigue escaneando `**/*.csv`). |
| `RAG_benchmark/app/components/runner.py`                                    | **Modificado** — `COMPONENT_FOLDER_NAMES = {chunking→chunking, retrieval→retrievers, embedding→embeddings, llm→llms}`; el logger se crea en `config.components_dir/<carpeta>`.                                                                                                                                                                                                                                                                                                            |
| `RAG_benchmark/app/pipelines/base.py`                                       | **Modificado** — `_execute_turn` conserva `user_msg` en turnos fallidos; `run_pipeline(pipeline_index=1)` escribe `configs.json[iter{n}]` **siempre** (aunque `config_fn` falle), escribe una fila por turno, y ante fallo antes del primer turno registra marcador `iter{n}-error` vía helper `_write_failed_iteration()`; guard `config_fn` que devuelva no-dict → `{}`. `config_fn` tipado `Callable[[int], dict[str, Any]]`.                                                          |
| `RAG_benchmark/app/pipelines/runner.py`                                     | **Modificado** — pasa `pipeline_index=i+1` a `run_pipeline`.                                                                                                                                                                                                                                                                                                                                                                                                                              |
| `RAG_benchmark/app/cli.py`                                                  | **Modificado** — usa `write_run_config`/`update_run_config`; eliminadas las exportaciones finales (`export_to_json`, `export_component_results_to_csv`, `export_pipeline_results_to_csv`); imprime las carpetas creadas.                                                                                                                                                                                                                                                                  |
| `RAG_benchmark/app/report.py`                                               | **Modificado** — solo `print_summary`; eliminados los exports finales.                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `RAG_benchmark/tests/test_benchmark_output.py`                              | **Modificado** — reescrito al nuevo layout (carpeta de run, colisión, `BenchmarkLogger` nuevo, config.json start/end, statuses sobre el nuevo CSV).                                                                                                                                                                                                                                                                                                                                       |
| `RAG_benchmark/tests/test_benchmark_pipeline_helpers.py`                    | **Modificado** — test de `PipelineResultsWriter`; **+3 tests de regresión**: `_write_failed_iteration` escribe marcador, `run_pipeline` con `config_fn` que lanza deja rastro en disco, y `config_fn` no-dict no aborta.                                                                                                                                                                                                                                                                  |
| `RAG_benchmark/docs/04-execution-flow.md`, `05-configuration-and-output.md` | **Modificados** — secciones de salida al nuevo layout (config.json, components/, pipelines/, escritura incremental, mapeo por id, marcador `iter{n}-error`).                                                                                                                                                                                                                                                                                                                              |

**Parte B — documentación tras el rename `benchmarks/` → `app/`.**

| Archivo                                                                              | Acción                                                                                                                                                      |
| ------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `RAG_benchmark/app/cli.py`                                                           | **Modificado** — docstring de uso: `python -m RAG_benchmark.app.cli`.                                                                                       |
| `RAG_benchmark/docs/README.md`                                                       | **Modificado** — referencia obsoleta a "JSONL" → "(CSV, JSON)".                                                                                             |
| `RAG_benchmark/docs/00-scope-and-boundaries.md`                                      | **Modificado** — eliminadas las filas de `run_benchmark.py`/`run_pipeline_benchmark.py` (wrappers que ya no existen).                                       |
| `RAG_benchmark/docs/01-overview.md`                                                  | **Modificado** — tablas `benchmarks/*` → `app/*`; descripciones de `BenchmarkLogger` (ya no "CSV+JSONL") y `report.py` (ya no "JSON, CSV exports").         |
| `RAG_benchmark/docs/02-component-benchmarks.md`                                      | **Modificado** — comandos CLI → `RAG_benchmark.app.cli`; módulos → `app/components/*`; `--skip-passes`: `logs/*.csv` → `components/<category>/results.csv`. |
| `RAG_benchmark/docs/03-pipeline-benchmarks.md`                                       | **Modificado** — `conversation.py` → `app/conversation.py`.                                                                                                 |
| `RAG_benchmark/docs/04-execution-flow.md`                                            | **Modificado** — comandos CLI → `RAG_benchmark.app.cli`; rutas de módulo → `app/...`.                                                                       |
| `RAG_benchmark/docs/05-configuration-and-output.md`                                  | **Modificado** — las 10 invocaciones `python -m RAG_benchmark.benchmarks.cli` → `RAG_benchmark.app.cli`.                                                    |
| `RAG_benchmark/tests/test_benchmark_output.py`, `test_benchmark_pipeline_helpers.py` | **Modificados** — docstrings con ruta de módulo → `RAG_benchmark/app/...`.                                                                                  |

## Estado alcanzado

1. **Nuevo layout por run** (la raíz es la fecha/hora):

   ```
   RAG_benchmark/results/<YYYYMMDD_HHMMSS>/
     config.json                 ← run_id, command, start/end_time, completed,
     │                             config completa, environment, extra, summary
     components/
       chunking/  retrievers/  embeddings/  llms/
         results.csv             ← id,timestamp,component_type,component_class,
         │                         model_name,config_name,status,time_seconds,
         │                         first_load_time,error_message
         configs.json            ← {id: config completa con params recursivos}
         io.json                 ← {id: {inputs, outputs}}
     pipelines/
       <N> - <pipeline_name>/
         results.csv             ← una fila por turno: id,run_id,pipeline_name,
         │                         iteration,turn_number,user_message,
         │                         assistant_response,... ,retrieved_chunks,error
         configs.json            ← {iter{n}: config redactada}
         io.json                 ← {iter{n}-turn{m}: {inputs, outputs}}
   ```

2. **Escritura incremental real**: cada ejecución de componente (`logger.log`),
   cada iteración de pipeline (`configs.json[iter{n}]` al inicio) y cada turno
   (`append_turn`) persiste al momento: JSON stores con escritura atómica
   (temp+rename) y CSV por append. Si el proceso muere, todo lo ya producido
   queda en disco.

3. **Mapeo por `id`**: componentes → contador `0001...` por carpeta (misma id
   en la fila CSV, en `configs.json` y en `io.json`); pipelines → `iter{n}`
   para la config del run y `iter{n}-turn{m}` para cada turno (la fila CSV
   lleva `id` y `run_id`).

4. **Iteraciones fallidas nunca se pierden**: si `config_fn` o la creación de
   sesión fallan antes del primer turno, se persiste la config (parcial/`{}`) y
   un marcador `iter{n}-error` en `io.json` + una fila en el CSV. Fix CRITICAL
   detectado en code review (el fallo de iteración no dejaba rastro en disco).

5. **`config.json` crash-safe**: escrito al inicio con `completed:false`,
   `end_time:null`; actualizado al final con `completed:true`, `end_time` y
   `summary`. `update_run_config` es no-op si falta el archivo y regenera el
   payload si está corrupto.

6. **Secrets redactados**: la config del pipeline se persiste tras
   `_redact_secrets` (los `api_key`/`API_key` quedan `""`) en `configs.json`.

7. **`--skip-passes` compatible**: `load_last_run_statuses` sigue escaneando
   `**/*.csv` recursivamente; el nuevo `components/<cat>/results.csv` conserva
   las columnas que lee y las filas de pipelines (sin columna `status`) se
   descartan.

## Verificación

- **Tests**: `python -m pytest RAG_benchmark/tests/` → **32 passed** (incluye
  los 3 tests de regresión nuevos del path de fallo).
- **Ruff**: `ruff check` limpio en todos los archivos tocados; los 17 avisos
  restantes son **pre-existentes** en `conversation.py` y `pipelines/configs.py`
  (no modificados).
- **Code review**: 1 Critical (iteración fallida sin rastro en disco) +
  3 Warnings (guard no-dict en `config_fn`, docs del marcador, tests de
  regresión) → corregidos; re-review **APROBADO** (0 Critical, 0 Warnings).
- **QA flow-tester**: 7/7 escenarios PASS (mapeo por id, escritura incremental
  real, iteración fallida, crash-safety de `config.json`, `JsonStore` corrupto,
  redacción de secrets, `--skip-passes`). 0 Critical/High; 3 Medium
  documentados (ver Pendientes).
- **Smoke tests** (independientes): layout end-to-end (config.json +
  components/ + pipelines/), iteración fallida escribe `iter{n}-error`,
  iteración exitosa escribe por turno, run_pipeline con `_FakeClient`.
- **CLI**: `python -m RAG_benchmark.app.cli --help` funciona (comandos
  `components` y `pipelines`).

## Decisiones y hallazgos relevantes

- **Un `configs.json` y un `io.json` por carpeta, indexados por `id`** (no un
  JSON por ejecución): interpretación de "un json [que declare] cada
  configuración utilizada / cada input-output". Alternativa (un JSON por
  ejecución) quedó como posible ajuste menor.
- **Carpetas de componentes**: `retrieval→retrievers`, `llm→llms`,
  `embedding→embeddings`, `chunking→chunking` (nombres plurales legibles).
- **Orden de escritura JSON-antes-CSV**: si el proceso muere entre escrituras,
  los JSON stores (con los datos completos) quedan y la fila CSV puede faltar;
  se prefirió a lo inverso (filas CSV sin su config/io).
- **Rename `benchmarks/` → `app/`**: lo realizó el usuario; el código ya
  importaba `RAG_benchmark.app.*`. La documentación (docs del benchmark,
  docstrings de `cli.py` y de los tests) se alineó al nuevo paquete; también se
  limpiaron referencias obsoletas (wrappers `run_benchmark.py`/
  `run_pipeline_benchmark.py` eliminados, "JSONL" inexistente, `logs/*.csv`).
- **`RAG_benchmark/` está en `.gitignore`**: todos los cambios del benchmark de
  esta sesión (y de sesiones previas) no aparecen en `git status`. Los únicos
  cambios trackeados relevantes serían los de `docs/RAG/backlog.md`.
- **No se usó git** durante la sesión (por instrucción del equipo: hay muchas
  sesiones sin commitear, previas y posteriores a esta).

## Pendientes detectados (fuera de alcance de esta sesión)

- **M1 (flow-tester)**: `append_turn`/`append_csv_row` no es idempotente — si
  se re-ejecuta sobre una carpeta existente se duplican filas CSV (el CLI
  siempre crea carpeta nueva por run, por lo que el flujo normal no lo
  dispara).
- **M2 (flow-tester, pre-existente)**: `load_last_run_statuses` pierde en
  silencio las filas posteriores a una fila CSV corrupta dentro del mismo
  archivo.
- **M3 (flow-tester)**: `writer.write_config` no está protegido con
  `try/except` — un fallo de persistencia (p. ej. disco lleno) aborta el run
  completo (intencional: los errores de escritura deben ser ruidosos).
- **`_redact_secrets` solo redacta claves exactas** `api_key`/`API_key`;
  variantes (`apiKey`, `token`, `secret`) quedarían expuestas en `configs.json`
  (heredado de la Sesión VI).
- **Ruff pre-existente** en `RAG_benchmark/` (`conversation.py`,
  `pipelines/configs.py`): líneas largas/trailing whitespace, no tocado por ser
  pre-existente y estar el directorio en `.gitignore`.

---

# Sesión 11: benchmark de pipelines — todos los documentos en cada sesión + `--skip-passes` en `pipelines`

## Objetivo

Dos tareas encargadas por el equipo, en la misma sesión, tras el reporte de un
error de CLI:

1. **Corregir el error `No such option: --skip-passes`** al ejecutar
   `py -m RAG_benchmark.app.cli pipelines --skip-passes`. El flag solo existía
   en el comando `components`, no en `pipelines`.
2. **Cargar TODOS los documentos del corpus en TODAS las sesiones de pipeline**
   (escenario RAG realista). Antes, cada iteración usaba **un solo documento**
   (`_select_document_id` ciclaba por papers: `document_ids[iteration % len]`);
   ahora cada sesión recibe el corpus completo.
3. **Implementar `--skip-passes` para `pipelines`** (granularidad **pipeline
   completo**): si en el run más reciente todas las iteraciones de un pipeline
   pasaron, se salta y se registra un resultado explícito `skipped=True`.

**Contexto:** el benchmark de componentes ya tenía `--skip-passes`
(`load_last_run_statuses` + `run_configs` con `skip_statuses`). El benchmark de
pipelines no lo tenía y la mecánica no era portable: los resultados de pipelines
se guardan por **turno** (`pipeline_name`, `run_id`, `error`) sin un status
`passed` persistido, y la clave del pipeline (`pub1`) no se guarda en el CSV
(solo el nombre del registry en `pipeline_name`).

## Archivos modificados

Todos dentro de `RAG_benchmark/` (directorio en `.gitignore`), salvo
`docs/RAG/backlog.md`.

| Archivo                                                     | Acción                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ----------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `RAG_benchmark/app/pipelines/configs.py`                    | **Modificado** — firmas `get_pubX_config(doc_ids: List[int])` con `"documents": list(doc_ids)`; `get_pub3_config(doc_ids)` delega en `get_pub1_config(doc_ids)`; docstrings Google-style.                                                                                                                                                                                                                                                                                                                                                                              |
| `RAG_benchmark/app/pipelines/base.py`                       | **Modificado** — eliminada `_select_document_id`; `run_pipeline` acepta `config_fn: Callable[[List[int]], Dict[str, Any]]`, pasa `list(self._document_ids)` en cada iteración (log "using N documents") y construye el resultado con `document_ids=list(self._document_ids)`; docstrings del módulo y de `run_pipeline` actualizados (cada sesión = conversación independiente sobre el corpus completo).                                                                                                                                                              |
| `RAG_benchmark/app/models.py`                               | **Modificado** — `PipelineRunResult.document_id: int` → `document_ids: List[int]`; añadido `skipped: bool = False`.                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `RAG_benchmark/app/config.py`                               | **Modificado** — eliminado el campo muerto `test_document_id` (remanente del flujo de documento único).                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `RAG_benchmark/app/benchmark_utils.py`                      | **Modificado** — nueva `load_passed_pipelines(results_dir) -> set[str]`: escaneo recursivo `**/results.csv` (usa la constante `RESULTS_CSV_FILENAME`), agrupa por `pipeline_name → run_folder → run_id` con `(total_rows, error_rows)`, evalúa solo el run más reciente (`parents[2]`, timestamp lexicográfico), pipeline pasa si todas sus iteraciones pasaron (≥1 turno y no todos con error = fallo parcial cuenta como passed, replicando `_pipeline_success`); tolera CSV corruptos y filas sin `pipeline_name`/`run_id` (los CSV de componentes no interfieren). |
| `RAG_benchmark/app/pipelines/runner.py`                     | **Modificado** — `run_pipeline_benchmarks` particiona `pipeline_keys` en skipped (`PipelineRunResult(skipped=True)`) y `to_run` (conserva índice original para `pipeline_index`); `runner.setup()` solo si hay algo que correr; summary con `successful`/`skipped`/`failed`; **fix**: el summary de error ya no se sobrescribe (antes una excepción en `setup()` se tragaba y el run se marcaba `completed:true`); `skip_passes` añadido a `config_snapshot`.                                                                                                          |
| `RAG_benchmark/app/cli.py`                                  | **Modificado** — flag `--skip-passes` en `pipelines` (pasado a `_make_config`), print "Skip passed", docstring de `_make_config` ampliado (componentes y pipelines), help de `--iter` actualizado (conversaciones independientes, no ciclado de papers).                                                                                                                                                                                                                                                                                                               |
| `RAG_benchmark/app/report.py`                               | **Modificado** — `print_summary` cuenta `skipped` y muestra `SKIPPED (already passed)`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `RAG_benchmark/tests/test_benchmark_pipeline_helpers.py`    | **Modificado** — quitados import y tests de `_select_document_id`; `_boom(doc_ids)` y `config_fn=lambda doc_ids: None`; nuevo `test_run_pipeline_passes_all_documents_to_config_fn` (verifica que `config_fn` recibe `[10, 20, 30]`, que `results[0].document_ids == [10, 20, 30]` y que el payload POSTeado de sesión lleva `"documents": [10, 20, 30]`).                                                                                                                                                                                                             |
| `RAG_benchmark/tests/test_pipeline_configs_schema_valid.py` | **Modificado** — `config_fn(1)` → `config_fn([1])`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `RAG_benchmark/tests/test_pipeline_skip_passes.py`          | **Creado** — 9 tests: `load_passed_pipelines` (todas pasan, iteración fallida no pasa, fallo parcial = passed, latest run wins, ignora CSV de componentes, tolera CSV corrupto) + flujo completo del runner (skip sin setup verificado con `mock`, `skip_passes=False` no salta, mezcla skip+run con `PipelineBenchmarkRunner` mockeado).                                                                                                                                                                                                                              |
| `RAG_benchmark/docs/03-pipeline-benchmarks.md`              | **Modificado** — paso 4 del flujo: carga del corpus completo (`config_fn(doc_ids)`), no ciclado de papers.                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| `RAG_benchmark/docs/04-execution-flow.md`                   | **Modificado** — `config_fn(doc_ids)` con todos los papers.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `RAG_benchmark/docs/05-configuration-and-output.md`         | **Modificado** — tabla CLI de `pipelines` con `--skip-passes` + ejemplo; campo `document_ids` y `skipped` en el data model `PipelineRunResult`; eliminada fila `test_document_id`.                                                                                                                                                                                                                                                                                                                                                                                     |

## Estado alcanzado

1. **Error de CLI explicado y resuelto** — `--skip-passes` solo estaba definido
   en `components` (ya funcionaba como "salta componentes cuyo último estado fue
   `passed`"). Con esta sesión el flag existe también en `pipelines`.

2. **Corpus completo por sesión** — cada iteración crea una conversación
   independiente sobre **todos** los papers de `RAG_benchmark/papers/` (8 PDFs).
   La key de skip por iteración (pipeline+paper) quedó obsoleta: al ser idéntico
   el corpus en todas las sesiones, la unidad natural de skip pasó a ser el
   **pipeline completo**.

3. **`--skip-passes` en pipelines** — `load_passed_pipelines()` decide qué
   pipelines ya pasaron (run más reciente, todas las iteraciones sin fallo
   total). Los pipelines saltados se registran como `PipelineRunResult(skipped=True)`
   explícitos, se cuentan en `summary.skipped` y se imprimen como
   `SKIPPED (already passed)`. Si todo está pasado, no se ejecuta `setup()`
   (no requiere papers).

4. **Fixes de robustez en el camino** — el summary de error de `run_pipeline_benchmarks`
   ya no se sobrescribe (un fallo de `setup()` dejaba antes un `config.json` con
   `completed:true`); `load_passed_pipelines` usa `parents[2]` (el folder de run
   real, no `<RUN>/pipelines`); campo muerto `test_document_id` eliminado.

## Verificación

- **Tests**: `py -m pytest RAG_benchmark/tests/` → **40 passed** (incluye los 9
  de `test_pipeline_skip_passes.py` y el nuevo test de payload de documentos).
- **Ruff**: `ruff check` limpio en todos los archivos modificados (los 5 E501
  restantes en `pipelines/configs.py` son pre-existentes, líneas de dict no
  tocadas).
- **CLI**: `py -m RAG_benchmark.app.cli pipelines --help` muestra
  `--skip-passes` y el nuevo help de `--iter`.
- **Code review** (2 rondas): la 1ª aprobó el cambio de corpus completo con 5
  Warnings (docs obsoletas + campo muerto) → corregidos; la 2ª (skip-passes)
  aprobó con 4 Warnings (off-by-one de `parents`, summary de error sobrescrito,
  docstring de fidelidad, test de no-setup débil) → corregidos, incluyendo tests
  reforzados.

## Decisiones y hallazgos relevantes

- **Granularidad de skip cambió por el corpus completo**: la decisión previa de
  skip por iteración (pipeline+paper) perdió sentido cuando todas las sesiones
  usan el mismo corpus; se adoptó **pipeline completo** (todas las iteraciones
  del run más reciente pasaron).
- **El CSV de pipelines no guarda la clave `pubX`** — solo el `pipeline_name`
  del registry (p. ej. "Publication 1 - Medical Fitness"); `load_passed_pipelines`
  devuelve nombres del registry y el runner mapea `entry["name"]`.
- **Semántica de éxito en disco**: una iteración pasó si tiene ≥1 turno y no
  TODOS los turnos tienen error (fallo parcial = success, igual que
  `_pipeline_success` en `base.py`). Limitación documentada: un run interrumpido
  con iteraciones faltantes se cuenta solo por las iteraciones registradas.
- **`RAG_benchmark/` está en `.gitignore`**: todos los cambios de la sesión son
  locales (no aparecen en `git status`).
- **No se usó git** durante la sesión (por instrucción del equipo: hay muchas
  sesiones sin commitear, previas y posteriores a esta).

## Pendientes detectados (fuera de alcance de esta sesión)

- **`run_pipeline` supera las ~30 líneas** (preexistente): conviene extraer el
  cuerpo de cada iteración a un helper (`_run_iteration(...)`).
- **Fidelidad de `load_passed_pipelines` a `_pipeline_success`** en el caso
  teórico de `pipeline_error` + turnos parciales (casi inalcanzable en la
  práctica, pero la docstring ya no afirma una réplica fiel).
- **E501 pre-existentes** en `pipelines/configs.py` (líneas de dict no tocadas).

---

# Sesión 12: fix de "no hay chunks recuperados" en el benchmark de pipelines (espacio de IDs del retriever denso)

## Objetivo

Resolver el problema reportado por el usuario: en los resultados del benchmark
de pipelines RAG la columna `chunks_retrieved` salía en `0` y `retrieved_chunks`
en `{}` para la **Publication 2 - EHR Summarization**
(`RAG_benchmark/results/20260805_203444/pipelines/2 - Publication 2 - EHR Summarization/results.csv`),
mientras que el resto de publicaciones (retriever denso directo o BM25) sí
guardaban chunks. La búsqueda concluyó que el bug era del **código RAG**, no del
benchmark ni del frontend.

**Diagnóstico preliminar (descartado):** se verificó que el pipeline RAG produce
chunks correctamente en el flujo normal (TFIDF, BM25, denso directo, MMR con
embeddings mock), que el frontend (`GenerativeChat` → `SourcesDisplay`) parsea y
muestra bien los chunks guardados, y que los procesos de una BD real de usuario
guardaban el JSON completo de chunks. El problema se manifestaba **solo** con
retrievers compuestos sobre un child denso (MMR, Sequential, Parallel,
CrossEncoder) en una BD persistente.

## Causa raíz

Existen **dos identificadores de chunk** distintos que el código mezclaba:

- `Chunk.id` — la **PK de base de datos** (autoincrement global en `chunk`).
- La **clave del dict** `self.chunks[doc_id]` — el **índice** del chunk
  (0-based dentro del documento).

`DenseRetriever.init_similarity_matrix()` indexaba su matriz de similitud por la
clave del dict (índice). Pero los retrievers compuestos (MMR reranker,
Sequential, Parallel, CrossEncoder) llaman a `child.score_chunks(c.id, ...)` y
`child.get_chunk_vectors(c.id, ...)` con `Chunk.id` (la PK). Los retrievers
**sparse** (TFIDF, BM25) ya usaban `c.id` de forma consistente, por eso solo el
child denso fallaba.

En una BD persistente (el benchmark reutiliza `RAG_benchmark/data/db.sqlite` y
los `id` de `chunk` son autoincrement globales que no coinciden con los
índices), `score_chunks` devolvía `[]` → el MMR se quedaba sin candidatos
puntuados → `ordered` vacío → `retrieve()` devolvía `[]` → el pipeline guardaba
`{}`. En BDs frescas pequeñas los ids coincidían por casualidad (id = índice + 1
en el primer chunk set), lo que enmascaraba el bug en tests y reproducciones
locales.

**Evidencia en la BD del benchmark** (`RAG_benchmark/data/db.sqlite`): las
sesiones 7–9 (Pub 2, MMR) tienen sus `ProcessData` de tipo `Dict` con `data =
'{}'` (dlen=2) en TODOS los turnos, mientras que las sesiones de Pub 1/3/4a/4b
(retriever denso directo o BM25) guardan dicts con decenas de chunks. En
`chunk`, los ids son globales (1..26801) y no coinciden con `chunk_index`.

## Archivos modificados

| Archivo                                                                      | Acción                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `DashAI/back/models/RAG/retrievers/dense/dense_retriever.py`                 | **Modificado** — `init_similarity_matrix()` indexa las filas por `chunk.id` (PK) en lugar de la clave del dict; añade `_chunk_key_by_id: {id → (doc_id, dict_key)}` para resolver la búsqueda en `retrieve()`; `retrieve()` usa `_chunk_key_by_id` en vez de `chunk_id_to_doc_id[chunk_id]` + `self.chunks[doc_id][chunk_id]`. `score_chunks()` y `get_chunk_vectors()` quedan consistentes automáticamente porque ya construían el mapa `{matrix_row_to_chunk_id[r]: r}` (ahora con PKs). |
| `DashAI/back/models/RAG/retrievers/cross_encoder/cross_encoder_retriever.py` | **Modificado** — mismo bug latente en `score_chunks()`: `chunk_map` se construía con `doc_chunks.update()` (claves = índices) y recibía PKs; ahora se indexa por `chunk.id`.                                                                                                                                                                                                                                                                                                               |
| `tests/back/RAG/test_dense_retriever_id_space.py`                            | **Creado** — tests de regresión: chunks con `id = 500 + índice` (ids ≠ índices); `test_dense_retriever_scores_chunks_by_db_id` (score_chunks con los ids devueltos por retrieve no vacío) y `test_mmr_reranker_returns_chunks_with_dense_child` (MMR sobre child denso devuelve 5 chunks). Fallan con el código previo y pasan con el fix.                                                                                                                                                 |

No se modificó ningún archivo extra (ni el benchmark, ni el frontend, ni la
capa de servicios); el bug se resolvió únicamente en los retrievers.

## Estado alcanzado

1. **El retriever denso indexa su matriz por `Chunk.id`** (PK), alineado con el
   resto de retrievers y con lo que los compuestos pasan a `score_chunks` /
   `get_chunk_vectors`. `retrieve()` mantiene su comportamiento (devuelve los
   `Chunk` correctos) vía el mapa auxiliar `_chunk_key_by_id`.

2. **Los retrievers compuestos vuelven a funcionar sobre child denso** con
   cualquier BD (fresca o persistente): MMR, Sequential, Parallel y CrossEncoder
   recuperan y puntúan chunks correctamente.

3. **Verificación reproducida antes/después** con chunks de ids corridos
   (`id = 500 + idx`): antes `score_chunks → 0` y `MMR.retrieve → 0`; después
   `score_chunks → 10` y `MMR.retrieve → 5` con ids/posiciones correctas.
   Además, end-to-end por `SetupService` con MMR + DenseEmbeddingRetriever y la
   BD con autoincrement desplazado (3 documentos dummy antes del real):
   `chunks in output: 5` (escenario idéntico a la Pub 2 del benchmark).

## Verificación

- **Tests RAG completos**: `pytest tests/back/RAG/` → **169 passed** (incluye
  los 2 tests nuevos de regresión). Sin regresiones.
- **Tests de regresión**: fallan con el código previo (`2 failed`) y pasan con
  el fix (`2 passed`), confirmando que son una regresión real.
- **Ruff**: `ruff check` y `ruff format --check` limpios en los 3 archivos
  tocados/creados.
- **Evidencia empírica**: la BD del benchmark (`RAG_benchmark/data/db.sqlite`)
  muestra que las sesiones de Pub 2 (MMR + denso) guardaban `{}` de chunks
  mientras las demás publicaciones guardaban dicts completos; el fix ataca
  exactamente esa divergencia.

## Decisiones y hallazgos relevantes

- **El bug estaba en el espacio de IDs del retriever denso**, no en el
  benchmark ni en el frontend. El benchmark solo lo expone al usar una BD
  persistente donde los `id` de `chunk` (autoincrement global) no coinciden con
  `chunk_index`. Un usuario lo reproduciría creando una sesión con un retriever
  compuesto (MMR/Sequential/Parallel/CrossEncoder) sobre un child
  `DenseEmbeddingRetriever` en una instalación con datos previos.
- **Por qué no se detectó antes**: los tests existentes del cross-encoder y los
  retrievers usan `Chunk(id, doc_id, chunk_id, ...)` (id == índice), y las BDs
  frescas pequeñas dan ids ≈ índice+1 (off-by-one que solo excluía el chunk 0 y
  el último). El `_FakeChildRetriever` de los tests además implementaba
  `score_chunks` con los ids que recibía, sin pasar por la lógica del denso.
- **Los sparse ya eran consistentes** (`matrix_row_to_chunk_map` guarda los
  `Chunk` y `chunk_id_to_row = {c.id: r ...}`), por eso el bug solo afectaba al
  denso.
- **`Chunk.id` siempre está seteado** cuando se construye el retriever: en el
  camino fresco `_persist_chunks_and_update_ids` muta `model.chunks[doc][idx].id`
  (mismo dict que `chunking_result.chunks`), y en el camino cacheado
  `_fetch_chunks_from_db` crea los `Chunk` con `id=db_chunk.id`.
- **`RAG_benchmark/` está en `.gitignore`**: la evidencia del benchmark es local
  (no trackeada). Los cambios trackeados de la sesión son `dense_retriever.py`,
  `cross_encoder_retriever.py` (untracked por ser módulo nuevo de sesiones
  previas) y el test nuevo (untracked).
- **No se usó git** durante la sesión (por instrucción del equipo: hay muchas
  sesiones sin commitear, previas y posteriores a esta).

## Pendientes detectados (fuera de alcance de esta sesión)

- **Re-ejecutar el benchmark de pipelines** para la Pub 2 (y cualquiera con MMR
  u otro compuesto sobre child denso) y confirmar que `chunks_retrieved` ya no
  sale en 0. El fix corrige el código; los resultados CSV antiguos
  (`20260805_203444`, etc.) quedaron con `{}` y deben regenerarse.
- **Los ids de los tests de retrievers** siguen usando `id == índice`
  (`_make_chunk`), lo que es menos fiel a producción; opcional migrarlos a ids
  corridos para cubrir el espacio de IDs en el resto de la suite.
- **`_chunk_key_by_id` no se persiste** (se reconstruye en
  `init_similarity_matrix` cada vez, igual que los mapas existentes); no es un
  problema porque el denso se reconstruye desde los chunks inyectados en cada
  build.

---

# Sesión 13: benchmark de pipelines RAG con e5-mistral-7b (crash de memoria), carpeta permanente de embeddings y cache de modelo

## Objetivo

Arreglar el benchmark de pipelines RAG (`pub4a`) que usaba
`intfloat/e5-mistral-7b-instruct` (7B parámetros) como embedding. En la máquina
del usuario (24 GB RAM, RTX 4060 Laptop 8 GB, torch 2.11 cu126) el run quedaba
**colgado o reiniciaba el PC** y nunca se guardaban las matrices de embeddings.
Además, hacer que los embeddings se **reciclen entre ejecuciones** (que queden
en una carpeta permanente en lugar de un temp que se borra al terminar).

**Restricción del usuario:** respetar el modelo `intfloat/e5-mistral-7b-instruct`
(la config de la tesis de RAGChecker Dense); solo se permite usar versiones más
pequeñas **dentro de la misma familia**, no cambiar de familia. De ser necesario
se ajusta el código de DashAI para que corra.

## Causas raíz (en orden de impacto)

1. **`AutoModel.from_pretrained` en `float32` = ~28 GB** (> 24 GB de RAM) → el
   PC se reiniciaba. El `script.py` de prueba funcionaba en CPU solo porque
   codificaba 2 queries; el benchmark embebe el corpus completo (1306 chunks).
2. **`float16` en CPU sigue siendo impracticable**: el encode del corpus con un
   modelo 7B en CPU no terminaba en ~1 h (parecía colgado), y por eso **no se
   creaba `RAG/embeddings/`** (los `.npy` se guardan después de codificar cada
   documento). No había bug de persistencia: los chunks sí se guardaban
   (`chunk = 1306` en DB), el problema era que el encode nunca terminaba.
3. **Recarga del modelo por turno**: cada `RAGJob` reconstruye el retriever →
   `DenseEmbeddingRetriever.init_model()` → `_embedding_instance.load()`.
   e5-mistral (14 GB fp16) se recargaba en cada turno; el 2º turno crasheaba en
   `Loading checkpoint shards: 0%` (agotamiento de memoria/VRAM acumulado). El
   primer turno de pub4a llegaba a completarse (respondía con 17-20 chunks).

## Archivos modificados

| Archivo                                                            | Acción                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DashAI/back/models/RAG/embeddings/dense/huggingface_embedding.py` | **Modificado** — params opcionales `torch_dtype` (`"float32"/"float16"/"bfloat16"`), `batch_size` (default 8) y `device_map` (default `None`; `"auto"` = offload GPU+CPU vía `accelerate`). `load()` usa `low_cpu_mem_usage=True` y carga los pesos en el dtype pedido (fp16 = 14 GB); con `device_map` no hace `.to(device)`. Mini-batching en `_encode_in_batches()` (acota la memoria de activaciones). **Cache de modelo en proceso** `_MODEL_CACHE` keyed por `(model_name, device, torch_dtype, device_map)` + `clear_model_cache()`: el 2º `load()` reusa el modelo sin recargar. Salida de pooling convertida a `float32`. |
| `DashAI/back/models/RAG/embeddings/dense/_overflow_handler.py`     | **Modificado** — acepta `torch_dtype`/`batch_size`/`device_map`, los pasa al base; guard de mini-batching en `_batch_encode_impl`; inputs no se mueven a `device` cuando hay `device_map`; salida a `float32`.                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `DashAI/back/models/RAG/embeddings/dense/_e5_embedding.py`         | **Modificado** — acepta y propaga `torch_dtype`/`batch_size`/`device_map`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `DashAI/back/models/RAG/embeddings/dense/e5_embedding.py`          | **Modificado** — `E5Embedding.__init__` lee `torch_dtype`/`batch_size`/`device_map` desde `kwargs` y los pasa al wrapper interno. **No se tocó `schema_field`** (instrucción del equipo): son claves extra que la validación Pydantic ignora, no campos del schema.                                                                                                                                                                                                                                                                                                                                                                |
| `tests/back/RAG/test_e5_embedding_memory.py`                       | **Creado** — tests de regresión: instanciación con los params extra, defaults sin ellos, mini-batching divide en sub-batches, `load()` con `low_cpu_mem_usage`+`dtype`, `load()` con `device_map` (sin `.to()`), **cache reutiliza el modelo** (2º `load()` no recarga), `torch_dtype` inválido lanza. Fixture autouse `clear_model_cache()` para aislar.                                                                                                                                                                                                                                                                          |
| `RAG_benchmark/app/config.py`                                      | **Modificado** (gitignored) — campo `data_dir` (default `RAG_benchmark/data`) — antes existía mal cableado (apuntaba a `papers`); ahora es la carpeta permanente de datos DashAI (DB + embeddings).                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `RAG_benchmark/app/cli.py`                                         | **Modificado** (gitignored) — opción `--data` en `components` y `pipelines`, propagada por `_make_config`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `RAG_benchmark/app/pipelines/base.py`                              | **Modificado** (gitignored) — `PipelineBenchmarkRunner` usa `config.data_dir` como `local_path` permanente (ya no `tempfile.mkdtemp`); documentos insertados **idempotente por hash de contenido** (`_paper_content_hash`, sha256 del archivo) para IDs estables entre runs; `teardown()` ya **no borra** la carpeta de datos; nombres de sesión con tag de run (`run <ts>, iter N`) para no colisionar con la `unique` de `generative_session.name` en la DB persistente.                                                                                                                                                         |
| `RAG_benchmark/app/pipelines/runner.py`                            | **Modificado** (gitignored) — `data_dir` añadido a `config_snapshot`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| `RAG_benchmark/app/pipelines/configs.py`                           | **Modificado** (gitignored) — embedding de pub4a: `device: "cuda"`, `torch_dtype: "float16"`, `batch_size: 16`, `device_map: "auto"`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| `RAG_benchmark/docs/03-pipeline-benchmarks.md`                     | **Modificado** (gitignored) — nota de memoria de pub4a (fp16 + device_map + mini-batch + cache + reciclaje).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `RAG_benchmark/docs/05-configuration-and-output.md`                | **Modificado** (gitignored) — `data_dir`/`--data` en tablas de config y CLI + nota de reciclaje.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `docs/RAG/backlog.md`                                              | **Modificado** — esta entrada.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |

## Estado alcanzado

1. **pub4a corre end-to-end** con e5-mistral en esta máquina (verificado con
   1 iter × 2 turnos): turnos con 17-20 chunks recuperados, ~50-70 s de
   generación Llama, sin errores. Antes: crash del PC en fp32 o colgado en CPU.

2. **Carpeta permanente + reciclaje de embeddings** — el benchmark corre sobre
   `RAG_benchmark/data` (sobrescribible con `--data`). Los documentos se keyean
   por hash de contenido (IDs estables entre runs), por lo que
   `rag_chunk_set`/`rag_embedding_model`/`rag_embedding_matrix` y los `.npy` se
   reutilizan: el corpus se embebe **una sola vez** y los runs siguientes cargan
   las matrices cacheadas (verificado: 2º run sin registros nuevos ni `.npy`
   reescritos).

3. **Cache de modelo en proceso** — cada turno reusa el e5-mistral ya cargado
   (GPU+CPU) en vez de recargar 14 GB → se eliminó el crash del 2º turno.

4. **Una matriz por (documento, chunk_set, modelo de embedding)** — confirmado
   con un repro de 2 sesiones con el mismo chunking pero MiniLM y e5-small:
   `embedding_model_id-1` y `-2` generan dos `.npy` distintos para el mismo
   documento (los `.npy` de `~/.DashAI/rag/embeddings/` que solo mostraban un
   `embedding_model_id-1` por doc eran **huérfanos** de runs muertos: archivos en
   disco sin registros en la DB).

## Verificación

- **Tests**: `RAG_benchmark/tests/` + `tests/back/RAG/` (incluidos
  `test_e5_embedding_memory.py`, `test_chunking_service.py`,
  `test_chunking_cache_integration.py`, configs API y session flow) → **108
  passed**; 0 regresiones. (Además 40 del benchmark en la pasada previa y 8 del
  test nuevo.)
- **Ruff**: `ruff check` y `ruff format --check` limpios en los archivos de
  DashAI y del benchmark tocados (los E501 restantes de `RAG_benchmark/` en
  `conversation.py` son pre-existentes y el directorio está en `.gitignore`).
- **Smoke real**: `run_pipeline_benchmarks(pipelines=['pub4a'], 1×2)` sobre
  `RAG_benchmark/data` → `success=True`, 2 turnos sin error, ~2 min; el run
  anterior (8 papers, chunking+encode) había quedado con las 24 matrices
  (8 docs × 3 modelos) commiteadas y se reusaron.
- **Tests de cache**: `test_load_reuses_cached_model` demuestra que el 2º
  `load()` con la misma key no vuelve a llamar `from_pretrained`.

## Decisiones y hallazgos relevantes

- **Respetar el modelo (decisión del usuario)**: no se cambió e5-mistral por una
  familia menor; el fix es de carga/ejecución (fp16 + offload + mini-batch +
  cache), no de modelo.
- **`device_map="auto"` fue aceptado tras una segunda consulta**: el usuario
  primero lo rechazó ("no hay que dividir entre GPU y CPU, hay un bug de chunks")
  porque creía que había un bug de persistencia. Se demostró que los chunks **sí**
  se guardaban y que el bloqueo era solo la velocidad del encode en CPU; tras
  ofrecer las opciones (offload GPU, cuantización 4-bit, esperar en CPU) eligió
  el offload. Medido: corpus de 1306 chunks en ~4.6 min con offload vs. 1 h+ sin
  terminar en CPU.
- **`schema_field` no se modificó** (instrucción del equipo): `torch_dtype`,
  `batch_size` y `device_map` se leen de `kwargs` en `E5Embedding.__init__` y son
  claves extra que la validación Pydantic ignora (default `extra='ignore'`).
- **La recarga por turno era el crash real de pub4a** (no el encode): el 1er
  turno cargaba el modelo y completaba; el 2º crasheaba en `Loading checkpoint
shards`. Se confirmó en el CSV de resultados (turnos 0-1 OK del run anterior).
- **Cache y ciclo de vida**: `RAGJob` sigue haciendo `del model;
torch.cuda.empty_cache(); gc.collect()` en `finally`; con la cache el modelo
  queda residente (referenciado en `_MODEL_CACHE`) — intencional para el
  benchmark. `clear_model_cache()` existe para tests/teardown.
- **Reciclaje y params del embedding**: la key del registro de modelo de
  embedding incluye TODOS los params del config; cambiar `torch_dtype`/
  `batch_size`/`device` entre runs crea un registro nuevo y re-embebe el corpus.
  Para forzar recomputo: borrar `RAG_benchmark/data`.
- **`~/.DashAI` vs benchmark**: los `.npy` del benchmark viven en
  `RAG_benchmark/data/RAG/embeddings/` (permanente, gitignored); los de la app
  normal en `~/.DashAI/RAG/embeddings/`. El benchmark ya no usa temp dirs
  (`dashai_benchmark_*`) que se borraban al terminar.
- **`RAG_benchmark/` está en `.gitignore`**: los cambios del benchmark (config,
  cli, base, runner, configs, docs) son locales; los cambios trackeados de la
  sesión son los 4 archivos de embeddings de DashAI y el test nuevo (untracked).
- **No se usó git** durante la sesión (por instrucción del equipo: hay muchas
  sesiones sin commitear, previas y posteriores a esta).

## Pendientes detectados (fuera de alcance de esta sesión)

- **Recarga del modelo a nivel de retriever**: aunque la cache elimina el reload
  por turno dentro del proceso, cada `RAGJob` reconstruye el retriever (crea una
  instancia nueva de `E5Embedding` que reusa el modelo cacheado). Si se quiere
  liberar el modelo entre pipelines de una misma ejecución habría que usar
  `clear_model_cache()` explícitamente (no se hace: se prefiere mantenerlo
  residente).
- **`RAG_benchmark/data` acumula sesiones/pipelines** entre runs (por la DB
  persistente); los runs antiguos dejan filas de `generative_session`/
  `generative_process`. No afecta a la ejecución (los nombres de sesión llevan
  tag de run), pero convendría una limpieza opcional.
- **Re-ejecutar el benchmark completo** (`pipelines`) ahora que pub4a ya no
  crashea, para regenerar resultados CSV de pub4a (los anteriores quedaron con
  `{}`/interrumpidos en `20260805_203444`).
- **`device_map="auto"` depende de `accelerate`** (ya instalado, 1.13.0); si la
  máquina no tiene GPU o la VRAM es menor, `device_map="auto"` seguiría
  funcionando con offload a CPU (más lento). Documentado en la config de pub4a.
- **Cuantiización 4-bit** (bitsandbytes) queda como alternativa pendiente no
  explorada (requiere instalar dependencia) para correr e5-mistral completo en
  GPU.

---

# Sesión 14: fix de la configuración avanzada de retrievers — solo aparecían los densos

## Objetivo

Arreglar que en la **vista de configuración avanzada de retrievers** del wizard
de sesión RAG (`RetrieverConfigurationStep.jsx`) solo aparecían los retrievers
**densos** en el dropdown; no aparecían los **sparse** (BM25, TF-IDF) ni los
**compuestos** (Sequential, Parallel, MMR, Cross-Encoder), tal como reportó el
usuario.

## Causa raíz

El endpoint `GET /v1/component/{name}/children/` **nunca devolvía `flags`** en su
respuesta. El frontend construye las opciones filtrando por `flags`:

- `RetrieverConfigurationStep.jsx` filtra `(c.flags || []).includes("keyword")`
  para los sparse y `("composite")` para los compuestos. Como `c.flags` siempre
  era `undefined`, ambos filtros daban listas **vacías** y solo quedaban los
  embeddings densos (que se incluyen sin depender de flags). Lo mismo ocurría con
  el filtro `abstract` de `RetrieverSection.jsx` y con el `groupBy` del
  autocomplete.

Los endpoints `/v1/component/` y `/v1/component/{id}/` ya soportaban
`include_flags` (commit `bc4222647`), pero el de children no se actualizó, y el
frontend jamás lo pedía.

**Fix secundario:** aunque los flags llegaran, `SentenceTransformerCrossEncoderRetriever`
no tenía el flag `"composite"` ni estaba en las listas de compuestos del frontend
(`COMPOSITE_NAMES`/`COMPOSITE_TYPES`), por lo que no aparecería en el grupo
compuesto. El backend ya lo trata como compuesto en `RAG_constants.py`
(`COMPOSITE_RETRIEVER_NAMES`).

## Archivos modificados

| Archivo                                                                                 | Acción                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `DashAI/back/api/api_v1/endpoints/components.py`                                        | **Modificado** — `get_child_components()` añade `include_flags: bool = Query(default=False)` y enriquece cada hijo con `_enrich_with_flags(child, include_flags)` antes de `_delete_class` (patrón consistente con `get_components` y `get_component_by_id`).                                                                                                                                                                                                                        |
| `DashAI/front/src/api/component.ts`                                                     | **Modificado** — `getChildComponents(componentName, recursive, includeFlags = false)` propaga `include_flags` como query param.                                                                                                                                                                                                                                                                                                                                                      |
| `DashAI/front/src/api/rag.ts`                                                           | **Modificado** — `getRetrievalParadigm()` y `getRetrieverComponents()` pasan `include_flags=true` (solo las llamadas de retrievers; chunking/prompts no lo necesitan).                                                                                                                                                                                                                                                                                                               |
| `DashAI/back/models/RAG/retrievers/cross_encoder/sentence_transformer_cross_encoder.py` | **Modificado** — `FLAGS` ahora incluye `"composite"` (antes solo `["cross_encoder", "sentence_transformer", "reranker"]`).                                                                                                                                                                                                                                                                                                                                                           |
| `DashAI/front/src/pages/generative/RAGSession/advanced/RetrieverConfigurationStep.jsx`  | **Modificado** — `SentenceTransformerCrossEncoderRetriever` añadido a `COMPOSITE_NAMES` (decide si se renderiza el `CompositeRetrieverBuilder`).                                                                                                                                                                                                                                                                                                                                     |
| `DashAI/front/src/pages/generative/RAGSession/advanced/CompositeRetrieverBuilder.jsx`   | **Modificado** — `SentenceTransformerCrossEncoderRetriever` añadido a `COMPOSITE_TYPES` (tratado como nodo compuesto en el árbol).                                                                                                                                                                                                                                                                                                                                                   |
| `DashAI/front/src/pages/generative/RAGSession/advanced/RetrieverNodeConfig.jsx`         | **Modificado** — `SentenceTransformerCrossEncoderRetriever` añadido a `COMPOSITE_TYPES` (agrupado como compuesto en el diálogo de nodo).                                                                                                                                                                                                                                                                                                                                             |
| `tests/back/api/test_components_api.py`                                                 | **Modificado** — 2 tests nuevos (`test_get_child_components_exclude_flags` / `include_flags`); registrados `TestParentComponent` (FLAGS `["abstract"]`) y `TestConcreteComponent` (FLAGS `["keyword","sparse"]`); actualizados 4 tests existentes afectados por los 2 componentes nuevos (conteos y aserciones de `test_get_all_components`, `test_get_components_select_tasks_and_models`, `test_get_components_related_with_some_task`, `test_get_components_by_type_and_task_2`). |

No se modificó ningún archivo extra: el fix es del backend de componentes (flags)

- el agrupamiento del frontend; la lógica de negocio RAG no se tocó.

## Estado alcanzado

1. **El endpoint de children devuelve flags** cuando se pide `include_flags=true`,
   alineado con el resto de endpoints de componentes. Por defecto (sin el param)
   no cambia el comportamiento: `false`.

2. **Dropdown de configuración avanzada completo**, verificado contra el registry
   real (los flags llegan tal cual a la UI):
   - **Sparse / keyword**: `BM25Retriever`, `TFIDFRetriever` → `["keyword","sparse"]`.
   - **Compuestos**: `SequentialRetriever`, `ParallelRetriever`,
     `MMRRerankerRetriever`, `SentenceTransformerCrossEncoderRetriever` →
     contienen `"composite"`.
   - **Dense**: embeddings (hijos de `DenseEmbedding`, filtrando `abstract`).

3. **Cross-encoder tratado como compuesto de forma consistente** entre backend
   (`FLAGS` + `COMPOSITE_RETRIEVER_NAMES`) y frontend (`COMPOSITE_NAMES` /
   `COMPOSITE_TYPES` en los 3 archivos). Al seleccionarlo se abre el
   `CompositeRetrieverBuilder` (necesario, porque su schema requiere estructura
   `children`).

4. **Beneficio colateral**: `RetrieverSection.jsx` (vista simple) filtra ahora
   correctamente las bases abstractas (`RetrieverModel`, `UnitRetriever`,
   `SparseRetriever`, `DenseRetriever`, `CompositeRetriever`,
   `CrossEncoderRetriever`), que antes aparecían como opciones por la ausencia de
   flags.

## Verificación

- **Tests**: `pytest tests/back/api/test_components_api.py` → **22 passed**
  (incluye los 2 nuevos del endpoint children; los 4 actualizados confirman que
  los componentes nuevos se registran sin romper el resto). Además
  `pytest tests/back -k "retriever or RAG or rag"` → **170 passed** (cero
  regresiones).
- **Smoke del registry real**: `get_child_components("RetrieverModel",
recursive=True)` con `_enrich_with_flags` devuelve BM25/TFIDF con
  `["keyword","sparse"]`, Sequential/Parallel/MMR/CrossEncoder con `"composite"`
  y DenseEmbeddingRetriever con `["dense","dense_embedding"]`.
- **Ruff**: `ruff check` y `ruff format --check` limpios en los archivos backend
  y el test.
- **Frontend**: `yarn eslint` sin errores en los 3 `.jsx` tocados (los `.ts` no
  están en el config de eslint) y `yarn prettier --check` limpio en los 5
  archivos.

## Decisiones y hallazgos relevantes

- **`include_flags` opt-in (default `False`)**: se mantuvo la convención de los
  otros endpoints de componentes en vez de activarlo por defecto. Las llamadas de
  chunking/prompts (`BaseChunkingModel`, `RAGGenerationPrompt`) siguen sin pedir
  flags; solo los retrievers los necesitan.
- **El bug era del endpoint children, no del registro**: todos los retrievers ya
  estaban registrados en `initial_components.py` con sus `FLAGS` correctos; la
  data nunca llegaba a la UI.
- **Doble inconsistencia del cross-encoder**: el backend (`RAG_constants.py`) ya
  lo trataba como compuesto pero no en `FLAGS`, y el frontend no lo listaba en
  ningún lado. Se corrigieron ambas puntas para que sea compuesto de forma
  coherente en toda la cadena (registro → API → dropdown → árbol).
- **Tests de registros**: `TestParentComponent`/`TestConcreteComponent` no pueden
  llevar "Base" en el nombre porque `ComponentRegistry._get_base_type` selecciona
  ancestros cuyo nombre contenga "Base" (rompería el registro con
  `TypeError: more than one base class`). Por eso se nombraron "Parent"/"Concrete".
- **El repo tiene muchas sesiones sin commitear**, previas y posteriores a esta.
  **No se usó git** (por instrucción del equipo).

## Pendientes detectados (fuera de alcance de esta sesión)

- **`allParadigms` como fallback de restauración**: `RetrieverConfigurationStep`
  recibe `allParadigms` (de `RetrieverSection`) como fallback al restaurar un
  modelo guardado, pero vuelve a fetchear sus propios datos. Con flags presentes
  la lista `merged` ya cubre todos los concretos; el fallback solo aplica a
  componentes que sigan faltando del merge (hoy ninguno). Opcional unificar la
  fuente de datos.
- **Derivar compuestos del registry**: las listas `COMPOSITE_NAMES`/
  `COMPOSITE_TYPES` del frontend siguen siendo por string (frágil ante un
  retriever compuesto nuevo). Alternativa: derivarlas del flag `"composite"` que
  ahora sí llega por la API (aunque el árbol necesita saber de antemano qué es
  compuesto para los hijos anidados).

---

# Sesión 15: mejora del árbol de la configuración avanzada de retrievers — tarjetas de operación, líneas del árbol y nombre del modelo de embedding

## Objetivo

Mejorar la **vista de configuración avanzada de retrievers** (el árbol de
`CompositeRetrieverBuilder.jsx` dentro del wizard de sesión RAG). Tres pedidos
del equipo:

1. **Mostrar los parámetros propios de cada retriever compuesto como tarjeta de
   operación final del árbol** — antes un cross-encoder o un MMR se veían como
   `SentenceTransformer Cross-Encoder` → `--child` (sin ninguna pista de sus
   parámetros). Se pidió algo como:

   ```
   MMR Reranker
   --child
   --reranking: Lambda=X, Top K=k

   SentenceTransformer Cross-encoder
   --child
   --reranking: [model name]

   Sequential retriever
   --child
   --Chunk fusion

   Parallel retriever
   --child
   --Chunk fusion: [estrategia]
   ```

   La tarjeta de operación (reranking / chunk fusion) debe ser el **nodo final**
   del retriever, **clicable** (abre el mismo diálogo de configuración que el
   nombre del nodo), y el child se sigue renderizando como hasta ahora (árbol si
   es compuesto, leaf si es simple).

2. **Arreglar las líneas del árbol** — con el espaciado inicial (3px por nivel)
   las líneas verticales quedaban tapadas por las tarjetas; además se intentaron
   flechas hacia abajo y conectores "L" que quedaron desalineados (triángulos en
   posiciones erráticas y líneas horizontales cruzando las verticales). El
   resultado final fue un árbol limpio con **espina vertical + conector
   horizontal** por hijo.

3. **Mostrar el modelo de embedding y el `model_name` del `DenseEmbeddingRetriever`**
   como subtítulo de la tarjeta (ej. `SentenceTransformer Embedding -
microsoft/harrier-oss-v1-0.6b`). Este punto falló en varias iteraciones hasta
   que se encontró la causa raíz (ver Decisiones).

## Archivos modificados

| Archivo                                                                               | Acción                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| ------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DashAI/front/src/pages/generative/RAGSession/advanced/CompositeRetrieverBuilder.jsx` | **Modificado** — núcleo de la sesión: `getOperationSummary()` (genera la tarjeta de operación por tipo de compuesto), `getDenseEmbeddingInfo()` (subtítulo del DenseEmbeddingRetriever), `getString()` y constantes de geometría del árbol, `denseDefaultsRef` (cache de `resolveDefaults("DenseEmbeddingRetriever")`) y `embNameMap` (mapa nombre → display name de los componentes `DenseEmbedding`); render de la tarjeta de operación como nodo final clicable; reescritura de la espina/conector del árbol; la tarjeta del nodo pasó de columna con `minWidth: 0`/`noWrap` a `minWidth: "fit-content"` + `maxWidth` + `overflowWrap` (que no se corte el nombre del modelo). |
| `DashAI/front/src/utils/i18n/locales/es/generative.json`                              | **Modificado** — claves nuevas en `rag.composite`: `reranking` ("Reordenamiento"), `chunkFusion` ("Fusión de chunks"), `mergeStrategyRoundRobin` ("Round robin"), `mergeStrategyInterleave` ("Intercalar").                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `DashAI/front/src/utils/i18n/locales/en/generative.json`                              | **Modificado** — mismas 4 claves: "Reranking", "Chunk fusion", "Round robin", "Interleave".                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `DashAI/front/src/utils/i18n/locales/pt/generative.json`                              | **Modificado** — "Reordenação", "Fusão de chunks", "Round robin", "Intercalar".                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `DashAI/front/src/utils/i18n/locales/de/generative.json`                              | **Modificado** — "Reranking", "Chunk-Fusion", "Round robin", "Verketten".                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `DashAI/front/src/utils/i18n/locales/zh/generative.json`                              | **Modificado** — "重新排序", "分块融合", "轮询", "交错合并".                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |

No se modificó ningún archivo extra: solo el componente del árbol y sus claves de
traducción. El backend, el benchmark y el resto del frontend quedaron intactos.

## Estado alcanzado

1. **Tarjeta de operación como nodo final** — para cada nodo compuesto del árbol
   se renderiza una tarjeta (borde punteado, icono `Merge` para fusión / `Sort`
   para re-ranker) después de los hijos:

   - `MMRRerankerRetriever` → `Reordenamiento: Lambda=X, Top K=k`
     (`mmr_lambda`, `top_k`).
   - `SentenceTransformerCrossEncoderRetriever` → `Reordenamiento: [model_name]`.
   - `ParallelRetriever` → `Fusión de chunks: Round robin / Intercalar`
     (`merge_strategy` traducido vía i18n).
   - `SequentialRetriever` → `Fusión de chunks` (solo etiqueta, sin valor).

   Es **clicable**: `onClick={() => onEdit(node.nodeId)}` abre el mismo
   `RetrieverNodeConfig` que el nombre del nodo. Los hijos se siguen renderizando
   igual que antes (recursivo: árbol si el hijo es compuesto, leaf si es simple).

2. **Árbol con geometría limpia** — después de varias iteraciones fallidas
   (flechas `▼`, conectores "L", `SPINE_OFFSET` proporcional), el layout final es:

   ```
   [Root card]
   │──────► [Child 1]
   │──────► [Child 2]
   │──────► ┄Operation┄
   ```

   - Espina vertical en `spineX = depth * INDENT` (borde izquierdo de la tarjeta
     del padre).
   - Conector horizontal de `spineX` a `spineX + INDENT` por cada hijo
     (`width: INDENT`, `top: "50%"`).
   - Operation card con `ml: spineX` (misma x que la espina).
   - `INDENT = 10`. **Sin flechas ni triángulos** (se eliminaron por completo al
     quedar en posiciones erráticas y cruzar las líneas).

3. **Subtítulo del DenseEmbeddingRetriever** — la tarjeta muestra:

   ```
   [SchemaIcon] Dense Embedding Retriever
                SentenceTransformer Embedding - microsoft/harrier-oss-v1-0.6b
   ```

   - `getDenseEmbeddingInfo()` extrae el componente del embedding y su
     `model_name` del **subform** `params.embedding_model`.
   - `denseDefaultsRef` cachea `resolveDefaults("DenseEmbeddingRetriever")` como
     fallback cuando el nodo todavía no tiene `embedding_model` (se muestra desde
     el primer render, sin necesidad de guardar dos veces).
   - `embNameMap` resuelve el display name de los componentes `DenseEmbedding`
     (fetched vía `getRetrieverComponents("DenseEmbedding")`).

4. **Ancho de tarjeta** — la columna de texto usa `minWidth: "fit-content"` con
   `maxWidth` acotado y `overflowWrap: "anywhere"`; el nombre del modelo ya no se
   corta con ellipsis (`noWrap` + `maxWidth: 320` eliminados).

## Verificación

- **Lint/format**: `yarn eslint` y `yarn prettier --write` limpios en
  `CompositeRetrieverBuilder.jsx`; `prettier --check` limpio en los 5 JSON de
  locales; los JSON validan con `ConvertFrom-Json`.
- **Sin tests automáticos**: no existen tests de frontend para el
  `CompositeRetrieverBuilder` (se ejecutó `eslint` sobre todo `RAGSession/` sin
  errores). La validación visual quedó pendiente del usuario (el árbol se ajustó
  iterativamente según su feedback).
- **Backend intacto**: no se tocó ningún `.py`; no se ejecutó la suite backend en
  esta sesión.

## Decisiones y hallazgos relevantes

- **Causa raíz del subtitle del embedding (bug escurridizo)** — el valor
  `embedding_model` **no** es `{component, params}` como se asumía al principio,
  sino un **subform** del schema de componente:

  ```js
  embedding_model: {
    properties: {
      component: "DenseEmbedding",                 // el parent
      params: {
        comp: {
          component: "SentenceTransformerEmbedding", // el modelo real
          params: { model_name: "microsoft/harrier-oss-v1-0.6b", ... },
        },
      },
    },
  }
  ```

  `getDenseEmbeddingInfo` leía `emb.component` (siempre `undefined`) en vez de
  `emb.properties.params.comp.component`. El fix parsea ambas formas (subform y
  la simple `{component, params}` como fallback). El fallback con
  `denseDefaultsRef` garantiza que el subtítulo aparezca en el **primer render**
  y no tras el primer guardado.

- **Lección de scope**: `TreeNodeView` es una función a nivel de módulo; las
  variables de `CompositeRetrieverBuilder` (`allComponents`, `denseDefaultsRef`)
  no le llegan por closure. Dos bugs de esta sesión (`allComponents is not
defined` y el subtítulo ausente) vinieron de ahí; la solución fue **pasar todo
  por props** (`findComponent`, `leafRegistry`, `denseDefaults`, `embNameMap`) y
  declararlo en `propTypes`.
- **`DenseEmbedding` no es paradigma de retrievers**: es un `BaseModel` padre de
  los embeddings, por lo que no sale de `getRetrievalParadigm()`; `embNameMap`
  se construye fetcheando sus hijos explícitamente
  (`getRetrieverComponents("DenseEmbedding")`).
- **`SPINE_OFFSET` fue un experimento del usuario** (lo puso en 0 y luego en
  `INDENT`): el valor final correcto es **0** — la espina corre en `depth*INDENT`,
  alineada con el borde izquierdo de la tarjeta del padre, y el conector horizontal
  de ancho `INDENT` llega a la tarjeta del hijo.
- **No se usó git** durante la sesión (por instrucción del equipo: hay muchas
  sesiones sin commitear, previas y posteriores a esta). El working tree ya
  contenía cambios de la Sesión XIV y anteriores.

## Pendientes detectados (fuera de alcance de esta sesión)

- **Verificación visual del árbol** con el usuario (espina, conectores y la
  tarjeta de operación) — los ajustes de geometría se hicieron a ciegas (sin
  ejecutar el dev server) y se iteraron según su feedback; conviene una revisión
  final con la app corriendo.
- **Tests de frontend**: `CompositeRetrieverBuilder` (y el resto de
  `RAGSession/`) no tiene tests de render; un test de humo (que la tarjeta de
  operación aparezca para cada compuesto y que el subtitle del dense se muestre)
  quedaría pendiente.
- **`embNameMap` vía `getRetrieverComponents("DenseEmbedding")`** depende de que
  el endpoint children de `DenseEmbedding` devuelva los componentes (los
  embeddings están registrados en `initial_components.py`); si se añade un
  embedding nuevo, el mapa se actualiza solo al re-fetchear.

---

# Sesión 16: arreglo del flujo RAG end-to-end (log SQL gigante y proceso que nunca completaba)

## Objetivo

Arreglar el flujo RAG de extremo a extremo con metodología **TDD**. El usuario
reportó que al usar una sesión RAG se generaba un **log SQL gigante** (cientos
de sentencias idénticas consecutivas) y que **el proceso nunca completaba**:
quedaba en `ERROR`/`DELIVERED` mientras el frontend polleaba sin fin
(`SELECT generative_process JOIN process_data ...` + `generative_session` +
`ROLLBACK` repetidos cada pocos segundos).

Se identificaron **dos causas raíz** independientes:

1. **N+1 en chunking** — `ChunkingService._update_chunk_ids` ejecutaba una
   `SELECT` a la tabla `chunk` **por cada chunk** recién persistido
   (`WHERE document_id=? AND chunk_index=? AND chunk_set_id=? LIMIT 1 OFFSET 0`),
   con `chunk_index` incrementando (81, 82, ... 108+). Con ~100 chunks eso son
   ~100 queries por `create()` → el log gigante.

2. **Validación tolerante → flujo roto** — el `RAGJob` fallaba en
   `build_pipeline` con `ValidationError` porque los schemas de componentes RAG
   exigían parámetros que el frontend NO envía (`BM25VectorizerModel(**{})`
   requiere 6 campos, `TFIDFVectorizerModel(**{})` 12, y el prompt default
   requería `template` que el frontend no manda). El proceso nunca llegaba a
   `FINISHED`.

## Contrato de negocio definido por el usuario (crítico para entender el fix)

Tras una primera iteración que intentó "rellenar vacíos" con defaults de
pydantic, el usuario lo rechazó explícitamente:

> _El backend nunca debe llenar vacíos ni parchear errores del frontend. Debe
> validar que se envíen configuraciones correctas al crear sesiones de RAG, no
> intentar arreglarlas después porque eso quita control al usuario._

Reglas finales:

1. **Validación estricta recursiva**: al crear (`POST /api/v1/generative-session/`)
   o actualizar (`PUT /api/v1/generative-session/{id}/parameters`) una sesión
   RAG, CADA `{component, params}` — incluidos sub-componentes anidados como el
   `BM25Vectorizer` dentro del `BM25Retriever` — debe validar contra su propio
   schema (`SCHEMA.model_validate(params)`). Si falla → **HTTP 400**.
2. **Única excepción — prompts default**: `DefaultRAGGenerationPrompt` y
   `DefaultQARAGenerationPrompt` (doble G en el QA: `...QARAGGenerationPrompt`)
   aceptan `{"language": "en"}` sin template; el backend **preprocesa**
   inyectando `template = TEMPLATES[language]` y luego valida como un componente
   cualquiera. El template inyectado se persiste. Un template
   ausente/vacío/whitespace/`null` también se normaliza al del idioma. Ningún
   otro componente rellena parámetros faltantes.

## Archivos modificados (producción)

| Archivo                                                                         | Acción                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DashAI/back/services/RAG/session_validation_service.py`                        | **Modificado** (existía de la Sesión I) — nuevo `_validate_component_params()`: recorre recursivamente todos los `{component, params}` vía `find_component_refs`, inyecta el template SOLO para prompts default (y lo escribe de vuelta en `normalized`), valida cada componente contra su schema, y normaliza tipos (`params.update(validated.model_dump(exclude_unset=True))`) procesando en orden inverso (hijos antes que padres). Se invoca en `prepare_RAG_params` (POST) y `validate_update_payload` (PUT). En el PUT, `prompt_id` se resuelve **antes** de la validación (paso 0, espejando el POST) para que el prompt resuelto se valide contra su schema. Se eliminó el helper `_resolve_prompt` (lógica inline). Guardia de template: `not (isinstance(template, str) and template.strip())`. |
| `DashAI/back/models/RAG/prompts/prompt.py`                                      | **Modificado** — `PromptSchema.template` pasa de `template: str = schema_field(...)` (patrón de anotación explícita) a `template: schema_field(...)` sin `: str =`. **Bug real de pydantic v2**: el patróng viejo hacía que pydantic usara el objeto `Annotated` como default del campo (`_AnnotatedAlias`), lo que corrompía `model_dump()` en prompts custom.                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `DashAI/back/models/RAG/prompts/generation/default_QA_RAG_generation_prompt.py` | **Modificado** — `__init__` estricto: `self.language = kwargs.pop("language")` y `self.template = kwargs.pop("template")` (el preprocesado del template vive en la validación de sesión, no en el modelo).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `DashAI/back/api/api_v1/endpoints/generative_session.py`                        | **Modificado** — el POST captura `except (ValueError, RAGWorkflowError)` (igual que el PUT) para que un prompt custom sin placeholders o un template inválido devuelvan **400** y no 500. Fixes ruff pre-existentes (`E713`/`W293`).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `DashAI/back/services/RAG/chunking_service.py`                                  | **Modificado** — fix N+1: `_persist_chunks` ahora devuelve `dict[tuple[int, int], int]` (mapeo `(document_id, chunk_index) → id`) construido desde los objetos ORM ya persistidos (leídos tras `flush()`, antes de `commit()`, para evitar refrescos por `expire_on_commit`); `_update_chunk_ids` consume ese mapa sin consultar la DB; `_update_chunk_ids` falla rápido (`KeyError`) si un chunk no está en el mapa.                                                                                                                                                                                                                                                                                                                                                                                     |

**Nota**: se **revirtió** un parche anterior (defaults de pydantic en
`BM25VectorizerSchema`/`TFIDFVectorizerSchema`/schemas de prompts, materialización
de template en `setup_service.py`, fallback en `__init__` de prompts y parámetro
`default` en `schema_field.py`) — todos quedaron a su estado HEAD, sin diff
residual. El fix real vive en la **validación de sesión**, no en rellenar vacíos.

## Archivos de test creados/modificados

| Archivo                                            | Acción                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `tests/back/RAG/test_RAG_strict_validation.py`     | **Creado** — 16 tests del contrato estricto (POST y PUT): vectorizer/Llama con `params: {}` → 400; prompt default `{"language": "en"}` → 201 con template inyectado; custom prompt sin template → 400; `temperature="not-a-number"` → 400; template vacío/whitespace/null normalizado; prompt default sin `language` → 400; PUT con `prompt_id` de un prompt schema-inválido → 400; normalización de tipos anidados (`max_df: 1` → `1.0`). |
| `tests/back/RAG/test_RAG_job_completes_flow.py`    | **Creado** — integración que ejecuta `RAGJob` completo con un `StubLLM` y verifica `RunStatus.FINISHED` con output "stub answer". Parametrizado `(BM25Retriever, DefaultRAGGenerationPrompt)` y `(TFIDFRetriever, DefaultQARAGenerationPrompt)`.                                                                                                                                                                                           |
| `tests/back/RAG/test_chunking_query_count.py`      | **Creado** — regresión del N+1: cuenta `SELECT`s a la tabla `chunk` durante `ChunkingService.create()` con `sqlalchemy.event` y exige ≤ 2.                                                                                                                                                                                                                                                                                                 |
| `tests/back/RAG/test_rag_session_flow.py`          | **Modificado** — vectorizer/LLM completos en payloads válidos; los 4 tests `..._accepted` (201, "deferred validation") pasan a `..._rejected` (400).                                                                                                                                                                                                                                                                                       |
| `tests/back/RAG/test_rag_session_validation.py`    | **Modificado** — payloads completos (BM25/TFIDF, quantization, separators).                                                                                                                                                                                                                                                                                                                                                                |
| `tests/back/RAG/test_rag_prompt_updates.py`        | **Modificado** — vectorizer TFIDF completo.                                                                                                                                                                                                                                                                                                                                                                                                |
| `tests/back/RAG/test_rag_prompts.py`               | **Modificado** — vectorizer BM25 completo + quantization.                                                                                                                                                                                                                                                                                                                                                                                  |
| `tests/back/RAG/test_rag_pipeline_api_configs.py`  | **Modificado** — separators, quantization, overflow_strategy, vectorizers completos.                                                                                                                                                                                                                                                                                                                                                       |
| `tests/back/RAG/test_rag_component_api_configs.py` | **Modificado** — payloads completos (BM25/TFIDF, quantization, overflow_strategy, device).                                                                                                                                                                                                                                                                                                                                                 |
| `tests/back/api/test_session_api.py`               | **Modificado** — `test_update_generative_session_params_merges_and_logs_history` con params completos (`chunk_size`/`chunk_overlap`, TFIDF completo, Qwen completo).                                                                                                                                                                                                                                                                       |

## Estado alcanzado

1. **El flujo RAG completa**: demostración end-to-end verificada — crear sesión
   (201) → enviar mensaje (201) → ejecutar `RAGJob` (sin errores) → proceso
   `FINISHED` con respuesta del modelo. Antes el proceso quedaba en
   `ERROR`/`DELIVERED` y el frontend polleaba sin fin.

2. **N+1 eliminado**: `ChunkingService.create()` pasa de ~93 `SELECT` a la tabla
   `chunk` a **0** (un solo `create()` corre en un número constante de queries).

3. **Validación estricta recursiva**: 400 ante cualquier sub-componente que no
   pase su schema, en POST y PUT, con la única excepción del template de los
   prompts default (inyectado y persistido).

4. **Sin defaults de pydantic tapando params**: el backend ya no "rellena vacíos";
   el frontend debe enviar configuraciones completas.

## Verificación

- **Tests**: `pytest tests/back/RAG/ tests/back/api/test_session_api.py`
  (excluyendo `test_cross_encoder_retriever.py`, `test_e5_embedding_memory.py`,
  `test_dense_retriever_id_space.py`) → **164 passed**.
- **Ruff**: limpio en todos los archivos de producción y tests tocados.
- **Demostración E2E**: script temporal que reproduce el flujo real del usuario
  (sesión vía API → proceso vía API → `RAGJob.run()` → `FINISHED` con respuesta)
  con salida `FLUJO RAG FUNCIONA: SI`.
- **Verificación manual de casos límite**: `template: null` → 201/200 (no 500);
  PUT con `prompt_id` schema-inválido → 400 (antes 200); `template: 123`
  (no-string) → normalizado al template del idioma.

## Decisiones y hallazgos relevantes

- **El parche de defaults fue descartado por el usuario**: la primera iteración
  dio `default=` de pydantic a los schemas de vectorizer/prompt (y materializó
  el template en `setup_service`), lo que hacía "funcionar" el flujo rellenando
  vacíos. El usuario lo rechazó: _"el backend nunca debe llenar vacíos ni
  parchear errores del frontend... eso quita control al usuario"_. Todo ese
  parche se revirtió; el fix vive en la validación de sesión.
- **La inyección del template en prompts default** se implementó como
  **preprocesado antes de validar** (no como default de schema): se inyecta
  `template = TEMPLATES[language]` en `_validate_component_params`, se valida
  contra el schema como cualquier componente y se persiste. Un template
  ausente/vacío/whitespace/`null`/no-string se normaliza al del idioma.
- **Bug de pydantic descubierto**: `PromptSchema.template: str = schema_field(...)`
  (patrón de anotación explícita) hacía que pydantic v2 usara el objeto
  `Annotated` como default del campo (`_AnnotatedAlias`), corrompiendo
  `model_dump()` en prompts custom. Se corrigió al patrón `template: schema_field(...)`.
- **Gap POST vs PUT corregido**: en el PUT, `prompt_id` se resolvía DESPUÉS de
  la validación, por lo que el prompt resuelto no se validaba contra su schema
  (demostrado: un `prompt_id` de un prompt con `language="de"` fuera del enum
  daba 400 en POST pero 200 en PUT). Se movió la resolución al paso 0.
- **Normalización de tipos anidados**: se procesan los refs en orden inverso
  (hijos antes que padres) para que el `model_dump` del padre no pise el
  write-back del hijo (`max_df: 1` → `1.0`).
- **Nota de proceso**: hubo una colisión con otro agente (tarea de visualización
  de documentos) cuyos cambios de tests se revirtieron; los 3 archivos de test
  nuevos se perdieron y fueron re-escritos por delegación. **No se usó git** por
  instrucción del equipo (hay muchas sesiones sin commitear, previas y
  posteriores a esta).
- **Lección de proceso**: la ejecución de la suite completa por cada subagente +
  Tech Lead hizo el ciclo muy lento. Para futuras sesiones: delegar en paralelo,
  restringir el nº de ejecuciones de los subagentes y hacer una única
  verificación consolidada.

## Pendientes detectados (fuera de alcance de esta sesión)

- **`RAGDatabaseError` → 400**: el catch `(ValueError, RAGWorkflowError)` en
  POST/PUT convierte un fallo real de DB de `resolve_prompt_id_to_component` en
  400 en vez de 500 (pre-existente, baja probabilidad, no bloqueante).
- **Claves desconocidas en la sesión**: `RAG_PARAM_KEYS_ALL` existe en
  `RAG_constants.py` pero el validation service no lo usa; claves top-level
  arbitrarias se aceptan y persisten (el job las descarta en silencio). Opción
  pendiente: fallar rápido en create/update.
- **Validación de schema en la ruta compuesta** (heredado de Sesiones III–IV):
  `_create_composite` no valida params contra `SCHEMA`.
- **`COMPOSITE_RETRIEVER_NAMES` por strings** (heredado): frágil ante nuevos
  retrievers compuestos.
- **`PromptService.create` no valida `parameters` contra el `SCHEMA` del
  componente** — habilitador raíz de que exista un prompt schema-inválido (ej.
  `language: "de"`); opción pendiente: validar al crear/actualizar prompts.

---

# Sesión 17: fix de la alineación del árbol de la configuración avanzada de retrievers (líneas verticales y conectores)

## Objetivo

Corregir la **alineación del árbol** de la configuración avanzada de retrievers
(el `CompositeRetrieverBuilder.jsx` del wizard de sesión RAG). Tras la Sesión XV
las tarjetas y los conectores existían, pero las **líneas verticales quedaban
desalineadas** respecto a las tarjetas: el spine del nivel 1 caía en una columna
y el conector de la card en otra (30 px de hueco), por lo que el árbol se veía
roto. El objetivo era llegar al layout descrito por el usuario:

```
Sentence transformer Cross encoder
[X]|[X] Child de  Cross encoder, ej: Parallel retriever
[X]|[2X]|[X] Child 1 de parallel retriever
[X]|[2X]|[X] Child 2 de parallel retriever
[X]|[2X]|[X] Child 3 de parallel retriever
[X]|[X] Chunk fusion del componente Parallel retriever
Reranking de Cross encoder
```

Donde `[X]` denota una unidad de espacio horizontal (base **parametrizable**),
`[2X]` dos unidades, y `|` la continuidad de una línea vertical. Regla clave del
diseño: **las líneas verticales deben quedar separadas por el mismo espacio que
el ancho de la indentación entre niveles**.

## Causa raíz (encontrada midiendo el DOM real)

El desalineamiento no era de lógica del árbol sino del **sistema de spacing de
MUI**, que aplica reglas distintas según la propiedad `sx`:

- El tema define `spacing: 4` (`DashAI/front/src/styles/theme.js:2`).
- En `sx`, las propiedades de **margen/padding/gap** con número se multiplican
  por `theme.spacing` → `ml: 10` → **40 px**.
- Las propiedades `left` / `width` numéricas **no** se multiplican → quedan en
  px crudos (`left: 5` → 5 px).
- Bonus: `width: 1` numérico en `sx` se computaba como **~100%** (la espina de
  1 px se renderizaba de 681 px de ancho, un quirk de MUI).

Como el código mezclaba `ml` (escalado ×4) con `left`/`width` (crudos), las
tarjetas quedaban en `x=0/40/80` pero spines y conectores en `x=5/15/35`: la
medición del DOM mostró el spine de nivel 1 en `x=5` y el conector de la card
`Parallel` en `x=35` → **hueco de 30 px**.

## Diagnóstico por medición del DOM (método)

El bug se aisló instrumentando el render con un **único** `console.log`
(`[CompositeRetrieverBuilder DOM layout]`) que:

- Marca los elementos clave con atributos `data-*`: `data-card` (tarjeta de
  nodo), `data-conn` (conector de la card), `data-spine` (espina vertical),
  `data-op` (tarjeta de operación y su conector).
- En un `useEffect([tree])` lee `getBoundingClientRect()` de cada uno
  (relativo al contenedor vía `treeBoxRef`) y `getComputedStyle()` (posición,
  `left`/`top`/`width`, `box-sizing`), volcando todo en un solo bloque.

Ese log reveló la inconsistencia de unidades y el ancho fantasma de 681 px de
las espinas.

## Archivos modificados

| Archivo                                                                               | Acción                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DashAI/front/src/pages/generative/RAGSession/advanced/CompositeRetrieverBuilder.jsx` | **Modificado** — única geometría del árbol re-expresada en **strings explícitos en px**: `INDENT` de `10` → `40` (px por nivel); card row `ml: \`${cardX}px\``; conector de card `left: \`${-INDENT/2}px\``con`width: \`${INDENT/2}px\``; espina de hijos `left: \`${cardX + INDENT/2}px\``con`width: "1px"`; conector de operación `left: \`${cardX - INDENT/2}px\`` con `width: \`${INDENT/2}px\``; card de operación `ml: \`${cardX}px\``. Se añadió la instrumentación de debug (`treeBoxRef`, `useEffect`de medición, atributos`data-*`) para verificar en vivo. |

No se modificó ningún archivo extra: el fix es exclusivamente de la geometría
del `CompositeRetrieverBuilder.jsx` (frontend). Backend, benchmark y resto del
frontend intactos.

## Estado alcanzado

1. **Geometría del árbol corregida** — toda la posición se expresa en px
   explícitos (strings `"...px"`), eliminando el factor `theme.spacing` de la
   ecuación. Con `INDENT = 40`:

   ```
   card d       → x = d*INDENT               (0, 40, 80)
   spine nivel d → x = d*INDENT ± INDENT/2   (20, 60 → separados 40 px = INDENT)
   conector      → de spine a card, ancho INDENT/2  (20→40, 60→80)
   ```

   Las líneas verticales consecutivas quedan **exactamente `INDENT` px aparte**
   (la regla del diseño) y cada conector toca su spine.

2. **Tarjeta de operación alineada** — el conector de la operación
   (chunk fusion / reranking) va del spine del nivel al borde de la card; la
   operación de la raíz (depth 0) no lleva ni spine ni conector (como en el
   diagrama del usuario).

3. **Espina vertical de 1 px real** — `width: "1px"` (string) en lugar de
   `width: 1` numérico, que MUI computaba como ~100% del contenedor.

4. **Instrumentación de debug en el archivo** — el log de medición del DOM y
   los atributos `data-*` permanecen en el código para la verificación visual
   final del usuario; se eliminarán al confirmar la alineación.

## Verificación

- **Lint/format**: `yarn eslint` y `npx prettier --write` limpios en
  `CompositeRetrieverBuilder.jsx`.
- **Medición del DOM** (log `[CompositeRetrieverBuilder DOM layout]`): las
  columnas de spines, conectores y cards cuadran tras el fix (antes: spine
  nivel 1 en `x=5` vs conector en `x=35`; después: spine en `20`, conector
  `20→40`, card en `40`).
- **Verificación visual pendiente del usuario**: la confirmación final de la
  alineación sobre la app corriendo queda pendiente de su revisión.

## Decisiones y hallazgos relevantes

- **El bug era del sistema de unidades de MUI, no de la lógica del árbol.** El
  `ml` (margen) escala con `theme.spacing` (×4) pero `left`/`width` numéricos
  no. Cualquier geometría que mezcle márgenes con posiciones absolutas en `sx`
  queda desalineada por el factor de spacing del tema.
- **Regla adoptada**: expresar toda la geometría del árbol como **strings en
  px** para que ningún valor dependa del multiplicador de spacing del tema
  (`INDENT` es la única base parametrizable, en `const INDENT = 40`).
- **`width: 1` numérico no es fiable en `sx`** de MUI v7: se computó como el
  ancho completo del contenedor (681 px). Usar siempre `"1px"` explícito.
- **Un solo log, no spam**: la primera versión de la instrumentación logueaba
  por nodo y el árbol serializado; el usuario reportó que era inmanejable
  ("pusiste tantos logs que no sé cuál mostrarte"). Se reemplazó por un único
  bloque que mide el DOM real (`getBoundingClientRect` + `getComputedStyle`).
- **La tarjeta de operación heredada de la Sesión XV** se mantuvo: es el nodo
  final del compuesto, clicable, con `ml` en `cardX` px y su conector propio;
  la espina que la atraviesa la dibuja el contenedor de hijos del nivel
  anterior (no la operación), de ahí que la operación no dibuje línea vertical.
- **No se usó git** durante la sesión (por instrucción del equipo: hay muchas
  sesiones sin commitear, previas y posteriores a esta). El working tree ya
  contenía los cambios de las Sesiones XIV–XVI y anteriores.

## Pendientes detectados (fuera de alcance de esta sesión)

- **Quitar la instrumentación de debug**: al confirmar la alineación visual,
  eliminar `treeBoxRef`, el `useEffect` de medición (y su `console.log`) y los
  atributos `data-*` de las tarjetas/conectores/spines.
- **Consolidar el estilo de espina/`borderLeft` con `"1px"`** en el resto del
  componente (el mismo quirk de `width: 1` puede afectar a cualquier otra
  geometría que use números).
- **Revisión visual final con la app corriendo** (heredado de la Sesión XV): la
  geometría del árbol se ajustó a ciegas y se verificó por medición del DOM;
  conviene confirmación visual del usuario.

---

# Sesión 18: benchmark de componentes con LLMs vía API (`--include-api-models`) + schemas remotos alineados con las APIs actuales

## Objetivo

Actualizar el benchmark por componente (`RAG_benchmark/app/components/llm.py`)
para testear también **LLMs vía API** (OpenAI y DeepSeek), pero **no por
defecto**: solo cuando se pasa el flag `--include-api-models`. Se usan **2
modelos hardcodeados** — los más baratos del mercado según precios web de hoy
(2026-08):

| Proveedor | Modelo              | Precio (por 1M tokens)     | Notas                                  |
| --------- | ------------------- | -------------------------- | -------------------------------------- |
| OpenAI    | `gpt-5-nano`        | $0.05 input / $0.40 output | Ya estaba en `gpt_available_models`    |
| DeepSeek  | `deepseek-v4-flash` | $0.14 input / $0.28 output | Faltaba en `deepseek_available_models` |

Además, por pedido explícito del usuario, se **revisaron los schemas de los
modelos remotos contra la documentación oficial** de las APIs de OpenAI y
DeepSeek, y se alinearon (la propuesta inicial era solo marcar como deprecados
los parámetros obsoletos de DeepSeek; el usuario rechazó esa opción: _"Hay que
dejar los schemas correctos, no parchar ni dejar deprecados"_).

## Archivos modificados

| Archivo                                                                      | Acción                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ---------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DashAI/back/models/remote_models/openai_text_to_text_generation_model.py`   | **Reescrito** — schema ampliado según la API actual: `max_completions_tokens` → `max_completion_tokens` (singular, nombre real de la API), nuevos `reasoning_effort` (none/minimal/low/medium/high/xhigh/max), `seed`, `response_format` (nested Pydantic `OpenAIResponseFormat`). Solo `API_key` y `model_name` siguen siendo requeridos; el resto opcional (`= None`). `generate()` construye el request condicionalmente y pasa solo los params no-None.                                                                                                                                                                                                                   |
| `DashAI/back/models/remote_models/deepseek_text_to_text_generation_model.py` | **Reescrito** — eliminados `frequency_penalty`/`presence_penalty` (DEPRECATED en la API de DeepSeek, "no tendrán efecto") y `max_completions_tokens` → `max_tokens` (nombre real de la API). Añadidos `thinking` (nested `DeepSeekThinking`: `type: enabled/disabled` + `reasoning_effort: low/high/max`), `response_format` (nested `DeepSeekResponseFormat`: text/json_object), `stop`. Modelos actualizados a `["deepseek-v4-flash", "deepseek-v4-pro"]` (se eliminaron `deepseek-chat` y `deepseek-reasoner`, ya no existen). `generate()` pasa `thinking`/`response_format`/`stop` vía `extra_body` (el cliente OpenAI de Python rechaza `thinking` como kwarg directo). |
| `RAG_benchmark/app/benchmark_data.py`                                        | **Modificado** — `LLM_MAP` con entradas para `OpenAITextToTextGenerationModel` y `DeepSeekTextToTextGenerationModel` (módulos remotos).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `RAG_benchmark/app/components/llm.py`                                        | **Modificado** — `API_LLM_CONFIGS` (2 configs API), `API_MODEL_CLASSES`, `API_MODEL_ENV_KEYS`; `_execute_llm()` inyecta la API key desde `os.environ` en una copia local de `params` (nunca se persiste); `run_all_llm_benchmarks(..., include_api_models=False)` añade los configs API solo con el flag (sin `device`).                                                                                                                                                                                                                                                                                                                                                      |
| `RAG_benchmark/app/config.py`                                                | **Modificado** — campo `include_api_models: bool = False` en `BenchmarkConfig` y en `from_env`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `RAG_benchmark/app/components/runner.py`                                     | **Modificado** — `extra_kwargs` de la categoría `llm` pasa `include_api_models`; añadido al `config_snapshot`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `RAG_benchmark/app/cli.py`                                                   | **Modificado** — flag `--include-api-models` en `components`, propagado vía `_make_config` y mostrado en el banner.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `RAG_benchmark/app/output.py`                                                | **Modificado** — `include_api_models` en `_config_snapshot`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `RAG_benchmark/tests/test_llm_api_models.py`                                 | **Creado** — 7 tests unitarios sin red (ver Verificación).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `RAG_benchmark/docs/02-component-benchmarks.md`                              | **Modificado** — sección LLM con los 2 modelos API, el flag opt-in, las API keys desde env/`.env` y que nunca se loguean.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `docs/RAG/backlog.md`                                                        | **Modificado** — esta entrada.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |

## Estado alcanzado

1. **Benchmark de LLMs vía API opt-in** — sin el flag no se ejecutan los modelos
   remotos (los configs API no llegan a `run_configs`); con `--include-api-models`
   se añaden `gpt-5-nano` (OpenAI) y `deepseek-v4-flash` (DeepSeek) a la categoría
   `llm`. La API key se lee del entorno en tiempo de ejecución
   (`OPENAI_API_KEY` / `DASHAI_DEEPSEEK_API_KEY`, cargadas desde
   `RAG_benchmark/.env` por `python-dotenv`) y se inyecta solo en la copia local
   de `params` dentro de `_execute_llm()`, por lo que **nunca aparece en
   `configs.json`/`io.json`/CSV** (mismo patrón que el embedding de OpenAI de la
   Sesión V).

2. **Ejecución real verificada** — `py -m RAG_benchmark.app.cli components -c llm
--include-api-models -i 10 --skip-passes` → **20/20 API runs successful, 0
   failed** (gpt-5-nano ~4–7 s, deepseek-v4-flash ~1.8–2.4 s); los 10 LLMs locales
   quedaron `skipped` (ya habían pasado en runs previos). Resultados en
   `RAG_benchmark/results/20260810_033539/`.

3. **Schemas remotos correctos según las APIs** — ambos con solo `API_key` +
   `model_name` requeridos y el resto opcional; campos obsoletos eliminados (no
   deprecados); `generate()` respeta los parámetros cuando se proveen.

## Verificación

- **Tests**: `py -m pytest RAG_benchmark/tests/` → **47 passed** (7 de
  `test_llm_api_models.py`: exclusión por defecto, inclusión con flag sin
  `device`, error claro sin API key, inyección de key verificada con módulo fake,
  **validación de `API_LLM_CONFIGS` contra los schemas reales**, `cfg` logueado
  sin `API_key`, `deepseek-v4-flash` en `deepseek_available_models`). Sin
  regresiones.
- **Ruff**: `ruff check` y `ruff format --check` limpios en todos los archivos
  tocados.
- **Smoke de schemas**: `model_validate` de ambos schemas con los params de
  `API_LLM_CONFIGS` + key dummy → OK; `thinking.model_dump(exclude_none=True)`
  → `{"type": "disabled"}`; `frequency_penalty`/`presence_penalty`/
  `max_completions_tokens` ausentes del schema DeepSeek.

## Decisiones y hallazgos relevantes

- **Elección de modelos (precios web, 2026-08)**: el usuario pidió "el modelo
  más barato"; se presentaron las opciones y eligió **ambos** (`gpt-5-nano` y
  `deepseek-v4-flash`), por lo que el benchmark API testea 2 modelos, no 1.
- **`gpt-5-nano` rechaza `temperature` distinto de 1**: error 400
  (`'temperature' does not support 0.1 ... Only the default (1) value is
supported`). Se eliminó `temperature` del config de OpenAI.
- **`gpt-5-nano` es un modelo de razonamiento**: con `max_completion_tokens`
  pequeño (~100–500) y `reasoning_effort: low`, el modelo gastaba **todos los
  tokens en razonamiento** (`finish_reason: length`, `reasoning_tokens: 500`,
  content vacío → "Response is empty"). Fix: `max_completion_tokens: 1000` +
  `reasoning_effort: "minimal"` (el valor `"none"` no está soportado por este
  modelo; los soportados son `minimal/low/medium/high`). Verificado de forma
  aislada con la respuesta completa (10 secciones sobre SQL vs NoSQL).
- **`thinking` de DeepSeek no es kwarg válido del cliente OpenAI**: el SDK de
  Python rechaza `Completions.create(**{..., "thinking": ...})` con
  `TypeError: unexpected keyword argument 'thinking'`. Se pasó vía
  `extra_body` (campo del SDK que se serializa en el body JSON), igual que
  `response_format` y `stop`.
- **`deepseek-v4-flash` usa thinking por defecto**: el config del benchmark
  fija `thinking: {"type": "disabled"}` para medir generación directa (sin
  tokens de razonamiento); el schema permite `enabled`/`disabled` + `reasoning_effort`.
- **`fill_objects`/`model_validate` con nested models**: los campos
  `response_format`/`thinking` se declararon como Pydantic `BaseModel` anidados;
  pydantic deserializa el dict de entrada y `model_dump(exclude_none=True)`
  serializa limpio para la API.
- **Decisiones descartadas**: no se tocó `config_object.py` (el
  `print(e.json())` en fallos de validación imprime la API key en consola) —
  decisión del usuario: _"la app siempre se corre en local, no hay problema con
  imprimir api keys"_. Tampoco se añadió un `dict`/JSON genérico como parámetro
  de schema (se prefirieron campos tipados y nested models).
- **`RAG_benchmark/` está en `.gitignore`**: los cambios del benchmark (configs,
  tests, docs) son locales. Los cambios trackeados de la sesión son los 2
  archivos de modelos remotos de DashAI y `docs/RAG/backlog.md`.
- **No se usó git** durante la sesión (por instrucción del equipo: hay muchas
  sesiones sin commitear, previas y posteriores a esta).

## Pendientes detectados (fuera de alcance de esta sesión)

- **`print(e.json())` en `DashAI/back/config_object.py`** expone el input
  completo (incluida la `API_key`) en stdout cuando falla la validación de un
  componente con key inyectada. Aceptado por el usuario (app local); si en el
  futuro se despliega el servidor, conviene redactar o loguear sin el input.
- **Los configs de `RAG_benchmark/app/pipelines/configs.py`** usan
  `OpenAIEmbedding` con `api_key: ""` (se inyecta en runtime); el LLM de
  generación sigue siendo local (`LlamaModel`). Si se quisiera usar un LLM vía
  API en pipelines, habría que añadir la variante de generación remota.
- **`reasoning_effort` de gpt-5-nano**: `"minimal"` reduce el razonamiento pero
  no lo elimina; el benchmark mide generación con razonamiento mínimo, no sin
  razonamiento (no hay valor `"none"` soportado para este modelo).
- **Coste de la salida de gpt-5-nano**: con `max_completion_tokens: 1000` el
  modelo puede emitir respuestas largas (~0.4 s/1000 tokens de output a
  $0.40/M); el benchmark de 10 iteraciones consumió ~0.0008 USD de output
  aprox. (insignificante, pero a escalas mayores conviene acotar).

---

# Sesión 19: validación de params del frontend RAG + propagación de errores de `resolveDefaults` + validación pre-save

## Objetivo

Revisar si el frontend de RAG envía los schemas con **todos los parámetros**
o si envía campos vacíos (ej. `TFIDFVectorizer:{}`), y corregir las
vulnerabilidades detectadas. El trabajo se dividió en 4 pedidos del usuario:

1. **Verificar el envío de schemas**: determinar si se envían params completos
   o vacíos, y en qué condiciones.
2. **Validación en el frontend antes de enviar**: detectar params de
   sub-componentes vacíos y mostrar error al usuario.
3. **Eliminar `.catch(() => ({}))` en `RetrieverSection.jsx`**: propagar errores
   de `resolveDefaults` en vez de silenciarlos (un fallo de la API producía
   params incompletos como `{ top_k: 10 }` sin `BM25Vectorizer`, `k1`, `b`...).
4. **Validación pre-save en `RAGSessionSetup`**: validar la configuración
   completa **sin guardar la sesión** (el botón Save valida y bloquea).

Se decidió **no** hacer el pedido 3 del plan original (tests de integración del
payload) por alcance.

## Análisis previo (hallazgos de la revisión)

- El frontend genera los defaults de cada componente vía
  `resolveDefaults(modelName)` (`utils/schema.js`), que produce el formato
  **wrapper `properties`** para sub-componentes:
  ```js
  { BM25Vectorizer: { properties: { component: "BM25VectorizerModel",
      params: { comp: { component: "BM25VectorizerModel", params: { ... } } } } } }
  ```
  Los presets del `RetrieverSection` construyen además el formato **canónico**
  `{ component, params }` (ej. `embedding_model`). Ambos formatos son correctos:
  el backend los normaliza con `normalize_payload()` en
  `back/core/schema_fields/utils.py`.
- En el **flujo normal** (APIs respondiendo), los params se envían completos. El
  placeholder `{"component": ..., "params": {}}` del schema (que produce
  `TFIDFVectorizer:{}`) **no se usa** en el flujo RAG actual.
- El riesgo real era el **fallo silencioso**: `resolveDefaults` capturaba todas
  las excepciones internamente y devolvía `{}`, y `RetrieverSection` además
  aplicaba `.catch(() => ({}))`. Con la API caída se enviaba un
  `BM25Retriever` con solo `{ top_k }` — exactamente el escenario de params
  incompletos.

## Archivos modificados

| Archivo                                                                      | Acción                                                                                                                                                                                                                                                                                                                                                                                                                     |
| ---------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DashAI/front/src/utils/ragValidation.js`                                    | **Creado** — `validateModelConfig(model, t)` y helpers `_checkSubComponents()` / `_isEmptyParams()`. Validación recursiva de un config `{ component, params }`: component no vacío, params no vacío, y recursión en sub-componentes (formato canónico `{component, params}`, formato wrapper `properties`, y arrays `children` de composite retrievers). Devuelve `{ valid, errors }` con mensajes **traducidos** vía `t`. |
| `DashAI/front/src/utils/schema.js`                                           | **Modificado** — `resolveDefaults(modelName, { throwOnError = false })`: por defecto mantiene el comportamiento (devuelve `{}` en fallo); con `throwOnError: true` re-lanza la excepción tras el `console.warn`. Retrocompatible.                                                                                                                                                                                          |
| `DashAI/front/src/pages/generative/RAGSession/sections/RetrieverSection.jsx` | **Modificado** — import y hook de `useSnackbar`; estado `loadError`; eliminados los 3 `.catch(() => ({}))` de `resolveDefaults` → `Promise.all` con `{ throwOnError: true }` dentro de `try/catch` que setea `loadError` + snackbar de error; snackbar añadida al catch externo (`getRetrieverComponents`); render de error si `loadError` (reemplaza los presets, evita configs incompletas).                             |
| `DashAI/front/src/pages/generative/RAGSession/RAGSessionSetup.jsx`           | **Modificado** — import de `validateModelConfig`; 4 bloques nuevos en `validateConfiguration()` (chunking, retriever, generator, prompt) que llaman a `validateModelConfig(config, t)` y muestran snackbars warning + `return false` (sin guardar) si algún params está incompleto.                                                                                                                                        |
| `DashAI/front/src/utils/i18n/locales/en/generative.json`                     | **Modificado** — claves nuevas en `rag.validation`: `modelComponentMissing`, `modelParamsIncomplete`, `modelParamsLoadFailed`.                                                                                                                                                                                                                                                                                             |
| `DashAI/front/src/utils/i18n/locales/es/generative.json`                     | **Modificado** — mismas 3 claves traducidas.                                                                                                                                                                                                                                                                                                                                                                               |
| `DashAI/front/src/utils/i18n/locales/pt/generative.json`                     | **Modificado** — mismas 3 claves traducidas.                                                                                                                                                                                                                                                                                                                                                                               |
| `DashAI/front/src/api/api.ts`                                                | **Modificado** — fix de un error de tipos **pre-existente** que impedía `yarn start` (`TS2339: Property 'language' does not exist on type 'i18n'`): el import cambió de `"i18next"` a `"../utils/i18n"` y el acceso se tipa con `(i18n as any).language`. No relacionado con la validación; se tocó solo para poder correr el frontend.                                                                                    |

No se modificó ningún archivo del backend ni del benchmark; todo el trabajo es
del frontend de DashAI.

## Estado alcanzado

1. **`validateModelConfig()`** — utilidad reutilizable que valida un config de
   modelo RAG:
   - Component no vacío (`modelComponentMissing`).
   - `params` es objeto no vacío (`modelParamsIncomplete`).
   - **Recursión profunda**: sub-componentes en formato canónico
     `{component, params}`, en formato wrapper `properties.params.comp`, y en
     arrays (`children` de `ParallelRetriever`/`SequentialRetriever`). Un
     sub-componente con `params: {}` o `params: null` se reporta.
   - Devuelve mensajes traducidos (recibe `t` como parámetro), sin strings
     hardcodeados en el módulo.

2. **Propagación real de errores de `resolveDefaults`** — con
   `{ throwOnError: true }`, un fallo de la API ya no produce silenciosamente
   `{}`. `RetrieverSection` muestra un error al usuario (snackbar + estado
   `loadError` que reemplaza el UI) en vez de construir presets con params
   incompletos.

3. **Validación pre-save** — `validateConfiguration()` en `RAGSessionSetup`
   valida los 4 modelos (chunking, retriever, generator, prompt) con
   `validateModelConfig` después de las validaciones existentes (nombre,
   documentos, componentes seleccionados). Si algo está incompleto, se muestran
   snackbars de warning y **la sesión no se guarda**.

4. **Fix incidental de tipos en `api.ts`** — necesario para que `yarn start`
   compile; corrige un error TS2339 pre-existente (TypeScript 7.0.2 +
   i18next v25).

## Verificación

- **Code review** (3 Critical encontrados y corregidos):
  - **C1 — propagación muerta**: el `try/catch` de `RetrieverSection` nunca se
    ejecutaba porque `resolveDefaults` capturaba el error internamente y devolvía
    `{}`. Se añadió la opción `throwOnError` a `resolveDefaults`.
  - **C2 — validación poco profunda**: `validateModelConfig` no inspeccionaba
    arrays (`children` de composites) ni anidados, y crasheaba con
    `params: null`. Se reescribió con recursión + guardas de null.
  - **C3 — i18n muerta**: las claves añadidas no se usaban (los mensajes eran
    strings hardcodeados en inglés). `validateModelConfig` ahora recibe `t` y
    devuelve mensajes traducidos; las claves se añadieron en en/es/pt.
- **Syntax check**: `node -e "require('./src/utils/ragValidation.js')"` → PASS.
  `schema.js` falla solo por import de TS (esperado en un require plano de Node).
- **`yarn start`**: compila hasta el error TS2339, corregido en `api.ts`. El
  frontend aún tiene un problema **pre-existente** del entorno
  (`react-scripts` 5.0.1 + Yarn 3.5 + Node 22 en Windows: `Cannot find module
'typescript'` / `jsonfile` intermitente tras `yarn install`). No es de esta
  sesión ni de los cambios; CRA es el setup histórico del proyecto (no se
  migró a Vite por decisión del usuario).
- **Ruff/backend**: no aplica (no se tocó backend).

## Decisiones y hallazgos relevantes

- **El frontend envía params completos en el flujo normal**: los defaults de
  `resolveDefaults` incluyen todos los placeholders del schema (verificado en
  `generateInitialValues` de `utils/schema.js`). El placeholder vacío del
  schema (`TFIDFVectorizer:{}`) solo se usaría como fallback si un path
  accediera directamente al `placeholder`, que no ocurre en el flujo RAG actual.
- **El riesgo real era el fallo silencioso**, no el envío: `resolveDefaults`
  devolvía `{}` ante cualquier error y `RetrieverSection` lo combinaba con
  `.catch(() => ({}))`, produciendo configs incompletas sin aviso. El fix ataca
  ambas capas (propagación + validación defensiva en el save).
- **Retrocompatibilidad de `resolveDefaults`**: la nueva opción `throwOnError`
  es opt-in; todos los llamadores existentes siguen con el comportamiento
  anterior (devolver `{}`). Solo `RetrieverSection` la activa.
- **`isConfigurationComplete` (el botón Save habilitado) no incluye la
  validación profunda** — la validación profunda ocurre al hacer clic en Save.
  Aceptado como alcance (el botón ya se deshabilita si falta un componente; la
  validación de params se dispara en el click para dar feedback con snackbars).
- **`api.ts`** se modificó por necesidad de correr el frontend; es un fix
  separado del objetivo de validación y así se documenta.
- **No se usó git** durante la sesión (por instrucción del equipo: hay muchas
  sesiones sin commitear, previas y posteriores a esta). El working tree ya
  contenía cambios de las Sesiones XIV–XVIII y anteriores.

## Pendientes detectados (fuera de alcance de esta sesión)

- **Problema de entorno del frontend**: `yarn start`/`yarn build` fallan de
  forma intermitente con `react-scripts` 5.0.1 + Yarn 3.5 + Node 22 en Windows
  (`Cannot find module 'typescript'`, `jsonfile`). Pre-existente; la migración
  a Vite (descartada por el usuario) o un `node_modules` reinstalado
  correctamente lo resolvería.
- **`isConfigurationComplete` sin validación profunda**: opcionalmente, espejar
  `validateModelConfig` en el `useMemo` para que el botón refleje la
  completitud real (no solo la selección de componentes).
- **Otros llamadores de `resolveDefaults` sin manejo de error visible**
  (`ChunkingSection.applyPreset`, `GeneratorSection.handleGeneratorChange`,
  `RetrieverConfigurationStep`, `ChunkingConfigurationStep`,
  `GeneratorConfigurationStep`): con `throwOnError` opt-in siguen con el
  comportamiento silencioso. Opcional: activarlo también allí y mostrar error.
- **`loadError` en `RetrieverSection` oculta todo el componente**: si la API de
  defaults falla, el usuario no puede ni abrir la configuración avanzada (que
  no depende de esos defaults). Aceptado como seguro (sin defaults los presets
  serían incompletos), pero podría permitirse el modal avanzado como fallback.

---

# Sesión 20: investigación del flujo RAG que no completa — cuello de botella en la fase de embedding (harrier-oss-v1-0.6b en CPU)

## Objetivo

Investigar por qué un pipeline RAG **no genera respuesta**: el usuario reportó
que al correr un pipeline se repetía en loop el mismo patrón de queries SQL
(`SELECT generative_process JOIN process_data ... is_input=0/1` +
`SELECT generative_session`), con caché de statement (`[cached since Xs ago]`)
cada pocos segundos, sin que el proceso terminara nunca.

**Primera hipótesis (descartada):** el ruido de SQL se interpretó inicialmente
como un problema de performance de las relaciones ORM `lazy="selectin"` de
`GenerativeProcess.input`/`output` (models.py), que disparan 2 SELECTs a
`process_data` por cada carga de un proceso. El usuario corrigió el foco: **las
queries repetidas son un síntoma, no la causa** — el frontend
(`GenerativeChat.jsx`) pollea cada 1.5 s `GET /v1/generative-process/{id}` por
cada proceso no finalizado, y como el proceso nunca cambia de estado, el poll
no se detiene.

**Causa real:** el RAG job se quedaba atascado en la **fase de embedding**.
`DenseRetriever.compute_missing_embeddings()` → `batch_encode(chunk_texts)`
tardaba "mucho rato" en completar (confirmado por debugging del usuario: la
ejecución pasaba esa línea solo después de un tiempo prolongado).

## Contexto del entorno investigado

Sesión RAG real del usuario (datos observados en `~/.DashAI/db.sqlite`):

- **8 documentos PDF** con **2283 chunks** totales (`chunk_size=500`,
  `CharacterChunkModel`):

  | doc_id | Archivo                      | Chunks |
  | ------ | ---------------------------- | ------ |
  | 1      | Atlas-Few-Shot-Learning.pdf  | 272    |
  | 2      | Dense-Passage-Retrieval.pdf  | 125    |
  | 3      | Faster-And-Lighter-LLMs.pdf  | 114    |
  | 4      | Gemini-Multimodal-Models.pdf | 495    |
  | 5      | Llama-2.pdf                  | 586    |
  | 6      | LoRA.pdf                     | 185    |
  | 7      | RAG-For-AIGC.pdf             | 322    |
  | 8      | RAG-Meeting-LLMs.pdf         | 184    |

- **Retriever configurado:** `ParallelRetriever` (compuesto). La BD solo tenía
  persistido el hijo `BM25Retriever` (`rag_sparse_retriever`), lo que sugiere
  que un hijo denso también participaba (las matrices `.npy` así lo indican).
- **Modelo de embedding:** `microsoft/harrier-oss-v1-0.6b` (0.6B, pooling
  `last_token`, `max_seq_length` 32768), ejecutándose en **CPU**.
- **Caché de embeddings en disco:** solo 3 de 8 documentos tenían
  `embeddings.npy` (`doc_id-1`, `doc_id-2`, `doc_id-3`) — los 5 restantes
  (incluidos los más grandes: Gemini 495 y Llama-2 586) quedaban por calcular.
- **BD sin registros de embedding:** `rag_embedding_matrix` y
  `rag_embedding_model` tenían **0 filas**, pese a que los `.npy` existían en
  disco. Indica que una ejecución anterior calculó matrices para docs 1–3 y
  guardó los `.npy`, pero el proceso **fue interrumpido/matado antes de
  persistir** los registros en la BD (`rag_dense_retriever` también en 0).
- **4 procesos generativos** todos en `DELIVERED` (de ejecuciones anteriores
  que sí completaron la fase de pipeline/sparse).

## Estado alcanzado

Sesión puramente **de diagnóstico** (sin cambios de código). Hallazgos:

1. **El loop de queries se explica por el polling del frontend**, no por un
   bug de SQLAlchemy. El proceso se queda en un estado intermedio (nunca llega
   a `FINISHED`/`ERROR`), el frontend no tiene nada que mostrar y pollea sin
   fin. El `lazy="selectin"` en `GenerativeProcess.input`/`output` amplifica el
   ruido (2 SELECTs extra por poll), pero no es la causa del atasco.

2. **Cuello de botella real: `batch_encode` en CPU.** En
   `_overflow_handler.py`, `_batch_encode_impl()` tokeniza **todos los chunks
   de un documento en un solo batch** (`padding=True` al más largo) y hace un
   único forward-pass del modelo de 0.6B por documento. Con docs de 495 y 586
   chunks, un forward-pass en CPU es inherentemente lento. Falta progreso
   visible: el usuario no sabe si está "colgado" o "avanzando" (los docs 1–3
   ya cacheados se saltan, pero no se loguea).

3. **El caché de embeddings funciona por archivo, no por registro BD.** Al
   re-ejecutar, `compute_missing_embeddings()` detecta los `.npy` existentes en
   disco y los salta; los 5 documentos restantes se calculan desde cero. Si la
   ejecución actual se completa, los `.npy` de docs 4–8 quedarán cacheados y
   las ejecuciones siguientes serán instantáneas en la fase de embedding.

4. **Sub-batching NO acelera el cómputo total** (pregunta del usuario): dividir
   los 586 chunks en lotes de ~32 haría ~19 forward-passes en vez de 1, con el
   mismo número total de operaciones (solo añade overhead de loop y reduce el
   padding máximo por lote). El costo dominante es el modelo de 0.6B en CPU, no
   el tamaño del batch.

## Verificación

- **Inspección de datos**: consulta directa a `~/.DashAI/db.sqlite` (tablas
  `document`, `chunk`, `rag_*`, `generative_process`, `generative_session`) y
  listado de `~/.DashAI/RAG/embeddings/`.
- **Debugging del usuario**: confirmó que la ejecución pasaba la línea
  `embeddings = self.embedding_model.batch_encode(chunk_texts)` solo tras un
  tiempo prolongado (embedding del doc en curso).
- **Sin tests**: sesión de diagnóstico, sin cambios de código; no aplica suite.

## Decisiones y hallazgos relevantes

- **Las queries repetidas en DEBUG no son el error**: SQLAlchemy loguea cada
  query dos veces (statement + parámetros) y el polling del frontend las
  re-ejecuta en cada ciclo; el arreglo real es que el proceso **complete** (o
  falle con estado `ERROR` visible), no silenciar el log.
- **Los tests no detectan el caso real** porque usan `StubLLM`/`StubEmbedding`
  que no descargan ni computan nada, corren `RAGJob().run()` de forma síncrona
  (sin el ciclo HTTP de polling) y no ejercitan modelos de embedding reales con
  muchos documentos/chunks. Un test de regresión debería (a) correr el flujo
  HTTP completo creando un proceso y polleando hasta `FINISHED`/`ERROR`, y/o
  (b) medir el progreso/timing de `compute_missing_embeddings` con un embedding
  ligero y muchos chunks.
- **Opciones de mitigación para el usuario (no implementadas):**
  - Dejar terminar la ejecución en curso para cachear los `.npy` de docs 4–8.
  - Usar un modelo de embedding más pequeño (`all-MiniLM-L6-v2`, 22M) o GPU.
  - Añadir logging de progreso en `compute_missing_embeddings` (cuántos chunks
    por documento, cuántos documentos quedan) para no parecer colgado.
- **Pendiente de diseño**: el sub-batching por sí solo no es la solución; si se
  implementara, sería por **memoria** (evitar OOM en docs muy grandes) y por
  **progreso incremental**, no por velocidad.

## Pendientes detectados (fuera de alcance de esta sesión)

- **Logging de progreso en la fase de embedding**: loguear documento/chunks que
  se están calculando y saltos de caché (`compute_missing_embeddings`).
- **Persistencia a mitad de cálculo**: la interrupción deja `.npy` huérfanos en
  disco sin registros en BD (`rag_embedding_matrix`/`rag_dense_retriever`);
  considerar persistir por documento a medida que se calcula (no solo al final).
- **Test de regresión del flujo completo** con polling HTTP y modelo real (o
  al menos con un embedding ligero y muchos chunks para medir timing/progreso).
- **Evaluar sub-batching** (por memoria/progreso, no velocidad) en
  `_overflow_handler._batch_encode_impl()`.
- **Evaluar recomendación de modelo de embedding** en el UI según el número de
  documentos/chunks y el dispositivo (CPU vs GPU).

---

# Sesión 21: fix de la configuración de retrievers — el modelo de embedding no se guardaba y fallaba al armar compuestos

## Objetivo

Corregir tres bugs reportados por el usuario al configurar retrievers en el
wizard de sesión RAG:

1. **Bug 1 — el embedding del preset híbrido no se guarda**: al cambiar el
   modelo de embedding del preset híbrido (avanzado), la elección no se
   persistía; se sobrescribía con el default.
2. **Bug 2 — no deja guardar un retriever paralelo BM25 + dense**:
   `POST /api/v1/generative-session/` devolvía 400 con
   `Component '' at 'retriever_model.params.children[0]' is not registered.`
3. **Bug 3 — el retriever denso puro (no compuesto) falla al ejecutar el job**:
   `Unsupported retriever type: SentenceTransformerEmbedding` — el nombre del
   componente del retriever llegaba como el nombre del _embedding_.

Metodología **TDD**: primero se escribieron tests de regresión que reproducen
los síntomas (el test del auto-save parcial confirma el comportamiento del
backend), luego se implementaron los fixes y se revisó el código
(`code-reviewer`).

## Causas raíz

### Bug 3 — el nombre del embedding se filtraba como componente del retriever

En `RetrieverConfigurationStep.jsx`, el efecto `load()` que restaura un
`retrieverModel` persistido con `component === "DenseEmbeddingRetriever"`
buscaba el **embedding** (hijo de `params.embedding_model`) en la lista de
opciones y lo asignaba a `selectedRetriever`. Al auto-guardar,
`handleParametersSave` emitía `selectedRetriever.name` como componente
top-level → la sesión guardaba `{component: "SentenceTransformerEmbedding",
params: {...}}` en vez de `{component: "DenseEmbeddingRetriever", params:
{embedding_model: {...}, similarity_metric, top_k}}`. En runtime,
`RetrieverSetupService._build_persistence_for` no reconocía la clase como
retriever → `RAGRetrieverError: Unsupported retriever type`.

### Bug 2A — hijos con `component: ""` se serializaban al backend

`CompositeRetrieverBuilder.handleAddChild` creaba un nodo placeholder con
`component: ""`; si el diálogo se cancelaba, el hijo vacío quedaba en el árbol.
`emit()` serializaba **todos** los hijos sin filtrar, por lo que un hijo con
`component: ""` llegaba al backend y `validate_component_refs` lo rechazaba
(`Component '' at ... is not registered`).

### Bug 2B — embeddings sueltos como hijos de compuestos

`RetrieverNodeConfig` construía `allOptions` volcando todos los `leafRegistry`
(que incluye los embeddings concretos bajo `DenseEmbedding`/`DenseEmbeddingRetriever`).
Un usuario podía seleccionar `SentenceTransformerEmbedding` directamente como
hijo de un compuesto, sin envolverlo en `DenseEmbeddingRetriever` → runtime
fallaba con `Unsupported retriever type`.

### Bug 1 + el "Dense plano" — el auto-save no propagaba los cambios del subform

Dos bugs de raíz en la capa de formularios (`FormSchema`):

- **`FormSchemaFieldWithParent.handleSubModelSave`** actualizaba el store del
  contexto pero **no llamaba `field.onChange()`**, por lo que el auto-save del
  formulario padre nunca se disparaba → `savedParamsRef.current` quedaba `null`
  → al cerrar el modal, `saveCurrentFormValues` no hacía nada y la sesión se
  guardaba con el config anterior (el default).
- **`FormSchemaRenderFields.handleChange`** pasaba a `handleUpdateSchema` solo
  `{ [fieldPath]: value }`, que se mergeaba con el `formValues` del store. Si el
  `useEffect` que inicializa el store aún no había corrido (race condition), el
  store estaba vacío → se perdían `similarity_metric` y `top_k`, y el backend
  rechazaba el payload incompleto (o el guardado quedaba roto).

### Bug 1 adicional — `selectPreset` sobrescribía la config custom

`RetrieverSection.selectPreset` no comprobaba `isAdvanced`; al hacer clic en una
tarjeta de preset con la config avanzada activa, `setRetrieverModel(preset)`
reseteaba el modelo custom a los defaults.

## Archivos modificados

| Archivo                                                                                | Acción                                                                                                                                                                                                                                                                   |
| -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `DashAI/front/src/components/shared/FormSchemaFieldWithParent.jsx`                     | **Modificado** — `handleSubModelSave` construye el valor actualizado y llama `field.onChange(updated)` para propagar el cambio al auto-save del formulario padre.                                                                                                        |
| `DashAI/front/src/components/shared/FormSchemaRenderFields.jsx`                        | **Modificado** — `handleChange` pasa `{ ...formik.values, [fieldPath]: value }` (valores completos de Formik) en vez de solo el campo cambiado, eliminando la race condition con el store.                                                                               |
| `DashAI/front/src/pages/generative/RAGSession/advanced/RetrieverConfigurationStep.jsx` | **Modificado** — al restaurar `DenseEmbeddingRetriever`, `selectedRetriever` se resuelve siempre al paradigma `DenseEmbeddingRetriever` (de `retrievers`/`allParadigms`), nunca al embedding.                                                                            |
| `DashAI/front/src/pages/generative/RAGSession/advanced/CompositeRetrieverBuilder.jsx`  | **Modificado** — `emit()` filtra hijos con `component` vacío (a nivel recursivo y raíz); `handleAddChild` limpia hijos vacíos previos, llama `emit(updated)` y guarda `editingParentId`; `onClose` del diálogo elimina el placeholder sin configurar; guards `n.children |     | []`; se eliminó el parámetro `children`sin usar de`TreeNodeView`. |
| `DashAI/front/src/pages/generative/RAGSession/advanced/RetrieverNodeConfig.jsx`        | **Modificado** — `allOptions` excluye los `leafRegistry` keyed `"DenseEmbedding"`/`"DenseEmbeddingRetriever"` (los embeddings concretos ya no se ofrecen como hijos directos; se selecciona `DenseEmbeddingRetriever` y el sub-form muestra el embedding).               |
| `DashAI/front/src/pages/generative/RAGSession/sections/RetrieverSection.jsx`           | **Modificado** — `selectPreset` con guard `isAdvanced`: si la config es avanzada, el clic en un preset solo abre el modal avanzado, sin sobrescribir el modelo.                                                                                                          |
| `tests/back/RAG/test_rag_session_validation.py`                                        | **Modificado** — nueva clase `TestRetrieverConfigRegression` con 4 tests de regresión (ver Verificación).                                                                                                                                                                |

No se modificó ningún archivo extra (ni backend de producción, ni benchmark, ni
parsers); los fixes son de capa de formulario/UI y tests.

## Estado alcanzado

1. **El retriever denso se guarda y ejecuta correctamente**: el componente
   top-level queda como `DenseEmbeddingRetriever` con `params.embedding_model`
   anidado; ya no se filtra `SentenceTransformerEmbedding` como componente.

2. **Los compuestos (Parallel/Sequential/MMR/CrossEncoder) se guardan sin
   hijos vacíos**: `emit()` nunca serializa un hijo con `component: ""`, y los
   placeholders cancelados se eliminan del árbol (ya no quedan zombies).

3. **No se ofrecen embeddings sueltos como hijos de compuestos**: el dropdown
   de `RetrieverNodeConfig` solo muestra `DenseEmbeddingRetriever` (que a su vez
   renderiza el sub-form del embedding) y el resto de retrievers concretos.

4. **El auto-save del subform funciona**: guardar parámetros del embedding vía
   el sub-form ("Configure") dispara `field.onChange`, el auto-save del form
   padre y la actualización de `savedParamsRef.current` → la config custom
   persiste al guardar la sesión.

5. **No se pierden params por race condition**: el auto-save envía SIEMPRE los
   valores completos de Formik, independientemente del estado del store del
   contexto.

6. **El clic en un preset no pisa la config avanzada**: `selectPreset` solo
   aplica el preset cuando no hay config avanzada activa.

## Verificación

- **Tests**: `pytest tests/back/RAG/test_rag_session_validation.py` → **65
  passed** (61 pre-existentes + 4 nuevos). Cero regresiones.
  - `test_dense_embedding_retriever_preserves_component_name` — una sesión con
    `DenseEmbeddingRetriever` guarda `component: "DenseEmbeddingRetriever"` (no
    el embedding).
  - `test_composite_retriever_rejects_empty_child_component` — un hijo con
    `component: ""` se rechaza con 400 (guarda contra Bug 2A).
  - `test_bare_embedding_as_child_accepts_but_fails_at_runtime` — documenta que
    un embedding suelto como hijo pasa la validación de sesión (está registrado)
    pero fallaría en runtime; el fix frontend evita el escenario.
  - `test_auto_save_partial_data_preserves_component` — un payload parcial
    (solo `embedding_model`, sin `similarity_metric`/`top_k`) se rechaza con 400
    y el error menciona `top_k`: el backend no acepta el auto-save roto.
- **Ruff**: `ruff check` limpio en el test modificado.
- **Build frontend**: `next build` falla por errores de TypeScript
  **pre-existentes** en `node_modules/react-i18next` (TS1139/TS1005), no
  relacionados con los cambios de esta sesión.

## Decisiones y hallazgos relevantes

- **TDD primero**: el test `test_auto_save_partial_data_preserves_component` se
  escribió primero y **falló** con 400 (el backend rechaza el payload parcial) —
  confirmando que el backend valida bien y que el bug era del frontend (el
  auto-save enviaba params incompletos). Ese comportamiento (400) se mantuvo en
  el test final como guarda.
- **Los dos bugs de la capa de formularios son genéricos de `FormSchema`**, no
  exclusivos de retrievers: cualquier sub-modelo configurado vía el diálogo
  "Configure" de un `FormSchemaFieldWithParent` y cualquier auto-save en un
  `FormSchema` se beneficiaban/afectaban. Por eso los fixes viven en
  `components/shared/`, no en `RAGSession/`.
- **`getModelFromSubform` ya soporta ambos formatos** (canonical y `properties`
  wrapper); el problema no era de parseo sino de propagación (falta de
  `field.onChange`) y de merge (race condition del store).
- **Code review** (2 iteraciones): la 1ª detectó que `handleAddChild` no llamaba
  `emit(updated)` (inconsistente con `handleRemoveChild`) y que los placeholders
  cancelados quedaban en el árbol (zombies) → se corrigieron (emit + limpieza en
  `onClose` + `editingParentId`). La 2ª iteración quedó aprobada sin Critical.
- **Nota de proceso**: el `code-reviewer` devolvió salidas vacías en 2 intentos
  por agotamiento de tokens del subagente; se reintentó y finalmente respondió.
- **`RAG_benchmark/` está en `.gitignore`** y el working tree tiene muchas
  sesiones sin commitear (previas y posteriores). **No se usó git** (por
  instrucción del equipo).

## Pendientes detectados (fuera de alcance de esta sesión)

- **`selectPreset` en modo avanzado no permite volver al preset por clic** (por
  diseño tras el fix): con config avanzada activa, el clic en un preset abre el
  modal avanzado en lugar de resetear al preset. Si se desea una forma explícita
  de "volver al preset", habría que añadir un botón/acción dedicado.
- **`COMPOSITE_NAMES`/`COMPOSITE_TYPES` por strings** (heredado de Sesiones
  XIV–XV): frágil ante un retriever compuesto nuevo; el flag `"composite"` ya
  llega por la API (Sesión XIV) y podría derivarse de ahí.
- **Build frontend con `next build` roto** por errores de TypeScript
  pre-existentes en `react-i18next` (no tocado en esta sesión; el proyecto usa
  `DISABLE_ESLINT_PLUGIN=true` y solo `yarn lint` corre ESLint explícitamente).
- **Los 4 tests nuevos son untracked** (con el resto de cambios sin commitear);
  al commitear, incluir `tests/back/RAG/test_rag_session_validation.py`.

---

# Sesión 22: deduplicación por hash de prompt y generation model (lookup determinístico) + limpieza de constraints viejos `(class_name, parameters)`

## Objetivo

Eliminar la comparación de columnas JSON en el lookup-or-create de prompts y
generation models del módulo RAG. El filtro `filter_by(parameters=dict)` sobre
columnas JSON de SQLAlchemy/SQLite no es confiable (la serialización del JSON
no garantiza orden de claves), así que se adoptó el mismo patrón que ya usaba
`ChunkingService.get_or_create_chunk_set()` con su `signature`: un **hash
SHA-256 determinístico** de los parámetros normalizados, persistido en una
columna propia con `UNIQUE`, y el lookup se hace por ese hash (comparación
`String = String`, siempre confiable).

**Contexto previo:** `PromptService.get_or_create()` (Sesión VIII) buscaba por
`(class_name, parameters)` probando params crudos y luego `sorted(...)`, lo que
era frágil ante el orden de claves del JSON serializado. `LLMService.get_or_create()`
(y `ChunkingService`) compartían la misma debilidad estructural.

## Evolución del trabajo en la sesión

La sesión arrancó con el refactor de extracción de utils compartidos y la
migración del hash (tablas `rag_prompt` y `rag_generation_model`). Al probarlo,
el usuario reportó un `IntegrityError`:

```
sqlalchemy.exc.IntegrityError: (sqlite3.IntegrityError) UNIQUE constraint failed:
rag_generation_model.class_name, rag_generation_model.parameters
[INSERT INTO "RAG_generation_model" (class_name, parameters, parameters_hash) ...]
```

**Causa raíz:** los constraints viejos `uix_rag_gen_model_class_params` y
`uix_rag_prompt_class_params` sobre `(class_name, parameters)` (creados por la
migración `b2c3d4e5f6a7`) seguían activos en la BD y bloqueaban el INSERT de un
registro con `class_name`+`parameters` ya existente aunque el hash fuera
distinto — la migración del hash añadió columnas y constraints nuevos pero no
dropeó los viejos.

**Iteraciones descartadas (parches que NO se aceptaron):** primero se intentó
añadir fallbacks de `IntegrityError` (rollback + re-lookup) en
`llm_service.py` y `prompt_service.py` y comparación raw de JSON en el fallback.
El usuario lo rechazó: _"Estás generando parches, eso no lo va a aceptar el
code reviewer"_. Los fallbacks se revirtieron por completo; la solución final
es estructural (dropear los constraints viejos), no de parcheo.

**Decisión del equipo sobre constraints:** el usuario pidió explícitamente
mantener un constraint para detectar errores. La solución conserva el constraint
`UNIQUE` sobre `parameters_hash` (la columna nueva) como guarda de detección; lo
que se elimina son los constraints viejos `(class_name, parameters)`, que eran
poco fiables sobre JSON en SQLite y duplicaban la protección.

## Archivos modificados

| Archivo                                                                        | Acción                                                                                                                                                                                                                                                                                                                                |
| ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DashAI/back/services/RAG/utils.py`                                            | **Creado** — `normalize_params()` (recursivo, JSON round-trip con `sort_keys=True`) y `build_parameters_hash()` (SHA-256 de `json.dumps(params, sort_keys=True)`), compartidos por prompt/LLM services. La fórmula de hash coincide exactamente con la del backfill de la migración.                                                  |
| `DashAI/back/services/RAG/prompt_service.py`                                   | **Modificado** — importa `normalize_params`/`build_parameters_hash` de `utils`; `get_or_create()` y el retry de `IntegrityError` buscan por `parameters_hash` vía `_find_by_hash()` (reemplaza a `_find_by_class_and_params()`); `create()` y `update()` persisten `parameters_hash` junto a `parameters`.                            |
| `DashAI/back/services/RAG/llm_service.py`                                      | **Modificado** — importa de `utils`; `get_or_create()` calcula `params_hash` una vez y hace `filter_by(parameters_hash=...)`; el INSERT incluye `parameters_hash`.                                                                                                                                                                    |
| `DashAI/back/dependencies/database/models.py`                                  | **Modificado** — añadido `parameters_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)` a `RAGPrompt` y `RAGGenerationModel`; **eliminado** el `__table_args__` con `UniqueConstraint("class_name", "parameters", ...)` de ambas clases (el constraint viejo ya no debe crearse en BD nuevas).                   |
| `DashAI/alembic/versions/a7b3c9d1e5f2_add_parameters_hash_rag.py`              | **Creado** — migración que añade `parameters_hash` a `rag_prompt` y `rag_generation_model`, hace backfill del hash de las filas existentes (`json.dumps(parameters, sort_keys=True)` + SHA-256, igual que el runtime), la hace `NOT NULL` y crea los constraints únicos `uq_rag_prompt_params_hash` / `uq_rag_gen_model_params_hash`. |
| `DashAI/alembic/versions/c8d4e0f2a6b3_drop_class_params_unique_constraints.py` | **Creado** — migración que droppea los constraints viejos `uix_rag_gen_model_class_params` (en `rag_generation_model`) y `uix_rag_prompt_class_params` (en `rag_prompt`) con `batch_alter_table` (SQLite). Downgrade simétrico: los re-crea.                                                                                          |

No se modificó ningún archivo extra: los fallbacks de `IntegrityError` que se
habían añadido a `llm_service.py`/`prompt_service.py` durante la sesión se
revirtieron (excepto el retry por hash que ya existía en `prompt_service.py`
desde la Sesión VIII). La lógica de negocio RAG no se tocó.

## Estado alcanzado

1. **Lookup determinístico por hash** — `PromptService` y `LLMService` deduplican
   comparando `parameters_hash` (SHA-256 de los params normalizados), no el JSON
   crudo. El hash se calcula igual al insertar y al buscar, con una única fuente
   de verdad en `utils.py` (`build_parameters_hash`), y coincide con el backfill
   de la migración (verificado con un parámetro de ejemplo: mismo digest en
   ambos caminos).

2. **IntegrityError eliminado en el flujo real** — con los constraints viejos
   droppeados, el insert de un `RAGGenerationModel`/`RAGPrompt` con los mismos
   `class_name`+`parameters` pero un hash distinto (o una carrera) ya no choca
   con la constraint `(class_name, parameters)`.

3. **Constraint de detección de errores preservado** — la columna
   `parameters_hash` es `NOT NULL` y `UNIQUE` en ambas tablas: la base de datos
   sigue rechazando duplicados reales (dos configs idénticas no pueden existir),
   pero por una clave determinística y fiable en SQLite.

4. **Modelos y migraciones consistentes** — el ORM ya no declara el constraint
   viejo (`__table_args__` eliminado), por lo que `create_all()` de BD frescas
   no lo recrea; la migración `c8d4e0f2a6b3` lo elimina de BD existentes. La
   cadena queda: `a7b3c9d1e5f2` (hash) → `c8d4e0f2a6b3` (drop de viejos).

## Verificación

- **Ruff**: `ruff check` y `ruff format` limpios en los archivos de servicios,
  modelos y las 2 migraciones.
- **Migraciones**: `a7b3c9d1e5f2` es la head que reviza `e9f8a7b6c5d4`;
  `c8d4e0f2a6b3` reviza `a7b3c9d1e5f2`. Ambas importan correctamente
  (`upgrade`/`downgrade`). `alembic check` en BD existente solo reporta "target
  database is not up to date" (las migraciones nuevas no se han aplicado aún en
  la BD de desarrollo).
- **Consistencia de hash**: `build_parameters_hash` produce el mismo digest que
  la fórmula inline de la migración para un mismo dict de parámetros
  (verificado en vivo).
- **Code review** (`code-reviewer`): **0 Critical**, 4 Warnings, todos
  **pre-existentes o no bloqueantes** — W1: nombres de constraint con distinta
  mayúscula entre modelos y migración en las otras tablas RAG (`RAGChunkingModel`,
  `RAGEmbeddingModel`, `RAGSparseRetriever`, `RAGDenseRetriever`); W2:
  `chunking_service.py` sigue usando `filter_by(class_name, parameters)` (fuera
  de alcance de esta sesión); W3: riesgo de divergencia de hash migración vs.
  runtime si algún param no es JSON-nativo (pre-existente); W4: el downgrade de
  `c8d4e0f2a6b3` recrea constraints que el ORM ya no declara (patrón Alembic
  estándar, aceptable).

## Decisiones y hallazgos relevantes

- **Parche vs. solución estructural**: el usuario rechazó explícitamente los
  fallbacks de `IntegrityError` y la comparación raw de JSON como "parches que
  no aceptaría el code reviewer". La solución aprobada droppea la causa raíz
  (constraints viejos sobre JSON) en una migración dedicada.
- **Sí debe haber constraint**: a diferencia de la tentación de "solo droppear
  la unicidad", el usuario pidió mantener la detección de errores; el
  `parameters_hash UNIQUE` cumple ese rol de forma fiable en SQLite (String
  exacto, sin semántica de JSON).
- **La migración del hash no dropeó los viejos**: ese fue el defecto de la
  primera migración (`a7b3c9d1e5f2`). Se corrigió con una migración nueva
  (`c8d4e0f2a6b3`) en vez de modificar la ya aplicada.
- **`RAG_benchmark/` está en `.gitignore`** y el working tree tiene muchas
  sesiones sin commitear (previas y posteriores). **No se usó git** (por
  instrucción del equipo). Los cambios de esta sesión (utils, services, models,
  2 migraciones) quedaron sin commitear junto al resto.

## Pendientes detectados (fuera de alcance de esta sesión)

- **Aplicar las migraciones** en la BD de desarrollo (`alembic upgrade head`) —
  necesario para que el fix surta efecto en el flujo real.
- **Extender el hash al resto de tablas RAG** (code review W1/W2): `RAGChunkingModel`,
  `RAGEmbeddingModel` y retrievers (sparse/dense) siguen con
  `UniqueConstraint("class_name", "parameters", ...)` y lookup por dict JSON;
  `chunking_service.py` sigue usando `filter_by(class_name, parameters)`.
  Heredado de Sesiones III–IV; conviene migrarlos al mismo patrón de
  `parameters_hash`.
- **Alinear nombres de constraint** de los modelos con las migraciones (W1):
  los `__table_args__` de `RAGChunkingModel`/`RAGEmbeddingModel`/`RAGSparseRetriever`/
  `RAGDenseRetriever` declaran `uix_RAG_*` (mayúscula) mientras `b2c3d4e5f6a7`
  creó `uix_rag_*` (minúscula).
- **Divergencia de hash migración vs. runtime** (W3): si algún parámetro
  persistido no es JSON-nativo (Decimal, tipos no estándar), el backfill de la
  migración y `build_parameters_hash` podrían producir digests distintos;
  verificar con datos reales al aplicar la migración.

---

# Sesión 23: fix del preview de documentos RAG — se descargaba el PDF en vez de mostrarse en el modal

## Objetivo

Corregir el render del preview de documentos en el módulo RAG. El usuario
reportó que al hacer clic en el botón "preview" de un documento PDF, en vez de
mostrarse la preview dentro del modal (iframe), el navegador **descargaba** el
archivo.

**Diagnóstico (causa raíz):** el backend ya exponía **dos endpoints** para servir
el contenido de un documento, con disposiciones distintas:

- `/api/v1/document/{id}/download` → `Content-Disposition: attachment` (descarga).
- `/api/v1/document/{id}/view` → `Content-Disposition: inline` (visualización).

`DocumentService._to_response()` ya construía ambos URLs en el response:
`file_url` (apunta a `/download`) y `preview_url` (apunta a `/view`). El problema
era del **frontend**: los componentes que arman la tabla/lista de documentos
asignaban `preview: doc.file_url` (el endpoint de **descarga**) en lugar de
`preview: doc.preview_url` (el de **vista inline**). El `DocumentPreviewModal.jsx`
correctamente renderiza los PDF vía `<iframe src={preview}>`, pero como la URL
apuntaba al endpoint de descarga, el navegador recibía `Content-Disposition:
attachment` y descargaba el archivo en vez de mostrarlo.

## Archivos modificados

Solo frontend; el backend no se tocó (ya tenía la arquitectura correcta).

| Archivo                                                           | Acción                                                                                                                                                                                     |
| ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `DashAI/front/src/types/documentResponse.ts`                      | **Modificado** — añadido `preview_url: string` a la interfaz `IDocumentResponse` (el tipo TS no lo incluía, aunque el backend ya lo devolvía).                                             |
| `DashAI/front/src/pages/generative/RAG/RAGDocumentsPage.jsx`      | **Modificado** — `preview: doc.file_url` → `preview: doc.preview_url` (línea ~153/155).                                                                                                    |
| `DashAI/front/src/components/generative/RAG/DocumentSelector.jsx` | **Modificado** — `preview: doc.file_url` → `preview: doc.preview_url` (línea 67).                                                                                                          |
| `DashAI/front/src/components/generative/RAG/DocumentsBar.jsx`     | **Modificado** — `preview: doc.file_url` → `preview: doc.preview_url` (línea 70, carga inicial) y `preview: savedDoc.file_url` → `preview: savedDoc.preview_url` (línea 130, tras upload). |

No se modificó ningún archivo extra (ni backend, ni benchmark, ni parsers); el
fix es exclusivamente del cableado del frontend al endpoint de vista inline.

## Estado alcanzado

1. **Los tres puntos de entrada de preview usan `preview_url`** (endpoint `/view`,
   `Content-Disposition: inline`): la página de documentos (`RAGDocumentsPage`),
   el selector del wizard de sesión (`DocumentSelector`) y la barra lateral
   (`DocumentsBar`, tanto en carga como tras un upload). El iframe del
   `DocumentPreviewModal` recibe ahora una URL que el navegador renderiza en
   línea.

2. **`IDocumentResponse` completo** — el tipo TypeScript ahora declara
   `preview_url: string` (y el backend ya lo incluía en el payload, por lo que
   los datos llegan sin cambios de servidor).

3. **PDF y TXT** — el modal conserva la lógica previa (PDF vía iframe, TXT vía
   fetch + `<pre>`); solo cambia la URL fuente de la preview.

## Verificación

- **Inspección del código**: se confirmó con grep/lectura que los 3 componentes
  asignan `preview` desde `doc.preview_url` (y `savedDoc.preview_url` en el
  upload de `DocumentsBar`) y que `documentResponse.ts` declara `preview_url`.
- **Backend**: no se tocó; `_serve_document` con `DISPOSITION_INLINE` ya servía
  el `/view` correctamente desde la Sesión de creación del módulo.
- **Revisión (code-reviewer)**: la tarea de code review fue **abortada por el
  usuario** antes de completarse, por lo que no hay veredicto de reviewer para
  esta sesión. La implementación fue delegada y aplicada por un subagente; los
  cambios quedaron verificados por inspección directa del Tech Lead.
- **Verificación visual pendiente del usuario**: abrir la preview de un PDF en
  la app corriendo y confirmar que se muestra en el modal (y no descarga).

## Decisiones y hallazgos relevantes

- **El backend ya tenía la arquitectura correcta** (endpoints separados de
  descarga y vista): el bug era 100 % de cableado del frontend. No hizo falta
  cambiar `Content-Disposition`, ni el servicio, ni los modelos.
- **`preview_url` es la URL correcta para cualquier render inline** (iframe,
  `<object>`, `<embed>`); `file_url` queda reservado para acciones de descarga
  explícitas. Los componentes `DocumentTable`/`DocumentList`/`DocumentSelector`
  solo usan la preview, así que todos debían apuntar a `/view`.
- **`DocumentListItem` usa `document.type`** (mayúscula normalizada en
  `DocumentsBar`) para el icono, mientras `DocumentTable`/`DocumentSelector`
  usan `file_type` (extensión en minúscula) para decidir el render TXT vs. PDF;
  ambas rutas convergen en `DocumentPreviewModal`, que soporta ambos campos
  (`document?.file_type || document?.type`).
- **No se usó git** durante la sesión (por instrucción del equipo: hay muchas
  sesiones sin commitear, previas y posteriores a esta). El working tree ya
  contenía cambios de las Sesiones XIV–XXII y anteriores.

## Pendientes detectados (fuera de alcance de esta sesión)

- **Completar la revisión por `code-reviewer`** de los 4 archivos modificados
  (la tarea fue abortada). El cambio es mínimo y de baja complejidad, pero la
  revisión quedó pendiente por proceso.
- **Verificación visual en la app**: abrir la preview de un PDF (y un TXT) con
  el servidor corriendo para confirmar el render inline en el modal.
- **Posible limpieza futura**: revisar si algún otro llamador de
  `DocumentPreviewModal` o consumidor de `file_url` para preview quedó sin
  migrar a `preview_url` (grep repo-wide de `file_url` en componentes de UI al
  momento de la sesión no mostró más usos de preview).

---

# Sesión 24: extractores de documentos — schemas reales, asignación en upload y UX del panel de detalle

## Objetivo

Cerrar la funcionalidad de **extractores de documentos** del módulo RAG. Se
trabajó en dos bloques:

1. **Schemas de extractores**: los 5 extractores (`PlainTextExtractor`,
   `PypdfExtractor`, `PyMuPDFExtractor`, `TextractExtractor`, `EasyOCRExtractor`)
   exponen sus parámetros reales como `ConfigObject` (schema-driven). Se
   corrigió un bug por el que **las `description` de algunos campos no llegaban
   al frontend** (el card del formulario solo mostraba el nombre del parámetro)
   y un bug derivado por el que **los campos se veían vacíos y la validación los
   rechazaba como "required field"**.
2. **UX del panel de detalle de documentos** (reportado por el usuario):
   1. `/documents` mostraba "Por defecto" sin indicar qué extractor se usa. Se
      decidió que **el extractor se asigna y persiste en el momento del upload**:
      nunca debe existir ambigüedad, no se rellena después.
   2. Permitía extraer con "Por defecto" sin mostrar su schema → ahora el
      schema del extractor activo **siempre** se muestra.
   3. Schema fields vacíos + "is a required field" al extraer → se arregló con
      `default=placeholder` en `schema_field()`.
   4. El panel de preview debía poder minimizarse/maximizarse → `Collapse` con
      toggle y auto-apertura tras extraer.

## Causas raíz (en orden de aparición)

1. **Pydantic V2 descarta `Field()` metadata cuando hay type annotation
   explícita**: `field: bool = schema_field(...)` hace que Pydantic use `bool`
   como tipo e ignore el `Annotated[bool, Field(...)]` del default (se pierde
   `description`). Los schemas de `PypdfSchema`, `PyMuPDFSchema` y
   `TextractSchema` usaban ese patrón; `PlainTextSchema` y `EasyOCRSchema` no,
   por eso ellos sí mostraban las descripciones.
2. **`schema_field()` no pasaba `default` a `Field()`**: al usar el patrón
   `field: schema_field(...)` (sin annotation explícita), Pydantic marcaba el
   campo como **required** (no hay default). El frontend mostraba el campo vacío
   y al extraer la validación rechazaba con "[param] is a required field".
3. **Sin extractor al subir un documento**: `upload()` creaba el `Document` sin
   `extractor_id`; la UI caía en "Por defecto" y el schema no se mostraba.
4. **`extractor_id` nullable**: la columna era `nullable=True` con
   `ondelete="SET NULL"`, permitiendo documentos sin extractor (ambigüedad).

## Archivos modificados

### Backend — producción

| Archivo                                                                  | Acción                                                                                                                                                                                                                                                                                                                                                     |
| ------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DashAI/back/core/schema_fields/schema_field.py`                         | **Modificado** — se añadió `"default": placeholder` a `field_params`. Ahora los campos schema-driven tienen default (Pydantic no los marca required) y el JSON schema expone `default`.                                                                                                                                                                    |
| `DashAI/back/models/RAG/extractors/pypdf2_extractor.py`                  | **Modificado** — `strict: bool = schema_field(...)` → `strict: schema_field(...)` (recupera `description`).                                                                                                                                                                                                                                                |
| `DashAI/back/models/RAG/extractors/pymupdf_extractor.py`                 | **Modificado** — `password: Optional[str] = schema_field(...)` → `password: schema_field(...)`; se quitó el import `Optional` sin uso.                                                                                                                                                                                                                     |
| `DashAI/back/models/RAG/extractors/textract_extractor.py`                | **Modificado** — `language`/`method` al patrón `field: schema_field(...)`; se quitó `Optional`; línea de description partida (E501).                                                                                                                                                                                                                       |
| `DashAI/back/services/RAG/document_service.py`                           | **Modificado** — `upload()` crea `RAGExtractor` con el default por tipo de archivo **antes** de crear el `Document` (y en el caso hash-dedup si `extractor_id is None`); `_to_response()` rellena `extractor` con el default de `_DEFAULT_EXTRACTORS` cuando `extractor_record` es None (edge case pre-migración) y añade `default_extractor` al response. |
| `DashAI/back/api/api_v1/schemas/document.py`                             | **Modificado** — se añadió `default_extractor: Optional[Dict[str, Any]] = None` a `DocumentResponse`.                                                                                                                                                                                                                                                      |
| `DashAI/back/dependencies/database/models.py`                            | **Modificado** — `Document.extractor_id` ahora `Mapped[int]`, `nullable=False`, FK `ondelete="RESTRICT"` (no se puede borrar un extractor en uso).                                                                                                                                                                                                         |
| `DashAI/alembic/versions/h1i2j3k4l5m6_make_extractor_id_not_nullable.py` | **Creado** — migración: backfillea documentos con `extractor_id IS NULL` creando `RAGExtractor` con el default por `file_type`; altera la columna a NOT NULL y recrea la FK con `RESTRICT` (batch mode SQLite).                                                                                                                                            |

### Frontend

| Archivo                                                              | Acción                                                                                                                                                                                                                                                                                        |
| -------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DashAI/front/src/components/generative/RAG/DocumentDetailPanel.jsx` | **Modificado** — se eliminó el `<MenuItem>` de "Por defecto"; el extractor activo siempre es el del documento (nunca cadena vacía); el `FormSchema` del extractor se renderiza siempre; preview con `Collapse` + `IconButton` (expandir/colapsar) y auto-apertura al terminar una extracción. |
| `DashAI/front/src/components/generative/RAG/DocumentTable.jsx`       | **Modificado** — el `valueGetter` de la columna extractor devuelve `row?.extractor?.component` (siempre poblado, sin fallback "Por defecto").                                                                                                                                                 |
| `DashAI/front/src/types/documentResponse.ts`                         | **Modificado** (durante el plan inicial) — se declaró `default_extractor` en `IDocumentResponse`.                                                                                                                                                                                             |

### Tests

| Archivo                                         | Acción                                                                                                                                                                                                                                                                                                                        |
| ----------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tests/back/RAG/conftest.py`                    | **Modificado** — helper `_create_test_document` crea `RAGExtractor` (txt→`PlainTextExtractor`) y lo asigna; usado por varios fixtures.                                                                                                                                                                                        |
| `tests/back/RAG/test_extraction_cache_flow.py`  | **Modificado** — helper `_create_document` con mapa por tipo (pdf→`TextractExtractor`, txt/md→`PlainTextExtractor`); se eliminó el caso `strict=True` en `test_pypdf2_different_params` (usaba `PyMuPDFExtractor` con `password`).                                                                                            |
| `tests/back/RAG/test_document_extractor_api.py` | **Modificado** — helper `_create_document` (5 call sites refactorizados).                                                                                                                                                                                                                                                     |
| `tests/back/RAG/test_RAG_prompts.py`            | **Modificado** — `_create_test_document` con extractor.                                                                                                                                                                                                                                                                       |
| `tests/back/api/test_session_api.py`            | **Modificado** — extractor inline por documento en el loop.                                                                                                                                                                                                                                                                   |
| `tests/back/RAG/test_RAG_strict_validation.py`  | **Modificado** — tests que enviaban params vacíos y esperaban 400 ahora esperan 201 (los defaults del schema aplican); docstring actualizado al nuevo contrato de defaults.                                                                                                                                                   |
| `tests/back/RAG/test_RAG_session_validation.py` | **Modificado** — `test_auto_save_partial_data_preserves_component` usa un `model_name` válido del enum y espera 201; `params2` de `test_prompt_validate_template_parametrized` con el nombre de componente corregido (`DefaultQARAGGenerationPrompt`, doble G) y template distinto para evitar colisión de `parameters_hash`. |

## Estado alcanzado

1. **Schemas con descripción y default**: todos los campos de los 5 extractores
   exponen `description` (título legible en el card del formulario) y `default`
   en el JSON schema. Verificado con
   `replace_defs_in_schema(PypdfSchema.model_json_schema())` → `strict` tiene
   `default=True` y su description.

2. **Extractor asignado en el upload**: `DocumentService.upload()` crea el
   `RAGExtractor` del default por tipo de archivo (`_DEFAULT_EXTRACTORS`:
   pdf→`TextractExtractor`, txt/md/rst/tex/csv→`PlainTextExtractor`) y lo asigna
   a `doc.extractor_id` **antes** del commit. El caso hash-dedup también asigna
   si el documento existente no tenía extractor.

3. **`extractor_id` NOT NULL**: invariante a nivel de base de datos. La
   migración backfillea los documentos sin extractor y recrea la FK con
   `ondelete="RESTRICT"`. En `_to_response()` el response siempre lleva
   `extractor` poblado (desde el record o desde el default por tipo) y además
   `default_extractor` como dato defensivo para el frontend.

4. **Frontend sin ambigüedad**: no existe opción "Por defecto"; el select y la
   tabla muestran el nombre real del extractor; el schema del extractor activo
   se muestra siempre; el preview es colapsable y se abre al extraer.

## Diagrama final

```
DocumentService.upload(file_type)
  └─ _DEFAULT_EXTRACTORS[file_type] → RAGExtractor(component_name, params={})
       └─ Document(extractor_id=<nuevo RAGExtractor.id>)   [extractor_id NOT NULL]

DocumentService._to_response(doc)
  └─ extractor = {component, params}  (siempre poblado: record o default por tipo)
  └─ default_extractor = {component, params}  (solo cuando no hay record explícito)

Frontend DocumentDetailPanel
  └─ select del extractor: nunca cadena vacía / "Por defecto"
  └─ FormSchema del extractor: siempre renderizado
  └─ preview: <Collapse in={previewOpen}> con toggle y auto-apertura
```

## Verificación

- **Tests**: `pytest tests/back/RAG/ -q` → **242 passed, 0 failed** (incluye
  extractores, cache flow, session validation, strict validation, prompts,
  cross-encoder). `pytest tests/back/RAG/test_cross_encoder_retriever.py` y las
  configs de componentes/pipeline siguen verdes.
- **Ruff**: `ruff check` y `ruff format --check` limpios en los archivos
  backend tocados.
- **Migración**: `alembic upgrade head` aplicado en la BD de desarrollo
  (`~/.DashAI/sqlite.db`); backfill funcionó (documentos PDF sin extractor
  recibieron `TextractExtractor`); `PRAGMA table_info(document)` confirma
  `extractor_id notnull=1` y FK `on_delete=RESTRICT`.
- **Diagnóstico de schemas**: los 5 schemas de extractores muestran
  `description` y `default` tras `replace_defs_in_schema`.
- **Frontend**: prettier/eslint limpios en los archivos tocados (verificado por
  el subagente; el build completo de Next.js tarda y no se relanzó en esta
  sesión).

## Decisiones y hallazgos relevantes

- **El extractor se asigna al subir (decisión del equipo)**: al corregir el
  reporte de "Por defecto", el plan inicial era añadir `default_extractor` y
  resolverlo en el frontend. El equipo lo descartó: _"al subir el documento se
  debe guardar el extractor, una vez subido no debe existir ambigüedad
  respecto al extractor, no se debe rellenar después"_. Por eso la asignación
  ocurre en `upload()` y la columna pasó a NOT NULL.
- **Bug de Pydantic V2 (description perdida)**: `strict: bool = schema_field(...)`
  hace que Pydantic ignore el `Annotated[..., Field(description=...)]` del
  default. El patrón correcto es `field: schema_field(...)` (sin annotation
  explícita), igual que `PlainTextSchema`/`EasyOCRSchema`. El `# type:
ignore[valid-type]` es necesario porque mypy no entiende `Annotated` como
  type annotation válida.
- **`default=placeholder` cambia el contrato de validación**: antes los params
  vacíos fallaban la validación (400) porque Pydantic marcaba los campos como
  required. Ahora los defaults aplican automáticamente (201). Se actualizaron
  los tests de `test_RAG_strict_validation.py` para reflejar el contrato
  correcto: campos con default aceptan params vacíos/missing y usan el default.
- **`PyMuPDFExtractor.password`**: `fitz.open()` no acepta `password` como
  kwarg; se usa `doc.needs_pass` + `doc.authenticate(password)` tras abrir el
  documento.
- **`RAGExtractor` compartido**: la tabla `rag_extractor` es un catálogo
  canónico de configs; múltiples documentos pueden referenciar el mismo
  extractor vía FK. No se deduplican registros idénticos (decisión previa del
  módulo).
- **No se usó git** durante la sesión (por instrucción del equipo: hay muchas
  sesiones sin commitear, previas y posteriores a esta). El working tree ya
  contenía el trabajo de sesiones anteriores.

## Pendientes detectados (fuera de alcance de esta sesión)

- **Verificación visual del usuario**: abrir la app y confirmar (a) la columna
  de la tabla de documentos muestra el nombre real del extractor, (b) el panel
  de detalle muestra el schema del extractor activo, (c) el preview colapsable
  funciona y (d) los campos del schema aparecen con sus defaults.
- **`default_extractor` quedó en el response** como dato defensivo para
  documentos pre-migración; puede revisarse si tras el backfill sigue siendo
  necesario o se elimina para simplificar el contrato.
- **Alembic `command.check`** reporta drift pre-existente ajeno a esta sesión
  (renombres `rag_*` → `RAG_*` en tablas); la migración de esta sesión sí queda
  en sync con el modelo.
- **`PypdfExtractor` por defecto es `strict=True`**: PDFs malformados (xref
  roto) fallan con `RAGDocumentParsingError`. Los tests de cache usan
  `strict=False` explícitamente para el PDF de prueba minimal. El default de la
  librería pypdf se mantiene tal cual (decisión consciente).

---

## Estado final

Las 24 sesiones documentadas en este backlog fueron commiteadas el 2026-08-12
en 10 commits organizados por funcionalidad:

1. `33c3db67f` Alembic migrations (6 migraciones de schema RAG)
2. `06c45c56c` Backend — RAG services architecture + business logic
3. `9c8bb7f55` Backend — Cross-encoder retrievers + retriever fixes
4. `19e7738a6` Backend — Remote model schemas (OpenAI + DeepSeek)
5. `4a280010c` Backend — Document extractors system
6. `cb9434ff6` Backend — Embedding placeholder fix
7. `5e165731d` Frontend — RAG wizard (retriever config, validation, tree)
8. `646e501c5` Frontend — RAG documents UX (preview, extractor panel)
9. `44c6cfb21` Tests — 10 nuevos archivos + 11 modificados (271 tests)
10. `18fa80dad` Docs + Config + Cleanup

**Total:** ~96 archivos modificados/creados, 271 tests pasando, 0 regresiones.

Este archivo (`backlog.md`) no fue commiteado por instrucción del equipo.
