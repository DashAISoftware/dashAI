from fastapi import APIRouter, Depends

from DashAI.back.api.api_v1.endpoints.app_config import router as app_config
from DashAI.back.api.api_v1.endpoints.auth import router as auth
from DashAI.back.api.api_v1.endpoints.components import router as components
from DashAI.back.api.api_v1.endpoints.converters import router as converters
from DashAI.back.api.api_v1.endpoints.credentials import router as credentials
from DashAI.back.api.api_v1.endpoints.datafile import router as datafile_router
from DashAI.back.api.api_v1.endpoints.dataset_source import router as dataset_source
from DashAI.back.api.api_v1.endpoints.datasets import router as datasets
from DashAI.back.api.api_v1.endpoints.documents import router as documents
from DashAI.back.api.api_v1.endpoints.explainers import router as explainers
from DashAI.back.api.api_v1.endpoints.explorers import router as explorers
from DashAI.back.api.api_v1.endpoints.folders import router as folders
from DashAI.back.api.api_v1.endpoints.generative_process import (
    router as generative_process,
)
from DashAI.back.api.api_v1.endpoints.generative_session import (
    router as generative_session,
)
from DashAI.back.api.api_v1.endpoints.hardware import router as hardware
from DashAI.back.api.api_v1.endpoints.jobs import router as jobs
from DashAI.back.api.api_v1.endpoints.metrics import router as metrics
from DashAI.back.api.api_v1.endpoints.model_sessions import router as model_sessions
from DashAI.back.api.api_v1.endpoints.notebook import router as notebook
from DashAI.back.api.api_v1.endpoints.pipelines import router as pipelines
from DashAI.back.api.api_v1.endpoints.plugins import router as plugins
from DashAI.back.api.api_v1.endpoints.predict import router as predict
from DashAI.back.api.api_v1.endpoints.projects import router as projects
from DashAI.back.api.api_v1.endpoints.prompts import router as prompts
from DashAI.back.api.api_v1.endpoints.rag import router as rag
from DashAI.back.api.api_v1.endpoints.reports import router as reports
from DashAI.back.api.api_v1.endpoints.runs import router as runs
from DashAI.back.api.api_v1.endpoints.statistical_tests import (
    router as statistical_tests,
)
from DashAI.back.api.api_v1.endpoints.system import router as system
from DashAI.back.auth.dependencies import get_current_user

# Every route needs a session, including the websockets (refused with 401
# before they are accepted). Endpoints that check permissions still ask for
# the user themselves; FastAPI resolves it once per request.
private = APIRouter(dependencies=[Depends(get_current_user)])
private.include_router(converters, prefix="/converter")
private.include_router(components, prefix="/component")
private.include_router(datasets, prefix="/dataset")
private.include_router(documents, prefix="/document")
private.include_router(model_sessions, prefix="/model-session")
private.include_router(explainers, prefix="/explainer")
private.include_router(reports, prefix="/report")
private.include_router(explorers, prefix="/explorer")
private.include_router(jobs, prefix="/job")
private.include_router(runs, prefix="/run")
private.include_router(predict, prefix="/predict")
private.include_router(generative_session, prefix="/generative-session")
private.include_router(generative_process, prefix="/generative-process")
private.include_router(pipelines, prefix="/pipelines")
private.include_router(plugins, prefix="/plugin")
private.include_router(prompts, prefix="/prompt")
private.include_router(notebook, prefix="/notebook")
private.include_router(metrics, prefix="/metrics")
private.include_router(hardware, prefix="/hardware")
private.include_router(dataset_source, prefix="/dataset-source")
private.include_router(datafile_router, prefix="/datafile")
private.include_router(statistical_tests, prefix="/statistical-tests")
private.include_router(folders, prefix="/folder")
private.include_router(credentials, prefix="/credential")
private.include_router(rag, prefix="/rag")
private.include_router(system, prefix="/system")
private.include_router(projects, prefix="/project")

api_router_v1 = APIRouter()
api_router_v1.include_router(private)
# The only routes open without a session, used by the login and register
# screens. Inside /auth, the routes about the current account (/me,
# /logout-all, /change-password) ask for the session themselves.
api_router_v1.include_router(app_config, prefix="/app-config")
api_router_v1.include_router(auth, prefix="/auth")
