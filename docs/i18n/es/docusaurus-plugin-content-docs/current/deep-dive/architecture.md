---
title: Arquitectura
sidebar_label: Arquitectura
---

DashAI es una plataforma modular y extensible para flujos de trabajo de aprendizaje automático. Proporciona una interfaz web para entrenar modelos, explorar conjuntos de datos, explicar predicciones y más. Este documento describe el funcionamiento interno de DashAI.

## Tabla de Contenidos

- [Visión General de Alto Nivel](#high-level-overview)
- [API](#api)
- [Componentes](#components)
- [Registro de Componentes](#component-registry)
- [Objeto Configurable](#configurable-object)
- [Base de Datos](#database)
- [Cola de Trabajos](#job-queue)
- [Trabajo](#job)
- [Ejemplos de Flujo de Trabajo](#workflow-examples)
  - [Entrenando un Modelo](#training-a-model)
  - [Creando un Gráfico para un Conjunto de Datos](#creating-a-plot-for-a-dataset)

---

## Visión General de Alto Nivel {#high-level-overview}

DashAI sigue una arquitectura cliente-servidor con tres procesos principales en tiempo de ejecución:

1. **Backend FastAPI** — sirve la API REST en el puerto 8000. En producción también sirve el SPA de React compilado en `/app/`.
2. **Consumidor Huey** — un trabajador en segundo plano que procesa tareas de larga duración (entrenamiento, exploración, predicción, etc.).
3. **Frontend React** — una aplicación de página única que se comunica con el backend a través de la API REST. En desarrollo se ejecuta de forma independiente en el puerto 3000 (`yarn start`); en producción se compila y es servida por FastAPI.

El punto de entrada es `DashAI/__main__.py`, que utiliza Typer como CLI. Al iniciarse:

1. Resuelve la ruta de datos local (por defecto `~/.DashAI`).
2. Inicia el consumidor Huey. En desarrollo (instalación Python normal) esto se hace mediante un **subproceso** externo; en modo empaquetado (PyInstaller) se ejecuta como un **hilo** en el mismo proceso.
3. Inicia el servidor FastAPI a través de Uvicorn.
4. Opcionalmente abre un navegador o una ventana PyWebView.

La inyección de dependencias es gestionada por **Kink**. El contenedor DI (`back/container.py`) conecta el motor de base de datos, la fábrica de sesiones, el registro de componentes y la cola de trabajos, de modo que los endpoints de la API los reciban automáticamente.

---

## API {#api}

DashAI usa **FastAPI** para exponer una API RESTful. Todos los endpoints se encuentran bajo el prefijo `/api/v1`.

### Estructura de Routers

La aplicación principal de FastAPI se crea en `back/app.py`. Monta un único `APIRouter` definido en `back/api/api_v1/api.py`, que agrupa routers individuales para cada recurso:

| Archivo de Router      | Recurso               | Propósito                                                        |
| ---------------------- | --------------------- | ---------------------------------------------------------------- |
| `components.py`        | `/component`          | Listar y filtrar componentes registrados                         |
| `datasets.py`          | `/dataset`            | Cargar, listar y validar conjuntos de datos                      |
| `model_sessions.py`    | `/model-session`      | CRUD para sesiones de entrenamiento de modelos                   |
| `runs.py`              | `/run`                | CRUD para ejecuciones de entrenamiento, métricas y gráficos de optimización |
| `jobs.py`              | `/job`                | Encolar trabajos y consultar su estado                           |
| `explorers.py`         | `/explorer`           | Iniciar y recuperar exploraciones de datos                       |
| `explainers.py`        | `/explainer`          | Iniciar explicaciones de modelos                                 |
| `converters.py`        | `/converter`          | Aplicar transformaciones de datos                                |
| `predict.py`           | `/predict`            | Ejecutar predicciones sobre nuevos datos                         |
| `plugins.py`           | `/plugin`             | Gestionar plugins                                                |
| `pipelines.py`         | `/pipeline`           | Orquestar flujos de trabajo complejos                            |
| `generative_session.py`| `/generative-session` | Sesiones de modelos generativos                                  |

### Inyección de Dependencias en Endpoints

Los endpoints reciben dependencias a través del mecanismo `Depends` de FastAPI combinado con el contenedor `di` de Kink:

```python
@router.post("/")
@inject
async def enqueue_job(
    job_params: JobParams,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
    component_registry: ComponentRegistry = Depends(lambda: di["component_registry"]),
    job_queue: BaseJobQueue = Depends(lambda: di["job_queue"]),
):
    ...
```

### Internacionalización

La API soporta respuestas multilingües. Los nombres de visualización y las descripciones de los componentes se almacenan como objetos `MultilingualString`, y la API los filtra según el encabezado `Accept-Language`.

---

## Componentes {#components}

Un **componente** es el bloque de construcción fundamental de DashAI. Toda pieza de funcionalidad conectable — modelos, tareas, métricas, exploradores, explicadores, convertidores, cargadores de datos, optimizadores y trabajos — es un componente.

### Tipos de Componentes

Cada clase de componente declara un atributo de clase `TYPE` que determina su categoría:

| TYPE          | Clase base        | Propósito                                     | Ejemplos                                     |
| ------------- | ----------------- | --------------------------------------------- | -------------------------------------------- |
| `Model`       | `BaseModel`       | Entrenar y predecir                           | SVC, RandomForest, DistilBertTransformer     |
| `Task`        | `BaseTask`        | Definir la semántica de la tarea de ML        | TextClassification, Regression, Translation  |
| `Metric`      | `BaseMetric`      | Evaluar el rendimiento del modelo             | Accuracy, F1, RMSE, MAE                      |
| `Explorer`    | `BaseExplorer`    | Visualizar y analizar datos                   | ScatterPlotExplorer, HistogramPlotExplorer   |
| `Explainer`   | `BaseExplainer`   | Interpretar las predicciones del modelo       | KernelShap, PermutationFeatureImportance     |
| `Converter`   | `BaseConverter`   | Transformar características                   | StandardScaler, OneHotEncoder, PCA, SMOTE    |
| `DataLoader`  | `BaseDataLoader`  | Cargar conjuntos de datos desde archivos      | CSVDataLoader, ExcelDataLoader               |
| `Optimizer`   | `BaseOptimizer`   | Optimización de hiperparámetros               | Optimizadores basados en Optuna              |
| `Job`         | `BaseJob`         | Ejecución de tareas en segundo plano          | ModelJob, ExplorerJob, PredictJob            |

### Metadatos de Componentes

Cada componente puede exponer metadatos utilizados por el frontend para su visualización y filtrado:

- `DESCRIPTION` — una descripción multilingüe de lo que hace el componente.
- `DISPLAY_NAME` — un nombre legible por humanos.
- `COLOR` — un color hexadecimal para la representación en la interfaz.
- `COMPATIBLE_COMPONENTS` — una lista de nombres de componentes con los que este componente es compatible (por ejemplo, una métrica que solo aplica a tareas de clasificación).

---

## Registro de Componentes {#component-registry}

El **Registro de Componentes** (`back/dependencies/registry/component_registry.py`) es un catálogo centralizado de todos los componentes disponibles. Se crea durante el inicio de la aplicación y se almacena en el contenedor DI.

### Registro

Cuando se registra una clase de componente, el registro:

1. Lee el atributo de clase `TYPE` para determinar la categoría del componente.
2. Verifica si la clase es un objeto configurable (tiene `get_schema()`).
3. Extrae metadatos (`DESCRIPTION`, `DISPLAY_NAME`, `COLOR`, etc.).
4. Almacena el componente en un diccionario jerárquico indexado por tipo y nombre.

Cada componente registrado se almacena como un diccionario:

```python
{
    "name": "SVC",
    "type": "Model",
    "class": SVCClass,
    "configurable_object": True,
    "schema": { ... },       # JSON Schema si es configurable
    "metadata": { ... },
    "description": MultilingualString(...),
    "display_name": MultilingualString(...),
    "color": "#3498db",
}
```

### Métodos de Búsqueda

| Método                                          | Descripción                                                              |
| ----------------------------------------------- | ------------------------------------------------------------------------ |
| `registry[name]`                                | Búsqueda directa por nombre de componente                                |
| `get_components_by_types(select, ignore)`        | Filtrar componentes por tipo (por ejemplo, solo Modelos)                 |
| `get_child_components(parent_name)`              | Obtener todos los componentes que heredan de un padre dado               |
| `get_related_components(component_id)`           | Obtener componentes compatibles vía `COMPATIBLE_COMPONENTS`              |

### Inicialización

La lista de componentes a registrar al inicio se define en `back/initial_components.py`. Se pueden agregar componentes adicionales en tiempo de ejecución a través del sistema de plugins.

---

## Objeto Configurable {#configurable-object}

Un **Objeto Configurable** es cualquier componente cuyo comportamiento puede personalizarse mediante parámetros suministrados por el usuario. El mecanismo se construye sobre Pydantic y JSON Schema.

### Cómo Funciona

1. **Definición del esquema** — Un componente define un atributo de clase `SCHEMA` como un modelo Pydantic. Cada campo del modelo representa un parámetro configurable:

   ```python
   class SVCSchema(BaseSchema):
       C: float = Field(default=1.0, description="Regularization parameter")
       kernel: str = Field(default="rbf", description="Kernel type")
   ```

2. **Generación del esquema** — `get_schema()` convierte el modelo Pydantic en un diccionario de JSON Schema. El frontend usa este esquema para renderizar dinámicamente los formularios de configuración.

3. **Validación y transformación** — Cuando el usuario envía una configuración, el backend llama a `validate_and_transform(params)`, que:
   - Valida los datos de parámetros en bruto contra el esquema Pydantic.
   - Instancia recursivamente cualquier referencia a componentes anidados (un parámetro de tipo `ComponentType` se resuelve en una instancia real del componente).

### Campos de Componentes

La utilidad `component_field()` (`back/core/schema_fields/component_field.py`) crea parámetros que hacen referencia a otros componentes. Por ejemplo, un modelo podría aceptar un convertidor como parámetro:

```python
class MyModelSchema(BaseSchema):
    preprocessor: ComponentType = component_field(
        component_type="Converter",
        description="Optional data preprocessor",
    )
```

El frontend renderiza esto como un menú desplegable poblado desde el registro, y el backend instancia el convertidor seleccionado cuando se crea el modelo.

---

## Base de Datos {#database}

DashAI usa **SQLite** como base de datos (almacenada en `~/.DashAI/db.sqlite`) con **SQLAlchemy** como ORM y **Alembic** para las migraciones de esquema.

### Tablas Principales

| Tabla              | Propósito                                                             |
| ------------------ | --------------------------------------------------------------------- |
| `Dataset`          | Conjuntos de datos cargados (nombre, ruta de archivo, estado, marcas de tiempo) |
| `ModelSession`     | Configuración de sesión de entrenamiento (conjunto de datos, tarea, columnas, divisiones, métricas seleccionadas) |
| `Run`              | Ejecución individual de entrenamiento (nombre del modelo, parámetros, optimizador, estado, rutas de gráficos) |
| `Metric`           | Valores de métricas por ejecución, división y nivel                   |
| `Prediction`       | Resultados de predicción (ejecución, conjunto de datos, ruta de resultados) |
| `Notebook`         | Notebooks de exploración (conjunto de datos, ruta de archivo, estado) |
| `Explorer`         | Registros de exploración (tipo, columnas, parámetros, ruta de resultados) |
| `Plugin`           | Plugins instalados                                                    |
| `GlobalExplainer`  | Explicaciones globales del modelo                                     |
| `LocalExplainer`   | Explicaciones locales del modelo (por instancia)                      |

### Enumeraciones Importantes

- **`RunStatus`**: `NOT_STARTED` → `DELIVERED` → `STARTED` → `FINISHED` | `ERROR`
- **`SplitEnum`**: `TRAIN`, `VALIDATION`, `TEST`
- **`LevelEnum`**: `LAST` (valor final), `STEP`, `BATCH`, `TRIAL` (para optimización)

### Almacenamiento de Datos

- **Los conjuntos de datos** se almacenan en formato Apache Arrow IPC (columnar, eficiente para cargas de trabajo de ML).
- **Los modelos entrenados** se guardan como archivos pickle/joblib en `~/.DashAI/runs/{run_id}/`.
- **Los gráficos** generados durante la optimización de hiperparámetros se almacenan como objetos Plotly serializados.
- **Las series temporales de métricas** (por paso, lote o prueba) se almacenan en la tabla `Metric` para el seguimiento del progreso del entrenamiento.

---

## Cola de Trabajos {#job-queue}

La **Cola de Trabajos** gestiona la ejecución asincrónica de tareas de larga duración. DashAI utiliza **Huey** — una cola de tareas Python ligera — respaldada por una base de datos SQLite.

### Arquitectura

| Capa              | Implementación                                                          |
| ----------------- | ----------------------------------------------------------------------- |
| Base abstracta    | `BaseJobQueue` (`back/dependencies/job_queues/base_job_queue.py`)       |
| Implementación    | `HueyJobQueue` (`back/dependencies/job_queues/huey_job_queue.py`)       |
| Almacenamiento    | SQLite en `~/.DashAI/job_queue.db` (separada de la BD principal)        |
| Serialización     | `dill` (maneja objetos Python complejos como lambdas)                   |

### Cómo Funciona la Cola

1. Un endpoint de la API llama a `job_queue.put(job)`, que encola el trabajo y retorna un ID de trabajo de inmediato.
2. El hilo consumidor de Huey (iniciado al arrancar la aplicación) recoge el trabajo y llama a `job.run()`.
3. El ciclo de vida del trabajo es rastreado mediante señales de Huey y una tabla `task_copy`:

   | Señal               | Actualización de estado |
   | ------------------- | ----------------------- |
   | `SIGNAL_ENQUEUED`   | `not_started`           |
   | `SIGNAL_EXECUTING`  | `started`               |
   | `SIGNAL_COMPLETE`   | `finished`              |
   | `SIGNAL_ERROR`      | `error`                 |

4. El frontend consulta `GET /api/v1/job/status/{job_id}` para hacer seguimiento del progreso.

### Métodos Principales

| Método                | Descripción                                        |
| --------------------- | -------------------------------------------------- |
| `put(job)`            | Encolar un trabajo, retorna el ID del trabajo      |
| `get(job_id)`         | Obtener el estado y metadatos del trabajo          |
| `peek()`              | Ver el próximo trabajo sin desencolarlo            |
| `is_empty()`          | Verificar si la cola tiene trabajos pendientes     |
| `async_get(job_id)`   | Versión asincrónica de get                         |

El backend SQLite usa el modo Write-Ahead Logging (WAL) para un acceso concurrente seguro entre el proceso de la API y el consumidor Huey.

---

## Trabajo {#job}

Un **Trabajo** encapsula una unidad de trabajo en segundo plano. Todos los trabajos heredan de `BaseJob` (`back/job/base_job.py`).

### Interfaz Base

```python
class BaseJob(metaclass=ABCMeta):
    TYPE = "Job"

    @abstractmethod
    def run(self) -> None: ...

    @abstractmethod
    def set_status_as_delivered(self) -> None: ...

    @abstractmethod
    def set_status_as_error(self) -> None: ...

    @abstractmethod
    def get_job_name(self) -> str: ...
```

### Tipos de Trabajos

| Clase de Trabajo     | Propósito                                                  |
| -------------------- | ---------------------------------------------------------- |
| `ModelJob`           | Entrenar un modelo y calcular métricas                     |
| `ExplorerJob`        | Ejecutar una exploración/visualización de datos            |
| `ExplainerJob`       | Generar explicaciones del modelo (SHAP, etc.)              |
| `PredictJob`         | Ejecutar predicciones sobre nuevos datos                   |
| `ConverterListJob`   | Aplicar una secuencia de transformaciones de datos         |
| `PipelineJob`        | Orquestar flujos de trabajo de múltiples pasos             |
| `GenerativeJob`      | Gestionar interacciones con modelos generativos            |
| `DatasetJob`         | Cargar y procesar conjuntos de datos                       |

Cada tipo de trabajo gestiona sus propias transiciones de estado en la base de datos y el manejo de errores. Cuando un trabajo falla, registra el mensaje de error en la base de datos y actualiza el estado de la entidad correspondiente a `ERROR`.

---

## Ejemplos de Flujo de Trabajo {#workflow-examples}

### Entrenando un Modelo {#training-a-model}

Este ejemplo recorre todo el proceso de entrenamiento de un modelo de clasificación de texto, desde la interacción del usuario hasta los resultados finales.

#### Paso 1: Crear una Sesión de Modelo

El usuario selecciona un conjunto de datos, una tarea, columnas de entrada/salida, métricas y divisiones de datos en el frontend. El frontend envía:

```
POST /api/v1/model-session/
{
    "dataset_id": 1,
    "task_name": "TextClassification",
    "input_columns": ["text"],
    "output_columns": ["label"],
    "train_metrics": ["Accuracy", "F1"],
    "validation_metrics": ["Accuracy"],
    "test_metrics": ["Accuracy"],
    "splits": { "train": 0.7, "validation": 0.15, "test": 0.15 }
}
```

La API crea un registro `ModelSession` en la base de datos y retorna su ID.

#### Paso 2: Crear una Ejecución

El usuario selecciona un modelo, configura sus parámetros y opcionalmente elige un optimizador de hiperparámetros. El frontend envía:

```
POST /api/v1/run/
{
    "model_session_id": 1,
    "model_name": "DistilBertTransformer",
    "parameters": { "learning_rate": 1e-5, "num_epochs": 3 },
    "optimizer_name": null,
    "optimizer_parameters": {},
    "goal_metric": "F1",
    "name": "DistilBERT run"
}
```

La API crea un registro `Run` con estado `NOT_STARTED`.

#### Paso 3: Encolar el Trabajo de Entrenamiento

El frontend solicita la ejecución del trabajo:

```
POST /api/v1/job/
{
    "job_type": "ModelJob",
    "kwargs": { "run_id": 1 }
}
```

La API instancia un `ModelJob` con el `run_id` dado, llama a `job_queue.put(job)` y retorna el ID del trabajo Huey al frontend de inmediato.

#### Paso 4: Ejecución en Segundo Plano

El consumidor Huey recoge el `ModelJob` y llama a `job.run()`. Dentro de `run()`:

1. Cargar los registros `Run`, `ModelSession` y `Dataset` desde la base de datos.
2. Cargar el conjunto de datos desde su archivo Arrow.
3. Instanciar la clase `Task` (por ejemplo, `TextClassification`) y llamar a `prepare_for_task()` para validar y formatear los datos.
4. Dividir los datos en subconjuntos de entrenamiento/validación/prueba según las proporciones de división de la sesión.
5. Instanciar la clase `Model` (por ejemplo, `DistilBertTransformer`) con los parámetros del usuario a través de `validate_and_transform()`.
6. Llamar a `model.train(x_train, y_train, x_val, y_val)`.
7. Para cada división (entrenamiento, validación, prueba), llamar a `model.calculate_metrics()`, que calcula todas las métricas seleccionadas y las almacena en la tabla `Metric`.
8. Guardar el modelo entrenado en disco en `~/.DashAI/runs/{run_id}/`.
9. Actualizar el estado de `Run` de `STARTED` a `FINISHED`.

Si se configura un optimizador de hiperparámetros, el paso 6 es reemplazado por `optimizer.optimize()`, que ejecuta múltiples pruebas, rastrea las métricas por prueba (`LevelEnum.TRIAL`) y genera gráficos de visualización Plotly (historial, segmento, contorno, importancia) guardados junto a la ejecución.

#### Paso 5: Recuperar Resultados

El frontend consulta el estado de finalización y recupera los resultados:

```
GET /api/v1/job/status/{job_id}         # Consultar hasta que finalice
GET /api/v1/run/{run_id}                # Obtener detalles de la ejecución con métricas
GET /api/v1/run/plot/{run_id}/history   # Obtener gráficos de optimización (si aplica)
```

El frontend muestra las métricas y cualquier visualización de optimización al usuario.

---

### Creando un Gráfico para un Conjunto de Datos {#creating-a-plot-for-a-dataset}

Este ejemplo muestra cómo un usuario crea una exploración de gráfico de dispersión para un conjunto de datos.

#### Paso 1: Seleccionar un Explorador

El frontend obtiene los exploradores disponibles del registro:

```
GET /api/v1/component/?select_types=["Explorer"]
```

La respuesta incluye los esquemas de los componentes, de modo que el frontend puede renderizar los formularios de configuración de forma dinámica. El usuario selecciona `ScatterPlotExplorer`.

#### Paso 2: Configurar e Iniciar la Exploración

El usuario selecciona columnas y establece parámetros (por ejemplo, mapeo de colores). El frontend valida los parámetros del explorador:

```
POST /api/v1/explorer/validate
{
    "exploration_type": "ScatterPlotExplorer",
    "columns": ["sepal_length", "sepal_width"],
    "parameters": { "color": "species" }
}
```

Tras la validación, el frontend crea el explorador y encola el trabajo:

```
POST /api/v1/explorer/
{
    "notebook_id": 1,
    "exploration_type": "ScatterPlotExplorer",
    "columns": ["sepal_length", "sepal_width"],
    "parameters": { "color": "species" }
}
```

Esto crea un registro `Explorer` en la base de datos y encola un `ExplorerJob`.

#### Paso 3: Ejecución en Segundo Plano

El consumidor Huey recoge el `ExplorerJob` y llama a `job.run()`:

1. Cargar el registro `Explorer` y el conjunto de datos asociado.
2. Instanciar el componente `ScatterPlotExplorer`.
3. Llamar a `explorer.launch_exploration(dataset, explorer_info)`, que genera la visualización.
4. Llamar a `explorer.save_notebook()` para persistir la exploración como un notebook.
5. Llamar a `explorer.get_results()` para extraer la salida renderizable.
6. Guardar los resultados en disco y actualizar el estado del `Explorer` a `FINISHED`.

#### Paso 4: Mostrar Resultados

El frontend recupera los resultados de la exploración:

```
GET /api/v1/explorer/{explorer_id}/results
```

La respuesta contiene los datos del gráfico (normalmente una especificación JSON de Plotly), que el frontend renderiza como una visualización interactiva.

---

## Resumen

La arquitectura de DashAI se basa en algunos patrones clave:

- **Extensibilidad basada en componentes** — toda la funcionalidad de ML (modelos, tareas, métricas, exploradores, etc.) está encapsulada en componentes que comparten un mecanismo común de registro y configuración.
- **Configuración basada en esquemas** — los componentes declaran esquemas Pydantic que se convierten en JSON Schema para la generación dinámica de formularios en el frontend y la validación en el backend.
- **Procesamiento asincrónico de trabajos** — las operaciones de larga duración se delegan a un trabajador en segundo plano Huey, con seguimiento de estado mediante señales y actualizaciones en la base de datos.
- **Clara separación de responsabilidades** — la capa de API gestiona el HTTP, el registro de componentes gestiona el descubrimiento, la cola de trabajos gestiona la ejecución y la base de datos gestiona la persistencia.
