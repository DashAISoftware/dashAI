---
title: REST API
sidebar_label: REST API
sidebar_position: 1
---

# REST API

DashAI exposes a RESTful API at `/api/v1`. All endpoints return JSON. The API is built with **FastAPI** and supports OpenAPI documentation at `/docs` (Swagger UI) and `/redoc`.

## Router Structure

| Router file | Resource prefix | Purpose |
|-------------|----------------|---------|
| `components.py` | `/api/v1/component` | List and filter registered components |
| `datasets.py` | `/api/v1/dataset` | Upload, list, and validate datasets |
| `model_sessions.py` | `/api/v1/model-session` | CRUD for model training sessions |
| `runs.py` | `/api/v1/run` | CRUD for training runs, metrics, optimization plots |
| `jobs.py` | `/api/v1/job` | Enqueue jobs and query job status |
| `explorers.py` | `/api/v1/explorer` | Launch and retrieve data explorations |
| `explainers.py` | `/api/v1/explainer` | Launch model explanations |
| `converters.py` | `/api/v1/converter` | Apply data transformations |
| `predict.py` | `/api/v1/predict` | Run predictions on new data |
| `plugins.py` | `/api/v1/plugin` | Manage installed plugins |
| `pipelines.py` | `/api/v1/pipeline` | Orchestrate complex workflows |
| `generative_session.py` | `/api/v1/generative-session` | Generative model sessions |
| `generative_process.py` | `/api/v1/generative-process` | Generative process execution and results |

## Key Endpoints

### Components

```http
GET /api/v1/component/
GET /api/v1/component/?select_types=["Model","Metric"]
```

Returns all registered components with their schemas and metadata. The frontend uses this to render configuration forms dynamically.

### Datasets

```http
GET    /api/v1/dataset/
POST   /api/v1/dataset/
GET    /api/v1/dataset/{dataset_id}
DELETE /api/v1/dataset/{dataset_id}
```

Datasets are uploaded as multipart form data.

### Model Sessions (Experiments)

```http
GET    /api/v1/model-session/
POST   /api/v1/model-session/
GET    /api/v1/model-session/{session_id}
PATCH  /api/v1/model-session/{session_id}
DELETE /api/v1/model-session/{session_id}
```

### Runs

```http
GET    /api/v1/run/
POST   /api/v1/run/
GET    /api/v1/run/{run_id}
PATCH  /api/v1/run/{run_id}
DELETE /api/v1/run/{run_id}
GET    /api/v1/run/metrics/{run_id}
GET    /api/v1/run/plot/{run_id}/history
```

### Jobs

```http
POST   /api/v1/job/
GET    /api/v1/job/status/{job_id}
```

All long-running operations (training, exploration, prediction) are submitted as jobs. The response includes a job ID for polling.

### Explorers

```http
GET    /api/v1/explorer/
POST   /api/v1/explorer/
POST   /api/v1/explorer/validate
GET    /api/v1/explorer/{explorer_id}/results
DELETE /api/v1/explorer/{explorer_id}
```

### Predictions

```http
GET    /api/v1/predict/
POST   /api/v1/predict/
GET    /api/v1/predict/{prediction_id}
DELETE /api/v1/predict/{prediction_id}
```

### Generative Sessions and Processes

```http
GET    /api/v1/generative-session/
POST   /api/v1/generative-session/
GET    /api/v1/generative-session/{session_id}
PATCH  /api/v1/generative-session/{session_id}
DELETE /api/v1/generative-session/{session_id}

POST   /api/v1/generative-process/
GET    /api/v1/generative-process/{process_id}
GET    /api/v1/generative-process/{process_id}/results
```

A **GenerativeSession** stores the model and parameters for a generative workflow
(text-to-text, text-to-image, ControlNet, etc.). Each invocation creates a
**GenerativeProcess** record that tracks status and stores input/output data.

## Dependency Injection

Endpoints receive database sessions, the component registry, and the job queue through FastAPI's `Depends` mechanism combined with the Kink DI container:

```python
@router.post("/")
@inject
async def create_run(
    run_params: RunParams,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
    component_registry: ComponentRegistry = Depends(lambda: di["component_registry"]),
    job_queue: BaseJobQueue = Depends(lambda: di["job_queue"]),
):
    ...
```

## Authentication

The current version does not implement authentication. The API is designed for local use.

## Interactive Docs

When running DashAI locally, you can explore the full API interactively:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI schema**: `http://localhost:8000/openapi.json`
