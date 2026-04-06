---
title: API
sidebar_label: API
---

DashAI uses **FastAPI** to expose a RESTful API. All endpoints live under the
`/api/v1` prefix.

## Router Structure

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

## Dependency Injection in Endpoints

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

## Internationalization

The API supports multilingual responses. Component display names and descriptions are
stored as `MultilingualString` objects, and the API filters them based on the
`Accept-Language` header.
