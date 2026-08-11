import logging
import pickle
from typing import TYPE_CHECKING, Optional

from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException
from kink import di, inject
from sqlalchemy import exc

from DashAI.back.api.api_v1.endpoints.explainers import (
    _as_artifact_target,
    _as_group_target,
    _is_grouped_raw,
    _resolve_story_explainer,
)
from DashAI.back.api.api_v1.schemas.insights_params import InsightGenerationParams
from DashAI.back.core.enums.status import ExplainerStatus
from DashAI.back.dependencies.database.models import (
    GlobalExplainer,
    InsightResult,
    LocalExplainer,
)
from DashAI.back.insights.analyzers.explainer_insights import (
    EXPLAINER_INSIGHT_ANALYZERS,
)
from DashAI.back.job.insight_generation_job import InsightGenerationJob

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker

    from DashAI.back.dependencies.job_queues import BaseJobQueue
    from DashAI.back.dependencies.registry import ComponentRegistry

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

router = APIRouter()


def _find_raw_target(raw: list, title: str) -> Optional[object]:
    """Find the artifact/group in a pickled ``plot()`` output by its title.

    Mirrors the coercion ``_attach_stories`` already does for ``story()``
    (via ``_as_group_target``/``_as_artifact_target``), so the returned
    object is exactly what ``insight_facts()`` expects as its
    ``explainer_output`` argument.
    """
    for item in raw:
        if _is_grouped_raw(item):
            groups = item.groups if hasattr(item, "groups") else item.get("groups", [])
            for group in groups:
                target = _as_group_target(group)
                if target.title == title:
                    return target
        else:
            target = _as_artifact_target(item)
            if target.title == title:
                return target
    return None


@router.post("/explainer/{scope}/{explainer_id}", status_code=status.HTTP_201_CREATED)
@inject
async def create_explainer_insight(
    scope: str,
    explainer_id: int,
    params: InsightGenerationParams,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
    component_registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
    job_queue: "BaseJobQueue" = Depends(lambda: di["job_queue"]),
):
    """Generate an AI insight for one artifact of an explainer's explanation.

    Builds the ``AnalysisContext`` data (via the explainer's
    ``insight_facts()``), creates an ``InsightResult`` row, and enqueues an
    ``InsightGenerationJob`` to fill it in — all in one call, mirroring how
    ``ComponentDownloadJob`` is triggered from its own dedicated endpoint
    rather than the generic ``/api/v1/job/``.

    Parameters
    ----------
    scope : str
        Either ``"global"`` or ``"local"``.
    explainer_id : int
        Id of the explainer whose explanation is being analyzed.
    params : InsightGenerationParams
        Which artifact to analyze and which provider to use.

    Returns
    -------
    dict
        ``{"id": job_id, "insight_result_id": ...}``.

    Raises
    ------
    HTTPException
        400 for an invalid scope; 404 if the explainer, its explanation,
        the requested artifact, or an AI insight analyzer for it cannot be
        found; 500 on a database error.
    """
    if scope not in ("global", "local"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid scope"
        )

    model = GlobalExplainer if scope == "global" else LocalExplainer

    with session_factory() as db:
        try:
            explainer_row = db.get(model, explainer_id)
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e

        if explainer_row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Explainer not found"
            )
        if explainer_row.status != ExplainerStatus.FINISHED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Explanation not found"
            )

        analyzer_class = EXPLAINER_INSIGHT_ANALYZERS.get(explainer_row.explainer_name)
        if analyzer_class is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"No AI insight analyzer for '{explainer_row.explainer_name}'."
                ),
            )

        plot_path = (
            explainer_row.plot_path if scope == "global" else explainer_row.plots_path
        )
        with open(explainer_row.explanation_path, "rb") as file:
            explanation = pickle.load(file)
        with open(plot_path, "rb") as file:
            plot = pickle.load(file)

        target = _find_raw_target(plot, params.artifact_title)
        if target is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found"
            )

        story_explainer = _resolve_story_explainer(
            explainer_row.explainer_name, explainer_row.parameters, component_registry
        )
        if story_explainer is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="This explainer does not support AI insights.",
            )

        facts = story_explainer.insight_facts(explanation, target)
        if facts is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="AI insight not available for this artifact.",
            )

        insight_result = InsightResult(
            consumer_type=f"{scope}_explainer",
            consumer_id=explainer_id,
            consumer_ref=params.artifact_title,
            context_data=facts,
            context_metadata={"language": params.language},
            analyzer_path=(
                f"{analyzer_class.__module__}.{analyzer_class.__qualname__}"
            ),
            provider_kind=params.provider_kind,
            provider_params=params.provider_params,
        )
        db.add(insight_result)
        db.commit()
        db.refresh(insight_result)
        insight_result_id = insight_result.id

    job = InsightGenerationJob(insight_result_id=insight_result_id)
    job.set_status_as_delivered()
    job_id = job_queue.put(job).id
    return {"id": job_id, "insight_result_id": insight_result_id}


@router.get("/{insight_result_id}")
@inject
async def get_insight(
    insight_result_id: int,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Return the status and text (if ready) of one AI insight request.

    Parameters
    ----------
    insight_result_id : int
        Id of the ``InsightResult`` row to fetch.

    Returns
    -------
    dict
        ``{"id", "status", "result_text", "error_message"}``.

    Raises
    ------
    HTTPException
        404 if the insight result does not exist.
    """
    with session_factory() as db:
        result = db.get(InsightResult, insight_result_id)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Insight not found"
            )
        return {
            "id": result.id,
            "status": result.status.name,
            "result_text": result.result_text,
            "error_message": result.error_message,
        }
