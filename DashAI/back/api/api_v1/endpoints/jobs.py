import asyncio
import json
import logging
import os
import tempfile
from urllib.parse import unquote

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.exceptions import HTTPException
from kink import di, inject
from streaming_form_data import StreamingFormDataParser
from streaming_form_data.targets import FileTarget, ValueTarget
from streaming_form_data.validators import MaxSizeValidator

from DashAI.back.dependencies.job_queues import BaseJobQueue
from DashAI.back.dependencies.job_queues.base_job_queue import JobQueueError
from DashAI.back.dependencies.registry import ComponentRegistry
from DashAI.back.job.base_job import BaseJob, JobError

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
@inject
async def get_jobs(
    job_queue: BaseJobQueue = Depends(lambda: di["job_queue"]),
):
    """Return all the jobs in the job queue."""
    return job_queue.to_list()


@router.get("/{job_id}")
@inject
async def get_job(
    job_id: int,
    job_queue: BaseJobQueue = Depends(lambda: di["job_queue"]),
):
    """Return the selected job from the job queue."""
    try:
        return job_queue.peek(job_id)
    except JobQueueError as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        ) from e


@router.post("/", status_code=status.HTTP_201_CREATED)
@inject
async def enqueue_job(
    request: Request,
    component_registry: ComponentRegistry = Depends(lambda: di["component_registry"]),
    job_queue: BaseJobQueue = Depends(lambda: di["job_queue"]),
):
    """Create a runner job and put it in the job queue."""
    MAX_FILE_SIZE = 4 * 1024**3  # 4GB
    content_type = request.headers.get("content-type", "")

    # parse multipart/form-data with file
    if "multipart/form-data" in content_type and "filename" in request.headers:
        filename = unquote(request.headers.get("filename", "uploaded_file"))
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, filename)

        parser = StreamingFormDataParser(headers=request.headers)
        parser.register(
            "file", FileTarget(file_path, validator=MaxSizeValidator(MAX_FILE_SIZE))
        )
        job_type_target = ValueTarget()
        kwargs_target = ValueTarget()
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
        kwargs.update(file_path=file_path, temp_dir=temp_dir, filename=filename)

    # parse regular form data
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

    # instantiate job with only primitive args
    JobClass = component_registry[job_type]["class"]
    job = JobClass(**kwargs)

    # mark delivered
    try:
        job.set_status_as_delivered()
    except JobError as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Job not delivered",
        ) from e

    # enqueue
    try:
        job_queue.put(job)
    except JobQueueError as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Job not enqueued"
        ) from e

    return job


@router.delete("/")
@inject
async def cancel_job(
    job_id: int,
    job_queue: BaseJobQueue = Depends(lambda: di["job_queue"]),
):
    """Delete the job with id job_id from the job queue."""
    try:
        job_queue.get(job_id)
    except JobQueueError as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        ) from e
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/")
async def update_job():
    """Placeholder for job update."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Method not implemented"
    )
