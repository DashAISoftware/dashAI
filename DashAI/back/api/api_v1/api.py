from fastapi import APIRouter

from DashAI.back.api.api_v1.endpoints import (
    components,
    converters,
    datasets,
    explainers,
    explorers,
    generative_process,
    generative_session,
    hardware,
    jobs,
    metrics,
    model_sessions,
    notebook,
    pipelines,
    plugins,
    predict,
    runs,
)

api_router_v1 = APIRouter()
api_router_v1.include_router(converters.router, prefix="/converter")
api_router_v1.include_router(components.router, prefix="/component")
api_router_v1.include_router(datasets.router, prefix="/dataset")
api_router_v1.include_router(model_sessions.router, prefix="/model-session")
api_router_v1.include_router(explainers.router, prefix="/explainer")
api_router_v1.include_router(explorers.router, prefix="/explorer")
api_router_v1.include_router(jobs.router, prefix="/job")
api_router_v1.include_router(runs.router, prefix="/run")
api_router_v1.include_router(predict.router, prefix="/predict")
api_router_v1.include_router(generative_session.router, prefix="/generative-session")
api_router_v1.include_router(generative_process.router, prefix="/generative-process")
api_router_v1.include_router(pipelines.router, prefix="/pipelines")
api_router_v1.include_router(plugins.router, prefix="/plugin")
api_router_v1.include_router(notebook.router, prefix="/notebook")
api_router_v1.include_router(metrics.router, prefix="/metrics")
api_router_v1.include_router(hardware.router, prefix="/hardware")
