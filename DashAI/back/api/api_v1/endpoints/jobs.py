import asyncio
import json
import logging
import os
import tempfile
from urllib.parse import unquote

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.exceptions import HTTPException
from kink import di, inject
from sqlalchemy.orm import sessionmaker
from streaming_form_data import StreamingFormDataParser
from streaming_form_data.targets import FileTarget, ValueTarget
from streaming_form_data.validators import MaxSizeValidator

from DashAI.back.api.api_v1.schemas.job_params import JobParams
from DashAI.back.dependencies.job_queues import BaseJobQueue
from DashAI.back.dependencies.job_queues.base_job_queue import JobQueueError
from DashAI.back.dependencies.job_queues.job_queue import job_queue_loop
from DashAI.back.dependencies.registry import ComponentRegistry
from DashAI.back.job.base_job import BaseJob, JobError

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/start/")
async def start_job_queue(
    request: Request,
    stop_when_queue_empties: bool = False,
):
    """Start the asynchronous job queue loop.

    This endpoint starts a persistent background loop that executes pending jobs
    from the job queue. If the loop is already running, no new loop will be started.

    Parameters
    ----------
    request : Request
        FastAPI request object, used to access app state.
    stop_when_queue_empties : bool, optional
        If True, the loop stops once the queue is empty (useful for one-off job runs).
        If False, the loop waits indefinitely for new jobs.

    Returns
    -------
    Response
        HTTP 202 if loop was started (or already running).
    """
    app = request.app
    # Start the loop only if it's not already running or was cancelled
    if not hasattr(app.state, "job_loop") or app.state.job_loop.done():
        app.state.job_loop = asyncio.create_task(
            job_queue_loop(stop_when_queue_empties)
        )
        logger.info("Started job queue loop.")
    else:
        logger.debug("Job queue loop is already running.")

    return Response(status_code=status.HTTP_202_ACCEPTED)


@router.get("/")
@inject
async def get_jobs(
    job_queue: BaseJobQueue = Depends(lambda: di["job_queue"]),
):
    """Return all the jobs in the job queue.

    Parameters
    ----------
    job_queue : BaseJobQueue
        The current app job queue.

    Returns
    ----------
    List[dict]
        A list of dict containing the Jobs.
    """
    all_jobs = job_queue.to_list()
    return all_jobs


@router.get("/{job_id}")
@inject
async def get_job(
    job_id: int,
    job_queue: BaseJobQueue = Depends(lambda: di["job_queue"]),
):
    """Return the selected job from the job queue

    Parameters
    ----------
    job_id: int
        id of the Job to get.
    job_queue : BaseJobQueue
        The current app job queue.

    Returns
    ----------
    dict
        A dict containing the Job information.

    Raises
    ----------
    HTTPException
        If is not posible to get the job from the job queue.
    """
    try:
        job = job_queue.peek(job_id)
    except JobQueueError as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        ) from e
    return job


@router.post("/", status_code=status.HTTP_201_CREATED)
@inject
async def enqueue_job(
    request: Request,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
    component_registry: ComponentRegistry = Depends(lambda: di["component_registry"]),
    job_queue: BaseJobQueue = Depends(lambda: di["job_queue"]),
):
    """Create a runner job and put it in the job queue.

    This endpoint can handle both regular form data and form data with files.

    Parameters
    ----------
    request : Request
        The request object containing the form data.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.
    component_registry : ComponentRegistry
        Registry containing the current app available components.
    job_queue : BaseJobQueue
        The current app job queue.

    Returns
    -------
    dict
        dict with the new job on the database
    """
    MAX_FILE_SIZE = 1024 * 1024 * 1024 * 4  # 4GB

    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type and "filename" in request.headers:
        filename = unquote(request.headers.get("filename", "uploaded_file"))

        temp_dir = tempfile.mkdtemp()

        file_path = os.path.join(temp_dir, filename)

        file_target = FileTarget(file_path, validator=MaxSizeValidator(MAX_FILE_SIZE))
        job_type_target = ValueTarget()
        kwargs_target = ValueTarget()

        parser = StreamingFormDataParser(headers=request.headers)
        parser.register("file", file_target)
        parser.register("job_type", job_type_target)
        parser.register("kwargs", kwargs_target)

        async for chunk in request.stream():
            parser.data_received(chunk)

        job_type = job_type_target.value.decode() if job_type_target.value else None
        kwargs_str = kwargs_target.value.decode() if kwargs_target.value else None

        if not job_type or not kwargs_str:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Missing job_type or kwargs",
            )

        kwargs = json.loads(kwargs_str)
        kwargs["file_path"] = file_path
        kwargs["temp_dir"] = temp_dir
        kwargs["filename"] = filename

        with session_factory() as db:
            params = JobParams(job_type=job_type, kwargs=kwargs, db=db)
            job: BaseJob = component_registry[params.job_type]["class"](
                **params.model_dump()
            )

            try:
                job.set_status_as_delivered()
            except JobError as e:
                logger.exception(e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Job not delivered",
                ) from e

            try:
                job_queue.put(job)
            except JobQueueError as e:
                logger.exception(e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Job not enqueued",
                ) from e

        return job

    else:
        form = await request.form()
        job_type = form.get("job_type")
        kwargs_str = form.get("kwargs")

        if not job_type or not kwargs_str:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Missing job_type or kwargs",
            )

        kwargs = json.loads(kwargs_str)

        with session_factory() as db:
            params = JobParams(job_type=job_type, kwargs=kwargs, db=db)
            job: BaseJob = component_registry[params.job_type]["class"](
                **params.model_dump()
            )

            try:
                job.set_status_as_delivered()
            except JobError as e:
                logger.exception(e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Job not delivered",
                ) from e

            try:
                job_queue.put(job)
            except JobQueueError as e:
                logger.exception(e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Job not enqueued",
                ) from e

        return job


@router.delete("/")
@inject
async def cancel_job(
    job_id: int,
    job_queue: BaseJobQueue = Depends(lambda: di["job_queue"]),
):
    """Delete the job with id job_id from the job queue.

    Parameters
    ----------
    job_id : int
        id of the job to delete.
    job_queue : BaseJobQueue
        The current app job queue.

    Returns
    -------
    Response
        response with code 204 NO_CONTENT

    Raises
    ----------
    HTTPException
        If is not posible to get the job from the job queue.
    """
    try:
        job_queue.get(job_id)
    except JobQueueError as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        ) from e
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/")
async def update_job():
    """Placeholder for job update.

    Raises
    ------
    HTTPException
        Always raises exception as it was intentionally not implemented.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Method not implemented"
    )
