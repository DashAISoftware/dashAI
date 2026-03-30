---
title: Architecture
sidebar_label: Architecture
---

DashAI is a modular, extensible platform for machine learning workflows. It provides a
web-based interface for training models, exploring datasets, explaining predictions, and
more. This document describes how DashAI works internally.

## Table of Contents

- [High-Level Overview](#high-level-overview)
- [API](#api)
- [Components](#components)
- [Component Registry](#component-registry)
- [Configurable Object](#configurable-object)
- [Semantic Types](#semantic-types)
- [Database](#database)
- [Job Queue](#job-queue)
- [Job](#job)
- [Notebook](#notebook)
- [Workflow Examples](#workflow-examples)
  - [Training a Model](#training-a-model)
  - [Creating a Plot for a Dataset](#creating-a-plot-for-a-dataset)

---

## High-Level Overview

DashAI follows a client-server architecture with three main runtime processes:

1. **FastAPI backend** — serves the REST API on port 8000. In production it also serves
   the compiled React SPA at `/app/`.
2. **Huey consumer** — a background worker that processes long-running jobs (training,
   exploration, prediction, etc.).
3. **React frontend** — a single-page application that communicates with the backend
   through the REST API. In development it runs separately on port 3000 (`yarn start`);
   in production it is compiled and served by FastAPI.

The entry point is `DashAI/__main__.py`, which uses Typer as CLI. On startup it:

1. Resolves the local data path (defaults to `~/.DashAI`).
2. Starts the Huey consumer. In development (normal Python install) this is an external
   **subprocess**; in bundled mode (PyInstaller) it runs as an in-process **thread**.
3. Starts the FastAPI server via Uvicorn.
4. Optionally opens a browser or a PyWebView window.

Dependency injection is handled by **Kink**. The DI container (`back/container.py`)
wires together the database engine, session factory, component registry, and job queue
so that API endpoints can receive them automatically.

---

## API

DashAI uses **FastAPI** to expose a RESTful API. All endpoints live under the
`/api/v1` prefix.

### Router structure

The main FastAPI application is created in `back/app.py`. It mounts a single
`APIRouter` defined in `back/api/api_v1/api.py`, which aggregates individual routers
for each resource:

| Router file             | Resource              | Purpose                                             |
| ----------------------- | --------------------- | --------------------------------------------------- |
| `components.py`         | `/component`          | List and filter registered components               |
| `datasets.py`           | `/dataset`            | Upload, list, and validate datasets                 |
| `model_sessions.py`     | `/model-session`      | CRUD for model training sessions                    |
| `runs.py`               | `/run`                | CRUD for training runs, metrics, optimization plots |
| `jobs.py`               | `/job`                | Enqueue jobs and query job status                   |
| `explorers.py`          | `/explorer`           | Launch and retrieve data explorations               |
| `explainers.py`         | `/explainer`          | Launch model explanations                           |
| `converters.py`         | `/converter`          | Apply data transformations                          |
| `predict.py`            | `/predict`            | Run predictions on new data                         |
| `plugins.py`            | `/plugin`             | Manage plugins                                      |
| `generative_session.py` | `/generative-session` | Generative model sessions                           |
| `generative_process.py` | `/generative-process` | Generative process execution and results            |

### Dependency injection in endpoints

Endpoints receive dependencies through FastAPI's `Depends` mechanism combined with
Kink's `di` container:

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

### Internationalization

The API supports multilingual responses. Component display names and descriptions are
stored as `MultilingualString` objects, and the API filters them based on the
`Accept-Language` header.

---

## Components

A **component** is the fundamental building block of DashAI. Every pluggable piece of
functionality — models, tasks, metrics, explorers, explainers, converters, data loaders,
optimizers, and jobs — is a component.

### Component types

Each component class declares a `TYPE` class attribute that determines its category:

| TYPE              | Base class            | Purpose                              | Examples                                                            |
| ----------------- | --------------------- | ------------------------------------ | ------------------------------------------------------------------- |
| `Model`           | `BaseModel`           | Train and predict                    | SVC, RandomForest, DistilBertTransformer                            |
| `GenerativeModel` | `BaseGenerativeModel` | Generate outputs from prompts/inputs | QwenModel, StableDiffusionV2Model                                   |
| `Task`            | `BaseTask`            | Define ML task semantics             | TextClassification, Regression, Translation                         |
| `GenerativeTask`  | `BaseGenerativeTask`  | Define generative task semantics     | TextToTextGenerationTask, TextToImageGenerationTask, ControlNetTask |
| `Metric`          | `BaseMetric`          | Evaluate model performance           | Accuracy, F1, RMSE, MAE                                             |
| `Explorer`        | `BaseExplorer`        | Visualize and analyze data           | ScatterPlotExplorer, HistogramPlotExplorer                          |
| `Explainer`       | `BaseExplainer`       | Interpret model predictions          | KernelShap, PermutationFeatureImportance                            |
| `Converter`       | `BaseConverter`       | Transform features                   | StandardScaler, OneHotEncoder, PCA, SMOTE                           |
| `DataLoader`      | `BaseDataLoader`      | Load datasets from files             | CSVDataLoader, ExcelDataLoader                                      |
| `Optimizer`       | `BaseOptimizer`       | Hyperparameter optimization          | Optuna-based optimizers                                             |
| `Job`             | `BaseJob`             | Background task execution            | ModelJob, ExplorerJob, PredictJob                                   |

### Component metadata

Every component can expose metadata used by the frontend for display and filtering:

- `DESCRIPTION` — a multilingual description of what the component does.
- `DISPLAY_NAME` — a human-readable name.
- `COLOR` — a hex color for UI rendering.
- `COMPATIBLE_COMPONENTS` — a list of component names this component works with
  (e.g., a metric that only applies to classification tasks).

---

## Component Registry

The **Component Registry** (`back/dependencies/registry/component_registry.py`) is a
centralized catalog of all available components. It is created during application
startup and stored in the DI container.

### Registration

When a component class is registered, the registry:

1. Reads the `TYPE` class attribute to determine the component category.
2. Checks whether the class is a configurable object (has `get_schema()`).
3. Extracts metadata (`DESCRIPTION`, `DISPLAY_NAME`, `COLOR`, etc.).
4. Stores the component in a hierarchical dictionary keyed by type and name.

Each registered component is stored as a dictionary:

```python
{
    "name": "SVC",
    "type": "Model",
    "class": SVCClass,
    "configurable_object": True,
    "schema": { ... },       # JSON Schema if configurable
    "metadata": { ... },
    "description": MultilingualString(...),
    "display_name": MultilingualString(...),
    "color": "#3498db",
}
```

### Lookup methods

| Method                                    | Description                                           |
| ----------------------------------------- | ----------------------------------------------------- |
| `registry[name]`                          | Direct lookup by component name                       |
| `get_components_by_types(select, ignore)` | Filter components by type (e.g., only Models)         |
| `get_child_components(parent_name)`       | Get all components that inherit from a given parent   |
| `get_related_components(component_id)`    | Get compatible components via `COMPATIBLE_COMPONENTS` |

### Initialization

The list of components to register on startup is defined in
`back/initial_components.py`. Additional components can be added at runtime through the
plugin system.

---

## Configurable Object

A **Configurable Object** is any component whose behavior can be customized through
user-supplied parameters. The mechanism is built on top of Pydantic and JSON Schema.

### How it works

1. **Schema definition** — A component defines a `SCHEMA` class attribute as a Pydantic
   model. Each field in the model represents a configurable parameter:

   ```python
   class LogisticRegressionSchema(BaseSchema):
       penalty: schema_field(
           none_type(enum_field(enum=["l1", "l2", "elasticnet"])),
           placeholder="l2",
           description=MultilingualString(
               en="Type of regularization penalty.",
               es="Tipo de penalización de regularización.",
           ),
           alias=MultilingualString(en="Penalty", es="Penalización"),
       )  # type: ignore
       C: schema_field(
           optimizer_float_field(gt=0.0),
           placeholder={"optimize": False, "fixed_value": 1.0,
                        "lower_bound": 0.01, "upper_bound": 100.0},
           description=MultilingualString(
               en="Inverse of regularization strength.",
               es="Inverso de la fuerza de regularización.",
           ),
           alias=MultilingualString(en="C", es="C"),
       )  # type: ignore
   ```

   Each field uses `schema_field()` with a type validator (e.g. `optimizer_float_field`,
   `enum_field`), a placeholder default, a bilingual description, and an alias for the UI
   label. The frontend uses the generated JSON Schema to render form controls; the
   optimizer uses type metadata to define search bounds.

2. **Schema generation** — `get_schema()` converts the Pydantic model into a JSON
   Schema dictionary. The frontend uses this schema to dynamically render configuration
   forms.

3. **Validation and transformation** — When the user submits a configuration, the
   backend calls `validate_and_transform(params)` which:
   - Validates raw parameter data against the Pydantic schema.
   - Recursively instantiates any nested component references (a parameter of type
     `ComponentType` is resolved into an actual component instance).

### Component fields

The `component_field()` utility (`back/core/schema_fields/component_field.py`) creates
parameters that reference other components. For example, a model might accept a
converter as a parameter:

```python
class BagOfWordsSchema(BaseSchema):
    tabular_classifier: schema_field(
        component_field(component_type="TabularClassificationModel"),
        placeholder=None,
        description=MultilingualString(
            en="Tabular classifier used as the underlying model.",
            es="Clasificador tabular usado como modelo subyacente.",
        ),
        alias=MultilingualString(
            en="Tabular classifier", es="Clasificador tabular"
        ),
    )  # type: ignore
```

The frontend renders component fields as a searchable dropdown populated from the
registry. When the component is instantiated, `validate_and_transform()` resolves the
selected component name into a live instance.

---

## Semantic Types

Every column in a DashAI dataset has a **semantic type** — a classification that goes beyond raw storage formats (e.g. `int32`, `string`) to express the ML-meaningful nature of the data: is this a continuous measurement, a discrete label, free-form text, or a date?

### Type hierarchy

```
DashAIDataType
├── DashAIValue   →  Integer, Float, Text, Date, Time, Timestamp, Duration, Decimal, Binary
└── Categorical   →  discrete labels with a str ↔ int encoding map
```

### Role in the system

| Where | How semantic types are used |
|-------|-----------------------------|
| **Dataset loading** | `infer_types()` assigns a type to every column via probabilistic inference (ptype) or a heuristic fallback. Types are persisted to Apache Arrow table metadata. |
| **Task validation** | Each task declares `inputs_types` and `outputs_types`. `validate_dataset_for_task()` rejects columns that do not match. For example, `TabularClassificationTask` requires a `Categorical` output. |
| **Converters** | Each converter implements `get_output_type()` to declare its output type, enabling type-safe pipeline chaining (e.g. `OneHotEncoder`: `Categorical` → `Integer`). |
| **Label encoding** | `Categorical` output columns are automatically integer-encoded before training and decoded back to string labels after prediction using the type's built-in `str2int` / `int2str` maps. |
| **Column-type edits** | `validate_type_change()` guards manual type changes in the UI, rejecting unsafe conversions (e.g. high-cardinality text promoted to `Categorical`). |

For the full type catalogue, inference logic, and conversion rules, see [Deep Dive → Semantic Types](./semantic-types).

---

## Database

DashAI uses **SQLite** as its database (stored at `~/.DashAI/db.sqlite`) with
**SQLAlchemy** as ORM and **Alembic** for schema migrations.

### Key tables

| Table                               | Purpose                                                                                                                                                                                                                         |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Dataset`                           | Uploaded dataset — name, Arrow file path, loading status, and timestamps.                                                                                                                                                       |
| `ModelSession`                      | Experiment configuration — dataset, task name, input/output columns, train/validation/test split ratios, and selected metrics per split.                                                                                        |
| `Run`                               | Individual training execution within a ModelSession — model name, parameters, optimizer config, goal metric, run artifacts, execution status and timing, and paths to optimization plots (history, slice, contour, importance). |
| `Metric`                            | Single metric measurement — name, value, split (`TRAIN`/`VALIDATION`/`TEST`), level (`LAST`/`STEP`/`BATCH`/`TRIAL`), and step index. Linked to a Run.                                                                           |
| `Prediction`                        | Prediction job — links a trained Run to an input Dataset, tracks execution status and timing, and stores the path to output results.                                                                                            |
| `GenerativeSession`                 | Generative model session — task type, model name, current parameters, and a human-readable name and description. Owns a history of parameter snapshots and all associated GenerativeProcess records.                            |
| `GenerativeProcess`                 | Single invocation of a GenerativeSession — tracks execution status and timing. Linked to ProcessData records that hold the input and output payloads.                                                                           |
| `ProcessData`                       | Input or output payload for a GenerativeProcess — serialized data value, data type (text, image, etc.), and an `is_input` flag to distinguish inputs from outputs.                                                              |
| `GenerativeSessionParameterHistory` | Immutable snapshot of a GenerativeSession's parameters captured at each change, providing a full audit trail of parameter evolution over time.                                                                                  |
| `Notebook`                          | Working dataset session — a mutable copy of a source Dataset on which Explorers and Converters can be applied. Changes can be reverted; the result can be saved as a new Dataset for model training.                            |
| `Explorer`                          | Visualization record within a Notebook — explorer type, selected columns, parameters, path to saved results, and execution status.                                                                                              |
| `Converter`                         | Single converter step applied to a Notebook's mutable dataset — converter type, parameters, execution status, and timing. Multiple records form an ordered transformation pipeline on the Notebook.                             |
| `Plugin`                            | Installed plugin — name, author, installed and latest versions, status, summary, and full description. Owns Tag records for classification.                                                                                     |
| `Tag`                               | Classification tag for a Plugin (e.g., `Model`, `Task`, `Metric`), used for filtering and discovery.                                                                                                                            |
| `GlobalExplainer`                   | Global model explanation — explainer type, linked Run, parameters, paths to explanation data and plot, and execution status. Covers the model as a whole.                                                                       |
| `LocalExplainer`                    | Local (per-instance) explanation — explainer type, linked Run and Dataset, parameters, fit parameters, scope, result paths, and execution status.                                                                               |

### Important enums

- **`RunStatus`**: `NOT_STARTED` → `DELIVERED` → `STARTED` → `FINISHED` | `ERROR`
- **`SplitEnum`**: `TRAIN`, `VALIDATION`, `TEST`
- **`LevelEnum`**: `LAST` (final value), `STEP`, `BATCH`, `TRIAL` (for optimization)

### Data storage

- **Datasets** are stored in Apache Arrow IPC format (columnar, efficient for ML
  workloads).
- **Trained models** are saved as pickle/joblib files under `~/.DashAI/runs/{run_id}/`.
- **Plots** generated during hyperparameter optimization are stored as serialized Plotly
  objects.
- **Metric time-series** (per step, batch, or trial) are stored in the `Metric` table
  for tracking training progress.

---

## Job Queue

The **Job Queue** handles asynchronous execution of long-running tasks. DashAI uses
**Huey** — a lightweight Python task queue — backed by a SQLite database.

### Architecture

| Layer          | Implementation                                                    |
| -------------- | ----------------------------------------------------------------- |
| Abstract base  | `BaseJobQueue` (`back/dependencies/job_queues/base_job_queue.py`) |
| Concrete impl. | `HueyJobQueue` (`back/dependencies/job_queues/huey_job_queue.py`) |
| Storage        | SQLite at `~/.DashAI/job_queue.db` (separate from main DB)        |
| Serialization  | `dill` (handles complex Python objects like lambdas)              |

### How the queue works

1. An API endpoint calls `job_queue.put(job)`, which enqueues the job and returns a
   job ID immediately.
2. The Huey consumer thread (started at application boot) picks up the job and calls
   `job.run()`.
3. Job lifecycle is tracked via Huey signals and a `task_copy` table:

   | Signal             | Status update |
   | ------------------ | ------------- |
   | `SIGNAL_ENQUEUED`  | `not_started` |
   | `SIGNAL_EXECUTING` | `started`     |
   | `SIGNAL_COMPLETE`  | `finished`    |
   | `SIGNAL_ERROR`     | `error`       |

4. The frontend polls `GET /api/v1/job/status/{job_id}` to track progress.

### Key methods

| Method              | Description                         |
| ------------------- | ----------------------------------- |
| `put(job)`          | Enqueue a job, returns job ID       |
| `get(job_id)`       | Get job status and metadata         |
| `peek()`            | View the next job without dequeuing |
| `is_empty()`        | Check if the queue has pending jobs |
| `async_get(job_id)` | Async version of get                |

The SQLite backend uses Write-Ahead Logging (WAL) mode for safe concurrent access
between the API process and the Huey consumer.

---

## Job

A **Job** encapsulates a unit of background work. All jobs inherit from `BaseJob`
(`back/job/base_job.py`).

### Base interface

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

### Job types

| Job class       | Purpose                                          |
| --------------- | ------------------------------------------------ |
| `ModelJob`      | Train a model and compute metrics                |
| `ExplorerJob`   | Execute a data exploration/visualization         |
| `ExplainerJob`  | Generate model explanations (SHAP, etc.)         |
| `PredictJob`    | Run predictions on new data                      |
| `ConverterJob`  | Apply data transformations to a Notebook dataset |
| `GenerativeJob` | Handle generative model interactions             |
| `DatasetJob`    | Load and process datasets                        |

Each job type manages its own database status transitions and error handling. When a job
fails, it records the error message in the database and updates the relevant entity's
status to `ERROR`.

---

## Notebook

A **Notebook** is a working session that lets users interact with a dataset without
modifying the original data.

### What is a Notebook?

When a Notebook is created from a dataset, DashAI makes a **mutable copy** of the
original dataset. The source `Dataset` record is never modified. Within a Notebook,
users can:

- Run **Explorers** (scatter plots, histograms, box plots) to visualize the data.
- Apply **Converters** (StandardScaler, PCA, SMOTE, etc.) to transform the dataset copy.
- **Revert** any converter to restore an earlier state.
- **Save** the modified dataset as a new `Dataset` record available for model training.

### Database representation

A Notebook is stored in the `Notebook` table, linked to the source `Dataset`. Each
Explorer or Converter applied within the Notebook creates an `Explorer` or `Converter`
record. Converters are applied sequentially via a `ConverterJob`.

### Lifecycle

```
Original Dataset ──(copy)──► Notebook Dataset
                                    │
                       Apply Explorers   (read-only visualizations)
                       Apply Converters  (in-place on mutable copy)
                       Revert Converters (restore earlier state)
                                    │
                            Save ──► New Dataset (available for training)
```

---

## Workflow Examples

### Training a Model

This example walks through the entire process of training a text classification model,
from user interaction to final results.

#### Step 1: Create a Model Session

The user selects a dataset, a task, input/output columns, metrics, and data splits in
the frontend. The frontend sends:

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

The API creates a `ModelSession` record in the database and returns its ID.

#### Step 2: Create a Run

The user selects a model, configures its parameters, and optionally selects a
hyperparameter optimizer. The frontend sends:

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

The API creates a `Run` record with status `NOT_STARTED`.

#### Step 3: Enqueue the training job

The frontend requests job execution:

```
POST /api/v1/job/
{
    "job_type": "ModelJob",
    "kwargs": { "run_id": 1 }
}
```

The API instantiates a `ModelJob` with the given `run_id`, calls `job_queue.put(job)`,
and returns the Huey job ID to the frontend immediately.

#### Step 4: Background execution

The Huey consumer picks up the `ModelJob` and calls `job.run()`. Inside `run()`:

1. Load the `Run`, `ModelSession`, and `Dataset` records from the database.
2. Load the dataset from its Arrow file.
3. Instantiate the `Task` class (e.g., `TextClassification`) and call
   `prepare_for_task()` to validate and format the data.
4. Split the data into train/validation/test subsets based on the session's split
   ratios.
5. Instantiate the `Model` class (e.g., `DistilBertTransformer`) with the user's
   parameters via `validate_and_transform()`.
6. Call `model.train(x_train, y_train, x_val, y_val)`.
7. For each split (train, validation, test), call `model.calculate_metrics()` which
   computes all selected metrics and stores them in the `Metric` table.
8. Save the trained model to disk at `~/.DashAI/runs/{run_id}/`.
9. Update the `Run` status from `STARTED` to `FINISHED`.

If a hyperparameter optimizer is configured, step 6 is replaced by
`optimizer.optimize()`, which runs multiple trials, tracks per-trial metrics
(`LevelEnum.TRIAL`), and generates Plotly visualization plots (history, slice, contour,
importance) saved alongside the run.

#### Step 5: Retrieve results

The frontend polls for completion and retrieves results:

```
GET /api/v1/job/status/{job_id}         # Poll until finished
GET /api/v1/run/{run_id}                # Get run details with metrics
GET /api/v1/run/plot/{run_id}/history   # Get optimization plots (if applicable)
```

The frontend displays the metrics and any optimization visualizations to the user.

---

### Creating a Plot for a Dataset

This example shows how a user creates a scatter plot exploration for a dataset.

#### Step 1: Select an explorer

The frontend fetches available explorers from the registry:

```
GET /api/v1/component/?select_types=["Explorer"]
```

The response includes component schemas, so the frontend can render configuration forms
dynamically. The user selects `ScatterPlotExplorer`.

#### Step 2: Configure and launch the exploration

The user selects columns and sets parameters (e.g., color mapping). The frontend
validates the explorer's parameters:

```
POST /api/v1/explorer/validate
{
    "exploration_type": "ScatterPlotExplorer",
    "columns": ["sepal_length", "sepal_width"],
    "parameters": { "color": "species" }
}
```

After validation, the frontend creates the explorer and enqueues the job:

```
POST /api/v1/explorer/
{
    "notebook_id": 1,
    "exploration_type": "ScatterPlotExplorer",
    "columns": ["sepal_length", "sepal_width"],
    "parameters": { "color": "species" }
}
```

This creates an `Explorer` record in the database and enqueues an `ExplorerJob`.

#### Step 3: Background execution

The Huey consumer picks up the `ExplorerJob` and calls `job.run()`:

1. Load the `Explorer` record and the associated dataset.
2. Instantiate the `ScatterPlotExplorer` component.
3. Call `explorer.launch_exploration(dataset, explorer_info)`, which generates the
   visualization.
4. Call `explorer.save_notebook()` to persist the exploration as a notebook.
5. Call `explorer.get_results()` to extract the renderable output.
6. Save results to disk and update the `Explorer` status to `FINISHED`.

#### Step 4: Display results

The frontend retrieves the exploration results:

```
GET /api/v1/explorer/{explorer_id}/results
```

The response contains the plot data (typically a Plotly JSON specification), which the
frontend renders as an interactive visualization.

---

## Summary

DashAI's architecture is built around a few key patterns:

- **Component-based extensibility** — all ML functionality (models, tasks, metrics,
  explorers, etc.) is encapsulated in components that share a common registration and
  configuration mechanism.
- **Schema-driven configuration** — components declare Pydantic schemas that are
  converted to JSON Schema for dynamic frontend form generation and backend validation.
- **Asynchronous job processing** — long-running operations are offloaded to a Huey
  background worker, with status tracking via signals and database updates.
- **Clean separation of concerns** — the API layer handles HTTP, the component registry
  handles discovery, the job queue handles execution, and the database handles
  persistence.
